'''
  Neuron primitive devices (DI, DO, AI, AO)
------------------------------------------
'''

import struct
import time
import datetime
# import atexit
from math import isnan, floor

from tornado import gen
from tornado.ioloop import IOLoop

from modbusclient_tornado import ModbusClientProtocol, StartClient
from pymodbus.pdu import ExceptionResponse

import devents
from devices import *
import config
#from spiarm import ProxyRegister

from log import *


class ENoBoard(Exception):
    pass


basereg0 = (
    ('DI', 'ndi', lambda x: (x + 15) / 16),
    ('DO', 'ndo', lambda x: (x + 15) / 16),
    ('AO', 'nao', lambda x: x),
    ('AI', 'nai', lambda x: x),
    ('STATUS', None, lambda x: 1),
    ('UART', 'nuart', lambda x: x),
    ('CNT', 'ndi', lambda x: 2 * x),
    ('PWM', 'ndo', lambda x: min(4, x)),
    ('ULED', 'hw', lambda x: 1 if x in (0,) else 0),
    ('ALL', None, None),
)

basereg1000 = (
    ('VER', None, lambda x: 10),
    ('DEB', 'ndi', lambda x: x),
    ('DS', 'ndi', lambda x: 3 if x > 0 else 0),
    ('PWM', 'ndo', lambda x: 2 if x > 0 else 0),
    ('AOSW', 'nao', lambda x: 1 if x > 0 else 0),
    ('AOCAL', 'nao', lambda x: 4 * x),
    ('AISW', 'nai1', lambda x: 1 if x > 0 else 0),
    ('AICAL', 'nai1', lambda x: 4 * x),
    ('AICAL2', 'nai2', lambda x: 2 * x),
    ('UART', 'nuart', lambda x: x),
    ('ALL', None, None),
)


class Neuron(object):
    def __init__(self, circuit, modbus_server, modbus_port, scan_freq, scan_enabled):
        self.circuit = circuit
        self.modbus_server = modbus_server
        self.modbus_port = modbus_port
        self.do_scanning = False
        self.is_scanning = False
        if scan_freq == 0:
            self.scan_interval = 0
        else:
            self.scan_interval = 1.0 / scan_freq
        self.scan_enabled = scan_enabled
        self.boards = list()

    def switch_to_async(self, loop):
        self.loop = loop
        self.client = ModbusClientProtocol()
        # start modus/tcp client. On connect call self.readboards
        loop.add_callback(lambda: StartClient(self.client, self.modbus_server, self.modbus_port, self.readboards))

    @gen.coroutine
    def readboards(self):
        """ Try to read version registers on 3 boards and create subdevices """
        # ToDo - destroy all boards and subdevices before creating
        for board in self.boards:
            del (board)
        self.boards = list()
        for i in (1, 2, 3):
            try:
                versions = yield self.client.read_input_registers(1000, 10, unit=i)
                logger.debug(type(versions))
                logger.debug(versions.registers)
                if isinstance(versions, ExceptionResponse):
                    raise ENoBoard("bad request")
                board = Board(i, self, versions.registers)
                data = yield self.client.read_input_registers(0, count=board.ndataregs, unit=i)
                configs = yield self.client.read_input_registers(1000, count=board.nconfigregs, unit=i)
                board.create_subdevices(data.registers, configs.registers)
                self.boards.append(board)
            except ENoBoard:
                pass
            except Exception, E:
                logger.debug(str(E))
                pass

    def start_scanning(self):
        self.do_scanning = True
        if not self.is_scanning:
            #if self.scan_interval != 0:
            self.loop.call_later(self.scan_interval, self.scan_boards)
            self.is_scanning = True


    def stop_scanning(self):
        if not self.scan_enabled:
            self.do_scanning = False


    @gen.coroutine
    def scan_boards(self):
        if self.client.connected:
            try:
                for board in self.boards:
                    data = yield self.client.read_input_registers(0, count=board.ndataregs, unit=board.circuit)
                    if isinstance(data, ExceptionResponse):
                        raise Exception("bad request")
                    board.set_data(0, data.registers)
            except Exception, E:
                logger.debug(str(E))
        if self.do_scanning and (self.scan_interval != 0):
            self.loop.call_later(self.scan_interval, self.scan_boards)
            self.is_scanning = True
        else:
            self.is_scanning = False


