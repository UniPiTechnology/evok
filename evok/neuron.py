'''
  Neuron primitive devices (DI, DO, AI, AO)
------------------------------------------
'''

import struct
import time
import datetime
# import atexit
from math import isnan, floor

from yaml import load, dump

from tornado import gen
from tornado.ioloop import IOLoop

from modbusclient_tornado import ModbusClientProtocol, StartClient
from pymodbus.pdu import ExceptionResponse

from pymodbus.exceptions import ConnectionException, ModbusIOException
from pymodbus.register_read_message import ReadHoldingRegistersResponse

import pymodbus.client

import modbusclient_rs485

import devents
from devices import *
#from spiarm import ProxyRegister

from log import *

import config 
from time import sleep
from modbusclient_rs485 import AsyncErrorResponse

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
	def __init__(self, circuit, Config, modbus_server, modbus_port, scan_freq, scan_enabled, hw_dict, direct_access=False, dev_id=0):
		self.dev_id = dev_id
		self.circuit = circuit
		self.hw_dict = hw_dict
		self.Config = Config
		self.direct_access = direct_access
		self.modbus_server = modbus_server
		self.modbus_port = modbus_port
		self.modbus_address = circuit
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
		# start modus/tcp modbusclient_rs485. On connect call self.readboards
		loop.add_callback(lambda: StartClient(self.client, self.modbus_server, self.modbus_port, self.readboards))

	@gen.coroutine
	def readboards(self):
		""" Try to read version registers on 3 boards and create subdevices """
		# ToDo - destroy all boards and subdevices before creating
		print "READING BOARDS SPI"
		for board in self.boards:
			del (board)
		self.boards = list()
		for i in (1, 2, 3):
			try:
				versions = yield self.client.read_input_registers(1000, 10, unit=i)
				if isinstance(versions, ExceptionResponse):
					raise ENoBoard("bad request")
				print versions.registers
				print type(versions)
				board = Board(self.Config, i, self, versions.registers, direct_access=self.direct_access, dev_id=self.dev_id)
				data = yield self.client.read_input_registers(0, count=board.ndataregs, unit=i)
				if i == 2:
					configs = yield self.client.read_input_registers(1000, count=20, unit=i)
				else: 
					configs = yield self.client.read_input_registers(1000, count=board.nconfigregs, unit=i)
				print board.ndataregs
				print board.nconfigregs
				board.parse_definition(data.registers, configs.registers, self.hw_dict, i)
				self.boards.append(board)
			except ENoBoard:
				print "NOBOARD"
				continue
			except Exception, E:
				logger.exception(str(E))
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

	def full(self):
		return {'dev': 'neuron', 'circuit': self.circuit, 'model': config.globals['model'], 'sn': config.globals['serial'], 'ver2': config.globals['version2']}
		
	
	@gen.coroutine
	def scan_boards(self):
		if self.client.connected:
			print "ERGO " + str(len(self.boards))
			try:
				for board in self.boards:
					data = yield self.client.read_input_registers(0, count=board.ndataregs, unit=board.modbus_address)
					if isinstance(data, ExceptionResponse):
						raise Exception("Wrong request")
					print data.registers
					board.set_data(0, data.registers)
			except Exception, E:
				logger.exception(str(E))
		if self.do_scanning and (self.scan_interval != 0):
			self.loop.call_later(self.scan_interval, self.scan_boards)
			self.is_scanning = True
		else:
			self.is_scanning = False

