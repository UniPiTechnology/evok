"""
  Code specific to Neuron devices
------------------------------------------
"""

import math
import datetime
from math import sqrt
from typing import Union

from tornado.ioloop import IOLoop
from pymodbus.client import AsyncModbusTcpClient
from pymodbus.pdu import ExceptionResponse
from pymodbus.exceptions import ModbusIOException, ConnectionException
from pymodbus.payload import BinaryPayloadDecoder, BinaryPayloadBuilder
from pymodbus.constants import Endian
from tornado.locks import Semaphore

from .devices import *
from .errors import ENoCacheRegister, ModbusSlaveError
from .modbus_unipi import EvokModbusSerialClient
from .log import *
from . import config
import time

import subprocess


class ModbusCacheMap(object):
    last_comm_time = 0
    def __init__(self, modbus_reg_map, modbus_slave):
        self.modbus_reg_map = modbus_reg_map
        self.modbus_slave: ModbusSlave = modbus_slave
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

    def get_register(self, count, index, slave=0, is_input=False):

        def raiseifNull(val, register):
            if val!=None: return val
            raise ENoCacheRegister(f"No cached value of register {register}")

        try:
            if is_input:
                _slice = (raiseifNull(self.registered_input[index+i], index+1) for i in range(count))
            else:
                _slice = (raiseifNull(self.registered[index+i], index+1) for i in range(count))
            return list(_slice)
        except KeyError as E:
            raise Exception('Unknown register %d' % E.args[0])

    async def do_scan(self, slave=0, initial=False):
        if initial:
            await self.sem.acquire()
        changeset = []
        for m_reg_group in self.modbus_reg_map:
            if (self.frequency[m_reg_group['start_reg']] >= m_reg_group['frequency']) or (self.frequency[m_reg_group['start_reg']] == 0):    # only read once for every [frequency] cycles
                val = None
                try:
                    if 'type' in m_reg_group and m_reg_group['type'] == 'input':
                        val = await self.modbus_slave.client.read_input_registers(m_reg_group['start_reg'], m_reg_group['count'], slave=slave)
                    else:
                        val = await self.modbus_slave.client.read_holding_registers(m_reg_group['start_reg'], m_reg_group['count'], slave=slave)
                    if not isinstance(val, ExceptionResponse) and not isinstance(val, ModbusIOException) and not isinstance(val, ExceptionResponse) and val is not None:
                        self.last_comm_time = time.time()
                        if 'type' in m_reg_group and m_reg_group['type'] == 'input':
                            for index in range(m_reg_group['count']):
                                if (m_reg_group['start_reg'] + index) in self.modbus_slave.datadeps and self.registered_input[(m_reg_group['start_reg'] + index)] != val.registers[index]:
                                    for ddep in self.modbus_slave.datadeps[m_reg_group['start_reg'] + index]:
                                        if (not ((isinstance(ddep, Input) or isinstance(ddep, ULED)))) or ddep.value_delta(val.registers[index]):
                                            changeset += [ddep]
                                self.registered_input[(m_reg_group['start_reg'] + index)] = val.registers[index]
                                self.frequency[m_reg_group['start_reg']] = 1
                        else:
                            for index in range(m_reg_group['count']):
                                if (m_reg_group['start_reg'] + index) in self.modbus_slave.datadeps and self.registered[(m_reg_group['start_reg'] + index)] != val.registers[index]:
                                    for ddep in self.modbus_slave.datadeps[m_reg_group['start_reg'] + index]:
                                        if (not ((isinstance(ddep, Input) or isinstance(ddep, ULED) or isinstance(ddep, Relay) or isinstance(ddep, Watchdog)))) or ddep.value_delta(val.registers[index]):
                                            changeset += [ddep]
                                self.registered[(m_reg_group['start_reg'] + index)] = val.registers[index]
                                self.frequency[m_reg_group['start_reg']] = 1
                except Exception as E:
                    logger.warning(E)
                    print(f"val: {val} \t {val.registers if hasattr(val, 'registers') else None}", flush=True)
            else:
                self.frequency[m_reg_group['start_reg']] += 1
        if len(changeset) > 0:
            proxy = Proxy(set(changeset))
            devents.status(proxy)
        if initial:
            self.sem.release()

    async def set_register(self, count, index, inp, slave=0, is_input=False):
        if len(inp) < count:
            raise Exception('Insufficient data to write into registers')
        for counter in range(count):
            if is_input:
                if index + counter not in self.registered_input:
                    raise Exception('Unknown register %d' % index + counter)
                await self.modbus_slave.client.write_register(index + counter, 1, inp[counter], slave=slave)
                self.registered_input[index + counter] = inp[counter]
            else:
                if index + counter not in self.registered:
                    raise Exception('Unknown register %d' % index + counter)
                await self.modbus_slave.client.write_register(index + counter, 1, inp[counter], slave=slave)
                self.registered[index + counter] = inp[counter]

    def has_register(self, index, is_input=False):
        if is_input:
            return index not in self.registered_input
        else:
            return index not in self.registered

    async def get_register_async(self, count, index, slave=0, is_input=False):
        if is_input:
            for counter in range(index,count+index):
                if counter not in self.registered_input:
                    raise Exception('Unknown register')
            val = await self.modbus_slave.client.read_input_registers(index, count, slave=slave)
        else:
            for counter in range(index,count+index):
                if counter not in self.registered:
                    raise Exception('Unknown register')
            val = await self.modbus_slave.client.read_holding_registers(index, count, slave=slave)
        for counter in range(len(val.registers)):
            self.registered[index+counter] = val.registers[counter]
        return val.registers


    async def set_register_async(self, count, index, inp, slave=0, is_input=False):
        if is_input:
            if len(inp) < count:
                raise Exception('Insufficient data to write into registers')
            for counter in range(count):
                if index + counter not in self.registered_input:
                    raise Exception('Unknown register')
                await self.modbus_slave.client.write_register(index + counter, 1, inp[counter], slave=slave)
                self.registered_input[index + counter] = inp[counter]
        else:
            if len(inp) < count:
                raise Exception('Insufficient data to write into registers')
            for counter in range(count):
                if index + counter not in self.registered:
                    raise Exception('Unknown register')
                await self.modbus_slave.client.write_register(index + counter, 1, inp[counter], slave=slave)
                self.registered[index + counter] = inp[counter]


