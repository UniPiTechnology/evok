'''
  Code specific to Neuron devices
------------------------------------------
'''
import struct
import datetime
from dali.bus import Bus
import dali.gear.general
from math import sqrt
from tornado import gen
from tornado.ioloop import IOLoop
from modbusclient_tornado import ModbusClientProtocol, StartClient
from pymodbus.pdu import ExceptionResponse
from pymodbus.exceptions import ModbusIOException
from tornado.locks import Semaphore
import modbusclient_rs485

from devices import *
from log import *
import config
import time

from modbusclient_rs485 import AsyncErrorResponse
import subprocess
from unipidali import SyncUnipiDALIDriver
from dali.address import Broadcast, Group

class ENoBoard(Exception):
    pass

class ModbusCacheMap(object):
    last_comm_time = 0
    def __init__(self, modbus_reg_map, neuron):
        self.modbus_reg_map = modbus_reg_map
        self.neuron = neuron
        self.sem = Semaphore(1)
        self.registered = {}
        self.registered_input = {}
        self.frequency = {}
        for m_reg_group in modbus_reg_map:
            self.frequency[m_reg_group['start_reg']] = 10000001    # frequency less than 1/10 million are not read on start
            for index in range(m_reg_group['count']):
                if 'type' in m_reg_group and m_reg_group['type'] == 'input':
                    self.registered_input[(m_reg_group['start_reg'] + index)] = None
                else:
                    self.registered[(m_reg_group['start_reg'] + index)] = None

    def get_register(self, count, index, unit=0, is_input=False):
        ret = []
        for counter in range(index,count+index):
            if is_input:
                if counter not in self.registered_input:
                    raise Exception('Unknown register %d' % counter)
                elif self.registered_input[counter] is None:
                    raise Exception('No cached value of register %d on unit %d - read error' % (counter, unit))
                ret += [self.registered_input[counter]]
            else:
                if counter not in self.registered:
                    raise Exception('Unknown register %d' % counter)
                elif self.registered[counter] is None:
                    raise Exception('No cached value of register %d on unit %d - read error' % (counter, unit))
                ret += [self.registered[counter]]
        return ret

    @gen.coroutine
    def do_scan(self, unit=0, initial=False):
        if initial:
            yield self.sem.acquire()
        changeset = []
        for m_reg_group in self.modbus_reg_map:
            if (self.frequency[m_reg_group['start_reg']] >= m_reg_group['frequency']) or (self.frequency[m_reg_group['start_reg']] == 0):    # only read once for every [frequency] cycles
                try:
                    val = None
                    if 'type' in m_reg_group and m_reg_group['type'] == 'input':
                        val = yield self.neuron.client.read_input_registers(m_reg_group['start_reg'], m_reg_group['count'], unit=unit)
                    else:
                        val = yield self.neuron.client.read_holding_registers(m_reg_group['start_reg'], m_reg_group['count'], unit=unit)
                    if not isinstance(val, AsyncErrorResponse) and not isinstance(val, ModbusIOException) and not isinstance(val, ExceptionResponse):
                        self.last_comm_time = time.time()
                        if 'type' in m_reg_group and m_reg_group['type'] == 'input':
                            for index in range(m_reg_group['count']):
                                if (m_reg_group['start_reg'] + index) in self.neuron.datadeps and self.registered_input[(m_reg_group['start_reg'] + index)] != val.registers[index]:
                                    for ddep in self.neuron.datadeps[m_reg_group['start_reg'] + index]:
                                        if (not ((isinstance(ddep, Input) or isinstance(ddep, ULED)))) or ddep.value_delta(val.registers[index]):
                                            changeset += [ddep]
                                self.registered_input[(m_reg_group['start_reg'] + index)] = val.registers[index]
                                self.frequency[m_reg_group['start_reg']] = 1
                        else:
                            for index in range(m_reg_group['count']):
                                if (m_reg_group['start_reg'] + index) in self.neuron.datadeps and self.registered[(m_reg_group['start_reg'] + index)] != val.registers[index]:
                                    for ddep in self.neuron.datadeps[m_reg_group['start_reg'] + index]:
                                        if (not ((isinstance(ddep, Input) or isinstance(ddep, ULED) or isinstance(ddep, Relay) or isinstance(ddep, Watchdog)))) or ddep.value_delta(val.registers[index]):
                                            changeset += [ddep]
                                self.registered[(m_reg_group['start_reg'] + index)] = val.registers[index]
                                self.frequency[m_reg_group['start_reg']] = 1
                except Exception, E:
                    logger.debug(str(E))
            else:
                self.frequency[m_reg_group['start_reg']] += 1
        if len(changeset) > 0:
            proxy = Proxy(set(changeset))
            devents.status(proxy)
        if initial:
            self.sem.release()

    def set_register(self, count, index, inp, unit=0, is_input=False):
        if len(inp) < count:
            raise Exception('Insufficient data to write into registers')
        for counter in range(count):
            if is_input:
                if index + counter not in self.registered_input:
                    raise Exception('Unknown register %d' % index + counter)
                self.neuron.client.write_register(index + counter, 1, inp[counter], unit=unit)
                self.registered_input[index + counter] = inp[counter]
            else:
                if index + counter not in self.registered:
                    raise Exception('Unknown register %d' % index + counter)
                self.neuron.client.write_register(index + counter, 1, inp[counter], unit=unit)
                self.registered[index + counter] = inp[counter]

    def has_register(self, index, is_input=False):
        if is_input:
            if index not in self.registered_input:
                return False
            else:
                return True
        else:
            if index not in self.registered:
                return False
            else:
                return True

    @gen.coroutine
    def get_register_async(self, count, index, unit=0, is_input=False):
        if is_input:
            for counter in range(index,count+index):
                if counter not in self.registered_input:
                    raise Exception('Unknown register')
            val = yield self.neuron.client.read_input_registers(index, count, unit=unit)
            for counter in range(len(val.registers)):
                self.registered_input[index+counter] = val.registers[counter]
            raise gen.Return(val.registers)
        else:
            for counter in range(index,count+index):
                if counter not in self.registered:
                    raise Exception('Unknown register')
            val = yield self.neuron.client.read_holding_registers(index, count, unit=unit)
            for counter in range(len(val.registers)):
                self.registered[index+counter] = val.registers[counter]
            raise gen.Return(val.registers)


    @gen.coroutine
    def set_register_async(self, count, index, inp, unit=0, is_input=False):
        if is_input:
            if len(inp) < count:
                raise Exception('Insufficient data to write into registers')
            for counter in range(count):
                if index + counter not in self.registered_input:
                    raise Exception('Unknown register')
                yield self.neuron.client.write_register(index + counter, 1, inp[counter], unit=unit)
                self.registered_input[index + counter] = inp[counter]
        else:
            if len(inp) < count:
                raise Exception('Insufficient data to write into registers')
            for counter in range(count):
                if index + counter not in self.registered:
                    raise Exception('Unknown register')
                yield self.neuron.client.write_register(index + counter, 1, inp[counter], unit=unit)
                self.registered[index + counter] = inp[counter]

class Neuron(object):
    def __init__(self, circuit, Config, modbus_server, modbus_port, scan_freq, scan_enabled, hw_dict, direct_access=False, major_group=1, dev_id=0):
        self.alias = ""
        self.devtype = NEURON
        self.dev_id = dev_id
        self.circuit = str(circuit)
        self.hw_dict = hw_dict
        self.datadeps = {}
        self.Config = Config
        self.direct_access = direct_access
        self.modbus_server = modbus_server
        self.modbus_port = modbus_port
        self.major_group = major_group
        self.modbus_address = 0
        self.do_scanning = False
        self.is_scanning = False
        self.scanning_error_triggered = False
        if scan_freq == 0:
            self.scan_interval = 0
        else:
            self.scan_interval = 1.0 / scan_freq
        self.scan_enabled = scan_enabled
        self.boards = list()
        self.modbus_cache_map = None
        self.versions = []
        self.logfile = Config.getstringdef("MAIN", "log_file", "/var/log/evok.log")

    def switch_to_async(self, loop, alias_dict):
        self.loop = loop
        self.client = ModbusClientProtocol()
        loop.add_callback(lambda: StartClient(self.client, self.modbus_server, self.modbus_port, self.readboards, callback_args=alias_dict))

    @gen.coroutine
    def set(self, print_log=None):
        if print_log is not None and print_log != 0:
            log_tail = subprocess.check_output(["tail", "-n 255", self.logfile])
            raise gen.Return(log_tail)
        else:
            raise gen.Return("")

    @gen.coroutine
    def readboards(self, alias_dict):
        """ Try to read version registers on 3 boards and create subdevices """
        logger.info("Reading SPI boards")
        for board in self.boards:
            del (board)
        self.boards = list()
        for i in (1, 2, 3):
            try:
                versions = yield self.client.read_input_registers(1000, 10, unit=i)
                if isinstance(versions, ExceptionResponse):
                    raise ENoBoard("Bad request")
                else:
                    self.versions += [versions.registers]
                board = Board(self.Config, i, self, versions.registers, major_group=i, direct_access=self.direct_access, dev_id=self.dev_id)
                yield board.parse_definition(self.hw_dict, i)
                self.boards.append(board)
            except ENoBoard:
                logger.info("No board on SPI %d" % i)
                continue
            except Exception, E:
                logger.exception(str(E))
                pass
        yield config.add_aliases(alias_dict)

    def start_scanning(self):
        self.do_scanning = True
        if not self.is_scanning:
            self.loop.call_later(self.scan_interval, self.scan_boards)
            self.is_scanning = True


    def stop_scanning(self):
        if not self.scan_enabled:
            self.do_scanning = False

    def full(self):
        ret = {'dev': 'neuron',
                'circuit': self.circuit,
                'model': config.up_globals['model'],
                'sn': config.up_globals['serial'],
                'ver2': config.up_globals['version2'],
                'board_count': len(self.boards),
                'glob_dev_id': self.dev_id,
                'last_comm': 0x7fffffff}
        if self.alias != '':
            ret['alias'] = self.alias
        if self.modbus_cache_map is not None:
            ret['last_comm'] = time.time() - self.modbus_cache_map.last_comm_time
        return ret

    def get(self):
        return self.full()

    @gen.coroutine
    def scan_boards(self):
        if self.client.connected:
            try:
                if self.modbus_cache_map is not None:
                    yield self.modbus_cache_map.do_scan()
            except Exception, E:
                if not self.scanning_error_triggered:
                    logger.exception(str(E))
                self.scanning_error_triggered = True
            self.scanning_error_triggered = False
        if self.do_scanning and (self.scan_interval != 0):
            self.loop.call_later(self.scan_interval, self.scan_boards)
            self.is_scanning = True
        else:
            self.is_scanning = False


class ModbusNeuron(object):

    def __init__(self, circuit, Config, scan_freq, scan_enabled, hw_dict, modbus_address=15,
                       major_group=1, device_name='unspecified', direct_access=False, dev_id=0):
        self.alias = ""
        self.devtype = NEURON
        self.modbus_cache_map = None
        self.datadeps = {}
        self.boards = list()
        self.dev_id = dev_id
        self.hw_dict = hw_dict
        self.direct_access = direct_access
        self.modbus_address = modbus_address
        self.device_name = device_name
        self.Config = Config
        self.do_scanning = False
        self.is_scanning = False
        self.scanning_error_triggered = False
        self.major_group = major_group
        self.hw_board_dict = {}
        if scan_freq == 0:
            self.scan_interval = 0
        else:
            self.scan_interval = 1.0 / scan_freq
        self.scan_enabled = scan_enabled
        self.versions = []
        self.logfile = Config.getstringdef("MAIN", "log_file", "/var/log/evok.log")

    def get(self):
        return self.full()

    @gen.coroutine
    def set(self, print_log=None):
        if print_log is not None and print_log != 0:
            log_tail = subprocess.check_output(["tail", "-n 255", self.logfile])
            raise gen.Return(log_tail)
        else:
            return gen.Return("")

    @gen.coroutine
    def readboards(self, alias_dict):
        logger.info("Reading the Modbus board on Modbus address %d" % self.modbus_address)
        self.boards = list()
        try:
            for defin in self.hw_dict.definitions:
                if defin and (defin['type'] == self.device_name):
                    self.hw_board_dict = defin
                    break
            self.versions = yield self.client.read_input_registers(1000, 10, unit=self.modbus_address)
            if isinstance(self.versions, ExceptionResponse):
                self.versions = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
            elif isinstance(self.versions, AsyncErrorResponse):
                self.versions = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
            else:
                self.versions = self.versions.registers

            board = UartBoard(self.Config, self.circuit, self.modbus_address, self, self.versions, dev_id=self.dev_id, direct_access=self.direct_access)
            yield board.parse_definition(self.hw_dict)
            self.boards.append(board)
            yield config.add_aliases(alias_dict)
        except ENoBoard:
            logger.info("No board detected on UART %d" % self.modbus_address)
        except Exception, E:
            Devices.remove_global_device(self.dev_id)
            logger.exception(str(E))
            pass

    def start_scanning(self):
        self.do_scanning = True
        if not self.is_scanning:
            self.loop.call_later(self.scan_interval, self.scan_boards)
            self.is_scanning = True

    def stop_scanning(self):
        if not self.scan_enabled:
            self.do_scanning = False

    @gen.coroutine
    def scan_boards(self, invoc=False):
        if self.is_scanning and invoc:
            raise gen.Return()
        try:
            if self.modbus_cache_map is not None:
                yield self.modbus_cache_map.do_scan(unit=self.modbus_address)
                self.scanning_error_triggered = False
        except Exception, E:
            if not self.scanning_error_triggered:
                logger.debug(str(E))
            self.scanning_error_triggered = True
        if self.do_scanning and (self.scan_interval != 0):
            self.loop.call_later(self.scan_interval, self.scan_boards)
            self.is_scanning = True
        else:
            self.is_scanning = False


class UartNeuron(ModbusNeuron):

    def __init__(self, circuit, Config, port, scan_freq, scan_enabled, hw_dict, 
                 baud_rate=19200, parity='N', stopbits=1, uart_address=15, major_group=1, 
                 device_name='unspecified', direct_access=False, neuron_uart_circuit="None", dev_id=0):
        ModbusNeuron.__init__(self,circuit, Config, scan_freq, scan_enabled, hw_dict, uart_address,
                              major_group, device_name, direct_access, dev_id)
        self.circuit = "UART_" + str(uart_address) + "_" + str(circuit)
        self.port = port
        self.baud_rate = baud_rate
        self.parity = parity
        self.stopbits = stopbits
        self.neuron_uart_circuit = neuron_uart_circuit

    def switch_to_async(self, loop, alias_dict):
        self.loop = loop
        if self.port in modbusclient_rs485.client_dict:
            self.client = modbusclient_rs485.client_dict[self.port]
        else:
            self.client = modbusclient_rs485.AsyncModbusGeneratorClient(method='rtu', stopbits=self.stopbits, bytesize=8, parity=self.parity, baudrate=self.baud_rate, timeout=1.5, port=self.port)
            modbusclient_rs485.client_dict[self.port] = self.client
        loop.add_callback(lambda: modbusclient_rs485.UartStartClient(self, self.readboards, callback_args=alias_dict))


    def full(self):
        ret = {'dev': 'extension',
                'circuit': self.circuit,
                'model': self.device_name,
                'uart_circuit': self.neuron_uart_circuit,
                'uart_port': self.port,
                'glob_dev_id': self.dev_id,
                'last_comm': 0x7fffffff}
        if self.alias != '':
            ret['alias'] = self.alias
        if self.modbus_cache_map is not None:
            ret['last_comm'] = time.time() - self.modbus_cache_map.last_comm_time
        return ret


