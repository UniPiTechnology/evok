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

up_globals = {
    'version': "UniPi 1.0",
    'devices': {
        'ai': {
            '1': 5.564920867,
            '2': 5.564920867,
        }
    },
    'version1': None,
    'version2': None,
}


def read_config():
    global up_globals
    up_globals['model'] = 'S103'
    up_globals['serial'] = 2535


class HWDict():
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
                try:
                    with open(file_path, 'r') as yfile:
                        self.definitions += [yaml.load(yfile, Loader=yaml.SafeLoader)]
                        logger.info("YAML Definition loaded: %s, type: %s, definition count %d", file_path,
                                    len(self.definitions[len(self.definitions) - 1]), len(self.definitions) - 1)
                except Exception as E:
                    raise E
                    pass


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


def create_devices(Config, hw_dict):
    dev_counter = 0
    Config.hw_dict = hw_dict
    for section in Config.sections():
        # split section name ITEM123 or ITEM_123 or ITEM-123 into device=ITEM and circuit=123
        res = re.search('^([^_-]+)[_-]+(.+)$', section)
        if not res:
            res = re.search('^(.*\D)(\d+)$', section)
            if not res: continue
        devclass = res.group(1)
        circuit = res.group(2)
        print(section, res, devclass, circuit)
        try:
            if devclass == 'OWBUS':
                import owclient
                bus = Config.get(section, "owbus")
                interval = Config.getfloat(section, "interval")
                scan_interval = Config.getfloat(section, "scan_interval")
                #### prepare 1wire process ##### (using thread affects timing!)
                resultPipe = multiprocessing.Pipe()
                taskPipe = multiprocessing.Pipe()
                bus_driver = owclient.OwBusDriver(circuit, taskPipe, resultPipe, bus=bus,
                                                  interval=interval, scan_interval=scan_interval)
                owbus = OWBusDevice(bus_driver, dev_id=0)
                Devices.register_device(OWBUS, owbus)
            elif devclass == 'SENSOR' or devclass == '1WDEVICE':
                # permanent thermometer
                bus = Config.get(section, "bus")
                owbus = (Devices.by_int(OWBUS, bus)).bus_driver
                ow_type = Config.get(section, "type")
                address = Config.get(section, "address")
                interval = Config.getintdef(section, "interval", 15)
                sensor = owclient.MySensorFabric(address, ow_type, owbus, interval=interval, circuit=circuit,
                                                 is_static=True)
                if ow_type in ["DS2408", "DS2406", "DS2404", "DS2413"]:
                    sensor = OWSensorDevice(sensor, dev_id=0)
                Devices.register_device(SENSOR, sensor)
            elif devclass == '1WRELAY':
                # Relays on DS2404
                sensor = Config.get(section, "sensor")
                sensor = (Devices.by_int(SENSOR, sensor)).sensor_dev
                pin = Config.getint(section, "pin")
                r = unipig.DS2408_relay(circuit, sensor, pin, dev_id=0)
                Devices.register_device(RELAY, r)
            elif devclass == '1WINPUT':
                # Inputs on DS2404
                sensor = Config.get(section, "sensor")
                sensor = (Devices.by_int(SENSOR, sensor)).sensor_dev
                pin = Config.getint(section, "pin")
                i = unipig.DS2408_input(circuit, sensor, pin, dev_id=0)
                Devices.register_device(INPUT, i)
            elif devclass == 'I2CBUS':
                # I2C bus on /dev/i2c-1 via pigpio daemon
                busid = Config.getint(section, "busid")
                bus_driver = I2cBus(circuit=circuit, busid=busid)
                i2cbus = I2CBusDevice(bus_driver, 0)
                Devices.register_device(I2CBUS, i2cbus)
            elif devclass == 'MCP':
                # MCP on I2c
                i2cbus = Config.get(section, "i2cbus")
                address = hexint(Config.get(section, "address"))
                bus = (Devices.by_int(I2CBUS, i2cbus)).bus_driver
                mcp = unipig.UnipiMcp(bus, circuit, address=address, dev_id=0)
                Devices.register_device(MCP, mcp)
            elif devclass == 'RELAY':
                # Relays on MCP
                mcp = Config.get(section, "mcp")
                mcp = Devices.by_int(MCP, mcp)
                pin = Config.getint(section, "pin")
                r = unipig.Relay(circuit, mcp, pin, dev_id=0)
                Devices.register_device(RELAY, r)
            elif devclass == 'GPIOBUS':
                # access to GPIO via pigpio daemon
                bus_driver = GpioBus(circuit=circuit)
                gpio_bus = GPIOBusDevice(bus_driver, 0)
                Devices.register_device(GPIOBUS, gpio_bus)
            elif devclass == 'PCA9685':
                # PCA9685 on I2C
                i2cbus = Config.get(section, "i2cbus")
                address = hexint(Config.get(section, "address"))
                frequency = Config.getintdef(section, "frequency", 400)
                bus = (Devices.by_int(I2CBUS, i2cbus)).bus_driver
                pca = unipig.UnipiPCA9685(bus, int(circuit), address=address, frequency=frequency, dev_id=0)
                Devices.register_device(PCA9685, pca)
            elif devclass in ('AO', 'ANALOGOUTPUT'):
                try:
                    # analog output on PCA9685
                    pca = Config.get(section, "pca")
                    channel = Config.getint(section, "channel")
                    # value = Config.getfloatdef(section, "value", 0)
                    driver = Devices.by_int(PCA9685, pca)
                    ao = unipig.AnalogOutputPCA(circuit, driver, channel, dev_id=0)
                except:
                    # analog output (PWM) on GPIO via pigpio daemon
                    gpiobus = Config.get(section, "gpiobus")
                    bus = (Devices.by_int(GPIOBUS, gpiobus)).bus_driver
                    frequency = Config.getintdef(section, "frequency", 100)
                    value = Config.getfloatdef(section, "value", 0)
                    ao = unipig.AnalogOutputGPIO(bus, circuit, frequency=frequency, value=value, dev_id=0)
                Devices.register_device(AO, ao)
            elif devclass in ('DI', 'INPUT'):
                # digital inputs on GPIO via pigpio daemon
                gpiobus = Config.get(section, "gpiobus")
                bus = (Devices.by_int(GPIOBUS, gpiobus)).bus_driver
                pin = Config.getint(section, "pin")
                debounce = Config.getintdef(section, "debounce", 0)
                counter_mode = Config.getstringdef(section, "counter_mode", "disabled")
                inp = unipig.Input(bus, circuit, pin, debounce=debounce, counter_mode=counter_mode, dev_id=0)
                Devices.register_device(INPUT, inp)
            elif devclass in ('EPROM', 'EE'):
                i2cbus = Config.get(section, "i2cbus")
                address = hexint(Config.get(section, "address"))
                size = Config.getintdef(section, "size", 256)
                bus = (Devices.by_int(I2CBUS, i2cbus)).bus_driver
                ee = unipig.Eprom(bus, circuit, size=size, address=address, dev_id=0)
                Devices.register_device(EE, ee)
            elif devclass in ('AICHIP',):
                i2cbus = Config.get(section, "i2cbus")
                address = hexint(Config.get(section, "address"))
                bus = (Devices.by_int(I2CBUS, i2cbus)).bus_driver
                mcai = unipig.UnipiMCP342x(bus, circuit, address=address, dev_id=0)
                Devices.register_device(ADCHIP, mcai)
            elif devclass in ('AI', 'ANALOGINPUT'):
                chip = Config.get(section, "chip")
                channel = Config.getint(section, "channel")
                interval = Config.getfloatdef(section, "interval", 0)
                bits = Config.getintdef(section, "bits", 14)
                gain = Config.getintdef(section, "gain", 1)
                if circuit in ('1', '2'):
                    correction = Config.getfloatdef(section, "correction", up_globals['devices']['ai'][circuit])
                else:
                    correction = Config.getfloatdef(section, "correction", 5.564920867)
                mcai = Devices.by_int(ADCHIP, chip)
                try:
                    corr_rom = Config.get(section, "corr_rom")
                    eeprom = Devices.by_int(EE, corr_rom)
                    corr_addr = hexint(Config.get(section, "corr_addr"))
                    ai = unipig.AnalogInput(circuit, mcai, channel, bits=bits, gain=gain,
                                            continuous=False, interval=interval, correction=correction, rom=eeprom,
                                            corr_addr=corr_addr, dev_id=0)
                except:
                    ai = unipig.AnalogInput(circuit, mcai, channel, bits=bits, gain=gain,
                                            continuous=False, interval=interval, correction=correction, dev_id=0)
                Devices.register_device(AI, ai)
            elif devclass == 'NEURON':
                from neuron import Neuron
                dev_counter += 1
                modbus_server = Config.getstringdef(section, "modbus_server", "127.0.0.1")
                modbus_port = Config.getintdef(section, "modbus_port", 502)
                scanfreq = Config.getfloatdef(section, "scan_frequency", 1)
                scan_enabled = Config.getbooldef(section, "scan_enabled", True)
                allow_register_access = Config.getbooldef(section, "allow_register_access", False)
                circuit = Config.getintdef(section, "global_id", 2)
                neuron = Neuron(circuit, Config, modbus_server, modbus_port, scanfreq, scan_enabled, hw_dict,
                                direct_access=allow_register_access,
                                dev_id=dev_counter)
                Devices.register_device(NEURON, neuron)
            elif devclass == 'EXTENSION':
                from neuron import UartNeuron
                dev_counter += 1
                modbus_uart_port = Config.getstringdef(section, "modbus_uart_port", "/dev/ttyNS0")
                scanfreq = Config.getfloatdef(section, "scan_frequency", 10)
                scan_enabled = Config.getbooldef(section, "scan_enabled", True)
                uart_baud_rate = Config.getintdef(section, "baud_rate", 19200)
                uart_parity = Config.getstringdef(section, "parity", 'N')
                uart_stopbits = Config.getintdef(section, "stop_bits", 1)
                uart_address = Config.getintdef(section, "address", 1)
                device_name = Config.getstringdef(section, "device_name", "unspecified")
                allow_register_access = Config.getbooldef(section, "allow_register_access", False)
                neuron_uart_circuit = Config.getstringdef(section, "neuron_uart_circuit", "None")
                circuit = Config.getintdef(section, "global_id", 2)
                neuron = UartNeuron(circuit, Config, modbus_uart_port, scanfreq, scan_enabled, hw_dict,
                                    baud_rate=uart_baud_rate,
                                    parity=uart_parity, stopbits=uart_stopbits, device_name=device_name,
                                    uart_address=uart_address,
                                    direct_access=allow_register_access, dev_id=dev_counter,
                                    neuron_uart_circuit=neuron_uart_circuit)
                Devices.register_device(NEURON, neuron)
            elif devclass == 'IRISCARD':
                from neuron import TcpNeuron
                dev_counter += 1
                modbus_server = Config.getstringdef(section, "modbus_server", "127.0.0.1")
                modbus_port = Config.getstringdef(section, "modbus_port", "502")
                scanfreq = Config.getfloatdef(section, "scan_frequency", 10)
                scan_enabled = Config.getbooldef(section, "scan_enabled", True)
                modbus_address = Config.getintdef(section, "address", 1)
                device_name = Config.getstringdef(section, "device_name", "unspecified")
                allow_register_access = Config.getbooldef(section, "allow_register_access", False)
                circuit = Config.getintdef(section, "global_id", 2)
                neuron = TcpNeuron(circuit, Config, modbus_server, modbus_port, scanfreq, scan_enabled, hw_dict,
                                   device_name=device_name, modbus_address=modbus_address,
                                   direct_access=allow_register_access, dev_id=dev_counter)
                Devices.register_device(NEURON, neuron)

        except Exception as E:
            logger.exception("Error in config section %s - %s", section, str(E))


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
