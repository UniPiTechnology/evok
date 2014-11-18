#!/usr/bin/python

import os
import ConfigParser
import tornado.httpserver
import tornado.ioloop
import tornado.web
# import tornado.websocket
from tornado import gen
from tornado.options import define, options
from tornado import web
from tornado import websocket
from tornado import escape
from tornado.concurrent import is_future

import signal

#import types

import base64
#from tornado.httpclient import AsyncHTTPClient

from tornadorpc_evok.json import JSONRPCHandler
import tornadorpc_evok as tornadorpc
#from tornadorpc import private, start_server, coroutine
#from tornadorpc.xml import XMLRPCHandler

import time
import random
import datetime
import multiprocessing
import json

#from apigpio import I2cBus, GpioBus
import unipig
import owclient
import config

from devices import *
from extcontrols import *
import extcontrols

define("port", default=80, help="run on the given port", type=int)


class UserCookieHelper():
    _passwords = []

    def get_current_user(self):
        if len(self._passwords) == 0: return True
        return self.get_secure_cookie("user")


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


class IndexHandler(UserCookieHelper, tornado.web.RequestHandler):
    def initialize(self, staticfiles):
        self.index = '%s/index.html' % staticfiles

    @tornado.web.authenticated
    @tornado.gen.coroutine
    def get(self):
        self.render(self.index)


registered_ws = {}


class WsHandler(websocket.WebSocketHandler):
    def open(self):
        #print "Opening %s" % (str(self))
        pass

    def on_event(self, device):
        #print "Sending to: %s,%s" % (str(self), device)
        try:
            self.write_message(device.full())
        except Exception as e:
            print "Exc: %s" % str(e)
            pass

    def on_message(self, message):
        #self.write_message(u''+ message)
        if message == 'register_all':
            if not registered_ws.has_key("all"):
                registered_ws["all"] = set()
            registered_ws["all"].add(self)
            #elif message == 'nfc2':
            #    registered_ws["nfc2"] = self

    def on_close(self):
        #print "Closing %s" % (str(self))
        if registered_ws.has_key("all") and (self in registered_ws["all"]):
            registered_ws["all"].remove(self)
            #elif registered_ws.has_key("nfc") and (registered_ws["nfc"] == self):
            #    registered_ws["nfc"] = None


class LoginHandler(tornado.web.RequestHandler):
    def get(self):
        try:
            errormessage = self.get_argument("error")
        except:
            errormessage = ""
        self.write('<html><body><div>%s</div><form action="" method="post">'
                   'Password: <input type="text" name="name">'
                   '<input type="submit" value="Sign in">'
                   '</form></body></html>' % errormessage)

    def check_permission(self, password, username):
        if username == "admin" and password in self._passwords:
            return True
        return False

    def post(self):
        username = self.get_argument("name")
        if self.check_permission(username, username):
            self.set_secure_cookie("user", escape.json_encode(username))
            self.redirect(self.get_argument("next", u"/"))
        else:
            error_msg = u"?error=" + escape.url_escape("Login incorrect")
            self.redirect(u"/login/" + error_msg)


class RestHandler(UserCookieHelper, tornado.web.RequestHandler):
    # usage: GET /rest/DEVICE/CIRCUIT
    #        or
    #        GET /rest/DEVICE/CIRCUIT/PROPERTY

    @tornado.web.authenticated
    def get(self, dev, circuit, prop):
        #print "%s-%s-%s" %(dev,circuit,prop)
        device = Devices.by_name(dev, circuit)
        if prop:
            if prop[0] in ('_'): raise Exception('Invalid property name')
            result = {prop: getattr(device, prop)}
        else:
            result = device.full()
        self.write(json.dumps(result))


    # usage: POST /rest/DEVICE/CIRCUIT
    #          post-data: prop1=value1&prop2=value2...

    #@tornado.web.authenticated
    @tornado.gen.coroutine
    def post(self, dev, circuit, prop):
        try:
            #print "%s-%s-%s" %(dev,circuit,prop)
            device = Devices.by_name(dev, circuit)
            kw = dict([(k, v[0]) for (k, v) in self.request.body_arguments.iteritems()])
            result = device.set(**kw)
            if is_future(result):
                result = yield result
            #print result        
            self.write(json.dumps({'success': True, 'result': result}))
        except Exception, E:
            self.write(json.dumps({'success': False, 'errors': {'__all__': str(E)}}))


class LoadAllHandler(UserCookieHelper, tornado.web.RequestHandler):
    #@tornado.gen.coroutine
    @tornado.web.authenticated
    def get(self):
        result = map(lambda dev: dev.full(), Devices.by_int(INPUT))
        result += map(lambda dev: dev.full(), Devices.by_int(RELAY))
        result += map(lambda dev: dev.full(), Devices.by_int(AI))
        result += map(lambda dev: dev.full(), Devices.by_int(AO))
        result += map(lambda dev: dev.full(), Devices.by_int(SENSOR))
        self.write(json.dumps(result))


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


