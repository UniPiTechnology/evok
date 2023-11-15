"""
Devices.
"""

import attr
import anyio
from typing import List

from .event import DeviceLocated, DeviceNotFound, DeviceValue, DeviceException
from .error import IsDirError

import logging

logger = logging.getLogger(__name__)

__all__ = ["Device"]


@attr.s
class NoLocationKnown(RuntimeError):
    device = attr.ib()


@attr.s
class NotADevice(RuntimeError):
    id = attr.ib()


dev_classes = dict()


def register(cls):
    dev_classes[cls.family] = cls
    return cls


def split_id(id):  # pylint: disable=redefined-builtin
    try:
        a, b, c = (int(x, 16) for x in id.split("."))
    except ValueError:
        raise NotADevice(id) from None
    return a, b, c


class _Value:
    def __init__(self, path, typ):
        self.path = path
        self.typ = typ

    def __repr__(self):
        return "<%s: %s %s>" % (self.__class__.__name__, self.path, self.typ)


class _RValue(_Value):
    def __init__(self, path, typ):
        super().__init__(path, typ)
        if typ in {"f", "g", "p", "t"}:
            self.conv = float
        elif typ in {"i", "u"}:
            self.conv = int
        elif typ == "y":
            self.conv = lambda x: bool(int(x))
        elif typ == "b":
            self.conv = lambda x: x
        else:
            self.conv = lambda x: x.decode("utf-8")


class _WValue(_Value):
    def __init__(self, path, typ):
        super().__init__(path, typ)
        if typ == "b":
            self.conv = lambda x: x
        elif typ == "y":
            self.conv = lambda x: b"1" if x else b"0"
        else:
            self.conv = lambda x: str(x).encode("utf-8")


class SimpleValue(_RValue):
    """Accessor for direct attribute access"""

    async def __get__(slf, self, cls):  # pylint: disable=no-self-argument
        res = await self.dev.attr_get(*slf.path)
        return slf.conv(res)


class SimpleGetter(_RValue):
    """Accessor for get_* function"""

    def __get__(slf, self, cls):  # pylint: disable=no-self-argument
        async def getter():
            res = await self.dev.attr_get(*slf.path)
            return slf.conv(res)

        return getter


class SimpleSetter(_WValue):
    """Accessor for set_* function"""

    def __get__(slf, self, cls):  # pylint: disable=no-self-argument
        async def setter(val):
            await self.dev.attr_set(*slf.path, value=slf.conv(val))

        return setter


class MultiValue(_RValue):
    """Accessor for direct array access"""

    async def __get__(slf, self, cls):  # pylint: disable=no-self-argument
        p = slf.path[:-1] + (slf.path[-1] + ".ALL",)
        res = await self.dev.attr_get(*p)
        conv = slf.conv
        return [conv(v) for v in res.split(b",")]


class MultiGetter(_RValue):
    """Accessor for array get_* function"""

    def __get__(slf, self, cls):  # pylint: disable=no-self-argument
        async def getter():
            p = slf.path[:-1] + (slf.path[-1] + ".ALL",)
            res = await self.dev.attr_get(*p)
            conv = slf.conv
            return [conv(v) for v in res.split(b",")]

        return getter


class MultiSetter(_WValue):
    """Accessor for array set_* function"""

    def __get__(slf, self, cls):  # pylint: disable=no-self-argument
        async def setter(val):
            conv = slf.conv
            p = slf.path[:-1] + (slf.path[-1] + ".ALL",)
            val = b",".join(conv(v) for v in val)
            await self.dev.attr_set(*p, value=val)

        return setter


class _IdxObj:
    def __init__(self, dev, ary):
        self.dev = dev
        self.ary = ary

    async def __getitem__(self, idx):
        if self.ary.num:
            idx = str(idx)
        else:
            idx = chr(ord("A") + idx)
        p = self.ary.path[:-1] + (self.ary.path[-1] + "." + idx,)
        res = await self.dev.attr_get(*p)
        return self.ary.conv(res)

    async def set(self, idx, val):
        if self.ary.num:
            idx = str(idx)
        else:
            idx = chr(ord("A") + idx)
        p = self.ary.path[:-1] + (self.ary.path[-1] + "." + idx,)
        await self.dev.attr_set(*p, value=val)


class ArrayValue(_RValue):
    """Accessor for direct array element access"""

    def __init__(self, path, typ, num):
        super().__init__(path, typ)
        self.num = num

    def __get__(slf, self, cls):  # pylint: disable=no-self-argument
        return _IdxObj(self.dev, slf)


class ArrayGetter(_RValue):
    """Accessor for array element get_* function"""

    def __init__(self, path, typ, num):
        super().__init__(path, typ)
        self.num = num

    def __get__(slf, self, cls):  # pylint: disable=no-self-argument
        async def getter(idx):
            if slf.num:
                idx = str(idx)
            else:
                idx = chr(ord("A") + idx)
            p = slf.path[:-1] + (slf.path[-1] + "." + idx,)
            res = await self.dev.attr_get(*p)
            return slf.conv(res)

        return getter


