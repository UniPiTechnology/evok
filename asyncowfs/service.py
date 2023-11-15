# base implementation

import anyio
from functools import partial

try:
    from contextlib import asynccontextmanager
except ImportError:
    from async_generator import asynccontextmanager

from typing import Optional, Union

from .server import Server
from .device import Device
from .event import ServerRegistered, ServerDeregistered
from .event import DeviceAdded, DeviceDeleted
from .util import ValueEvent

import logging

logger = logging.getLogger(__name__)

__all__ = ["OWFS"]


class Service:
    """\
        This is the master class you use for communicating with OWFS.
        You typically start it thus::

            async def rdr(ow):
                async for evt in ow:
                    process(evt)

            async with OWFS() as ow:
                await ow.add_task(rdr, ow)
                s = await ow.add_server("localhost",4304)

        :param scan: time between directory scanning.
            None: do not scan repeatedly

        :param initial_scan: time to first scan
            False: no initial scal
            True: scan immediately, block before returning

        :param polling: flag whether to poll devices.
            Default: True.

        :param load_structs: Flag whether to generate accessors from OWFS data.
            Default: True
        """

    def __init__(
        self,
        nursery,
        scan: Union[float, None] = None,
        initial_scan: Union[float, bool] = True,
        load_structs: bool = True,
        polling: bool = True,
        random: int = 0,
    ):
        self.nursery = nursery
        self._servers = set()  # typ.MutableSet[Server]  # Server
        self._devices = dict()  # ID => Device
        self._tasks = set()  # typ.MutableSet[]  # actually their cancel scopes
        self._event_queue = None  # typ.Optional[anyio.Queue]
        self._random = random
        self._scan = scan
        self._initial_scan = initial_scan
        self._polling = polling
        self._load_structs = load_structs

    async def add_server(
        self,
        host: str,
        port: int = 4304,
        polling: Optional[bool] = None,
        scan: Union[float, bool, None] = None,
        initial_scan: Union[float, bool, None] = None,
        random: Optional[int] = None,
        name: str = None,
    ):
        """Add this server to the list.

        :param polling: if False, don't poll.
        :param scan: Override ``self._scan`` for this server.
        :param initial_scan: Override ``self._initial_scan`` for this server.
        """
        if scan is None:
            scan = self._scan
        if initial_scan is None:
            initial_scan = self._initial_scan
        if polling is None:
            polling = self._polling
        if random is None:
            random = self._random
        if name is None:
            name = host

        s = Server(self, host, port, name=name)
        await self.push_event(ServerRegistered(s))
        try:
            await s.start()
        except BaseException as exc:
            logger.error("Could not start %s:%s %s", host, port, repr(exc))
            await self.push_event(ServerDeregistered(s))
            raise
        self._servers.add(s)
        await s.start_scan(scan=scan, initial_scan=initial_scan, polling=polling, random=random)
        return s

    async def ensure_struct(self, dev, server=None, maybe=False):
        """
        Load a device's class's structure definition from any server.

        :param dev: The device whose class to set up
        :param server: Try this server, not all of them
        :param maybe: if set, don't load if ``load_structs`` is set

        """
        if maybe and not self._load_structs:
            return
        cls = type(dev)
        if cls._did_setup:
            return
        if server is not None:
            await cls.setup_struct(server)
        else:
            for s in list(self._servers):
                await cls.setup_struct(s)
                return

    async def get_device(self, id):  # pylint: disable=redefined-builtin
        """
        Return the :class:`anyio_owfs.device.Device` instance for the device
        with this ID. Create it if it doesn't exist (this will trigger a
        `DeviceAdded` event).
        """
        try:
            return self._devices[id]
        except KeyError:
            dev = Device(self, id)
            self._devices[dev.id] = dev
            await self.push_event(DeviceAdded(dev))
            return dev

    async def _add_task(self, val, proc, *args):
        with anyio.CancelScope() as scope:
            val.set(scope)
            try:
                await proc(*args)
            finally:
                try:
                    self._tasks.remove(scope)
                except KeyError:
                    pass

    async def scan_now(self, polling=True):
        """
        Task to scan the whole system.

        :param polling: if False, do not add polling tasks
        """
        async with anyio.create_task_group() as n:
            for s in list(self._servers):
                n.start_soon(partial(s.scan_now, polling=polling))
                #n.spawn(partial(s.scan_now, polling=polling))

    async def add_task(self, proc, *args):
        """
        Add a background task. It is auto-cancelled when the service ends.
        Alternately, this call returns its cancel scope.
        """
        val = ValueEvent()
        self.nursery.start_soon(self._add_task, val, proc, *args)
        #self.nursery.spawn(self._add_task, val, proc, *args)
        scope = await val.get()
        self._tasks.add(scope)
        return scope

    async def push_event(self, event):
        """
        Queue an event.
        """
        if self._event_queue is not None:
            await self._event_queue.send(event)

    async def _del_server(self, s):
        self._servers.remove(s)
        await self.push_event(ServerDeregistered(s))

    async def delete_device(self, dev):
        """
        Drop this device.

        This method is never called automatically; it's the caller's
        responsibility to determine whether a DeviceRemoved event really is
        fatal.
        """
        if dev.bus is not None:
            raise RuntimeError("This device is present on %r" % (dev.bus,))
        del self._devices[dev.id]

        await self.push_event(DeviceDeleted(dev))

    @property
    def devices(self):
        return self._devices.values()

    # context

    async def __aenter__(self):
        return self

    async def __aexit__(self, *tb):
        for s in list(self._servers):
            await s.drop()
        if self._event_queue is not None:
            await self._event_queue.aclose()
        for t in list(self._tasks):
            t.cancel()

    # listen to events

    @property
    def events(self):
        class EventWrapper:
            # pylint: disable=no-self-argument
            _q_r = None

            async def __aenter__(slf):
                assert self._event_queue is None
                self._event_queue, slf._q_r = anyio.create_memory_object_stream(1000)  # bus events
                return slf

            async def __aexit__(slf, *tb):
                if tb[1] is None:
                    try:
                        while True:
                            with anyio.fail_after(0.01, shield=True):
                                evt = await slf._q_r.receive()
                            logger.error("Unprocessed: %s", evt)
                    except TimeoutError:
                        pass
                self._event_queue = None

            def __aiter__(slf):
                return slf

            async def __anext__(slf):
                try:
                    res = await slf._q_r.receive()
                except anyio.EndOfStream:
                    raise StopAsyncIteration  # pylint: disable=raise-missing-from
                return res

        return EventWrapper()


@asynccontextmanager
async def OWFS(**kwargs):
    async with anyio.create_task_group() as n:
        s = Service(n, **kwargs)
        async with s:
            yield s
