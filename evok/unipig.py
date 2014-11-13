#!/usr/bin/python


import struct
import time
import datetime
import atexit

from tornado import gen
from tornado.ioloop import IOLoop
import pigpio
import devents

class Eprom(object):

    def __init__(self, i2cbus, circuit, address = 0x50):
        # running with blocking
        self.circuit = circuit
        self.i2cbus = i2cbus
        self.i2c = i2cbus.i2c_open(i2cbus.busid, address, 0)
        atexit.register(self.stop)

    def full(self):
        return {'dev':'ee','circuit':self.circuit}

    def stop(self):
        self.i2cbus.i2c_close(self.i2c)

    @gen.coroutine
    def write_byte(self, index, value):
        assert (index < 16 and index >= 0)
        with (yield self.i2cbus.iolock.acquire()):
            #write byte
            extents = [struct.pack("I", (value & 0xff))]
            result = yield self.i2cbus.apigpio_command_ext(
                                pigpio._PI_CMD_I2CWB,
                                self.i2c, index, 4, extents)
            pigpio._u2i(result) #check errors

    @gen.coroutine
    def read_byte(self, index):
        assert (index < 16 and index >= 0)
        with (yield self.i2cbus.iolock.acquire()):
            result = yield self.i2cbus.apigpio_command(
                           pigpio._PI_CMD_I2CRB, self.i2c, index)
            raise gen.Return(pigpio._u2i(result))
            


#################################################################
#
# Relays on MCP 23008
#
#################################################################

MCP23008_IODIR = 0x00  # direction 1=inp, 0=out
MCP23008_IPOL  = 0x01  # reversed input polarity.
MCP23008_GPPU  = 0x06  # pullup
MCP23008_GPIO  = 0x09  # input/output
MCP23008_OLAT  = 0x0A  # latch output status


