#!/usr/bin/python
import base64
import functools
import inspect
from typing import Awaitable, Optional

import tornado.ioloop

from tornado_jsonrpc2 import JSONRPCHandler
from tornado_jsonrpc2.exceptions import MethodNotFound

from .devices import *


async def create_response(request, backend):
    try:
        method = getattr(backend, request.method)
    except AttributeError:
        raise MethodNotFound(f"Method '{request.method}' not found!")

    awaitable = False
    if inspect.isawaitable(method) or inspect.iscoroutine(method) or inspect.iscoroutinefunction(method):
        awaitable = True

    try:
        params = request.params
    except AttributeError:
        if awaitable:
            return await method()
        else:
            return method()

    if isinstance(params, list):
        if awaitable:
            return await method(*params)
        else:
            return method(*params)
    elif isinstance(params, dict):
        if awaitable:
            return await method(**params)
        else:
            return method(**params)


class UserBasicHelper(JSONRPCHandler):
    _passwords = []

    def initialize(self, response_creator: Awaitable = None, version: Optional[str] = None):
        if response_creator is None:
            response_creator = functools.partial(create_response,
                                                 backend=self)
        super().initialize(response_creator=response_creator, version=version)

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

        # print (username, password)
        # print self._passwords
        if (username == 'rpc' and password in self._passwords):
            return True
        else:
            self._request_auth()


class Handler(UserBasicHelper):

    @tornado.web.authenticated
    async def post(self):
        await JSONRPCHandler.post(self)

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

    async def relay_set(self, circuit, value):
        relay = Devices.by_int(RELAY, str(circuit))
        return await relay.set_state(value)

    async def relay_set_for_time(self, circuit, value, timeout):
        relay = Devices.by_int(RELAY, str(circuit))
        if timeout <= 0:
            raise Exception('Invalid timeout %s' % str(timeout))
        return await relay.set(value, timeout)

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

    # def ai_measure(self, circuit):

    ###### Analog Output (0-10V) ######
    async def ao_set_value(self, circuit, value):
        ao = Devices.by_int(AO, str(circuit))
        return await ao.set_value(value)

    async def ao_set(self, circuit, value, frequency):
        ao = Devices.by_int(AO, str(circuit))
        return await ao.set(value, frequency)

    ###### OwBus (1wire bus) ######
    def owbus_get(self, circuit):
        ow = Devices.by_int(OWBUS, str(circuit))
        return ow.bus_driver.scan_interval

    def owbus_set(self, circuit, scan_interval):
        ow = Devices.by_int(OWBUS, str(circuit))
        return ow.bus_driver.set(scan_interval=scan_interval)

    def owbus_scan(self, circuit):
        ow = Devices.by_int(OWBUS, str(circuit))
        return ow.bus_driver.set(do_scan=True)

    def owbus_list(self, circuit):
        ow = Devices.by_int(OWBUS, str(circuit))
        return ow.bus_driver.list()

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

    async def pca_set(self, circuit, channel, on, off):
        pca = Devices.by_int(PCA9685, str(circuit))
        return await pca.set(channel, on, off)

    async def pca_set_pwm(self, circuit, channel, val):
        pca = Devices.by_int(PCA9685, str(circuit))
        return await pca.set_pwm(channel, val)

    ###### EEprom ######
    async def ee_read_byte(self, circuit, index):
        ee = Devices.by_int(EE, str(circuit))
        return await ee.read_byte(index)

    async def ee_write_byte(self, circuit, index, value):
        ee = Devices.by_int(EE, str(circuit))
        return await ee.write_byte(index, value)