class ArraySetter(_WValue):
    """Accessor for array element set_* function"""

    def __init__(self, path, typ, num):
        super().__init__(path, typ)
        self.num = num

    def __get__(slf, self, cls):  # pylint: disable=no-self-argument
        async def setter(idx, val):
            if slf.num:
                idx = str(idx)
            else:
                idx = chr(ord("A") + idx)
            p = slf.path[:-1] + (slf.path[-1] + "." + idx,)
            await self.dev.attr_set(*p, value=slf.conv(val))

        return setter


class SubDir:
    _subdirs = set()
    dev = None  # needs to be filled by subclass

    def __getattr__(self, name):
        if name not in self._subdirs:
            return super().__getattribute__(name)
        c = getattr(self, "_cls_" + name)(self)
        c.dev = self.dev
        return c


async def setup_accessors(server, cls, typ, *subdir):
    cls.fields = {}
    for d in await server.dir("structure", typ, *subdir):
        dd = subdir + (d,)
        try:
            v = await server.attr_get("structure", typ, *dd)
        except IsDirError:

            t = typ

            class SubPath(SubDir):
                typ = t
                subdir = dd

                def __init__(self, base):
                    self.base = base

                def __repr__(self):
                    return "<%s %s %s>" % (
                        self.__class__.__name__,
                        self.base,
                        self.subdir,
                    )

                def __get__(self, obj, cls):
                    if obj is None:
                        return cls
                    try:
                        return getattr(obj, "_" + self.dd[-1])
                    except AttributeError:
                        c = getattr(cls, self.__name__)()
                        setattr(obj, "_" + self.dd[-1], c)
                        c.dev = obj.dev
                        return c

            SubPath.__name__ = "_cls_" + d
            setattr(cls, "_cls_" + d, SubPath)
            cls._subdirs.add(d)
            await setup_accessors(server, SubPath, typ, *dd)

        else:
            v = v.decode("utf-8").split(",")
            try:
                v[1] = int(v[1])
                v[2] = int(v[2])
                v[4] = int(v[4])
            except ValueError:
                raise ValueError("broken setup vector", (typ, dd), v) from None
            if v[1] == 0:
                if d.endswith(".0"):
                    num = True
                elif d.endswith(".A"):
                    num = False
                else:
                    num = None
                v[1] = num
                cls.fields[d] = v

                if num is None:
                    if v[3] in {"ro", "rw"}:
                        if hasattr(cls, d):
                            logger.debug("%s: not overwriting %s", cls, d)
                        else:
                            setattr(cls, d, SimpleValue(dd, v[0]))
                        setattr(cls, "get_" + d, SimpleGetter(dd, v[0]))
                    if v[3] in {"wo", "rw"}:
                        setattr(cls, "set_" + d, SimpleSetter(dd, v[0]))
                else:
                    d = d[:-2]
                    dd = subdir + (d,)
                    if v[3] in {"ro", "rw"}:
                        if hasattr(cls, d):
                            logger.debug("%s: not overwriting %s", cls, d)
                        else:
                            setattr(cls, d, ArrayValue(dd, v[0], num))
                        setattr(cls, "get_" + d, ArrayGetter(dd, v[0], num))
                    if v[3] in {"wo", "rw"}:
                        setattr(cls, "set_" + d, ArraySetter(dd, v[0], num))

                    if v[3] in {"ro", "rw"}:
                        if hasattr(cls, d + "_all"):
                            logger.debug("%s: not overwriting %s", cls, d + "_all")
                        else:
                            setattr(cls, d + "_all", MultiValue(dd, v[0]))
                        setattr(cls, "get_" + d + "_all", MultiGetter(dd, v[0]))
                    if v[3] in {"wo", "rw"}:
                        setattr(cls, "set_" + d + "_all", MultiSetter(dd, v[0]))


