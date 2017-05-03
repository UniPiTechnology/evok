import devents

"""
   Structured list/dict of all devices in system
   
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

    def by_int(self, devtypeid, circuit=None):
        devdict = self._arr[devtypeid]
        if circuit is None:
            return devdict.values()
        try:
            return devdict[circuit]
        except KeyError:
            raise Exception('Invalid device circuit number %s' % str(circuit))

    def by_name(self, devtype, circuit=None):
        try:
            devdict = self[devtype]
        except KeyError:
            raise Exception('Invalid device type %s' % str(devtype))
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
)

devtype_altnames = {
    'di': 'input',
    'analoginput': 'ai',
    'analogoutput': 'ao',
    'eprom': 'ee'}

## 
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