class Proxy(object):
    def __init__(self, changeset):
        self.changeset = changeset

    def full(self):
        self.result = [c.full() for c in self.changeset]
        self.full = self.fullcache
        return self.result

    def fullcache(self):
        return self.result


class Board(object):
    def __init__(self, circuit, neuron, versions):
        self.circuit = circuit
        self.neuron = neuron
        self.sw = versions[0]
        self.ndi = (versions[1] & 0xff00) >> 8
        self.ndo = (versions[1] & 0x00ff)
        self.nai = (versions[2] & 0xff00) >> 8
        self.nao = (versions[2] & 0x00f0) >> 4
        self.nuart = (versions[2] & 0x000f)
        self.hw = (versions[3] & 0xff00) >> 8
        self.hwv = (versions[3] & 0x00ff)
        self.serial = versions[5] + (versions[6] << 16)
        self.nai1 = self.nai if self.hw != 0 else 1  # full featured AI (with switched V/A)
        self.nai2 = 0 if self.hw != 0 else 1  # Voltage only AI
        self.ndataregs = self.get_base_reg(0, 'ALL')
        self.nconfigregs = self.get_base_reg(1000, 'ALL') - 1000
        #print self.ndataregs, self.nconfigregs


    def get_base_reg(self, base, kind):
        if base == 0:
            registers = basereg0
            cur = 0
        elif base == 1000:
            registers = basereg1000
            cur = 1000
        else:
            raise Exception('bad base index')
        for reg in registers:
            if kind == reg[0]: return cur
            x = reg[1]
            func = reg[2]
            if not (x is None): x = getattr(self, x)
            cur += func(x)


    def create_subdevices(self, data, configs):
        self.data = data
        self.configs = configs
        self.datadeps = [set() for _ in range(len(data))]
        if (self.hw == 0):
            self.volt_refx = (3.3 * configs[9])
            self.volt_ref = (3.3 * configs[9]) / data[5]

        base = self.get_base_reg(0, 'DI')
        base_deb = self.get_base_reg(1000, 'DEB') - 1000
        base_counter = self.get_base_reg(0, 'CNT')

        for i in range(self.ndi):
            if i == 16: base += 1
            _inp = Input("%s_%02d" % (self.circuit, i + 1), self, base, 0x1 << (i % 16),
                         regdebounce=base_deb + i, regcounter=base_counter + (2 * i))
            self.datadeps[base].add(_inp)
            self.datadeps[base_counter + (2 * i)].add(_inp)
            Devices.register_device(INPUT, _inp)

        base = self.get_base_reg(0, 'DO')  # + (self.circuit - 1) * 100
        for i in range(self.ndo):
            if i == 16: base += 1
            _r = Relay("%s_%02d" % (self.circuit, i + 1), self, i, base, 0x1 << (i % 16))
            self.datadeps[base].add(_r)
            Devices.register_device(RELAY, _r)

        base = self.get_base_reg(0, 'AO')
        base_cal = self.get_base_reg(1000, 'AOCAL') - 1000
        for i in range(self.nao):
            _ao = AnalogOutput("%s_%02d" % (self.circuit, i + 1), self, base + i, base_cal + i)
            self.datadeps[base + i].add(_ao)
            Devices.register_device(AO, _ao)

        base = self.get_base_reg(0, 'AI')
        base_cal = self.get_base_reg(1000, 'AICAL') - 1000
        for i in range(self.nai):
            _ai = AnalogInput("%s_%02d" % (self.circuit, i + 1), self, base + i, base_cal + 4 * i)
            self.datadeps[base + i].add(_ai)
            Devices.register_device(AI, _ai)
            if i == 1: break

    def set_data(self, register, data):
        # ToDo!
        changeset = set()
        #print data
        for i in range(len(data)):
            try:
                if data[i] == self.data[i]: continue
            except:
                pass
            changeset.update(self.datadeps[i])  # add devices to set

        self.data = data
        if len(changeset) > 0:
            proxy = Proxy(changeset)
            devents.status(proxy)