class ModbusSlave(object):

    def __init__(self, client: Union[AsyncModbusTcpClient, EvokModbusSerialClient],
                 circuit, evok_config, scan_freq, scan_enabled, hw_dict, slave_id=1,
                 major_group=1, device_model='unspecified', dev_id=0):
        self.alias = ""
        self.devtype = MODBUS_SLAVE
        self.modbus_cache_map = None
        self.datadeps = {}
        self.boards = list()
        self.dev_id = dev_id
        self.hw_dict = hw_dict
        self.modbus_address = slave_id
        self.device_model = device_model
        self.evok_config = evok_config
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
        self.logfile = evok_config.getstringdef( "log_file", "/var/log/evok.log")
        self.client: Union[AsyncModbusTcpClient, EvokModbusSerialClient] = client
        self.loop: Union[None, IOLoop] = None
        self.circuit: Union[None, str] = circuit

    def get(self):
        return self.full()

    def switch_to_async(self, loop: IOLoop, alias_dict):
        self.loop = loop
        loop.add_callback(lambda: self.readboards(alias_dict))

    async def set(self, print_log=None):
        if print_log is not None and print_log != 0:
            log_tail = subprocess.check_output(["tail", "-n 255", self.logfile])
            return log_tail
        else:
            return ""

    async def readboards(self, alias_dict):
        logger.info(f"Reading the Modbus board on Modbus address {self.modbus_address}\t({self.circuit})")
        self.boards = list()
        try:
            for defin in self.hw_dict.definitions:
                if defin and (defin['type'] == self.device_model):
                    self.hw_board_dict = defin
                    break
            board = Board(self.evok_config, self.circuit, self.modbus_address, self, dev_id=self.dev_id)
            await board.parse_definition(self.hw_dict)
            self.boards.append(board)
            config.add_aliases(alias_dict)
        except ConnectionException as E:
            logger.error(f"No board detected on Modbus {self.modbus_address}\t({type(E).__name__}:{E})")
        except Exception as E:
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

    async def scan_boards(self, invoc=False):
        if self.is_scanning and invoc:
            return
        try:
            if self.modbus_cache_map is not None:
                await self.modbus_cache_map.do_scan(slave=self.modbus_address)
                self.scanning_error_triggered = False
        except Exception as E:
            if not self.scanning_error_triggered:
                logger.debug(str(E))
            self.scanning_error_triggered = True
        if self.do_scanning and (self.scan_interval != 0):
            self.loop.call_later(self.scan_interval, self.scan_boards)
            self.is_scanning = True
        else:
            self.is_scanning = False

    def full(self):
        ret = {'dev': 'extension',
                'circuit': self.circuit,
                'model': self.device_model,
                'glob_dev_id': self.dev_id,
                'last_comm': 0x7fffffff}
        if self.alias != '':
            ret['alias'] = self.alias
        if self.modbus_cache_map is not None:
            ret['last_comm'] = time.time() - self.modbus_cache_map.last_comm_time

        # TODO: zkontrolovat, jestli existruji v 'self.client'
        'modbus_server'
        'modbus_port'
        'uart_circuit'
        'uart_port'

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


