import devents

"""
   Structured list/dict of all devices in the system
   
"""
class DeviceList(dict):
	def __init__(self, altnames):
		super(DeviceList, self).__init__()
		self._arr = []
		self.altnames = altnames

	def __setitem__(self, key, value):
		if not (key in self.keys()): self._arr.append(value)
		super(DeviceList, self).__setitem__(key, value)

	def __getitem__(self, key):
		try:
			return super(DeviceList, self).__getitem__(key)
		except KeyError:
			return super(DeviceList, self).__getitem__(self.altnames[key])

	def remove_item(self, key, value):
		del (self[devtype_names[key]])[value.circuit]
		#try:
		#except KeyError:
		#	del (self[self.altnames[key]])[value]
		#super(DeviceList, self).pop(key)

	def remove_global_device(self, glob_dev_id):
		for devtype_name in devtype_names:
			to_delete = []
			for dev_name in self[devtype_name]:
				if ((self[devtype_name])[dev_name]).dev_id == glob_dev_id:
					to_delete += [(self[devtype_name])[dev_name]]
			for value in to_delete:
				del (self[devtype_name])[value.circuit]


	def by_int(self, devtypeid, circuit=None, major_group=None):
		devdict = self._arr[devtypeid]
		if circuit is None:
			if major_group is not None:
				outp = []
				if len(devdict.values()) > 1:
					for single_dev in devdict.values():	
						if single_dev.major_group == major_group:
							outp += [single_dev]
					return outp
				elif len(devdict.values()) > 0:
					single_dev = devdict.values()[0]
					if single_dev.major_group == major_group:
						return devdict.values()
					else:
						return []
				else:
					return []
			else:
				return devdict.values()
		try:
			return devdict[circuit]
		except KeyError:
			raise Exception('Invalid device circuit number %s' % str(circuit))

	def by_name(self, devtype, circuit=None):
		try:
			devdict = self[devtype]
		except KeyError:
			devdict = self[self.altnames[devtype]]
			#raise Exception('Invalid device type %s' % str(devtype))
		if circuit is None:
			return devdict.values()
		try:
			return devdict[circuit]
		except KeyError:
			raise Exception('Invalid device circuit number %s' % str(circuit))

	def register_device(self, devtype, device):
		""" can be called with devtype = INTEGER or NAME
		"""
		if devtype is None:
			raise Exception('Devicetype must contain INTEGER OR NAME')
		if type(devtype) is int:
			devdict = self._arr[devtype]
		else:
			devdict = self[devtype]
		devdict[str(device.circuit)] = device
		devents.config(device)


# # define device types constants
RELAY = 0
INPUT = 1
AI = 2
AO = 3
EE = 4
SENSOR = 5
I2CBUS = 6
ADCHIP = 7
OWBUS = 8
MCP = 9
GPIOBUS = 10
PCA9685 = 11
DS2408 = 12
UNIPI2 = 13
UART = 14
NEURON = 15
BOARD = 16
OUTPUT = 17
LED = 18
WATCHDOG = 19
REGISTER = 20



## corresponding device types names !! ORDER IS IMPORTANT
devtype_names = (
	'relay',
	'input',
	'ai',
	'ao',
	'ee',
	'sensor',
	'i2cbus',
	'adchip',
	'owbus',
	'mcp',
	'gpiobus',
	'pca9685',
	'ds2408',
	'unipi2',
	'uart',
	'neuron',
	'board',
	'output',
	'led',
	'watchdog',
	'register'
)

devtype_altnames = {
	'di': 'input',
	'do': 'output',
	'analoginput': 'ai',
	'analogoutput': 'ao',
	'eprom': 'ee',
	'wd': 'watchdog',
	'rs485': 'uart'
	}

Devices = DeviceList(devtype_altnames)
for n in devtype_names:
	Devices[n] = {}

#define units
NONE = 0
CELSIUS = 1
VOLT = 2
AMPERE = 3
OHM = 4

unit_names = (
	'',
	'C',
	'V',
	'mA',
	'Ohm',
)

unit_altnames = {
	'': '',
	'C': 'Celsius',
	'V': 'Volt',
	'mA': 'miliampere',
	'Ohm': 'ohm'
}

class UniPiDevice(object):
	def __init__(self):
		False
