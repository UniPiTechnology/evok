
import socket

from pymodbus.factory import ClientDecoder
from pymodbus.transaction import ModbusSocketFramer
from pymodbus.transaction import FifoTransactionManager
from pymodbus.transaction import DictTransactionManager
from pymodbus.exceptions import ConnectionException

from pymodbus.bit_read_message import *
from pymodbus.bit_write_message import *
from pymodbus.register_read_message import *
from pymodbus.register_write_message import *


from tornado import gen
from tornado.concurrent import TracebackFuture
from tornado.iostream import StreamClosedError
from tornado.tcpclient import TCPClient

#---------------------------------------------------------------------------#
# Logging
#---------------------------------------------------------------------------#
import logging
_logger = logging.getLogger(__name__)



class ModbusClientProtocol():
    '''
    This represents the base modbus client protocol.  All the application
    layer code is deferred to a higher level wrapper.
    '''

    def __init__(self, framer=None):
        ''' Initializes the framer module

        :param framer: The framer to use for the protocol
        '''
        self.connected = False
        self.framer = framer or ModbusSocketFramer(ClientDecoder())
        if isinstance(self.framer, ModbusSocketFramer):
            self.transaction = DictTransactionManager(self)
        else: self.transaction = FifoTransactionManager(self)

    def setTransport(self, stream):

        # clear frame buffer
        self.framer.advanceFrame()
        # clear all transaction with exception
        for tid in self.transaction:
            future = self.transaction.getTransaction(tid)
            future.set_exception(ConnectionException("Slave closed"))
        self.transport = stream
        self.connected = stream != None


    def dataReceived(self, data):
        ''' Get response, check for valid message, decode result
            To be used as streaming_callback to IOStream.read_until_close 

        :param data: The data returned from the server
        '''
        self.framer.processIncomingPacket(data, self._handleResponse)

    def _handleResponse(self, reply):
        ''' Handle the processed response and link to correct deferred

        :param reply: The reply to process
        '''
        if reply is not None:
            tid = reply.transaction_id
            future = self.transaction.getTransaction(tid)
            if future:
                future.set_result(reply)
                #handler.callback(reply)
            else: _logger.debug("Unrequested message: " + str(reply))


    @gen.coroutine
    def execute(self, request):
        ''' Starts the producer to send the next request to
        consumer.write(Frame(request))
        '''
        request.transaction_id = self.transaction.getNextTID()
        packet = self.framer.buildPacket(request)
        if not self.transport:
            raise ConnectionException("Slave not connected")
        yield self.transport.write(packet)
        future = TracebackFuture()
        self.transaction.addTransaction(future, request.transaction_id)
        res = yield future
        raise gen.Return(res)


    @gen.coroutine
    def read_input_registers(self, address, count=1, **kwargs):
        request = ReadInputRegistersRequest(address, count, **kwargs)
        res = yield self.execute(request)
        raise gen.Return(res)

    @gen.coroutine
    def write_coil(self, address, value, **kwargs):
        request = WriteSingleCoilRequest(address, value, **kwargs)
        res = yield self.execute(request)
        raise gen.Return(res)

    @gen.coroutine
    def write_register(self, address, value, **kwargs):
        request = WriteSingleRegisterRequest(address, value, **kwargs)
        res = yield self.execute(request)
        raise gen.Return(res)


@gen.coroutine
def StartClient(client, host='127.0.0.1', port=502, callback=None):
    ''' Connect to tcp host and, join to client.transport, wait for reply data
        Reconnect on close
    ''' 
    while True:
        try:
            stream = yield TCPClient().connect(host, port)
            client.setTransport(stream)
            future = stream.read_until_close(streaming_callback = client.dataReceived)
            if callback:
                yield callback()
            yield future
        except StreamClosedError:
            pass
        except Exception, E:
            print str(E)
            stream.close() 
        finally:
            client.setTransport(None)

'''
    client = ModbusClientProtocol()
    StartClient(client)    

'''