class Board(object):
    def __init__(self, evok_config, circuit, modbus_address, modbus_slave: ModbusSlave, major_group=1, dev_id=0):
        self.alias = ""
        self.devtype = BOARD
        self.dev_id = dev_id
        self.evok_config = evok_config
        self.circuit = circuit
        self.legacy_mode = not (evok_config.getbooldef('use_experimental_api', False))
        self.modbus_slave: ModbusSlave = modbus_slave
        self.major_group = major_group
        self.modbus_address = modbus_address

    async def set(self, alias=None):
        if not alias is None:
            if Devices.add_alias(alias, self, file_update=True):
                self.alias = alias
        return await self.full()

    async def initialise_cache(self, cache_definition):
        if cache_definition and (self.modbus_slave.device_model == cache_definition['type']):
            if 'modbus_register_blocks' in cache_definition:
                if self.modbus_slave.modbus_cache_map == None:
                    self.modbus_slave.modbus_cache_map = ModbusCacheMap(cache_definition['modbus_register_blocks'], self.modbus_slave)
                    await self.modbus_slave.modbus_cache_map.do_scan(initial=True, slave=self.modbus_address)
                    await self.modbus_slave.modbus_cache_map.sem.acquire()
                    self.modbus_slave.modbus_cache_map.sem.release()
                else:
                    await self.modbus_slave.modbus_cache_map.sem.acquire()
                    self.modbus_slave.modbus_cache_map.sem.release()
            else:
                raise Exception("HW Definition %s requires Modbus register blocks to be specified" % cache_definition['type'])

    def parse_feature_di(self, max_count, m_feature, board_id):
        counter = 0
        while counter < max_count:
            board_val_reg = m_feature['val_reg']
            board_counter_reg = m_feature['counter_reg']
            board_deboun_reg = m_feature['deboun_reg']
            start_index = 0
            if 'start_index' in m_feature:
                start_index = m_feature['start_index']
            if ('ds_modes' in m_feature) and ('direct_reg' in m_feature) and ('polar_reg' in m_feature) and ('toggle_reg' in m_feature):
                _inp = Input("%s_%02d" % (self.circuit, counter + 1 + start_index), self, board_val_reg, 0x1 << (counter % 16),
                             regdebounce=board_deboun_reg + counter, major_group=0, regcounter=board_counter_reg + (2 * counter), modes=m_feature['modes'],
                             dev_id=self.dev_id, ds_modes=m_feature['ds_modes'], regmode=m_feature['direct_reg'], regtoggle=m_feature['toggle_reg'],
                             regpolarity=m_feature['polar_reg'], legacy_mode=self.legacy_mode)
            else:
                _inp = Input("%s_%02d" % (self.circuit, counter + 1 + start_index), self, board_val_reg, 0x1 << (counter % 16),
                             regdebounce=board_deboun_reg + counter, major_group=0, regcounter=board_counter_reg + (2 * counter), modes=m_feature['modes'],
                             dev_id=self.dev_id, legacy_mode=self.legacy_mode)
            if board_val_reg in self.modbus_slave.datadeps:
                self.modbus_slave.datadeps[board_val_reg]+=[_inp]
            else:
                self.modbus_slave.datadeps[board_val_reg] = [_inp]
            if (board_counter_reg + (2 * counter)) in self.modbus_slave.datadeps:
                self.modbus_slave.datadeps[board_counter_reg + (2 * counter)]+=[_inp]
            else:
                self.modbus_slave.datadeps[board_counter_reg + (2 * counter)] = [_inp]
            Devices.register_device(INPUT, _inp)
            counter+=1

    def parse_feature_ro(self, max_count, m_feature, board_id):
        counter = 0
        while counter < max_count:
            board_val_reg = m_feature['val_reg']
            if m_feature['type'] == 'DO' and m_feature['pwm_reg'] and m_feature['pwm_ps_reg'] and m_feature['pwm_c_reg']:
                if not self.legacy_mode:
                    _r = Relay("%s_%02d" % (self.circuit, counter + 1), self, m_feature['val_coil'] + counter, board_val_reg, 0x1 << (counter % 16),
                               dev_id=self.dev_id, major_group=0, pwmcyclereg=m_feature['pwm_c_reg'], pwmprescalereg=m_feature['pwm_ps_reg'], digital_only=True,
                               pwmdutyreg=m_feature['pwm_reg'] + counter, modes=m_feature['modes'], legacy_mode=self.legacy_mode)
                else:
                    _r = Relay("%s_%02d" % (self.circuit, counter + 1), self, m_feature['val_coil'] + counter, board_val_reg, 0x1 << (counter % 16),
                               dev_id=self.dev_id, major_group=0, pwmcyclereg=m_feature['pwm_c_reg'], pwmprescalereg=m_feature['pwm_ps_reg'], digital_only=True,
                               pwmdutyreg=m_feature['pwm_reg'] + counter, modes=m_feature['modes'], legacy_mode=self.legacy_mode)
            else:
                    _r = Relay("%s_%02d" % (self.circuit, counter + 1), self, m_feature['val_coil'] + counter, board_val_reg, 0x1 << (counter % 16),
                               dev_id=self.dev_id, major_group=0, legacy_mode=self.legacy_mode)
            if board_val_reg in self.modbus_slave.datadeps:
                self.modbus_slave.datadeps[board_val_reg]+=[_r]
            else:
                self.modbus_slave.datadeps[board_val_reg] = [_r]
            Devices.register_device(RELAY, _r)
            counter+=1

    def parse_feature_led(self, max_count, m_feature, board_id):
        counter = 0
        while counter < max_count:
            board_val_reg = m_feature['val_reg']
            _led = ULED("%s_%02d" % (self.circuit, counter + 1), self, counter, board_val_reg, 0x1 << (counter % 16), m_feature['val_coil'] + counter,
                        dev_id=self.dev_id, major_group=0, legacy_mode=self.legacy_mode)
            if (board_val_reg + counter) in self.modbus_slave.datadeps:
                self.modbus_slave.datadeps[board_val_reg] += [_led]
            else:
                self.modbus_slave.datadeps[board_val_reg] = [_led]
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
            if (board_val_reg + counter) in self.modbus_slave.datadeps:
                self.modbus_slave.datadeps[board_val_reg + counter]+=[_wd]
            else:
                self.modbus_slave.datadeps[board_val_reg + counter] = [_wd]
            Devices.register_device(WATCHDOG, _wd)
            counter+=1

    def parse_feature_ao(self, max_count, m_feature, board_id):
        counter = 0
        while counter < max_count:
            board_val_reg = m_feature['val_reg']
            if 'res_val_reg' in m_feature:
                _ao = AnalogOutputBrain("%s_%02d" % (self.circuit, counter + 1), self, board_val_reg + counter,
                                   regmode=m_feature['mode_reg'], reg_res=m_feature['res_val_reg'],
                                   dev_id=self.dev_id, major_group=self.major_group, legacy_mode=self.legacy_mode)
            else:
                _ao = AnalogOutput("%s_%02d" % (self.circuit, counter + 1), self, board_val_reg + counter, dev_id=self.dev_id,
                                   major_group=0, legacy_mode=self.legacy_mode)
            if (board_val_reg + counter) in self.modbus_slave.datadeps:
                self.modbus_slave.datadeps[board_val_reg + counter]+=[_ao]
            else:
                self.modbus_slave.datadeps[board_val_reg + counter] = [_ao]
            Devices.register_device(AO, _ao)
            counter+=1

    def parse_feature_ai18(self, max_count, m_feature, board_id):
        value_reg = m_feature['val_reg']
        mode_reg = m_feature['mode_reg']
        for i in range(max_count):
            circuit = "%s_%02d" % (self.circuit, i + 1)
            _ai = AnalogInput18(circuit, self, value_reg, regmode=mode_reg+i,
                                dev_id=self.dev_id, major_group=0, modes=m_feature['modes'])

            if value_reg in self.modbus_slave.datadeps:
                self.modbus_slave.datadeps[value_reg]+=[_ai]
            else:
                self.modbus_slave.datadeps[value_reg] = [_ai]
            Devices.register_device(AI, _ai)
            value_reg += 2;


    def parse_feature_ai(self, max_count, m_feature, board_id):
        counter = 0
        while counter < max_count:
            board_val_reg = m_feature['val_reg']
            tolerances = m_feature.get('tolerances')
            circuit = "%s_%02d" % (self.circuit, counter + 1)
            if m_feature.get('tolerance', None) == 'brain':
                board_val_reg = m_feature['val_reg'] + counter
                _ai = AnalogInput(circuit, self, board_val_reg,
                                  regmode=m_feature['mode_reg'],
                                  dev_id=self.dev_id, major_group=0, tolerances=tolerances, modes=m_feature['modes'], legacy_mode=self.legacy_mode)
            elif (m_feature.get('type') == "AI18" ):
                board_val_reg = m_feature['val_reg'] + counter * 2
                _ai = AnalogInput18(circuit, self, board_val_reg,
                                  regmode=m_feature['mode_reg'] + counter,
                                  dev_id=self.dev_id, major_group=0, modes=m_feature['modes'])
            else:
                board_val_reg = m_feature['val_reg'] + counter * 2
                _ai = AnalogInput(circuit, self, board_val_reg,
                                  regmode=m_feature['mode_reg'] + counter if m_feature.get('mode_reg', None) is not None else None,
                                  dev_id=self.dev_id, major_group=0, tolerances=tolerances, modes=m_feature['modes'], legacy_mode=self.legacy_mode)

            if board_val_reg in self.modbus_slave.datadeps:
                self.modbus_slave.datadeps[board_val_reg]+=[_ai]
            else:
                self.modbus_slave.datadeps[board_val_reg] = [_ai]
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
            if board_val_reg and ((board_val_reg + counter) in self.modbus_slave.datadeps):
                self.modbus_slave.datadeps[board_val_reg + counter] += [_reg]
            elif board_val_reg:
                self.modbus_slave.datadeps[board_val_reg + counter] = [_reg]
            Devices.register_device(REGISTER, _reg)
            counter+=1

    def parse_feature_uart(self, max_count: int, m_feature: dict, board_id):
        counter = 0
        while counter < max_count:
            board_val_reg = m_feature['conf_reg']
            address_reg = int(m_feature.get('address_reg', -1))
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
        elif m_feature['type'] == 'REGISTER':
            self.parse_feature_register(max_count, m_feature, board_id)
        elif m_feature['type'] == 'UART':
            self.parse_feature_uart(max_count, m_feature, board_id)
        elif m_feature['type'] == 'UNIT_REGISTER':
            self.parse_feature_unit_register(max_count, m_feature, board_id)
        elif m_feature['type'] == 'EXT_CONFIG':
            self.parse_feature_ext_config(m_feature, board_id)
        else:
            logging.error("Unknown feature: " + str(m_feature) + " at board id: " + str(board_id))

    async def parse_definition(self, hw_dict):
        try:
            for defin in hw_dict.definitions:
                if defin and (self.modbus_slave.device_model == defin['type']):
                    await self.initialise_cache(defin);
                    for m_feature in defin['modbus_features']:
                        self.parse_feature(m_feature)
                    return
            logging.error(f"Not found type '{self.modbus_slave.device_model}' in loaded hw-definitions.")
        except ENoCacheRegister as E:
            raise ModbusSlaveError(f"Error while parsing HW definition. ({E}) \t Please check your configuration file.")

    def get(self):
        return self.full()