class UartNeuron(object):
	def __init__(self, circuit, Config, port, scan_freq, scan_enabled, hw_dict, baud_rate=19200, parity='N', stopbits=1, uart_address=15, device_name='unspecified', direct_access=False, dev_id=0):
		self.boards = list()
		self.dev_id = dev_id
		self.circuit = "RS485_" + str(uart_address) + "_" + str(circuit)
		self.hw_dict = hw_dict
		self.port = port
		self.direct_access = direct_access
		self.modbus_address = uart_address
		self.device_name = device_name
		self.Config = Config
		self.do_scanning = False
		self.is_scanning = False
		self.baud_rate = baud_rate
		self.parity = parity
		self.stopbits = stopbits
		self.hw_board_dict = {}
		if scan_freq == 0:
			self.scan_interval = 0
		else:
			self.scan_interval = 1.0 / scan_freq
		self.scan_enabled = scan_enabled

	def switch_to_async(self, loop):
		self.loop = loop
		if self.port in modbusclient_rs485.client_dict:
			self.client = modbusclient_rs485.client_dict[self.port]
		else:
			self.client = modbusclient_rs485.AsyncModbusGeneratorClient(method='rtu', stopbits=self.stopbits, bytesize=8, parity=self.parity, baudrate=self.baud_rate, timeout=1.5, port=self.port)
			modbusclient_rs485.client_dict[self.port] = self.client
		#self.client.connect()
		#self.client = AsyncModbusSerialClient(port="/dev/ttyNS0")
		# start modus/tcp modbusclient_rs485. On connect call self.readboards
		#modbusclient_rs485.UartStartClient(self.client, self.readboards)
		#self.client = pymodbus.client.sync.ModbusSerialClient(method='rtu', stopbits=self.stopbits, bytesize=8, parity=self.parity, baudrate=self.baud_rate, timeout=0.05, port=self.port)
		#self.client.connect()
		#while (True):
		#	reply = self.client.read_input_registers(address=0, count=20, unit=15)
		#	print reply.registers
		loop.add_callback(lambda: modbusclient_rs485.UartStartClient(self, self.readboards))

	@gen.coroutine
	def readboards(self):
		""" Try to read version registers on 3 boards and create subdevices """
		# ToDo - destroy all boards and subdevices before creating
		for board in self.boards:
			del (board)
		print "READING BOARDS UART"
		self.boards = list()
		try:
			for defin in self.hw_dict.definitions:
				if defin and (defin['type'] == self.device_name):
					self.hw_board_dict = defin
					break
				
			if "first_board_conf_count" not in self.hw_board_dict:
				self.hw_board_dict['first_board_conf_count'] = 0
			if "first_board_data_count" not in self.hw_board_dict:
				self.hw_board_dict['first_board_data_count'] = 0
			
			versions = yield self.client.read_input_registers(1000, self.hw_board_dict['first_board_conf_count'], unit=self.modbus_address)
			#print versions
			#print type(versions)
			#logger.debug(type(versions))
			#logger.debug(versions.registers)
			if isinstance(versions, ExceptionResponse):
				board = UartBoard(self.Config, self.circuit, self.modbus_address, self, [0, 0, 0, 0, 0, 0, 0, 0, 0, 0], dev_id=self.dev_id)
			elif isinstance(versions, AsyncErrorResponse):
				board = UartBoard(self.Config, self.circuit, self.modbus_address, self, [0, 0, 0, 0, 0, 0, 0, 0, 0, 0], dev_id=self.dev_id)
			else:
				board = UartBoard(self.Config, self.circuit, self.modbus_address, self, versions.registers, dev_id=self.dev_id)
			data = yield self.client.read_input_registers(0, count=self.hw_board_dict['first_board_data_count'], unit=self.modbus_address)
			#print data.registers
			configs = yield self.client.read_input_registers(1000, count=self.hw_board_dict['first_board_conf_count'], unit=self.modbus_address)
			#print "ccc %d" % 1
			#print configs.registers
			board.parse_definition(data, configs, self.hw_dict, 1)
			self.boards.append(board)
		except ENoBoard:
			print "No Board"
		except Exception, E:
			logger.exception(str(E))
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

	def full(self):
		return {'dev': 'neuron', 'circuit': self.circuit}
		
	
	@gen.coroutine
	def scan_boards(self):
		print "Number of boards scanned: " + str(len(self.boards)) 
		try:
			yield self.client.read_input_registers(address=0, count=10, unit=self.modbus_address)
			for board in self.boards:
				print "Number of datadeps: " + str(len(board.datadeps))
				data = yield self.client.read_input_registers(0, count=len(board.datadeps), unit=board.modbus_address)
				if isinstance(data, ExceptionResponse):
					raise Exception("Wrong request")
				elif isinstance(data, AsyncErrorResponse):
					raise Exception("Wrong UART request")
				board.set_data(0, data.registers)
		except Exception, E:
			logger.exception(str(E))
		if self.do_scanning and (self.scan_interval != 0):
			#self.loop.call_later(self.scan_interval, self.scan_boards)
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


class UartBoard(object):
	def __init__(self, Config, circuit, modbus_address, neuron, versions, direct_access=False, dev_id=0):
		self.dev_id = dev_id
		self.Config = Config
		self.circuit = circuit
		self.direct_access = direct_access
		self.legacy_mode = not (Config.getbooldef('MAIN','use_experimental_api',False))
		self.neuron = neuron
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
		self.nai2 = 0 if self.hw != 0 else 1  # Voltage only AI
		#self.ndataregs = self.get_base_reg(0, 'ALL')
		#self.nconfigregs = self.get_base_reg(1000, 'ALL') - 1000
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