class TcpNeuron(ModbusNeuron):

    def __init__(self, circuit, Config, modbus_server, modbus_port, scan_freq, scan_enabled, hw_dict, 
                 modbus_address=1, major_group=1, device_name='unspecified', direct_access=False, dev_id=0):
        ModbusNeuron.__init__(self,circuit, Config, scan_freq, scan_enabled, hw_dict, modbus_address,
                              major_group, device_name, direct_access, dev_id)
        self.circuit = circuit; #"EXT_" + str(modbus_address)
        self.modbus_server = modbus_server
        self.modbus_port = modbus_port


    def switch_to_async(self, loop, alias_dict):
        self.loop = loop
        self.client = ModbusClientProtocol()
        loop.add_callback(lambda: StartClient(self.client, self.modbus_server, self.modbus_port,
                                              self.readboards, callback_args=alias_dict))

    def full(self):
        ret = {'dev': 'extension',
                'circuit': self.circuit,
                'model': self.device_name,
                'modbus_server': self.modbus_server,
                'modbus_port': self.modbus_port,
                'glob_dev_id': self.dev_id,
                'last_comm': 0x7fffffff}
        if self.alias != '':
            ret['alias'] = self.alias
        if self.modbus_cache_map is not None:
            ret['last_comm'] = time.time() - self.modbus_cache_map.last_comm_time
        return ret


class Proxy(object):
    def __init__(self, changeset):
        self.changeset = changeset

    def full(self):
        self.result = [c.full() for c in self.changeset]
        self.full = self.fullcache
        return self.result

    def fullcache(self):
        return self.result

class UartBoard(object):
    def __init__(self, Config, circuit, modbus_address, neuron, versions, direct_access=False, major_group=1, dev_id=0):
        self.alias = ""
        self.devtype = BOARD
        self.dev_id = dev_id
        self.Config = Config
        self.circuit = circuit
        self.direct_access = direct_access
        self.legacy_mode = not (Config.getbooldef('MAIN','use_experimental_api', False))
        self.neuron = neuron
        self.major_group = major_group
        self.modbus_address = modbus_address
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
        self.nai2 = 0 if self.hw != 0 else 1           # Voltage only AI

    @gen.coroutine
    def set(self, alias=None):
        if not alias is None:
            if Devices.add_alias(alias, self, file_update=True):
                self.alias = alias
        return gen.Return(self.full())

    @gen.coroutine
    def initialise_cache(self, cache_definition):
        if cache_definition and (self.neuron.device_name == cache_definition['type']):
            if cache_definition.has_key('modbus_register_blocks'):
                if self.neuron.modbus_cache_map == None:
                    self.neuron.modbus_cache_map = ModbusCacheMap(cache_definition['modbus_register_blocks'], self.neuron)
                    yield self.neuron.modbus_cache_map.do_scan(initial=True, unit=self.modbus_address)
                    yield self.neuron.modbus_cache_map.sem.acquire()
                    self.neuron.modbus_cache_map.sem.release()
                else:
                    yield self.neuron.modbus_cache_map.sem.acquire()
                    self.neuron.modbus_cache_map.sem.release()
            else:
                raise Exception("HW Definition %s requires Modbus register blocks to be specified" % cache_definition['type'])

    def parse_feature_di(self, max_count, m_feature, board_id):
        counter = 0
        while counter < max_count:
            board_val_reg = m_feature['val_reg']
            board_counter_reg = m_feature['counter_reg']
            board_deboun_reg = m_feature['deboun_reg']
            start_index = 0
            if m_feature.has_key('start_index'):
                start_index = m_feature['start_index']
            if m_feature.has_key('ds_modes') and m_feature.has_key('direct_reg') and m_feature.has_key('polar_reg') and m_feature.has_key('toggle_reg'):
                _inp = Input("%s_%02d" % (self.circuit, counter + 1 + start_index), self, board_val_reg, 0x1 << (counter % 16),
                             regdebounce=board_deboun_reg + counter, major_group=0, regcounter=board_counter_reg + (2 * counter), modes=m_feature['modes'],
                             dev_id=self.dev_id, ds_modes=m_feature['ds_modes'], regmode=m_feature['direct_reg'], regtoggle=m_feature['toggle_reg'],
                             regpolarity=m_feature['polar_reg'], legacy_mode=self.legacy_mode)
            else:
                _inp = Input("%s_%02d" % (self.circuit, counter + 1 + start_index), self, board_val_reg, 0x1 << (counter % 16),
                             regdebounce=board_deboun_reg + counter, major_group=0, regcounter=board_counter_reg + (2 * counter), modes=m_feature['modes'],
                             dev_id=self.dev_id, legacy_mode=self.legacy_mode)
            if self.neuron.datadeps.has_key(board_val_reg):
                self.neuron.datadeps[board_val_reg]+=[_inp]
            else:
                self.neuron.datadeps[board_val_reg] = [_inp]
            if self.neuron.datadeps.has_key(board_counter_reg + (2 * counter)):
                self.neuron.datadeps[board_counter_reg + (2 * counter)]+=[_inp]
            else:
                self.neuron.datadeps[board_counter_reg + (2 * counter)] = [_inp]
            Devices.register_device(INPUT, _inp)
            counter+=1

    def parse_feature_ro(self, max_count, m_feature, board_id):
        counter = 0
        while counter < max_count:
            board_val_reg = m_feature['val_reg']
            #if m_feature['type'] == 'DO' and m_feature['pwm_reg'] and m_feature['pwm_ps_reg'] and (m_feature['pwm_c_reg'] or m_feature['pwm_pres_reg']):
            if m_feature['type'] == 'DO' and m_feature.get('pwm_reg') is not None:
                # PWM with presets

                if m_feature.get('pwm_preset_reg') is not None:

                    # PWM with both preset and cycle registers
                    if m_feature.get('pwm_c_reg') is not None:
                        _r = Relay("%s_%02d" % (self.circuit, counter + 1), self, m_feature['val_coil'] + counter,
                                   board_val_reg, 0x1 << (counter % 16),
                                   dev_id=self.dev_id, major_group=0, pwmcyclereg=m_feature['pwm_c_reg'],
                                   pwmprescalereg=m_feature['pwm_ps_reg'], digital_only=True,
                                   pwmdutyreg=m_feature['pwm_reg'] + counter, presetreg=m_feature['pwm_preset_reg'], presets=m_feature['presets'], modes=m_feature['modes'],
                                   legacy_mode=self.legacy_mode)
                    # PWM with preset register
                    else:
                        _r = Relay("%s_%02d" % (self.circuit, counter + 1), self, m_feature['val_coil'] + counter,
                                   board_val_reg, 0x1 << (counter % 16),
                                   dev_id=self.dev_id, major_group=0,
                                   pwmprescalereg=m_feature['pwm_ps_reg'], digital_only=True,
                                   pwmdutyreg=m_feature['pwm_reg'] + counter, presetreg=m_feature['pwm_preset_reg'], presets=m_feature['presets'], modes=m_feature['modes'],
                                   legacy_mode=self.legacy_mode)

                # SW PWM without preset register
                else:
                    _r = Relay("%s_%02d" % (self.circuit, counter + 1), self, m_feature['val_coil'] + counter,
                               board_val_reg, 0x1 << (counter % 16),
                               dev_id=self.dev_id, major_group=0, pwmcyclereg=m_feature['pwm_c_reg'],
                               pwmprescalereg=m_feature['pwm_ps_reg'], digital_only=True,
                               pwmdutyreg=m_feature['pwm_reg'] + counter, modes=m_feature['modes'],
                               legacy_mode=self.legacy_mode)



            else:
                    _r = Relay("%s_%02d" % (self.circuit, counter + 1), self, m_feature['val_coil'] + counter, board_val_reg, 0x1 << (counter % 16),
                               dev_id=self.dev_id, major_group=0, legacy_mode=self.legacy_mode)
            if self.neuron.datadeps.has_key(board_val_reg):
                self.neuron.datadeps[board_val_reg]+=[_r]
            else:
                self.neuron.datadeps[board_val_reg] = [_r]
            Devices.register_device(RELAY, _r)
            counter+=1

    def parse_feature_led(self, max_count, m_feature, board_id):
        counter = 0
        while counter < max_count:
            board_val_reg = m_feature['val_reg']
            _led = ULED("%s_%02d" % (self.circuit, counter + 1), self, counter, board_val_reg, 0x1 << (counter % 16), m_feature['val_coil'] + counter,
                        dev_id=self.dev_id, major_group=0, legacy_mode=self.legacy_mode)
            if self.neuron.datadeps.has_key(board_val_reg + counter):
                self.neuron.datadeps[board_val_reg] += [_led]
            else:
                self.neuron.datadeps[board_val_reg] = [_led]
            Devices.register_device(LED, _led)
            counter+=1

    def parse_feature_wd(self, max_count, m_feature, board_id):
        counter = 0
        while counter < max_count:
            board_val_reg = m_feature['val_reg']
            board_timeout_reg = m_feature['timeout_reg']
            _wd = Watchdog("%s_%02d" % (self.circuit, counter + 1), self, counter, board_val_reg + counter, board_timeout_reg + counter,
                           dev_id=self.dev_id, major_group=0, nv_save_coil=m_feature['nv_sav_coil'], reset_coil=m_feature['reset_coil'],
                           legacy_mode=self.legacy_mode)
            if self.neuron.datadeps.has_key(board_val_reg + counter):
                self.neuron.datadeps[board_val_reg + counter]+=[_wd]
            else:
                self.neuron.datadeps[board_val_reg + counter] = [_wd]
            Devices.register_device(WATCHDOG, _wd)
            counter+=1

    def parse_feature_ao(self, max_count, m_feature, board_id):
        counter = 0
        while counter < max_count:
            board_val_reg = m_feature['val_reg']
            if m_feature.has_key('cal_reg'):
                _ao = AnalogOutput("%s_%02d" % (self.circuit, counter + 1), self, board_val_reg + counter, regcal=m_feature['cal_reg'],
                                   regmode=m_feature['mode_reg'], reg_res=m_feature['res_val_reg'], modes=m_feature['modes'],
                                   dev_id=self.dev_id, major_group=m_feature['major_group'], legacy_mode=self.legacy_mode)
            else:
                _ao = AnalogOutput("%s_%02d" % (self.circuit, counter + 1), self, board_val_reg + counter, dev_id=self.dev_id,
                                   major_group=0, legacy_mode=self.legacy_mode)
            if self.neuron.datadeps.has_key(board_val_reg + counter):
                self.neuron.datadeps[board_val_reg + counter]+=[_ao]
            else:
                self.neuron.datadeps[board_val_reg + counter] = [_ao]
            Devices.register_device(AO, _ao)
            counter+=1

    def parse_feature_ai18(self, max_count, m_feature, board_id):
        value_reg = m_feature['val_reg']
        mode_reg = m_feature['mode_reg']
        for i in range(max_count):
            circuit = "%s_%02d" % (self.circuit, i + 1)
            _ai = AnalogInput18(circuit, self, value_reg, regmode=mode_reg+i,
                                dev_id=self.dev_id, major_group=0, modes=m_feature['modes'])

            if self.neuron.datadeps.has_key(value_reg):
                self.neuron.datadeps[value_reg]+=[_ai]
            else:
                self.neuron.datadeps[value_reg] = [_ai]
            Devices.register_device(AI, _ai)
            value_reg += 2;


    def parse_feature_ai(self, max_count, m_feature, board_id):
        counter = 0
        while counter < max_count:
            board_val_reg = m_feature['val_reg']
            tolerances = m_feature.get('tolerances')
            circuit = "%s_%02d" % (self.circuit, counter + 1)
            if m_feature.has_key('cal_reg'):
                board_val_reg = m_feature['val_reg'] + counter
                _ai = AnalogInput(circuit, self, board_val_reg, regcal=m_feature['cal_reg'],
                                  regmode=m_feature['mode_reg'], 
                                  dev_id=self.dev_id, major_group=0, tolerances=tolerances, modes=m_feature['modes'], legacy_mode=self.legacy_mode)
            elif (m_feature.get('type') == "AI18" ):
                board_val_reg = m_feature['val_reg'] + counter * 2
                _ai = AnalogInput18(circuit, self, board_val_reg,
                                  regmode=m_feature['mode_reg'] + counter, 
                                  dev_id=self.dev_id, major_group=0, modes=m_feature['modes'])
            elif (m_feature.get('type') == "AI12"):
                board_val_reg = m_feature['val_reg'] + counter * 2
                board_val_reg_raw = m_feature['val_reg'] + 17 + counter * 2
                _ai = AnalogInput12(circuit, self, board_val_reg, board_val_reg_raw,
                                    regmode=m_feature['mode_reg'] + counter,
                                    dev_id=self.dev_id, major_group=0, modes=m_feature['modes'])

            else:
                board_val_reg = m_feature['val_reg'] + counter * 2
                _ai = AnalogInput(circuit, self, board_val_reg,
                                  regmode=m_feature['mode_reg'] + counter, 
                                  dev_id=self.dev_id, major_group=0, tolerances=tolerances, modes=m_feature['modes'], legacy_mode=self.legacy_mode)

            if self.neuron.datadeps.has_key(board_val_reg):
                self.neuron.datadeps[board_val_reg]+=[_ai]
            else:
                self.neuron.datadeps[board_val_reg] = [_ai]
            Devices.register_device(AI, _ai)
            counter+=1

    def parse_feature_register(self, max_count, m_feature, board_id):
        counter = 0
        while counter < max_count:
            board_val_reg = m_feature['start_reg']
            if 'reg_type' in m_feature and m_feature['reg_type'] == 'input':
                _reg = Register("%s_%d_inp" % (self.circuit, board_val_reg + counter), self, counter, board_val_reg + counter, reg_type='input', dev_id=self.dev_id,
                                major_group=0, legacy_mode=self.legacy_mode)
            else:
                _reg = Register("%s_%d" % (self.circuit, board_val_reg + counter), self, counter, board_val_reg + counter, dev_id=self.dev_id,
                                major_group=0, legacy_mode=self.legacy_mode)
            if board_val_reg and self.neuron.datadeps.has_key(board_val_reg + counter):
                self.neuron.datadeps[board_val_reg + counter] += [_reg]
            elif board_val_reg:
                self.neuron.datadeps[board_val_reg + counter] = [_reg]
            Devices.register_device(REGISTER, _reg)
            counter+=1

    def parse_feature_uart(self, max_count, m_feature, board_id):
        counter = 0
        while counter < max_count:
            board_val_reg = m_feature['conf_reg']
            address_reg = m_feature['address_reg']
            _uart = Uart("%s_%02d" % (self.circuit, counter + 1), self, board_val_reg + counter, dev_id=self.dev_id,
                         major_group=0, parity_modes=m_feature['parity_modes'], speed_modes=m_feature['speed_modes'],
                         stopb_modes=m_feature['stopb_modes'], address_reg=address_reg, legacy_mode=self.legacy_mode)
            Devices.register_device(UART, _uart)
            counter+=1

    def parse_feature_unit_register(self, max_count, m_feature, board_id):
        counter = 0
        board_val_reg = m_feature['value_reg']
        while counter < max_count:

            #self, circuit, arm, post, reg, dev_id=0, major_group=0

            _offset = m_feature.get("offset",0)
            _factor = m_feature.get("factor",1)
            _unit = m_feature.get("unit")
            _name = m_feature.get("name")
            _valid_mask = m_feature.get('valid_mask_reg')
            _post_write_action = m_feature.get('post_write')
            _datatype = m_feature.get('datatype')

            _xgt = UnitRegister("{}_{}".format(self.circuit, board_val_reg + counter), self, board_val_reg + counter, reg_type="input",
                                dev_id=self.dev_id, datatype=_datatype, major_group=0, offset=_offset, factor=_factor, unit=_unit,
                                valid_mask=_valid_mask, name=_name, post_write=_post_write_action)

            Devices.register_device(UNIT_REGISTER, _xgt)
            counter+=1

    def parse_feature_ext_config(self, m_feature, board_id):


        #_xext_conf = ExtConfig("{}_CONFIG".format(self.circuit), self, reg_groups=m_feature, dev_id=self.dev_id)
        _xext_conf = ExtConfig("{}".format(self.circuit), self, reg_groups=m_feature, dev_id=self.dev_id)
        Devices.register_device(EXT_CONFIG, _xext_conf)

        # --------------------------------------------------------------
        """
        board_val_reg = m_feature['value_reg']
        while counter < max_count:

            _valid_mask = m_feature.get('valid_mask_reg')
            _post_write_action = m_feature.get('post_write')

            _xgt = UnitRegister("{}_{}".format(self.circuit, board_val_reg + counter), self, board_val_reg + counter, reg_type="input",
                                dev_id=self.dev_id, major_group=0, offset=_offset, factor=_factor, unit=_unit,
                                valid_mask=_valid_mask, name=_name, post_write=_post_write_action)
            counter+=1
        """


    def parse_feature(self, m_feature):
        board_id = 1 # UART Extension has always only one group
        #print("Kajda " + str(m_feature['type']))
        max_count = m_feature.get('count')
        if m_feature['type'] == 'DI':
            self.parse_feature_di(max_count, m_feature, board_id)
        elif (m_feature['type'] == 'RO' or m_feature['type'] == 'DO'):
            self.parse_feature_ro(max_count, m_feature, board_id)
        elif m_feature['type'] == 'LED':
            self.parse_feature_led(max_count, m_feature, board_id)
        elif m_feature['type'] == 'WD':
            self.parse_feature_wd(max_count, m_feature, board_id)
        elif m_feature['type'] == 'AO':
            self.parse_feature_ao(max_count, m_feature, board_id)
        elif m_feature['type'] == 'AI':
            self.parse_feature_ai(max_count, m_feature, board_id)
        elif m_feature['type'] == 'AI18':
            self.parse_feature_ai(max_count, m_feature, board_id)
        elif m_feature['type'] == 'AI12':
            self.parse_feature_ai(max_count, m_feature, board_id)
        elif m_feature['type'] == 'REGISTER' and self.direct_access:
            self.parse_feature_register(max_count, m_feature, board_id)
        elif m_feature['type'] == 'UART':
            self.parse_feature_uart(max_count, m_feature, board_id)
        elif m_feature['type'] == 'UNIT_REGISTER':
            self.parse_feature_unit_register(max_count, m_feature, board_id)
        elif m_feature['type'] == 'EXT_CONFIG':
            self.parse_feature_ext_config(m_feature, board_id)
        else:
            print("Unknown feature: " + str(m_feature) + " at board id: " + str(board_id))

    @gen.coroutine
    def parse_definition(self, hw_dict):
        self.volt_refx = 33000
        self.volt_ref = 3.3
        for defin in hw_dict.definitions:
            if defin and (self.neuron.device_name == defin['type']):
                yield self.initialise_cache(defin);
                for m_feature in defin['modbus_features']:
                    self.parse_feature(m_feature)

    def get(self):
        return self.full()


