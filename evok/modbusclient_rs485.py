"""
Implementation of a Modbus Client Using Tornado
-----------------------------------------------
Example run:

    from pymodbus_async.client import AsyncModbusSerialClient
    from pymodbus.exceptions import ConnectionException, ModbusIOException
    from pymodbus.register_read_message import ReadHoldingRegistersResponse
    import tornado.ioloop
    import sys

    def read_async():
        client = AsyncModbusSerialClient(method='rtu', stopbits=1, bytesize=8, parity='E', baudrate=19200, timeout=1, port='/dev/ttyUSB0')
        try:
            res = client.read_holding_registers(address=0, count=1, unit=1)
        except ConnectionException as ex:
            print("ConnectionException: %s" % str(ex))
            sys.exit()
        except ModbusIOException as ex:
            print("ModbusIOException: %s" % str(ex))
            sys.exit()
        res.addCallback(async_reply)

    def async_reply(result):
        if isinstance(result, ReadHoldingRegistersResponse):
            print("registers: %s" % str(result.registers))
        else:
            print("ERROR: %s" % str(result))
        tornado.ioloop.IOLoop.instance().stop()

    read_async()
    tornado.ioloop.IOLoop.instance().start()

"""
from pymodbus.client.sync import ModbusSerialClient as ModbusClient
from pymodbus.transaction import ModbusRtuFramer

from pymodbus.register_read_message import ReadHoldingRegistersRequest
from pymodbus.transaction import FifoTransactionManager
from pymodbus.client.sync import BaseModbusClient
from pymodbus.exceptions import ModbusIOException, NotImplementedException
from pymodbus.client.sync import ModbusSerialClient
from pymodbus.constants import Defaults
from pymodbus.factory import ClientDecoder

from pymodbus.pdu import ModbusResponse
from pymodbus.compat import byte2int

import socket
import tornado.ioloop
from functools import partial

import serial

import time
import datetime

import logging
_logger = logging.getLogger(__name__)

class AsyncErrorResponse(ModbusResponse):
    SerialConnectionError = 1
    SerialWriteError = 2
    SerialReadError = 3
    SerialReadTimeout = 4
    def __init__(self, error_code, **kwargs):
        _logger.info("AsyncErrorResponse.__init__()")
        super(AsyncErrorResponse, self).__init__(**kwargs)
        self.error_code = error_code

class AsyncModbusRtuFramer(ModbusRtuFramer):
    def __init__(self, decoder):
        _logger.info("AsyncModbusRtuFramer.__init__()")
        super(AsyncModbusRtuFramer, self).__init__(decoder)
        self.__buffer = b'' # we can't access ModbusRtuFramer.__buffer
        self.__buflen = 0
    def addToFrame(self, message):
        ModbusRtuFramer.addToFrame(self, message)
        self.__buffer += message
        self.__buflen = self.__buflen + len(message)
    def resetFrame(self):
        ModbusRtuFramer.resetFrame(self)
        self.__buffer = b''
        self.__buflen = 0
    def isFrameReady(self):
        _logger.info("AsyncModbusRtuFramer.isFrameReady()")
        if self.decoder:
            _logger.info("self.decoder: %s", str(self.decoder))
        return ModbusRtuFramer.isFrameReady(self)
    def getFrameLen(self):
        return self.__buflen
    def isExceptionFrame(self):
        if self.__buflen == 5 and byte2int(self.__buffer[1]) > 0x80:
            return True
        return False
    def processIncomingPacket(self, data, callback):
        _logger.info("AsyncModbusRtuFramer.processIncomingPacket(%s)", str(data))
        _logger.debug("  FRAME READY? " + str(self.isFrameReady()))
        while self.isFrameReady():
            _logger.debug("  FRAME CHECK? " + str(self.checkFrame()))
            if self.checkFrame():
                result = self.decoder.decode(self.getFrame())
                if result is None:
                    raise ModbusIOException("Unable to decode response")
                self.populateResult(result)
                self.advanceFrame()
                self.resetFrame()
                callback(result)  # defer or push to a thread?
                return
            else: self.resetFrame() # clear possible errors
    def processError(self, error, callback):
        _logger.info("AsyncModbusRtuFramer.processError(%s)", str(error))
        self.resetFrame()
        result = AsyncErrorResponse(error)
        callback(result)

