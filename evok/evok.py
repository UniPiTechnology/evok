#!/usr/bin/python

import asyncio

import os
from collections import OrderedDict
import configparser as ConfigParser
import tornado.httpserver
import tornado.httpclient
import tornado.ioloop
import tornado.web
import yaml

from . import schemas

from operator import methodcaller
from tornado import gen
from tornado.options import define, options
from tornado import websocket
from tornado import escape
from tornado.concurrent import is_future
from tornado.gen import Return

from tornado.process import Subprocess  # not sure about it
import subprocess  # not sure about it

from .log import *
# from tornadows import soaphandler, webservices
# from tornadows.soaphandler import webservice
# from __builtin__ import str
from _ast import alias

# from test.badsyntax_future3 import result

try:
    from urllib.parse import urlparse  # py2
except ImportError:
    from urlparse import urlparse  # py3

import signal

import json
from . import config
from .devices import *

from tornado_json.requesthandlers import APIHandler
from tornado_json import schema
from tornado_json.exceptions import APIError

# from tornadows import complextypes

# Read config during initialisation
config_path = '/etc/evok'
if not os.path.isdir(config_path):
    config_path = os.path.dirname(os.path.realpath(__file__)) + '/evok'
    os.mkdir(config_path) if not os.path.exists(config_path) else None
evok_config = config.EvokConfig(config_path)

wh = None
cors = False
corsdomains = '*'
allow_unsafe_configuration_handlers = evok_config.getbooldef('allow_unsafe_configuration_handlers', False)

from . import rpc_handler


class UserCookieHelper():
    _passwords = []

    def get_current_user(self):
        if len(self._passwords) == 0: return True
        return self.get_secure_cookie("user")


'''
class SoapProperty(complextypes.ComplexType):
    property_name = str
    property_value = str

class SoapPropertyList(complextypes.ComplexType):
    device_type = str
    device_circuit = str
    property_item = [SoapProperty]

class SoapQueryInput(complextypes.ComplexType):
    device_type = str
    device_circuit = str

class SoapQueryInputList(complextypes.ComplexType):
    single_query = [SoapQueryInput]

class SoapCommandInputList(complextypes.ComplexType):
    single_command = [SoapPropertyList]

class SoapOutputList(complextypes.ComplexType):
    single_output = [SoapPropertyList]
'''


def enable_cors(handler):
    if cors:
        handler.set_header("Access-Control-Allow-Headers", "*")
        handler.set_header("Access-Control-Allow-Headers", "Content-Type, Depth, User-Agent, X-File-Size,"
                                                           "X-Requested-With, X-Requested-By, If-Modified-Since, X-File-Name, Cache-Control")
        handler.set_header("Access-Control-Allow-Origin", corsdomains)
        handler.set_header("Access-Control-Allow-Credentials", "true")
        handler.set_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")


# class IndexHandler(UserCookieHelper, tornado.web.RequestHandler):
#
#    def initialize(self, staticfiles):
#        self.index = '%s/index.html' % staticfiles
#        enable_cors(self)
#
#    @tornado.web.authenticated
#    @tornado.gen.coroutine
#    def get(self):
#        self.render(self.index)
registered_ws = {}


class WhHandler():
    def __init__(self, url, allowed_types, complex_events):
        self.http_client = tornado.httpclient.AsyncHTTPClient()
        self.url = url
        self.allowed_types = allowed_types
        self.complex_events = complex_events

    def open(self):
        logger.debug("New WebSocket modbusclient_rs485 connected")
        if not ("all" in registered_ws):
            registered_ws["all"] = set()

        registered_ws["all"].add(self)

    def on_event(self, device):
        dev_all = device.full()
        outp = []
        for single_dev in dev_all:
            if single_dev['dev'] in self.allowed_types:
                outp += [single_dev]
        try:
            if len(outp) > 0:
                if not self.complex_events:
                    self.http_client.fetch(self.url, method="GET")
                else:
                    self.http_client.fetch(self.url, method="POST", body=json.dumps(outp))
        except Exception as E:
            logger.exception(str(E))


