import logging
import os
from typing import List, Dict, Union

from tornado.ioloop import IOLoop

from .modbus_unipi import EvokModbusSerialClient, EvokModbusTcpClient

from .modbus_slave import ModbusSlave

from . import owdevice

import yaml
from .devices import *

# from neuron import WiFiAdapter

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
            if file_path.endswith(".yaml") and os.path.isfile(file_path):
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


class TcpBusDevice:
    def __init__(self, circuit: str, bus_driver: EvokModbusTcpClient, dev_id):
        self.dev_id = dev_id
        self.bus_driver = bus_driver
        self.circuit = circuit

    def switch_to_async(self, loop: IOLoop):
        loop.add_callback(lambda: self.bus_driver.connect())


class SerialBusDevice:
    def __init__(self, circuit: str,  bus_driver: EvokModbusSerialClient, dev_id):
        self.dev_id = dev_id
        self.bus_driver = bus_driver
        self.circuit = circuit

    def switch_to_async(self, loop: IOLoop):
        self.bus_driver.ioloop = loop
        loop.add_callback(lambda: self.bus_driver.connect())


class EvokConfig:

    def __init__(self, conf_dir_path: str):
        data = self.__get_final_conf(scope=[conf_dir_path+'/config.yaml'])
        self.hw_tree: dict = self.__get_hw_tree(data)
        self.apis: dict = self.__get_apis_conf(data)
        self.logging: dict = self.__get_logging_conf(data)

    def __merge_data(self, source: dict, append: dict):
        for key in append:
            if key in source and type(source[key]) == dict and type(append[key]) == dict:
                source[key] = self.__merge_data(source[key], append[key])
            else:
                source[key] = append[key]
        return source

    def __get_final_conf(self, conf_dir_path: Union[None, str] = None,
                         scope: Union[None, List[str]] = None,
                         check_autogen: bool = True) -> dict:
        if scope is None:
            files = os.listdir(conf_dir_path)
            if 'config.yaml' not in files:
                raise EvokConfigError(f"Missing 'config.yaml' in evok configuration directory ({conf_dir_path})")
            scope = files
        final_conf = {}
        for path in scope:
            try:
                with open(path, 'r') as f:
                    ydata: dict = yaml.load(f, Loader=yaml.Loader)
                self.__merge_data(final_conf, ydata)
            except FileNotFoundError:
                logger.warning(f"Config file {path} not found!")
        if check_autogen and final_conf.get('autogen', False):
            logger.info(f"Including autogen....")
            return self.__get_final_conf(scope=['/etc/evok/autogen.yaml', *scope], check_autogen=False)
        return final_conf

    @staticmethod
    def __get_hw_tree(data: dict) -> dict:
        ret = {}
        if 'hw_tree' not in data:
            logger.warning("Section 'hw_tree' not in configuration!")
            return ret
        for name, value in data['hw_tree'].items():
            ret[name] = value
        return ret

    @staticmethod
    def __get_apis_conf(data: dict) -> dict:
        ret = {}
        if 'apis' not in data:
            logger.warning("Section 'apis' not in configuration!")
            return ret
        for name, value in data['apis'].items():
            ret[name] = value
        return ret

    @staticmethod
    def __get_logging_conf(data: dict) -> dict:
        ret = {}
        if 'logging' not in data:
            logger.warning("Section 'logging' not in configuration!")
            return ret
        for name, value in data['logging'].items():
            ret[name] = value
        return ret

    def configtojson(self):
        return self.main  # TODO: zkontrolovat!!

    def get_hw_tree(self) -> dict:
        return self.hw_tree

    def get_api(self, name: str) -> dict:
        if name not in self.apis:
            logging.warning(f"Api '{name}' not found")
            return {}
        return self.apis[name]


def hexint(value):
    if value.startswith('0x'):
        return int(value[2:], 16)
    return int(value)


