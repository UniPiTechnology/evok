'''
    Code specific to UniPi 1.1 devices
'''

import asyncio
import multiprocessing
import struct
import time
import datetime
import atexit
from math import isnan, floor

#from tornado import gen
from tornado.ioloop import IOLoop
#import pigpio
from devices import *
import config
from evok import owclient
from evok.apigpio import GpioBus, I2cBus
from log import *

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


class Unipig:
    """
    Class for unipig control
    """
    def __init__(self, circuit, evok_conf, hw_dict, device_model='unspecified' , dev_id=0):
        self.alias = ""
        self.circuit = circuit
        self.dev_id = dev_id
        self.devtype = MODBUS_SLAVE
        self.modbus_cache_map = None
        self.datadeps = {}
        self.boards = list()
        self.hw_dict = hw_dict
        self.device_model = device_model
        self.evok_conf = evok_conf
        self.do_scanning = False
        self.is_scanning = False
        self.scanning_error_triggered = False
        self.hw_board_dict = {}
        self.versions = []
        self.logfile = evok_conf.getstringdef("log_file", "/var/log/evok.log")

    def get(self):
        return self.full()

    async def set(self, print_log=None):
        return ""

    async def readboards(self, alias_dict):
        self.boards = list()
        try:
            for defin in self.hw_dict.definitions:
                if defin and (defin['type'] == self.device_model):
                    self.hw_board_dict = defin
                    break
            board = Board(self.evok_conf, self.circuit, self)
            await board.parse_definition(self.hw_dict)
            self.boards.append(board)
            await config.add_aliases(alias_dict)
        except Exception as E:
            Devices.remove_global_device(0)
            logger.exception(str(E))
            pass

    def switch_to_async(self, loop, alias_dict):
        self.loop = loop
        loop.add_callback(lambda: self.readboards(alias_dict))


