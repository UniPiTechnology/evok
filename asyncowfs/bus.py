"""
Buses.
"""

from random import random
import anyio

from .device import NotADevice, split_id, NoLocationKnown
from .event import BusAdded, BusDeleted, DeviceAlarm
from .error import OWFSReplyError
#!!!!
from asyncio import CancelledError

import logging

logger = logging.getLogger(__name__)


class Bus:
    """Describes one bus."""

    def __init__(self, server, *path):
        self.service = server.service
        self.server = server
        self.path = path

        self._buses = dict()  # subpath => bus
        self._devices = dict()  # id => device
        self._unseen = 0  # didn't find when scanning
        self._tasks = dict()  # polltype => task
        self._intervals = dict()
        self._random = dict()  # varying intervals

    def __repr__(self):
        return "<%s:%s %s>" % (
            self.__class__.__name__,
            self.server,
            "/" + "/".join(self.path),
        )

    def __eq__(self, x):
        x = getattr(x, "path", x)
        return self.path == x

    def __hash__(self):
        return hash(self.path)

    @property
    def devices(self):
        """Iterate over the devices on this bus"""
        try:
            return list(self._devices.values())
        except AttributeError:
            return ()

    @property
    def buses(self):
        """Iterate over the sub.buses on this bus"""
        return list(self._buses.values())

    async def delocate(self):
        """This bus can no longer be found"""
        if self._buses:
            for b in self.buses:
                await b.delocate()
            self._buses = None
        for j in self._tasks.values():
            print("Bus task to cancel:",j)
            j.cancel()
        self._tasks = dict()

        if self._devices:
            for d in self.devices:
                await d.delocate(bus=self)
            self._devices = None
        await self.service.push_event(BusDeleted(self))

    @property
    def all_buses(self):
        yield self
        for b in self.buses:
            yield from b.all_buses

    async def get_bus(self, *path):
        try:
            return self._buses[path]
        except TypeError:
            return None  # bus is gone
        except KeyError:
            bus = Bus(self.server, *self.path, *path)
            self._buses[path] = bus
            await self.service.push_event(BusAdded(bus))
            return bus

    async def _scan_one(self, polling=True):
        """Scan a single bus, plus all buses attached to it"""
        buses = set()
        res = await self.dir()
        old_devs = set(self._devices.keys())
        for d in res:
            try:
                split_id(d)  # only tests for conformity
            except NotADevice as err:
                logger.debug("Not a device: %s", err)
                continue
            dev = await self.service.get_device(d)
            await self.service.ensure_struct(dev, server=self.server, maybe=True)
            if dev.bus is self:
                old_devs.remove(d)
            else:
                await self.add_device(dev)
            dev._unseen = 0
            logger.debug("Found %s/%s", "/".join(self.path), d)
            for b in dev.buses():
                buses.add(b)
                bus = await self.get_bus(*b)
                if bus is not None:
                    buses.update(await bus._scan_one(polling=polling))

        for d in old_devs:
            dev = self._devices[d]
            if True or dev._unseen > 2:
                await dev.delocate(self)
            else:
                dev._unseen += 1
        if polling:
            await self.update_poll()
        return buses

    async def update_poll(self):
        """Start all new polling jobs, terminate old ones"""
        items = set()
        intervals = dict()
        randoms = dict()
        for dev in self.devices:
            for k in dev.polling_items():
                i = dev.polling_interval(k)
                if i is None:
                    continue
                items.add(k)
                if isinstance(i, (tuple, list)):
                    i, j = i
                else:
                    j = None
                oi = intervals.get(k, i)
                intervals[k] = min(oi, i)
                if j is not None:
                    oi = randoms.get(k, j)
                    randoms[k] = min(oi, j)

        old_items = set(self._tasks.keys()) - items
        for x in old_items:
            j = self._tasks.pop(x)
            print("Bus task to cancel:",j)
            j.cancel()

        self._intervals.update(intervals)
        self._random.update(randoms)
        for x in items:
            if x not in self._tasks:
                self._tasks[x] = await self.service.add_task(self._poll, x)

    async def _poll(self, name):
        """Task to run a specific poll in the background"""
        while True:
            i = self._intervals[name]
            j = self._random.get(name, 0)
            if j:
                i *= 1 + (random() - 0.5) / j
            logger.info("Delay %s for %f", name, i)
            await anyio.sleep(i)
            await self.poll(name)

    async def add_device(self, dev):
        await dev.locate(self)
        self._devices[dev.id] = dev

    async def _del_device(self, dev):
        del self._devices[dev.id]

    def dir(self, *subpath):
        return self.server.dir(*self.path, *subpath)

    async def attr_get(self, *attr):
        """Read this attribute"""
        return await self.server.attr_get(*self.path, *attr)

    async def attr_set(self, *attr, value):
        """Write this attribute"""
        if self.server is None:
            raise NoLocationKnown(self)
        return await self.server.attr_set(*self.path, *attr, value=value)

    # ##### Support for polling and alarm handling ##### #

    async def poll(self, name):
        """Run one poll.

        This typically runs via a :meth:`_poll` task, started by :meth:`update_poll`.
        """
        try:
            try:
                p = getattr(self, "poll_" + name)
            except AttributeError:
                for d in self.devices:
                    p = getattr(d, "poll_" + name, None)
                    if p is not None:
                        await p()
            else:
                async with self.server.simul_lock:
                    await p()
        #except CancelledError:
        #    pass
        except OWFSReplyError:
            logger.exception("Poll '%s' on %s", name, self)

    async def poll_alarm(self):
        """Scan the 'alarm' subdirectory"""
        for dev in await self.dir("alarm"):
            dev = await self.service.get_device(dev)
            await self.add_device(dev)
            reasons = await dev.poll_alarm()
            await self.service.push_event(DeviceAlarm(dev, reasons))

    async def _poll_simul(self, name, delay):
        """Write to a single 'simultaneous' entry"""
        logger.debug("Simul %s %r", name, self)
        await self.attr_set("simultaneous", name, value=1)
        await anyio.sleep(delay)
        for dev in self.devices:
            try:
                p = getattr(dev, "poll_" + name)
            except AttributeError:
                pass
            else:
                await p(simul=True)


    def poll_temperature(self):
        """Read all temperature data"""
        return self._poll_simul("temperature", 1.2)

    def poll_voltage(self):
        """Read all voltage data"""
        return self._poll_simul("voltage", 1.2)