#

	def parse_definition(self, data, configs, hw_dict, board_id):
		if isinstance(data, ExceptionResponse) or isinstance(data, AsyncErrorResponse):
			self.data = []
		else:
			self.data = data.registers
		
		if isinstance(configs, ExceptionResponse) or isinstance(configs, AsyncErrorResponse):
			self.configs = []
		else:
			self.configs = configs.registers
		self.datadeps = {} #[set() for _ in range(len(data))]
		if (self.sw != 0 and self.hw == 0):
				self.volt_refx = (3.3 * configs[9])
				self.volt_ref = (3.3 * configs[9]) / data[5]
		else:
			self.volt_refx = 33000
			self.volt_ref = 3.3

		#print "test2 %d" % board_id
		#base = self.get_base_reg(0, 'DI')
		#base_deb = self.get_base_reg(1000, 'DEB') - 1000
		#base_counter = self.get_base_reg(0, 'CNT')
		#print "test3 %d" % board_id
		
		#print hw_dict.definitions
		#print config.globals['model']
		for defin in hw_dict.definitions:
			#try:
				#print defin['type']
				if defin and (defin['type'] == self.neuron.device_name):
					#print defin['type']
					#print len(defin)
					self.ndataregs = defin['first_board_data_count']
					self.nconfigregs = defin['first_board_conf_count']
					for m_feature in defin['modbus_features']:
						#print m_feature
						counter = 0
						max_count = m_feature['count'] 
						if m_feature['type'] == 'DI' and m_feature['major_group'] == board_id:
							#print m_feature['type']
							#print m_feature['count']
							while counter < max_count:
								board_val_reg = m_feature['val_reg'] - (100 * (board_id - 1))
								board_counter_reg = m_feature['counter_reg'] - (100 * (board_id - 1))
								board_deboun_reg = m_feature['deboun_reg'] - (100 * (board_id - 1))
								_inp = Input("%s_%02d" % (self.circuit, counter + 1), self, board_val_reg, 0x1 << (counter % 16),
											 regdebounce=board_deboun_reg + counter, regcounter=board_counter_reg + (2 * counter))
								#logging.info("Registered DI %02d" % counter + 1)
								#print m_feature['count']
								if self.datadeps.has_key(board_val_reg):
									self.datadeps[board_val_reg]+=[_inp]
								else:
									self.datadeps[board_val_reg] = [_inp]
								if self.datadeps.has_key(board_counter_reg + (2 * counter)):
									self.datadeps[board_counter_reg + (2 * counter)]+=[_inp]
								else:
									self.datadeps[board_counter_reg + (2 * counter)] = [_inp]
								counter+=1
								#print counter
								Devices.register_device(INPUT, _inp)
						elif (m_feature['type'] == 'RO' or m_feature['type'] == 'DO') and m_feature['major_group'] == board_id:
							#print m_feature['type']
							#print m_feature['count']
							while counter < max_count:
								board_val_reg = m_feature['val_reg'] - (100 * (board_id - 1))
								_r = Relay("%s_%02d" % (self.circuit, counter + 1), self, counter, board_val_reg, 0x1 << (counter % 16))
								if self.datadeps.has_key(board_val_reg):
									self.datadeps[board_val_reg]+=[_r]
								else:
									self.datadeps[board_val_reg] = [_r]
								Devices.register_device(RELAY, _r)
								counter+=1
								#print counter
						elif m_feature['type'] == 'LED' and m_feature['major_group'] == board_id:
							#print m_feature['type']
							#print m_feature['count']
							while counter < max_count:
								board_val_reg = m_feature['val_reg'] - (100 * (board_id - 1))
								_led = ULED("%s_%02d" % (self.circuit, counter + 1), self, counter, board_val_reg, 0x1 << (counter % 16), m_feature['val_coil'] + counter)
								if self.datadeps.has_key(board_val_reg + counter):
									self.datadeps[board_val_reg + counter]+=[_led]
								else:
									self.datadeps[board_val_reg + counter] = [_led]
								Devices.register_device(LED, _led)
								counter+=1
						elif m_feature['type'] == 'WD' and m_feature['major_group'] == board_id:
							#print m_feature['type']
							#print m_feature['count']
							while counter < max_count:
								board_val_reg = m_feature['val_reg'] - (100 * (board_id - 1))
								board_timeout_reg = m_feature['timeout_reg'] - (100 * (board_id - 1)) - 1000
								_wd = Watchdog("%s_%02d" % (self.circuit, counter + 1), self, counter, board_val_reg + counter, board_timeout_reg + counter, dev_id=0)
								if self.datadeps.has_key(board_val_reg + counter):
									self.datadeps[board_val_reg + counter]+=[_wd]
								else:
									self.datadeps[board_val_reg + counter] = [_wd]
								Devices.register_device(WATCHDOG, _wd)
								counter+=1						
						elif m_feature['type'] == 'AO' and m_feature['major_group'] == board_id:
							#print m_feature['type']
							#print m_feature['count']
							while counter < max_count:
								board_val_reg = m_feature['val_reg'] - (100 * (board_id - 1))
								if m_feature.has_key('cal_reg'):
									_ao = AnalogOutput("%s_%02d" % (self.circuit, counter + 1), self, board_val_reg + counter, regcal=m_feature['cal_reg'] + 1, regmode=m_feature['mode_reg'], reg_res=m_feature['res_val_reg'], modes=m_feature['modes'])
								else:
									_ao = AnalogOutput("%s_%02d" % (self.circuit, counter + 1), self, board_val_reg + counter)
								if self.datadeps.has_key(board_val_reg + counter):
									self.datadeps[board_val_reg + counter]+=[_ao]
								else:
									self.datadeps[board_val_reg + counter] = [_ao]
								Devices.register_device(AO, _ao)
								counter+=1
								print counter
						elif m_feature['type'] == 'AI' and m_feature['major_group'] == board_id:
							#print m_feature['type']
							#print m_feature['count']
							while counter < max_count:
								board_val_reg = m_feature['val_reg'] - (100 * (board_id - 1))
								if m_feature.has_key('cal_reg'):
									_ai = AnalogInput("%s_%02d" % (self.circuit, counter + 1), self, board_val_reg + counter, regcal=m_feature['cal_reg'] + 4)
								else:
									_ai = AnalogInput("%s_%02d" % (self.circuit, counter + 1), self, board_val_reg + counter * 2)
								if self.datadeps.has_key(board_val_reg + counter):
									self.datadeps[board_val_reg + counter]+=[_ai]
								else:
									self.datadeps[board_val_reg + counter] = [_ai]
								Devices.register_device(AI, _ai)
								counter+=1
								#print counter
						elif m_feature['type'] == 'REGISTER' and m_feature['major_group'] == board_id and self.direct_access:
							while counter < max_count:
								board_val_reg = m_feature['start_reg'] - (100 * (board_id - 1))
								_reg = Register("%s_%02d" % (self.circuit, counter + 1), self, counter, board_val_reg + counter, dev_id=0)
								if board_val_reg < 1000 and self.datadeps.has_key(board_val_reg + counter):
									self.datadeps[board_val_reg + counter] += [_reg]
								elif board_val_reg < 1000:
									self.datadeps[board_val_reg + counter] = [_reg]
								Devices.register_device(REGISTER, _reg)
								counter+=1
								#print counter
						elif m_feature['type'] == 'UART' and m_feature['major_group'] == board_id:
							#print m_feature['type']
							#print m_feature['count']
							while counter < max_count:
								board_val_reg = m_feature['conf_reg'] - (100 * (board_id - 1))
								_uart = Uart("%s_%02d" % (self.circuit, counter + 1), self, board_val_reg + counter, dev_id=0)
								Devices.register_device(UART, _uart)
								counter+=1
								#print counter
															
							
							
			#except KeyError, E:
			#	continue

	def set_data(self, register, data):
		# ToDo!
		changeset = []
		print data
		for i in range(len(data)):
			try:
				if data[i] == self.data[i]: continue
			except:
				pass
			if self.datadeps.has_key(i):
				changeset += self.datadeps[i]  # add devices to set

		self.data = data
		if len(changeset) > 0:
			proxy = Proxy(set(changeset))
			devents.status(proxy)