class Board(object):
    def __init__(self, evok_conf, circuit, unipig: Unipig):
        self.alias = ""
        self.devtype = BOARD
        self.evok_conf = evok_conf
        self.circuit = circuit
        self.unipig: Unipig = unipig

    async def set(self, alias=None):
        if not alias is None:
            if Devices.add_alias(alias, self, file_update=True):
                self.alias = alias
        return await self.full()

    def parse_feature_ro(self, feature: dict):
        # Relays on MCP
        mcp = feature.get("mcp")
        mcp = Devices.by_int(MCP, mcp)
        pin = feature.get("pin")
        circuit = feature.get("circuit")
        r = Relay(circuit, mcp, pin, dev_id=0)
        Devices.register_device(RELAY, r)

    def parse_feature_ai(self, feature: dict):
        chip = feature.get("chip")
        channel = feature.get("channel")
        interval = feature.get("interval", 0)
        bits = feature.get("bits", 14)
        gain = feature.get("gain", 1)
        circuit = feature.get("circuit")
        if circuit in ('1', '2'):
            correction = feature.get("correction")
        else:
            correction = feature.get("correction", 5.564920867)
        mcai = Devices.by_int(ADCHIP, chip)
        try:
            circuit = feature.get("circuit")
            corr_rom = feature.get("corr_rom")
            eeprom = Devices.by_int(EE, corr_rom)
            corr_addr = int(feature.get("corr_addr"))
            ai = AnalogInput(circuit, mcai, channel, bits=bits, gain=gain,
                                continuous=False, interval=interval, correction=correction, rom=eeprom,
                                corr_addr=corr_addr, dev_id=0)
        except:
            ai = AnalogInput(circuit, mcai, channel, bits=bits, gain=gain,
                                continuous=False, interval=interval, correction=correction, dev_id=0)
        Devices.register_device(AI, ai)

    def parse_feature_ao(self, feature: dict):
        try:
            # analog output on PCA9685
            pca = feature.get("pca")
            channel = feature.get("channel")
            circuit = feature.get("circuit")
            # value = Config.getfloatdef(section, "value", 0)
            driver = Devices.by_int(PCA9685, pca)
            ao = AnalogOutputPCA(circuit, driver, channel, dev_id=0)
        except:
            # analog output (PWM) on GPIO via pigpio daemon
            gpiobus = feature.get("gpiobus")
            bus = (Devices.by_int(GPIOBUS, gpiobus)).bus_driver
            frequency = feature.get("frequency", 100)
            value = feature.get("value", 0)
            circuit = feature.get("circuit")
            ao = AnalogOutputGPIO(bus, circuit, frequency=frequency, value=value, dev_id=0)
        Devices.register_device(AO, ao)

    def parse_feature_di(self, feature: dict):
        # digital inputs on GPIO via pigpio daemon
        gpiobus = feature.get("gpiobus")
        bus = (Devices.by_int(GPIOBUS, gpiobus)).bus_driver
        pin = feature.get("pin")
        debounce = feature.get("debounce", 0)
        counter_mode = feature.get("counter_mode", "disabled")
        circuit = feature.get("circuit")
        inp = Input(bus, circuit, pin, debounce=debounce, counter_mode=counter_mode, dev_id=0)
        Devices.register_device(INPUT, inp)

    def parse_feature_mcp(self, feature: dict):
        # MCP on I2c
        i2cbus = feature.get("i2cbus")
        address = int(feature.get("address"))
        circuit = feature.get("circuit")
        bus = (Devices.by_int(I2CBUS, i2cbus)).bus_driver
        mcp = UnipiMcp(bus, circuit, address=address, dev_id=0)
        Devices.register_device(MCP, mcp)

    def parse_feature_eeprom(self, feature: dict):
        i2cbus = feature.get("i2cbus")
        address = int(feature.get("address"))
        size = feature.get("size", 256)
        circuit = feature.get("circuit")
        bus = (Devices.by_int(I2CBUS, i2cbus)).bus_driver
        ee = Eprom(bus, circuit, size=size, address=address, dev_id=0)
        Devices.register_device(EE, ee)

    def parse_feature_aichip(self, feature: dict):
        i2cbus = feature.get("i2cbus")
        address = int(feature.get("address"))
        circuit = feature.get("circuit")
        bus = (Devices.by_int(I2CBUS, i2cbus)).bus_driver
        mcai = UnipiMCP342x(bus, circuit, address=address, dev_id=0)
        Devices.register_device(ADCHIP, mcai)

    def parse_feature_pca9685(self, feature: dict):
        # PCA9685 on I2C
        i2cbus = feature.get("i2cbus")
        address = int(feature.get("address"))
        frequency = feature.get("frequency", 400)
        circuit = feature.get("circuit")
        bus = (Devices.by_int(I2CBUS, i2cbus)).bus_driver
        pca = UnipiPCA9685(bus, circuit, address=address, frequency=frequency, dev_id=0)
        Devices.register_device(PCA9685, pca)

    def parse_feature_1w_relay(self, feature: dict):
        # Relays on DS2404
        sensor = feature.get("sensor")
        sensor = (Devices.by_int(SENSOR, sensor)).sensor_dev
        pin = feature.get("pin")
        circuit = feature.get("circuit")
        r = DS2408_relay(circuit, sensor, pin, dev_id=0)
        Devices.register_device(RELAY, r)

    def parse_feature_1w_input(self, feature: dict):
        # Inputs on DS2404
        sensor = feature.get("sensor")
        sensor = (Devices.by_int(SENSOR, sensor)).sensor_dev
        pin = feature.get("pin")
        circuit = feature.get("circuit")
        i = DS2408_input(circuit, sensor, pin, dev_id=0)
        Devices.register_device(INPUT, i)

    def parse_feature_i2cbus(self, feature: dict):
        busid = feature.get("busid")
        bus_driver = I2cBus(circuit=feature.get('circuit'), busid=busid)
        i2cbus = I2CBusDevice(bus_driver, 0)
        Devices.register_device(I2CBUS, i2cbus)

    def parse_feature_gpiobus(self, feature: dict):
        bus_driver = GpioBus(circuit=feature.get('circuit'))
        gpio_bus = GPIOBusDevice(bus_driver, 0)
        Devices.register_device(GPIOBUS, gpio_bus)

    def parse_feature_owbus(self, feature: dict):
        bus = feature.get("owbus")
        interval = feature.get("interval")
        scan_interval = feature.get("scan_interval")
        circuit = feature.get('circuit')

        resultPipe = multiprocessing.Pipe()
        taskPipe = multiprocessing.Pipe()
        bus_driver = owclient.OwBusDriver(circuit, taskPipe, resultPipe, bus=bus,
                                          interval=interval, scan_interval=scan_interval)
        owbus = OWBusDevice(bus_driver, dev_id=0)
        Devices.register_device(OWBUS, owbus)

    def parse_feature(self, feature: dict):
        if feature['type'] == 'DI':
            self.parse_feature_di(feature)
        elif feature['type'] == 'RELAY':
            self.parse_feature_ro(feature)
        elif feature['type'] == 'MCP':
            self.parse_feature_mcp(feature)
        elif feature['type'] in ('AO', 'ANALOGOUTPUT'):
            self.parse_feature_ao(feature)
        elif feature['type'] in ('DI', 'INPUT'):
            self.parse_feature_di(feature)
        elif feature['type'] in ('EPROM', 'EE'):
            self.parse_feature_eeprom(feature)
        elif feature['type'] in ('AICHIP',):
            self.parse_feature_aichip(feature)
        elif feature['type'] in ('AI', 'ANALOGINPUT'):
            self.parse_feature_ai(feature)
        elif feature['type'] == 'PCA9685':
            self.parse_feature_pca9685(feature)
        elif feature['type'] == '1WRELAY':
            self.parse_feature_1w_relay(feature)
        elif feature['type'] == '1WINPUT':
            self.parse_feature_1w_input(feature)
        elif feature['type'] == 'GPIOBUS':
            self.parse_feature_gpiobus(feature)
        elif feature['type'] == 'I2CBUS':
            self.parse_feature_i2cbus(feature)
        elif feature['type'] == 'OWBUS':
            self.parse_feature_owbus(feature)
        else:
            logging.error("Unknown feature: " + str(feature) + " at UNIPIG")

    async def parse_definition(self, hw_dict):
        self.volt_refx = 33000
        self.volt_ref = 3.3
        for defin in hw_dict.definitions:
            if defin and (self.unipig.device_model == defin['type']):
                for name, feature in defin.items():
                    if type(feature) is not dict:
                        continue
                    feature['type'], feature['circuit'] = name.split('_')
                    self.parse_feature(feature)
                return
        logging.error(f"Not found type '{self.unipig.device_model}' in loaded hw-definitions.")

    def get(self):
        return self.full()