class Board(object):
    def __init__(self, Config, circuit, neuron, versions, major_group=1, dev_id=0, direct_access=False):
        self.alias = ""
        self.devtype = BOARD
        self.dev_id = dev_id
        self.Config = Config
        self.circuit = circuit
        self.direct_access = direct_access
        self.legacy_mode = not (Config.getbooldef('MAIN','use_experimental_api', False))
        self.modbus_address = 0
        self.sw = versions[0]
        self.neuron = neuron
        self.major_group = major_group
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

    @gen.coroutine
    def set(self, alias=None):
        if not alias is None:
            if Devices.add_alias(alias, self, file_update=True):
                self.alias = alias
        return gen.Return(self.full())

    @gen.coroutine
    def initialise_cache(self, cache_definition):
        if cache_definition.has_key('modbus_register_blocks'):
            if self.neuron.modbus_cache_map == None:
                self.neuron.modbus_cache_map = ModbusCacheMap(cache_definition['modbus_register_blocks'], self.neuron)
                yield self.neuron.modbus_cache_map.do_scan(initial=True)
                yield self.neuron.modbus_cache_map.sem.acquire()
                self.neuron.modbus_cache_map.sem.release()
                if (self.hw == 0):
                    self.volt_refx = (3.3 * (1 + self.neuron.modbus_cache_map.get_register(1, 1009)[0]))
                    self.volt_ref = (3.3 * (1 + self.neuron.modbus_cache_map.get_register(1, 1009)[0])) / self.neuron.modbus_cache_map.get_register(1, 5)[0]
            else:
                yield self.neuron.modbus_cache_map.sem.acquire()
                self.neuron.modbus_cache_map.sem.release()
        else:
            raise Exception("HW Definition %s requires Modbus register blocks to be specified" % cache_definition['type'])

    def parse_feature_di(self, max_count, m_feature, board_id):
        counter = 0
        while counter < max_count:
            board_val_reg = m_feature['val_reg']
            board_counter_reg = m_feature['counter_reg']
            board_deboun_reg = m_feature['deboun_reg']
            if m_feature.has_key('ds_modes') and m_feature.has_key('direct_reg') and m_feature.has_key('polar_reg') and m_feature.has_key('toggle_reg'):
                _inp = Input("%s_%02d" % (self.circuit, len(Devices.by_int(INPUT, major_group=m_feature['major_group'])) + 1), self, board_val_reg, 0x1 << (counter % 16),
                             regdebounce=board_deboun_reg + counter, major_group=m_feature['major_group'], regcounter=board_counter_reg + (2 * counter), modes=m_feature['modes'],
                             dev_id=self.dev_id, ds_modes=m_feature['ds_modes'], regmode=m_feature['direct_reg'], regtoggle=m_feature['toggle_reg'],
                             regpolarity=m_feature['polar_reg'], legacy_mode=self.legacy_mode)
            else:
                _inp = Input("%s_%02d" % (self.circuit, len(Devices.by_int(INPUT, major_group=m_feature['major_group'])) + 1), self, board_val_reg, 0x1 << (counter % 16),
                             regdebounce=board_deboun_reg + counter, major_group=m_feature['major_group'], regcounter=board_counter_reg + (2 * counter), modes=m_feature['modes'],
                             dev_id=self.dev_id, legacy_mode=self.legacy_mode)
            if self.neuron.datadeps.has_key(board_val_reg):
                self.neuron.datadeps[board_val_reg]+=[_inp]
            else:
                self.neuron.datadeps[board_val_reg] = [_inp]
            if self.neuron.datadeps.has_key(board_counter_reg + (2 * counter)):
                self.neuron.datadeps[board_counter_reg + (2 * counter)]+=[_inp]
            else:
                self.neuron.datadeps[board_counter_reg + (2 * counter)] = [_inp]
            Devices.register_device(INPUT, _inp)
            counter+=1

    def parse_feature_ro(self, max_count, m_feature, board_id):
        counter = 0
        while counter < max_count:
            board_val_reg = m_feature['val_reg']
            if m_feature['type'] == 'DO' and m_feature['pwm_reg'] and m_feature['pwm_ps_reg'] and m_feature['pwm_c_reg']:
                if not self.legacy_mode:
                    _r = Relay("%s_%02d" % (self.circuit, len(Devices.by_int(RELAY, major_group=m_feature['major_group'])) + 1), self, m_feature['val_coil'] + counter, board_val_reg, 0x1 << (counter % 16),
                               dev_id=self.dev_id, major_group=m_feature['major_group'], pwmcyclereg=m_feature['pwm_c_reg'], pwmprescalereg=m_feature['pwm_ps_reg'], digital_only=True,
                               pwmdutyreg=m_feature['pwm_reg'] + counter, modes=m_feature['modes'], legacy_mode=self.legacy_mode)
                else:
                    _r = Relay("%s_%02d" % (self.circuit, len(Devices.by_int(RELAY, major_group=m_feature['major_group'])) + 1), self, m_feature['val_coil'] + counter, board_val_reg, 0x1 << (counter % 16),
                               dev_id=self.dev_id, major_group=m_feature['major_group'], pwmcyclereg=m_feature['pwm_c_reg'], pwmprescalereg=m_feature['pwm_ps_reg'], digital_only=True,
                               pwmdutyreg=m_feature['pwm_reg'] + counter, modes=m_feature['modes'], legacy_mode=self.legacy_mode)
            else:
                    _r = Relay("%s_%02d" % (self.circuit, len(Devices.by_int(RELAY, major_group=m_feature['major_group'])) + 1), self, m_feature['val_coil'] + counter, board_val_reg, 0x1 << (counter % 16),
                               dev_id=self.dev_id, major_group=m_feature['major_group'], legacy_mode=self.legacy_mode)
            if self.neuron.datadeps.has_key(board_val_reg):
                self.neuron.datadeps[board_val_reg]+=[_r]
            else:
                self.neuron.datadeps[board_val_reg] = [_r]
            Devices.register_device(RELAY, _r)
            counter+=1

    def parse_feature_led(self, max_count, m_feature, board_id):
        counter = 0
        while counter < max_count:
            board_val_reg = m_feature['val_reg']
            _led = ULED("%s_%02d" % (self.circuit, len(Devices.by_int(LED, major_group=m_feature['major_group'])) + 1), self, counter, board_val_reg, 0x1 << (counter % 16), m_feature['val_coil'] + counter,
                        dev_id=self.dev_id, major_group=m_feature['major_group'], legacy_mode=self.legacy_mode)
            if self.neuron.datadeps.has_key(board_val_reg):
                self.neuron.datadeps[board_val_reg]+=[_led]
            else:
                self.neuron.datadeps[board_val_reg] = [_led]
            Devices.register_device(LED, _led)
            counter+=1

    def parse_feature_wd(self, max_count, m_feature, board_id):
        counter = 0
        while counter < max_count:
            board_val_reg = m_feature['val_reg']
            board_timeout_reg = m_feature['timeout_reg']
            _wd = Watchdog("%s_%02d" % (self.circuit, len(Devices.by_int(WATCHDOG, major_group=m_feature['major_group'])) + 1), self, counter, board_val_reg + counter, board_timeout_reg + counter,
                           dev_id=self.dev_id, major_group=m_feature['major_group'], nv_save_coil=m_feature['nv_sav_coil'], reset_coil=m_feature['reset_coil'],
                           legacy_mode=self.legacy_mode)
            if self.neuron.datadeps.has_key(board_val_reg + counter):
                self.neuron.datadeps[board_val_reg + counter]+=[_wd]
            else:
                self.neuron.datadeps[board_val_reg + counter] = [_wd]
            Devices.register_device(WATCHDOG, _wd)
            counter+=1

    def parse_feature_ao(self, max_count, m_feature, board_id):
        counter = 0
        while counter < max_count:
            board_val_reg = m_feature['val_reg']
            if m_feature.has_key('cal_reg'):
                res_val_reg = m_feature['res_val_reg']
                _ao = AnalogOutput("%s_%02d" % (self.circuit, len(Devices.by_int(AO, major_group=m_feature['major_group'])) + 1), self, board_val_reg + counter, regcal=m_feature['cal_reg'],
                                   regmode=m_feature['mode_reg'], reg_res=m_feature['res_val_reg'], modes=m_feature['modes'],
                                   dev_id=self.dev_id, major_group=m_feature['major_group'], legacy_mode=self.legacy_mode)
                if self.neuron.datadeps.has_key(res_val_reg + counter):
                    self.neuron.datadeps[res_val_reg + counter]+=[_ao]
                else:
                    self.neuron.datadeps[res_val_reg + counter] = [_ao]
            else:
                _ao = AnalogOutput("%s_%02d" % (self.circuit, len(Devices.by_int(AO, major_group=m_feature['major_group'])) + 1), self, board_val_reg + counter, dev_id=self.dev_id,
                                   major_group=m_feature['major_group'], legacy_mode=self.legacy_mode)
            if self.neuron.datadeps.has_key(board_val_reg + counter):
                self.neuron.datadeps[board_val_reg + counter]+=[_ao]
            else:
                self.neuron.datadeps[board_val_reg + counter] = [_ao]
            Devices.register_device(AO, _ao)
            counter+=1

    def parse_feature_ai(self, max_count, m_feature, board_id):
        counter = 0
        while counter < max_count:
            board_val_reg = m_feature['val_reg']
            tolerances = m_feature['tolerances']
            if m_feature.has_key('cal_reg'):
                _ai = AnalogInput("%s_%02d" % (self.circuit, len(Devices.by_int(AI, major_group=m_feature['major_group'])) + 1), self, board_val_reg + counter, regcal=m_feature['cal_reg'], regmode=m_feature['mode_reg'],
                                  dev_id=self.dev_id, major_group=m_feature['major_group'], tolerances=tolerances, modes=m_feature['modes'], legacy_mode=self.legacy_mode)
                if self.neuron.datadeps.has_key(board_val_reg + counter):
                    self.neuron.datadeps[board_val_reg + counter] += [_ai]
                else:
                    self.neuron.datadeps[board_val_reg + counter] = [_ai]
            else:
                _ai = AnalogInput("%s_%02d" % (self.circuit, len(Devices.by_int(AI, major_group=m_feature['major_group'])) + 1), self, board_val_reg + counter * 2, regmode=m_feature['mode_reg'] + counter,
                                 dev_id=self.dev_id, major_group=m_feature['major_group'], tolerances=tolerances, modes=m_feature['modes'], legacy_mode=self.legacy_mode)
                if self.neuron.datadeps.has_key(board_val_reg + (counter * 2)):
                    self.neuron.datadeps[board_val_reg + (counter * 2)] += [_ai]
                else:
                    self.neuron.datadeps[board_val_reg + (counter * 2)] = [_ai]
            Devices.register_device(AI, _ai)
            counter+=1

    def parse_feature_register(self, max_count, m_feature, board_id):
        counter = 0
        while counter < max_count:
            board_val_reg = m_feature['start_reg']
            if 'reg_type' in m_feature and m_feature['reg_type'] == 'input':
                _reg = Register("%s_%d_inp" % (self.circuit, board_val_reg + counter), self, counter, board_val_reg + counter, reg_type='input', dev_id=self.dev_id,
                                major_group=m_feature['major_group'], legacy_mode=self.legacy_mode)
            else:
                _reg = Register("%s_%d" % (self.circuit, board_val_reg + counter), self, counter, board_val_reg + counter, dev_id=self.dev_id,
                                major_group=m_feature['major_group'], legacy_mode=self.legacy_mode)
            if board_val_reg and self.neuron.datadeps.has_key(board_val_reg + counter):
                self.neuron.datadeps[board_val_reg + counter] += [_reg]
            elif board_val_reg:
                self.neuron.datadeps[board_val_reg + counter] = [_reg]
            Devices.register_device(REGISTER, _reg)
            counter+=1

    def parse_feature_uart(self, max_count, m_feature, board_id):
        counter = 0
        while counter < max_count:
            board_val_reg = m_feature['conf_reg']
            _uart = Uart("%s_%02d" % (self.circuit, len(Devices.by_int(UART, major_group=m_feature['major_group'])) + 1), self, board_val_reg + counter, dev_id=self.dev_id,
                         major_group=m_feature['major_group'], parity_modes=m_feature['parity_modes'], speed_modes=m_feature['speed_modes'],
                         stopb_modes=m_feature['stopb_modes'], legacy_mode=self.legacy_mode)
            Devices.register_device(UART, _uart)
            counter+=1

    def parse_feature_light_channel(self, max_count, m_feature, board_id):
        counter = 0
        while counter < max_count:
            read_reg = m_feature['read_reg'] + (counter * 3)
            write_reg = m_feature['write_reg'] + (counter * 2)
            status_reg = m_feature['status_reg']
            _light_c = LightChannel("%s_%02d" % (self.circuit, len(Devices.by_int(LIGHT_CHANNEL, major_group=m_feature['major_group'])) + 1),
                                  self, counter, status_reg, 0x1 << counter, read_reg + 1, read_reg, write_reg, read_reg + 2, write_reg + 1, dev_id=self.dev_id,
                                  major_group=m_feature['major_group'], legacy_mode=self.legacy_mode)
            Devices.register_device(LIGHT_CHANNEL, _light_c)
            counter+=1

    def parse_feature(self, m_feature, board_id):
        max_count = m_feature['count']
        if m_feature['type'] == 'DI' and m_feature['major_group'] == board_id:
            self.parse_feature_di(max_count, m_feature, board_id)
        elif (m_feature['type'] == 'RO' or m_feature['type'] == 'DO') and m_feature['major_group'] == board_id:
            self.parse_feature_ro(max_count, m_feature, board_id)
        elif m_feature['type'] == 'LED' and m_feature['major_group'] == board_id:
            self.parse_feature_led(max_count, m_feature, board_id)
        elif m_feature['type'] == 'WD' and m_feature['major_group'] == board_id:
            self.parse_feature_wd(max_count, m_feature, board_id)
        elif m_feature['type'] == 'AO' and m_feature['major_group'] == board_id:
            self.parse_feature_ao(max_count, m_feature, board_id)
        elif m_feature['type'] == 'AI' and m_feature['major_group'] == board_id:
            self.parse_feature_ai(max_count, m_feature, board_id)
        elif m_feature['type'] == 'REGISTER' and m_feature['major_group'] == board_id and self.direct_access:
            self.parse_feature_register(max_count, m_feature, board_id)
        elif m_feature['type'] == 'UART' and m_feature['major_group'] == board_id:
            self.parse_feature_uart(max_count, m_feature, board_id)
        elif m_feature['type'] == 'LIGHT_CHANNEL' and m_feature['major_group'] == board_id:
            self.parse_feature_light

    @gen.coroutine
    def parse_definition(self, hw_dict, board_id):
        self.volt_refx = 33000
        self.volt_ref = 3.3
        if 'model' not in config.up_globals:
            logger.info("NO NEURON EEPROM DATA DETECTED, EXITING")
            logger.info("PLEASE USE A FRESH EVOK IMAGE, OR ENABLE I2C, I2C-DEV AND THE EEPROM OVERLAY")
            exit(-1);
        defin = hw_dict.neuron_definition
        if defin and defin['type'] in config.up_globals['model']:
            yield self.initialise_cache(defin)
            for m_feature in defin['modbus_features']:
                self.parse_feature(m_feature, board_id)

    def get(self):
        return self.full()

