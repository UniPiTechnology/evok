import os
import multiprocessing
import struct
import ConfigParser
import neuron
from tornado import gen
from log import *
from devices import *
from neuron import WiFiAdapter

try:
    import unipig
    from apigpio import I2cBus, GpioBus
except:
    pass

up_globals = {
    'version': "1.0",
    'devices': {
        'ai': {
            '1': 5.564920867,
            '2': 5.564920867,
        }
    },
    'version1': None,
    'version2': None,
}

def read_eprom_config():
    try:
        with open('/sys/class/i2c-dev/i2c-1/device/1-0050/eeprom','r') as f:
            ee_bytes=f.read(256)
            if ee_bytes[224:226] == '\xfa\x55':
                if ord(ee_bytes[226]) == 1 and ord(ee_bytes[227]) == 1:
                    up_globals['version'] = "UniPi 1.1"
                elif ord(ee_bytes[226]) == 11 and ord(ee_bytes[227]) == 1:
                    up_globals['version'] = "UniPi Lite 1.1"
                else:
                    up_globals['version'] = "UniPi 1.0"
                up_globals['version1'] = up_globals['version']
                #AIs coeff
                if up_globals['version'] in ("UniPi 1.1", "UniPi 1.0"):
                    up_globals['devices'] = { 'ai': {
                                              '1': struct.unpack('!f', ee_bytes[240:244])[0],
                                              '2': struct.unpack('!f', ee_bytes[244:248])[0],
                                         }}
                else:
                    up_globals['devices'] = { 'ai': {
                                              '1': 0,
                                              '2': 0,
                                         }}
                up_globals['serial'] = struct.unpack('i', ee_bytes[228:232])[0]
                logger.debug("eprom: UniPi version %s, serial: %d", up_globals['version'], up_globals['serial'])
    except Exception:
        pass
    try:
        with open('/sys/class/i2c-dev/i2c-1/device/1-0057/eeprom','r') as f:
            ee_bytes=f.read(128)
            if ee_bytes[96:98] == '\xfa\x55':
                up_globals['version2'] = "%d.%d" % (ord(ee_bytes[99]), ord(ee_bytes[98]))
                up_globals['model'] = "%s" % (ee_bytes[106:110],)
                up_globals['serial'] = struct.unpack('i', ee_bytes[100:104])[0]
                logger.info("eprom: UniPi Neuron %s version: %s serial: 0x%x", up_globals["model"], up_globals['version2'],up_globals["serial"])
    except Exception:
        pass
    try:
        with open('/sys/class/i2c-dev/i2c-0/device/1-0057/eeprom','r') as f:
            ee_bytes=f.read(128)
            if ee_bytes[96:98] == '\xfa\x55':
                up_globals['version2'] = "%d.%d" % (ord(ee_bytes[99]), ord(ee_bytes[98]))
                up_globals['model'] = "%s" % (ee_bytes[106:110],)
                up_globals['serial'] = struct.unpack('i', ee_bytes[100:104])[0]
                logger.info("eprom: UniPi Neuron %s version: %s serial: 0x%x", up_globals["model"], up_globals['version2'],up_globals["serial"])
    except Exception:
        pass

    
class HWDict():
    def __init__(self, d_path):
        self.definitions = []
        self.neuron_definition = None
        for filen in os.listdir(d_path):
            if filen.endswith(".yaml"):
                try:
                    with open(d_path + filen, 'r') as yfile:    
                        self.definitions += [yaml.load(yfile)]
                        logger.info("YAML Definition loaded: %s, type: %s, definition count %d", filen, len(self.definitions[len(self.definitions)-1]),  len(self.definitions) - 1)
                except Exception:
                    pass
            elif filen.endswith("BuiltIn") and 'model' in up_globals:
                try:
                    with open(d_path + filen + "/" + up_globals['model'] + '.yaml', 'r') as yfile:    
                        self.neuron_definition = yaml.load(yfile)
                        logger.info("YAML Definition loaded: %s, type: UniPiBuiltIn", d_path + filen + "/" + up_globals['model'] + '.yaml')
                except Exception:
                    logger.error("No valid YAML definition for active Neuron/Axon device!! Device name %s", up_globals['model'])
                    pass
                    
