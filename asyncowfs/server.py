"""
Access to an owserver.
"""

import anyio

from collections import deque
from typing import Union
from functools import partial
from concurrent.futures import CancelledError

from .event import ServerConnected, ServerDisconnected
from .event import BusAdded
from .protocol import (
    NOPMsg,
    DirMsg,
    AttrGetMsg,
    AttrSetMsg,
    MessageProtocol,
    ServerBusy,
)
from .bus import Bus
from .util import ValueEvent

import logging

logger = logging.getLogger(__name__)


class Server:
    """\
        Encapsulate one server connection.
    """

    def __init__(self, service, host="localhost", port=4304, name=None):
        self.service = service
        self.host = host
        self.port = port
        self.name = name or host
        self.stream = None
        self._msg_proto = None
        self.requests = deque()
        self._wqueue_w, self._wqueue_r = anyio.create_memory_object_stream(100)
        self._read_task = None
        self._write_task = None
        self._scan_task = None
        self._buses = dict()  # path => bus
        self._scan_lock = anyio.Lock()
        self._scan_args = None
        self._backoff = 2
        self._current_tg = None
        self._current_run = None

        self.simul_lock = anyio.Lock()

    async def get_bus(self, *path):
        """Return the bus at this path. Allocate new if not existing."""
        try:
            return self._buses[path]
        except KeyError:
            bus = Bus(self, *path)
            self._buses[bus.path] = bus
            await self.service.push_event(BusAdded(bus))
            return bus

    def __repr__(self):
        return "<%s:%s:%d %s>" % (
            self.__class__.__name__,
            self.host,
            self.port,
            "OK" if self.stream else "closed",
        )

    async def _reader(self, evt):
        try:
            with anyio.CancelScope() as scope:
                self._read_task = scope
                evt.set()
                it = self._msg_proto.__aiter__()
                while True:
                    try:
                        with anyio.fail_after(15):
                            res, data = await it.__anext__()
                    except StopAsyncIteration:
                        raise anyio.ClosedResourceError from None
                    except ServerBusy:
                        logger.debug("Server %s busy", self.host)
                    else:
                        msg = self.requests.popleft()
                        await msg.process_reply(res, data, self)
                        if not msg.done():
                            self.requests.appendleft(msg)
        except anyio.ClosedResourceError:
            if self._current_tg is not None:
                self._current_tg.cancel_scope.cancel()

    async def _run_one(self, val: ValueEvent):
        try:
            async with anyio.create_task_group() as tg:
                self._current_tg = tg
                self.stream = await anyio.connect_tcp(self.host, self.port)

                ml, self.requests = deque(self.requests), deque()
                try:
                    self._msg_proto = MessageProtocol(self, is_server=False)

                    e_w = anyio.Event()
                    e_r = anyio.Event()
                    tg.start_soon(self._writer, e_w)
                    tg.start_soon(self._reader, e_r)
                    await e_r.wait()
                    await e_w.wait()

                    # re-send messages, but skip those that have been cancelled
                    while ml:
                        msg = ml.popleft()
                        if not msg.cancelled:
                            try:
                                await self._wqueue_w.send(msg)
                            except BaseException:
                                ml.appendleft(msg)

                except BaseException:
                    self.requests = ml
                    raise

                await self.chat(NOPMsg())

                if self._scan_args is not None:
                    tg.start_soon(partial(self.start_scan, **self._scan_args))
                    #tg.spawn(partial(self.start_scan, **self._scan_args))
                if val is not None:
                    val.set(None)
                self._backoff = 0.1
                pass  # wait for tasks
            pass  # exited tasks

        finally:
            self._current_tg = None
            if self.stream is not None:
                with anyio.CancelScope(shield=True):
                    await self.stream.aclose()
                self.stream = None

    async def start(self):
        """Start talking. Returns when the connection is established,
        raises an error if that's not possible.
        """
        val = ValueEvent()
        self.service.nursery.start_soon(self._run_reconnected, val)
        await val.get()
        await self.service.push_event(ServerConnected(self))

    async def _run_reconnected(self, val: ValueEvent):
        try:
            with anyio.CancelScope() as scope:
                self._current_run = scope
                while True:
                    try:
                        await self._run_one(val)
                    except anyio.get_cancelled_exc_class():
                        raise
                    except (
                        BrokenPipeError,
                        TimeoutError,
                        EnvironmentError,
                        anyio.IncompleteRead,
                        ConnectionResetError,
                        anyio.ClosedResourceError,
                        StopAsyncIteration,
                    ) as exc:
                        if val is not None and not val.is_set():
                            val.set_error(exc)
                            return
                        logger.error("Disconnected")
                        val = None

                        await anyio.sleep(self._backoff)
                        if self._backoff < 10:
                            self._backoff *= 1.5
                    else:
                        pass
        finally:
            self._current_run = None

    async def setup_struct(self, dev):
        await dev.setup_struct(self)

    async def chat(self, msg):
        await self._wqueue_w.send(msg)
        try:
            res = await msg.get_reply()
            return res
        except BaseException:
            msg.cancel()
            raise

    async def _writer(self, evt):
        with anyio.CancelScope() as scope:
            self._write_task = scope
            evt.set()
            while True:
                try:
                    with anyio.fail_after(10):
                        msg = await self._wqueue_r.receive()
                except TimeoutError:
                    msg = NOPMsg()

                self.requests.append(msg)
                await msg.write(self._msg_proto)

    async def drop(self):
        """Stop talking and delete yourself"""
        try:
            await self.aclose()
        finally:
            await self.service._del_server(self)

    async def aclose(self):
        if self._current_run is not None:
            self._current_run.cancel()
        if self._current_tg is not None:
            self._current_tg.cancel_scope.cancel()

        await self.service.push_event(ServerDisconnected(self))

        if self._buses is not None:
            for b in list(self._buses.values()):
                await b.delocate()
        self._buses = None
        for m in self.requests:
            m.cancel()

    @property
    def all_buses(self):
        for b in list(self._buses.values()):
            yield from b.all_buses

    async def dir(self, *path):
        return await self.chat(DirMsg(path))

    async def _scan(self, interval, initial_interval, polling, random=0):
        if not initial_interval:
            initial_interval = interval
        # 5% variation, to prevent clustering
        if random:
            initial_interval *= 1 + (random() - 0.5) / random
        await anyio.sleep(initial_interval)

        while True:
            await self.scan_now(polling=polling)
            #async with self._scan_lock:
            #    await self._scan_base(polling=polling)
            if not interval:
                return
            i = interval
            if random:
                i *= 1 + (random() - 0.5) / random
            await anyio.sleep(i)

    async def scan_now(self, polling=True):
        if self._scan_lock.locked():
            # scan in progress: just wait for it to finish
            async with self._scan_lock:
                pass
        else:
            async with self._scan_lock:
                await self._scan_base(polling=polling)

    async def _scan_base(self, polling=True):
        old_paths = set(self._buses.keys())

        # step 1: enumerate
        try:
            for d in await self.dir():
                if d.startswith("bus."):
                    bus = await self.get_bus(d)
                    bus._unseen = 0
                    try:
                        old_paths.remove(d)
                    except KeyError:
                        pass
                    buses = await bus._scan_one(polling=polling)
                    old_paths -= buses
        except CancelledError:
            return

        # step 2: deregister buses, if not seen often enough
        for p in old_paths:
            bus = self._buses.get(p, None)
            if bus is None:
                continue
            if bus._unseen > 2:
                await bus.delocate()
            else:
                bus._unseen += 1

    async def start_scan(
        self,
        scan: Union[float, None] = None,
        initial_scan: Union[float, bool] = True,
        polling=True,
        random: int = 0,
    ):
        """Scan this server.

        :param scan: Flag how often to re-scan the bus.
            None: don't scan at all
            >0: repeat in the background
        :param initial_scan: Flag when to initially scan the bus.
            False: don't.
            True: immediately, wait until complete.
            >0: return immediately, delay initial scan that many seconds.
        :type scan: :class:`float` or ``None``
        :type initial_scan: :class:`float` or :class:`bool`
        :param polling: Flag whether to start tasks for periodic polling
            (alarm handling, temperature, …). Defaults to ``True``.
        """
        self._scan_args = dict(scan=scan, initial_scan=False, polling=polling, random=random)
        if not scan and not initial_scan:
            return
        if scan and scan < 1:
            raise RuntimeError("You can't scan that often.")
        if initial_scan is True:
            await self.scan_now(polling=polling)
            initial_scan = False

        if initial_scan or scan:
            self._scan_task = self._current_tg.start_soon(
                self._scan, scan, initial_scan, polling, random
            )
#            self._scan_task = await self._current_tg.spawn(
#                self._scan, scan, initial_scan, polling, random
#            )

    async def attr_get(self, *path):
        return await self.chat(AttrGetMsg(*path))

    async def attr_set(self, *path, value):
        return await self.chat(AttrSetMsg(*path, value=value))
