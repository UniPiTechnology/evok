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

import devents
from devices import *
import config
#from spiarm import ProxyRegister

from log import *

import config

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
	def __init__(self, circuit, modbus_server, modbus_port, scan_freq, scan_enabled, hw_dict, dev_id=0):
		self.dev_id = dev_id
		self.circuit = circuit
		self.hw_dict = hw_dict
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
		# start modus/tcp modbusclient_rs485. On connect call self.readboards
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
				#logger.debug(type(versions))
				#logger.debug(versions.registers)
				if isinstance(versions, ExceptionResponse):
					raise ENoBoard("bad request")
				#print "bbb %d" % i
				board = Board(i, self, versions.registers)
				data = yield self.client.read_input_registers(0, count=board.ndataregs, unit=i)
				configs = yield self.client.read_input_registers(1000, count=board.nconfigregs, unit=i)
				#print "ccc %d" % i
				#print data.registers
				#print configs.registers
				board.parse_definition(data.registers, configs.registers, self.hw_dict, i)
				#print "aaa %d" % i
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
			try:
				for board in self.boards:
					data = yield self.client.read_input_registers(0, count=board.ndataregs, unit=board.circuit)
					if isinstance(data, ExceptionResponse):
						raise Exception("bad request")
					board.set_data(0, data.registers)
			except Exception, E:
				logger.exception(str(E))
		if self.do_scanning and (self.scan_interval != 0):
			self.loop.call_later(self.scan_interval, self.scan_boards)
			self.is_scanning = True
		else:
			self.is_scanning = False

class UartNeuron(object):
	def __init__(self, circuit, scan_freq, scan_enabled, hw_dict, dev_id=0):
		self.dev_id = dev_id
		self.circuit = circuit
		self.hw_dict = hw_dict
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
		for board in self.boards:
			del (board)
		self.boards = list()
		for i in (1, 2, 3):
			try:
				versions = yield self.client.read_input_registers(1000, 10, unit=i)
				#logger.debug(type(versions))
				#logger.debug(versions.registers)
				if isinstance(versions, ExceptionResponse):
					raise ENoBoard("bad request")
				#print "bbb %d" % i
				board = Board(i, self, versions.registers)
				data = yield self.client.read_input_registers(0, count=board.ndataregs, unit=i)
				configs = yield self.client.read_input_registers(1000, count=board.nconfigregs, unit=i)
				#print "ccc %d" % i
				#print data.registers
				#print configs.registers
				board.parse_definition(data.registers, configs.registers, self.hw_dict, i)
				#print "aaa %d" % i
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
			try:
				for board in self.boards:
					data = yield self.client.read_input_registers(0, count=board.ndataregs, unit=board.circuit)
					if isinstance(data, ExceptionResponse):
						raise Exception("bad request")
					board.set_data(0, data.registers)
			except Exception, E:
				logger.exception(str(E))
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
	def __init__(self, circuit, neuron, versions, dev_id=0):
		self.dev_id = dev_id
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
									_ao = AnalogOutput("%s_%02d" % (self.circuit, counter + 1), self, board_val_reg + counter, regcal=m_feature['cal_reg'] + 1)
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
						elif m_feature['type'] == 'REGISTER' and m_feature['major_group'] == board_id:
							#print m_feature['type']
							#print m_feature['count']
							while counter < max_count:
								board_val_reg = m_feature['val_reg'] - (100 * (board_id - 1))
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
		#print data
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


class Relay(object):
	pending_id = 0
	
	def __init__(self, circuit, arm, coil, reg, mask, dev_id=0):
		self.dev_id = dev_id
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

class ULED(object):
	pending_id = 0
	
	def __init__(self, circuit, arm, post, reg, mask, coil, dev_id=0):
		self.dev_id = dev_id
		self.circuit = circuit
		self.arm = arm
		self.bitmask = mask
		self.regvalue = lambda: arm.data[reg]
		self.valreg = reg
		self.coil = coil
		#print "TEST A"
		#print "TEST B"
		#print "TEST C"
		#self.reg.devices.add(self)
		#self.regcounter1.devices.add(self)
		#self.regcounter2.devices.add(self)
		#self.regdebounce.devices.add(self)
		#print "TEST D"

	def full(self):
		return {'dev': 'led', 'circuit': self.circuit, 'value': self.value}

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
		yield self.arm.neuron.client.write_coil(self.coil, 1 if value else 0, unit=self.arm.circuit)
		raise gen.Return(1 if value else 0)

	def set(self, value=None, timeout=None):
		""" Sets new on/off status. Disable pending timeouts
		"""
		if value is None:
			raise Exception('Value must be specified')
		value = int(value)
		self.arm.neuron.client.write_coil(self.coil, 1 if value else 0, unit=self.arm.circuit)
		return (1 if value else 0)
		#return (1 if self.mcp.value & self._mask else 0)