class Board(object):
	def __init__(self, Config, circuit, neuron, versions, dev_id=0, direct_access=False):
		self.dev_id = dev_id
		self.Config = Config
		self.circuit = circuit
		self.direct_access = direct_access
		self.legacy_mode = not (Config.getbooldef('MAIN','use_experimental_api',False))
		self.modbus_address = circuit
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


#

	def parse_definition(self, data, configs, hw_dict, board_id):
		self.data = data
		#print "test1 %d" % board_id
		self.configs = configs
		self.datadeps = {} #[set() for _ in range(len(data))]
		if (self.hw == 0):
			self.volt_refx = (3.3 * configs[9])
			self.volt_ref = (3.3 * configs[9]) / data[5]
		else:
			self.volt_refx = 33000
			self.volt_ref = 3.3
		#print "test2 %d" % board_id
		#base = self.get_base_reg(0, 'DI')
		#base_deb = self.get_base_reg(1000, 'DEB') - 1000
		#base_counter = self.get_base_reg(0, 'CNT')
		#print "test3 %d" % board_id
		
		#print hw_dict.definitions
		#print config.globals['model']
		for defin in hw_dict.definitions:
			#try:
				#print defin['type']
				if defin and defin['type'] in config.globals['model']:
					#print defin['type']
					#print len(defin)
					for m_feature in defin['modbus_features']:
						#print m_feature
						counter = 0
						max_count = m_feature['count'] 
						if m_feature['type'] == 'DI' and m_feature['major_group'] == board_id:
							while counter < max_count:
								board_val_reg = m_feature['val_reg'] - (100 * (board_id - 1))
								board_counter_reg = m_feature['counter_reg'] - (100 * (board_id - 1))
								board_deboun_reg = m_feature['deboun_reg'] - (100 * (board_id - 1))
								_inp = Input("%s_%02d" % (self.circuit, counter + 1), self, board_val_reg, 0x1 << (counter % 16),
											 regdebounce=board_deboun_reg + counter, regcounter=board_counter_reg + (2 * counter),
											 dev_id=self.dev_id, legacy_mode=self.legacy_mode)
								if self.datadeps.has_key(board_val_reg):
									self.datadeps[board_val_reg]+=[_inp]
								else:
									self.datadeps[board_val_reg] = [_inp]
								if self.datadeps.has_key(board_counter_reg + (2 * counter)):
									self.datadeps[board_counter_reg + (2 * counter)]+=[_inp]
								else:
									self.datadeps[board_counter_reg + (2 * counter)] = [_inp]
								Devices.register_device(INPUT, _inp)
								counter+=1
						elif (m_feature['type'] == 'RO' or m_feature['type'] == 'DO') and m_feature['major_group'] == board_id:
							while counter < max_count:
								board_val_reg = m_feature['val_reg'] - (100 * (board_id - 1))
								_r = Relay("%s_%02d" % (self.circuit, counter + 1), self, counter, board_val_reg, 0x1 << (counter % 16),
										   dev_id=self.dev_id, legacy_mode=self.legacy_mode)
								if self.datadeps.has_key(board_val_reg):
									self.datadeps[board_val_reg]+=[_r]
								else:
									self.datadeps[board_val_reg] = [_r]
								Devices.register_device(RELAY, _r)
								counter+=1
						elif m_feature['type'] == 'LED' and m_feature['major_group'] == board_id:
							while counter < max_count:
								board_val_reg = m_feature['val_reg'] - (100 * (board_id - 1))
								_led = ULED("%s_%02d" % (self.circuit, counter + 1), self, counter, board_val_reg, 0x1 << (counter % 16), m_feature['val_coil'] + counter,
										    dev_id=self.dev_id, legacy_mode=self.legacy_mode)
								if self.datadeps.has_key(board_val_reg + counter):
									self.datadeps[board_val_reg + counter]+=[_led]
								else:
									self.datadeps[board_val_reg + counter] = [_led]
								Devices.register_device(LED, _led)
								counter+=1
						elif m_feature['type'] == 'WD' and m_feature['major_group'] == board_id:
							while counter < max_count:
								board_val_reg = m_feature['val_reg'] - (100 * (board_id - 1))
								board_timeout_reg = m_feature['timeout_reg'] - (100 * (board_id - 1)) - 1000
								_wd = Watchdog("%s_%02d" % (self.circuit, counter + 1), self, counter, board_val_reg + counter, board_timeout_reg + counter,
											   dev_id=self.dev_id, legacy_mode=self.legacy_mode)
								if self.datadeps.has_key(board_val_reg + counter):
									self.datadeps[board_val_reg + counter]+=[_wd]
								else:
									self.datadeps[board_val_reg + counter] = [_wd]
								Devices.register_device(WATCHDOG, _wd)
								counter+=1						
						elif m_feature['type'] == 'AO' and m_feature['major_group'] == board_id:
							while counter < max_count:
								board_val_reg = m_feature['val_reg'] - (100 * (board_id - 1))
								if m_feature.has_key('cal_reg'):
									_ao = AnalogOutput("%s_%02d" % (self.circuit, counter + 1), self, board_val_reg + counter, regcal=m_feature['cal_reg'] + 1,
													   regmode=m_feature['mode_reg'], reg_res=m_feature['res_val_reg'], modes=m_feature['modes'],
													   dev_id=self.dev_id, legacy_mode=self.legacy_mode)
								else:
									_ao = AnalogOutput("%s_%02d" % (self.circuit, counter + 1), self, board_val_reg + counter, dev_id=self.dev_id,
													   legacy_mode=self.legacy_mode)
								if self.datadeps.has_key(board_val_reg + counter):
									self.datadeps[board_val_reg + counter]+=[_ao]
								else:
									self.datadeps[board_val_reg + counter] = [_ao]
								Devices.register_device(AO, _ao)
								counter+=1
								print counter
						elif m_feature['type'] == 'AI' and m_feature['major_group'] == board_id:
							while counter < max_count:
								board_val_reg = m_feature['val_reg'] - (100 * (board_id - 1))
								if m_feature.has_key('cal_reg'):
									_ai = AnalogInput("%s_%02d" % (self.circuit, counter + 1), self, board_val_reg + counter, regcal=m_feature['cal_reg'] + 4,
													  dev_id=self.dev_id, legacy_mode=self.legacy_mode)
								else:
									_ai = AnalogInput("%s_%02d" % (self.circuit, counter + 1), self, board_val_reg + counter * 2, dev_id=self.dev_id,
													  legacy_mode=self.legacy_mode)
								if self.datadeps.has_key(board_val_reg + counter):
									self.datadeps[board_val_reg + counter]+=[_ai]
								else:
									self.datadeps[board_val_reg + counter] = [_ai]
								Devices.register_device(AI, _ai)
								counter+=1
						elif m_feature['type'] == 'REGISTER' and m_feature['major_group'] == board_id and self.direct_access:
							while counter < max_count:
								board_val_reg = m_feature['start_reg'] - (100 * (board_id - 1))
								_reg = Register("%s_%02d" % (self.circuit, counter + 1), self, counter, board_val_reg + counter, dev_id=self.dev_id,
											    legacy_mode=self.legacy_mode)
								if board_val_reg < 1000 and self.datadeps.has_key(board_val_reg + counter):
									self.datadeps[board_val_reg + counter] += [_reg]
								elif board_val_reg < 1000:
									self.datadeps[board_val_reg + counter] = [_reg]
								Devices.register_device(REGISTER, _reg)
								counter+=1
						elif m_feature['type'] == 'UART' and m_feature['major_group'] == board_id:
							while counter < max_count:
								board_val_reg = m_feature['conf_reg'] - (100 * (board_id - 1))
								_uart = Uart("%s_%02d" % (self.circuit, counter + 1), self, board_val_reg + counter, dev_id=self.dev_id,
											 legacy_mode=self.legacy_mode)
								Devices.register_device(UART, _uart)
								counter+=1

	def set_data(self, register, data):
		# ToDo!
		changeset = []
		print data
		for i in range(len(data)):
			try:
				if data[i] == self.data[i]: continue
			except:
				logger.exception("invalid data scanned")
			if self.datadeps.has_key(i):
				changeset += self.datadeps[i]  # add devices to set

		print changeset
		self.data = data
		if len(changeset) > 0:
			proxy = Proxy(set(changeset))
			devents.status(proxy)


