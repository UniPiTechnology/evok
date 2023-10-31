import logging
import os
import multiprocessing
from typing import List, Dict

try:
    from modbus_slave import TcpModbusSlave, UartModbusSlave
except ImportError:
    pass
try:
    import owclient
except ImportError:
    pass

import yaml
from devices import *

# from neuron import WiFiAdapter

try:
    import unipig
    from apigpio import I2cBus, GpioBus
except:
    pass


class EvokConfigError(Exception):
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


class OWBusDevice:
    def __init__(self, bus_driver, dev_id):
        self.dev_id = dev_id
        self.bus_driver = bus_driver
        self.circuit = bus_driver.circuit

    def full(self):
        return self.bus_driver.full()


class OWSensorDevice:
    def __init__(self, sensor_dev, dev_id):
        self.dev_id = dev_id
        self.sensor_dev = sensor_dev
        self.circuit = sensor_dev.circuit

    def full(self):
        return self.sensor_dev.full()


class EvokConfig:

    def __init__(self, conf_dir_path: str):
        data = self.__get_final_conf(conf_dir_path=conf_dir_path)
        self.main: dict = self.__get_main_conf(data)
        self.hw_tree: dict = self.__get_hw_tree(data)

    @staticmethod
    def __get_final_conf(conf_dir_path) -> dict:
        files = os.listdir(conf_dir_path)
        if 'config.yaml' not in files:
            raise EvokConfigError(f"Missing 'config.yaml' in evok configuration directory ({conf_dir_path})")
        scope = [conf_dir_path+'/config.yaml']
        final_conf = {}
        for path in scope:
            with open(path, 'r') as f:
                ydata: dict = yaml.load(f, Loader=yaml.Loader)
            for name, value in ydata.items():
                final_conf[name] = value  # TODO: zahloubeni (neztracet data, pouze expandovat)
        return final_conf

    @staticmethod
    def __get_main_conf(data: dict) -> dict:
        ret = {}
        for name, value in data.items():
            if name not in ['hw_tree']:
                ret[name] = value
        return ret

    @staticmethod
    def __get_hw_tree(data: dict) -> dict:
        ret = {}
        if 'hw_tree' not in data:
            logger.warning("Section 'hw_tree' not in configuration!")
            return ret
        for name, value in data['hw_tree'].items():
            ret[name] = value
        return ret

    def configtojson(self):
        return self.main  # TODO: zkontrolovat!!

    def getintdef(self, key, default):
        try:
            return int(self.main[key])
        except:
            return default

    def getfloatdef(self, key, default):
        try:
            return float(self.main[key])
        except:
            return default

    def getbooldef(self, key, default):
        try:
            return bool(self.main[key])
        except:
            return default

    def getstringdef(self, key, default):
        try:
            return str(self.main[key])
        except:
            return default

    def get_hw_tree(self) -> dict:
        return self.hw_tree


def hexint(value):
    if value.startswith('0x'):
        return int(value[2:], 16)
    return int(value)


def create_devices(evok_config: EvokConfig, hw_dict):
    dev_counter = 0
    for bus_name, bus_data in evok_config.get_hw_tree().items():
        bus_data: dict
        # split section name ITEM123 or ITEM_123 or ITEM-123 into device=ITEM and circuit=123
        bus_type = bus_data['type']
        logging.info(f"Creating bus '{bus_name}' with type '{bus_type}'")
        for device_name, device_data in bus_data['devices'].items():
            logging.info(f"^ Creating device '{device_name}' with type '{bus_type}'")
            try:
                dev_counter += 1
                if bus_type == 'OWBUS':
                    # permanent thermometer
                    ow_type = device_data.get("type")
                    address = device_data.get("address")
                    interval = device_data.getintdef("interval", 15)
                    owbus = None  # TODO: vytvorit, pokud neexistuje!!
                    sensor = owclient.MySensorFabric(address, ow_type, owbus, interval=interval, circuit=circuit,
                                                     is_static=True)
                    if ow_type in ["DS2408", "DS2406", "DS2404", "DS2413"]:
                        sensor = OWSensorDevice(sensor, dev_id=0)
                    Devices.register_device(SENSOR, sensor)
                elif bus_type == 'MODBUSTCP':
                    modbus_server = bus_data.get("modbus_server", "127.0.0.1")
                    modbus_port = bus_data.get("port", 502)

                    slave_id = device_data.get("slave-id", 1)
                    scanfreq = device_data.get("scan_frequency", 1)
                    scan_enabled = device_data.get("scan_enabled", True)
                    device_model = device_data["model"]
                    circuit = device_name
                    major_group = device_name

                    slave = TcpModbusSlave(circuit, evok_config, modbus_server, modbus_port, scanfreq, scan_enabled,
                                           hw_dict, device_model=device_model, slave_id=slave_id,
                                           dev_id=dev_counter, major_group=major_group)
                    Devices.register_device(MODBUS_SLAVE, slave)
                elif bus_type == "MODBUSRTU":
                    serial_port = bus_data["port"]
                    serial_baud_rate = bus_data.get("baudrate", 19200)
                    serial_parity = bus_data.get("parity", 'N')

                    slave_id = device_data.get("slave-id", 1)
                    scanfreq = device_data.get("scan_frequency", 1)
                    scan_enabled = device_data.get("scan_enabled", True)
                    device_model = device_data["model"]
                    circuit = device_name
                    major_group = device_name

                    slave = UartModbusSlave(circuit, evok_config, serial_port, scanfreq, scan_enabled, hw_dict,
                                            baud_rate=serial_baud_rate, parity=serial_parity, slave_id=slave_id,
                                            device_model=device_model, dev_id=dev_counter, major_group=major_group)
                    Devices.register_device(MODBUS_SLAVE, slave)
                else:
                    dev_counter -= 1
                    logger.error(f"Unknown device type: '{device_type}'! skipping...")

            except Exception as E:
                logger.exception(f"Error in config section '{bus_type}:{device_name}' - {str(E)}")


def add_aliases(alias_conf):
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