class Relay(object):
    pending_id = 0

    def __init__(self, circuit, arm, coil, reg, mask):
        self.circuit = circuit
        self.arm = arm
        self.coil = coil
        self.bitmask = mask
        self.regvalue = lambda: arm.data[reg]
        #self.reg.devices.add(self)

    def full(self):
        return {'dev': 'relay', 'circuit': self.circuit, 'value': self.value, 'pending': self.pending_id != 0}

    def simple(self):
        return {'dev': 'relay', 'circuit': self.circuit, 'value': self.value}

    @property
    def value(self):
        try:
            if self.regvalue() & self.bitmask: return 1
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
        yield self.arm.neuron.client.write_coil(self.coil, 1 if value else 0, unit=self.arm.circuit)
        raise gen.Return(1 if value else 0)

    def set(self, value=None, timeout=None):
        """ Sets new on/off status. Disable pending timeouts
        """
        if value is None:
            raise Exception('Value must be specified')
        value = int(value)
        if not (timeout is None):
            timeout = float(timeout)

        self.arm.neuron.client.write_coil(self.coil, 1 if value else 0, unit=self.arm.circuit)

        if timeout is None:
            return (1 if value else 0)

        def timercallback():
            self.pending_id = None
            self.arm.write_bit(self.coil, 0 if value else 1, unit=self.arm.circuit)

        self.pending_id = IOLoop.instance().add_timeout(
            datetime.timedelta(seconds=float(timeout)), timercallback)
        return (1 if value else 0)
        #return (1 if self.mcp.value & self._mask else 0)


class Input():
    def __init__(self, circuit, arm, reg, mask, regcounter=None, regdebounce=None):
        self.circuit = circuit
        self.arm = arm
        self.bitmask = mask
        self.regcounter = regcounter
        self.regdebounce = regdebounce
        self.regvalue = lambda: arm.data[reg]
        self.regcountervalue = self.regdebouncevalue = lambda: None
        if not (regcounter is None): self.regcountervalue = lambda: arm.data[regcounter] + (
            arm.data[regcounter + 1] << 16)
        if not (regdebounce is None): self.regdebounce = lambda: arm.configs[regdebounce]
        #self.reg.devices.add(self)
        #self.regcounter1.devices.add(self)
        #self.regcounter2.devices.add(self)
        #self.regdebounce.devices.add(self)
        self.counter_mode = "disabled"

    @property
    def debounce(self):
        try:
            return self.regdebounce()
        except:
            pass
        return 0

    @property
    def value(self):
        if self.counter_mode != "disabled": return self.counter
        try:
            if self.regvalue() & self.bitmask: return 1
        except:
            pass
        return 0

    @property
    def counter(self):
        try:
            return self.regcountervalue()
        except:
            return 0

    def full(self):
        return {'dev': 'input', 'circuit': self.circuit, 'value': self.value,
                'debounce': self.debounce, 'counter_mode': self.counter_mode,
                'counter': self.counter}

    def simple(self):
        return {'dev': 'input', 'circuit': self.circuit, 'value': self.value}

    def set(self, debounce=None, counter=None):
        if not (debounce is None):
            if not (self._regdebounce is None):
                self.arm.write_regs(self.regdebounce.regnum, debounce, unit=self.arm.circuit)
                #devents.config(self)
        if not (counter is None):
            if not (self._regcounter is None):
                self.arm.write_regs(self.regcounter.regnum, (0, 0), unit=self.arm.circuit)
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


def uint16_to_int(inp):
    if inp > 0x8000: return (inp - 0x10000)
    return inp