class Relay(object):
	pending_id = 0
	
	def __init__(self, circuit, arm, coil, reg, mask, dev_id=0, legacy_mode=True):
		self.dev_id = dev_id
		self.circuit = circuit
		self.arm = arm
		self.legacy_mode = legacy_mode
		self.coil = coil
		self.bitmask = mask
		self.regvalue = lambda: arm.data[reg]

	def full(self):
		if self.legacy_mode:
			return {'dev': 'relay', 'circuit': self.circuit, 'value': self.value, 'pending': self.pending_id != 0}
		else:
			return {'dev': 'relay', 'circuit': self.circuit, 'value': self.value, 'pending': self.pending_id != 0, 'glob_dev_id': self.dev_id}

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
		yield self.arm.neuron.client.write_coil(self.coil, 1 if value else 0, unit=self.arm.modbus_address)
		raise gen.Return(1 if value else 0)

	def set(self, value=None, timeout=None):
		""" Sets new on/off status. Disable pending timeouts
		"""
		if value is None:
			raise Exception('Value must be specified')
		value = int(value)
		if not (timeout is None):
			timeout = float(timeout)

		self.arm.neuron.client.write_coil(self.coil, 1 if value else 0, unit=self.arm.modbus_address)

		if timeout is None:
			return (1 if value else 0)

		def timercallback():
			self.pending_id = None
			self.arm.write_bit(self.coil, 0 if value else 1, unit=self.arm.modbus_address)

		self.pending_id = IOLoop.instance().add_timeout(
			datetime.timedelta(seconds=float(timeout)), timercallback)
		return (1 if value else 0)
		#return (1 if self.mcp.value & self._mask else 0)