class Relay(object):
    pending_id = 0

    PWM_PRESET_MAP = {0:1000, 1:100, 2:0}
    PWM_PRESET_MAP_STRINGS = {0: "1kHz", 1: "100Hz", 2: "Custom"}
    PWM_PRESET_CUSTOM = 0
    def __init__(self, circuit, arm, coil, reg, mask, dev_id=0, major_group=0, pwmcyclereg=-1, pwmprescalereg=-1, pwmdutyreg=-1, presetreg=-1, legacy_mode=True, digital_only=False, modes=['Simple'], presets=[]):
        self.alias = ""
        self.devtype = RELAY
        self.dev_id = dev_id
        self.circuit = circuit
        self.arm = arm
        self.modes = modes
        self.pwmcyclereg = pwmcyclereg
        self.pwmprescalereg = pwmprescalereg
        self.pwmdutyreg = pwmdutyreg
        self.pwmpresetreg = presetreg
        self.pwm_duty = 0
        self.pwm_duty_val = 0
        self.pwm_freq = 0
        self.pwm_cycle_val = 0
        self.pwm_prescale_val = 0
        self.major_group = major_group
        self.legacy_mode = legacy_mode
        self.digital_only = digital_only
        self.coil = coil
        self.valreg = reg
        self.pwm_presets = presets
        self.pwm_preset = -1
        self.bitmask = mask
        self.regvalue = lambda: self.arm.neuron.modbus_cache_map.get_register(1,self.valreg, unit=self.arm.modbus_address)[0]
        if self.pwmdutyreg >= 0: # This instance supports PWM mode
            self.pwm_duty_val = (self.arm.neuron.modbus_cache_map.get_register(1, self.pwmdutyreg, unit=self.arm.modbus_address))[0]
            # With preset
            if self.pwmpresetreg > 0:
                self.pwm_preset = (self.arm.neuron.modbus_cache_map.get_register(1, self.pwmpresetreg, unit=self.arm.modbus_address))[0]
                if Relay.PWM_PRESET_MAP[self.pwm_preset] != Relay.PWM_PRESET_CUSTOM:
                    self.pwm_freq = Relay.PWM_PRESET_MAP[self.pwm_preset]
                else:
                    self.pwm_prescale_val = (self.arm.neuron.modbus_cache_map.get_register(1, self.pwmprescalereg, unit=self.arm.modbus_address))[0]
                    self.pwm_freq = 1000 / (1 + self.pwm_prescale_val)

            # Without preset
            else:
                if self.pwmcyclereg >=0:
                    self.pwm_cycle_val = ((self.arm.neuron.modbus_cache_map.get_register(1, self.pwmcyclereg, unit=self.arm.modbus_address))[0] + 1)
                self.pwm_prescale_val = (self.arm.neuron.modbus_cache_map.get_register(1, self.pwmprescalereg, unit=self.arm.modbus_address))[0]

                if (self.pwm_cycle_val > 0) and (self.pwm_prescale_val > 0):
                    self.pwm_freq = 48000000 / (self.pwm_cycle_val * self.pwm_prescale_val)
                else:
                    self.pwm_freq = 0

            if self.pwm_duty_val == 0:
                self.pwm_duty = 0
                self.mode = 'Simple'  # Mode field is for backward compatibility, will be deprecated soon
            else:
                if pwmcyclereg > 0:
                    self.pwm_duty = (100 / (float(self.pwm_cycle_val) / float(self.pwm_duty_val)))
                    self.pwm_duty = round(self.pwm_duty ,1) if self.pwm_duty % 1 else int(self.pwm_duty)
                else:
                    self.pwm_duty = self.pwm_duty_val

                self.mode = 'PWM'  # Mode field is for backward compatibility, will be deprecated soon
        else: # This RELAY instance does not support PWM mode (no pwmdutyreg given)
            self.mode = 'Simple'

        self.forced_changes = arm.neuron.Config.getbooldef("MAIN", "force_immediate_state_changes", False)


    def full(self, forced_value=None):
        ret =  {'dev': 'relay',
                'relay_type': 'physical',
                'circuit': self.circuit,
                'value': self.value,
                'pending': self.pending_id != 0,
                'mode': self.mode,
                'modes': self.modes,
                'glob_dev_id': self.dev_id}
        if self.digital_only:
            ret['relay_type'] = 'digital'
            ret['pwm_freq'] = self.pwm_freq
            ret['pwm_duty'] = self.pwm_duty
        if self.pwmpresetreg > 0:
            ret['pwm_preset'] = Relay.PWM_PRESET_MAP_STRINGS[self.pwm_preset]
            ret['pwm_presets'] = self.pwm_presets
        if self.alias != '':
            ret['alias'] = self.alias
        if forced_value is not None:
            ret['value'] = forced_value
        return ret

    def simple(self):
        return {'dev': 'relay',
                'circuit': self.circuit,
                'value': self.value}

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
        yield self.arm.neuron.client.write_coil(self.coil, 1 if value else 0, unit=self.arm.modbus_address)
        raise gen.Return(1 if value else 0)

    def value_delta(self, new_val):
        return (self.regvalue() ^ new_val) & self.bitmask

    @gen.coroutine
    def set(self, value=None, timeout=None, mode=None, pwm_freq=None, pwm_duty=None, alias=None):
        """ Sets new on/off status. Disable pending timeouts
        """
        if self.pending_id:
            IOLoop.instance().remove_timeout(self.pending_id)
            self.pending_id = None

        #if pwm_duty is not None and self.mode == 'PWM' and float(pwm_duty) <= 0.01:
        #    mode = 'Simple'
        # New system - mode field will no longer be used

        # Set PWM Freq
        if (pwm_freq is not None) and (float(pwm_freq) > 0):
            self.pwm_freq = pwm_freq;


            if self.pwmcyclereg > 0:
                self.pwm_delay_val = 48000000 / float(pwm_freq)
                if ((int(self.pwm_delay_val) % 50000) == 0) and ((self.pwm_delay_val / 50000) < 65535):
                    self.pwm_cycle_val = 50000
                    self.pwm_prescale_val = self.pwm_delay_val / 50000
                elif ((int(self.pwm_delay_val) % 10000) == 0) and ((self.pwm_delay_val / 10000) < 65535):
                    self.pwm_cycle_val = 10000
                    self.pwm_prescale_val = self.pwm_delay_val / 10000
                elif ((int(self.pwm_delay_val) % 5000) == 0) and ((self.pwm_delay_val / 5000) < 65535):
                    self.pwm_cycle_val = 5000
                    self.pwm_prescale_val = self.pwm_delay_val / 5000
                elif ((int(self.pwm_delay_val) % 1000) == 0) and ((self.pwm_delay_val / 1000) < 65535):
                    self.pwm_cycle_val = 1000
                    self.pwm_prescale_val = self.pwm_delay_val / 1000
                else:
                    self.pwm_prescale_val = sqrt(self.pwm_delay_val)
                    self.pwm_cycle_val = self.pwm_prescale_val

                if self.pwm_duty > 0:
                    self.pwm_duty_val = float(self.pwm_cycle_val) * float(float(self.pwm_duty) / 100.0)
                #else:
                #    self.pwm_duty_val = 0
                #    self.arm.neuron.client.write_register(self.pwmdutyreg, self.pwm_duty_val, unit=self.arm.modbus_address)

                self.arm.neuron.client.write_register(self.pwmcyclereg, self.pwm_cycle_val - 1, unit=self.arm.modbus_address)
                self.arm.neuron.client.write_register(self.pwmprescalereg, self.pwm_prescale_val, unit=self.arm.modbus_address)
                self.arm.neuron.client.write_register(self.pwmdutyreg, self.pwm_duty_val, unit=self.arm.modbus_address)

                other_devs = Devices.by_int(RELAY, major_group=self.major_group)  # All PWM outs in the same group share this registers
                for other_dev in other_devs:
                    if other_dev.pwm_duty > 0:
                        other_dev.pwm_freq = self.pwm_freq
                        other_dev.pwm_delay_val = self.pwm_delay_val
                        other_dev.pwm_cycle_val = self.pwm_cycle_val
                        other_dev.pwm_prescale_val = self.pwm_prescale_val
                        yield other_dev.set(pwm_duty=other_dev.pwm_duty)

            if self.pwmpresetreg > 0:
                # IF wanted freq is one of preset options
                for preset, freq in Relay.PWM_PRESET_MAP.iteritems():
                    if int(pwm_freq) == freq:
                        self.pwm_preset = preset
                        self.arm.neuron.client.write_register(self.pwmpresetreg, self.pwm_preset,
                                                              unit=self.arm.modbus_address)
                        break

                other_devs = Devices.by_int(RELAY, major_group=self.major_group)  # All PWM outs in the same group share this registers
                for other_dev in other_devs:
                    if other_dev.pwm_duty > 0:
                        other_dev.pwm_freq = self.pwm_freq
                        other_dev.pwm_preset = self.pwm_preset
                        other_dev.pwm_prescale_val = self.pwm_prescale_val
                        yield other_dev.set(pwm_duty=other_dev.pwm_duty)

        # Set Binary value
        if value is not None:
            parsed_value = 1 if int(value) else 0

            if pwm_duty is not None:
                if (pwm_duty == 100 and parsed_value == 1) or (pwm_duty == 0 and parsed_value == 0): # No conflict in this case
                    pass
                else:
                    raise Exception('Set value conflict: Cannot set both value and pwm_duty at once.')

            if not (timeout is None):
                timeout = float(timeout)

            self.mode = 'Simple'
            self.arm.neuron.client.write_coil(self.coil, parsed_value, unit=self.arm.modbus_address)
            if self.pwm_duty != 0:
                self.pwm_duty = 0
                self.arm.neuron.client.write_register(self.pwmdutyreg, self.pwm_duty, unit=self.arm.modbus_address) # Turn off PWM

        # Set PWM Duty
        elif pwm_duty is not None and 0.0 <= float(pwm_duty) <= 100.0:
            self.pwm_duty = pwm_duty
            if self.pwmcyclereg > 0:
                self.pwm_duty_val = float(self.pwm_cycle_val) * float(float(self.pwm_duty) / 100.0)
            else:
                self.pwm_duty_val = int(self.pwm_duty)

            if self.value != 0:
                self.arm.neuron.client.write_coil(self.coil, 0, unit=self.arm.modbus_address)
            self.arm.neuron.client.write_register(self.pwmdutyreg, self.pwm_duty_val, unit=self.arm.modbus_address)
            self.mode = 'PWM'

        if alias is not None:
            if Devices.add_alias(alias, self, file_update=True):
                self.alias = alias

        if timeout is None:
            if (value is not None) and self.forced_changes:
                raise gen.Return(self.full(forced_value=parsed_value))
            else:
                raise gen.Return(self.full())

        def timercallback():
            self.pending_id = None
            self.arm.neuron.client.write_coil(self.coil, 0 if value else 1, unit=self.arm.modbus_address)

        self.pending_id = IOLoop.instance().add_timeout(
            datetime.timedelta(seconds=float(timeout)), timercallback)

        if (value is not None) and self.forced_changes:
            raise gen.Return(self.full(forced_value=parsed_value))
        else:
            raise gen.Return(self.full())

    def get(self):
        return self.full()

