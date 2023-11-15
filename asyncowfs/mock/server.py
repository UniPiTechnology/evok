import os
import trio
import anyio
from asyncowfs import OWFS
from asyncowfs.protocol import MessageProtocol, OWMsg
from asyncowfs.error import OWFSReplyError, NoEntryError, IsDirError

try:
    from contextlib import asynccontextmanager
except ImportError:
    from async_generator import asynccontextmanager
from functools import partial

import logging

logger = logging.getLogger(__name__)

# pylint: disable=raise-missing-from


def _chk(v):
    if v is None:
        return False
    v[0] += 1
    if v[0] >= len(v):
        v[0] = 1
    return v[v[0]]


async def _schk(v):
    if v is None:
        return
    v[0] += 1
    if v[0] >= len(v):
        v[0] = 1
    if v[v[0]] > 0:
        logger.debug("Slow reply %s", v[v[0]])
    await trio.sleep(v[v[0]])


class FakeMaster:
    def __init__(self, stream):
        self.stream = stream


async def some_server(tree, options, socket):
    """
    This is a fake 1wire server task.

    ``tree``: the 1wire hierarchy to serve::

        {
            "bus.0": {
                "10.345678.90": {
                    "latesttemp": "12.5",
                    "temperature": "12.5",
                    "templow": "10",
                    "temphigh": "20",
                }
            },
            "structure": asyncowfs.mock.structs,
        }


    ``options``: an object with optional ``busy_every``, ``close_every``
    and/or ``slow_every`` attributes. These must be an array with an offset
    and a list of flags. Each call cycles through the array and,
    respectively, reports to be busy, closes the connection, or delays its
    answer. This allows you to test various interesting bus conditions.
    See the ``tests/test_example.pytest_basic_structs`` test for example
    use.

    ``socket``: the connection to the client.
    """
    rdr = MessageProtocol(FakeMaster(socket), is_server=True)
    logger.debug("START Server")

    each_busy = options.get("busy_every", None)
    each_close = options.get("close_every", None)
    each_slow = options.get("slow_every", None)
    try:
        if _chk(each_close):
            return
        async for command, format_flags, data, offset in rdr:
            print("READ", command, format_flags, data, offset)
            try:
                if _chk(each_busy):
                    await rdr.write(0, format_flags, 0, data=None)
                await _schk(each_slow)
                if _chk(each_close):
                    return
                if command == OWMsg.nop:
                    await rdr.write(0, format_flags, 0)
                elif command == OWMsg.dirall:
                    data = data.rstrip(b"\0")
                    subtree = tree
                    path = []
                    for k in data.split(b"/"):
                        if k == b"":
                            continue
                        path.append(k)
                        k = k.decode("utf-8")
                        try:
                            subtree = subtree[k]
                        except KeyError:
                            raise NoEntryError(command, data)
                    res = []
                    for k in sorted(subtree.keys()):
                        k = k.encode("utf-8")
                        res.append(k)
                    if path:
                        path = b"/" + b"/".join(path) + b"/"
                    else:
                        path = b"/"
                    data = b",".join(path + k for k in res)
                    await rdr.write(0, format_flags, len(data), data + b"\0")
                elif command == OWMsg.read:
                    data = data.rstrip(b"\0")
                    res = tree
                    for k in data.split(b"/"):
                        if k == b"":
                            continue
                        k = k.decode("utf-8")
                        try:
                            res = res[k]
                        except KeyError:
                            raise NoEntryError(command, data)
                    if isinstance(res, dict):
                        raise IsDirError(command, data)
                    if not isinstance(res, bytes):
                        res = str(res).encode("utf-8")
                    await rdr.write(0, format_flags, len(res), res + b"\0")
                elif command == OWMsg.write:
                    val = data[-offset:].decode("utf-8")
                    data = data[:-offset]
                    data = data.rstrip(b"\0")
                    res = tree
                    last = None
                    for k in data.split(b"/"):
                        if k == b"":
                            continue
                        if last is not None:
                            try:
                                res = res[last]
                            except KeyError:
                                raise NoEntryError(command, data)
                        last = k.decode("utf-8")
                    assert last is not None
                    if last not in res:
                        raise NoEntryError(command, data)
                    res[last] = val
                    await rdr.write(0, format_flags, 0)
                else:
                    raise RuntimeError(
                        "Unknown command: %d %x %s %d"
                        % (command, format_flags, repr(data), offset)
                    )
            except OWFSReplyError as err:
                logger.info("Error: %s", err)
                await rdr.write(
                    -err.err, format_flags  # pylint: disable=invalid-unary-operand-type
                )

    except anyio.ClosedResourceError:
        pass
    finally:
        await socket.aclose()
        logger.debug("END Server")