class Watchdog(object):
	
	def __init__(self, circuit, arm, post, reg, timeout_reg, dev_id=0):
		self.dev_id = dev_id
		self.circuit = circuit
		self.arm = arm
		self.timeoutvalue = lambda: arm.configs[timeout_reg]
		self.regvalue = lambda: arm.data[reg]
		self.valreg = reg
		self.toreg = timeout_reg

	def full(self):
		return {'dev': 'wd', 'circuit': self.circuit, 'value': self.regvalue(), 'timeout': self.timeoutvalue()}

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
		self.arm.neuron.client.write_register(self.valreg, 1 if value else 0, unit=self.arm.circuit)
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
			self.arm.neuron.client.write_register(self.toreg + 1000, timeout, unit=self.arm.circuit)
			self.arm.configs[self.toreg] = timeout
		self.arm.neuron.client.write_register(self.valreg, 1 if value else 0, unit=self.arm.circuit)
		raise gen.Return(1 if value else 0)
		#return (1 if self.mcp.value & self._mask else 0)


class Register():
	def __init__(self, circuit, arm, post, reg, dev_id=0):
		self.dev_id = dev_id
		self.circuit = circuit
		self.arm = arm
		self.regvalue = lambda: arm.data[reg]
		self.valreg = reg

	def full(self):
		return {'dev': 'register', 'circuit': self.circuit, 'value': self.regvalue()}
		

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
		self.arm.neuron.client.write_register(self.valreg, value if value else 0, unit=self.arm.circuit)
		raise gen.Return(value if value else 0)


	@gen.coroutine
	def set(self, value=None, timeout=None):
		""" Sets new on/off status. Disable pending timeouts
		"""
		if value is None:
			raise Exception('Value must be specified')
		value = int(value)
		self.arm.neuron.client.write_register(self.valreg, value if value else 0, unit=self.arm.circuit)
		raise gen.Return(value if value else 0)
	

class Input():
	def __init__(self, circuit, arm, reg, mask, regcounter=None, regdebounce=None, dev_id=0):
		self.dev_id = dev_id
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

	@gen.coroutine
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

class Uart():
	def __init__(self, circuit, arm, reg, dev_id=0):
		self.dev_id = dev_id
		self.circuit = circuit
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
		return {'dev': 'uart', 'circuit': self.circuit, 'conf': self.conf}

	def simple(self):
		return {'dev': 'uart', 'circuit': self.circuit, 'conf': self.conf}

	@gen.coroutine
	def set(self, conf=None):
		if not (conf is None):
			self.arm.write_regs(self.valreg, conf, unit=self.arm.circuit)

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


class AnalogOutput():
	def __init__(self, circuit, arm, reg, regcal=-1, dev_id=0):
		self.dev_id = dev_id
		self.circuit = circuit
		self.reg = reg
		self.regvalue = lambda: arm.data[reg]
		self.regcal = regcal
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
		return {'dev': 'ao', 'circuit': self.circuit, 'value': self.value,
				'unit': unit_names[VOLT] if self.is_voltage() else unit_names[AMPERE]}

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
		self.arm.neuron.client.write_register(self.reg, valuei, unit=self.arm.circuit)
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
			self.arm.neuron.client.write_register(1000 + self.regcal - 1, val, unit=self.arm.circuit)
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
			self.arm.neuron.client.write_register(self.reg, valuei, unit=self.arm.circuit)
			if self.circuit == '1_01':
				raise gen.Return(float(valuei) * self.factor + self.offset)
			else:
				raise gen.Return(float(valuei) * 0.0025)

class AnalogInput():
	def __init__(self, circuit, arm, reg, regcal=-1, dev_id=0):
		self.dev_id = dev_id
		self.circuit = circuit
		self.regvalue = lambda: arm.data[reg]
		self.valreg = reg
		self.regcal = regcal
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
			#print self.circuit, self.regvalue(),self.vfactor,self.voffset

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
			self.arm.neuron.client.write_register(1000 + self.regcal - 1, val, unit=self.arm.circuit)

	def full(self):
		return {'dev': 'ai', 'circuit': self.circuit, 'value': self.value,
				'unit': unit_names[VOLT] if self.is_voltage() else unit_names[AMPERE]}

	def simple(self):
		return {'dev': 'ai', 'circuit': self.circuit, 'value': self.value}

	@property  # docasne!!
	def voltage(self):
		return self.value