class WsHandler(websocket.WebSocketHandler):

    def check_origin(self, origin):
        # fix issue when Node-RED removes the 'prefix://'
        parsed_origin = urlparse(origin)
        origin = parsed_origin.netloc
        origin = origin.lower()
        # return origin == host or origin_origin == host
        return True

    def open(self):
        self.filter = ["default"]
        logger.debug("New WebSocket client connected")
        if not ("all" in registered_ws):
            registered_ws["all"] = set()

        registered_ws["all"].add(self)

    def on_event(self, device):
        dev_all = device.full()
        outp = []
        try:
            if len(self.filter) == 1 and self.filter[0] == "default":
                self.write_message(json.dumps(device.full()))
            else:
                if 'dev' in dev_all:
                    dev_all = [dev_all]
                for single_dev in dev_all:
                    if single_dev['dev'] in self.filter:
                        outp += [single_dev]
                if len(outp) > 0:
                    self.write_message(json.dumps(outp))
        except Exception as e:
            logger.error("Exc: %s", str(e))
            pass

    @tornado.gen.coroutine
    def on_message(self, message):
        try:
            message = json.loads(message)
            try:
                cmd = message["cmd"]
            except:
                cmd = None
            # get FULL state of each IO
            if cmd == "all":
                result = []
                # devices = [INPUT, RELAY, AI, AO, SENSOR, UNIT_REGISTER]
                devices = [INPUT, RELAY, AI, AO, SENSOR]
                if evok_config.getbooldef("websocket_all_filtered", False):
                    if (len(self.filter) == 1 and self.filter[0] == "default"):
                        for dev in devices:
                            result += map(lambda dev: dev.full(), Devices.by_int(dev))
                    else:
                        for dev in range(0, 25):
                            added_results = map(lambda dev: dev.full() if dev.full() is not None else '',
                                                Devices.by_int(dev))
                            for added_result in added_results:
                                if added_result != '' and added_result['dev'] in self.filter:
                                    result.append(added_result)
                else:
                    for dev in range(0, 25):
                        added_results = map(lambda dev: dev.full() if dev.full() is not None else '',
                                            Devices.by_int(dev))
                        for added_result in added_results:
                            if added_result != '':
                                result.append(added_result)
                self.write_message(json.dumps(result))
            # set device state
            elif cmd == "filter":
                devices = []
                try:
                    for single_dev in message["devices"]:
                        if (str(single_dev) in devtype_names) or (str(single_dev) in devtype_altnames):
                            devices += [single_dev]
                    if len(devices) > 0 or len(message["devices"]) == 0:
                        self.filter = devices
                        if message["devices"][0] == "default":
                            self.filter = ["default"]
                    else:
                        raise Exception("Invalid 'devices' argument: %s" % str(message["devices"]))
                except Exception as E:
                    logger.exception("Exc: %s", str(E))
            elif cmd is not None:
                dev = message["dev"]
                circuit = message["circuit"]
                try:
                    value = message["value"]
                except:
                    value = None
                try:
                    device = Devices.by_name(dev, circuit)
                    func = getattr(device, cmd)
                    if value is not None:
                        if type(value) == dict:
                            result = func(**value)
                        else:
                            result = func(value)
                    else:
                        # Set other property than "value" (e.g. counter of an input)
                        funcdata = {key: value for (key, value) in message.items() if
                                    key not in ("circuit", "value", "cmd", "dev")}
                        if len(funcdata) > 0:
                            result = func(**funcdata)
                        else:
                            result = func()
                    if is_future(result):
                        result = yield result
                    if cmd == "full":
                        self.write_message(json.dumps(result))
                    # send response only to the modbusclient_rs485 requesting full info
                # nebo except Exception as e:
                except Exception as E:
                    logger.error("Exc: %s", str(E))

        except Exception as E:
            logger.debug("Skipping WS message: %s (%s)", message, str(E))
            # skip it since we do not understand this message....
            pass

    def on_close(self):
        if ("all" in registered_ws) and (self in registered_ws["all"]):
            registered_ws["all"].remove(self)
            if len(registered_ws["all"]) == 0:
                for neuron in Devices.by_int(MODBUS_SLAVE):
                    neuron.stop_scanning()


class LogoutHandler(tornado.web.RequestHandler):
    def get(self):
        self.clear_cookie("user")
        self.redirect(self.get_argument("next", "/"))


class LoginHandler(tornado.web.RequestHandler):
    def initialize(self):
        enable_cors(self)

    def post(self):
        username = 'admin'
        password = self.get_argument("password", "")
        auth = self.check_permission(password, username)
        if auth:
            self.set_secure_cookie("user", escape.json_encode(username))
            self.redirect(self.get_argument("next", u"/"))
        else:
            error_msg = u"?error=" + tornado.escape.url_escape("Login incorrect")
            self.redirect(u"/auth/login/" + error_msg)

    def get(self):
        self.redirect(self.get_argument("next", u"/"))

    def check_permission(self, password, username=''):
        if username == "admin" and password in self._passwords:
            return True
        return False


class LegacyRestHandler(UserCookieHelper, tornado.web.RequestHandler):
    def initialize(self):
        enable_cors(self)
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Headers", "x-requested-with")
        self.set_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')

    # usage: GET /rest/DEVICE/CIRCUIT
    #        or
    #        GET /rest/DEVICE/CIRCUIT/PROPERTY
    @tornado.web.authenticated
    def get(self, dev, circuit, prop):
        device = Devices.by_name(dev, circuit)
        if prop:
            if prop[0] in ('_'): raise Exception('Invalid property name')
            result = {prop: getattr(device, prop)}
        else:
            result = device.full()
        self.write(json.dumps(result))
        self.finish()

    # usage: POST /rest/DEVICE/CIRCUIT
    #          post-data: prop1=value1&prop2=value2...
    async def post(self, dev, circuit, prop):
        try:
            device = Devices.by_name(dev, circuit)
            kw = dict([(k, v[0].decode()) for (k, v) in self.request.body_arguments.items()])
            result = await device.set(**kw)
            self.write(json.dumps({'success': True, 'result': result}))
        except Exception as E:
            self.write(json.dumps({'success': False, 'errors': {'__all__': str(E)}}))
        self.set_header('Content-Type', 'application/json')
        await self.finish()

    def options(self):
        self.set_status(204)
        self.finish()


class RestOWireHandler(UserCookieHelper, APIHandler):
    def initialize(self):
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Headers", "x-requested-with")
        self.set_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        enable_cors(self)

    # usage: GET /rest/DEVICE/CIRCUIT
    #        or
    #        GET /rest/DEVICE/CIRCUIT/PROPERTY
    @tornado.web.authenticated
    @schema.validate()
    def get(self, circuit, prop):
        device = Devices.by_name("sensor", circuit)
        if prop:
            if prop[0] in ('_'): raise Exception('Invalid property name')
            result = {prop: getattr(device, prop)}
        else:
            result = device.full()
        return result
    @schema.validate(input_schema=schemas.owire_post_inp_schema, input_example=schemas.owire_post_inp_example)
    @tornado.gen.coroutine
    def post(self, circuit, prop):
        try:
            device = Devices.by_name("sensor", circuit)
            js_dict = json.loads(self.request.body)
            result = device.set(**js_dict)
            if is_future(result):
                result = yield result
            raise Return({'result': result})
        except Return as E:
            raise E
        except Exception as E:
            raise Return({'errors': str(E)})

    def options(self):
        self.set_status(204)
        self.finish()


