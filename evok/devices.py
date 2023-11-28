from . import devents
import yaml
import re
from .log import *

"""
   Structured dict/dict of all devices in the system

"""


class DeviceList(dict):
    alias_dict = {}

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

    def remove_global_device(self, glob_dev_id):
        try:
            for devtype_name in devtype_names:
                to_delete = []
                for dev_name in self[devtype_name]:
                    if ((self[devtype_name])[dev_name]).dev_id == glob_dev_id:
                        to_delete += [(self[devtype_name])[dev_name]]
                for value in to_delete:
                    del (self[devtype_name])[value.circuit]
        except KeyError as E:
            logger.warning(f"Trying to remove non-existing global device ({E})")

    def by_int(self, devtypeid, circuit=None, major_group=None):
        circuit = str(circuit) if circuit is not None else None
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
                    single_dev = list(devdict.values())[0]
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
            if circuit in self.alias_dict:
                return self.alias_dict[circuit]
            else:
                raise Exception(f'Invalid device circuit number {str(circuit)} with devtypeid {devtypeid}')

    def by_name(self, devtype, circuit=None):
        circuit = str(circuit) if circuit is not None else None
        try:
            devdict = self[devtype]
        except KeyError:
            devdict = self[self.altnames[devtype]]
        if circuit is None:
            return devdict.values()
        try:
            return devdict[circuit]
        except KeyError:
            if circuit in self.alias_dict:
                return self.alias_dict[circuit]
            else:
                raise Exception(f'Invalid device circuit number {str(circuit)} with devtype {devtype}')

    def register_device(self, devtype, device):
        """ can be called with devtype = INTEGER or NAME
        """
        if devtype is None:
            raise Exception('Device type must contain INTEGER or NAME')
        if type(devtype) is int:
            devdict = self._arr[devtype]
        else:
            devdict = self[devtype]
        devdict[str(device.circuit)] = device
        devents.config(device)
        logging.debug(f"Registed new device '{devtype_names[devtype]}' with circuit {device.circuit} \t ({device})")

    def add_alias(self, alias_key, device, file_update=False):
        if (not (alias_key.startswith("al_")) or (len(re.findall(r"[A-Za-z0-9\-\._]*", alias_key)) > 2)):
            if (alias_key == ''):
                if device.alias in self.alias_dict:
                    del self.alias_dict[device.alias]
                if file_update:
                    self.save_alias_dict()
                return True
            else:
                raise Exception("Invalid alias %s" % alias_key)
                return False
        if not alias_key in self.alias_dict:
            if device.alias in self.alias_dict:
                del self.alias_dict[device.alias]
            self.alias_dict[alias_key] = device
            if file_update:
                self.save_alias_dict()
            return True
        else:
            if (alias_key != device.alias):
                raise Exception("Duplicate alias %s" % alias_key)
            return False

    def save_alias_dict(self):
        try:
            with open("/var/evok/evok-alias.yaml", 'w+') as yfile:
                out_dict = {"version": 1.0, "aliases":[]}
                for single_alias in self.alias_dict:
                    out_dict["aliases"] += [{"circuit": self.alias_dict[single_alias].circuit, "dev_type": self.alias_dict[single_alias].devtype, "name": single_alias}]
                yfile.write(yaml.dump(out_dict))
        except Exception as E:
            logger.exception(str(E))


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
MODBUS_SLAVE = 15
BOARD = 16
OUTPUT = 17
LED = 18
WATCHDOG = 19
REGISTER = 20
WIFI = 21
LIGHT_CHANNEL = 22
LIGHT_DEVICE = 23
UNIT_REGISTER = 24
EXT_CONFIG = 25
TCPBUS = 26
SERIALBUS = 27

# # corresponding device types names !! ORDER IS IMPORTANT
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
    'modbus_slave',
    'board',
    'misc_output',
    'led',
    'watchdog',
    'register',
    'wifi',
    'light_channel',
    'light_device',
    'unit_register',
    'ext_config',
    'tcp_bus',
    'serial_bus',
)

devtype_altnames = {
    'di': 'input',
    'output': 'relay',
    'do': 'relay',
    'analoginput': 'ai',
    'analogoutput': 'ao',
    'eprom': 'ee',
    'wd': 'watchdog',
    'rs485': 'uart',
    'temp': 'sensor'
    }

Devices = DeviceList(devtype_altnames)
for n in devtype_names:
    Devices[n] = {}

# define units
NONE = 0
CELSIUS = 1
VOLT = 2
AMPERE = 3
OHM = 4

unit_names = [
    '',
    'C',
    'V',
    'mA',
    'Ohm',
]

unit_altnames = {
    '': '',
    'C': 'Celsius',
    'V': 'Volt',
    'mA': 'miliampere',
    'Ohm': 'ohm'
}