class Eprom(object):
    def __init__(self, i2cbus, circuit, address=0x50, size=256, major_group=1, dev_id=0):
        # running with blocking
        self.alias = ""
        self.devtype = EE
        self.dev_id = dev_id
        self.circuit = circuit
        self.i2cbus = i2cbus
        self.size = size
        self.major_group = major_group
        self.i2c = i2cbus.i2c_open(i2cbus.busid, address, 0)
        atexit.register(self.stop)
        self.__init_board_version()

    def full(self):
        return {'dev': 'ee', 'circuit': self.circuit, 'glob_dev_id': self.dev_id}

    def stop(self):
        self.i2cbus.i2c_close(self.i2c)

    def __init_board_version(self):
        prefix = self.i2cbus.i2c_read_byte_data(self.i2c, 0xe2)
        suffix = self.i2cbus.i2c_read_byte_data(self.i2c, 0xe3)
        if prefix == 1 and suffix == 1:
            config.up_globals['version'] = "1.1"
        else:
            config.up_globals['version'] = "1.0"
        # print "UniPi version:" + config.up_globals['version']

    async def write_byte(self, index, value):
        assert (index < self.size and index >= 0)
        async with self.i2cbus.iolock:
            # write byte
            extents = [struct.pack("I", (value & 0xff))]
            result = await self.i2cbus.apigpio_command_ext(
                pigpio._PI_CMD_I2CWB,
                self.i2c, index, 4, extents)
            pigpio._u2i(result)  # check errors

    async def read_byte(self, index):
        assert (index < 256 and index >= 0)
        async with self.i2cbus.iolock:
            result = await self.i2cbus.apigpio_command(
                pigpio._PI_CMD_I2CRB, self.i2c, index)
            return(pigpio._u2i(result))


#################################################################
#
# Relays on MCP 23008
#
#################################################################

MCP23008_IODIR = 0x00  # direction 1=inp, 0=out
MCP23008_IPOL = 0x01  # reversed input polarity.
MCP23008_GPPU = 0x06  # pullup
MCP23008_GPIO = 0x09  # input/output
MCP23008_OLAT = 0x0A  # latch output status


class UnipiMcp(object):
    def __init__(self, i2cbus, circuit, address=0x20, major_group=1, dev_id=0):
        self.alias = ""
        self.devtype = MCP
        self.dev_id = dev_id
        # running with blocking
        self.circuit = circuit
        self.i2cbus = i2cbus
        self.major_group = major_group
        self.i2c = i2cbus.i2c_open(i2cbus.busid, address, 0)
        atexit.register(self.stop)
        i2cbus.i2c_write_byte_data(self.i2c, MCP23008_IODIR, 0x00)  # all output !
        #pi.i2c_write_byte_data(self.i2c, MCP23008_GPPU, 0x00)   # no pullup, not req on output
        self.relays = []
        self.value = i2cbus.i2c_read_byte_data(self.i2c, MCP23008_OLAT)

    def stop(self):
        self.i2cbus.i2c_close(self.i2c)

    def full(self):
        return {'dev': 'mcp', 'circuit': self.circuit, 'glob_dev_id': self.dev_id}

    def register_relay(self, relay):
        if not (relay in self.relays):
            self.relays.append(relay)

    async  def __set_masked_value(self, mask, value):
        # old pattern
        if value:
            byte_val = (self.value | mask) & 0xff
        else:
            byte_val = (self.value & ~mask) & 0xff

        async with self.i2cbus.iolock:
            #write byte
            extents = [struct.pack("I", byte_val)]
            result = await self.i2cbus.apigpio_command_ext(
                pigpio._PI_CMD_I2CWB,
                self.i2c, MCP23008_GPIO, 4, extents)
            pigpio._u2i(result)  # check errors

            #read byte
            result = await self.i2cbus.apigpio_command(
                pigpio._PI_CMD_I2CRB,
                self.i2c, MCP23008_OLAT)
            mask = self.value
            self.value = pigpio._u2i(result)
            mask = mask ^ self.value
            for r in filter(lambda r: r._mask & mask, self.relays):
                devents.status(r)

    async def set_masked_value(self, mask, value):

        if value:
            await self.set_bitmap(mask, 0xff)
        else:
            await self.set_bitmap(mask, 0x0)


    async  def set_bitmap(self, mask, bitmap):
        byte_val = (self.value & ~mask) | (bitmap & mask)
        async with self.i2cbus.iolock:
            #write byte
            extents = [struct.pack("I", byte_val)]
            result = await self.i2cbus.apigpio_command_ext(
                pigpio._PI_CMD_I2CWB,
                self.i2c, MCP23008_GPIO, 4, extents)
            pigpio._u2i(result)  # check errors

            #read byte
            result = await self.i2cbus.apigpio_command(
                pigpio._PI_CMD_I2CRB,
                self.i2c, MCP23008_OLAT)
            mask = self.value
            self.value = pigpio._u2i(result)
            mask = mask ^ self.value
            for r in filter(lambda r: r._mask & mask, self.relays):
                devents.status(r)