class RestUARTHandler(UserCookieHelper, APIHandler):
    def initialize(self):
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Headers", "x-requested-with")
        self.set_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        enable_cors(self)

    # usage: GET /rest/DEVICE/CIRCUIT
    #        or
    #        GET /rest/DEVICE/CIRCUIT/PROPERTY
    @tornado.web.authenticated
    @schema.validate()
    def get(self, circuit, prop):
        device = Devices.by_name("uart", circuit)
        if prop:
            if prop[0] in ('_'): raise Exception('Invalid property name')
            result = {prop: getattr(device, prop)}
        else:
            result = device.full()
        return result

    # usage: POST /rest/DEVICE/CIRCUIT
    #          post-data: prop1=value1&prop2=value2...
    @schema.validate(input_schema=schemas.uart_post_inp_schema, input_example=schemas.uart_post_inp_example)
    @tornado.gen.coroutine
    def post(self, circuit, prop):
        try:
            device = Devices.by_name("uart", circuit)
            js_dict = json.loads(self.request.body)
            result = device.set(**js_dict)
            if is_future(result):
                result = yield result
            raise Return({'result': result})
        except Return as E:
            raise E
        except Exception as E:
            raise Return({'errors': str(E)})

    def options(self):
        self.set_status(204)
        self.finish()


class RestNeuronHandler(UserCookieHelper, APIHandler):
    def initialize(self):
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Headers", "x-requested-with")
        self.set_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        enable_cors(self)

    # usage: GET /rest/DEVICE/CIRCUIT
    #        or
    #        GET /rest/DEVICE/CIRCUIT/PROPERTY
    @tornado.web.authenticated
    @schema.validate()
    def get(self, circuit, prop):
        device = Devices.by_name("neuron", circuit)
        if prop:
            if prop[0] in ('_'): raise Exception('Invalid property name')
            result = {prop: getattr(device, prop)}
        else:
            result = device.full()
        return result

    # usage: POST /rest/DEVICE/CIRCUIT
    #          post-data: prop1=value1&prop2=value2...
    @schema.validate(input_schema=schemas.neuron_post_inp_schema, input_example=schemas.neuron_post_inp_example)
    @tornado.gen.coroutine
    def post(self, circuit, prop):
        try:
            device = Devices.by_name("neuron", circuit)
            js_dict = json.loads(self.request.body)
            result = device.set(**js_dict)
            if is_future(result):
                result = yield result
            raise Return({'result': result})
        except Return as E:
            raise E
        except Exception as E:
            raise Return({'errors': str(E)})

    def options(self):
        self.set_status(204)
        self.finish()


class RestLEDHandler(UserCookieHelper, tornado.web.RequestHandler):
    def initialize(self):
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Headers", "x-requested-with")
        self.set_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        enable_cors(self)

    # usage: GET /rest/DEVICE/CIRCUIT
    #        or
    #        GET /rest/DEVICE/CIRCUIT/PROPERTY
    @tornado.web.authenticated
    def get(self, circuit, prop):
        device = Devices.by_name("led", circuit)
        if prop:
            if prop[0] in ('_'): raise Exception('Invalid property name')
            result = {prop: getattr(device, prop)}
        else:
            result = device.full()
        return result

    # usage: POST /rest/DEVICE/CIRCUIT
    #          post-data: prop1=value1&prop2=value2...
    #@schema.validate(input_schema=schemas.led_post_inp_schema, input_example=schemas.led_post_inp_example)
    async def post(self, circuit, prop):
        try:
            device = Devices.by_name("led", circuit)
            kw = json.loads(self.request.body)
            result = await device.set(**kw)
            self.write(json.dumps({'success': True, 'result': result}))
        except Exception as E:
            self.write(json.dumps({'success': False, 'errors': {'__all__': str(E)}}))
        self.set_header('Content-Type', 'application/json')
        await self.finish()

    def success(self, output: str):
        print(f"Co to je???: {output}")

    def options(self):
        self.set_status(204)
        self.finish()


class RestWatchdogHandler(UserCookieHelper, APIHandler):
    def initialize(self):
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Headers", "x-requested-with")
        self.set_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        enable_cors(self)

    # usage: GET /rest/DEVICE/CIRCUIT
    #        or
    #        GET /rest/DEVICE/CIRCUIT/PROPERTY
    @tornado.web.authenticated
    @schema.validate()
    def get(self, circuit, prop):
        device = Devices.by_name("watchdog", circuit)
        if prop:
            if prop[0] in ('_'): raise Exception('Invalid property name')
            result = {prop: getattr(device, prop)}
        else:
            result = device.full()
        return result

    # usage: POST /rest/DEVICE/CIRCUIT
    #          post-data: prop1=value1&prop2=value2...
    @schema.validate(input_schema=schemas.wd_post_inp_schema, input_example=schemas.wd_post_inp_example)
    @tornado.gen.coroutine
    def post(self, circuit, prop):
        try:
            device = Devices.by_name("watchdog", circuit)
            js_dict = json.loads(self.request.body)
            result = device.set(**js_dict)
            if is_future(result):
                result = yield result
            raise Return({'result': result})
        except Return as E:
            raise E
        except Exception as E:
            raise Return({'errors': str(E)})

    def options(self):
        self.set_status(204)
        self.finish()


