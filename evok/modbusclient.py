
import multiprocessing

import minimalmodbus

from functools import partial
import utils


class ModbusDevice(minimalmodbus.Instrument):
    def __init__(self, port_name, slave_address):
        minimalmodbus.Instrument.__init__(self, port_name, slave_address)

    def full(self):
        return {'dev': 'modbusdevice', 'address': self.address, 'value': None}

    def simple(self):
        return self.full()

    # todo use decorator
    def read(self, address):
        try:
            return utils.retry_func(partial(self.read_register, address), max_retry=10)
        except utils.RetryException as e:
            print "Failed to read from instrument error:{e}".format(**locals())
            raise e.exp

    def write(self, address, value):
        try:
            return utils.retry_func(partial(self.write_register, address, value), max_retry=10)
        except utils.RetryException as e:
            print "Failed to write from instrument error:{e}".format(**locals())
            raise e.exp


class RelayBoard16(ModbusDevice):
    def __init__(self, port_name, slave_address, baudrate, bytesize, timeout):
        minimalmodbus.Instrument.__init__(self, port_name, slave_address)

        #self.debug = True
        self.serial.baudrate = baudrate
        self.serial.bytesize = bytesize
        self.serial.timeout = timeout


        self.__relay_state = self.read(100)
        print "RelayBoard16 port_name:{port_name}; slave_address:{slave_address}; relay_states:{relay_state}".format(relay_state=self.__relay_state, **locals())

    def set_relay_state(self, index, value):
        if index < 16:
            new_value = self.__relay_state
            if value is True:
                # Set a bit
                new_value |= (0x1 << index)
            else:
                # Clear a bit
                new_value &= ~(0x1 << index)

            if new_value != self.__relay_state:
                self.__relay_state = new_value
                self.write(100, self.__relay_state)

    def get_relay_state(self, index):
        if index < 16:
            if (self.__relay_state & (0x1 << index)) != 0x0:
                return True
            else:
                return False


class ModBusDriver(multiprocessing.Process):
    def __init__(self, circuit, port, baudrate, bytesize, timeout):
        multiprocessing.Process.__init__(self)
        self.circuit = circuit
        self.devices = []

        self.port = port
        self.baudrate = baudrate
        self.bytesize = bytesize
        self.timeout = timeout  # seconds

    def create_devices(self, circuit, address, type):
        print "Modbus Device Factory: Type:\"{type}\" addr:{address}".format(**locals())

        device = None
        if (type == 'RelayBoard16'):
            device = RelayBoard16(self.port, address, baudrate=self.baudrate, bytesize=self.bytesize, timeout=self.timeout)

        else:
            print "Unknown modbus device %s (%s)".format(**locals())
            device = minimalmodbus.Instrument(self.port, address)

            device.debug = True
            device.serial.baudrate = self.baudrate
            device.serial.bytesize = self.bytesize
            device.serial.timeout = self.timeout

        device.circuit = circuit
        self.devices.append(device)

        return device

    def full(self):
        return {'dev': 'modbus', 'circuit': self.circuit, 'port': self.port}


if __name__ == "__main__":
    print "a"
    relays = RelayBoard16(port_name='/dev/ttyUSB0', slave_address=10, baudrate=9600, bytesize=8, timeout=0.05)

    for _ in range(0, 15):
        for i in range(0, 15):
            relays.set_relay_state(i, True)

        for i in range(0, 15):
            relays.set_relay_state(i, False)