_lastt = 0


class Relay(object):
    pending_id = 0

    def __init__(self, circuit, mcp, pin, major_group=1, dev_id=0):
        self.alias = ""
        self.devtype = RELAY
        self.dev_id = dev_id
        self.circuit = circuit
        self.major_group = major_group
        self.mcp = mcp
        self.pin = pin
        self._mask = 1 << pin
        mcp.register_relay(self)
        #self.logger.debug("Relay %d initialized on MCP", self.circuit)

    def full(self):
        return {'dev': 'relay', 'circuit': self.circuit, 'value': self.value, 'pending': self.pending_id != 0, 'glob_dev_id': self.dev_id}

    def simple(self):
        return {'dev': 'relay', 'circuit': self.circuit, 'value': self.value}

    @property
    def value(self):
        return 1 if self.mcp.value & self._mask else 0

    def get_state(self):
        """ Returns ( status, is_pending )
              current on/off status is taken from last mcp value without reading it from hardware
              is_pending is Boolean
        """
        return (self.value, self.pending_id != 0)

    async def set_state(self, value):
        """ Sets new on/off status. Disable pending timeouts
        """
        if self.pending_id:
            IOLoop.instance().remove_timeout(self.pending_id)
            self.pending_id = None
        await self.mcp.set_masked_value(self._mask, value)
        return(1 if self.mcp.value & self._mask else 0)

    async def set(self, value=None, timeout=None, alias=None):
        """ Sets new on/off status. Disable pending timeouts
        """
        if not(value is None):
            #raise Exception('Value must be specified')
            value = int(value)

        if not (timeout is None):
            timeout = float(timeout)

        await self.mcp.set_masked_value(self._mask, value)

        if timeout is None:
            return(1 if self.mcp.value & self._mask else 0)

        async def timercallback():
            self.pending_id = None
            await self.mcp.set_masked_value(self._mask, not value)
            #global _lastt
            #t = IOLoop.instance().time()
            #print "%s %s" % (t-_lastt,t)
            #_lastt = t

        self.pending_id = IOLoop.instance().add_timeout(
            datetime.timedelta(seconds=float(timeout)), timercallback)

        return 1 if self.mcp.value & self._mask else 0


#################################################################
#
# Analog Inputs on MCP 342x
#
#################################################################
BIT_MASKS = (
    (0b11111111111, 0b100000000000, 1.0 / 240),  #12bit
    (0b1111111111111, 0b10000000000000, 1.0 / 60),  #14bit
    (0b111111111111111, 0b1000000000000000, 1.0 / 15),  #16bit
    (0b11111111111111111, 0b100000000000000000, 1.0 / 3.75)  #18bit
)