class RestRegisterHandler(UserCookieHelper, APIHandler):
    def initialize(self):
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Headers", "x-requested-with")
        self.set_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        enable_cors(self)

    # usage: GET /rest/DEVICE/CIRCUIT
    #        or
    #        GET /rest/DEVICE/CIRCUIT/PROPERTY
    @tornado.web.authenticated
    @schema.validate()
    def get(self, circuit, prop):
        device = Devices.by_name("register", circuit)
        if prop:
            if prop[0] in ('_'): raise Exception('Invalid property name')
            result = {prop: getattr(device, prop)}
        else:
            result = device.full()
        return result

    # usage: POST /rest/DEVICE/CIRCUIT
    #          post-data: prop1=value1&prop2=value2...
    # @tornado.web.authenticated
    @schema.validate(input_schema=schemas.register_post_inp_schema, input_example=schemas.register_post_inp_example)
    @tornado.gen.coroutine
    def post(self, circuit, prop):
        try:
            device = Devices.by_name("register", circuit)
            js_dict = json.loads(self.request.body)
            result = device.set(**js_dict)
            if is_future(result):
                result = yield result
            raise Return({'result': result})
        except Return as E:
            raise E
        except Exception as E:
            raise Return({'errors': str(E)})

    def options(self):
        self.set_status(204)
        self.finish()


class RestExtConfigHandler(UserCookieHelper, APIHandler):
    def initialize(self):
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Headers", "x-requested-with")
        self.set_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        enable_cors(self)

    # usage: GET /rest/DEVICE/CIRCUIT
    #        or
    #        GET /rest/DEVICE/CIRCUIT/PROPERTY
    @tornado.web.authenticated
    @schema.validate()
    def get(self, circuit, prop):
        device = Devices.by_name("ext_config", circuit)
        if prop:
            if prop[0] in ('_'): raise Exception('Invalid property name')
            result = {prop: getattr(device, prop)}
        else:
            result = device.full()
        return result

    # usage: POST /rest/DEVICE/CIRCUIT
    #          post-data: prop1=value1&prop2=value2...
    # @tornado.web.authenticated
    @schema.validate(input_schema=schemas.register_post_inp_schema, input_example=schemas.register_post_inp_example)
    @tornado.gen.coroutine
    def post(self, circuit, prop):
        try:
            device = Devices.by_name("ext_config", circuit)
            js_dict = json.loads(self.request.body)
            result = device.set(**js_dict)
            if is_future(result):
                result = yield result
            raise Return({'result': result})
        except Return as E:
            raise E
        except Exception as E:
            raise Return({'errors': str(E)})

    def options(self):
        self.set_status(204)
        self.finish()


class RestUnitRegisterHandler(UserCookieHelper, APIHandler):
    def initialize(self):
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Headers", "x-requested-with")
        self.set_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        enable_cors(self)

    # usage: GET /rest/DEVICE/CIRCUIT
    #        or
    #        GET /rest/DEVICE/CIRCUIT/PROPERTY
    @tornado.web.authenticated
    @schema.validate()
    def get(self, circuit, prop):
        device = Devices.by_name("unit_register", circuit)
        if prop:
            if prop[0] in ('_'): raise Exception('Invalid property name')
            result = {prop: getattr(device, prop)}
        else:
            result = device.full()
        return result

    # usage: POST /rest/DEVICE/CIRCUIT
    #          post-data: prop1=value1&prop2=value2...
    # @tornado.web.authenticated
    @schema.validate(input_schema=schemas.register_post_inp_schema, input_example=schemas.register_post_inp_example)
    @tornado.gen.coroutine
    def post(self, circuit, prop):
        try:
            device = Devices.by_name("unit_register", circuit)
            js_dict = json.loads(self.request.body)
            result = device.set(**js_dict)
            if is_future(result):
                result = yield result
            raise Return({'result': result})
        except Return as E:
            raise E
        except Exception as E:
            raise APIError(status_code=400, log_message=str(E))

    def options(self):
        self.set_status(204)
        self.finish()


class RestDIHandler(UserCookieHelper, APIHandler):
    post_out_example = {"result": 1, "success": True}

    def initialize(self):
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Headers", "x-requested-with")
        self.set_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        enable_cors(self)

    # usage: GET /rest/DEVICE/CIRCUIT
    #        or
    #        GET /rest/DEVICE/CIRCUIT/PROPERTY
    @tornado.web.authenticated
    @schema.validate()
    def get(self, circuit, prop):
        device = Devices.by_name("input", circuit)
        if prop:
            if prop[0] in ('_'): raise Exception('Invalid property name')
            result = {prop: getattr(device, prop)}
        else:
            result = device.full()
        return result

    # usage: POST /rest/DEVICE/CIRCUIT
    #          post-data: prop1=value1&prop2=value2...
    @schema.validate(input_schema=schemas.di_post_inp_schema, input_example=schemas.di_post_inp_example)
    @tornado.gen.coroutine
    def post(self, circuit, prop):
        try:
            device = Devices.by_name("input", circuit)
            js_dict = json.loads(self.request.body)
            result = device.set(**js_dict)
            if is_future(result):
                result = yield result
            raise Return({'result': result})
        except Return as E:
            raise E
        except Exception as E:
            raise Return({'errors': str(E)})

    def options(self):
        self.set_status(204)
        self.finish()


class RestOwbusHandler(UserCookieHelper, APIHandler):
    def initialize(self):
        enable_cors(self)
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Headers", "x-requested-with")
        self.set_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')

    # usage: GET /rest/DEVICE/CIRCUIT
    #        or
    #        GET /rest/DEVICE/CIRCUIT/PROPERTY

    @tornado.web.authenticated
    @schema.validate()
    def get(self, circuit, prop):
        device = Devices.by_name("owbus", circuit)
        if prop:
            if prop[0] in ('_'): raise Exception('Invalid property name')
            result = {prop: getattr(device, prop)}
        else:
            result = device.full()
        return result

    # usage: POST /rest/DEVICE/CIRCUIT
    #          post-data: prop1=value1&prop2=value2...
    @schema.validate()
    @tornado.gen.coroutine
    def post(self, circuit, prop):
        try:
            device = Devices.by_name("owbus", circuit)
            js_dict = json.loads(self.request.body)
            result = device.bus_driver.set(**js_dict)
            if is_future(result):
                result = yield result
            raise Return({'result': result})
        except Return as E:
            raise E
        except Exception as E:
            raise Return({'errors': str(E)})

    def options(self):
        # no body
        self.set_status(204)
        self.finish()


