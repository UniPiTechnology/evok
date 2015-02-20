import multiprocessing
import re

import unipig
from apigpio import I2cBus, GpioBus
from devices import *
import owclient

globals = {
    'version': "1.0",
}


def hexint(value):
    if value.startswith('0x'):
        return int(value[2:], 16)
    return int(value)


def getintdef(Config, section, key, default):
    try:
        return Config.getint(section, key)
    except:
        return default


def getfloatdef(Config, section, key, default):
    try:
        return Config.getfloat(section, key)
    except:
        return default


def create_devices(Config):
    for section in Config.sections():
        # split section name ITEM123 or ITEM_123 or ITEM-123 into device=ITEM and circuit=123
        res = re.search('^([^_-]+)[_-]+(.+)$', section)
        if not res:
            res = re.search('^(.*\D)(\d+)$', section)
            if not res: continue
        devclass = res.group(1)
        # devclass = re.sub('[_-]*$','',devclass)
        # circuit = int(res.group(2))
        circuit = res.group(2)
        #print "%s %s %s" % (section,devclass, circuit)
        try:
            if devclass == 'OWBUS':
                bus = Config.get(section, "owbus")
                interval = Config.getfloat(section, "interval")
                scan_interval = Config.getfloat(section, "scan_interval")

                #### prepare 1wire process ##### (using thread affects timing!)
                resultPipe = multiprocessing.Pipe()
                taskPipe = multiprocessing.Pipe()
                owbus = owclient.OwBusDriver(circuit, taskPipe, resultPipe, bus=bus,
                                             interval=interval, scan_interval=scan_interval)
                Devices.register_device(OWBUS, owbus)
            elif devclass == 'SENSOR':
                #permanent thermometer
                bus = Config.get(section, "bus")
                owbus = Devices.by_int(OWBUS, bus)
                typ = Config.get(section, "type")
                address = Config.get(section, "address")
                interval = Config.getfloat(section, "interval")
                therm1 = owclient.MySensorFabric(address, typ, owbus, interval=1, circuit=circuit)
                Devices.register_device(SENSOR, therm1)
            elif devclass == 'I2CBUS':
                # I2C bus on /dev/i2c-1 via pigpio daemon
                busid = Config.getint(section, "busid")
                i2cbus = I2cBus(circuit=circuit, host='localhost', busid=busid)
                Devices.register_device(I2CBUS, i2cbus)
            elif devclass == 'MCP':
                # MCP on I2c
                i2cbus = Config.get(section, "i2cbus")
                address = hexint(Config.get(section, "address"))
                bus = Devices.by_int(I2CBUS, i2cbus)
                mcp = unipig.UnipiMcp(bus, circuit, address=address)
                Devices.register_device(MCP, mcp)
            elif devclass == 'RELAY':
                # Relays on MCP
                mcp = Config.get(section, "mcp")
                mcp = Devices.by_int(MCP, mcp)
                pin = Config.getint(section, "pin")
                r = unipig.Relay(circuit, mcp, pin)
                Devices.register_device(RELAY, r)
            elif devclass == 'GPIOBUS':
                # access to GPIO via pigpio daemon
                bus = GpioBus(circuit=circuit, host='localhost')
                Devices.register_device(GPIOBUS, bus)
            elif devclass in ('AO', 'ANALOGOUTPUT', 'PWM'):
                # analog output (PWM) on GPIO via pigpio daemon
                gpiobus = Config.get(section, "gpiobus")
                bus = Devices.by_int(GPIOBUS, gpiobus)
                frequency = getintdef(Config, section, "frequency", 100)
                value = getfloatdef(Config, section, "value", 0)
                ao = unipig.AnalogOutput(bus, circuit, frequency=frequency, value=value)
                Devices.register_device(AO, ao)
            elif devclass in ('INPUT', 'DI'):
                # digital inputs on GPIO via pigpio daemon
                gpiobus = Config.get(section, "gpiobus")
                bus = Devices.by_int(GPIOBUS, gpiobus)
                pin = Config.getint(section, "pin")
                debounce = getintdef(Config, section, "debounce", 0)
                inp = unipig.Input(bus, circuit, pin, debounce=debounce)
                Devices.register_device(INPUT, inp)
            elif devclass in ('EPROM', 'EE'):
                i2cbus = Config.get(section, "i2cbus")
                address = hexint(Config.get(section, "address"))
                size = getintdef(Config, section, "size", 256)
                bus = Devices.by_int(I2CBUS, i2cbus)
                ee = unipig.Eprom(bus, circuit, size=size, address=address)
                Devices.register_device(EE, ee)
            elif devclass in ('AICHIP',):
                i2cbus = Config.get(section, "i2cbus")
                address = hexint(Config.get(section, "address"))
                bus = Devices.by_int(I2CBUS, i2cbus)
                mcai = unipig.UnipiMCP342x(bus, circuit, address=address)
                Devices.register_device(ADCHIP, mcai)
            elif devclass in ('AI', 'ANALOGINPUT'):
                chip = Config.get(section, "chip")
                channel = Config.getint(section, "channel")
                interval = getfloatdef(Config, section, "interval", 0)
                bits = getintdef(Config, section, "bits", 14)
                gain = getintdef(Config, section, "gain", 1)
                correction = getfloatdef(Config, section, "correction", 5.564920867)
                corr_rom = Config.get(section, "corr_rom")
                eeprom = Devices.by_int(EE, corr_rom)
                corr_addr = hexint(Config.get(section, "corr_addr"))
                mcai = Devices.by_int(ADCHIP, chip)
                ai = unipig.AnalogInput(circuit, mcai, channel, bits=bits, gain=gain,
                                        continuous=False, interval=interval, correction=correction, rom=eeprom,
                                        corr_addr=corr_addr)
                Devices.register_device(AI, ai)

        except Exception, E:
            print("Error in config section %s - %s" % (section, str(E)))
            #raise