class ULED(object):
    def __init__(self, circuit, arm, post, reg, mask, coil, dev_id=0, major_group=0, legacy_mode=True):
        self.alias = ""
        self.devtype = LED
        self.dev_id = dev_id
        self.circuit = circuit
        self.arm = arm
        self.major_group = major_group
        self.legacy_mode = legacy_mode
        self.bitmask = mask
        self.valreg = reg
        self.regvalue = lambda: self.arm.neuron.modbus_cache_map.get_register(1, self.valreg, unit=self.arm.modbus_address)[0]
        self.coil = coil

    def full(self):
        ret = {'dev': 'led', 'circuit': self.circuit, 'value': self.value, 'glob_dev_id': self.dev_id}
        if self.alias != '':
            ret['alias'] = self.alias
        return ret


    def simple(self):
        return {'dev': 'led', 'circuit': self.circuit, 'value': self.value}

    @property
    def value(self):
        try:
            if self.regvalue() & self.bitmask: return 1
        except:
            pass
        return 0

    def value_delta(self, new_val):
        return (self.regvalue() ^ new_val) & self.bitmask

    def get_state(self):
        """ Returns ( status, is_pending )
              current on/off status is taken from last mcp value without reading it from hardware
              is_pending is Boolean
        """
        return (self.value)

    @gen.coroutine
    def set_state(self, value):
        """ Sets new on/off status. Disable pending timeouts
        """
        yield self.arm.neuron.client.write_coil(self.coil, 1 if value else 0, unit=self.arm.modbus_address)
        raise gen.Return(1 if value else 0)

    @gen.coroutine
    def set(self, value=None, alias=None):
        """ Sets new on/off status. Disable pending timeouts
        """
        if alias is not None:
            
            if Devices.add_alias(alias, self, file_update=True):
                self.alias = alias
        if value is not None:
            value = int(value)
            self.arm.neuron.client.write_coil(self.coil, 1 if value else 0, unit=self.arm.modbus_address)
        raise gen.Return(self.full())

    def get(self):
        return self.full()

class LightDevice(object):
    def __init__(self, circuit, arm, bus, dev_id=0):
        self.alias = ""
        self.devtype = LIGHT_DEVICE
        self.dev_id = dev_id

    def full(self):
        ret = {'dev': 'light_channel', 'circuit': self.circuit, 'glob_dev_id': self.dev_id}
        if self.alias != '':
            ret['alias'] = self.alias
        return ret

    def get(self):
        return self.full()

class LightChannel(object):
    def __init__(self, circuit, arm, bus_number, reg_status, status_mask, reg_transmit, reg_receive, reg_receive_counter, reg_config_transmit, reg_config_receive, dev_id=0, major_group=0, legacy_mode=True):
        self.alias = ""
        self.devtype = LIGHT_CHANNEL
        self.dev_id = dev_id
        self.circuit = circuit
        self.arm = arm
        self.major_group = major_group
        self.legacy_mode = legacy_mode
        self.reg_status = reg_status
        self.bus_number = bus_number
        self.status_mask = status_mask
        self.reg_transmit = reg_transmit
        self.reg_receive = reg_receive
        self.reg_receive_counter = reg_receive_counter
        self.reg_config_transmit = reg_config_transmit
        self.reg_config_receive = reg_config_receive
        self.broadcast_commands = ["recall_max_level", "recall_min_level", "off", "up", "down", "step_up", "step_down", "step_down_and_off",
                                   "turn_on_and_step_up", "DAPC", "reset", "identify_device", "DTR0", "DTR1", "DTR2"]
        self.group_commands = ["recall_max_level", "recall_min_level", "off", "up", "down", "step_up", "step_down", "step_down_and_off",
                               "turn_on_and_step_up", "DAPC", "reset", "identify_device"]
        self.scan_types = ["assigned", "unassigned"]
        self.light_driver = SyncUnipiDALIDriver(self.bus_number)
        #self.light_driver.logger = logger
        #self.light_driver.debug = True
        self.light_bus = Bus(self.circuit, self.light_driver)

    def full(self):
        ret = {'dev': 'light_channel', 'circuit': self.circuit, 'glob_dev_id': self.dev_id, 'broadcast_commands': self.broadcast_commands,
               'group_commands': self.group_commands, 'scan_types': self.scan_types}
        if self.alias != '':
            ret['alias'] = self.alias
        return ret


    def get(self):
        return self.full()

    def simple(self):
        return {'dev': 'light_channel', 'circuit': self.circuit}

    @gen.coroutine
    def set(self, broadcast_command=None, broadcast_argument=None, group_command=None, group_address=None, group_argument=None, scan=None, alias=None):
        """ Sets new on/off status. Disable pending timeouts
        """
        if alias is not None:
            if Devices.add_alias(alias, self):
                self.alias = alias
        if scan is not None and scan is self.scan_types:
            try:
                self.light_bus.assign_short_addresses()
            except Exception, E:
                logger.exception(str(E))
        elif broadcast_command is not None:
            if broadcast_command == "recall_max_level":
                command = dali.gear.general.RecallMaxLevel(Broadcast())
            elif broadcast_command == "recall_min_level":
                command = dali.gear.general.RecallMinLevel(Broadcast())
            elif broadcast_command == "off":
                command = dali.gear.general.Off(Broadcast())
            elif broadcast_command == "up":
                command = dali.gear.general.Up(Broadcast())
            elif broadcast_command == "down":
                command = dali.gear.general.Down(Broadcast())
            elif broadcast_command == "step_up":
                command = dali.gear.general.StepUp(Broadcast())
            elif broadcast_command == "step_down":
                command = dali.gear.general.StepDown(Broadcast())
            elif broadcast_command == "step_down_and_off":
                command = dali.gear.general.StepDownAndOff(Broadcast())
            elif broadcast_command == "turn_on_and_step_up":
                command = dali.gear.general.OnAndStepUp(Broadcast())
            elif broadcast_command == "DAPC" and broadcast_argument is not None:
                if broadcast_argument == "MASK" or broadcast_argument == "OFF":
                    command = dali.gear.general.DAPC(Broadcast(), broadcast_argument)
                else:
                    command = dali.gear.general.DAPC(Broadcast(), int(broadcast_argument))
            elif broadcast_command == "reset":
                command = dali.gear.general.Reset(Broadcast())
            elif broadcast_command == "identify_device":
                command = dali.gear.general.IdentifyDevice(Broadcast())
            elif broadcast_command == "DTR0":
                command = dali.gear.general.DTR0(int(broadcast_argument))
            elif broadcast_command == "DTR1":
                command = dali.gear.general.DTR1(int(broadcast_argument))
            elif broadcast_command == "DTR2":
                command = dali.gear.general.DTR2(int(broadcast_argument))
            else:
                raise Exception("Invalid lighting broadcast command: %d" % broadcast_command)
            self.light_driver.logger = logger
            self.light_driver.debug = True
            print('Response: {}'.format(self.light_driver.send(command)))
        elif group_command is not None:
            if group_command == "recall_max_level":
                command = dali.gear.general.RecallMaxLevel(Group(group_address))
            elif group_command == "recall_min_level":
                command = dali.gear.general.RecallMinLevel(Group(group_address))
            elif group_command == "off":
                command = dali.gear.general.Off(Group(group_address))
            elif group_command == "up":
                command = dali.gear.general.Up(Group(group_address))
            elif group_command == "down":
                command = dali.gear.general.Down(Group(group_address))
            elif group_command == "step_up":
                command = dali.gear.general.StepUp(Group(group_address))
            elif group_command == "step_down":
                command = dali.gear.general.StepDown(Group(group_address))
            elif group_command == "step_down_and_off":
                command = dali.gear.general.StepDownAndOff(Group(group_address))
            elif group_command == "turn_on_and_step_up":
                command = dali.gear.general.OnAndStepUp(Group(group_address))
            elif group_command == "DAPC" and group_argument is not None:
                if group_argument == "MASK" or group_argument == "OFF":
                    command = dali.gear.general.DAPC(Group(group_address), group_argument)
                else:
                    command = dali.gear.general.DAPC(Group(group_address), int(group_argument))
            elif group_command == "reset":
                command = dali.gear.general.Reset(Group(group_address))
            elif group_command == "identify_device":
                command = dali.gear.general.IdentifyDevice(Group(group_address))
            else:
                raise Exception("Invalid lighting broadcast command (and/or required argument was not provided): %d" % group_command)
            self.light_driver.logger = logger
            self.light_driver.debug = True
            print('Response: {}'.format(self.light_driver.send(command)))
        raise gen.Return(self.full())



class Watchdog(object):
    def __init__(self, circuit, arm, post, reg, timeout_reg, nv_save_coil=-1, reset_coil=-1, wd_reset_ro_coil=-1, dev_id=0, major_group=0, legacy_mode=True):
        self.alias = ""
        self.devtype = WATCHDOG
        self.dev_id = dev_id
        self.circuit = circuit
        self.arm = arm
        self.major_group = major_group
        self.legacy_mode = legacy_mode
        self.timeoutvalue = lambda: self.arm.neuron.modbus_cache_map.get_register(1, self.toreg, unit=self.arm.modbus_address)
        self.regvalue = lambda: self.arm.neuron.modbus_cache_map.get_register(1, self.toreg, unit=self.arm.modbus_address)[0]
        self.nvsavvalue = 0
        self.resetvalue = 0
        self.nv_save_coil = nv_save_coil
        self.reset_coil = reset_coil
        self.wd_reset_ro_coil = wd_reset_ro_coil
        self.wdwasresetvalue = 0
        self.valreg = reg
        self.toreg = timeout_reg

    def full(self):
        ret = {'dev': 'wd',
               'circuit': self.circuit,
               'value': self.value,
               'timeout': self.timeout[0],
               'was_wd_reset': self.was_wd_boot_value,
               'nv_save' :self.nvsavvalue,
               'glob_dev_id': self.dev_id}
        if self.alias != '':
            ret['alias'] = self.alias
        return ret

    def get(self):
        return self.full()

    def simple(self):
        return {'dev': 'wd',
                'circuit': self.circuit,
                'value': self.regvalue()}

    def value_delta(self, new_val):
        return (self.regvalue() ^ new_val) & 0x03 #Only the two lowest bits contains watchdog status

    @property
    def value(self):
        try:
            if self.regvalue() & self.bitmask: return 1
        except:
            pass
        return 0

    @property
    def timeout(self):
        try:
            if self.timeoutvalue(): return self.timeoutvalue()
        except:
            pass
        return 0

    @property
    def was_wd_boot_value(self):
        try:
            if self.regvalue() & 0b10: return 1
        except:
            pass
        return 0

    def get_state(self):
        """ Returns ( status, is_pending )
              current on/off status is taken from last mcp value without reading it from hardware
              is_pending is Boolean
        """
        return (self.value, self.timeout)

    @gen.coroutine
    def set_state(self, value):
        """ Sets new on/off status. Disable pending timeouts
        """
        self.arm.neuron.client.write_register(self.valreg, 1 if value else 0, unit=self.arm.modbus_address)
        raise gen.Return(1 if value else 0)

    @gen.coroutine
    def set(self, value=None, timeout=None, reset=None, nv_save=None, alias=None):
        """ Sets new on/off status. Disable pending timeouts
        """
        if alias is not None:
            if Devices.add_alias(alias, self, file_update=True):
                self.alias = alias

        if self.nv_save_coil >= 0 and nv_save is not None and nv_save != self.nvsavvalue:
            if nv_save != 0:
                self.nvsavvalue = 1
            else:
                self.nvsavvalue = 0
            self.arm.neuron.client.write_coil(self.nv_save_coil, 1, unit=self.arm.modbus_address)

        if value is not None:
            value = int(value)
            self.arm.neuron.client.write_register(self.valreg, 1 if value else 0, unit=self.arm.modbus_address)

        if not (timeout is None):
            timeout = int(timeout)
            if timeout > 65535:
                timeout = 65535
            self.arm.neuron.client.write_register(self.toreg, timeout, unit=self.arm.modbus_address)

        if self.reset_coil >= 0 and reset is not None:
            if reset != 0:
                self.nvsavvalue = 0
                self.arm.neuron.client.write_coil(self.reset_coil, 1, unit=self.arm.modbus_address)
                logger.info("Performed reset of board %s" % self.circuit)

        raise gen.Return(self.full())



