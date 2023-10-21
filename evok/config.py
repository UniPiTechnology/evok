import os
import multiprocessing
import configparser as ConfigParser
from typing import List

import yaml
from devices import *

# from neuron import WiFiAdapter

try:
    import unipig
    from apigpio import I2cBus, GpioBus
except:
    pass


class HWDict:
    def __init__(self, dir_paths: List[str] = None, paths: List[str] = None):
        """
        :param dir_paths: path to dir for load
        :param paths: paths to config files
        """
        self.definitions = []
        scope = list()
        if dir_paths is not None:
            for dp in dir_paths:
                scope.extend([dp + f for f in os.listdir(dp)])
        if paths is not None:
            scope.extend(paths)
        if scope is None or len(scope) == 0:
            raise ValueError(f"HWDict: no scope!")
        for file_path in scope:
            if file_path.endswith(".yaml"):
                with open(file_path, 'r') as yfile:
                    ydata = yaml.load(yfile, Loader=yaml.SafeLoader)
                    if ydata is None:
                        logger.warning(f"Empty Definition file '{file_path}'! skipping...")
                        continue
                    self.definitions.append(ydata)
                    logger.info(f"YAML Definition loaded: {file_path}, type: {len(self.definitions[-1])}, "
                                f"definition count {len(self.definitions) - 1}")


class OWBusDevice():
    def __init__(self, bus_driver, dev_id):
        self.dev_id = dev_id
        self.bus_driver = bus_driver
        self.circuit = bus_driver.circuit

    def full(self):
        return self.bus_driver.full()


class OWSensorDevice():
    def __init__(self, sensor_dev, dev_id):
        self.dev_id = dev_id
        self.sensor_dev = sensor_dev
        self.circuit = sensor_dev.circuit

    def full(self):
        return self.sensor_dev.full()


class I2CBusDevice():
    def __init__(self, bus_driver, dev_id):
        self.dev_id = dev_id
        self.bus_driver = bus_driver
        self.circuit = bus_driver.circuit

    def full(self):
        return None


class GPIOBusDevice():
    def __init__(self, bus_driver, dev_id):
        self.dev_id = dev_id
        self.bus_driver = bus_driver
        self.circuit = bus_driver.circuit

    def full(self):
        return None


class EvokConfig(ConfigParser.RawConfigParser):

    def __init__(self):
        ConfigParser.RawConfigParser.__init__(self, inline_comment_prefixes=(';'))

    def configtojson(self):
        return dict(
            (section,
             dict(
                 (option,
                  self.get(section, option)
                  ) for option in self.options(section))
             ) for section in self.sections())

    def getintdef(self, section, key, default):
        try:
            return self.getint(section, key)
        except:
            return default

    def getfloatdef(self, section, key, default):
        try:
            return self.getfloat(section, key)
        except:
            return default

    def getbooldef(self, section, key, default):
        true_booleans = ['yes', 'true', '1']
        false_booleans = ['no', 'false', '0']
        try:
            val = self.get(section, key).lower()
            if val in true_booleans:
                return True
            if val in false_booleans:
                return False
            return default
        except:
            return default

    def getstringdef(self, section, key, default):
        try:
            return self.get(section, key)
        except:
            return default


def hexint(value):
    if value.startswith('0x'):
        return int(value[2:], 16)
    return int(value)


