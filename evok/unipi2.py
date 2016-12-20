'''
  UniPi2 primitive devices (DI, DO, AI, AO)
------------------------------------------
'''

import struct
import time
import datetime
#import atexit
from math import isnan, floor

from tornado import gen
from tornado.ioloop import IOLoop
import devents
from devices import *
import config
from spiarm import ProxyRegister

class Relay(object):
    pending_id = 0

    def __init__(self, circuit, arm, coil, reg, mask):
        self.circuit = circuit
        self.arm = arm
        self.coil = coil
        self.bitmask = mask
        self.reg = arm.get_proxy_register(reg)
        self.reg.devices.add(self)
        #arm.register_relay(self)

    def full(self):
        return {'dev': 'relay', 'circuit': self.circuit, 'value': self.value, 'pending': self.pending_id != 0}

    def simple(self):
        return {'dev': 'relay', 'circuit': self.circuit, 'value': self.value}

    @property
    def value(self):
        try:
           if self.reg.value & self.bitmask: return 1
        except:
           pass
        return 0

    def get_state(self):
        """ Returns ( status, is_pending )
              current on/off status is taken from last mcp value without reading it from hardware
              is_pending is Boolean
        """
        return (self.value, self.pending_id != 0)

    @gen.coroutine
    def set_state(self, value):
        """ Sets new on/off status. Disable pending timeouts
        """
        if self.pending_id:
            IOLoop.instance().remove_timeout(self.pending_id)
            self.pending_id = None
        #yield self.mcp.set_masked_value(self._mask, value)
        raise gen.Return(1 if self.reg.value & self.bitmask else 0)

    def set(self, value=None, timeout=None):
        """ Sets new on/off status. Disable pending timeouts
        """
        if value is None:
            raise Exception('Value must be specified')
        value = int(value)
        if not (timeout is None):
            timeout = float(timeout)

        #yield self.mcp.set_masked_value(self._mask, value)
        self.arm.write_bit(self.coil, 1 if value else 0)

        if timeout is None:
            return (1 if self.reg.value & self.bitmask else 0)

        def timercallback():
            self.pending_id = None
            self.arm.write_bit(self.coil, 0 if value else 1)

        self.pending_id = IOLoop.instance().add_timeout(
            datetime.timedelta(seconds=float(timeout)), timercallback)
        return (1 if value else 0)
        #return (1 if self.mcp.value & self._mask else 0)


class Input():
    def __init__(self, circuit, arm, reg, mask, regcounter=None, regdebounce=None):
        self.circuit = circuit
        self.arm = arm
        self.bitmask = mask
        self.reg = arm.get_proxy_register(reg)
        self.regcounter1 = None if regcounter is None else arm.get_proxy_register(regcounter) 
        self.regcounter2 = None if regcounter is None else arm.get_proxy_register(regcounter+1) 
        self.regdebounce = None if regdebounce is None else arm.get_proxy_register(regdebounce)
        self.reg.devices.add(self)
        self.regcounter1.devices.add(self)
        self.regcounter2.devices.add(self)
        self.regdebounce.devices.add(self)
        #self.counter_mode = "rising"
        self.counter_mode = "disabled"
        #if counter_mode in ["rising", "falling", "disabled"]:
        #    self.value = 0
        #    self.counter_mode = counter_mode
        #else:
        #    self.counter_mode = 'disabled'
        #    print 'DI%s: counter_mode must be one of: rising, falling or disabled. Counting is disabled!' % self.circuit

    @property
    def debounce(self):
        try: return self.regdebounce.value
        except: pass
        return 0

    @property
    def value(self):
        if self.counter_mode: return self.counter
        try:
           if self.reg & self.bitmask: return 1
        except:
           pass
        return 0

    @property
    def counter(self):
        try:
           r1 = self.regcounter1.value
           r2 = self.regcounter2.value
           return r1 + 0x10000*r2
        except:
           return 0

    def full(self):
        return {'dev': 'input', 'circuit': self.circuit, 'value': self.value,
                'debounce': self.debounce, 'counter_mode':'self.counter_mode',
                'counter': self.counter }

    def simple(self):
        return {'dev': 'input', 'circuit': self.circuit, 'value': self.value }

    def set(self, debounce=None, counter=None):
        if not (debounce is None):
            if not(self._regdebounce is None):
               self.arm.write_regs(self.regdebounce.regnum,debounce)
            #devents.config(self)
        if not (counter is None):
            if not(self._regcounter is None):
               self.arm.write_regs(self.regcounter.regnum,(0,0))
            #devents.status(self)

    def get(self):
        """ Returns ( value, debounce )
              current on/off value is taken from last value without reading it from hardware
        """
        return (self.value, self.debounce)

    def get_value(self):
        """ Returns value
              current on/off value is taken from last value without reading it from hardware
        """
        return self.value


class AnalogOutput():

    def __init__(self, circuit, arm, reg):
        self.circuit = circuit
        self.reg = arm.get_proxy_register(reg)
        self.reg.devices.add(self)
        self.factor = 10.50 / 4095
        self.arm = arm

    @property
    def value(self):
        try:
           return self.reg.value * self.factor  # 3.558*3
        except:
           return 0

    def full(self):
        return {'dev': 'ao', 'circuit': self.circuit, 'value': self.value}

    def simple(self):
        return {'dev': 'ao', 'circuit': self.circuit, 'value': self.value}

    @gen.coroutine
    def set_value(self, value):
        valuei = int(float(value) / self.factor)
        self.arm.write_regs(self.reg.regnum,valuei)
        raise gen.Return(value)

    def set(self, value=None, frequency=None):
        valuei = int(float(value) / self.factor)
        self.arm.write_regs(self.reg.regnum,valuei)
        return value


class AnalogInput():

    def __init__(self, circuit, arm, reg, correction = None):
        self.circuit = circuit
        self.reg = arm.get_proxy_register(reg)
        self.reg.devices.add(self)
        self.arm = arm
        self.correction = 1 if correction is None else correction

    @property
    def value(self):
        try:
           return self.reg.value * 10.65 / 4095 * self.correction
        except:
           return 0

    def full(self):
        return {'dev': 'ai', 'circuit': self.circuit, 'value': self.value}

    def simple(self):
        return {'dev': 'ai', 'circuit': self.circuit, 'value': self.value}


    @property  # docasne!!
    def voltage(self):
        return self.value