class ULED(object):
	pending_id = 0
	
	def __init__(self, circuit, arm, post, reg, mask, coil, dev_id=0, legacy_mode=True):
		self.dev_id = dev_id
		self.circuit = circuit
		self.arm = arm
		self.legacy_mode = legacy_mode
		self.bitmask = mask
		self.regvalue = lambda: arm.data[reg]
		self.valreg = reg
		self.coil = coil
		#self.regcounter1.devices.add(self)
		#self.regcounter2.devices.add(self)
		#self.regdebounce.devices.add(self)

	def full(self):
		if self.legacy_mode:
			return {'dev': 'led', 'circuit': self.circuit, 'value': self.value}
		else:
			return {'dev': 'led', 'circuit': self.circuit, 'value': self.value, 'glob_dev_id': self.dev_id}

	def simple(self):
		return {'dev': 'led', 'circuit': self.circuit, 'value': self.value}

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
		return (self.value)

	@gen.coroutine
	def set_state(self, value):
		""" Sets new on/off status. Disable pending timeouts
		"""
		yield self.arm.neuron.client.write_coil(self.coil, 1 if value else 0, unit=self.arm.modbus_address)
		raise gen.Return(1 if value else 0)

	def set(self, value=None, timeout=None):
		""" Sets new on/off status. Disable pending timeouts
		"""
		if value is None:
			raise Exception('Value must be specified')
		value = int(value)
		self.arm.neuron.client.write_coil(self.coil, 1 if value else 0, unit=self.arm.modbus_address)
		return (1 if value else 0)
		#return (1 if self.mcp.value & self._mask else 0)


class Watchdog(object):
	
	def __init__(self, circuit, arm, post, reg, timeout_reg, dev_id=0, legacy_mode=True):
		self.dev_id = dev_id
		self.circuit = circuit
		self.arm = arm
		self.legacy_mode = legacy_mode
		self.timeoutvalue = lambda: arm.configs[timeout_reg]
		self.regvalue = lambda: arm.data[reg]
		self.valreg = reg
		self.toreg = timeout_reg

	def full(self):
		if self.legacy_mode:
			return {'dev': 'wd', 'circuit': self.circuit, 'value': self.regvalue(), 'timeout': self.timeoutvalue()}
		else:
			return {'dev': 'wd', 'circuit': self.circuit, 'value': self.regvalue(), 'timeout': self.timeoutvalue(), 'glob_dev_id': self.dev_id}			

	def simple(self):
		return {'dev': 'wd', 'circuit': self.circuit, 'value': self.regvalue()}

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
	def set(self, value=None, timeout=None):
		""" Sets new on/off status. Disable pending timeouts
		"""
		if value is None:
			raise Exception('Value must be specified')
		value = int(value)
		if not (timeout is None):
			timeout = int(timeout)
			if timeout > 65535:
				timeout = 65535
			self.arm.neuron.client.write_register(self.toreg + 1000, timeout, unit=self.arm.modbus_address)
			self.arm.configs[self.toreg] = timeout
		self.arm.neuron.client.write_register(self.valreg, 1 if value else 0, unit=self.arm.modbus_address)
		raise gen.Return(1 if value else 0)
		#return (1 if self.mcp.value & self._mask else 0)


class Register():
	def __init__(self, circuit, arm, post, reg, reg_type="input", dev_id=0, legacy_mode=True):
		self.dev_id = dev_id
		self.circuit = circuit
		self.arm = arm
		self.legacy_mode = legacy_mode
		self.regvalue = lambda: arm.data[reg]
		self.valreg = reg
		self.reg_type = reg_type

	def full(self):
		if self.legacy_mode:
			return {'dev': 'register', 'circuit': self.circuit, 'value': self.regvalue()}
		else:
			return {'dev': 'register', 'circuit': self.circuit, 'value': self.regvalue(), 'glob_dev_id': self.dev_id}			
		

	def simple(self):
		return {'dev': 'register', 'circuit': self.circuit, 'value': self.regvalue()}


	@property
	def value(self):
		try:
			if self.regvalue(): 
				return self.regvalue()
		except:
			pass
		return 0

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
	def set(self, value=None, timeout=None):
		""" Sets new on/off status. Disable pending timeouts
		"""
		if value is None:
			raise Exception('Value must be specified')
		value = int(value)
		self.arm.neuron.client.write_register(self.valreg, value if value else 0, unit=self.arm.modbus_address)
		raise gen.Return(value if value else 0)
	