class AsyncFifoTransactionManager(FifoTransactionManager):
    def execute(self, request):
        _logger.info("AsyncFifoTransactionManager.execute(%s)", str(request))
        self.request = request
        self.request.transaction_id = self.getNextTID()
        self.frame = self.client.framer.buildPacket(self.request)
        try:
            self.recvsize = self.client.framer.getResponseSize(self.request)
        except NotImplementedException:
            self.recvsize = 0;
        time_since_last_read = time.time() - self.client._last_frame_end
        _logger.info(" time_since_last_read: %f, _silent_interval: %f", time_since_last_read, self.client._silent_interval)
        if time_since_last_read < self.client._silent_interval:
            _logger.debug(" will delay to wait for 3.5 char")
            self.client.ioloop.add_timeout(datetime.timedelta(seconds=(self.client._silent_interval - time_since_last_read)), partial(self._sendAsyncRequest, self.frame))
        else:
            try:
                self._sendSyncRequest(self.frame)
            except socket.error as ex:
                self.delTransaction(self.request.transaction_id)
                raise ModbusIOException(str(ex))
        return self._buildResponse(self.request.transaction_id)
    def _sendSyncRequest(self, data):
        try:
            self.client._send(self.frame)
        except socket.error as ex:
            self.client.close()
            _logger.debug("  Transaction failed. (%s) " % ex)
            raise ex
    def _sendAsyncRequest(self, data):
        try:
            self.client._send(self.frame)
        except socket.error as msg:
            self.client.close()
            _logger.debug("  Transaction failed. (%s) " % msg)
            self.client.framer.processError(AsyncErrorResponse.SerialWriteError,  self.client._handleResponse)
    def _buildResponse(self, tid):
        _logger.info("AsyncFifoTransactionManager._buildResponse(%s)", str(tid))
        d = self
        self.addTransaction(d, tid)
        return d
    def addCallback(self, cb):
        _logger.info("AsyncFifoTransactionManager.addCallback(%s)", str(cb))
        self.callback = cb
    def executeCallback(self, reply):
        _logger.info("AsyncFifoTransactionManager.executeCallback(%s)", str(reply))
        if self.callback:
            self.callback(reply)

class AsyncModbusClient(BaseModbusClient):
    def __init__(self, framer):
        _logger.info("AsyncModbusClient.__init__()")
        self.framer = framer
        self.transaction = AsyncFifoTransactionManager(self)

class AsyncModbusSerialClient(ModbusSerialClient):
    def __init__(self, method='ascii', **kwargs):
        _logger.info("AsyncModbusSerialClient.__init__()")
        self.method = method
        self.socket = None
        AsyncModbusClient.__init__(self, self.__implementation(method))
        self.port = kwargs.get('port', 0)
        self.stopbits = kwargs.get('stopbits', Defaults.Stopbits)
        self.bytesize = kwargs.get('bytesize', Defaults.Bytesize)
        self.parity = kwargs.get('parity',   Defaults.Parity)
        self.baudrate = kwargs.get('baudrate', Defaults.Baudrate)
        self.timeout = kwargs.get('timeout',  Defaults.Timeout) or Defaults.Timeout
        self._last_frame_end = 0.0
        self._silent_interval = 3.5 * (1 + 8 + 2) / self.baudrate
        self.ioloop = tornado.ioloop.IOLoop.instance()
        self.timer = None
    @staticmethod
    def __implementation(method):
        method = method.lower()
        if method == 'rtu': return AsyncModbusRtuFramer(ClientDecoder())
        raise ParameterException("Unsupported framer method requested")
    def connect(self):
        _logger.info("AsyncModbusSerialClient.connect()")
        if self.socket: return True
        timeout = self.timeout  # remember timeout
        self.timeout = 0        # use non-blocking serial
        res = ModbusSerialClient.connect(self)
        self.timeout = timeout
        if self.socket:
            self.ioloop.add_handler(self.socket.fileno(), partial(self.dataReceived, self.socket), self.ioloop.READ)
        return res
    def close(self):
        if self.socket:
            self.ioloop.remove_handler(self.socket.fileno())
        return ModbusSerialClient.close(self)
    def dataReceived(self, socket, fd, events):
        _logger.info("AsyncModbusSerialClient.dataReceived(%s, %s, %s)", str(socket), str(fd), str(events))
        if events & self.ioloop.ERROR:
            _logger.critical("Serial ERROR")
            self.framer.processError(AsyncErrorResponse.SerialConnectionError,  self._handleResponse)
            return
        try:
            data = socket.read(65535)
        except serial.serialutil.SerialException as msg:
            _logger.critical("SerialException: %s", str(msg))
            self.framer.processError(AsyncErrorResponse.SerialReadError,  self._handleResponse)
            return
        _logger.debug("DATA: %s", str(data))
        self.framer.addToFrame(data)
        if self.framer.isExceptionFrame():
            self.framer.processIncomingPacket(data, self._handleResponse)
            return
        if self.transaction.recvsize:
            if self.framer.getFrameLen() < self.transaction.recvsize:
                _logger.debug("  not enough data yet")
                return
        self.framer.processIncomingPacket(data, self._handleResponse)
    def _handleResponse(self, reply):
        _logger.info("AsyncModbusSerialClient._handleResponse(%s)", str(reply))
        if self.timer:
            self.ioloop.remove_timeout(self.timer)
            self.timer = None
        self.framer.resetFrame()
        if reply is not None:
            tid = reply.transaction_id
            handler = self.transaction.getTransaction(tid)
            if handler:
                handler.executeCallback(reply)
            else: _logger.error("  Unrequested message: " + str(reply))

    def _send(self, request):
        _logger.info("AsyncModbusSerialClient._send(%s)", str(request))
        super(AsyncModbusSerialClient, self)._send(request)
        self._last_frame_end = time.time()
        if self.timeout:
            self.timer = self.ioloop.add_timeout(datetime.timedelta(seconds=self.timeout), self._timeout)
    def _recv(self, size):
        _logger.info("AsyncModbusSerialClient._recv((%d)",  size)
        result = self.socket.read(size)
        self._last_frame_end = time.time()
        return result
    def _timeout(self):
        _logger.info("AsyncModbusSerialClient._timeout()")
        self.framer.processError(AsyncErrorResponse.SerialReadTimeout,  self._handleResponse)