class Device(SubDir):
    """Base class for devices.

    A device may or may not have a known location.

    Whenever a device is located, poll activity is auto-started.
    """

    _did_setup = False
    _poll: dict = None
    bus = None
    _events = None
    _wait_bus = None

    def __new__(cls, service, id):  # pylint: disable=redefined-builtin
        family_id, code, chksum = split_id(id)

        cls = dev_classes.get(family_id)  # pylint: disable=self-cls-assignment
        if cls is None:

            class cls(Device):  # pylint: disable=function-redefined
                family = family_id

            cls.__name__ = "Device_%02x" % (family_id,)
            dev_classes[family_id] = cls

        self = object.__new__(cls)

        self.id = id.upper()
        self.family = family_id
        self.code = code
        self.chksum = chksum

        self.service = service
        self.bus = None

        self._unseen = 0
        self._events = []
        self._wait_bus = anyio.Event()
        self._poll = {}  # name > poll task scopes
        self._intervals = {}
        self._task_lock = anyio.Lock()

        return self

    def __init__(self, service, id):  # pylint: disable=redefined-builtin,unused-argument
        logger.debug("NewDev %s", id)

    @property
    def dev(self):
        return self

    def queue_event(self, evt):
        """Remember this event. Used if an event arrives when the device
        hasn't yet been set up by high-level code
        """
        self._events.append(evt)

    @property
    def queued_events(self):
        """Return queued events. Shall be called exactly once."""
        e, self._events = self._events, None
        if e is None:
            raise RuntimeError("You cannot call `queued_events` " "more than once")
        return iter(e)

    @classmethod
    async def setup_struct(cls, server):
        """Read the device's structural data from OWFS
        and add methods to access the fields"""

        if cls._did_setup is not False:
            return
        cls._did_setup = None

        try:
            fc = "%02X" % (cls.family)
            await setup_accessors(server, cls, fc)

        except BaseException:
            cls._did_setup = False
            raise
        else:
            cls._did_setup = True

    def __eq__(self, x):
        x = getattr(x, "id", x)
        return self.id == x

    def __hash__(self):
        return hash(self.id)

    def __repr__(self):
        return "<%s:%s @ %s>" % (self.__class__.__name__, self.id, self.bus)

    def buses(self):
        return set()

    async def locate(self, bus):
        """The device has been seen here."""
        if self.bus is bus:
            return
        self.bus = bus
        self._wait_bus.set()
        await self.service.push_event(DeviceLocated(self))
        for typ, val in self._intervals.items():
            await self._set_poll_task(typ, val)

    async def wait_bus(self):
        await self._wait_bus.wait()

    async def delocate(self, bus):
        """The device is no longer located here."""
        if self.bus is bus:
            self._wait_bus = anyio.Event()
            await self._delocate()

    async def _delocate(self):
        await self.bus._del_device(self)
        self.bus = None
        for t in self._poll.values():
            print("Device poll task to cancel", t)
            t.cancel()
        self._poll = {}
        await self.service.push_event(DeviceNotFound(self))

    async def attr_get(self, *attrs: List[str]):
        """Read this attribute (ignoring device struct)"""
        if self.bus is None:
            raise NoLocationKnown(self)
        return await self.bus.attr_get(self.id, *attrs)

    async def attr_set(self, *attrs: List[str], value):
        """Write this attribute (ignoring device struct)"""
        if self.bus is None:
            raise NoLocationKnown(self)
        return await self.bus.attr_set(self.id, *attrs, value=value)

    async def get(self, *attrs):
        """Read this attribute (following device struct)"""
        dev = self
        for k in attrs:
            if isinstance(k, int):
                dev = dev[k]
            else:
                dev = getattr(dev, k)
        #if type(dev) in (int, str): return dev
        return await dev

    async def set(self, *attrs, value):
        """Write this attribute (following device struct)"""
        dev = self
        for k in attrs[:-1]:
            if isinstance(k, int):
                dev = dev[k]
            else:
                dev = getattr(dev, k)
        if isinstance(dev, _IdxObj):
            await dev.set(attrs[-1], value)
        else:
            await getattr(dev, "set_" + attrs[-1])(value)

    def polling_items(self):
        """Enumerate poll variants supported by this device.

        This is a generator. If you override, call::

            yield from super().polling_items()

        See the associated ``poll_<name>`` methods on
        :class:`anyio_owfs.bus.Bus` for details.

        Special return values:

        * "alarm": you need to implement ``.stop_alarm``
        """
        if False:  # pylint: disable=using-constant-test
            yield None

    def polling_interval(self, typ: str):
        """Return the interval WRT how often to poll for this type.

        The default implementation looks up the "interval_<typ>" attribute
        or returns ``None`` if that doesn't exist.
        """
        try:
            return self._intervals[typ]
        except KeyError:
            return getattr(self, "interval_" + typ, None)

    async def set_polling_interval(self, typ: str, value: float = 0):
        if isinstance(typ, str):
            styp = typ
        else:
            styp = "/".join(str(x) for x in typ)
        if value > 0:
            self._intervals[styp] = value
        else:
            self._intervals.pop(styp, None)

        if self.bus is not None:
            if hasattr(self, "poll_" + styp):
                await self.bus.update_poll()
            else:
                await self._set_poll_task(styp, value)

    async def _set_poll_task(self, typ, value):
        async with self._task_lock:
            try:
                task = self._poll.pop(typ)
            except KeyError:
                pass
            else:
                task.cancel()
            if not value:
                return

            *p, n = typ.split("/") if isinstance(typ, str) else typ
            s = self
            for pp in p:
                if isinstance(pp, int):
                    s = s[pp]
                else:
                    s = getattr(s, pp)
            if isinstance(n, int) or hasattr(s, "get_" + n):
                self._poll[typ] = await self.service.add_task(self._poll_task, s, n, typ, value)

            else:
                raise RuntimeError("%r: No poll for %s" % (self, typ))

    async def _poll_task(self, s, n, typ, value):
        await anyio.sleep(value / 5)
        while True:
            try:
                if isinstance(n, int):
                    v = await s[n]
                else:
                    v = await getattr(s, n)
            except Exception as exc:
                #logger.exception("Reader at %s %s", self, typ)
                await self.service.push_event(DeviceException(self, typ, exc))
            else:
                await self.service.push_event(DeviceValue(self, typ, v))
            await anyio.sleep(value)

    async def poll_alarm(self):
        """Tells the device not to trigger an alarm any more.

        You *need* to override this if your device can trigger an alarm
        condition. Also, this method *must* disable the alarm; your
        application can re-enable it later, when processing the
        :class:`anyio_owfs.event.DeviceAlarm` event.
        """
        pass  # pylint
        raise NotImplementedError(
            "<%s> (%02x) needs 'poll_alarm'" % (self.__class__.__name__, self.family)
        )


