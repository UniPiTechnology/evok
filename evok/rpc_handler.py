#!/usr/bin/python

import tornado
import tornado.ioloop

from tornadorpc_evok.json import JSONRPCHandler
import tornadorpc_evok as tornadorpc

import time
import datetime
import json

import config

from devices import *


class userBasicHelper():
    _passwords = []

    def _request_auth(self):
        self.set_header('WWW-Authenticate', 'Basic realm=tmr')
        self.set_status(401)
        self.finish()
        return False

    def get_current_user(self):
        if len(self._passwords) == 0: return True
        auth_header = self.request.headers.get('Authorization')
        if auth_header is None:
            return self._request_auth()
        if not auth_header.startswith('Basic '):
            return self._request_auth()
        auth_decoded = base64.decodestring(auth_header[6:])
        username, password = auth_decoded.split(':', 2)

        print (username, password)
        print self._passwords
        if (username == 'rpc' and password in self._passwords):
            return True
        else:
            self._request_auth()


class Handler(userBasicHelper, JSONRPCHandler):
    @tornado.web.authenticated
    def post(self):
        JSONRPCHandler.post(self)

    ###### Input ######
    def input_get(self, circuit):
        inp = Devices.by_int(INPUT, str(circuit))
        return inp.get()

    def input_get_value(self, circuit):
        inp = Devices.by_int(INPUT, str(circuit))
        return inp.get_value()

    def input_set(self, circuit, debounce):
        inp = Devices.by_int(INPUT, str(circuit))
        return inp.set(debounce=debounce)


    ###### Relay ######
    def relay_get(self, circuit):
        relay = Devices.by_int(RELAY, str(circuit))
        return relay.get_state()

    @tornadorpc.coroutine
    def relay_set(self, circuit, value):
        relay = Devices.by_int(RELAY, str(circuit))
        result = yield relay.set_state(value)
        raise gen.Return(result)

    @tornadorpc.coroutine
    def relay_set_for_time(self, circuit, value, timeout):
        relay = Devices.by_int(RELAY, str(circuit))
        if timeout <= 0:
            raise Exception('Invalid timeout %s' % str(timeout))
        result = yield relay.set(value, timeout)
        raise gen.Return(result)

    ###### Analog Input ######
    def ai_get(self, circuit):
        ai = Devices.by_int(AI, str(circuit))
        return ai.get()

    def ai_set_bits(self, circuit, bits):
        ai = Devices.by_int(AI, str(circuit))
        return ai.set(bits=bits)

    def ai_set_interval(self, circuit, interval):
        ai = Devices.by_int(AI, str(circuit))
        return ai.set(interval=interval)

    def ai_set_gain(self, circuit, gain):
        ai = Devices.by_int(AI, str(circuit))
        return ai.set(gain=gain)

    def ai_set(self, circuit, bits, gain, interval):
        ai = Devices.by_int(AI, str(circuit))
        return ai.set(bits=bits, gain=gain, interval=interval)

    #def ai_measure(self, circuit):

    ###### Analog Output (0-10V) ######
    @tornadorpc.coroutine
    def ao_set_value(self, circuit, value):
        ao = Devices.by_int(AO, str(circuit))
        result = yield ao.set_value(value)
        raise gen.Return(result)

    @tornadorpc.coroutine
    def ao_set(self, circuit, value, frequency):
        ao = Devices.by_int(AO, str(circuit))
        result = yield ao.set(value, frequency)
        raise gen.Return(result)

    ###### OwBus (1wire bus) ######
    def owbus_get(self, circuit):
        ow = Devices.by_int(OWBUS, str(circuit))
        return ow.scan_interval

    def owbus_set(self, circuit, scan_interval):
        ow = Devices.by_int(OWBUS, str(circuit))
        return ow.set(scan_interval=scan_interval)

    def owbus_scan(self, circuit):
        ow = Devices.by_int(OWBUS, str(circuit))
        return ow.set(do_scan=True)

    def owbus_list(self, circuit):
        ow = Devices.by_int(OWBUS, str(circuit))
        return ow.list()

    ###### Sensors (1wire thermo,humidity) ######
    def sensor_set(self, circuit, interval):
        sens = Devices.by_int(SENSOR, str(circuit))
        return sens.set(interval=interval)

    def sensor_get(self, circuit):
        sens = Devices.by_int(SENSOR, str(circuit))
        return sens.get()

    def sensor_get_value(self, circuit):
        sens = Devices.by_int(SENSOR, str(circuit))
        return sens.get_value()

    @tornadorpc.coroutine
    def pca_set(self, circuit, channel, on, off):
        pca = Devices.by_int(PCA9685, str(circuit))
        result = yield pca.set(channel, on, off)
        raise gen.Return(result)

    @tornadorpc.coroutine
    def pca_set_pwm(self, circuit, channel, val):
        pca = Devices.by_int(PCA9685, str(circuit))
        result = yield pca.set_pwm(channel, val)
        raise gen.Return(result)

    ###### EEprom ######
    @tornadorpc.coroutine
    def ee_read_byte(self, circuit, index):
        ee = Devices.by_int(EE, str(circuit))
        result = yield ee.read_byte(index)
        raise gen.Return(result)

    @tornadorpc.coroutine
    def ee_write_byte(self, circuit, index, value):
        ee = Devices.by_int(EE, str(circuit))
        result = yield ee.write_byte(index, value)