class RestDOHandler(UserCookieHelper, APIHandler):
    def initialize(self):
        enable_cors(self)
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Headers", "x-requested-with")
        self.set_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')

    # usage: GET /rest/DEVICE/CIRCUIT
    #        or
    #        GET /rest/DEVICE/CIRCUIT/PROPERTY

    @tornado.web.authenticated
    @schema.validate(output_schema=schemas.relay_get_out_schema, output_example=schemas.relay_get_out_example)
    def get(self, circuit, prop):
        device = Devices.by_name("output", circuit)
        if prop:
            if prop[0] in ('_'): raise Exception('Invalid property name')
            result = {prop: getattr(device, prop)}
        else:
            result = device.full()
        return result

    # usage: POST /rest/DEVICE/CIRCUIT
    #          post-data: prop1=value1&prop2=value2...
    @schema.validate(input_schema=schemas.relay_post_inp_schema, input_example=schemas.relay_post_inp_example)
    @tornado.gen.coroutine
    def post(self, circuit, prop):
        try:
            device = Devices.by_name("output", circuit)
            js_dict = json.loads(self.request.body)
            result = device.set(**js_dict)
            if is_future(result):
                result = yield result
            raise Return({'result': result})
        except Return as E:
            raise E
        except Exception as E:
            raise Return({'errors': str(E)})

    def options(self):
        # no body
        self.set_status(204)
        self.finish()



class RestAIHandler(UserCookieHelper, APIHandler):
    def initialize(self):
        enable_cors(self)
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Headers", "x-requested-with")
        self.set_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')

    # usage: GET /rest/DEVICE/CIRCUIT
    #        or
    #        GET /rest/DEVICE/CIRCUIT/PROPERTY
    @tornado.web.authenticated
    @schema.validate()
    def get(self, circuit, prop):
        device = Devices.by_name("ai", circuit)
        if prop:
            if prop[0] in ('_'): raise Exception('Invalid property name')
            result = {prop: getattr(device, prop)}
        else:
            result = device.full()
        return result

    # usage: POST /rest/DEVICE/CIRCUIT
    #          post-data: prop1=value1&prop2=value2...
    @schema.validate(input_schema=schemas.ai_post_inp_schema, input_example=schemas.ai_post_inp_example)
    @tornado.gen.coroutine
    def post(self, circuit, prop):
        try:
            device = Devices.by_name("ai", circuit)
            js_dict = json.loads(self.request.body)
            result = device.set(**js_dict)
            if is_future(result):
                result = yield result
            raise Return({'result': result})
        except Return as E:
            raise E
        except Exception as E:
            raise Return({'errors': str(E)})

    def options(self):
        self.set_status(204)
        self.finish()


class RestAOHandler(UserCookieHelper, APIHandler):
    def initialize(self):
        enable_cors(self)
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Headers", "x-requested-with")
        self.set_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')

    # usage: GET /rest/DEVICE/CIRCUIT
    #        or
    #        GET /rest/DEVICE/CIRCUIT/PROPERTY
    @tornado.web.authenticated
    @schema.validate()
    def get(self, circuit, prop):
        device = Devices.by_name("ao", circuit)
        if prop:
            if prop[0] in ('_'): raise Exception('Invalid property name')
            result = {prop: getattr(device, prop)}
        else:
            result = device.full()
        return result

    # usage: POST /rest/DEVICE/CIRCUIT
    #          post-data: prop1=value1&prop2=value2...
    @schema.validate(input_schema=schemas.ao_post_inp_schema, input_example=schemas.ao_post_inp_example)
    @tornado.gen.coroutine
    def post(self, circuit, prop):
        try:
            device = Devices.by_name("ao", circuit)
            js_dict = json.loads(self.request.body)
            result = device.set(**js_dict)
            if is_future(result):
                result = yield result
            raise Return({'result': result})
        except Return as E:
            raise E
        except Exception as E:
            raise Return({'errors': str(E)})

    def options(self):
        # no body
        self.set_status(204)
        self.finish()


class RemoteCMDHandler(UserCookieHelper, tornado.web.RequestHandler):  # ToDo CHECK
    def initialize(self):
        enable_cors(self)

    @tornado.gen.coroutine
    @tornado.web.authenticated
    def post(self):
        service = self.get_argument('service', '')
        status = self.get_argument('status', '')
        if service in ('ssh', 'sshd'):
            if status in ('start', 'stop', 'enable', 'disable'):
                yield call_shell_subprocess('service %s %s' % (service, status))
        if service == 'pw':
            yield call_shell_subprocess('echo -e "%s\\n%s" | passwd root' % (status, status))
        self.finish()


class ConfigHandler(UserCookieHelper, tornado.web.RequestHandler):
    def initialize(self):
        enable_cors(self)
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Headers", "x-requested-with")
        self.set_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')

    @tornado.web.authenticated
    def get(self):
        self.write(evok_config.configtojson())
        self.finish()

    @tornado.gen.coroutine
    @tornado.web.authenticated
    def post(self):
        conf = ConfigParser.ConfigParser()
        # make sure it it saved in the received order
        from collections import OrderedDict
        data = json.loads(self.request.body, object_pairs_hook=OrderedDict)
        for key in data:
            conf.add_section(key)
            for param in data[key]:
                val = data[key][param]
                conf.set(key, param, val)
        cfgfile = open(config.config_path, 'w')
        conf.write(cfgfile)
        cfgfile.close()
        yield call_shell_subprocess('service evok restart')
        self.finish()


class VersionHandler(UserCookieHelper, APIHandler):
    version = 'Unspecified'

    def initialize(self):
        enable_cors(self)
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Headers", "x-requested-with")
        self.set_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        with open('version.txt', 'r') as f:
            self.version = f.read(255)

    def get(self):
        self.write(self.version)
        self.finish()