class ExtConfig(object):

    def __init__(self, circuit, arm, reg_groups, dev_id=0):

        self._alias = ""
        self._devtype = EXT_CONFIG
        self.circuit = circuit
        self._reg_map = {}
        self._dev_id = dev_id
        self._arm = arm
        self._params = {}
        self.post_write = reg_groups.get("post_write_coils", None)

        for reg_block in reg_groups['reg_blocks']:
            reg_base_addr = reg_block['start_reg']
            if reg_block['count'] > 1: # Array of registers
                for reg_offset in range(reg_block['count']):
                    self._params["{}_{}".format(reg_block['name'], reg_offset + 1)] = reg_base_addr + reg_offset
            else: # Single register only
                    self._params[reg_block['name']] = reg_base_addr

    def __getattr__(self, name):

        if name in self._params:
            return self.get_param(name)
        else:
            raise AttributeError("Parameter {} not found in {}".format(name, self.circuit))

    def full(self):

        ret = self.simple()
        ret['glob_dev_id'] = self._dev_id

        if self._alias != '':
            ret['alias'] = self._alias

        return ret

    def simple(self):
        ret = {'dev': 'ext_config',
                'circuit': self.circuit}

        for (param, reg_addr) in self._params.items():
            ret[param] = self._arm.neuron.modbus_cache_map.get_register(1, reg_addr, unit=self._arm.modbus_address, is_input=False)[0]

        return ret

    def get_param(self, par_name):
        return self._arm.neuron.modbus_cache_map.get_register(1, self._params[par_name], unit=self._arm.modbus_address, is_input=False)[0]

    def get(self):
        return self.full()

    def get_state(self):
        """ Returns ( status, is_pending )
              current on/off status is taken from last mcp value without reading it from hardware
              is_pending is Boolean
        """
        return (self.value)

    @gen.coroutine
    def set(self, alias=None, **kwargs):
        """ Sets new on/off status. Disable pending timeouts """
        if alias is not None:
            if Devices.add_alias(alias, self, file_update=True):
                self.alias = alias

        if len(kwargs) > 0:

            for param, value in kwargs.items():
                self._arm.neuron.client.write_register(self._params[param], int(value), unit=self._arm.modbus_address)

            if isinstance(self.post_write, list):
                for coil in self.post_write:
                    self._arm.neuron.client.write_coil(coil, 1, unit=self._arm.modbus_address)

        raise gen.Return(self.full())


class UnitRegister():

    def __init__(self, circuit, arm, reg, reg_type="input", dev_id=0, major_group=0, datatype=None, unit=None, offset=0, factor=1, valid_mask=None, name=None, post_write=None):
        # TODO - valid mask reg
        self.alias = ""
        self.devtype = UNIT_REGISTER
        self.dev_id = dev_id
        self.circuit = circuit
        self.arm = arm
        self.major_group = major_group
        self.valreg = reg
        self.offset = offset
        self.factor = factor
        self.unit = unit
        self.name = name
        self.post_write = post_write
        self.datatype = datatype

        if reg_type == "input":
            _is_iput = True
        else:
            _is_iput = False

        if valid_mask is not None:
            self.valid_mask = lambda: self.arm.neuron.modbus_cache_map.get_register(1, valid_mask, unit=self.arm.modbus_address, is_input=_is_iput)[0]
        else:
            self.valid_mask = None

        if self.datatype is None or self.datatype == "unsigned16":
            if factor == 1 and offset == 0: # Reading RAW value - save some CPU time
                self.regvalue = lambda: self.arm.neuron.modbus_cache_map.get_register(1, self.valreg, unit=self.arm.modbus_address, is_input=_is_iput)[0]
            else:
                self.regvalue = lambda: (self.arm.neuron.modbus_cache_map.get_register(1, self.valreg, unit=self.arm.modbus_address, is_input=_is_iput)[0] * self.factor) + self.offset

        elif self.datatype == "signed16":
                self.regvalue = lambda: (self.__parse_signed(self.arm.neuron.modbus_cache_map.get_register(1, self.valreg, unit=self.arm.modbus_address, is_input=_is_iput)[0]) * self.factor) + self.offset

        elif self.datatype == "float32":
            # TODO - add factor and offset version
            self.regvalue = lambda: self.__parse_float32(self.arm.neuron.modbus_cache_map.get_register(2, self.valreg, unit=self.arm.modbus_address, is_input=_is_iput))

    def __parse_signed(self, raw_value):
        return (raw_value - 65536 if raw_value > 32767 else raw_value)

    def __parse_float32(self, raw_regs):
        datal = bytearray(4)
        datal[1] = raw_regs[0] & 0xFF
        datal[0] = (raw_regs[0] >> 8) & 0xFF
        datal[3] = raw_regs[1] & 0xFF
        datal[2] = (raw_regs[1] >> 8) & 0xFF

        return struct.unpack_from('>f', datal)[0]

    @gen.coroutine
    def set(self, value=None, alias=None, **kwargs):
        """ Sets new on/off status. Disable pending timeouts """
        if alias is not None:
            if Devices.add_alias(alias, self, file_update=True):
                self.alias = alias

        raise Exception("Unit_register object is read-only")

    def full(self):

        ret = {'dev': 'unit_register',
               'circuit': self.circuit,
               'value': (self.regvalue()),
               'glob_dev_id': self.dev_id}

        if self.name is not None:
            ret['name'] = self.name

        if self.valid_mask is not None:
            ret['valid'] = "true" if (self.valid_mask() & (1 << self.valreg - 1)) != 0 else "false"

        if self.unit is not None:
            ret['unit'] = self.unit

        if self.alias != '':
            ret['alias'] = self.alias
        return ret

    def simple(self):
        return {'dev': 'unit_register',
                'circuit': self.circuit,
                'value': self.regvalue()}

    @property
    def value(self):
        try:
            if self.regvalue():
                return self.regvalue()
        except:
            pass
        return 0

    def get(self):
        return self.full()

    def get_state(self):
        """ Returns ( status, is_pending )
              current on/off status is taken from last mcp value without reading it from hardware
              is_pending is Boolean
        """
        return (self.value)

class Register():
    def __init__(self, circuit, arm, post, reg, reg_type="holding", dev_id=0, major_group=0, legacy_mode=True):
        self.alias = ""
        self.devtype = REGISTER
        self.dev_id = dev_id
        self.circuit = circuit
        self.arm = arm
        self.major_group = major_group
        self.legacy_mode = legacy_mode
        self.valreg = reg
        self.reg_type = reg_type
        if reg_type == "input":
            self.regvalue = lambda: self.arm.neuron.modbus_cache_map.get_register(1, self.valreg, unit=self.arm.modbus_address, is_input=True)[0]
        else:
            self.regvalue = lambda: self.arm.neuron.modbus_cache_map.get_register(1, self.valreg, unit=self.arm.modbus_address, is_input=False)[0]

    def full(self):
        ret = {'dev': 'register',
               'circuit': self.circuit,
               'value': self.regvalue(),
               'glob_dev_id': self.dev_id}
        if self.alias != '':
            ret['alias'] = self.alias
        return ret

    def simple(self):
        return {'dev': 'register',
                'circuit': self.circuit,
                'value': self.regvalue()}

    @property
    def value(self):
        try:
            if self.regvalue():
                return self.regvalue()
        except:
            pass
        return 0


    def get(self):
        return self.full()

    def get_state(self):
        """ Returns ( status, is_pending )
              current on/off status is taken from last mcp value without reading it from hardware
              is_pending is Boolean
        """
        return (self.value)

    @gen.coroutine
    def set_state(self, value):
        """ Sets new on/off status. Disable pending timeouts
        """
        self.arm.neuron.client.write_register(self.valreg, value if value else 0, unit=self.arm.modbus_address)
        raise gen.Return(value if value else 0)

    @gen.coroutine
    def set(self, value=None, alias=None):
        """ Sets new on/off status. Disable pending timeouts
        """
        if alias is not None:
            if Devices.add_alias(alias, self, file_update=True):
                self.alias = alias
        if value is not None:
            value = int(value)
            self.arm.neuron.client.write_register(self.valreg, value if value else 0, unit=self.arm.modbus_address)

        raise gen.Return(self.full())

class Input():
    def __init__(self, circuit, arm, reg, mask, regcounter=None, regdebounce=None, regmode=None, regtoggle=None, regpolarity=None,
                 dev_id=0, major_group=0, modes=['Simple'], ds_modes=['Simple'], counter_modes=['Enabled', 'Disabled'], legacy_mode=True):
        self.alias = ""
        self.devtype = INPUT
        self.dev_id = dev_id
        self.circuit = circuit
        self.arm = arm
        self.modes = modes
        self.ds_modes = ds_modes
        self.counter_modes = counter_modes
        self.major_group = major_group
        self.legacy_mode = legacy_mode
        self.bitmask = mask
        self.regcounter = regcounter
        self.regdebounce = regdebounce
        self.regmode = regmode
        self.regtoggle = regtoggle
        self.regpolarity = regpolarity
        self.reg = reg
        self.regvalue = lambda: self.arm.neuron.modbus_cache_map.get_register(1, self.reg, unit=self.arm.modbus_address)[0]
        self.regcountervalue = self.regdebouncevalue = lambda: None
        if not (regcounter is None): self.regcountervalue = lambda: self.arm.neuron.modbus_cache_map.get_register(1, regcounter, unit=self.arm.modbus_address)[0] + (self.arm.neuron.modbus_cache_map.get_register(1, regcounter + 1, unit=self.arm.modbus_address)[0] << 16)
        if not (regdebounce is None): self.regdebouncevalue = lambda: self.arm.neuron.modbus_cache_map.get_register(1, regdebounce, unit=self.arm.modbus_address)[0]
        self.mode = 'Simple'
        self.ds_mode = 'Simple'
        if 'DirectSwitch' in self.modes:
            curr_ds = self.arm.neuron.modbus_cache_map.get_register(1, self.regmode, unit=self.arm.modbus_address)[0]
            if (curr_ds & self.bitmask) > 0:
                self.mode = 'DirectSwitch'
                curr_ds_pol = self.arm.neuron.modbus_cache_map.get_register(1, self.regpolarity, unit=self.arm.modbus_address)[0]
                curr_ds_tgl = self.arm.neuron.modbus_cache_map.get_register(1, self.regtoggle, unit=self.arm.modbus_address)[0]
                if (curr_ds_pol & self.bitmask):
                    self.ds_mode = 'Inverted'
                elif (curr_ds_tgl & self.bitmask):
                    self.ds_mode = 'Toggle'
        self.counter_mode = "Enabled"

    @property
    def debounce(self):
        try:
            return self.regdebouncevalue()
        except:
            pass
        return 0

    @property
    def value(self):
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

    def value_delta(self, new_val):
        return (self.regvalue() ^ new_val) & self.bitmask

    def full(self):
        ret = {'dev': 'input',
               'circuit': self.circuit,
               'value': self.value,
               'debounce': self.debounce,
               'counter_modes': self.counter_modes,
               'counter_mode': self.counter_mode,
               'counter': self.counter if self.counter_mode == 'Enabled' else 0,
               'mode': self.mode,
               'modes': self.modes,
               'glob_dev_id': self.dev_id }
        if self.mode == 'DirectSwitch':
            ret['ds_mode'] = self.ds_mode
            ret['ds_modes'] = self.ds_modes
        if self.alias != '':
            ret['alias'] = self.alias
        return ret


    def simple(self):
        if self.counter_mode == 'Enabled':
            return {'dev': 'input',
                    'circuit': self.circuit,
                    'value': self.value,
                    'counter': self.counter}
        else:
            return {'dev': 'input',
                    'circuit': self.circuit,
                    'value': self.value}

    @gen.coroutine
    def set(self, debounce=None, mode=None, counter=None, counter_mode=None, ds_mode=None, alias=None):
        if alias is not None:
            if Devices.add_alias(alias, self, file_update=True):
                self.alias = alias

        if mode is not None and mode != self.mode and mode in self.modes:
            self.mode = mode
            if self.mode == 'DirectSwitch':
                curr_ds = yield self.arm.neuron.modbus_cache_map.get_register_async(1, self.regmode, unit=self.arm.modbus_address)
                curr_ds_val = curr_ds[0]
                curr_ds_val = curr_ds_val | int(self.bitmask)
                yield self.arm.neuron.client.write_register(self.regmode, curr_ds_val, unit=self.arm.modbus_address)
            else:
                curr_ds = yield self.arm.neuron.modbus_cache_map.get_register_async(1, self.regmode, unit=self.arm.modbus_address)
                curr_ds_val = curr_ds[0]
                curr_ds_val = curr_ds_val & (~int(self.bitmask))
                yield self.arm.neuron.client.write_register(self.regmode, curr_ds_val, unit=self.arm.modbus_address)

        if self.mode == 'DirectSwitch' and ds_mode is not None and ds_mode in self.ds_modes:
            self.ds_mode = ds_mode
            curr_ds_pol = yield self.arm.neuron.modbus_cache_map.get_register_async(1, self.regpolarity, unit=self.arm.modbus_address)
            curr_ds_tgl = yield self.arm.neuron.modbus_cache_map.get_register_async(1, self.regtoggle, unit=self.arm.modbus_address)
            curr_ds_pol_val = curr_ds_pol[0]
            curr_ds_tgl_val = curr_ds_tgl[0]
            if self.ds_mode == 'Inverted':
                curr_ds_pol_val = curr_ds_pol_val | self.bitmask
                curr_ds_tgl_val = curr_ds_tgl_val & (~self.bitmask)
            elif self.ds_mode == 'Toggle':
                curr_ds_pol_val = curr_ds_pol_val & (~self.bitmask)
                curr_ds_tgl_val = curr_ds_tgl_val | self.bitmask
            else:
                curr_ds_pol_val = curr_ds_pol_val & (~self.bitmask)
                curr_ds_tgl_val = curr_ds_tgl_val & (~self.bitmask)
            yield self.arm.neuron.client.write_register(self.regpolarity, curr_ds_pol_val, unit=self.arm.modbus_address)
            yield self.arm.neuron.client.write_register(self.regtoggle, curr_ds_tgl_val, unit=self.arm.modbus_address)

        if counter_mode is not None and counter_mode in self.counter_modes and counter_mode != self.counter_mode:
            self.counter_mode = counter_mode

        if debounce is not None:
            if self.regdebounce is not None:
                yield self.arm.neuron.client.write_register(self.regdebounce, int(float(debounce)), unit=self.arm.modbus_address)
        if counter is not None:
            if self.regcounter is not None:
                yield self.arm.neuron.client.write_registers(self.regcounter, ((int(float(counter)) & 0xFFFF), (int(float(counter)) >> 16) & 0xFFFF), unit=self.arm.modbus_address)
        raise gen.Return(self.full())

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