class UnipiMCP342x(object):
    """ 
        MCP342[128] single/multi channel A/D convertor
    """

    def __init__(self, i2cbus, circuit, address=0x68, major_group=1, dev_id=0):
        # running with blocking
        #self.__config = 0x1c | channel  # continuos operation, 18bit, gain=1
        self.alias = ""
        self.circuit = circuit
        self.major_group = major_group
        self.i2cbus = i2cbus
        self.dev_id = dev_id
        self.i2c = i2cbus.i2c_open(i2cbus.busid, address, 0)
        atexit.register(self.stop)
        self.channels = []
        self.readlen = 4
        self.continuous = False
        self.must_measure = True
        #i2cbus.i2c_write_byte(self.i2c, self.__config)

    def stop(self):
        self.i2cbus.i2c_close(self.i2c)

    def full(self):
        return {'dev': 'adchip', 'circuit': self.circuit, 'glob_dev_id': self.dev_id}

    def switch_to_async(self, mainLoop):
        mainLoop.add_callback(self.measure_loop, mainLoop)

    def calc_mode(self, channel, bits, gain, continuous):
        if not (channel in range(4)): raise Exception("Bad channel number")
        mode = channel << 5
        mode = mode | (bool(continuous) << 4) | ((not bool(continuous)) << 7)  # from one-shoot must be bit7 set
        """ sample rate and resolution
            12 = 12 bit (240 SPS max)  3.5 cifry
            14 = 14 bit (60 SPS max)   4 cifry
            16 = 16 bit (15 SPS max)   5 cifer 
            18 = 18 bit (3.75 SPS max) 5.5 cifry
        """
        if not (bits in (12, 14, 16, 18)): raise Exception("Bad bit resolution")
        mode = mode | ((bits - 12 ) >> 1) << 2
        """ PGA gain selection
                1 = 1x 
                2 = 2x
                4 = 4x
                8 = 8x
        """
        if not gain in (1, 2, 4, 8): raise Exception("Bad gain value")
        bg = 3 if gain == 8 else 2 if gain == 4 else 1 if gain == 2 else 0
        mode = mode | bg
        return mode

    def calc_waittime(self, bits):
        return BIT_MASKS[(bits - 12) >> 1][2]
        #if bits == 12: return 1.0/240
        #if bits == 14: return 1.0/60
        #if bits == 16: return 1.0/15
        #if bits == 18: return 1.0/3.75


    def register_channel(self, ai):
        if not (ai in self.channels):
            self.channels.append(ai)
        ai._mode = self.calc_mode(ai.channel, ai.bits, ai.gain, ai.continuous)
        ai._waittime = self.calc_waittime(ai.bits)
        if ai.continuous:
            self.continuous = True
            self.must_measure = True


    async def measure_loop(self, mainloop):
        # print("Entering measure loop")
        #mainloop = IOLoop.instance()
        try:
            next = None
            looptime = mainloop.time()
            for channel in self.channels:
                channel._nextmeasure = looptime
                await channel._read_correction()
                next = channel

            while True:
                looptime = mainloop.time()
                if next:
                    if not self.continuous or self.must_measure:
                        # run measurement for channel                
                        await self.measure(next)
                        await asyncio.sleep(next._waittime)

                    # try to read value 
                    if (await self.read_raw()):
                        ## set next time for current channel
                        channel = self.lastmeasure
                        if channel.interval > 0:
                            channel._nextmeasure = looptime + channel.interval
                        else:
                            channel._nextmeasure = 0  # single measurement only
                # calc waiting time
                next = None
                for channel in self.channels:
                    if (channel._nextmeasure > 0) and ((next is None) or (channel._nextmeasure < next._nextmeasure)):
                        next = channel

                if next:
                    looptime = mainloop.time()
                    if looptime < next._nextmeasure:
                        await asyncio.sleep(next._nextmeasure-looptime)
                else:
                    await asyncio.sleep(1)

        except Exception as E:
            logger.debug("%s", str(E))


    async  def measure(self, ai):
        self.lastmeasure = ai
        self.continuous = ai.continuous
        async with self.i2cbus.iolock:
            await self.i2cbus.apigpio_command(pigpio._PI_CMD_I2CWS, self.i2c, ai._mode)
        self.must_measure = False

    async def read_raw(self):
        # reads the raw value from the selected previously planned one-shot operation or continuous
        # requires correctly bits
        readlen = 4 if self.lastmeasure.bits == 18 else 3  # if bits=18 : 4 else: 3
        async with self.i2cbus.iolock:
            bytes = pigpio.u2i((await self.i2cbus.apigpio_command(pigpio._PI_CMD_I2CRD, self.i2c, readlen)))
            if bytes <= 0: return
            data = await self.i2cbus.arxbuf(bytes)

        status = data[readlen - 1]
        if status & 0x80:
            # print("Converting in progress")
            return  # converting in progress
        if (self.lastmeasure._mode & 0x7f) != (status & 0x7f):
            # print("Status unexpected")
            return  # something is bad

        value = 0
        for i in range(readlen - 1): value = (value << 8) | data[i]  # join bytes into number
        #print("readRaw end %s %x" %(value,status))
        bits = (status & 0x0c) >> 2
        sign = BIT_MASKS[bits][1] & value
        value &= BIT_MASKS[bits][0]
        if sign: value = -value
        self.lastmeasure._set_voltage(2.048 / BIT_MASKS[bits][0] * value)
        return(True)


class AnalogInput():
    def __init__(self, circuit, mcp, channel, bits=18, gain=1, continuous=False, interval=5.0, correction=5.0, rom=None,
                 corr_addr=None, major_group=1, dev_id=0):
        self.alias = ""
        self.devtype = AI
        self.dev_id = dev_id
        self.circuit = circuit
        self.major_group = major_group
        self.mcp = mcp
        self.channel = channel
        self.conf = False
        self.bits = bits
        self.gain = gain
        self.continuous = continuous
        self.interval = interval
        self.rom = rom
        self.corr_addr = corr_addr
        self.correction = correction
        self.value = None
        self.mtime = None
        mcp.register_channel(self)
        self.koef = self.correction / self.gain

    async def _read_correction(self):
        if self.rom and self.corr_addr:
            hexstr = ""
            for addr in range(self.corr_addr, self.corr_addr + 4):
                res = await self.rom.read_byte(addr)
                result = '{:x}'.format(res)
                if len(result) == 1:
                    result = '0' + result
                hexstr += result
            correction = struct.unpack('!f', hexstr.decode('hex'))[0]
            if correction == 0 or isnan(correction):
                # most probably it is version 1.0 or set by default
                # correction = 5.564920867
                correction = self.correction
            self.correction = correction
        self.koef = self.correction / self.gain

    @property  # docasne!!
    def voltage(self):
        return self.value

    def full(self):
        return {'dev': 'ai', 'circuit': self.circuit, 'value': self.value,
                'time': self.mtime, 'interval': self.interval, 'bits': self.bits, 'gain': self.gain,
                'glob_dev_id': self.dev_id, 'mode': "Simple", "modes": ["Simple"]}

    def simple(self):
        return {'dev': 'ai', 'circuit': self.circuit, 'value': self.value}

    def _set_voltage(self, raw_value):
        if raw_value < 0: raw_value = 0  #value = - (value & self.mask)
        self.value = raw_value * self.koef
        #self.mtime = datetime.datetime.now()
        self.time = time.time()
        devents.status(self)
        #print("Voltage_%d=%s V" %(self.channel,self.voltage,))

    def get(self):
        return (self.value, "%s" % self.time)

    async def set(self, bits=None, gain=None, interval=None, mode=None, alias=None):
        if not (bits is None): self.bits = int(bits)
        if not (gain is None):
            self.gain = int(gain)
            self.koef = self.correction / self.gain
        if not (interval is None): self.interval = float(interval)
        self.mcp.register_channel(self)
        devents.config(self)
        return 0


        #async
        #def Measure(self):
        #    await self.mcp.measure(self)


