#!/usr/bin/python

import asyncio

import os
from collections import OrderedDict

import tornado.httpserver
import tornado.httpclient
import tornado.ioloop
import tornado.web


from operator import methodcaller
from tornado.options import define, options
from tornado import websocket
from tornado import escape
from .handlers_base import EvokWebHandlerBase

try:
    from urllib.parse import urlparse  # py2
except ImportError:
    from urlparse import urlparse  # py3

import signal

import json
from . import config
from .devices import *

# from tornadows import complextypes

# Read config during initialisation
config_path = '/etc/evok'
if not os.path.isdir(config_path):
    config_path = os.path.dirname(os.path.realpath(__file__)) + '/evok'
    os.mkdir(config_path) if not os.path.exists(config_path) else None
evok_config = config.EvokConfig(config_path)

wh = None

from . import rpc_handler


class UserCookieHelper:
    _passwords = []

    def get_current_user(self):
        if len(self._passwords) == 0: return True
        return self.get_secure_cookie("user")


registered_ws = {}


class WhHandler:
    def __init__(self, url, allowed_types, complex_events):
        self.http_client = tornado.httpclient.AsyncHTTPClient()
        self.url = url
        self.allowed_types = allowed_types
        self.complex_events = complex_events

    def open(self):
        logger.debug(f"New WebHook connected {self.url}")
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
        outp = []
        try:
            if len(self.filter) == 1 and self.filter[0] == "default":
                self.write_message(json.dumps(device.full()))
            else:
                dev_all = device.full()
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

    async def on_message(self, message):
        try:
            message = json.loads(message)
            try:
                cmd = message["cmd"]
            except:
                cmd = None
            # get FULL state of each IO
            if cmd == "all":
                result = []
                devices = [INPUT, RELAY, AI, AO, SENSOR]
                if evok_config.get_api('websocket').get("all_filtered", False):
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
                await self.write_message(json.dumps(result))
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
                            result = await func(**value)
                        else:
                            result = await func(value)
                    else:
                        # Set other property than "value" (e.g. counter of an input)
                        funcdata = {key: value for (key, value) in message.items() if
                                    key not in ("circuit", "value", "cmd", "dev")}
                        if len(funcdata) > 0:
                            result = await func(**funcdata)
                        else:
                            result = await func()
                    if cmd == "full":
                        await self.write_message(json.dumps(result))
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


class LegacyRestHandler(UserCookieHelper, EvokWebHandlerBase):
    def _get_kw(self) -> dict:
        return dict([(k, v[0].decode()) for (k, v) in self.request.body_arguments.items()])


class LegacyJsonHandler(UserCookieHelper, EvokWebHandlerBase):
    def _get_kw(self) -> dict:
        return json.loads(self.request.body)


class LoadAllHandler(UserCookieHelper, EvokWebHandlerBase):
    async def get(self):  # noqa
        """This function returns a heterogeneous list of all devices exposed via the REST API"""
        result = self._get_all()
        self.write(json.dumps(result))
        self.set_header('Content-Type', 'application/json')
        await self.finish()

    async def post(self):  # noqa
        pass


class VersionHandler(UserCookieHelper, tornado.web.RequestHandler):
    version = 'Unspecified'

    def initialize(self):
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Headers", "x-requested-with")
        self.set_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        # TODO: ziskat verzy!!

    def get(self):
        self.write(self.version)
        self.finish()