class Uart():
    def __init__(self, circuit, arm, reg, dev_id=0, parity_modes=['None'], speed_modes=['19200bps'], stopb_modes = ['One'],
                 address_reg=-1, major_group=0, legacy_mode=True):
        self.alias = ""
        self.devtype = UART
        self.dev_id = dev_id
        self.circuit = circuit
        self.legacy_mode = legacy_mode
        self.arm = arm
        self.parity_modes = parity_modes
        self.speed_modes = speed_modes
        self.stopb_modes = stopb_modes
        self.speed_mask  = 0x0001000f         # Termios mask
        self.parity_mask = 0x00000300         # Termios mask
        self.stopb_mask  = 0x00000040         # Termios mask
        self.major_group = major_group
        self.valreg = reg
        self.address_reg = address_reg
        self.regvalue = lambda: self.arm.neuron.modbus_cache_map.get_register(1, self.valreg, unit=self.arm.modbus_address)[0]
        parity_mode_val = (self.arm.neuron.modbus_cache_map.get_register(1, self.valreg, unit=self.arm.modbus_address)[0]) & self.parity_mask
        speed_mode_val = (self.arm.neuron.modbus_cache_map.get_register(1, self.valreg, unit=self.arm.modbus_address)[0]) & self.speed_mask
        stopb_mode_val = (self.arm.neuron.modbus_cache_map.get_register(1, self.valreg, unit=self.arm.modbus_address)[0]) & self.stopb_mask
        if self.address_reg != -1:
            self.address_val = self.arm.neuron.modbus_cache_map.get_register(1, self.address_reg, unit=self.arm.modbus_address)[0]
            self.addressvalue = lambda: self.arm.neuron.modbus_cache_map.get_register(1, self.address_reg, unit=self.arm.modbus_address)[0]
        else:
            self.address_val = 0
            self.addressvalue = None

        if parity_mode_val == 0x00000300:
            self.parity_mode = 'Odd'
        elif parity_mode_val == 0x00000200:
            self.parity_mode = 'Even'
        else:
            self.parity_mode = 'None'

        if speed_mode_val == 0x0000000b:
            self.speed_mode = '2400bps'
        elif speed_mode_val == 0x0000000c:
            self.speed_mode = '4800bps'
        elif speed_mode_val == 0x0000000d:
            self.speed_mode = '9600bps'
        elif speed_mode_val == 0x0000000e:
            self.speed_mode = '19200bps'
        elif speed_mode_val == 0x0000000f:
            self.speed_mode = '38400bps'
        elif speed_mode_val == 0x00010001:
            self.speed_mode = '57600bps'
        elif speed_mode_val == 0x00010002:
            self.speed_mode = '115200bps'
        else:
            self.speed_mode = '19200bps'
        if stopb_mode_val == 0x00000040:
            self.stopb_mode = 'Two'
        else:
            self.stopb_mode = 'One'


    @property
    def conf(self):
        try:
            if self.regvalue(): return self.regvalue()
        except:
            pass
        return 0

    def full(self):
        ret = {'dev': 'uart',
               'circuit': self.circuit,
               'conf_value': self.conf,
               'parity_modes': self.parity_modes,
               'parity_mode': self.parity_mode,
               'speed_modes': self.speed_modes,
               'speed_mode': self.speed_mode,
               'stopb_modes': self.stopb_modes,
               'stopb_mode': self.stopb_mode,
               'sw_address': self.address_val,
               'glob_dev_id': self.dev_id}
        if self.alias != '':
            ret['alias'] = self.alias
        return ret

    def simple(self):
        return {'dev': 'uart',
                'circuit': self.circuit,
                'conf_value': self.conf}

    @gen.coroutine
    def set(self, conf_value=None, parity_mode=None, speed_mode=None, stopb_mode=None, sw_address=None, alias=None):
        val = self.regvalue()
        if conf_value is not None:
            self.arm.neuron.client.write_register(self.valreg, conf_value, unit=self.arm.modbus_address)
        if parity_mode is not None and parity_mode in self.parity_modes and parity_mode != self.parity_mode:
            val &= ~self.parity_mask
            if parity_mode == 'None':
                val = val
            elif parity_mode == 'Odd':
                val |= 0x00000300
            elif parity_mode == 'Even':
                val |= 0x00000200
            else:
                val = val
            self.arm.neuron.client.write_register(self.valreg, val, unit=self.arm.modbus_address)
            self.parity_mode = parity_mode

        if speed_mode is not None and speed_mode in self.speed_modes and speed_mode != self.speed_mode:
            val &= ~self.speed_mask
            if speed_mode == '2400bps':
                val |= 0x0000000b
            elif speed_mode == '4800bps':
                val |= 0x0000000c
            elif speed_mode == '9600bps':
                val |= 0x0000000d
            elif speed_mode == '19200bps':
                val |= 0x0000000e
            elif speed_mode == '38400bps':
                val |= 0x0000000f
            elif speed_mode == '57600bps':
                val    |= 0x00010001
            elif speed_mode == '115200bps':
                val    |= 0x00010002
            else:
                val |= 0x0000000e
            self.arm.neuron.client.write_register(self.valreg, val, unit=self.arm.modbus_address)
            self.speed_mode = speed_mode

        if stopb_mode is not None and stopb_mode in self.stopb_modes and stopb_mode != self.stopb_mode:
            val &= ~self.stopb_mask
            if stopb_mode == 'One':
                val = val
            elif stopb_mode == 'Two':
                val |= 0x00000040
            self.arm.neuron.client.write_register(self.valreg, val, unit=self.arm.modbus_address)
            self.stopb_mode = stopb_mode

        if sw_address is not None and self.address_val != 0:
            self.arm.neuron.client.write_register(self.address_reg, sw_address, unit=self.arm.modbus_address)

        if alias is not None:
            if Devices.add_alias(alias, self, file_update=True):
                self.alias = alias

        raise gen.Return(self.full())

    def get(self):
        return self.full()

    def get_value(self):
        """ Returns value
              current on/off value is taken from last value without reading it from hardware
        """
        return self.conf

def uint16_to_int(inp):
    if inp > 0x8000: return (inp - 0x10000)
    return inp


class WiFiAdapter():
    def __init__(self, circuit, dev_id=0, major_group=0, ip_addr="192.168.1.100", enabled=False, enabled_routing=False, legacy_mode=True):
        self.alias = ""
        self.devtype = WIFI
        self.dev_id = dev_id
        self.circuit = circuit
        self.legacy_mode = legacy_mode
        self.major_group = major_group
        self.enabled_val = enabled
        self.enabled_routing_val = enabled_routing
        self.ip_addr = ip_addr
        self.packets_recieved = 0
        self.packets_sent = 0
        try:
            if ("UP" in subprocess.check_output(["ifconfig", "-a", "wlan0"])) and ("running" in subprocess.check_output(["systemctl", "status", "unipidns"])):
                self.enabled_val = True
        except subprocess.CalledProcessError:
            self.enabled_val = False
        try:
            if ("MASQUERADE" in subprocess.check_output(["iptables", "-t", "nat", "-L"])):
                self.enabled_routing_val = True
        except subprocess.CalledProcessError:
            self.enabled_routing_val = False

    @property
    def enabled(self):
        if self.enabled_val:
            return 'Enabled'
        else:
            return 'Disabled'

    @property
    def routing_enabled(self):
        if self.enabled_routing_val:
            return 'Enabled'
        else:
            return 'Disabled'

    @gen.coroutine
    def get_packets(self):
        subprocess.check_output(["ifconfig", "-a", "wlan0"])

    def full(self):
        ret = {'dev': 'wifi',
               'ap_state': self.enabled,
               'eth0_masq': self.routing_enabled,
               'circuit': self.circuit,
               'glob_dev_id': self.dev_id}
        if self.alias != '':
            ret['alias'] = self.alias
        return ret

    def simple(self):
        return {'dev': 'wifi',
                'circuit': self.circuit,
                'ap_state': self.enabled,
                'eth0_masq': self.routing_enabled,
                #'ip': self.ip_addr,
                'glob_dev_id': self.dev_id}

    @gen.coroutine
    def set(self, ap_state=None, eth0_masq=None, alias=None):
        if alias is not None:
            if Devices.add_alias(alias, self, file_update=True):
                self.alias = alias
        if ap_state is not None and ap_state in ['Enabled', 'Disabled'] and ap_state != self.enabled:
            if ap_state == 'Enabled':
                subprocess.check_output(["systemctl", "start", "unipidns"])
                self.enabled_val = True
            else:
                if not (("UP" in subprocess.check_output(["ifconfig", "-a", "wlan0"])) and ("running" in subprocess.check_output(["systemctl", "status", "unipidns"]))):
                    raise Exception("WiFi could not be terminated due to invalid state (possibly is starting up?)")
                subprocess.check_output(["systemctl", "stop", "unipidns"])
                subprocess.check_output(["systemctl", "stop", "unipiap"])
                self.enabled_val = False
        if eth0_masq is not None and eth0_masq in ['Enabled', 'Disabled'] and eth0_masq != self.routing_enabled:
            if eth0_masq == 'Enabled':
                subprocess.check_output(["iptables", "-t", "nat", "-A", "POSTROUTING", "-o", "eth0", "-j", "MASQUERADE"])
                self.enabled_routing_val = True
            else:
                subprocess.check_output(["iptables", "-t", "nat", "-D", "POSTROUTING", "-o", "eth0", "-j", "MASQUERADE"])
                self.enabled_routing_val = False
        raise gen.Return(self.full())

    def get(self):
        return self.full()


class AnalogOutput():
    def __init__(self, circuit, arm, reg, regcal=-1, regmode=-1, reg_res=0, dev_id=0, modes=['Voltage'], major_group=0, legacy_mode=True):
        self.alias = ""
        self.devtype = AO
        self.dev_id = dev_id
        self.circuit = circuit
        self.reg = reg
        self.regvalue = lambda: self.arm.neuron.modbus_cache_map.get_register(1, self.reg, unit=self.arm.modbus_address)[0]
        self.regcal = regcal
        self.regmode = regmode
        self.legacy_mode = legacy_mode
        self.reg_res = reg_res
        self.regresvalue = lambda: self.arm.neuron.modbus_cache_map.get_register(1, self.reg_res, unit=self.arm.modbus_address)[0]
        self.modes = modes
        self.arm = arm
        self.major_group = major_group
        if regcal >= 0:
            self.offset = (uint16_to_int(self.arm.neuron.modbus_cache_map.get_register(1, self.regcal + 1, unit=self.arm.modbus_address)[0]) / 10000.0)
        else:
            self.offset = 0
        self.is_voltage = lambda: True
        if circuit == '1_01' and regcal >= 0:
            self.is_voltage = lambda: bool(self.arm.neuron.modbus_cache_map.get_register(1, self.regmode, unit=self.arm.modbus_address)[0] == 0)
        if self.is_voltage():
            self.mode = 'Voltage'
        elif self.arm.neuron.modbus_cache_map.get_register(1, self.regmode, unit=self.arm.modbus_address)[0] == 1:
            self.mode = 'Current'
        else:
            self.mode = 'Resistance'
        self.reg_shift = 2 if self.is_voltage() else 0
        if self.circuit == '1_01':
            self.factor = arm.volt_ref / 4095 * (1 + uint16_to_int(self.arm.neuron.modbus_cache_map.get_register(1, regcal + self.reg_shift, unit=self.arm.modbus_address)[0]) / 10000.0)
            self.factorx = arm.volt_refx / 4095 * (1 + uint16_to_int(self.arm.neuron.modbus_cache_map.get_register(1, regcal + self.reg_shift, unit=self.arm.modbus_address)[0]) / 10000.0)
        else:
            self.factor = arm.volt_ref / 4095 * (1 / 10000.0)
            self.factorx = arm.volt_refx / 4095 * (1 / 10000.0)
        if self.is_voltage():
            self.factor *= 3
            self.factorx *= 3
        else:
            self.factor *= 10
            self.factorx *= 10

    @property
    def value(self):
        try:
            if self.circuit == '1_01':
                return self.regvalue() * self.factor + self.offset
            else:
                return self.regvalue() * 0.0025
        except:
            return 0

    @property
    def res_value(self):
        try:
            if self.circuit == '1_01':
                return float(self.regresvalue()) / 10.0
            else:
                return float(self.regvalue()) * 0.0025
        except:
            return 0

    def full(self):
        ret = {'dev': 'ao',
               'circuit': self.circuit,
               'mode': self.mode,
               'modes': self.modes,
               'glob_dev_id': self.dev_id}
        if self.mode == 'Resistance':
            ret['value'] = self.res_value
            ret['unit'] = (unit_names[OHM])
        else:
            ret['value'] = self.value
            ret['unit'] = (unit_names[VOLT]) if self.is_voltage() else (unit_names[AMPERE])
        if self.alias != '':
            ret['alias'] = self.alias
        return ret

    def simple(self):
        if self.mode == 'Resistance':
            return {'dev': 'ao',
                    'circuit': self.circuit,
                    'value': self.res_value}
        else:
            return {'dev': 'ao',
                    'circuit': self.circuit,
                    'value': self.value}

    @gen.coroutine
    def set_value(self, value):
        if self.circuit == '1_01':
            valuei = int((float(value) - self.offset) / self.factor)
        else:
            valuei = int((float(value) / 0.0025))
        if valuei < 0:
            valuei = 0
        elif valuei > 4095:
            valuei = 4095
        self.arm.neuron.client.write_register(self.reg, valuei, unit=self.arm.modbus_address)
        if self.circuit == '1_01':
            raise gen.Return(float(valuei) * self.factor + self.offset)
        else:
            raise gen.Return(float(valuei) * 0.0025)

    @gen.coroutine
    def set(self, value=None, mode=None, alias=None):
        if alias is not None:
            if Devices.add_alias(alias, self, file_update=True):
                self.alias = alias
        if mode is not None and mode in self.modes and self.regmode != -1:
            val = self.arm.neuron.modbus_cache_map.get_register(1, self.regmode, unit=self.arm.modbus_address)[0]
            cur_val = self.value
            if mode == "Voltage":
                val = 0
                if (self.mode == 'Current'):
                    self.factor = (self.factor / 10) * 3
            elif mode == "Current":
                val = 1
                if (self.mode == 'Voltage' or self.mode == 'Resistance'):
                    self.factor = (self.factor / 3) * 10
            elif mode == "Resistance":
                val = 3
            self.mode = mode
            self.arm.neuron.client.write_register(self.regmode, val, unit=self.arm.modbus_address)
            if mode == "Voltage" or mode == "Current":
                yield self.set_value(cur_val)        # Restore original value (i.e. 1.5V becomes 1.5mA)
        if not (value is None):
            if self.circuit == '1_01':
                valuei = int((float(value) - self.offset) / self.factor)
            else:
                valuei = int((float(value) / 0.0025))
            if valuei < 0:
                valuei = 0
            elif valuei > 4095:
                valuei = 4095
            self.arm.neuron.client.write_register(self.reg, valuei, unit=self.arm.modbus_address)
        raise gen.Return(self.full())

    def get(self):
        return self.full()