class Input():
	def __init__(self, circuit, arm, reg, mask, regcounter=None, regdebounce=None, dev_id=0, legacy_mode=True):
		self.dev_id = dev_id
		self.circuit = circuit
		self.arm = arm
		self.legacy_mode = legacy_mode
		self.bitmask = mask
		self.counterreg = regcounter
		self.debouncereg = regdebounce
		self.regvalue = lambda: arm.data[reg]
		self.regcountervalue = self.regdebouncevalue = lambda: None
		if not (regcounter is None): self.regcountervalue = lambda: arm.data[regcounter] + (
			arm.data[regcounter + 1] << 16)
		if not (regdebounce is None): self.regdebouncevalue = lambda: arm.configs[regdebounce - 1000]
		self.counter_mode = "disabled"

	@property
	def debounce(self):
		try:
			return self.regdebouncevalue()
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
		if self.legacy_mode:
			return {'dev': 'input', 'circuit': self.circuit, 'value': self.value,
					'debounce': self.debounce, 'counter_mode': self.counter_mode,
					'counter': self.counter}
		else:
			return {'dev': 'input', 'circuit': self.circuit, 'value': self.value,
					'debounce': self.debounce, 'counter_mode': self.counter_mode,
					'counter': self.counter, 'glob_dev_id': self.dev_id}			

	def simple(self):
		return {'dev': 'input', 'circuit': self.circuit, 'value': self.value}

	@gen.coroutine
	def set(self, debounce=None, counter=None):
		if not (debounce is None):
			if not (self.debouncereg is None):
				print [self.debouncereg, debounce, self.arm.modbus_address]
				self.arm.neuron.client.write_register(self.debouncereg, int(float(debounce)), self.arm.modbus_address)
				#devents.config(self)
		if not (counter is None):
			if not (self.counterreg is None):
				self.arm.neuron.client.write_register(self.counterreg, int(float(counter)), self.arm.modbus_address)
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

class Uart():
	def __init__(self, circuit, arm, reg, dev_id=0, legacy_mode=True):
		self.dev_id = dev_id
		self.circuit = circuit
		self.legacy_mode = legacy_mode
		self.arm = arm
		self.regvalue = lambda: arm.configs[reg - 1000]
		self.valreg = reg

	@property
	def conf(self):
		try:
			if self.regvalue(): return self.regvalue()
		except:
			pass
		return 0

	def full(self):
		if self.legacy_mode:
			return {'dev': 'uart', 'circuit': self.circuit, 'conf': self.conf}
		else:
			return {'dev': 'uart', 'circuit': self.circuit, 'conf': self.conf, 'glob_dev_id': self.dev_id}

	def simple(self):
		return {'dev': 'uart', 'circuit': self.circuit, 'conf': self.conf}

	@gen.coroutine
	def set(self, conf=None):
		if not (conf is None):
			self.arm.neuron.client.write_register(self.valreg, conf, unit=self.arm.modbus_address)

	def get(self):
		""" Returns ( value, debounce )
			  current on/off value is taken from last value without reading it from hardware
		"""
		return (self.conf)

	def get_value(self):
		""" Returns value
			  current on/off value is taken from last value without reading it from hardware
		"""
		return self.conf

def uint16_to_int(inp):
	if inp > 0x8000: return (inp - 0x10000)
	return inp


