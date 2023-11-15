# for message type classification see
# http://owfs.org/index.php?page=owserver-message-types
# and 'enum msg_classification' from module/owlib/src/include/ow_message.h

import attr

import logging

logger = logging.getLogger(__name__)


class OWFSReplyError(Exception):
    err: int = None


@attr.s(eq=False)
class GenericOWFSReplyError(OWFSReplyError):
    err = attr.ib()
    req = attr.ib()
    server = attr.ib()


_errors = {}


@attr.s(eq=False)
class OWFSReplyError_(OWFSReplyError):
    req = attr.ib()
    server = attr.ib()


def _register(cls):
    _errors[cls.err] = cls
    return cls


@_register
@attr.s(eq=False)
class AttrPermissionError(OWFSReplyError_):
    err = 13


@_register
@attr.s(eq=False)
class InUseError(OWFSReplyError_):
    err = 98


@_register
@attr.s(eq=False)
class NotAvailableError(OWFSReplyError_):
    err = 99


@_register
@attr.s(eq=False)
class TryAgainError(OWFSReplyError_):
    err = 11


@_register
@attr.s(eq=False)
class BadFSError(OWFSReplyError_):
    err = 9


@_register
@attr.s(eq=False)
class BadMsgError(OWFSReplyError_):
    err = 74


@_register
@attr.s(eq=False)
class BusyError(OWFSReplyError_):
    err = 16


@_register
@attr.s(eq=False)
class ConnAbortedError(OWFSReplyError_):
    err = 103


@_register
@attr.s(eq=False)
class FaultError(OWFSReplyError_):
    err = 14


@_register
@attr.s(eq=False)
class CallInterruptedError(OWFSReplyError_):
    err = 4


@_register
@attr.s(eq=False)
class InvalidDataError(OWFSReplyError_):
    err = 22


@_register
@attr.s(eq=False)
class BusIOError(OWFSReplyError_):
    err = 5


@_register
@attr.s(eq=False)
class IsDirError(OWFSReplyError_):
    err = 21


@_register
@attr.s(eq=False)
class LoopError(OWFSReplyError_):
    err = 40


@_register
@attr.s(eq=False)
class MsgSizeError(OWFSReplyError_):
    err = 90


@_register
@attr.s(eq=False)
class NameTooLongError(OWFSReplyError_):
    err = 36


@_register
@attr.s(eq=False)
class NoBufsError(OWFSReplyError_):
    err = 105


@_register
@attr.s(eq=False)
class NoDeviceError(OWFSReplyError_):
    err = 19


@_register
@attr.s(eq=False)
class NoEntryError(OWFSReplyError_):
    err = 2


@_register
@attr.s(eq=False)
class NoFreeMemoryError(OWFSReplyError_):
    err = 12


@_register
@attr.s(eq=False)
class NoMessageError(OWFSReplyError_):
    err = 42


@_register
@attr.s(eq=False)
class NoDirectoryError(OWFSReplyError_):
    err = 20


@_register
@attr.s(eq=False)
class NotSupportedError(OWFSReplyError_):
    err = 95


@_register
@attr.s(eq=False)
class RangeError(OWFSReplyError_):
    err = 34


@_register
@attr.s(eq=False)
class ReadOnlyError(OWFSReplyError_):
    err = 30


@_register
@attr.s(eq=False)
class InputPathTooLongError(OWFSReplyError_):
    err = 26


@_register
@attr.s(eq=False)
class BadPathSyntaxError(OWFSReplyError_):
    err = 27


@_register
@attr.s(eq=False)
class TextInPathError(OWFSReplyError_):
    err = 77


@_register
@attr.s(eq=False)
class BadCRC8Error(OWFSReplyError_):
    err = 28


@_register
@attr.s(eq=False)
class UnknownNameError(OWFSReplyError_):
    err = 29


@_register
@attr.s(eq=False)
class AliasTooLongError(OWFSReplyError_):
    err = 31


@_register
@attr.s(eq=False)
class UnknownPropertyError(OWFSReplyError_):
    err = 32


@_register
@attr.s(eq=False)
class NotAnArrayError(OWFSReplyError_):
    err = 33


@_register
@attr.s(eq=False)
class IsAnArrayError(OWFSReplyError_):
    err = 35