class UnipiMcp(object):

    def __init__(self, i2cbus, circuit, address = 0x20):
        # running with blocking
        self.circuit = circuit
        self.i2cbus = i2cbus
        self.i2c = i2cbus.i2c_open(i2cbus.busid, address, 0)
        atexit.register(self.stop)
        i2cbus.i2c_write_byte_data(self.i2c, MCP23008_IODIR, 0x00)  # all output !
        #pi.i2c_write_byte_data(self.i2c, MCP23008_GPPU, 0x00)   # no pullup, not req on output
        self.relays = []
        self.value = i2cbus.i2c_read_byte_data(self.i2c, MCP23008_OLAT)

    def stop(self):
        self.i2cbus.i2c_close(self.i2c)

    def full(self):
        return {'dev':'mcp','circuit':self.circuit}

    def register_relay(self,relay):
        if not(relay in self.relays):
            self.relays.append(relay)

    @gen.coroutine
    def set_masked_value(self, mask, value):
        if value:
            byte_val = (self.value | mask) & 0xff
        else:
            byte_val = (self.value & ~mask) & 0xff

        with (yield self.i2cbus.iolock.acquire()):
            #write byte
            extents = [struct.pack("I", byte_val)]
            result = yield self.i2cbus.apigpio_command_ext(
                                pigpio._PI_CMD_I2CWB,
                                self.i2c, MCP23008_GPIO, 4, extents)
            pigpio._u2i(result) # check errors

            #read byte
            result = yield  self.i2cbus.apigpio_command(
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

    def __init__(self, circuit, mcp, pin):
        self.circuit = circuit
        self.mcp = mcp
        self.pin = pin
        self._mask = 1 << pin
        mcp.register_relay(self) 
        #self.logger.debug("Relay %d initialized on MCP", self.circuit)

    def full(self):
        return {'dev':'relay', 'circuit':self.circuit, 'value': self.value, 'pending' : self.pending_id != 0}

    def simple(self):
        return {'dev':'relay', 'circuit':self.circuit, 'value': self.value}

    @property
    def value(self):
        return  1 if self.mcp.value & self._mask else 0   

    def get_state(self):
        """ Returns ( status, is_pending )
              current on/off status is taken from last mcp value without reading it from hardware
              is_pending is Boolean
        """
        return (self.value, self.pending_id != 0)
        
    @gen.coroutine
    def set_state(self, value):
        """ Sets new on/off status. Disable pending timeouts
        """
        if self.pending_id: 
            IOLoop.instance().remove_timeout(self.pending_id)
            self.pending_id = None
        yield self.mcp.set_masked_value(self._mask, value)
        raise gen.Return(1 if self.mcp.value & self._mask else 0)

    @gen.coroutine
    def set(self, value=None, timeout=None):
        """ Sets new on/off status. Disable pending timeouts
        """
        if value is None: 
            raise Exception('Value must be specified')
        value = int(value)
        if not(timeout is None):
            timeout = float(timeout)

        yield self.mcp.set_masked_value(self._mask, value)

        if timeout is None:
            raise gen.Return(1 if self.mcp.value & self._mask else 0)
        
        def timercallback():
            self.pending_id = None
            self.mcp.set_masked_value(self._mask, not value)
            #global _lastt
            #t = IOLoop.instance().time()           
            #print "%s %s" % (t-_lastt,t)
            #_lastt = t

        self.pending_id = IOLoop.instance().add_timeout(
                            datetime.timedelta(seconds=float(timeout)),timercallback)
        raise gen.Return(1 if self.mcp.value & self._mask else 0)


#################################################################
#
# Analog Inputs on MCP 342x
#
#################################################################
BIT_MASKS=(
(0b11111111111,      0b100000000000,      1.0/240),   #12bit
(0b1111111111111,    0b10000000000000,    1.0/60),    #14bit 
(0b111111111111111,  0b1000000000000000,  1.0/15),    #16bit
(0b11111111111111111,0b100000000000000000,1.0/3.75)   #18bit
)

class UnipiMCP342x(object):
    """ 
        MCP342[128] single/multi channel A/D convertor
    """
    def __init__(self, i2cbus, circuit, address = 0x68):
        # running with blocking
        #self.__config = 0x1c | channel  # continuos operation, 18bit, gain=1
        self.circuit = circuit
        self.i2cbus = i2cbus
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
        return {'dev':'adchip','circuit':self.circuit}

    def calc_mode(self, channel, bits, gain, continuous):
        mode = 0
        if not (channel in range(4)) : raise Exception("Bad channel number")
        mode = channel << 5
        mode = mode | (bool(continuous) << 4) | ((not bool(continuous)) << 7) # from one-shoot must be bit7 set
        """ sample rate and resolution
            12 = 12 bit (240 SPS max)  3.5 cifry
            14 = 14 bit (60 SPS max)   4 cifry
            16 = 16 bit (15 SPS max)   5 cifer 
            18 = 18 bit (3.75 SPS max) 5.5 cifry
        """
        if not (bits in (12,14,16,18)) : raise Exception("Bad bit resolution")
        mode = mode | ((bits - 12 )>>1) << 2
        """ PGA gain selection
                1 = 1x 
                2 = 2x
                4 = 4x
                8 = 8x
        """
        if not gain in (1,2,4,8): raise Exception("Bad gain value")
        bg = 3 if gain == 8 else 2 if gain == 4 else 1 if gain == 2 else 0
        mode = mode | bg
        return mode 

    def calc_waittime(self, bits):
        return BIT_MASKS[(bits - 12) >> 1][2]
        #if bits == 12: return 1.0/240
        #if bits == 14: return 1.0/60
        #if bits == 16: return 1.0/15
        #if bits == 18: return 1.0/3.75


    def register_channel(self,ai):
        if not(ai in self.channels):
            self.channels.append(ai)
        ai._mode = self.calc_mode(ai.channel,ai.bits,ai.gain, ai.continuous)
        ai._waittime = self.calc_waittime(ai.bits)
        if ai.continuous: 
            self.continuous = True
            self.must_measure = True


    @gen.coroutine
    def measure_loop(self,mainloop):
        print("Entering measure loop")
        #mainloop = IOLoop.instance()
        try:
            next = None
            looptime = mainloop.time() 
            for channel in self.channels:
                channel._nextmeasure = looptime
                next = channel

            while True:
                looptime = mainloop.time() 
                if next:
                    if not self.continuous or self.must_measure:
                        # run measurement for channel                
                        yield self.measure(next)
                        yield gen.Task(mainloop.call_later,next._waittime)

                    # try to read value 
                    if (yield self.read_raw()): 
                        ## set next time for current channel
                        channel = self.lastmeasure
                        if channel.interval > 0:
                            channel._nextmeasure = looptime+channel.interval
                        else:
                            channel._nextmeasure = 0 # single measurement only
                # calc waiting time
                next = None
                for channel in self.channels: 
                    if (channel._nextmeasure > 0) and ((next is None) or (channel._nextmeasure < next._nextmeasure)): 
                        next = channel
                      
                if next:
                    looptime = mainloop.time()
                    if looptime < next._nextmeasure:
                        yield gen.Task(mainloop.call_at,next._nextmeasure)
                else:
                    yield gen.Task(mainloop.call_later,1)

        except Exception, E:
            print("%s" % str(E))

                
    @gen.coroutine
    def measure(self, ai):
        self.lastmeasure = ai
        self.continuous = ai.continuous
        with (yield self.i2cbus.iolock.acquire()):
            yield self.i2cbus.apigpio_command(pigpio._PI_CMD_I2CWS, self.i2c, ai._mode)
        self.must_measure = False

    @gen.coroutine
    def read_raw(self):
        # reads the raw value from the selected previously planned one-shot operation or continuos
        # requires correctly bits
        readlen = 4 if self.lastmeasure.bits == 18 else 3     # if bits=18 : 4 else: 3
        with (yield self.i2cbus.iolock.acquire()):
            bytes = pigpio.u2i((yield self.i2cbus.apigpio_command(pigpio._PI_CMD_I2CRD, self.i2c, readlen)))
            if bytes <= 0: return
            data = yield self.i2cbus.arxbuf(bytes)
 
        status = data[readlen -1]
        if status & 0x80: 
            print("Converting in progress")
            return # converting in progress
        if (self.lastmeasure._mode & 0x7f) != (status & 0x7f): 
            print("Status unexpected")
            return # something is bad

        value = 0
        for i in range(readlen-1): value = (value << 8) | data[i]  # join bytes into number
        #print("readRaw end %s %x" %(value,status))
        bits = (status & 0x0c) >> 2 
        sign = BIT_MASKS[bits][1] & value
        value &= BIT_MASKS[bits][0]
        if sign : value = -value
        self.lastmeasure._set_voltage(2.048/BIT_MASKS[bits][0] * value)
        raise gen.Return(True)


class AnalogInput():

    def __init__(self, circuit, mcp,  channel, bits=18, gain=1, continuous=False, interval=5.0, correction = 5.0):
        self.circuit = circuit
        self.mcp = mcp
        self.channel = channel
        self.conf = False
        self.bits = bits
        self.gain = gain
        self.continuous = continuous
        self.interval = interval
        #self.correction = 5.51681777
        self.correction = correction
        self.value = None
        self.mtime = None
        mcp.register_channel(self)
        self.koef = self.correction / self.gain

    @property    # docasne!!
    def voltage(self):
        return self.value

    def full(self):
        return {'dev':'ai','circuit':self.circuit,'value':self.value,
            'time':self.mtime, 'interval':self.interval, 'bits':self.bits, 'gain': self.gain}

    def simple(self):
        return {'dev':'ai','circuit':self.circuit,'value':self.value}

    def _set_voltage(self, raw_value):
        if raw_value < 0: raw_value = 0   #value = - (value & self.mask)
        self.value = raw_value * self.koef
        #self.mtime = datetime.datetime.now()
        self.time = time.time()
        devents.status(self)
        #print("Voltage_%d=%s V" %(self.channel,self.voltage,))

    def get(self):
        return (self.value,"%s" % self.time)

    #@gen.coroutine
    def set(self, bits=None, gain=None, interval=None):
        if not(bits is None): self.bits = int(bits)
        if not(gain is None): 
            self.gain = int(gain)
            self.koef = self.correction / self.gain
        if not(interval is None): self.interval = float(interval)
        self.mcp.register_channel(self)
        devents.config(self)
        return 0

        
    #@gen.coroutine
    #def Measure(self):
    #    yield self.mcp.measure(self)



#################################################################
#
# PWM on pin 18
#
#################################################################

class AnalogOutput():

    def __init__(self, gpiobus, circuit, pin=18, frequency = 400, value = 10):
        self.bus = gpiobus
        self.circuit = circuit
        self.pin = pin
        self.frequency = frequency
        self.value = value
        gpiobus.set_PWM_frequency(pin, frequency)
        gpiobus.set_PWM_range(pin, 1000)
        gpiobus.set_PWM_dutycycle(pin,int(round((10-value)*100)))

    def full(self):
        return {'dev':'ao','circuit':self.circuit,'value':self.value,'frequency':self.frequency}

    def simple(self):
        return {'dev':'ao','circuit':self.circuit,'value':self.value}

    @gen.coroutine    
    def set_value(self, value):
        if value > 10.0: value = 10.0
        elif value < 0 : value = 0.0
        value10 = int(round((10-value)*100))
        result = pigpio._u2i((yield self.bus.apigpio_command( pigpio._PI_CMD_PWM, self.pin, value10)))
        self.value = value
        devents.status(self)
        raise gen.Return(result)
        
    @gen.coroutine    
    def set(self, value=None, frequency=None):
        result = None
        if not(frequency is None) and (frequency != self.frequency):
            print int(frequency)
            result = pigpio._u2i((yield self.bus.apigpio_command( pigpio._PI_CMD_PFS, self.pin, int(frequency))))
            self.frequency = frequency
            if not(value is None):        
                result = yield self.set_value(float(value))
            else:
                result = yield self.set_value(self.value)
            devents.config(self)
            raise gen.Return(result)

        if not(value is None) and (value != self.value):
            result = yield self.set_value(float(value))
        raise gen.Return(result)

#################################################################
#
# Digital Input
#
#################################################################

class Input():

    def __init__(self, gpiobus, circuit, pin, debounce=None):
        self.bus = gpiobus
        self.circuit = circuit
        self.pin = pin
        self.mask = 1 << pin
        self._debounce = 0 if not debounce else debounce / 1000.0 # milisecs
        self.value = None
        self.pending = None
        self.tick = 0
        gpiobus.set_pull_up_down(pin, pigpio.PUD_UP)
        gpiobus.register_input(self)

    @property
    def debounce(self):
        return int(self._debounce*1000)

    def full(self):
        return {'dev':'input','circuit':self.circuit,'value':self.value,
            'time':self.tick, 'debounce':self.debounce}

    def simple(self):
        return {'dev':'input','circuit':self.circuit,'value':self.value}


    def _cb_set_value(self, value, tick, seq):

        def debcallback():
                self.pending = None
                self.value = value
                self.pulse_us = tick - self.tick
                self.tick = tick
                devents.status(self)
                #print("Input-%d = %d  %d" %(self.circuit,self.value, self.pulse_us))

        value = int(not bool(value)) # normalize value and invert it - 0 = led on unipi board is off, 1 = led is shinning 
        if self._debounce:
            if self.pending: 
                self.bus.mainloop.remove_timeout(self.pending)
                #IOLoop.instance().remove_timeout(self.pending)
                self.pending = None

            if value != self.value:
                self.pending = self.bus.mainloop.add_timeout(datetime.timedelta(seconds=self._debounce),debcallback)
                #self.pending = IOLoop.instance().add_timeout(datetime.timedelta(seconds=self._debounce),debcallback)
            return

        self.value = value
        #print("Input-%d = %d  %d" %(self.circuit,self.value, tick - self.tick))
        self.tick = tick
        devents.status(self)
        
    #@gen.coroutine    
    def set(self, debounce = None):
        if not(debounce is None):
            if not debounce:
                self._debounce = 0
            else: 
                self._debounce = float(debounce) / 1000.0 #milisecs
            devents.config(self)

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