class HWDefinition():
    def __init__(self):
        False
    
class OWBusDevice():
    def __init__(self, bus_driver, dev_id):
        self.dev_id = dev_id
        self.bus_driver = bus_driver
        self.circuit = bus_driver.circuit
        
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
    
class GPIOBusDevice():
    def __init__(self, bus_driver, dev_id):
        self.dev_id = dev_id
        self.bus_driver = bus_driver
        self.circuit = bus_driver.circuit
    
class EvokConfig(ConfigParser.RawConfigParser):

    def __init__(self):
        ConfigParser.RawConfigParser.__init__(self)

    def configtojson(self):
        return dict(
             ( section, 
               dict(
                ( option,
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
                #permanent thermometer
                bus = Config.get(section, "bus")
                owbus = (Devices.by_int(OWBUS, bus)).bus_driver
                ow_type = Config.get(section, "type")
                address = Config.get(section, "address")
                interval = Config.getintdef(section, "interval", 15)
                sensor = owclient.MySensorFabric(address, ow_type, owbus, interval=interval, circuit=circuit,
                                                 is_static=True)
                if ow_type in ["DS2408","DS2406", "DS2404", "DS2413"]:
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
                bus_driver = I2cBus(circuit=circuit, host='localhost', busid=busid)
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
                bus_driver = GpioBus(circuit=circuit, host='localhost')
                gpio_bus = GPIOBusDevice(bus_driver, 0)
                Devices.register_device(GPIOBUS, gpio_bus)
            elif devclass == 'PCA9685':
                #PCA9685 on I2C
                i2cbus = Config.get(section, "i2cbus")
                address = hexint(Config.get(section, "address"))
                frequency = Config.getintdef(section, "frequency", 400)
                bus = (Devices.by_int(I2CBUS, i2cbus)).bus_driver
                pca = unipig.UnipiPCA9685(bus, int(circuit), address=address, frequency=frequency, dev_id=0)
                Devices.register_device(PCA9685, pca)
            elif devclass in ('AO', 'ANALOGOUTPUT'):
                try:
                    #analog output on PCA9685
                    pca = Config.get(section, "pca")
                    channel = Config.getint(section, "channel")
                    #value = Config.getfloatdef(section, "value", 0)
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
                neuron = Neuron(circuit, Config, modbus_server, modbus_port, scanfreq, scan_enabled, hw_dict, direct_access=allow_register_access, 
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
                neuron = UartNeuron(circuit, Config, modbus_uart_port, scanfreq, scan_enabled, hw_dict, baud_rate=uart_baud_rate, 
                                    parity=uart_parity, stopbits=uart_stopbits, device_name=device_name, uart_address=uart_address,
                                    direct_access=allow_register_access, dev_id=dev_counter, neuron_uart_circuit=neuron_uart_circuit)
                Devices.register_device(NEURON, neuron)

        except Exception, E:
            logger.exception("Error in config section %s - %s", section, str(E))

@gen.coroutine
def add_aliases(alias_conf):
    if alias_conf is not None:
        for alias_conf_single in alias_conf:
            if alias_conf_single is not None:
                if "version" in alias_conf_single and "aliases" in alias_conf_single and alias_conf_single["version"] == 1.0:
                    for dev_pointer in alias_conf_single['aliases']:
                        try:
                            dev_obj = Devices.by_int(dev_pointer["dev_type"], dev_pointer["circuit"])
                            logger.info("Alias loaded: " + str(dev_obj) + " " + str(dev_pointer["name"]))
                            if Devices.add_alias(dev_pointer["name"], dev_obj):
                                dev_obj.alias = dev_pointer["name"]
                        except Exception, E:
                            logger.exception(str(E))

def add_wifi():
    wifi = WiFiAdapter("1_01")
    Devices.register_device(WIFI, wifi)