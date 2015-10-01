# import logging
#import threading
import multiprocessing
import os
import time
import ow
import devents
#import math
#import datetime
import signal
import apigpio

MAX_LOSTINTERVAL = 300  # 5minut

OWCMD_INTERVAL = 1
OWCMD_SCAN = 2
OWCMD_SCAN_INTERVAL = 3
OWCMD_DEFAULT_INTERVAL = 4
OWCMD_SET_PIO = 5
SUPPORTED_DEVICES = ["DS18S20", "DS18B20", "DS2438", "DS2408"]

import fcntl


def set_non_blocking(fd):
    flags = fcntl.fcntl(fd, fcntl.F_GETFL)
    fcntl.fcntl(fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

class MySensor(object):
    def __init__(self, addr, typ, bus, interval=None, dynamic=True, circuit=None, is_static=False):
        self.type = typ
        self.circuit = circuit if circuit != None else addr
        self.address = addr
        self.interval = bus.interval if interval is None else interval  # seconds
        self.is_dynamic_interval = dynamic  # dynamically change interval #TODO
        self.last_value = None
        self.value = None
        self.lost = False
        self.time = 0
        self.readtime = 0
        self.sens = None
        if is_static:
            self.__bus = bus  #can't pickle, must be reset/set  by pickeling/unpicklgin
        bus.register_sensor(self)

    def get_value(self):
        return self.value

    def get(self):
        return (self.value, self.lost, self.time, self.interval)

    def set(self, interval=None):
        if not (interval is None):
            self.__bus.taskWr.send((OWCMD_INTERVAL, self.circuit, interval))
            self.interval = interval
            devents.config(self)

    def _set_value(self, value):
        """ Called in master process after receiving result from subprocess
            to update values
            Invokes Events
        """
        if type(value) is bool:
            if not self.lost:
                self.lost = True
                devents.status(self)
        elif type(value) is tuple:
            self.lost = False
            if self.value is None:
                self.value = ()
                for i in range(len(value)):
                    self.value += (None,)
            for old, new in zip(self.value, value):
                if old != new:
                    self.value = value
                    self.time = time.time()
                    devents.status(self)
                    break
        else:
            self.lost = False
            self.time = time.time()
            if self.value != value:
                self.value = value
                devents.status(self)

    def read_val_from_sens(self, sens):
        raise NotImplementedError("Please Implement this method")

    def calc_interval(self):
        if self.lost:
            self.lostinterval *= 2
            if self.lostinterval > MAX_LOSTINTERVAL: self.lostinterval = MAX_LOSTINTERVAL
            return self.lostinterval
        if self.is_dynamic_interval:
            ##TODO
            pass
        return self.interval

    def set_lost(self):
        if self.lost: return
        self.lost = True
        self.lostinterval = self.interval

class DS18B20(MySensor):  # thermometer

    def full(self):
        return {'dev': 'temp', 'circuit': self.circuit, 'address': self.address,
                'value': self.value, 'lost': self.lost, 'time': self.time, 'interval': self.interval, 'typ': self.type}

    def simple(self):
        return {'dev': 'temp', 'circuit': self.circuit, 'value': self.value, 'lost': self.lost, 'typ': self.type}

    def read_val_from_sens(self, sens):
        new_val = float(sens.temperature)
        if not (new_val == 85.0 and abs(new_val - self.value) > 2):
            self.value = round(float(sens.temperature) * 2, 1) / 2  # 4 bits for frac part of number
        else:
            print "PoR detected! 85C"

# class DS2438(MySensor):  # vdd + vad + thermometer
#
#     def full(self):
#         if not (type(self.value) is tuple):
#             self.value = (None, None, None)
#         return {'dev': 'ds2438', 'circuit': self.circuit, 'vdd': self.value[0], 'vad': self.value[1],
#                 'temp': self.value[2], 'lost': self.lost, 'time': self.time, 'interval': self.interval, 'typ': self.type}
#
#     def simple(self):
#         if not (type(self.value) is tuple):
#             self.value = (None, None, None)
#         return {'dev': 'ds2438', 'circuit': self.circuit, 'vdd': self.value[0], 'vad': self.value[1],
#                 'temp': self.value[2], 'lost': self.lost, 'typ': self.type}
#
#     def read_val_from_sens(self, sens):
#         self.value = (sens.VDD, sens.VAD, sens.temperature)

class DS2408(MySensor):
    def __init__(self, addr, typ, bus, interval=None, is_dynamic_interval=True, circuit=None, is_static=False):
        self.type = typ
        self.circuit = circuit if circuit != None else addr
        self.address = addr
        self.interval = bus.interval if interval is None else interval  # seconds
        self.is_dynamic_interval = is_dynamic_interval  # dynamically change interval #TODO
        self.last_value = None
        self.value = None
        self.lost = False
        self.time = 0
        self.readtime = 0
        self.sens = None
        if is_static:
            self.__bus = bus  #can't pickle, must be reset/set  by pickeling/unpicklgin
        bus.register_sensor(self)
        self.pios = []

    def read_val_from_sens(self, sens):
        #actual values must be read from sensed_ALL, but writes to the GPIOs must be done in PIO_x(PIO_ALL)
        #pios_values = map(int, self.sens.sensed_ALL.split(','))
        pios_values = [int(not int(i)) for i in self.sens.sensed_ALL.split(',')]
        self.value = pios_values

    def full(self):
        return {'dev': '1wdevice', 'circuit': self.circuit, 'address': self.address, 'value': None, 'typ': self.type}

    def simple(self):
        return self.full()

    def m_set_pio(self, pio, value):
        self.__bus.taskWr.send((OWCMD_SET_PIO, self.circuit, value))

    def set_pio(self, pio, value):
        setattr(self.sens, 'PIO_'+repr(pio), str(value))

    def register_pio(self, pio):
        if not pio in self.pios:
            self.pios.append(pio)

    def _set_value(self, value):
        """ Called in master process after receiving result from subprocess
            to update values
            Invokes Events
        """
        if type(value) is bool:
            if not self.lost:
                self.lost = True
                devents.status(self)
        else:
            self.lost = False
            self.time = time.time()
            if self.value != value:
                self.value = value
                devents.status(self)
                #update DS_2408_pio object that are attached to this DS2408
                if type(value) is list:
                    pios_cnt = len(value)
                    for pio in self.pios:
                        if pio.pin < pios_cnt:
                            pio.set_value(value[pio.pin])

def MySensorFabric(address, typ, bus, interval=None, dynamic=True, circuit=None, is_static=False):
    if (typ == 'DS18B20') or (typ == 'DS18S20'):
        return DS18B20(address, typ, bus, interval=interval, circuit=circuit)
    # elif (typ == 'DS2438'):
    #     return DS2438(address, typ, bus, interval=interval, circuit=circuit)
    elif (typ == 'DS2408'):
        return DS2408(address, typ, bus, interval=interval, circuit=circuit, is_static=is_static)
    else:
        print "Unsupported 1wire device %s (%s) detected" % (typ, address)
        return None


class OwBusDriver(multiprocessing.Process):
    def __init__(self, circuit, taskPipe, resultPipe, interval=60, scan_interval=300, bus='--i2c=/dev/i2c-1:ALL'):
        multiprocessing.Process.__init__(self)
        self.circuit = circuit
        self.taskQ = taskPipe[0]
        self.taskWr = taskPipe[1]
        self.resultRd = resultPipe[0]
        self.resultQ = resultPipe[1]
        self.scan_interval = scan_interval
        self.interval = interval
        self.scanned = set()
        self.mysensors = list()
        self.bus = bus
        self.register_in_caller = lambda x: None  # pro registraci, zatim prazdna funkce
        # ow.init(bus)

    #        self.logger = logging.getLogger(Globals.APP_NAME)
    #        self.logger.debug("owclient initialized")


    def full(self):
        return {'dev': 'owbus', 'circuit': self.circuit, 'bus': self.bus}

    def list(self):
        list = dict()
        for dev in SUPPORTED_DEVICES:
            temp_list = [sens.address for sens in self.mysensors if sens.type == dev]
            list[dev] = temp_list
        return list

    def set(self, scan_interval=None, do_scan=False, interval=None):
        chg = False
        if not (interval is None):
            if interval != self.interval:
                self.taskWr.send((OWCMD_DEFAULT_INTERVAL, 0, interval))
                self.interval = interval
                chg = True
        if not (scan_interval is None):
            if scan_interval != self.scan_interval:
                self.taskWr.send((OWCMD_SCAN_INTERVAL, 0, scan_interval))
                self.scan_interval = scan_interval
                chg = True
        if do_scan:
            self.taskWr.send((OWCMD_SCAN, 0, 0))

        if chg:
            devents.config(self)

    def register_sensor(self, mysensor):
        self.mysensors.append(mysensor)

    #use in main process, callback for tornado ioloop = Consumer of results
    def check_resultq(self, r_pipe, event):  #, register_in_caller):
        obj = self.resultRd.recv()
        if isinstance(obj, MySensor):
            self.register_sensor(obj)
            self.register_in_caller(obj)
            obj.__bus = self
            #Devices.register_device(5,obj)
            print "New sensor " + str(obj.type) + " - " +str(obj.circuit)
        elif type(obj) is tuple:
            # obj[0] - circuit/address of sensor
            # obj[1] - Boolean(True) -> Lost
            #        - value
            #        - (value,value..)
            circuit = obj[0]
            mysensor = next(x for x in self.mysensors if x.circuit == circuit)
            if mysensor: mysensor._set_value(obj[1])
            #print "Temperature %s is %s" % (obj[0],obj[1])


    # ####################################w.init(b#
    # this part is running used in subprocess

    def do_scan(self):
        """ Initiate 1wire bus scanning, 
            check existence in self.scanned
            join sens with mysensor
        """
        for sens in ow.Sensor("/uncached").sensors():
            if not (sens in self.scanned):
                address = sens.address
                try:
                    # find sensor in list self.mysenors by address
                    mysensor = next(x for x in self.mysensors if x.address == address)
                    #print "Sensor found " + str(mysensor.circuit)
                except Exception:
                    #if not found, create new one
                    mysensor = MySensorFabric(address, sens.type, self, interval=15)
                    if mysensor:
                        # notify master process about new sensor
                        self.resultQ.send(mysensor)
                #mysensor = self.find_mysensor(sens)
                if mysensor:
                    mysensor.sens = sens
                    self.scanned.add(sens)

    def do_command(self, cmd):
        command, circuit, value = cmd
        #print "cmd %s" % command
        if command == OWCMD_INTERVAL:
            mysensor = next(x for x in self.mysensors if x.circuit == circuit)
            if mysensor:
                mysensor.interval = value
        elif command == OWCMD_SCAN:
            self.do_scan()
        elif command == OWCMD_SCAN_INTERVAL:
            self.scan_interval = value
        elif command == OWCMD_DEFAULT_INTERVAL:
            self.interval = value
        elif command == OWCMD_SET_PIO:
            mysensor = next(x for x in self.mysensors if x.circuit == circuit)
            if mysensor:
                pin, value = value
                mysensor.set_pio(pin, int(value))


    def run(self):
        """ Main loop 
            Every scan_interval initiate bus scanning
            Peridocally scan 1wire sensors, else sleep
        """
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        # apigpio.mainprog = 0
        # for i in range(25):
        # try:
        # if not (i in (0,1,2,self.taskQ.fileno(), self.resultQ.fileno())):
        #         os.close(i)
        #   except Exception, E:
        #     print str(E)
        ow.init(self.bus)
        print "Entering 1wire loop"
        self.do_scan()
        while len(self.mysensors) == 0:
            if self.taskQ.poll(20):
                #commands from master
                cmd = self.taskQ.recv()
                self.do_command(cmd)
            self.do_scan()

        scan_time = time.time() + self.scan_interval
        mysensor = min(self.mysensors, key=lambda x: x.time)
        while True:
            t1 = time.time()
            #if t1 <= scan_time: 
            if t1 >= scan_time:
                self.do_scan()
                t1 = time.time()
                scan_time = t1 + self.scan_interval
            try:
                mysensor.read_val_from_sens(mysensor.sens)
                mysensor.lost = False
                mysensor.readtime = t1
                if self.resultQ:
                    # send measurement into result queue
                    self.resultQ.send((mysensor.circuit, mysensor.value))
            except (ow.exUnknownSensor, AttributeError):
                if not mysensor.lost:
                    mysensor.set_lost()
                    self.resultQ.send((mysensor.circuit, mysensor.lost))
            mysensor.time = t1 + mysensor.calc_interval()
            mysensor = min(self.mysensors, key=lambda x: x.time)
            t1 = time.time()
            if mysensor.time > t1:
                if self.taskQ.poll(mysensor.time - t1):
                    #commands from master
                    cmd = self.taskQ.recv()
                    self.do_command(cmd)