class Relay(object):
    pending_id = 0
    def __init__(self, circuit, arm, coil, reg, mask, dev_id=0, major_group=0, pwmcyclereg=-1, pwmprescalereg=-1, pwmdutyreg=-1, legacy_mode=True, digital_only=False, modes=['Simple']):
        self.alias = ""
        self.devtype = RELAY
        self.dev_id = dev_id
        self.circuit = circuit
        self.arm = arm
        self.modes = modes
        self.pwmcyclereg = pwmcyclereg
        self.pwmprescalereg = pwmprescalereg
        self.pwmdutyreg = pwmdutyreg
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
        self.bitmask = mask
        self.regvalue = lambda: self.arm.modbus_slave.modbus_cache_map.get_register(1, self.valreg, slave=self.arm.modbus_address)[0]
        if self.pwmdutyreg >= 0: # This instance supports PWM mode
            self.pwm_duty_val = (self.arm.modbus_slave.modbus_cache_map.get_register(1, self.pwmdutyreg, slave=self.arm.modbus_address))[0]
            self.pwm_cycle_val = ((self.arm.modbus_slave.modbus_cache_map.get_register(1, self.pwmcyclereg, slave=self.arm.modbus_address))[0] + 1)
            self.pwm_prescale_val = (self.arm.modbus_slave.modbus_cache_map.get_register(1, self.pwmprescalereg, slave=self.arm.modbus_address))[0]
            if (self.pwm_cycle_val > 0) and (self.pwm_prescale_val > 0):
                self.pwm_freq = 48000000 / (self.pwm_cycle_val * self.pwm_prescale_val)
            else:
                self.pwm_freq = 0
            if (self.pwm_duty_val == 0):
                self.pwm_duty = 0
                self.mode = 'Simple'  # Mode field is for backward compatibility, will be deprecated soon
            else:
                logger.info("Pocitam z {} {}".format(self.pwm_cycle_val, self.pwm_duty_val))
                self.pwm_duty = (100 / (float(self.pwm_cycle_val) / float(self.pwm_duty_val)))
                self.pwm_duty = round(self.pwm_duty ,1) if self.pwm_duty % 1 else int(self.pwm_duty)
                self.mode = 'PWM'  # Mode field is for backward compatibility, will be deprecated soon
        else: # This RELAY instance does not support PWM mode (no pwmdutyreg given)
            self.mode = 'Simple'

        self.forced_changes = arm.modbus_slave.evok_config.getbooldef("force_immediate_state_changes", False)

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

    async def set_state(self, value):
        """ Sets new on/off status. Disable pending timeouts
        """
        if self.pending_id:
            IOLoop.instance().remove_timeout(self.pending_id)
            self.pending_id = None
        await self.arm.modbus_slave.client.write_coil(self.coil, 1 if value else 0, slave=self.arm.modbus_address)
        return 1 if value else 0

    def value_delta(self, new_val):
        return (self.regvalue() ^ new_val) & self.bitmask

    async def set(self, value=None, timeout=None, mode=None, pwm_freq=None, pwm_duty=None, alias=None):
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

            other_devs = Devices.by_int(RELAY, major_group=self.major_group)  # All PWM outs in the same group share this registers
            for other_dev in other_devs:
                if other_dev.pwm_duty > 0:
                    other_dev.pwm_freq = self.pwm_freq
                    other_dev.pwm_delay_val = self.pwm_delay_val
                    other_dev.pwm_cycle_val = self.pwm_cycle_val
                    other_dev.pwm_prescale_val = self.pwm_prescale_val
                    await other_dev.set(pwm_duty=other_dev.pwm_duty)

            await self.arm.modbus_slave.client.write_register(self.pwmcyclereg, self.pwm_cycle_val - 1, slave=self.arm.modbus_address)
            await self.arm.modbus_slave.client.write_register(self.pwmprescalereg, self.pwm_prescale_val, slave=self.arm.modbus_address)
            await self.arm.modbus_slave.client.write_register(self.pwmdutyreg, self.pwm_duty_val, slave=self.arm.modbus_address)

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
            await self.arm.modbus_slave.client.write_coil(self.coil, parsed_value, slave=self.arm.modbus_address)
            if self.pwm_duty != 0:
                self.pwm_duty = 0
                await self.arm.modbus_slave.client.write_register(self.pwmdutyreg, self.pwm_duty, slave=self.arm.modbus_address) # Turn off PWM

        # Set PWM Duty
        elif pwm_duty is not None and float(pwm_duty) >= 0.0 and float(pwm_duty) <= 100.0:
            self.pwm_duty = pwm_duty
            self.pwm_duty_val = float(self.pwm_cycle_val) * float(float(self.pwm_duty) / 100.0)
            if self.value != 0:
                self.arm.modbus_slave.client.write_coil(self.coil, 0, slave=self.arm.modbus_address)
            await self.arm.modbus_slave.client.write_register(self.pwmdutyreg, self.pwm_duty_val, slave=self.arm.modbus_address)
            self.mode = 'PWM'

        if alias is not None:
            if Devices.add_alias(alias, self, file_update=True):
                self.alias = alias

        if timeout is None:
            return self.full()

        async def timercallback():
            self.pending_id = None
            await self.arm.modbus_slave.client.write_coil(self.coil, 0 if value else 1, slave=self.arm.modbus_address)

        self.pending_id = IOLoop.instance().add_timeout(
            datetime.timedelta(seconds=float(timeout)), timercallback)

        return self.full()

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
        self.regvalue = lambda: self.arm.modbus_slave.modbus_cache_map.get_register(1, self.valreg, slave=self.arm.modbus_address)[0]
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
        return self.value

    async def set_state(self, value):
        """ Sets new on/off status. Disable pending timeouts
        """
        await self.arm.modbus_slave.client.write_coil(self.coil, 1 if value else 0, slave=self.arm.modbus_address)
        return 1 if value else 0

    async def set(self, value=None, alias=None):
        """ Sets new on/off status. Disable pending timeouts
        """
        if alias is not None:
            if Devices.add_alias(alias, self):
                self.alias = alias
        if value is not None:
            value = int(value)
            await self.arm.modbus_slave.client.write_coil(self.coil, 1 if value else 0, slave=self.arm.modbus_address)
        return self.full()

    def get(self):
        return self.full()


