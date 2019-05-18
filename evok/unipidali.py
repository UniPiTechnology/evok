#
# Author: Miroslav Ondra  <ondra@faster.cz>
# Based on tridonic.py from https://github.com/sde1000/python-dali 
# Author: Stephen Early
# Author-email: steve@assorted.org.uk
# License: LGPL3+
#

from __future__ import print_function
from __future__ import unicode_literals
from dali.command import from_frame
from dali.driver.base import AsyncDALIDriver
from dali.driver.base import DALIDriver
from dali.driver.base import SyncDALIDriver
from dali.frame import BackwardFrame
from dali.frame import BackwardFrameError
from dali.frame import ForwardFrame
import logging
import struct

from remotearm import RemoteArm
from time import sleep

DA_OPT_TWICE = 0x8
DA_OPT_17BIT = 0x4


# debug logging related
DRIVER_CONSTRUCT = 0x0
DRIVER_EXTRACT = 0x1
_exco_str = {
    DRIVER_CONSTRUCT: 'CONSTRUCT',
    DRIVER_EXTRACT: 'EXTRACT',
}


def _log_frame(logger, exco, opt, ad, cm, st):
    msg = (
        '{}\n'
        '    Type: {}\n'
        '    Address: {}\n'
        '    Command: {}\n'
    )
    logger.info(msg.format(
        _exco_str[exco],
        #_dr_str.get(dr, 'UNKNOWN'),
        #_ty_str.get(ty, 'UNKNOWN'),
        hex(opt),
        hex(ad),
        hex(cm),
    ))


class DALINoResponse(object):

    def __repr__(self):
        return 'NO_RESPONSE'

    __str__ = __repr__


DALI_NO_RESPONSE = DALINoResponse()


class UnipiDALIDriver(DALIDriver):
    """``DALIDriver`` implementation for UniPi DALI ModBus device.
    """
    # debug logging
    debug = False
    logger = logging.getLogger('UnipiDALIDriver')
    # next sequence number
    _next_sn = 1

    def construct(self, command):
        """Data expected by DALI Modbus 
             Reg_1 - 16bit - length, ...
             Reg_2 - 16bit - address,command
        """
        frame = command.frame
        if len(frame) == 16:
            opt = 0x2
            if command.is_config: opt |= DA_OPT_TWICE
            ad, cm1 = frame.as_byte_sequence
            reg2 = (ad << 8) | cm1
            reg1 = opt << 8
        elif len(frame) == 24:
            opt = 0x3
            if command.is_config: opt |= DA_OPT_TWICE
            ad, cm1, cm2 = frame.as_byte_sequence
            reg1 = (opt << 8) | ad
            reg2 = (cm1 << 8) | cm2
        else:
            raise ValueError('Unknown frame length: {}'.format(len(frame)))

        if self.debug:
            _log_frame(
                self.logger, DRIVER_CONSTRUCT, opt, ad, cm1,0)
        return (reg1, reg2)


    def extract(self, data):
        """ ----- """
        if data[0] == 0x100:
            return BackwardFrame(data[1])
        if data[0] == 0x200:
            return ForwardFrame(16, [data[1] >> 8, data[1] & 0xff])
        else:
            return DALI_NO_RESPONSE
        #msg = 'Unknown direction received: {}'.format(hex(dr))
        #self.logger.warning(msg)

    def _get_sn(self):
        """Get next sequence number."""
        sn = self._next_sn
        if sn > 255:
            sn = self._next_sn = 1
        else:
            self._next_sn += 1
        return sn


class SyncUnipiDALIDriver(UnipiDALIDriver, SyncDALIDriver):
    """Synchronous implementation for UnipiDali    """

    def __init__(self, bus=0, unit=2):
        self.backend = RemoteArm('127.0.0.1', unit=unit)
        self.bus = bus
        self._sendreg = 13+ 2*bus
        self._recvreg = 1 + 3*bus


    def send(self, command, timeout=None):
        registers = self.construct(command)
        self.backend.write_regs(self._sendreg, registers)
        if command.is_config: # ToDo in firmware
            sleep(0.02)
            self.backend.write_regs(self._sendreg, registers)
        counter1, = self.backend.read_regs(self._recvreg,1)
        needsResponse = command.response is not None
        frame = None
        if needsResponse: # wait max 6*10ms
            for i in range(6): 
                sleep(0.01)
                counter2, reg1, reg2 = self.backend.read_regs(self._recvreg,3)
                if (counter1 != counter2):
                    #print ("%d %04x %04x" % (i, reg1, reg2))
                    frame = self.extract((reg1, reg2))
                    if isinstance(frame, BackwardFrame):
                        if command.response:
                            return command.response(frame)
                    return frame
        return DALI_NO_RESPONSE



def _test_sync(logger, command):
    print('Test sync driver')
    driver = SyncUnipiDALIDriver()
    driver.logger = logger
    driver.debug = True

    print('Response: {}'.format(driver.send(command)))
    driver.backend.close()




if __name__ == '__main__':
    """Usage: python unipidali.py address value
    """
    from dali.gear.general import DAPC, QueryStatus, QueryDeviceType, QueryActualLevel, QueryLightSourceType
    from dali.gear.general import RecallMaxLevel, RecallMinLevel, Off
    from dali.address import Short
    import signal
    import sys
    import time

    # setup console logging
    logger = logging.getLogger('UnipiDALIDriver')
    #logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    logger.addHandler(handler)

    # sync interface
    addr = Short(int(sys.argv[1]))
    # command to send
    #command = DAPC(addr, int(sys.argv[2]))
    #_test_sync(logger, command)
    command = QueryStatus(addr)
    _test_sync(logger, command)
    command = QueryDeviceType(addr)
    _test_sync(logger, command)
    #command = QueryLightSourceType(addr)
    #_test_sync(logger, command)
    command = QueryActualLevel(addr)
    _test_sync(logger, command)
    #command = RecallMaxLevel(addr)
    #command = RecallMinLevel(addr)
    command = Off(addr)
    _test_sync(logger, command)