def create_devices(evok_config: EvokConfig, hw_dict):
    dev_counter = 0
    for bus_name, bus_data in evok_config.get_hw_tree().items():
        bus_data: dict
        if not bus_data.get("enabled", True):
            logger.info(f"Skipping disabled bus '{bus_name}'")
            continue
        bus_type = bus_data['type']

        bus = None
        if bus_type == 'OWBUS':
            dev_counter += 1
            interval = bus_data.get("interval", 60)
            scan_interval = bus_data.get("scan_interval", 300)

            circuit = bus_name
            ow_bus_driver = owdevice.OwBusDriver(circuit, interval=interval, scan_interval=scan_interval)
            bus = OWBusDevice(ow_bus_driver, dev_id=dev_counter)
            Devices.register_device(OWBUS, bus)

        elif bus_type == 'MODBUSTCP':
            dev_counter += 1
            modbus_server = bus_data.get("hostname", "127.0.0.1")
            modbus_port = bus_data.get("port", 502)
            bus_driver = EvokModbusTcpClient(host=modbus_server, port=modbus_port)
            bus = TcpBusDevice(circuit=bus_name, bus_driver=bus_driver, dev_id=dev_counter)
            Devices.register_device(TCPBUS, bus)

        elif bus_type == "MODBUSRTU":
            dev_counter += 1
            serial_port = bus_data["port"]
            serial_baud_rate = bus_data.get("baudrate", 19200)
            serial_parity = bus_data.get("parity", 'N')
            serial_stopbits = bus_data.get("stopbits", 1)
            bus_driver = EvokModbusSerialClient(port=serial_port, baudrate=serial_baud_rate, parity=serial_parity,
                                                stopbits=serial_stopbits, timeout=1)
            bus = SerialBusDevice(circuit=bus_name, bus_driver=bus_driver, dev_id=dev_counter)
            Devices.register_device(SERIALBUS, bus)

        if 'devices' not in bus_data:
            logging.info(f"Creating bus '{bus_name}' with type '{bus_type}'.")
            continue

        logging.info(f"Creating bus '{bus_name}' with type '{bus_type}' with devices.")
        for device_name, device_data in bus_data['devices'].items():
            if not device_data.get("enabled", True):
                logger.info(f"^ Skipping disabled device '{device_name}'")
                continue
            logging.info(f"^ Creating device '{device_name}' with type '{bus_type}'")
            try:
                dev_counter += 1
                if bus_type == 'OWBUS':
                    ow_type = device_data.get("type")
                    address = device_data.get("address")
                    interval = device_data.getintdef("interval", 15)

                    circuit = device_name
                    sensor = owdevice.MySensorFabric(address, ow_type, bus, interval=interval, circuit=circuit,
                                                     is_static=True)
                    if ow_type in ["DS2408", "DS2406", "DS2404", "DS2413"]:
                        sensor = OWSensorDevice(sensor, dev_id=dev_counter)
                    Devices.register_device(SENSOR, sensor)

                elif bus_type in ['MODBUSTCP', 'MODBUSRTU']:
                    slave_id = device_data.get("slave-id", 1)
                    scanfreq = device_data.get("scan_frequency", 50)
                    scan_enabled = device_data.get("scan_enabled", True)
                    device_model = device_data["model"]
                    circuit = device_name
                    major_group = device_name

                    slave = ModbusSlave(bus.bus_driver, circuit, evok_config, scanfreq, scan_enabled,
                                        hw_dict, device_model=device_model, slave_id=slave_id,
                                        dev_id=dev_counter, major_group=major_group)
                    Devices.register_device(MODBUS_SLAVE, slave)

                else:
                    dev_counter -= 1
                    logger.error(f"Unknown bus type: '{bus_type}'! skipping...")

            except Exception as E:
                logger.exception(f"Error in config section '{bus_type}:{device_name}' - {str(E)}")


def load_aliases(path):
    alias_dicts = HWDict(paths=[path]).definitions
    # HWDict returns List(), take only first item
    alias_conf = alias_dicts[0] if len(alias_dicts) > 0 else dict()
    version = alias_conf.get("version",None)
    if version == 1.0:
        # transform array to dict and rename dev_type -> devtype if version 1.0
        result = dict(((rec["name"], {"circuit": rec.get("circuit",None), "devtype": rec.get("dev_type", None)}) \
                       for rec in alias_conf.get("aliases", {}) \
                       if rec.get("name", None) is not None))
    elif version == 2.0:
        result = alias_conf.get("aliases", {})
    else:
        result = {}
    Devices.aliases = Aliases(result)
    logger.debug(f"Load aliases with {result}")


# don't call it directly in asyn loop -- block
def save_aliases(alias_dict, path):
    try:
        logger.info(f"Saving alias file {path}")
        with open(path, 'w+') as yfile:
            yfile.write(yaml.dump({"version": 2.0, "aliases": alias_dict}))
    except Exception as E:
        logger.exception(str(E))