class Watchdog(object):
    def __init__(self, circuit, arm, post, reg, timeout_reg, nv_save_coil=-1, reset_coil=-1, wd_reset_ro_coil=-1, dev_id=0, major_group=0, legacy_mode=True):
        self.alias = ""
        self.devtype = WATCHDOG
        self.dev_id = dev_id
        self.circuit = circuit
        self.arm = arm
        self.major_group = major_group
        self.legacy_mode = legacy_mode
        self.timeoutvalue = lambda: self.arm.modbus_slave.modbus_cache_map.get_register(1, self.toreg, slave=self.arm.modbus_address)
        self.regvalue = lambda: self.arm.modbus_slave.modbus_cache_map.get_register(1, self.toreg, slave=self.arm.modbus_address)[0]
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
               'timeout': self.timeout,
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
            if self.timeoutvalue(): return self.timeoutvalue()[0]
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

    async def set_state(self, value):
        """ Sets new on/off status. Disable pending timeouts
        """
        await self.arm.modbus_slave.client.write_register(self.valreg, 1 if value else 0, slave=self.arm.modbus_address)
        return 1 if value else 0

    async def set(self, value=None, timeout=None, reset=None, nv_save=None, alias=None):
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
            await self.arm.modbus_slave.client.write_coil(self.nv_save_coil, 1, slave=self.arm.modbus_address)
        if value is not None:
            value = int(value)


        await self.arm.modbus_slave.client.write_register(self.valreg, 1 if value else 0, slave=self.arm.modbus_address)

        if not (timeout is None):
            timeout = int(timeout)
            if timeout > 65535:
                timeout = 65535
            await self.arm.modbus_slave.client.write_register(self.toreg, timeout, slave=self.arm.modbus_address)

        if self.reset_coil >= 0 and reset is not None:
            if reset != 0:
                self.nvsavvalue = 0
                await self.arm.modbus_slave.client.write_coil(self.reset_coil, 1, slave=self.arm.modbus_address)
                logger.info("Performed reset of board %s" % self.circuit)

        return self.full()



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
            ret[param] = self._arm.modbus_slave.modbus_cache_map.get_register(1, reg_addr, slave=self._arm.modbus_address, is_input=False)[0]

        return ret

    def get_param(self, par_name):
        return self._arm.modbus_slave.modbus_cache_map.get_register(1, self._params[par_name], slave=self._arm.modbus_address, is_input=False)[0]

    def get(self):
        return self.full()

    def get_state(self):
        """ Returns ( status, is_pending )
              current on/off status is taken from last mcp value without reading it from hardware
              is_pending is Boolean
        """
        return (self.value)

    async def set(self, alias=None, **kwargs):
        """ Sets new on/off status. Disable pending timeouts """
        if alias is not None:
            if Devices.add_alias(alias, self, file_update=True):
                self.alias = alias

        if len(kwargs) > 0:

            for param, value in kwargs.items():
                await self._arm.modbus_slave.client.write_register(self._params[param], int(value), slave=self._arm.modbus_address)

            if isinstance(self.post_write, list):
                for coil in self.post_write:
                    await self._arm.modbus_slave.client.write_coil(coil, 1, slave=self._arm.modbus_address)

        return self.full()


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
            self.valid_mask = lambda: self.arm.modbus_slave.modbus_cache_map.get_register(1, valid_mask, slave=self.arm.modbus_address, is_input=_is_iput)[0]
        else:
            self.valid_mask = None

        if self.datatype is None:
            if factor == 1 and offset == 0: # Reading RAW value - save some CPU time
                self.regvalue = lambda: self.arm.modbus_slave.modbus_cache_map.get_register(1, self.valreg, slave=self.arm.modbus_address, is_input=_is_iput)[0]
            else:
                self.regvalue = lambda: (self.arm.modbus_slave.modbus_cache_map.get_register(1, self.valreg, slave=self.arm.modbus_address, is_input=_is_iput)[0] * self.factor) + self.offset

        elif datatype == "float32":

            # TODO - add factor and offset version
            self.regvalue = lambda: self.__parse_float32(self.arm.modbus_slave.modbus_cache_map.get_register(2, self.valreg, slave=self.arm.modbus_address, is_input=_is_iput))


    def __parse_float32(self, raw_regs):
        ret = float(BinaryPayloadDecoder.fromRegisters(raw_regs, Endian.BIG, Endian.BIG).decode_32bit_float())
        return ret if not math.isnan(ret) else 'NaN'

    async def set(self, value=None, alias=None, **kwargs):
        """ Sets new on/off status. Disable pending timeouts """
        if alias is not None:
            if Devices.add_alias(alias, self, file_update=True):
                self.alias = alias

        raise Exception("Unit_register object is read-only")


        # nastavit to nepujde

        if value is not None:

            self.arm.modbus_slave.client.write_register(self.valreg, int(value), slave=self.arm.modbus_address)

            if isinstance(self.post_write, list):
                for coil in self.post_write:
                    self.arm.modbus_slave.client.write_coil(coil, 1, slave=self.arm.modbus_address)



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
                print("CTU " + str(self.circuit))
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
            self.regvalue = lambda: self.arm.modbus_slave.modbus_cache_map.get_register(1, self.valreg, slave=self.arm.modbus_address, is_input=True)[0]
        else:
            self.regvalue = lambda: self.arm.modbus_slave.modbus_cache_map.get_register(1, self.valreg, slave=self.arm.modbus_address, is_input=False)[0]

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

    async def set_state(self, value):
        """ Sets new on/off status. Disable pending timeouts
        """
        await self.arm.modbus_slave.client.write_register(self.valreg, value if value else 0, slave=self.arm.modbus_address)
        return value if value else 0

    async def set(self, value=None, alias=None):
        """ Sets new on/off status. Disable pending timeouts
        """
        if alias is not None:
            if Devices.add_alias(alias, self, file_update=True):
                self.alias = alias
        if value is not None:
            value = int(value)
            await self.arm.modbus_slave.client.write_register(self.valreg, value if value else 0, slave=self.arm.modbus_address)

        return self.full()

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
        self.regvalue = lambda: self.arm.modbus_slave.modbus_cache_map.get_register(1, self.reg, slave=self.arm.modbus_address)[0]
        self.regcountervalue = self.regdebouncevalue = lambda: None
        if not (regcounter is None): self.regcountervalue = lambda: self.arm.modbus_slave.modbus_cache_map.get_register(1, regcounter, slave=self.arm.modbus_address)[0] + (self.arm.modbus_slave.modbus_cache_map.get_register(1, regcounter + 1, slave=self.arm.modbus_address)[0] << 16)
        if not (regdebounce is None): self.regdebouncevalue = lambda: self.arm.modbus_slave.modbus_cache_map.get_register(1, regdebounce, slave=self.arm.modbus_address)[0]
        self.mode = 'Simple'
        self.ds_mode = 'Simple'
        if 'DirectSwitch' in self.modes:
            curr_ds = self.arm.modbus_slave.modbus_cache_map.get_register(1, self.regmode, slave=self.arm.modbus_address)[0]
            if (curr_ds & self.bitmask) > 0:
                self.mode = 'DirectSwitch'
                curr_ds_pol = self.arm.modbus_slave.modbus_cache_map.get_register(1, self.regpolarity, slave=self.arm.modbus_address)[0]
                curr_ds_tgl = self.arm.modbus_slave.modbus_cache_map.get_register(1, self.regtoggle, slave=self.arm.modbus_address)[0]
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

    async def set(self, debounce=None, mode=None, counter=None, counter_mode=None, ds_mode=None, alias=None):
        if alias is not None:
            if Devices.add_alias(alias, self, file_update=True):
                self.alias = alias

        if mode is not None and mode != self.mode and mode in self.modes:
            self.mode = mode
            if self.mode == 'DirectSwitch':
                curr_ds = await self.arm.modbus_slave.modbus_cache_map.get_register_async(1, self.regmode, slave=self.arm.modbus_address)
                curr_ds_val = curr_ds[0]
                curr_ds_val = curr_ds_val | int(self.bitmask)
                await self.arm.modbus_slave.client.write_register(self.regmode, curr_ds_val, slave=self.arm.modbus_address)
            else:
                curr_ds = await self.arm.modbus_slave.modbus_cache_map.get_register_async(1, self.regmode, slave=self.arm.modbus_address)
                curr_ds_val = curr_ds[0]
                curr_ds_val = curr_ds_val & (~int(self.bitmask))
                await self.arm.modbus_slave.client.write_register(self.regmode, curr_ds_val, slave=self.arm.modbus_address)

        if self.mode == 'DirectSwitch' and ds_mode is not None and ds_mode in self.ds_modes:
            self.ds_mode = ds_mode
            curr_ds_pol = await self.arm.modbus_slave.modbus_cache_map.get_register_async(1, self.regpolarity, slave=self.arm.modbus_address)
            curr_ds_tgl = await self.arm.modbus_slave.modbus_cache_map.get_register_async(1, self.regtoggle, slave=self.arm.modbus_address)
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
            await self.arm.modbus_slave.client.write_register(self.regpolarity, curr_ds_pol_val, slave=self.arm.modbus_address)
            await self.arm.modbus_slave.client.write_register(self.regtoggle, curr_ds_tgl_val, slave=self.arm.modbus_address)

        if counter_mode is not None and counter_mode in self.counter_modes and counter_mode != self.counter_mode:
            self.counter_mode = counter_mode

        if debounce is not None:
            if self.regdebounce is not None:
                await self.arm.modbus_slave.client.write_register(self.regdebounce, int(float(debounce)), slave=self.arm.modbus_address)
        if counter is not None:
            if self.regcounter is not None:
                await self.arm.modbus_slave.client.write_registers(self.regcounter, ((int(float(counter)) & 0xFFFF), (int(float(counter)) >> 16) & 0xFFFF), slave=self.arm.modbus_address)
        return self.full()

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
    def __init__(self, circuit, arm, reg, dev_id=0, parity_modes=['None'], speed_modes=['19200bps'], stopb_modes = ['One'], address_reg=-1, major_group=0, legacy_mode=True):
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
        self.regvalue = lambda: self.arm.modbus_slave.modbus_cache_map.get_register(1, self.valreg, slave=self.arm.modbus_address)[0]
        parity_mode_val = (self.arm.modbus_slave.modbus_cache_map.get_register(1, self.valreg, slave=self.arm.modbus_address)[0]) & self.parity_mask
        speed_mode_val = (self.arm.modbus_slave.modbus_cache_map.get_register(1, self.valreg, slave=self.arm.modbus_address)[0]) & self.speed_mask
        stopb_mode_val = (self.arm.modbus_slave.modbus_cache_map.get_register(1, self.valreg, slave=self.arm.modbus_address)[0]) & self.stopb_mask
        if self.address_reg != -1:
            self.address_val = self.arm.modbus_slave.modbus_cache_map.get_register(1, self.address_reg, slave=self.arm.modbus_address)[0]
            self.addressvalue = lambda: self.arm.modbus_slave.modbus_cache_map.get_register(1, self.address_reg, slave=self.arm.modbus_address)[0]
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

    async def set(self, conf_value=None, parity_mode=None, speed_mode=None, stopb_mode=None, sw_address=None, alias=None):
        val = self.regvalue()
        if conf_value is not None:
            self.arm.modbus_slave.client.write_register(self.valreg, conf_value, slave=self.arm.modbus_address)
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
            self.arm.modbus_slave.client.write_register(self.valreg, val, slave=self.arm.modbus_address)
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
            await self.arm.modbus_slave.client.write_register(self.valreg, val, slave=self.arm.modbus_address)
            self.speed_mode = speed_mode

        if stopb_mode is not None and stopb_mode in self.stopb_modes and stopb_mode != self.stopb_mode:
            val &= ~self.stopb_mask
            if stopb_mode == 'One':
                val = val
            elif stopb_mode == 'Two':
                val |= 0x00000040
            await self.arm.modbus_slave.client.write_register(self.valreg, val, slave=self.arm.modbus_address)
            self.stopb_mode = stopb_mode

        if sw_address is not None and self.address_val != 0:
            await self.arm.modbus_slave.client.write_register(self.address_reg, sw_address, slave=self.arm.modbus_address)

        if alias is not None:
            if Devices.add_alias(alias, self, file_update=True):
                self.alias = alias

        return self.full()

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

    async def get_packets(self):
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

    async def set(self, ap_state=None, eth0_masq=None, alias=None):
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
        return self.full()

    def get(self):
        return self.full()