@_register
@attr.s(eq=False)
class NotBitfieldError(OWFSReplyError_):
    err = 37


@_register
@attr.s(eq=False)
class IndexTooLargeError(OWFSReplyError_):
    err = 38


@_register
@attr.s(eq=False)
class NoSubpathError(OWFSReplyError_):
    err = 39


@_register
@attr.s(eq=False)
class DeviceNotFoundError(OWFSReplyError_):
    err = 41


@_register
@attr.s(eq=False)
class DeviceError(OWFSReplyError_):
    err = 43


@_register
@attr.s(eq=False)
class BusShortError(OWFSReplyError_):
    err = 44


@_register
@attr.s(eq=False)
class NoSuchBusError(OWFSReplyError_):
    err = 45


@_register
@attr.s(eq=False)
class BusNotAppropriateError(OWFSReplyError_):
    err = 46


@_register
@attr.s(eq=False)
class BusNotRespondingError(OWFSReplyError_):
    err = 47


@_register
@attr.s(eq=False)
class BusResetError(OWFSReplyError_):
    err = 48


@_register
@attr.s(eq=False)
class BusClosedError(OWFSReplyError_):
    err = 49


@_register
@attr.s(eq=False)
class BusNotOpenedError(OWFSReplyError_):
    err = 50


@_register
@attr.s(eq=False)
class BusCommunicationError(OWFSReplyError_):
    err = 51


@_register
@attr.s(eq=False)
class BusTimeoutError(OWFSReplyError_):
    err = 52


@_register
@attr.s(eq=False)
class TelnetError(OWFSReplyError_):
    err = 53


@_register
@attr.s(eq=False)
class TCPError(OWFSReplyError_):
    err = 54


@_register
@attr.s(eq=False)
class BusIsLocalError(OWFSReplyError_):
    err = 55


@_register
@attr.s(eq=False)
class BusIsRemoteError(OWFSReplyError_):
    err = 56


@_register
@attr.s(eq=False)
class ReadTooLargeError(OWFSReplyError_):
    err = 57


@_register
@attr.s(eq=False)
class DataCommunicationError(OWFSReplyError_):
    err = 58


@_register
@attr.s(eq=False)
class NotRPropertyError(OWFSReplyError_):
    err = 59


@_register
@attr.s(eq=False)
class NotReadablePropertyError(OWFSReplyError_):
    err = 60


@_register
@attr.s(eq=False)
class DataTooLargeError(OWFSReplyError_):
    err = 61


@_register
@attr.s(eq=False)
class DataTooSmallError(OWFSReplyError_):
    err = 62


@_register
@attr.s(eq=False)
class DataFormatError(OWFSReplyError_):
    err = 63


@_register
@attr.s(eq=False)
class NotWPropertyError(OWFSReplyError_):
    err = 64


@_register
@attr.s(eq=False)
class NotWritablePropertyError(OWFSReplyError_):
    err = 65


@_register
@attr.s(eq=False)
class ReadOnlyModeError(OWFSReplyError_):
    err = 66


@_register
@attr.s(eq=False)
class DataCommError(OWFSReplyError_):
    err = 67


@_register
@attr.s(eq=False)
class OutputPathTooLongError(OWFSReplyError_):
    err = 68


@_register
@attr.s(eq=False)
class DevNotADirectoryError(OWFSReplyError_):
    err = 69


@_register
@attr.s(eq=False)
class NotADeviceError(OWFSReplyError_):
    err = 70


@_register
@attr.s(eq=False)
class UnknownQueryError(OWFSReplyError_):
    err = 71


@_register
@attr.s(eq=False)
class SocketError(OWFSReplyError_):
    err = 72


@_register
@attr.s(eq=False)
class DeviceTimeoutError(OWFSReplyError_):
    err = 73


@_register
@attr.s(eq=False)
class VersionError(OWFSReplyError_):
    err = 75


@_register
@attr.s(eq=False)
class PacketSizeError(OWFSReplyError_):
    err = 76


@_register
@attr.s(eq=False)
class UnexpectedNullError(OWFSReplyError_):
    err = 78


@_register
@attr.s(eq=False)
class NoMemoryError(OWFSReplyError_):
    err = 79