class AnalogInput():
    def __init__(self, circuit, arm, reg, regcal=-1, regmode=-1, dev_id=0, major_group=0, legacy_mode=True, tolerances='brain', modes=['Voltage']):
        self.alias = ""
        self.devtype = AI
        self.dev_id = dev_id
        self.circuit = circuit
        self.valreg = reg
        self.arm = arm
        self.regvalue = lambda: self.arm.neuron.modbus_cache_map.get_register(1, self.valreg, unit=self.arm.modbus_address)[0]
        self.regcal = regcal
        self.legacy_mode = legacy_mode
        self.regmode = regmode
        self.modes = modes
        self.mode = 'Voltage'
        self.unit_name = unit_names[VOLT]
        self.tolerances = tolerances
        self.sec_ai_mode = 0
        if self.tolerances == '500series':
            self.sec_ai_mode = self.arm.neuron.modbus_cache_map.get_register(1, self.regmode, unit=self.arm.modbus_address)[0]
            self.mode = self.get_500_series_mode()
            self.unit_name = self.internal_unit
        self.major_group = major_group
        self.is_voltage = lambda: True
        if self.tolerances == 'brain' and regcal >= 0:
            self.is_voltage = lambda: bool(self.arm.neuron.modbus_cache_map.get_register(1, self.regmode, unit=self.arm.modbus_address)[0] == 0)
            if self.is_voltage():
                self.mode = "Voltage"
            else:
                self.mode = "Current"
                self.unit_name = unit_names[AMPERE]
        self.tolerance_mode = self.get_tolerance_mode()
        self.reg_shift = 2 if self.is_voltage() else 0
        if regcal >= 0:
            self.vfactor = arm.volt_ref / 4095 * (1 + uint16_to_int(self.arm.neuron.modbus_cache_map.get_register(1, regcal + self.reg_shift + 1, unit=self.arm.modbus_address)[0]) / 10000.0)
            self.vfactorx = arm.volt_refx / 4095 * (1 + uint16_to_int(self.arm.neuron.modbus_cache_map.get_register(1, regcal + self.reg_shift + 1, unit=self.arm.modbus_address)[0]) / 10000.0)
            self.voffset = (uint16_to_int(self.arm.neuron.modbus_cache_map.get_register(1, regcal + self.reg_shift + 2, unit=self.arm.modbus_address)[0]) / 10000.0)
        else:
            self.vfactor = arm.volt_ref / 4095 * (1 / 10000.0)
            self.vfactorx = arm.volt_refx / 4095 * (1 / 10000.0)
            self.voffset = 0
        if self.is_voltage():
            self.vfactor *= 3
            self.vfactorx *= 3
        else:
            self.vfactor *= 10
            self.vfactorx *= 10

    @property
    def value(self):
        try:
            if self.circuit == '1_01':
                raw_val = self.regvalue()

                if raw_val == 0 or raw_val == 65535:
                    return 0

                if raw_val > 32768: # Negative value present
                    raw_val = raw_val - 65536

                return (raw_val * self.vfactor) + self.voffset
            else:
                byte_arr = bytearray(4)
                byte_arr[2] = (self.regvalue() >> 8) & 255
                byte_arr[3] = self.regvalue() & 255
                byte_arr[0] = (self.arm.neuron.modbus_cache_map.get_register(1, self.valreg + 1, unit=self.arm.modbus_address)[0] >> 8) & 255
                byte_arr[1] = self.arm.neuron.modbus_cache_map.get_register(1, self.valreg + 1, unit=self.arm.modbus_address)[0] & 255
                return struct.unpack('>f', str(byte_arr))[0]
        except Exception, E:
            logger.exception(str(E))
            return 0


    def get_tolerance_modes(self):
        if self.tolerances == 'brain':
            if self.mode == 'Voltage':
                return ["10.0"]
            else:
                return ["20.0"]
        elif self.tolerances == '500series':
            if self.mode == 'Voltage':
                return ["0.0", "2.5", "10.0"]
            elif self.mode == 'Current':
                return ["20.0"]
            elif self.mode == "Resistance":
                return ["1960.0", "100.0"]

    def get_tolerance_mode(self):
        if self.tolerances == 'brain':
            if self.mode == 'Voltage':
                return "10.0"
            else:
                return "20.0"
        elif self.tolerances == '500series':
            if self.sec_ai_mode == 0:
                return "0.0"
            elif self.sec_ai_mode == 1:
                return "10.0"
            elif self.sec_ai_mode == 2:
                return "2.5"
            elif self.sec_ai_mode == 3:
                return "20.0"
            elif self.sec_ai_mode == 4:
                return "1960.0"
            elif self.sec_ai_mode == 5:
                return "100.0"

    def get_500_series_mode(self):
        if self.sec_ai_mode == 0:
            return "Voltage"
        elif self.sec_ai_mode == 1:
            return "Voltage"
        elif self.sec_ai_mode == 2:
            return "Voltage"
        elif self.sec_ai_mode == 3:
            return "Current"
        elif self.sec_ai_mode == 4:
            return "Resistance"
        elif self.sec_ai_mode == 5:
            return "Resistance"

    def get_500_series_sec_mode(self):
        if self.mode == "Voltage":
            if self.tolerance_mode == "0.0":
                return 0
            elif self.tolerance_mode == "10.0":
                return 1
            elif self.tolerance_mode == "2.5":
                return 2
        elif self.mode == "Current":
            if self.tolerance_mode == "20.0":
                return 3
        elif self.mode == "Resistance":
            if self.tolerance_mode == "1960.0":
                return 4
            elif self.tolerance_mode == "100.0":
                return 5

    @gen.coroutine
    def set(self, mode=None, range=None, alias=None):
        if alias is not None:
            if Devices.add_alias(alias, self, file_update=True):
                self.alias = alias
        if mode is not None and mode in self.modes:
            if self.tolerances == "brain" and mode != self.mode:
                self.mode = mode
                if self.mode == "Voltage":
                    self.unit_name = unit_names[VOLT]
                    yield self.arm.neuron.client.write_register(self.regmode, 0, unit=self.arm.modbus_address)
                elif self.mode == "Current":
                    self.unit_name = unit_names[AMPERE]
                    yield self.arm.neuron.client.write_register(self.regmode, 1, unit=self.arm.modbus_address)
                self.reg_shift = 2 if self.mode == "Voltage" else 0
                if self.regcal >= 0:
                    self.vfactor = self.arm.volt_ref / 4095 * (1 + uint16_to_int(self.arm.neuron.modbus_cache_map.get_register(1, self.regcal + self.reg_shift + 1, unit=self.arm.modbus_address)[0]) / 10000.0)
                    self.vfactorx = self.arm.volt_refx / 4095 * (1 + uint16_to_int(self.arm.neuron.modbus_cache_map.get_register(1, self.regcal + self.reg_shift + 1, unit=self.arm.modbus_address)[0]) / 10000.0)
                    self.voffset = (uint16_to_int(self.arm.neuron.modbus_cache_map.get_register(1, self.regcal + self.reg_shift + 2, unit=self.arm.modbus_address)[0]) / 10000.0)
                else:
                    self.vfactor = self.arm.volt_ref / 4095 * (1 / 10000.0)
                    self.vfactorx = self.arm.volt_refx / 4095 * (1 / 10000.0)
                    self.voffset = 0
                if self.mode == "Voltage":
                    self.vfactor *= 3
                    self.vfactorx *= 3
                else:
                    self.vfactor *= 10
                    self.vfactorx *= 10
                self.tolerance_mode = self.get_tolerance_mode()
            elif self.tolerances == "500series":
                self.mode = mode
                if self.mode == "Voltage":
                    self.unit_name = unit_names[VOLT]
                    self.sec_ai_mode = 1
                elif self.mode == "Current":
                    self.unit_name = unit_names[AMPERE]
                    self.sec_ai_mode = 3
                elif self.mode == "Resistance":
                    self.unit_name = unit_names[OHM]
                    self.sec_ai_mode = 4
                self.tolerance_mode = self.get_tolerance_mode()
                yield self.arm.neuron.client.write_register(self.regmode, self.sec_ai_mode, unit=self.arm.modbus_address)
        if self.tolerances == '500series' and range is not None and range in self.get_tolerance_modes():
            if self.mode == "Voltage":
                self.unit_name = unit_names[VOLT]
            elif self.mode == "Current":
                self.unit_name = unit_names[AMPERE]
            else:
                self.unit_name = unit_names[OHM]
            self.tolerance_mode = range
            self.sec_ai_mode = self.get_500_series_sec_mode()
            yield self.arm.neuron.client.write_register(self.regmode, self.sec_ai_mode, unit=self.arm.modbus_address)
        raise gen.Return(self.full())

    def full(self):
        ret = {'dev': 'ai',
               'circuit': self.circuit,
                  'value': self.value,
                  'unit': self.unit_name,
                'glob_dev_id': self.dev_id,
               'mode': self.mode,
                  'modes': self.modes,
                  'range': self.tolerance_mode,
                  'range_modes': self.get_tolerance_modes()}
        if self.alias != '':
            ret['alias'] = self.alias
        return ret

    def get(self):
        return self.full()

    def simple(self):
        return {'dev': 'ai',
                'circuit': self.circuit,
                'value': self.value}

    @property
    def voltage(self):
        return self.value

    @property
    def internal_unit(self):
        if self.mode == "Voltage":
            return unit_names[VOLT]
        elif self.mode == "Current":
            return unit_names[AMPERE]
        else:
            return unit_names[OHM]


class AnalogInput18():

    def __init__(self, circuit, arm, reg, regmode=-1, dev_id=0, major_group=0, modes=['Voltage']):
        self.alias = ""
        self.devtype = AI
        self.dev_id = dev_id
        self.circuit = circuit
        self.valreg = reg
        self.arm = arm
        self.regmode = regmode
        self.modes = modes
        self.mode = 'Voltage'
        self.unit_name = ''
        self.tolerances = ["Integer 18bit", "Float"]
        self.tolerance_mode = "Integer 18bit"
        self.raw_mode = self.arm.neuron.modbus_cache_map.get_register(1, self.regmode, unit=self.arm.modbus_address)[0]
        self.mode = self.get_mode()
        self.major_group = major_group
        self.calibration = {'Voltage': 10.0/(1<<18)/0.9772, 'Current': 40.0/(1<<18)}


    @property
    def value(self):
        try:
            U32 = self.arm.neuron.modbus_cache_map.get_register(2, self.valreg, unit=self.arm.modbus_address)
            raw_value = U32[0] | (U32[1] << 16)
            return raw_value if self.tolerance_mode == "Integer 18bit" else float(raw_value)*self.calibration[self.mode]
        except Exception, E:
            logger.exception(str(E))
            return 0

    def get_mode(self):
        if self.raw_mode == 1:
            return "Current"
        else:
            return "Voltage"


    @gen.coroutine
    def set(self, mode=None, range=None, alias=None):
        if alias is not None:
            if Devices.add_alias(alias, self, file_update=True):
                self.alias = alias
        if mode is not None and mode in self.modes:
            self.mode = mode
            if self.mode == "Voltage":
                    self.raw_mode = 0
            elif self.mode == "Current":
                    self.raw_mode = 1
            yield self.arm.neuron.client.write_register(self.regmode, self.raw_mode, unit=self.arm.modbus_address)

        if range is not None and range in self.tolerances:
            self.tolerance_mode = range
            if range == "Float":
                self.unit_name = unit_names[AMPERE] if self.mode == "Current" else unit_names[VOLT]
            else:
                self.unit_name = ''

        raise gen.Return(self.full())

    def full(self):
        ret = {'dev': 'ai',
               'circuit': self.circuit,
               'value': self.value,
               'unit': self.unit_name,
               'glob_dev_id': self.dev_id,
               'mode': self.mode,
               'modes': self.modes,
               'range': self.tolerance_mode,
               'range_modes': self.tolerances
              }
        if self.alias != '':
            ret['alias'] = self.alias
        return ret

    def get(self):
        return self.full()

    def simple(self):
        return {'dev': 'ai',
                'circuit': self.circuit,
                'value': self.value}

    @property
    def voltage(self):
        return self.value


class AnalogInput12():
    """
    Internal ADC of the ARM Cortex-M0 MCU
    """


    def __init__(self, circuit, arm, reg_float, reg_raw, regmode=-1, dev_id=0, major_group=0, modes=['Voltage', 'Current'], formats=["Integer RAW", "Float"]):
        self.alias = ""
        self.devtype = AI
        self.dev_id = dev_id
        self.circuit = circuit
        self.valreg = reg_float
        self.valreg_raw = reg_raw
        self.arm = arm
        self.regmode = regmode
        self.modes = modes
        self.mode = 'Voltage'
        self.unit_name = unit_names[VOLT]
        self.val_formats = formats
        self.val_format = "Float"
        self.raw_mode = self.arm.neuron.modbus_cache_map.get_register(1, self.regmode, unit=self.arm.modbus_address)[0]
        self.mode = self.get_mode()
        self.major_group = major_group

    @property
    def value(self):
        try:
            if self.val_format == "Integer RAW":
                regs = self.arm.neuron.modbus_cache_map.get_register(2, self.valreg_raw, unit=self.arm.modbus_address)
                val = regs[0] | (regs[1] << 16)
            else:
                regs = self.arm.neuron.modbus_cache_map.get_register(2, self.valreg, unit=self.arm.modbus_address)
                byte_arr = bytearray(4)
                byte_arr[2] = (regs[0] >> 8) & 255
                byte_arr[3] = regs[0] & 255
                byte_arr[0] = (regs[1] >> 8) & 255
                byte_arr[1] = regs[1] & 255
                val = round(struct.unpack('>f', str(byte_arr))[0],3)

            return val
        except Exception, E:
            logger.exception(str(E))
            return 0

    def get_mode(self):
        if self.raw_mode == 2:
            return "Current"
        else:
            return "Voltage"

    def full(self):
        ret = {'dev': 'ai',
               'circuit': self.circuit,
               'value': self.value,
               'unit': self.unit_name,
               'glob_dev_id': self.dev_id,
               'mode': self.mode,
               'modes': self.modes,
               'val_format': self.val_format,
               'val_formats': self.val_formats
              }
        if self.alias != '':
            ret['alias'] = self.alias
        return ret

    def get(self):
        return self.full()

    def simple(self):
        return {'dev': 'ai',
                'circuit': self.circuit,
                'value': self.value}

    @gen.coroutine
    def set(self, mode=None, val_format=None, alias=None):
        if alias is not None:
            if Devices.add_alias(alias, self, file_update=True):
                self.alias = alias

        if mode is not None and mode in self.modes:
            self.mode = mode
            if self.mode == "Voltage":
                self.raw_mode = 1
            elif self.mode == "Current":
                self.raw_mode = 2
            yield self.arm.neuron.client.write_register(self.regmode, self.raw_mode, unit=self.arm.modbus_address)

        if val_format is not None and val_format in self.val_formats:
            self.val_format = val_format

        if self.val_format == "Float":
            self.unit_name = unit_names[AMPERE] if self.mode == "Current" else unit_names[VOLT]
        else:
            self.unit_name = ''

        raise gen.Return(self.full())

    @property
    def voltage(self):
        return self.value