class EventChecker:
    """
    This class is used to verify that whatever happens on the bus is what
    you'd expect to happen.

    Useful mainly as regression test, to ensure that new versions of your
    code actually do the requests they're supposed to do / don't generate
    more bus traffic.
    """

    pos: int = None

    def __init__(self, events=[]):  # pylint: disable=dangerous-default-value
        self.events = events[:]

    def add(self, event):
        self.events.push(event)

    async def __call__(self, ow, evt=None):
        self.pos = 0
        try:
            async with ow.events as ev:
                if evt is not None:
                    evt.set()
                async for e in ev:
                    if e is None:
                        break
                    logger.debug("Event %s", e)
                    self.check_next(e)
        except RuntimeError:
            raise
        else:
            self.check_last()
        # don't check on BaseException =Cancellation

    def check_next(self, e):
        try:
            t = self.events[self.pos]
        except IndexError:
            raise RuntimeError("Unexpected event %s" % (e,))
        self.pos += 1
        if isinstance(t, type) and isinstance(e, t):
            pass
        elif not (t == e):
            raise RuntimeError("Wrong event: want %s but has %s" % (t, e))
            # logger.error("Wrong event: want %s but has %s", t, e)

    def check_last(self):
        logger.debug("Event END")
        if self.pos != len(self.events):
            raise RuntimeError("Superfluous event #%d: %s" % (self.pos, self.events[self.pos]))


@asynccontextmanager
async def server(  # pylint: disable=dangerous-default-value  # intentional
    tree={}, options={}, events=None, polling=False, scan=None, initial_scan=True, **kw
):
    """
    This is a mock 1wire server+client.

    The context manager returns the client.

    ``tree`` and ``opotions`` are used as in `some_server`, ``polling``,
    ``scan`` and ``initial_scan`` are used to set up the client, other
    keyword arguments are forwarded to the client constructor.
    """
    PORT = (os.getpid() % 9999) + 40000
    async with OWFS(**kw) as ow:
        async with anyio.create_task_group() as tg:
            s = None
            try:
                listener = await anyio.create_tcp_listener(
                    local_host="127.0.0.1", local_port=PORT, reuse_port=True
                )

                async def may_close():
                    try:
                        await listener.serve(partial(some_server, tree, options))
                    except (anyio.ClosedResourceError, anyio.BrokenResourceError):
                        pass
                    except trio.MultiError as exc:
                        exc = exc.filter(lambda x:  None if isinstance(x,trio.Cancelled) else x,exc)
                        if not isinstance(exc, (anyio.ClosedResourceError, anyio.BrokenResourceError)):
                            raise
                    except BaseException as exc:
                        import pdb;pdb.set_trace()
                        raise

                if events is not None:
                    evt = anyio.Event()
                    tg.spawn(events, ow, evt)
                    await evt.wait()
                addr = listener.extra(anyio.abc.SocketAttribute.raw_socket).getsockname()
                tg.spawn(may_close)

                s = await ow.add_server(
                    *addr, polling=polling, scan=scan, initial_scan=initial_scan
                )
                ow.test_server = s
                yield ow
            finally:
                ow.test_server = None
                await listener.aclose()
                with anyio.CancelScope(shield=True):
                    if s is not None:
                        await s.drop()
                    await ow.push_event(None)
                    await anyio.sleep(0.1)
                tg.cancel_scope.cancel()