class  AnalogOutput():
	def __init__(self, circuit, arm, reg, regcal=-1, regmode=-1, reg_res=-1, dev_id=0, modes=['Voltage'], legacy_mode=True):
		self.dev_id = dev_id
		self.circuit = circuit
		self.reg = reg
		self.regvalue = lambda: arm.data[reg]
		self.regcal = regcal
		self.regmode = regmode
		self.legacy_mode = legacy_mode
		self.reg_res = reg_res
		self.modes = modes
		self.arm = arm
		
		if regcal >= 0:
			self.offset = (uint16_to_int(arm.configs[regcal - 1000 + 1]) / 10000.0)
		else:
			self.offset = 0
		self.is_voltage = lambda: True
		if circuit == '1_01' and regcal >= 0:
			self.is_voltage = lambda: not bool(arm.configs[regcal - 1000 - 1] & 0b1)
		self.reg_shift = 2 if self.is_voltage() else 0
		if regcal >= 0:
			self.factor = arm.volt_ref / 4095 * (1 + uint16_to_int(arm.configs[regcal - 1000 + self.reg_shift]) / 10000.0)
			self.factorx = arm.volt_refx / 4095 * (1 + uint16_to_int(arm.configs[regcal - 1000 + self.reg_shift]) / 10000.0)
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

	def full(self):
		if self.legacy_mode:
			return {'dev': 'ao', 'circuit': self.circuit, 'value': self.value,
				'unit': unit_names[VOLT] if self.is_voltage() else unit_names[AMPERE], 'modes': self.modes}
		else:
			return {'dev': 'ao', 'circuit': self.circuit, 'value': self.value,
				'unit': unit_names[VOLT] if self.is_voltage() else unit_names[AMPERE], 'modes': self.modes,
				'glob_dev_id': self.dev_id}			

	def simple(self):
		return {'dev': 'ao', 'circuit': self.circuit, 'value': self.value}

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
		#print valuei, value
		self.arm.neuron.client.write_register(self.reg, valuei, unit=self.arm.modbus_address)
		if self.circuit == '1_01':
			raise gen.Return(float(valuei) * self.factor + self.offset)
		else:
			raise gen.Return(float(valuei) * 0.0025)

	@gen.coroutine
	def set(self, value=None, frequency=None, mode=None):
		if mode is not None:
			val = self.arm.configs[self.regcal - 1]
			if mode == "V":
				val &= ~0b1
			elif mode == "mA":
				val |= 0b1
			self.arm.neuron.client.write_register(1000 + self.regcal - 1, val, unit=self.arm.modbus_address)
		# print value
		if value is not None:
			if self.circuit == '1_01':
				valuei = int((float(value) - self.offset) / self.factor)
			else:
				valuei = int((float(value) / 0.0025))
			#print "test test test: " + str(valuei)
			if valuei < 0:
				valuei = 0
			elif valuei > 4095:
				valuei = 4095
				
			#print valuei, value
			self.arm.neuron.client.write_register(self.reg, valuei, unit=self.arm.modbus_address)
			if self.circuit == '1_01':
				raise gen.Return(float(valuei) * self.factor + self.offset)
			else:
				raise gen.Return(float(valuei) * 0.0025)

class AnalogInput():
	def __init__(self, circuit, arm, reg, regcal=-1, dev_id=0, legacy_mode=True):
		self.dev_id = dev_id
		self.circuit = circuit
		self.regvalue = lambda: arm.data[reg]
		self.valreg = reg
		self.regcal = regcal
		self.legacy_mode = legacy_mode
		#self.reg.devices.add(self)
		self.arm = arm
		self.is_voltage = lambda: True
		if circuit == '1_01' and regcal >= 0:
			self.is_voltage = lambda: not bool(arm.configs[regcal - 1000 - 1] & 0b1)
		#print self.is_voltage 
		#print circuit, self.vfactor, self.vfactorx, self.voffset
		#self.afactorx = 10 * arm.volt_refx / 4095 *(1 + uint16_to_int(arm.configs[regcal+2])/10000.0)
		#self.aoffset = (uint16_to_int(arm.configs[regcal+3])/10000.0)
		self.reg_shift = 2 if self.is_voltage() else 0
		if regcal >= 0:
			self.vfactor = arm.volt_ref / 4095 * (1 + uint16_to_int(arm.configs[regcal - 1000 + self.reg_shift]) / 10000.0)
			self.vfactorx = arm.volt_refx / 4095 * (1 + uint16_to_int(arm.configs[regcal - 1000 + self.reg_shift]) / 10000.0)
			self.voffset = (uint16_to_int(arm.configs[regcal - 1000 + 1]) / 10000.0)
		else:
			self.vfactor = arm.volt_ref / 4095 * (1 / 10000.0)
			self.vfactorx = arm.volt_refx / 4095 * (1 / 10000.0)	
			self.voffset = 0
		if self.is_voltage():
			self.vfactor *= 1
			self.vfactorx *= 1
		else:
			self.vfactor *= 10
			self.vfactorx *= 10


	@property
	def value(self):
		try:
			if self.circuit == '1_01':
				return (self.regvalue() * self.vfactor) + self.voffset
			else:
				byte_arr = bytearray(4)
				byte_arr[2] = (self.regvalue() >> 8) & 255
				byte_arr[3] = self.regvalue() & 255
				byte_arr[0] = (self.arm.data[self.valreg + 1] >> 8) & 255
				byte_arr[1] = self.arm.data[self.valreg + 1] & 255
				return struct.unpack('>f', str(byte_arr))[0]
		except Exception, E:
			logger.exception(str(E))
			return 0

	def set(self, mode=None):
		if mode is not None:
			val = self.arm.configs[self.regcal - 1]
			if mode == "V":
				val &= ~0b1
			elif mode == "mA":
				val |= 0b1
			self.arm.neuron.client.write_register(1000 + self.regcal - 1, val, unit=self.arm.modbus_address)

	def full(self):
		if self.legacy_mode:
			return {'dev': 'ai', 'circuit': self.circuit, 'value': self.value,
					'unit': unit_names[VOLT] if self.is_voltage() else unit_names[AMPERE]}
		else:
			return {'dev': 'ai', 'circuit': self.circuit, 'value': self.value,
					'unit': unit_names[VOLT] if self.is_voltage() else unit_names[AMPERE],
					'glob_dev_id': self.dev_id}
			
	def simple(self):
		return {'dev': 'ai', 'circuit': self.circuit, 'value': self.value}

	@property  # docasne!!
	def voltage(self):
		return self.value