def gener_status_cb(mainloop):
    def status_cb(device, *kwargs):
        #if add_computes(device):
        #    mainloop.add_callback(compute) 
        if registered_ws.has_key("all"):
            map(lambda x: x.on_event(device), registered_ws['all'])
        pass

    return status_cb


def gener_config_cb(mainloop):
    def config_cb(device, *kwargs):
        if registered_ws.has_key("all"):
            map(lambda x: x.on_event(device), registered_ws['all'])
        pass
        #if add_computes(device):
        #    mainloop.add_callback(compute) 
        #print device
        #d = device.full()
        #print "%s%s " %(d['dev'],d['circuit']) 

    return config_cb


################################ MAIN ################################

def main():
    # wait a second before sending first task
    #time.sleep(1)

    tornado.options.parse_command_line()

    Config = ConfigParser.SafeConfigParser(defaults={'webname': 'unipi', 'staticfiles': '/var/www', 'bus': 1})
    Config.add_section('MAIN')
    path = '/etc/evok.conf'
    if not os.path.isfile(path):
        path = os.path.dirname(os.path.realpath(__file__)) + '/evok.conf'
    Config.read(path)
    webname = Config.get("MAIN", "webname")
    staticfiles = Config.get("MAIN", "staticfiles")
    cookie_secret = Config.get("MAIN", "secret")
    try:
        pw = Config.get("MAIN", "password")
        userCookieHelper._passwords.append(pw)
    except:
        pass
    try:
        pw = Config.get("MAIN", "rpcpassword")
        print pw
        userBasicHelper._passwords.append(pw)
        print pw
    except:
        pass

    app = tornado.web.Application(
        handlers=[
            #(r"/", web.RedirectHandler, {"url": "http://%s/" % webname }),
            (r"/", IndexHandler, dict(staticfiles=staticfiles)),
            (r"/index.html", IndexHandler, dict(staticfiles=staticfiles)),
            (r"/login/", LoginHandler),
            (r"/stylesheets/(.*)", web.StaticFileHandler, {"path": "%s/stylesheets" % staticfiles}),
            (r"/images/(.*)", web.StaticFileHandler, {"path": "%s/images" % staticfiles}),
            (r"/js/(.*)", web.StaticFileHandler, {"path": "%s/js" % staticfiles}),
            (r"/rpc", Handler),
            (r"/rest/all/?", LoadAllHandler),
            (r"/rest/([^/]+)/([^/]+)/?(.+)?", RestHandler),
            (r"/ws", WsHandler),
            #(r"/.*", web.RedirectHandler, {"url": "http://%s/" % webname }),
        ],
        login_url='/login/',
        cookie_secret=cookie_secret
    )

    #app.add_handlers(r'%s.*' % webname , [(r"/", IndexHandler, dict(staticfiles=staticfiles))])

    #### prepare http server #####
    httpServer = tornado.httpserver.HTTPServer(app)
    httpServer.listen(options.port)
    print "Listening on port:", options.port

    mainLoop = tornado.ioloop.IOLoop.instance()

    # prepare Hw Devices
    devents.register_config_cb(gener_config_cb(mainLoop))
    devents.register_status_cb(gener_status_cb(mainLoop))
    config.create_devices(Config)

    #""" Setting the '_server' attribute if not set - simple link to mainloop"""
    for (srv, urlspecs) in app.handlers:
        for urlspec in urlspecs:
            try:
                setattr(urlspec.handler_class, '_server', mainLoop)
            except AttributeError:
                urlspec.handler_class._server = mainLoop

    # switch buses to async mode, start processes, plan some actions - specific for different devtypes
    for bus in Devices.by_int(I2CBUS):
        bus.switch_to_async(mainLoop)
    for bus in Devices.by_int(GPIOBUS):
        bus.switch_to_async(mainLoop)
    for adc in Devices.by_int(ADCHIP):
        mainLoop.add_callback(lambda: adc.measure_loop(mainLoop))
    for owbus in Devices.by_int(OWBUS):
        owbus.daemon = True
        owbus.start()
        owbus.register_in_caller = lambda d: Devices.register_device(SENSOR, d)
        owclient.set_non_blocking(owbus.resultRd)
        mainLoop.add_handler(owbus.resultRd, owbus.check_resultq, tornado.ioloop.IOLoop.READ)

    def sig_handler(sig, frame):
        if sig in (signal.SIGTERM, signal.SIGINT):
            tornado.ioloop.IOLoop.instance().add_callback(shutdown)

    #gracefull shutdown
    def shutdown():
        print "Shutting down"
        httpServer.stop()
        #todo: and shut immediately?
        tornado.ioloop.IOLoop.instance().stop()

    signal.signal(signal.SIGTERM, sig_handler)
    signal.signal(signal.SIGINT, sig_handler)

    mainLoop.start()


if __name__ == "__main__":
    main()