@register
class SwitchDevice(Device):
    family = 0x1F

    def buses(self):
        """Return a list of the connected buses.
        'main' should be processed first.
        """
        b = []
        b.append((self.id, "main"))
        b.append((self.id, "aux"))
        return b

    async def poll_alarm(self):
        """Clear alarm"""
        raise RuntimeError("TODO")
        # res = await self.get_event_all()
        # await self.set_clearalarm(1)


@register
class TemperatureDevice(Device):
    family = 0x10

    interval_temperature = None
    alarm_temperature = None

    async def poll_alarm(self):
        """Turn off alarm condition by adapting the temperature bounds"""
        self.alarm_temperature = t = await self.latesttemp
        reasons = {"temp": t}

        t_h = await self.temphigh
        if t > t_h:
            await self.set_temphigh(int(t + 2))
            reasons["high"] = t_h
        t_l = await self.templow
        if t < t_l:
            await self.set_templow(int(t - 1))
            reasons["low"] = t_l
        return reasons

    def polling_items(self):
        yield from super().polling_items()
        yield "temperature"
        yield "alarm"

    async def poll_temperature(self, simul=False):
        # Bug workaround
        try:
            t = await (self.latesttemp if simul and len(self.bus.path)<=1 else self.temperature)
            if t == 85:
                logger.error("TEMP: got 85 on %r", self)
                return
        except Exception as exc:
            #logger.exception("Reader at %s temperature", self)
            await self.service.push_event(DeviceException(self, "temperature", exc))
        else:
            await self.service.push_event(DeviceValue(self, "temperature", t))

        ## Bug workaround
        #t = await (self.latesttemp if simul and len(self.bus.path)<=1 else self.temperature)
        #if t == 85:
        #    logger.error("TEMP: got 85 on %r", self)
        #    return
        #await self.service.push_event(DeviceValue(self, "temperature", t))


#   @property
#   def temperature(self):
#       return self.latesttemp


@register
class TemperatureBDevice(TemperatureDevice):
    family = 0x28


@register
class VoltageDevice(Device):
    family = 0x20

    interval_voltage = None
    alarm_voltage = None

    async def poll_alarm(self):
        """Turn off alarm condition by adapting the voltage bounds"""
        reasons = {}
        v = await self.voltage_all
        ah = await self.alarm.high_all
        al = await self.alarm.low_all
        power = await self.set_alarm.unset
        if power:
            reasons["power_on"] = True
            await self.set_alarm.set_unset(0)
        if any(ah):
            vh = await self.set_alarm.set_high_all
            for i in range(4):
                if not ah[i]:
                    continue
                reasons["high_" + str(i)] = vh[i]
                await self.set_alarm.set_high(i, 0)
        if any(al):
            vl = await self.set_alarm.set_low_all
            for i in range(4):
                if not al[i]:
                    continue
                reasons["low_" + str(i)] = vl[i]
                await self.set_alarm.set_low(i, 0)
        for i in range(4):
            reasons["volt_" + str(i)] = v[i]

        return reasons

    def polling_items(self):
        yield from super().polling_items()
        yield "voltage"
        yield "alarm"

    async def poll_voltage(self, simul=False):
        try:
            v = await self.volt_all
        except Exception as exc:
            #logger.exception("Reader at %s temperature", self)
            await self.service.push_event(DeviceException(self, "volt_all", exc))
        else:
            await self.service.push_event(DeviceValue(self, "volt_all", v))


@register
class PIODevice(Device):
    family = 0x05
    # dumb slave, no special handling
