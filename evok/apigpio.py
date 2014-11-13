#!/usr/bin/python

import os
import struct
import pigpio
import toro
from tornado.iostream import IOStream, PipeIOStream
from tornado import gen
from tornado.ioloop import IOLoop

pipe_name_i = '/dev/pigpio'
pipe_name_o = '/dev/pigout'
pipe_name_n = '/dev/pigpio%d'

class _PigBus(object,pigpio.pi):
    '''
        Common class for I2cBus and GpioBus
    '''
    def __init__(self,
                circuit,
                host = os.getenv("PIGPIO_ADDR", ''),
                port = os.getenv("PIGPIO_PORT", 8888)
                ):

        #super(PigBus,self).__init__(self,host, port)
        self.circuit = circuit
        pigpio.pi.__init__(self,host, port)
        self.iolock = toro.Lock()
        # dispose _notify thread
        self._notify.stop()
        self._notify = None

    def switch_to_async(self, mainloop):
        '''
        Switch from synchronous to async operations
        '''
        self.iostream = IOStream(self.sl.s)
        self.iostream._add_io_state(self.iostream.io_loop.WRITE) # nevim, zd je potreba

    @gen.coroutine
    def apigpio_command(self, cmd, p1, p2):
       """
       Runs a pigpio socket command.
       """
       yield self.iostream.write(struct.pack('IIII', cmd, p1, p2, 0))
       result = yield self.iostream.read_bytes(16)
       dummy, res = struct.unpack('12sI', result)
       raise gen.Return(res)

    @gen.coroutine
    def apigpio_command_ext(self, cmd, p1, p2, p3, extents):
       """
       Runs a pigpio socket command ext.
       """
       #ext = bytearray(struct.pack('IIII', cmd, p1, p2, p3))
       ext = struct.pack('IIII', cmd, p1, p2, p3)
       for x in extents:
          ext += x
          #if type(x) == type(""):
          #   ext.extend(pigpio._b(x))
          #else:
          #   ext.extend(x)
          
       yield self.iostream.write(ext)
       result = yield self.iostream.read_bytes(16)
       dummy, res = struct.unpack('12sI', result)   
       raise gen.Return(res)

    @gen.coroutine
    def arxbuf(self, count):
        """Returns count bytes from the command socket."""
        ext = yield self.iostream.read_bytes(count)
        ext = bytearray(ext)
        while len(ext) < count:
            rbytes = yield self.iostream.read_bytes(count - len(ext))
            ext.extend(rbytes)
        raise gen.Return(ext)


class I2cBus(_PigBus):

    def __init__(self, circuit = 1,
                host = os.getenv("PIGPIO_ADDR", ''),
                port = os.getenv("PIGPIO_PORT", 8888),
                busid = 1
                ):
        super(I2cBus, self).__init__(circuit, host, port)
        #_PigBus.__init__(self, circuit, host, port)
        self.busid = busid

    def full(self):
        return {'dev':'i2cbus','circuit':self.circuit,'busid':self.busid}


class GpioBus(_PigBus):

    def __init__(self, circuit = 0,
                host = os.getenv("PIGPIO_ADDR", ''),
                port = os.getenv("PIGPIO_PORT", 8888)
                ):
        super(GpioBus, self).__init__(circuit, host, port)
        self.inputs = {}
        self.notify_mask = 0
        self.notify_pig = self.notify_open()
        self.notify_handle = os.open(pipe_name_n % self.notify_pig, os.O_RDONLY)

    def full(self):
        return {'dev':'gpiobus','circuit':self.circuit}

    def stop(self):
        try: 
            os.close(self.notify_h) 
        except Exception: pass
        self.notify_close(self.notify_pig)

    def register_input(self, inp):
        self.inputs[inp.pin] = inp
        self.notify_mask |= inp.mask
        
    def switch_to_async(self, mainloop):
        self.mainloop = mainloop
        # read current status of gpio inputs
        self.bank1 = self.read_bank_1() & self.notify_mask
        for inp in self.inputs.values():
            try:
                inp._cb_set_value(self.bank1 & inp.mask,0,0)
            except Exception, E : print str(E)

        self.notify_begin(self.notify_pig, self.notify_mask)# | 1<<18)
        #print "%0x" % self.notify_mask
        _PigBus.switch_to_async(self, mainloop)
        self.notify = PipeIOStream(self.notify_handle)
        mainloop.add_handler(self.notify, self.notify_callback, IOLoop.READ) #+IOLoop.WRITE)

    #@gen.coroutine
    def notify_callback(self, fd, event):
        #PIPE_BUF=512
        #try:        
        #  bb = yield self.notify.read_bytes(PIPE_BUF,partial=True)
        #  print len(bb)
        #except Exception, E : print str(E)
        seq, flag, tick, level = struct.unpack('HHII', os.read(self.notify_handle,12))
        #seq, flag, tick, level = struct.unpack('HHII', (yield self.notify.read_bytes(12)))
        if flag & 0x20:
            # watchdog on pin
            pin = flag & 0x1f
            # ???
            return
        level &= self.notify_mask 
        changes = level ^ self.bank1
        #print "Change %08x %08x" % (changes, level)
        # check all changed input pins and set values
        for inp in filter(lambda inp: changes & inp.mask, self.inputs.values()):
                try:
                    inp._cb_set_value(level & inp.mask,tick,seq)
                except Exception, E : print str(E)
        self.bank1 = level
        return


