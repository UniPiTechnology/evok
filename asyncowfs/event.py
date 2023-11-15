"""
Events: whatever is happening on the bus
"""

import attr


class Event:
    """Base class for all events"""

    pass


@attr.s
class ServerEvent(Event):
    """Base class for all server-related events"""

    server = attr.ib()


@attr.s
class ServerRegistered(ServerEvent):
    """A new known server appears. The server is not yet connected!"""

    pass


@attr.s
class ServerConnected(ServerEvent):
    """We have connected to a server"""

    pass


@attr.s
class ServerDisconnected(ServerEvent):
    """We have disconnected from a server"""

    pass


@attr.s
class ServerDeregistered(ServerEvent):
    """This server is no longer known"""

    pass


@attr.s
class BusEvent(Event):
    """Base class for all Bus-related events"""

    bus = attr.ib()


@attr.s
class BusAdded(BusEvent):
    """The Bus has been created. Its location is not yet known!"""

    pass


class BusAdded_Path:
    """Not an event. Used for storing the bus path for comparisons in tests."""

    def __init__(self, *path):
        self.path = path

    def __repr__(self):
        return "<%s: %s>" % (self.__class__.__name__, "/".join(self.path))

    def __eq__(self, x):
        if isinstance(x, BusAdded_Path):
            x = x.path
        elif isinstance(x, BusAdded):
            x = x.bus.path
        elif not isinstance(x, (list, tuple)):
            return False
        return self.path == x


@attr.s
class BusDeleted(BusEvent):
    """The Bus has been deleted"""

    pass


@attr.s
class DeviceEvent(Event):
    """Base class for all device-related events"""

    device = attr.ib()


@attr.s
class DeviceAdded(DeviceEvent):
    """The device has been created. Its location is not yet known!"""

    pass


@attr.s
class DeviceDeleted(DeviceEvent):
    """The device has been deleted"""

    pass


@attr.s
class DeviceLocated(DeviceEvent):
    """The device has been found"""

    pass

    @property
    def server(self):
        return self.device.server

    @property
    def path(self):
        return self.device.path

    @property
    def bus(self):
        return self.device.bus


@attr.s
class DeviceNotFound(DeviceEvent):
    """The device's location is no longer known"""

    pass


@attr.s
class DeviceAlarm(DeviceEvent):
    """The device triggered an alarm condition."""

    reasons = attr.ib(factory=dict)
    pass


@attr.s
class DeviceValue(DeviceEvent):
    """The device poll has read a value."""

    attribute = attr.ib()
    value = attr.ib()


@attr.s
class DeviceException(DeviceEvent):
    """The device poll did not work."""

    attribute = attr.ib()
    exception = attr.ib()