class AnalogOutputBrain:
    def __init__(self, circuit, arm, reg, regmode=-1, reg_res=0, dev_id=0, major_group=0, legacy_mode=True):
        self.alias = ""
        self.devtype = AO
        self.dev_id = dev_id
        self.circuit = circuit
        self.reg = reg
        self.regmode = regmode
        self.legacy_mode = legacy_mode
        self.reg_res = reg_res
        self.modes = ['Voltage', 'Current', 'Resistance']
        self.arm = arm
        self.major_group = major_group
        self.is_voltage = lambda: bool(self.arm.modbus_slave.modbus_cache_map.get_register(1, self.regmode, slave=self.arm.modbus_address)[0] == 0)
        if self.is_voltage():
            self.mode = 'Voltage'
        elif self.arm.modbus_slave.modbus_cache_map.get_register(1, self.regmode, slave=self.arm.modbus_address)[0] == 1:
            self.mode = 'Current'
        else:
            self.mode = 'Resistance'

    @property
    def value(self):
        try:
            ret = self.arm.modbus_slave.modbus_cache_map.get_register(2, self.reg, slave=self.arm.modbus_address)
            ret = BinaryPayloadDecoder.fromRegisters(ret, Endian.BIG, Endian.LITTLE).decode_32bit_float()
            return float(ret)
        except:
            return 0

    @property
    def res_value(self):
        try:
            ret = self.arm.modbus_slave.modbus_cache_map.get_register(2, self.reg_res, slave=self.arm.modbus_address)
            ret = BinaryPayloadDecoder.fromRegisters(ret, Endian.BIG, Endian.LITTLE).decode_32bit_float()
            return float(ret)
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

    async def set_value(self, value):
        if value < 0:
            value = 0
        # TODO: omezenit horni hodnoty!!!

        builder = BinaryPayloadBuilder(byteorder=Endian.BIG, wordorder=Endian.LITTLE)
        builder.add_32bit_float(float(value))
        value_set = builder.to_registers()

        await self.arm.modbus_slave.client.write_registers(self.reg, values=value_set, slave=self.arm.modbus_address)
        return value

    async def set(self, value=None, mode=None, alias=None):
        if alias is not None:
            if Devices.add_alias(alias, self, file_update=True):
                self.alias = alias
        if mode is not None and mode in self.modes and self.regmode != -1:
            val = self.arm.modbus_slave.modbus_cache_map.get_register(1, self.regmode, slave=self.arm.modbus_address)[0]
            cur_val = self.value
            if mode == "Voltage":
                val = 0
            elif mode == "Current":
                val = 1
            elif mode == "Resistance":
                val = 3
            self.mode = mode
            await self.arm.modbus_slave.client.write_register(self.regmode, val, slave=self.arm.modbus_address)
            if mode == "Voltage" or mode == "Current":
                await self.set_value(cur_val)        # Restore original value (i.e. 1.5V becomes 1.5mA)
        if not (value is None):
            await self.set_value(float(value))  # Restore original value (i.e. 1.5V becomes 1.5mA)
        return self.full()

    def get(self):
        return self.full()