def create_devices(evok_config: EvokConfig, hw_config: dict, hw_dict):
    dev_counter = 0
    # Config.hw_dict = hw_dict
    for bus_name, bus_data in hw_config.items():
        bus_data: dict
        # split section name ITEM123 or ITEM_123 or ITEM-123 into device=ITEM and circuit=123
        bus_type = bus_data['type']
        logging.info(f"Creating bus '{bus_name}' with type '{bus_type}'")
        for device_name, device_data in bus_data['devices'].items():
            device_type = device_data['type']
            logging.info(f"^ Creating device '{device_name}' with type '{device_type}'")
            try:
                if device_type == 'OWBUS':
                    import owclient
                    bus = device_data.get("owbus")
                    interval = device_data.get("interval")
                    scan_interval = device_data.get("scan_interval")
                    #### prepare 1wire process ##### (using thread affects timing!)
                    resultPipe = multiprocessing.Pipe()
                    taskPipe = multiprocessing.Pipe()
                    bus_driver = owclient.OwBusDriver(circuit, taskPipe, resultPipe, bus=bus,
                                                      interval=interval, scan_interval=scan_interval)
                    owbus = OWBusDevice(bus_driver, dev_id=0)
                    Devices.register_device(OWBUS, owbus)
                elif device_type == 'SENSOR' or device_type == '1WDEVICE':
                    # permanent thermometer
                    bus = device_type.get("bus")
                    owbus = (Devices.by_int(OWBUS, bus)).bus_driver
                    ow_type = device_data.get("type")
                    address = device_data.get("address")
                    interval = device_data.getintdef("interval", 15)
                    sensor = owclient.MySensorFabric(address, ow_type, owbus, interval=interval, circuit=circuit,
                                                     is_static=True)
                    if ow_type in ["DS2408", "DS2406", "DS2404", "DS2413"]:
                        sensor = OWSensorDevice(sensor, dev_id=0)
                    Devices.register_device(SENSOR, sensor)
                elif device_type == 'I2CBUS':
                    # I2C bus on /dev/i2c-1 via pigpio daemon
                    busid = device_data.get("busid")
                    bus_driver = I2cBus(circuit=circuit, busid=busid)
                    i2cbus = I2CBusDevice(bus_driver, 0)
                    Devices.register_device(I2CBUS, i2cbus)
                elif device_type == 'GPIOBUS':
                    # access to GPIO via pigpio daemon
                    bus_driver = GpioBus(circuit=circuit)
                    gpio_bus = GPIOBusDevice(bus_driver, 0)
                    Devices.register_device(GPIOBUS, gpio_bus)
                elif device_type == 'UNIPIG':
                    from unipig import Unipig
                    device_model = device_data["model"]
                    unipig = Unipig(circuit, evok_config, hw_dict, device_model)
                    Devices.register_device(MODBUS_SLAVE, unipig)
                elif device_type == 'MODBUS_SLAVE':
                    from neuron import TcpModbusSlave
                    dev_counter += 1
                    modbus_server = device_data.get("modbus_server", "127.0.0.1")
                    modbus_port = device_data.get("modbus_port", 502)
                    modbus_address = device_data.get("slave-id", 1)
                    scanfreq = device_data.get("scan_frequency", 1)
                    scan_enabled = device_data.get("scan_enabled", True)
                    device_model = device_data["model"]
                    circuit = device_name
                    major_group = device_name
                    neuron = TcpModbusSlave(circuit, evok_config, modbus_server, modbus_port, scanfreq, scan_enabled,
                                            hw_dict, device_model=device_model, modbus_address=modbus_address,
                                            dev_id=dev_counter, major_group=major_group)
                    Devices.register_device(MODBUS_SLAVE, neuron)
                else:
                    logger.error(f"Unknown device type: '{device_type}'! skipping...")

            except Exception as E:
                logger.exception(f"Error in config section '{bus_type}:{device_name}' - {str(E)}")


async def add_aliases(alias_conf):
    if alias_conf is not None:
        for alias_conf_single in alias_conf:
            if alias_conf_single is not None:
                if "version" in alias_conf_single and "aliases" in alias_conf_single and alias_conf_single[
                    "version"] == 1.0:
                    for dev_pointer in alias_conf_single['aliases']:
                        try:
                            dev_obj = Devices.by_int(dev_pointer["dev_type"], dev_pointer["circuit"])
                            logger.info("Alias loaded: " + str(dev_obj) + " " + str(dev_pointer["name"]))
                            if Devices.add_alias(dev_pointer["name"], dev_obj):
                                dev_obj.alias = dev_pointer["name"]
                        except Exception as E:
                            logger.exception(str(E))


def add_wifi():
    wifi = WiFiAdapter("1_01")
    Devices.register_device(WIFI, wifi)