class AnalogOutput():
    def __init__(self, circuit, arm, reg, regcal):
        self.circuit = circuit
        self.reg = reg
        self.regvalue = lambda: arm.data[reg]
        self.regcal = regcal
        self.arm = arm
        self.offset = (uint16_to_int(arm.configs[regcal + 1]) / 10000.0)
        self.is_voltage = lambda: True
        if circuit == '1_01':
            self.is_voltage = lambda: not bool(arm.configs[regcal - 1] & 0b1)
        self.reg_shift = 2 if self.is_voltage() else 0
        self.factor = arm.volt_ref / 4095 * (1 + uint16_to_int(arm.configs[regcal + self.reg_shift]) / 10000.0)
        self.factorx = arm.volt_refx / 4095 * (1 + uint16_to_int(arm.configs[regcal + self.reg_shift]) / 10000.0)
        if self.is_voltage():
            self.factor *= 3
            self.factorx *= 3
        else:
            self.factor *= 10
            self.factorx *= 10


    @property
    def value(self):
        try:
            return self.regvalue() * self.factor + self.offset
        except:
            return 0

    def full(self):
        return {'dev': 'ao', 'circuit': self.circuit, 'value': self.value,
                'unit': unit_names[VOLT] if self.is_voltage() else unit_names[AMPERE]}

    def simple(self):
        return {'dev': 'ao', 'circuit': self.circuit, 'value': self.value}

    @gen.coroutine
    def set_value(self, value):
        valuei = int((float(value) - self.offset) / self.factor)
        if valuei < 0:
            valuei = 0
        elif valuei > 4095:
            valuei = 4095
        #print valuei, value
        self.arm.neuron.client.write_register(self.reg, valuei, unit=self.arm.circuit)
        raise gen.Return(float(valuei) * self.factor + self.offset)

    def set(self, value=None, frequency=None, mode=None):
        if mode is not None:
            val = self.arm.configs[self.regcal - 1]
            if mode == "V":
                val &= ~0b1
            elif mode == "mA":
                val |= 0b1
            self.arm.neuron.client.write_register(1000 + self.regcal - 1, val, unit=self.arm.circuit)
        # print value
        if value is not None:
            valuei = int((float(value) - self.offset) / self.factor)
            if valuei < 0:
                valuei = 0
            elif valuei > 4095:
                valuei = 4095
            #print valuei, value
            self.arm.neuron.client.write_register(self.reg, valuei, unit=self.arm.circuit)
            raise gen.Return(float(valuei) * self.factor + self.offset)


class AnalogInput():
    def __init__(self, circuit, arm, reg, regcal):
        self.circuit = circuit
        self.regvalue = lambda: arm.data[reg]
        self.regcal = regcal
        #self.reg.devices.add(self)
        self.arm = arm
        self.is_voltage = lambda: True
        if circuit == '1_01':
            self.is_voltage = lambda: not bool(arm.configs[regcal - 1] & 0b1)
        #print self.is_voltage
        #print circuit, self.vfactor, self.vfactorx, self.voffset
        #self.afactorx = 10 * arm.volt_refx / 4095 *(1 + uint16_to_int(arm.configs[regcal+2])/10000.0)
        #self.aoffset = (uint16_to_int(arm.configs[regcal+3])/10000.0)
        self.reg_shift = 2 if self.is_voltage() else 0
        self.vfactor = arm.volt_ref / 4095 * (1 + uint16_to_int(arm.configs[regcal + self.reg_shift]) / 10000.0)
        self.vfactorx = arm.volt_refx / 4095 * (1 + uint16_to_int(arm.configs[regcal + self.reg_shift]) / 10000.0)
        self.voffset = (uint16_to_int(arm.configs[regcal + 1]) / 10000.0)
        if self.is_voltage():
            self.vfactor *= 3
            self.vfactorx *= 3
        else:
            self.vfactor *= 10
            self.vfactorx *= 10


    @property
    def value(self):
        try:
            #print self.circuit, self.regvalue(),self.vfactor,self.voffset
            return (self.regvalue() * self.vfactor) + self.voffset
        except:
            return 0

    def set(self, mode=None):
        if mode is not None:
            val = self.arm.configs[self.regcal - 1]
            if mode == "V":
                val &= ~0b1
            elif mode == "mA":
                val |= 0b1
            self.arm.neuron.client.write_register(1000 + self.regcal - 1, val, unit=self.arm.circuit)

    def full(self):
        return {'dev': 'ai', 'circuit': self.circuit, 'value': self.value,
                'unit': unit_names[VOLT] if self.is_voltage() else unit_names[AMPERE]}

    def simple(self):
        return {'dev': 'ai', 'circuit': self.circuit, 'value': self.value}

    @property  # docasne!!
    def voltage(self):
        return self.value