class AnalogOutput():
    def __init__(self, circuit, arm, reg, regmode=-1, dev_id=0, modes=['Voltage'], major_group=0, legacy_mode=True):
        self.alias = ""
        self.devtype = AO
        self.dev_id = dev_id
        self.circuit = circuit
        self.reg = reg
        self.regvalue = lambda: self.arm.modbus_slave.modbus_cache_map.get_register(1, self.reg, slave=self.arm.modbus_address)[0]
        self.regmode = regmode
        self.legacy_mode = legacy_mode
        self.modes = modes
        self.arm = arm
        self.major_group = major_group
        self.offset = 0
        self.is_voltage = lambda: True
        if self.is_voltage():
            self.mode = 'Voltage'
        else:
            self.mode = 'Current'

    @property
    def value(self):
        try:
            return self.regvalue() * 0.0025
        except:
            return 0

    @property
    def res_value(self):
        try:
            return float(self.regvalue()) * 0.0025
        except:
            return 0

    def full(self):
        ret = {'dev': 'ao',
               'circuit': self.circuit,
               'mode': self.mode,
               'modes': self.modes,
               'glob_dev_id': self.dev_id}
        ret['value'] = self.value
        ret['unit'] = (unit_names[VOLT]) if self.is_voltage() else (unit_names[AMPERE])
        if self.alias != '':
            ret['alias'] = self.alias
        return ret

    def simple(self):
        return {'dev': 'ao',
                'circuit': self.circuit,
                'value': self.value}

    async def set_value(self, value):
        valuei = int((float(value) / 0.0025))
        if valuei < 0:
            valuei = 0
        elif valuei > 4095:
            valuei = 4095
        await self.arm.modbus_slave.client.write_register(self.reg, valuei, slave=self.arm.modbus_address)
        return float(valuei) * 0.0025

    async def set(self, value=None, mode=None, alias=None):
        if alias is not None:
            if Devices.add_alias(alias, self, file_update=True):
                self.alias = alias
        if mode is not None and mode in self.modes and self.regmode != -1:
            val = self.arm.modbus_slave.modbus_cache_map.get_register(1, self.regmode, slave=self.arm.modbus_address)[0]
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
            await self.arm.modbus_slave.client.write_register(self.regmode, val, slave=self.arm.modbus_address)
            if mode == "Voltage" or mode == "Current":
                await self.set_value(cur_val)        # Restore original value (i.e. 1.5V becomes 1.5mA)
        if not (value is None):
            await self.set_value(value)
        return self.full()

    def get(self):
        return self.full()