#################################################################
#
# PCA9685 16-channel, 12-bit PWM Fm+ I2C-bus LED controller Driver
#
# ################################################################

class UnipiPCA9685(object):
    #Registers
    __MODE1             = 0x00
    __MODE2             = 0x01
    __SUBADR1           = 0x02
    __SUBADR2           = 0x03
    __SUBADR3           = 0x04
    __PRESCALE          = 0xFE
    __LED0_ON_L         = 0x06
    __LED0_ON_H         = 0x07
    __LED0_OFF_L        = 0x08
    __LED0_OFF_H        = 0x09

    #Bits
    __RESTART           = 0x80
    __SLEEP             = 0x10
    __OUTDRV            = 0x04
    __INVRT             = 0x10

    #Constants
    __LED_MULTIPLIER    = 0x04
    __CLOCK_FREQ        = 25000000.0


    def __init__(self, i2cbus, circuit, address, frequency=400, dev_id=0):
        self.alias = ""
        self.devtype = I2CBUS
        self.dev_id = dev_id
        self.circuit = circuit
        self.i2cbus = i2cbus
        self.i2c = i2cbus.i2c_open(i2cbus.busid, address, 0)
        atexit.register(self.stop)
        self.channels = []
        self.nr_channels = 16
        #read state of all outputs
        for channel in range(0, self.nr_channels):
            on = int(self.i2cbus.i2c_read_byte_data(self.i2c, self.__LED0_ON_H + self.__LED_MULTIPLIER * channel) << 8)
            on += int(self.i2cbus.i2c_read_byte_data(self.i2c, self.__LED0_ON_L + self.__LED_MULTIPLIER * channel))
            off = int(self.i2cbus.i2c_read_byte_data(self.i2c, self.__LED0_OFF_H + self.__LED_MULTIPLIER * channel) << 8)
            off += int(self.i2cbus.i2c_read_byte_data(self.i2c, self.__LED0_OFF_L + self.__LED_MULTIPLIER * channel))
            self.channels.append((on, off))
            # print "Channel: " + str(channel) + " - " + str(self.channels[channel])

        #set open-drain structure
        i2cbus.i2c_write_byte_data(self.i2c, self.__MODE2, self.__OUTDRV)

        #set open-drain structure and non-inverting function
        #i2cbus.i2c_write_byte_data(self.i2c, self.__MODE2, self.__OUTDRV | self.__INVRT)

        time.sleep(0.005)
        i2cbus.i2c_write_byte_data(self.i2c, self.__MODE1, 0x01 & self.__SLEEP)
        time.sleep(0.005)

        #set frequency
        self.frequency = frequency
        self.__set_freq(self.frequency)

    async def __set_freq(self, freq):
        """
        Set frequency of all channels between 40Hz - 1 000Hz using internal oscillator
        """
        # todo: test frequencies less than 40Hz
        # freq = freq if freq >= 40 else 40
        prescale = int(floor((self.__CLOCK_FREQ / 4096 / freq) - 1 + 0.5))
        prescale = prescale if prescale >= 3 else 3 #hw forces min value of prescale value to 3
        # print "Setting PWM frequency on PCA9685 %d to %d with prescale %d" % (self.circuit, freq, prescale)
        old_mode = await self.i2cbus.i2c_read_byte_data(self.i2c, self.__MODE1) #backup old mode
        new_mode = (old_mode & 0x7F) | self.__SLEEP #sleep mode
        await self.i2cbus.i2c_write_byte_data(self.i2c, self.__MODE1, new_mode) #set SLEEP bit on register MODE1
        await self.i2cbus.i2c_write_byte_data(self.i2c, self.__PRESCALE, prescale) #set PRESCALE register
        await self.i2cbus.i2c_write_byte_data(self.i2c, self.__MODE1, old_mode) #restore previous MODE1 register value
        time.sleep(0.005)
        await self.i2cbus.i2c_write_byte_data(self.i2c, self.__MODE1, old_mode | self.__RESTART) #restart!]
        self.frequency = freq

    async def set_pwm(self, channel, val):
        """
        Set PWM value on channel 0 - 4095
        """
        val = val if val <= 4095 else 4095
        val = val if val >= 0 else 0
        await self.set(channel, 0, val)

    async def set(self, channel, on, off):
        """
        Set LED_on and LED_OFF registers value on channel, on(off) values between 0-4096
        """
        if channel > self.nr_channels - 1: #numbering from 0 to 15
            return
        on = on if on <= 4096 else 4096
        on = on if on >= 0 else 0
        off = off if off <= 4096 else 4096
        off = off if off >= 0 else 0

        async with self.i2cbus.iolock:
            byte_val = on & 0xFF
            extents = [struct.pack("I", byte_val)]
            await self.i2cbus.apigpio_command_ext(
                pigpio._PI_CMD_I2CWB,
                self.i2c, self.__LED0_ON_L + self.__LED_MULTIPLIER*channel, 4, extents)
            result = await self.i2cbus.apigpio_command(
                pigpio._PI_CMD_I2CRB,
                self.i2c, self.__LED0_ON_L + self.__LED_MULTIPLIER*channel)
            pigpio._u2i(result)  # check errors

            byte_val = on >> 8
            extents = [struct.pack("I", byte_val)]
            result = await self.i2cbus.apigpio_command_ext(
                pigpio._PI_CMD_I2CWB,
                self.i2c, self.__LED0_ON_H + self.__LED_MULTIPLIER*channel, 4, extents)
            pigpio._u2i(result)  # check errors

            byte_val = off & 0xFF
            extents = [struct.pack("I", byte_val)]
            result = await self.i2cbus.apigpio_command_ext(
                pigpio._PI_CMD_I2CWB,
                self.i2c, self.__LED0_OFF_L + self.__LED_MULTIPLIER*channel, 4, extents)
            pigpio._u2i(result)  # check errors

            byte_val = off >> 8
            extents = [struct.pack("I", byte_val)]
            result = await self.i2cbus.apigpio_command_ext(
                pigpio._PI_CMD_I2CWB,
                self.i2c, self.__LED0_OFF_H + self.__LED_MULTIPLIER*channel, 4, extents)
            pigpio._u2i(result)  # check errors

            #update object's channels registers
            self.channels[channel] = (on, off)
            #print "PCA9685 "+ str(self.circuit) +" Channel: " + str(channel) + " - " + str((on, off))
            return(True)

    def stop(self):
        self.i2cbus.i2c_close(self.i2c)

    def full(self):
        return {'dev': 'pca9685', 'circuit': self.circuit, 'glob_dev_id': self.dev_id}

    def register_output(self, output):
        if not (output in self.channels):
            self.channels.append(output)