@gen.coroutine
def call_shell_subprocess(cmd, stdin_data=None, stdin_async=False):
    """
    Wrapper around subprocess call using Tornado's Subprocess class.
    """
    stdin = Subprocess.STREAM if stdin_async else subprocess.PIPE

    sub_process = tornado.process.Subprocess(
        cmd, stdin=stdin, stdout=Subprocess.STREAM, stderr=Subprocess.STREAM, shell=True
    )

    if stdin_data:
        if stdin_async:
            yield Subprocess.Task(sub_process.stdin.write, stdin_data)
        else:
            sub_process.stdin.write(stdin_data)

    if stdin_async or stdin_data:
        sub_process.stdin.close()

    result, error = yield [
        gen.Task(sub_process.stdout.read_until_close),
        gen.Task(sub_process.stderr.read_until_close)
    ]

    raise gen.Return((result, error))


class JSONLoadAllHandler(UserCookieHelper, APIHandler):
    def initialize(self):
        enable_cors(self)
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Headers", "x-requested-with")
        self.set_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')

    # @schema.validate(output_schema=schemas.all_get_out_schema)
    async def get(self):
        """This function returns a heterogeneous list of all devices exposed via the REST API"""
        result = list(map(lambda dev: dev.full(), Devices.by_int(INPUT)))
        result += map(lambda dev: dev.full(), Devices.by_int(RELAY))
        result += map(lambda dev: dev.full(), Devices.by_int(OUTPUT))
        result += map(lambda dev: dev.full(), Devices.by_int(AI))
        result += map(lambda dev: dev.full(), Devices.by_int(AO))
        result += map(lambda dev: dev.full(), Devices.by_int(SENSOR))
        result += map(lambda dev: dev.full(), Devices.by_int(LED))
        result += map(lambda dev: dev.full(), Devices.by_int(WATCHDOG))
        result += map(lambda dev: dev.full(), Devices.by_int(MODBUS_SLAVE))
        result += map(lambda dev: dev.full(), Devices.by_int(UART))
        result += map(lambda dev: dev.full(), Devices.by_int(REGISTER))
        result += map(lambda dev: dev.full(), Devices.by_int(WIFI))
        result += map(lambda dev: dev.full(), Devices.by_int(LIGHT_CHANNEL))
        result += map(lambda dev: dev.full(), Devices.by_int(UNIT_REGISTER))
        result += map(lambda dev: dev.full(), Devices.by_int(EXT_CONFIG))
        self.success(result)

    def options(self):
        # no body
        self.set_status(204)
        self.finish()


class RestLoadAllHandler(UserCookieHelper, APIHandler):
    def initialize(self):
        enable_cors(self)
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Headers", "x-requested-with")
        self.set_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')

    async def get(self):
        """This function returns a heterogeneous list of all devices exposed via the REST API"""
        result = list(map(lambda dev: dev.full(), Devices.by_int(INPUT)))
        result += map(lambda dev: dev.full(), Devices.by_int(RELAY))
        result += map(lambda dev: dev.full(), Devices.by_int(AI))
        result += map(lambda dev: dev.full(), Devices.by_int(AO))
        result += map(lambda dev: dev.full(), Devices.by_int(SENSOR))
        result += map(lambda dev: dev.full(), Devices.by_int(LED))
        result += map(lambda dev: dev.full(), Devices.by_int(WATCHDOG))
        result += map(lambda dev: dev.full(), Devices.by_int(MODBUS_SLAVE))
        result += map(lambda dev: dev.full(), Devices.by_int(UART))
        result += map(lambda dev: dev.full(), Devices.by_int(REGISTER))
        result += map(lambda dev: dev.full(), Devices.by_int(WIFI))
        result += map(lambda dev: dev.full(), Devices.by_int(LIGHT_CHANNEL))
        result += map(lambda dev: dev.full(), Devices.by_int(OWBUS))
        result += map(lambda dev: dev.full(), Devices.by_int(UNIT_REGISTER))
        result += map(lambda dev: OrderedDict(sorted(dev.full().items(), key=lambda t: t[0])),
                      Devices.by_int(EXT_CONFIG))  # Sort for better reading
        self.write(json.dumps(result))
        self.set_header('Content-Type', 'application/json')
        self.finish()

    def options(self):
        # no body
        self.set_status(204)
        self.finish()