class AnalogInput():
    def __init__(self, circuit, arm, reg, regmode=None, dev_id=0, major_group=0, legacy_mode=True, tolerances='brain', modes=['Voltage']):
        self.alias = ""
        self.devtype = AI
        self.dev_id = dev_id
        self.circuit = circuit
        self.valreg = reg
        self.arm = arm
        self.legacy_mode = legacy_mode
        self.regmode = regmode
        self.modes = modes
        self.mode = 'Voltage'
        self.unit_name = unit_names[VOLT]
        self.tolerances = tolerances
        self.sec_ai_mode = 0
        if self.tolerances == '500series':
            self.sec_ai_mode = self.arm.modbus_slave.modbus_cache_map.get_register(1, self.regmode, slave=self.arm.modbus_address)[0]
            self.mode = self.get_500_series_mode()
            self.unit_name = self.internal_unit
        self.major_group = major_group
        self.is_voltage = lambda: True
        if self.tolerances == 'brain':
            self.is_voltage = lambda: bool(self.arm.modbus_slave.modbus_cache_map.get_register(1, self.regmode, slave=self.arm.modbus_address)[0] == 0)
            if self.is_voltage():
                self.mode = "Voltage"
            else:
                self.mode = "Current"
                self.unit_name = unit_names[AMPERE]
        if self.tolerances == "simple":
            pass
        self.tolerance_mode = self.get_tolerance_mode()

    @property
    def value(self):
        try:
            ret = self.arm.modbus_slave.modbus_cache_map.get_register(2, self.valreg, slave=self.arm.modbus_address)
            ret = BinaryPayloadDecoder.fromRegisters(ret, Endian.BIG, Endian.LITTLE).decode_32bit_float()
            return float(ret)
        except Exception as E:
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
        elif self.tolerances == 'simple':
            return ["10.0"]

    def get_tolerance_mode(self):
        if self.tolerances == 'brain':
            if self.mode == 'voltage':
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
        if self.tolerances == 'simple':
            return "10.0"

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

    async def set(self, mode=None, range=None, alias=None):
        if alias is not None:
            if Devices.add_alias(alias, self, file_update=True):
                self.alias = alias
        if mode is not None and mode in self.modes:
            if self.tolerances == "brain" and mode != self.mode:
                self.mode = mode
                if self.mode == "Voltage":
                    self.unit_name = unit_names[VOLT]
                    await self.arm.modbus_slave.client.write_register(self.regmode, 0, slave=self.arm.modbus_address)
                elif self.mode == "Current":
                    self.unit_name = unit_names[AMPERE]
                    await self.arm.modbus_slave.client.write_register(self.regmode, 1, slave=self.arm.modbus_address)
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
                await self.arm.modbus_slave.client.write_register(self.regmode, self.sec_ai_mode, slave=self.arm.modbus_address)
        if self.tolerances == '500series' and range is not None and range in self.get_tolerance_modes():
            if self.mode == "Voltage":
                self.unit_name = unit_names[VOLT]
            elif self.mode == "Current":
                self.unit_name = unit_names[AMPERE]
            else:
                self.unit_name = unit_names[OHM]
            self.tolerance_mode = range
            self.sec_ai_mode = self.get_500_series_sec_mode()
            await self.arm.modbus_slave.client.write_register(self.regmode, self.sec_ai_mode, slave=self.arm.modbus_address)
        return self.full()

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
        self.raw_mode = self.arm.modbus_slave.modbus_cache_map.get_register(1, self.regmode, slave=self.arm.modbus_address)[0]
        self.mode = self.get_mode()
        self.major_group = major_group
        self.calibration = {'Voltage': 10.0/(1<<18)/0.9772, 'Current': 40.0/(1<<18)}


    @property
    def value(self):
        try:
            U32 = self.arm.modbus_slave.modbus_cache_map.get_register(2, self.valreg, slave=self.arm.modbus_address)
            raw_value = U32[0] | (U32[1] << 16)
            return raw_value if self.tolerance_mode == "Integer 18bit" else float(raw_value)*self.calibration[self.mode]
        except Exception as E:
            logger.exception(str(E))
            return 0

    def get_mode(self):
        if self.raw_mode == 1:
            return "Current"
        else:
            return "Voltage"


    async def set(self, mode=None, range=None, alias=None):
        if alias is not None:
            if Devices.add_alias(alias, self, file_update=True):
                self.alias = alias
        if mode is not None and mode in self.modes:
            self.mode = mode
            if self.mode == "Voltage":
                    self.raw_mode = 0
            elif self.mode == "Current":
                    self.raw_mode = 1
            await self.arm.modbus_slave.client.write_register(self.regmode, self.raw_mode, slave=self.arm.modbus_address)

        if range is not None and range in self.tolerances:
            self.tolerance_mode = range
            if range == "Float":
                self.unit_name = unit_names[AMPERE] if self.mode == "Current" else unit_names[VOLT]
            else:
                self.unit_name = ''

        return self.full()

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