class AnalogOutputPCA():
    def __init__(self, circuit, pca, channel, major_group=1, dev_id=0):
        self.alias = ""
        self.devtype = AO
        self.dev_id = dev_id
        self.circuit = circuit
        self.pca = pca
        self.channel = channel
        self.major_group = major_group
        self.value = 0
        self.value = self.pca.channels[self.channel][1]/409.5

    def full(self):
        return {'dev': 'ao', 'circuit': self.circuit, 'value': self.value, 'frequency': self.pca.frequency, 'glob_dev_id': self.dev_id}

    def simple(self):
        return {'dev': 'ao', 'circuit': self.circuit, 'value': self.value}

    async def set_value(self, value):
        value = float(value)
        result = await self.pca.set_pwm(self.channel, int(floor(value*409.5+0.5)))
        self.value = value
        return(result)

    async def set(self, value=None, frequency=None):
        value = float(value)
        result = await self.pca.set_pwm(self.channel, int(floor(value*409.5+0.5)))
        self.value = value
        return(result)


#################################################################
#
# PWM on pin 18
#
#################################################################
class AnalogOutputGPIO():
    def __init__(self, gpiobus, circuit, pin=18, frequency=400, major_group=1, value=0, dev_id=0):
        self.alias = ""
        self.devtype = AO
        self.dev_id = dev_id
        self.bus = gpiobus
        self.circuit = circuit
        self.major_group = major_group
        self.pin = pin
        self.frequency = frequency
        self.value = value
        gpiobus.set_PWM_frequency(pin, frequency)
        gpiobus.set_PWM_range(pin, 1000)
        gpiobus.set_PWM_dutycycle(pin, self.__calc_value(value))

    def full(self):
        return {'dev': 'ao', 'circuit': self.circuit, 'value': self.value, 'frequency': self.frequency, 'glob_dev_id': self.dev_id}

    def simple(self):
        return {'dev': 'ao', 'circuit': self.circuit, 'value': self.value}

    def __calc_value(self, value):
        if value > 10.0:
            value = 10.0
        elif value < 0:
            value = 0.0
        if config.up_globals['version'] == "UniPi 1.0":
            return int(round((10 - value) * 100))
        else:
            return int(round(value * 100))

    async def set_value(self, value):
        value10 = self.__calc_value(value)
        result = pigpio._u2i((await self.bus.apigpio_command(pigpio._PI_CMD_PWM, self.pin, value10)))
        self.value = value
        devents.status(self)
        return result

    async def set(self, value=None, frequency=None, alias=None):
        result = None
        if not (frequency is None) and (frequency != self.frequency):
            # print int(frequency)
            result = pigpio._u2i((await self.bus.apigpio_command(pigpio._PI_CMD_PFS, self.pin, int(frequency))))
            self.frequency = frequency
            if not (value is None):
                result = await self.set_value(float(value))
            else:
                result = await self.set_value(self.value)
            devents.config(self)
            return result

        if not (value is None) and (value != self.value):
            result = await self.set_value(float(value))
        return result


#################################################################
#
# Digital Input
#
#################################################################