class JSONBulkHandler(APIHandler):
    def initialize(self):
        # enable_cors(self)
        self.set_header("Content-Type", "application/json")
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Headers", "x-requested-with")
        self.set_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')

    def options(self):
        # no body
        self.set_status(204)
        self.finish()

    @schema.validate()
    @tornado.gen.coroutine
    def post(self):
        """This function returns a heterogeneous list of all devices exposed via the REST API"""
        result = {}
        js_dict = json.loads(self.request.body)
        if 'group_queries' in js_dict:
            for single_query in js_dict['group_queries']:
                all_devs = []
                for device_type in single_query['device_types']:
                    all_devs += Devices.by_name(device_type)
                if 'group' in single_query:
                    all_devs_filtered = []
                    for single_dev in all_devs:
                        if single_dev.arm.major_group == single_query['group']:
                            all_devs_filtered += single_dev
                    all_devs = all_devs_filtered
                if 'device_circuits' in single_query:
                    all_devs_filtered = []
                    for single_dev in all_devs:
                        if single_dev.circuit in single_query['device_circuits']:
                            all_devs_filtered += single_dev
                    all_devs = all_devs_filtered
                if 'global_device_id' in single_query:
                    all_devs_filtered = []
                    for single_dev in all_devs:
                        if single_dev.dev_id == single_query['global_device_id']:
                            all_devs_filtered += single_dev
                    all_devs = all_devs_filtered
                if 'group_queries' in result:
                    result['group_queries'] += [map(methodcaller('full'), all_devs)]
                else:
                    result['group_queries'] = [map(methodcaller('full'), all_devs)]
        if 'group_assignments' in js_dict:
            for single_command in js_dict['group_assignments']:
                all_devs = Devices.by_name(single_command['device_type'])
                if 'group' in single_command:
                    all_devs_filtered = []
                    for single_dev in all_devs:
                        if single_dev.arm.major_group == single_command['group']:
                            all_devs_filtered += single_dev
                    all_devs = all_devs_filtered
                if 'device_circuits' in single_command:
                    all_devs_filtered = []
                    for single_dev in all_devs:
                        if single_dev.circuit in single_command['device_circuits']:
                            all_devs_filtered += single_dev
                    all_devs = all_devs_filtered
                if 'global_device_id' in single_command:
                    all_devs_filtered = []
                    for single_dev in all_devs:
                        if single_dev.dev_id == single_command['global_device_id']:
                            all_devs_filtered += single_dev
                    all_devs = all_devs_filtered
                for i in range(len(all_devs)):
                    outp = all_devs[i].set(**(single_command['assigned_values']))
                    if is_future(outp):
                        yield outp
                if 'group_assignments' in result:
                    result['group_assignments'] += [map(methodcaller('full'), all_devs)]
                else:
                    result['group_assignments'] = [map(methodcaller('full'), all_devs)]
        if 'individual_assignments' in js_dict:
            for single_command in js_dict['individual_assignments']:
                outp = Devices.by_name(single_command['device_type'], circuit=single_command['device_circuit'])
                outp = outp.set(**(single_command['assigned_values']))
                if is_future(outp):
                    outp = yield outp
                if 'individual_assignments' in result:
                    result['individual_assignments'] += [outp]
                else:
                    result['individual_assignments'] = [outp]
        raise gen.Return(result)



# callback generators for devents
def gener_status_cb(mainloop, modbus_context):
    def status_cb_modbus(device, *kwargs):
        modbus_context.status_callback(device)
        if "all" in registered_ws:
            for x in registered_ws['all']:
                x.on_event(device)

    def status_cb(device, *kwargs):
        if "all" in registered_ws:
            for x in registered_ws['all']:
                x.on_event(device)

    if modbus_context:
        return status_cb_modbus
    return status_cb


def gener_config_cb(mainloop, modbus_context):
    def config_cb_modbus(device, *kwargs):
        modbus_context.config_callback(device)

    def config_cb(device, *kwargs):
        pass

    if modbus_context:
        return config_cb_modbus
    return config_cb


################################ MAIN ################################