class JSONBulkHandler(tornado.web.RequestHandler):
    def initialize(self):
        self.set_header("Content-Type", "application/json")
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Headers", "x-requested-with")
        self.set_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')

    def options(self):
        # no body
        self.set_status(204)
        self.finish()

    async def post(self):
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
                            all_devs_filtered.append(single_dev)
                    all_devs = all_devs_filtered
                if 'device_circuits' in single_query:
                    all_devs_filtered = []
                    for single_dev in all_devs:
                        if single_dev.circuit in single_query['device_circuits']:
                            all_devs_filtered.append(single_dev)
                    all_devs = all_devs_filtered
                if 'global_device_id' in single_query:
                    all_devs_filtered = []
                    for single_dev in all_devs:
                        if single_dev.dev_id == single_query['global_device_id']:
                            all_devs_filtered.append(single_dev)
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
                            all_devs_filtered.append(single_dev)
                    all_devs = all_devs_filtered
                if 'device_circuits' in single_command:
                    all_devs_filtered = []
                    for single_dev in all_devs:
                        if single_dev.circuit in single_command['device_circuits']:
                            all_devs_filtered.append(single_dev)
                    all_devs = all_devs_filtered
                if 'global_device_id' in single_command:
                    all_devs_filtered = []
                    for single_dev in all_devs:
                        if single_dev.dev_id == single_command['global_device_id']:
                            all_devs_filtered.append(single_dev)
                    outp = await all_devs[i].set(**(single_command['assigned_values']))
                if 'group_assignments' in result:
                    result['group_assignments'] += [map(methodcaller('full'), all_devs)]
                else:
                    result['group_assignments'] = [map(methodcaller('full'), all_devs)]
        if 'individual_assignments' in js_dict:
            for single_command in js_dict['individual_assignments']:
                outp = Devices.by_name(single_command['device_type'], circuit=single_command['device_circuit'])
                outp = await outp.set(**(single_command['assigned_values']))
                if 'individual_assignments' in result:
                    result['individual_assignments'] += [outp]
                else:
                    result['individual_assignments'] = [outp]
        self.write(json.dumps(result))
        await self.finish()


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
    log_file = evok_config.logging.get("file", "./evok.log")
    log_level = evok_config.logging.get("level", "INFO").upper()

    # rotating file handler
    filelog_handler = logging.handlers.TimedRotatingFileHandler(filename=log_file, when='D', backupCount=7)
    log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    filelog_handler.setFormatter(log_formatter)
    filelog_handler.setLevel(log_level)
    logger.addHandler(filelog_handler)
    # logging.getLogger('pymodbus').setLevel(logging.DEBUG)

    logger.info(f"Starting using config file {config_path}")

    hw_dict = config.HWDict(dir_paths=[f'{config_path}/hw_definitions/'])
    alias_dict = (config.HWDict(dir_paths=['/var/lib/evok/'])).definitions

    define("cors", default=True, help="enable CORS support", type=bool)
    port = evok_config.apis.get("port", 8080)
    if options.as_dict()['port'] != -1:
        port = options.as_dict()['port']  # use command-line option instead of config option

    app_routes = [
        (r"/rpc/?", rpc_handler.Handler),
        (r"/rest/all/?", LoadAllHandler),
        (r"/rest/([^/]+)/([^/]+)/?([^/]+)?/?", LegacyRestHandler),
        (r"/bulk/?", JSONBulkHandler),
        (r"/json/all/?", LoadAllHandler),
        (r"/json/([^/]+)/([^/]+)/?([^/]+)?/?", LegacyJsonHandler),
        (r"/version/?", VersionHandler),
        (r"/ws/?", WsHandler),
        (r"/(.*)", tornado.web.StaticFileHandler, {
            "path": "/opt/evok/www",
            "default_filename": "index.html"
        })
    ]

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

    modbus_context = None

    webhook_config = evok_config.get_api('webhook')
    if webhook_config.get("enabled", False):
        wh_address = webhook_config.get("address", "http://127.0.0.1:80/index.html")
        wh_types = webhook_config.get("device_mask", ["input", "sensor", "uart", "watchdog"])
        wh_complex = webhook_config.get("complex_events", False)
        wh = WhHandler(wh_address, wh_types, wh_complex)
        wh.open()

    mainLoop = tornado.ioloop.IOLoop.instance()

    #### prepare hardware according to config #####
    # prepare callbacks for config events
    devents.register_config_cb(gener_config_cb(mainLoop, modbus_context))
    devents.register_status_cb(gener_status_cb(mainLoop, modbus_context))

    # create hw devices
    config.create_devices(evok_config, hw_dict)
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
