import multiprocessing
import os
import time
import onewire as ow
import signal
import string
from tornado.ioloop import IOLoop
import devents
import devices
from log import *

from pymodbus.client.sync import ModbusTcpClient as ModbusClient
from pymodbus.exceptions import ConnectionException

MAX_LOSTINTERVAL = 300  # 5 minutes

OWCMD_INTERVAL = 1
OWCMD_SCAN = 2
OWCMD_SCAN_INTERVAL = 3
OWCMD_DEFAULT_INTERVAL = 4
OWCMD_SET_PIO = 5
OWCMD_RESET_MASTER = 6
SUPPORTED_DEVICES = ["DS18S20", "DS18B20", "DS2438", "DS2408", "DS2413"]

import fcntl

def set_non_blocking(fd):
    flags = fcntl.fcntl(fd, fcntl.F_GETFL)
    fcntl.fcntl(fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

class MySensor(object):
    def __init__(self, addr, typ, bus, interval=None, dynamic=True, circuit=None, major_group=1, is_static=False):
        self.alias = ""
        self.devtype = devices.SENSOR
        self.type = typ
        self.circuit = circuit if circuit != None else addr
        self.major_group = major_group
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
            self.__bus = bus  #can't pickle, must be reset/set by pickling/un-pickling
        bus.register_sensor(self)

    def get_value(self):
        return self.value

    def get(self):
        return (self.value, self.lost, self.time, self.interval)

    def set(self, interval=None, alias=None):

        if alias is not None:
            if devices.Devices.add_alias(alias, self, file_update=True):
                self.alias = alias

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

    def _set_interval(self, interval):
        self.interval = interval

    def read_val_from_sens(self, sens):
        raise NotImplementedError("Please Implement this method")

    def calc_interval(self):
        if self.lost: # Sensor is inactive (disconnected)
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
        ret = {'dev': 'temp',
                'circuit': self.circuit,
                'address': self.address,
                'value': self.value,
                'lost': self.lost,
                'time': self.time,
                'interval': self.interval,
                'typ': self.type}

        if self.alias != '':
            ret['alias'] = self.alias

        return ret


    def simple(self):
        return {'dev': 'temp',
                'circuit': self.circuit,
                'value': self.value,
                'lost': self.lost,
                'typ': self.type}

    def read_val_from_sens(self, sens):
        new_val = float(sens.temperature)
        if not (new_val == 85.0 and abs(new_val - self.value) > 2):
            self.value = round(float(sens.temperature) * 2, 1) / 2  # 4 bits for frac part of number
        else:
            logger.debug("PoR detected! 85C")

class DS2438(MySensor):  # vdd + vad + thermometer

    def full(self):
        if not (type(self.value) is tuple):
            self.value = (None, None, None)
        ret = {'dev': '1wdevice',
                'circuit': self.circuit,
                'humidity': (((((float(self.value[1]) / float(self.value[0])) - 0.1515)) / 0.00636) / (1.0546 - 0.00216 * float(self.value[2]))),
                'vdd': self.value[0],
                'vad': self.value[1],
                'temp': self.value[2],
                'vis': self.value[3],
                'lost': self.lost,
                'time': self.time,
                'interval': self.interval,
                'typ': self.type}

        if self.alias != '':
            ret['alias'] = self.alias

        return ret


    def simple(self):
        if not (type(self.value) is tuple):
            self.value = (None, None, None)
        return {'dev': '1wdevice',
                'circuit': self.circuit,
                'vdd': self.value[0],
                'vad': self.value[1],
                'temp': self.value[2],
                'vis': self.value[3],
                'lost': self.lost,
                'typ': self.type}

    def read_val_from_sens(self, sens):
        self.value = (sens.VDD, sens.VAD, sens.temperature, sens.vis)


class DS2408(MySensor):
    def __init__(self, addr, typ, bus, interval=None, is_dynamic_interval=True, circuit=None, major_group=1, is_static=False):
        self.type = typ
        self.circuit = circuit if circuit != None else addr
        self.address = addr
        self.major_group = major_group
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
        ret = {'dev': '1wdevice',
                'circuit': self.circuit,
                'address': self.address,
                'value': None,
                'typ': self.type}

        if self.alias != '':
            ret['alias'] = self.alias

        return ret


    def simple(self):
        return self.full()

    def m_set_pio(self, pio, value):
        self.__bus.taskWr.send((OWCMD_SET_PIO, self.circuit, value))

    def set_pio(self, pio, value):
        if self.type == 'DS2408':
            setattr(self.sens, 'PIO_'+repr(pio), str(value))
        elif self.type == 'DS2406' or self.type == 'DS2413':
            pio_alpha = dict(zip(range(0, 26), string.ascii_uppercase))
            setattr(self.sens, 'PIO_'+pio_alpha[pio], str(value))

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


def MySensorFabric(address, typ, bus, interval=None, dynamic=True, circuit=None, major_group = 1, is_static=False):
    if (typ == 'DS18B20') or (typ == 'DS18S20'):
        return DS18B20(address, typ, bus, interval=interval, circuit=circuit)
    elif (typ == 'DS2438'):
        return DS2438(address, typ, bus, interval=interval, circuit=circuit)
    elif (typ == 'DS2408') or (typ == 'DS2406') or (typ == 'DS2413'):
        return DS2408(address, typ, bus, interval=interval, circuit=circuit, is_static=is_static)
    else:
        logger.debug("Unsupported 1wire device %s (%s) detected", typ, address)
        return None


class OwBusDriver(multiprocessing.Process):
    def __init__(self, circuit, taskPipe, resultPipe, interval=60, scan_interval=300, major_group=1, bus='--i2c=/dev/i2c-1:ALL'):
        multiprocessing.Process.__init__(self)
        self.devtype = devices.OWBUS
        self.circuit = circuit
        self.taskQ = taskPipe[0]
        self.taskWr = taskPipe[1]
        self.resultRd = resultPipe[0]
        self.resultQ = resultPipe[1]
        self.major_group = major_group
        self.scan_interval = scan_interval
        self.interval = interval
        self.scanned = set()
        self.mysensors = list()
        self.bus = bus
        self.cycle_cnt = 0
        self.register_in_caller = lambda x: None  # pro registraci, zatim prazdna funkce
        # ow.init(bus)
        self.ow = None


    def full(self):
        return {'dev': 'owbus',
                'circuit': self.circuit,
                'bus': self.bus,
                'scan_interval': self.scan_interval,
                'interval': self.interval,
                'do_scan' : False,
                'do_reset' : False}

    def list(self):
        list = dict()
        for dev in SUPPORTED_DEVICES:
            temp_list = [sens.address for sens in self.mysensors if sens.type == dev]
            list[dev] = temp_list
        return list


    def switch_to_async(self, mainLoop):
        self.daemon = True
        self.start()
        self.register_in_caller = lambda d: devices.Devices.register_device(devices.SENSOR, d)
        set_non_blocking(self.resultRd)
        mainLoop.add_handler(self.resultRd, self.check_resultq, IOLoop.READ)


    def set(self, scan_interval=None, do_scan=False, interval=None, circuit=None, do_reset=None):
        chg = False

        if do_reset is not None:
            self.taskWr.send((OWCMD_RESET_MASTER, 0, 0))
        if not (interval is None):
            if interval != self.interval:
                self.taskWr.send((OWCMD_INTERVAL, 0 if circuit is None else circuit, interval))
                if circuit is None: self.interval = interval
                chg = True
        if not (scan_interval is None):
            if scan_interval != self.scan_interval:
                self.taskWr.send((OWCMD_SCAN_INTERVAL, 0, scan_interval))
                self.scan_interval = scan_interval
                chg = True
        if do_scan:
            logger.debug("Invoked scan of 1W bus")
            self.taskWr.send((OWCMD_SCAN, 0, 0))

        if chg:
            devents.config(self)

        return(self.full())

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
            logger.debug("New sensor %s - %s", str(obj.type),str(obj.circuit))
        elif type(obj) is tuple:
            # obj[0] - circuit/address of sensor
            # obj[1] - Boolean(True) -> Lost
            #        - value
            #        - (value,value..)
            circuit = obj[0]
            mysensor = next(x for x in self.mysensors if x.circuit == circuit)

            if len(obj) == 3 and mysensor: # Interval is also updated
                mysensor._set_interval(obj[2])
            elif mysensor:
                mysensor._set_value(obj[1]) # Set value - updates mysensor.time with current time.


    # ####################################w.init(b#
    # this part is running used in subprocess
    def do_scan(self, invoked_async = False):
        """ Initiate 1wire bus scanning,
            check existence in self.scanned
            join sens with mysensor
        """
        tmp_buf = set()
        self.cycle_cnt += 1
        for sens in self.ow.find(): # For every sensor connected to the bus

            sens.address = str(sens.address)[:16]

            tmp_buf.add(sens.address)

            if not (sens.address in self.scanned): # The sensor is scanned for a first time
                address = sens.address
                try:
                    # find sensor in list self.mysenors by address - statically added in the config file
                    mysensor = next(x for x in self.mysensors if x.address == address)
                    logger.info("Sensor found " + str(mysensor.circuit))
                except Exception:
                    #if not found, create new one
                    mysensor = MySensorFabric(address, sens.type, self, self.interval)
                    if mysensor:
                        # notify master process about new sensor - sensor is appended to mysensors HERE
                        self.resultQ.send(mysensor)
                #mysensor = self.find_mysensor(sens)
                if mysensor:
                    mysensor.sens = sens
                    self.scanned.add(sens.address)

            elif invoked_async is True: # Reset planned scan time if invoked async
                mysensor = next(x for x in self.mysensors if x.address == str(sens.address))
                if (mysensor) and (mysensor.lost is True):
                    mysensor.time = 0

        tmp_all = tmp_buf | self.scanned # Create union with all the sensors - both active and inactive
        inactives = (tmp_all - tmp_buf) # Get incative ones as difference
        for sens in inactives: # All inactive sensors set as "lost"
            mysensor = next(x for x in self.mysensors if x.address == sens)
            if not mysensor.lost:
                mysensor.set_lost()
                self.resultQ.send((mysensor.circuit, mysensor.lost))

    def do_reset(self):
        logger.debug("Invoked reset of 1W master")
        try:
            with ModbusClient('127.0.0.1') as client: # Send request to local unipi-tcp in simple sync mode
                ret = client.write_coil(1001, True, unit=1)
                time.sleep(0.2)
                ret = client.write_coil(1001, False, unit=1)
            #ow.finish()
            #time.sleep(0.05)
            #ow.init(self.bus)
        except (ConnectionException):
            pass

    # This routine is invoked from the subprocess
    def do_command(self, cmd):
        command, circuit, value = cmd
        if command == OWCMD_INTERVAL:
            if circuit == 0: # Global interval change - for all connected sensors
                t1 = time.time()
                for mysensor in self.mysensors: # Global change - for all sensors
                    mysensor.interval = value
                    mysensor.time = t1 + mysensor.calc_interval()
                    self.resultQ.send((mysensor.circuit, mysensor.value, value))
            else: # Just for single sensor
                    if len(self.mysensors) > 0:
                        mysensor = next(x for x in self.mysensors if x.circuit == circuit)
                        if mysensor:
                            mysensor.interval = value
                            mysensor.time = time.time() + mysensor.calc_interval()
                            self.resultQ.send((mysensor.circuit, mysensor.value, value))

        elif command == OWCMD_SCAN:
            self.do_scan(invoked_async=True)
        elif command == OWCMD_SCAN_INTERVAL:
            self.scan_interval = value
        elif command == OWCMD_DEFAULT_INTERVAL:
            self.interval = value
        elif command == OWCMD_RESET_MASTER:
            self.do_reset()

        elif command == OWCMD_SET_PIO:
            mysensor = next(x for x in self.mysensors if x.circuit == circuit)
            if mysensor:
                pin, value = value
                mysensor.set_pio(pin, int(value))

    def run(self):
        """ Main loop of the subprocess
            Every scan_interval initiate bus scanning
            Peridocally scan 1wire sensors, else sleep
        """
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        #ow.init(self.bus) old
        self.ow = ow.Onewire(self.bus)
        logger.info("Entering OWW loop with PID {}".format(os.getpid()))

        while True: # If no sensors are in cache
            if self.scan_interval != 0:
                self.do_scan() # Do initial scan
            if len(self.mysensors) > 0:
                break

            if self.taskQ.poll(20): # Wait 20 second for CMD from main loop
                #CMD from main loop
                cmd = self.taskQ.recv()
                self.do_command(cmd)

        mysensor = min(self.mysensors, key=lambda x: x.time) # Find sensor with min time (all se to 0 as default)

        scan_time = time.time() + self.scan_interval # Plan next scan


        while True: # "Main loop"

            if self.scan_interval != 0:
                t1 = time.time()
                if t1 >= scan_time: # Is time to scan the bus
                    self.do_scan()
                    scan_time = t1 + self.scan_interval # Plan next scan

            try:    # Read values from selected sensor
                t1 = time.time()
                mysensor.read_val_from_sens(mysensor.sens) # Read temperature from DS thermometer
                mysensor.lost = False # Readout was successful
                mysensor.readtime = t1 # Store last read time - UNUSED NOW, redundant to mysensor.time
                if self.resultQ:
                    # send measurement into result queue
                    self.resultQ.send((mysensor.circuit, mysensor.value))
            except (TypeError, AttributeError):
                if not mysensor.lost: # Catch the edge
                    mysensor.set_lost()
                    self.resultQ.send((mysensor.circuit, mysensor.lost)) # Send info about lost to the queue
            mysensor.time = t1 + mysensor.calc_interval()
            mysensor = min(self.mysensors, key=lambda x: x.time)
            t1 = time.time()
            sleep_time = 0 if mysensor.time < t1 else mysensor.time - t1
            while self.taskQ.poll(sleep_time) is True:
                #commands from master
                cmd = self.taskQ.recv()
                self.do_command(cmd)
                mysensor = min(self.mysensors, key=lambda x: x.time)
                t1 = time.time()
                sleep_time = 0 if mysensor.time < t1 else mysensor.time - t1
