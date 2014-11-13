#import logging
#import threading
import multiprocessing
import os
import time
import ow
import devents
#import math
#import datetime

MAX_LOSTINTERVAL=300 # 5minut

OWCMD_INTERVAL = 1
OWCMD_SCAN = 2
OWCMD_SCAN_INTERVAL = 3
OWCMD_DEFAULT_INTERVAL = 4

import fcntl
def set_non_blocking(fd):
    flags = fcntl.fcntl(fd, fcntl.F_GETFL)
    fcntl.fcntl(fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)


class MySensor:
    def __init__(self, addr, typ, bus, interval=None, dynamic = True, circuit = None, in_subprocess = False):
        self.type = typ
        self.circuit = circuit if circuit != None else addr
        self.address = addr
        self.interval = bus.interval if interval is None else interval # seconds
        self.dynamic = dynamic            # dynamically change interval #TODO
        self.last_value = None
        self.value = None
        self.lost = False
        self.time = 0
        self.readtime = 0
        self.sens = None
        if in_subprocess:
            self.__bus = bus   #can't pickle, must be reset/set  by pickeling/unpicklgin
        bus.register_sensor(self)


    def get_value(self):
        return self.value

    def get(self):
        return (self.value, self.lost, self.time, self.interval)

    def set(self, interval=None):
        if not(interval is None):   
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
            for old,new in zip(self.value,value): 
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
        #print "Temperature %s is %s" % (self.circuit,self.value)


    def read_val_from_sens(self, sens):
        raise NotImplementedError("Please Implement this method")

    def calc_interval(self):
        if self.lost:
            self.lostinterval *= 2
            if self.lostinterval > MAX_LOSTINTERVAL: self.lostinterval = MAX_LOSTINTERVAL 
            return self.lostinterval
        if self.dynamic:
            ##TODO
            pass
        return self.interval

    def set_lost(self):
        if self.lost: return
        self.lost = True
        self.lostinterval = self.interval


class DS18B20(MySensor): # thermometer

    def full(self):
        return {'dev':'temp', 'circuit':self.circuit, 'address':self.address, 
                'value':self.value, 'lost':self.lost, 'time':self.time, 'interval':self.interval}

    def simple(self):
        return {'dev':'temp','circuit':self.circuit,'temp':self.value,'lost':self.lost}
    
    def read_val_from_sens(self, sens):
        #try:
            self.value = round(float(sens.temperature)*2,1)/2  # 4 bits for frac part of number
        #except:
        #    pass
        #print self.value


class DS2438(MySensor): # humidity + thermometer

    def full(self):
        if not(type(self.value) is tuple): 
            self.value=(None,None)
        return {'dev':'humid','circuit':self.circuit,'value':self.value[0],
            'temp':self.value[1],'lost':self.lost,'time':self.time,'interval':self.interval}

    def simple(self):
        if not(type(self.value) is tuple): 
            self.value=(None,None)
        return {'dev':'temp','circuit':self.circuit,'humid':self.value[0],'lost':self.lost}

    def read_val_from_sens(self, sens):
        self.value = (sens.humidity.strip(), send.temperature.strip())


def MySensorFabric(address, typ, bus, interval=None, dynamic = True, circuit = None):

    if (typ == 'DS18B20')or(typ == 'DS18S20'):
        return DS18B20(address, typ, bus, interval=interval, circuit=circuit)
    elif (sens.type == 'DS2438'):
        return DS2438(address, typ, bus, interval=interval, circuit=circuit)
    else: return None
    

    
class OwBusDriver(multiprocessing.Process):

    def __init__(self, circuit, taskPipe, resultPipe, interval=60, scan_interval=300, bus='/dev/i2c-1'):
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
        self.register_in_caller = lambda x: None # pro registraci, zatim prazdna funkce 
        ow.init(bus)
#        self.logger = logging.getLogger(Globals.APP_NAME)
#        self.logger.debug("owclient initialized")


    def full(self):
        return {'dev':'owbus','circuit':self.circuit,'bus':self.bus}


    def set(self, scan_interval = None, do_scan = False, interval = None):
        chg = False
        if not(interval is None):   
            if interval != self.interval:
                self.taskWr.send((OWCMD_DEFAULT_INTERVAL, 0, interval))
                self.interval = interval
                chg = True
        if not(scan_interval is None):   
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
    def check_resultq(self, r_pipe, event): #, register_in_caller):
        obj = self.resultRd.recv()
        if isinstance(obj,MySensor):
            self.register_sensor(obj)
            self.register_in_caller(obj)
            obj.__bus = self
            #Devices.register_device(5,obj)
            print "new sensor " + str(obj.circuit)
        elif type(obj) is tuple:
            # obj[0] - circuit/address of sensor
            # obj[1] - Boolean(True) -> Lost
            #        - value
            #        - (value,value..)
            circuit = obj[0]
            mysensor = next(x for x in self.mysensors if x.circuit == circuit)
            if mysensor: mysensor._set_value(obj[1])
            #print "Temperature %s is %s" % (obj[0],obj[1])


    ######################################
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
                except Exception:
                    #if not found, create new one
                    mysensor = MySensorFabric(address, sens.type, self)
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

          

    def run(self):
        """ Main loop 
            Every scan_interval initiate bus scanning
            Peridocally scan 1wire sensors, else sleep
        """    
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
                    self.resultQ.send((mysensor.circuit,mysensor.value))
            except (ow.exUnknownSensor, AttributeError):
                if not mysensor.lost:
                    mysensor.set_lost()
                    self.resultQ.send((mysensor.circuit,mysensor.lost))
            mysensor.time = t1 + mysensor.calc_interval()
            mysensor = min(self.mysensors, key=lambda x: x.time)
            t1 = time.time()
            if mysensor.time > t1:
                if self.taskQ.poll(mysensor.time - t1):
                    #commands from master
                    cmd = self.taskQ.recv()
                    self.do_command(cmd)

