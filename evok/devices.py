from . import devents
import yaml
import re
from copy import deepcopy
from typing import Any, Type, Tuple, List, Mapping, Callable

from .log import logger

"""
   Structured dict/dict of all devices in the system

"""

# ToDo: ...
Device = Any

class Aliases:
    alias_dict: Mapping[str, Device] = {}
    initial_dict: Mapping[str, Mapping[str, str]] = {}

    def __init__(self, initial_dict: Mapping[str, Mapping[str, str]]):
        self.initial_dict = initial_dict
        self.dirty_callback: Callable = None

    def __getitem__(self, key):
        return self.alias_dict.__get_item__(self.key)

    def register_dirty_cb(self, func: Callable) -> None:
        self.dirty_callback = func

    def set_dirty(self) -> None:
        if self.dirty_callback:
            self.dirty_callback()

    def validate(self, alias: str) -> None:
        # check duplicity
        if alias in self.alias_dict:
            raise Exception(f"Duplicate alias {alias}")
        # check alias name
        if (not (alias.startswith("al_")) or (len(re.findall(r"[A-Za-z0-9\-\._]*", alias)) > 2)):
            raise Exception(f"Invalid alias {alias}")

    def add(self, alias: str, device: Device, file_update:bool=False):
        if (alias != device.alias):
            self.validate(alias)
        # delete old alias
        if device.alias: self.delete(device.alias)
        # delete alias from initial_dict
        if alias: self.delete(alias)
        # create new alias
        self.alias_dict[alias] = device
        if file_update:
            self.set_dirty()

    def delete(self, alias: str, file_update:bool=False) -> None:
        # delete alias from regular dict
        if alias in self.alias_dict:
            del self.alias_dict[alias]
            if file_update:
                self.set_dirty()
        # delete alias from initial dict
        if alias in self.initial_dict:
            del self.initial_dict[alias]
            if file_update:
                self.set_dirty()

    def get_aliases_by_circuit(self, devtype: int, circuit: str):
        return  list((alias for alias, rec in self.initial_dict.items()\
                            if (rec.get("devtype", None) == devtype) and (rec.get("circuit", None) == circuit)))

    def get_dict_to_save(self) -> Mapping[str, Mapping[str, str]]:
        aliases = deepcopy(self.initial_dict)
        aliases.update(dict(((alias, {"circuit":device.circuit, "devtype":device.devtype})
                             for alias,device in self.alias_dict.items())))
        return aliases


class DeviceList(dict):
    aliases = Aliases({})

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
            if circuit in self.aliases:
                return self.aliases[circuit]
            else:
                raise Exception(f'Invalid device circuit number {str(circuit)} with devtypeid {devtypeid}')

    def by_name(self, devtype, circuit=None):
        try:
            devdict = self[devtype]
        except KeyError:
            devdict = self[self.altnames[devtype]]
        if circuit is None:
            return devdict.values()
        circuit = str(circuit)
        try:
            return devdict[circuit]
        except KeyError:
            if circuit in self.aliases:
                return self.aliases[circuit]
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
        # assign saved alias
        for alias in self.aliases.get_aliases_by_circuit(devtype, str(device.circuit)):
            try:
                self.aliases.add(alias, device)
                device.alias = alias
                logger.info(f"Set alias {alias} to {devtype_names[devtype]}[{device.circuit}]")
            except Exception as E:
                logger.warning(f"Error on setting saved alias: {str(E)}")

        devents.config(device)
        logging.debug(f"Registed new device '{devtype_names[devtype]}' with circuit {device.circuit} \t ({device})")

    def set_alias(self, alias: str, device: Device, file_update:bool=False) -> None:
        try:
            if (alias == '' or alias is None):
                if device.alias: self.aliases.delete(device.alias, file_update)
                device.alias = alias
                logger.debug(f"Reset alias of {devtype_names[device.devtype]}[{device.circuit}]")
            elif alias != device.alias:
                self.aliases.add(alias, device, file_update)
                device.alias = alias
                logger.debug(f"Set alias {alias} of {devtype_names[device.devtype]}[{device.circuit}]")
        except Exception as E:
            logger.error(f"Error on setting alias {alias}: {str(E)}")
            raise E


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