class Input():
    def __init__(self, gpiobus, circuit, pin, debounce=None, major_group=1, counter_mode='disabled', dev_id=0):
        self.alias = ""
        self.devtype = INPUT
        self.dev_id = dev_id
        self.bus = gpiobus
        self.circuit = circuit
        self.major_group = major_group
        self.pin = pin
        self.mask = 1 << pin
        self._debounce = 0 if not debounce else debounce / 1000.0  # millisecs
        self.value = None
        self.__value = None
        self.pending = None
        self.tick = 0
        if counter_mode in ["rising", "falling", "disabled"]:
            self.value = 0
            self.counter_mode = counter_mode
        else:
            self.counter_mode = 'disabled'
            logger.debug('DI%s: counter_mode must be one of: rising, falling or disabled. Counting is disabled!', self.circuit)
        gpiobus.set_pull_up_down(pin, pigpio.PUD_UP)
        gpiobus.register_input(self)

    @property
    def debounce(self):
        return int(self._debounce * 1000)

    @property
    def bitvalue(self):
        return self.__value

    def full(self):
        return {'dev': 'input', 'circuit': self.circuit, 'value': self.value,
                'bitvalue' : self.__value,
                'time': self.tick, 'debounce': self.debounce,
                'counter_mode': self.counter_mode == 'rising' or self.counter_mode == 'falling',
                'glob_dev_id': self.dev_id}

    def simple(self):
        return {'dev': 'input', 'circuit': self.circuit, 'value': self.value,
                'counter_mode': self.counter_mode == 'rising' or self.counter_mode == 'falling'}


    def _cb_set_value(self, value, tick, seq):

        def debcallback():
            self.pending = None
            self.pulse_us = tick - self.tick
            self.__value = value
            self.tick = tick
            if (self.counter_mode == 'rising') and (value == 1):
                self.value += 1
            elif (self.counter_mode == 'falling') and (value == 0):
                self.value += 1
            elif self.counter_mode == 'disabled':
                self.value = value
            devents.status(self)
            #print("Input-%d = %d  %d" %(self.circuit,self.value, self.pulse_us))

        value = int(not bool(value))  # normalize value and invert it - 0 = led on unipi board is off, 1 = led is shinning
        if self._debounce:
            if self.pending:
                self.bus.mainloop.remove_timeout(self.pending)
                self.pending = None

            if value != self.__value:
                self.pending = self.bus.mainloop.add_timeout(datetime.timedelta(seconds=self._debounce), debcallback)
            return

        self.__value = value
        self.tick = tick
        if self.counter_mode == 'rising' and value == 1:
            self.value += 1
        elif self.counter_mode == 'falling' and value == 0:
            self.value += 1
        elif self.counter_mode == 'disabled':
            self.value = value
        devents.status(self)

    async def set(self, debounce=None, counter=None, counter_mode=None, alias=None):
        if (counter_mode is not None and counter_mode != self.counter_mode and counter_mode in ["rising", "falling", "disabled"]):
            self.counter_mode = counter_mode
        if not (debounce is None):
            if not debounce:
                self._debounce = 0
            else:
                self._debounce = float(debounce) / 1000.0  #milisecs
            devents.config(self)
        if not (counter is None):
            if self.counter_mode != 'disabled':
                self.value = counter
                devents.status(self)


    def get(self):
        """ Returns ( value, debounce )
              current on/off value is taken from last value without reading it from hardware
        """
        return (self.value, self.debounce)

    def get_value(self):
        """ Returns value
              current on/off value is taken from last value without reading it from hardware
        """
        return self.value


class DS2408_pio(object):
    def __init__(self, circuit, ds2408, pin, major_group=1, dev_id=0):
        self.alias = ""
        self.devtype = SENSOR
        self.circuit = circuit
        self.dev_id = dev_id
        self.major_group = major_group
        self.ds2408 = ds2408
        self.pin = pin
        self.value = None
        self.ds2408.register_pio(self)

    def full(self):
        return None

    def simple(self):
        pass

    async def set(self, value):
        pass

    def get_value(self):
        """ Returns value
              current on/off value is taken from last value without reading it from hardware
        """
        return self.value

    def get(self):
        return self.get_value()


    async def set_value(self, value):
        #value = int(not value)
        if self.value != value:
            self.value = value
            devents.status(self)


class DS2408_input(DS2408_pio):
    def full(self):
        return {'dev': 'input', 'circuit': self.circuit, 'value': self.value,
                'time': 0, 'debounce': 0, 'glob_dev_id': self.dev_id}

    def simple(self):
        return {'dev': 'input', 'circuit': self.circuit, 'value': self.value}

class DS2408_relay(DS2408_pio):
    pending_id = 0

    def full(self):
        return {'dev': 'relay', 'circuit': self.circuit, 'value': self.value, 'pending': self.pending_id != 0, 'glob_dev_id': self.dev_id}

    def simple(self):
        return {'dev': 'relay', 'circuit': self.circuit, 'value': self.value}

    async def set_state(self, value):
        await self.set(value)

    async def set(self, value=None, timeout=None):
        if value is None:
            raise Exception('Value must be specified')
        value = int(value)

        if not (timeout is None):
            timeout = float(timeout)

        self.ds2408.m_set_pio(self.circuit, (self.pin, value))

        if timeout is None:
            return 1 if self.value & value else 0

        def timercallback():
            self.pending_id = None
            self.ds2408.m_set_pio(self.circuit, (self.pin, int(not value)))

        self.pending_id = IOLoop.instance().add_timeout(
            datetime.timedelta(seconds=float(timeout)), timercallback)

        return 1 if self.value & value else 0