def main():
    # define("path1", default='', help="Use this config file, if device is Unipi 1.x", type=str)
    # define("path2", default='', help="Use this config file, if device is Unipi Neuron", type=str)
    define("port", default=-1, help="Http server listening ports", type=int)
    define("modbus_port", default=-1, help="Modbus/TCP listening port, 0 disables modbus", type=int)
    tornado.options.parse_command_line()

    # tornado.httpclient.AsyncHTTPClient.configure("tornado.curl_httpclient.CurlAsyncHTTPClient")
    log_file = evok_config.getstringdef("log_file", "./evok.log")
    log_level = evok_config.getstringdef("log_level", "INFO").upper()

    # rotating file handler
    filelog_handler = logging.handlers.TimedRotatingFileHandler(filename=log_file, when='D', backupCount=7)
    log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    filelog_handler.setFormatter(log_formatter)
    filelog_handler.setLevel(log_level)
    logger.addHandler(filelog_handler)
    # logging.getLogger('pymodbus').setLevel(logging.DEBUG)

    logger.info(f"Starting using config file {config_path}")

    hw_dict = config.HWDict(dir_paths=[f'{config_path}/hw_definitions/'])
    alias_dict = (config.HWDict(dir_paths=['/var/evok/'])).definitions

    cors = True
    corsdomains = evok_config.getstringdef("cors_domains", "*")
    define("cors", default=True, help="enable CORS support", type=bool)
    port = evok_config.getintdef("port", 8080)
    if options.as_dict()['port'] != -1:
        port = options.as_dict()['port']  # use command-line option instead of config option

    modbus_address = evok_config.getstringdef("modbus_address", '')
    modbus_port = evok_config.getintdef("modbus_port", 0)

    if options.as_dict()['modbus_port'] != -1:
        modbus_port = options.as_dict()['modbus_port']  # use command-line option instead of config option

    app_routes = [
        (r"/rpc/?", rpc_handler.Handler),
        (r"/rest/all/?", RestLoadAllHandler),
        (r"/rest/([^/]+)/([^/]+)/?([^/]+)?/?", LegacyRestHandler),
        (r"/bulk/?", JSONBulkHandler),
        (r"/json/all/?", JSONLoadAllHandler),
        (r"/json/input/?([^/]+)/?([^/]+)?/?", RestDIHandler),
        (r"/json/di/?([^/]+)/?([^/]+)?/?", RestDIHandler),
        (r"/json/output/?([^/]+)/?([^/]+)?/?", RestDOHandler),
        (r"/json/do/?([^/]+)/?([^/]+)?/?", RestDOHandler),
        (r"/json/relay/?([^/]+)/?([^/]+)?/?", RestDOHandler),
        (r"/json/register/?([^/]+)/?([^/]+)?/?", RestRegisterHandler),
        (r"/json/ai/?([^/]+)/?([^/]+)?/?", RestAIHandler),
        (r"/json/analoginput/?([^/]+)/?([^/]+)?/?", RestAIHandler),
        (r"/json/ao/?([^/]+)/?([^/]+)?/?", RestAOHandler),
        (r"/json/analogoutput/?([^/]+)/?([^/]+)?/?", RestAOHandler),
        (r"/json/led/?([^/]+)/?([^/]+)?/?", RestLEDHandler),
        (r"/json/watchdog/?([^/]+)/?([^/]+)?/?", RestWatchdogHandler),
        (r"/json/wd/?([^/]+)/?([^/]+)?/?", RestWatchdogHandler),
        (r"/json/neuron/?([^/]+)/?([^/]+)?/?", RestNeuronHandler),
        (r"/json/rs485/?([^/]+)/?([^/]+)?/?", RestUARTHandler),
        (r"/json/uart/?([^/]+)/?([^/]+)?/?", RestUARTHandler),
        (r"/json/temp/?([^/]+)/?([^/]+)?/?", RestOWireHandler),
        (r"/json/sensor/?([^/]+)/?([^/]+)?/?", RestOWireHandler),
        (r"/json/1wdevice/?([^/]+)/?([^/]+)?/?", RestOWireHandler),
        (r"/json/owbus/?([^/]+)/?([^/]+)?/?", RestOwbusHandler),
        (r"/json/unit_register/?([^/]+)/?([^/]+)?/?", RestUnitRegisterHandler),
        (r"/json/ext_config/?([^/]+)/?([^/]+)?/?", RestExtConfigHandler),
        (r"/version/?", VersionHandler),
        (r"/ws/?", WsHandler),
        (r"/(.*)", tornado.web.StaticFileHandler, {
            "path": "../var/www/evok",
            "default_filename": "index.html"
        })
    ]

    if allow_unsafe_configuration_handlers:
        app_routes.append((r"/config/?", ConfigHandler))
        app_routes.append((r"/config/cmd/?", RemoteCMDHandler))

    app = tornado.web.Application(
        handlers=app_routes
    )
    # docs = get_api_docs(app_routes)
    # print docs
    # try:
    #    with open('./API_docs.md', "w") as api_out:
    #        api_out.writelines(docs)
    # except Exception as E:
    #    logger.exception(str(E))

    #### prepare http server #####
    httpServer = tornado.httpserver.HTTPServer(app)
    httpServer.listen(port)
    logger.info("HTTP server listening on port: %d", port)

    if modbus_port > 0:  # used for UniPi 1.x
        from modbus_tornado import ModbusServer, ModbusApplication
        import modbus_unipi
        # modbus_context = modbus_unipi.UnipiContext()  # full version
        modbus_context = modbus_unipi.UnipiContextGpio()  # limited version

        modbus_server = ModbusServer(ModbusApplication(store=modbus_context, identity=modbus_unipi.identity))
        modbus_server.listen(modbus_port, address=modbus_address)
        logger.info("Modbus/TCP server istening on port: %d", modbus_port)
    else:
        modbus_context = None

    if evok_config.getbooldef("soap_server_enabled", False):  # TODO: zachranit??
        soap_services = [
            ('UniPiQueryService', UniPiQueryService),
            ('UniPiCommandService', UniPiCommandService)
        ]
        soap_app = webservices.WebService(soap_services)
        soap_server = tornado.httpserver.HTTPServer(soap_app)
        soap_port = evok_config.getintdef("soap_server_port", 8081)
        soap_server.listen(soap_port)
        logger.info("Starting SOAP server on %d", soap_port)

    if evok_config.getbooldef("webhook_enabled", False):
        wh_types = json.loads(
            evok_config.getstringdef("webhook_device_mask", '["input", "sensor", "uart", "watchdog"]'))
        wh_complex = evok_config.getbooldef("webhook_complex_events", False)
        wh = WhHandler(evok_config.getstringdef("webhook_address", "http://127.0.0.1:80/index.html"), wh_types,
                       wh_complex)
        wh.open()

    mainLoop = tornado.ioloop.IOLoop.instance()

    #### prepare hardware according to config #####
    # prepare callbacks for config events
    devents.register_config_cb(gener_config_cb(mainLoop, modbus_context))
    devents.register_status_cb(gener_status_cb(mainLoop, modbus_context))

    # create hw devices
    config.create_devices(evok_config, hw_dict)
    if evok_config.getbooldef("wifi_control_enabled", False):
        config.add_wifi()
    '''
    """ Setting the '_server' attribute if not set - simple link to mainloop"""
    for (srv, urlspecs) in app.handlers:
        for urlspec in urlspecs:
            try:
                setattr(urlspec.handler_class, '_server', mainLoop)
            except AttributeError:
                urlspec.handler_class._server = mainLoop
    '''
    # switch buses to async mode, start processes, plan some actions
    for bustype in (I2CBUS, GPIOBUS, OWBUS):
        for device in Devices.by_int(bustype):
            device.bus_driver.switch_to_async(mainLoop)

    for bustype in (ADCHIP, TCPBUS, SERIALBUS):
        for device in Devices.by_int(bustype):
            device.switch_to_async(mainLoop)

    for modbus_slave in Devices.by_int(MODBUS_SLAVE):
        modbus_slave.switch_to_async(mainLoop, alias_dict)
        if modbus_slave.scan_enabled:
            modbus_slave.start_scanning()


    def sig_handler(sig, frame):
        if sig in (signal.SIGTERM, signal.SIGINT):
            tornado.ioloop.IOLoop.instance().add_callback_from_signal(shutdown)

    # graceful shutdown
    def shutdown():
        for bus in Devices.by_int(I2CBUS):
            bus.bus_driver.switch_to_sync()
        for bus in Devices.by_int(GPIOBUS):
            bus.bus_driver.switch_to_sync()
        logger.info("Shutting down")
        tornado.ioloop.IOLoop.instance().stop()

    signal.signal(signal.SIGTERM, sig_handler)
    signal.signal(signal.SIGINT, sig_handler)

    mainLoop.start()


if __name__ == "__main__":
    main()
