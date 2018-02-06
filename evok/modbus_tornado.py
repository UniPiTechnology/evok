"""
Implementation of a Tornado Modbus Server
------------------------------------------

"""
from binascii import b2a_hex
from tornado import ioloop, tcpserver, gen
from pymodbus.constants import Defaults
from pymodbus.factory import ServerDecoder
from pymodbus.datastore import ModbusServerContext, ModbusSlaveContext, ModbusSequentialDataBlock
from pymodbus.device import ModbusControlBlock, ModbusAccessControl, ModbusDeviceIdentification
from pymodbus.transaction import ModbusSocketFramer
from pymodbus.interfaces import IModbusFramer
from pymodbus.pdu import ModbusExceptions as merror

__all__ = [ "StartTcpServer" ]

#---------------------------------------------------------------------------#
# Logging
#---------------------------------------------------------------------------#
import logging
_logger = logging.getLogger(__name__)

#---------------------------------------------------------------------------#
# Modbus TCP Server
#---------------------------------------------------------------------------#
class ModbusServer(tcpserver.TCPServer):

    def __init__(self, application, io_loop=None, max_buffer_size=None):
        self.application = application
        super(ModbusServer, self).__init__(io_loop, max_buffer_size)
        self._connections = set()
    
    @gen.coroutine
    def close_all_connections(self):
        while self._connections:
            # Peek at an arbitrary element of the set
            conn = next(iter(self._connections))
            yield conn.close()

    def handle_stream(self, stream, address):
        _logger.debug("Client Connected [%s]" % str(address))
        mbconn = ModbusConnection(stream, address, self.application)
        self._connections.add(mbconn)
        mbconn.start_run(self) 

    def on_close(self, conn):
        _logger.debug("Client Disconnected [%s]" % str(conn.address))
        self._connections.remove(conn)

class ModbusConnection(object):
    """Handles a connection to Modbus/TCP client, executing modbus requests.

    Input stream asynchronously reads data chunks, in callback sending o framer for processing.
    Recognized requests are executed and results writed onection is closed.
    """
    def __init__(self, stream, address, application):
        self.stream = stream
        self.address = address
        self.application = application
        self._request = None
        #self._request_finished = False
        self.framer = self.application.framer(decoder=self.application.decoder)

    def start_run(self, delegate):
        self.stream.set_close_callback(lambda : self._on_close(delegate))
        self.stream.read_bytes(1,callback=self._on_data)

    def _on_close(self, delegate):
        """ deregister itself from ModbusServer"""
        delegate.on_close(self)

    def _on_data(self, data):
        """
        Callback when we receive any data
            - process chunk of data
            - schedule next reading from stream
        """
        if _logger.isEnabledFor(logging.DEBUG):
            _logger.debug(" ".join([hex(ord(x)) for x in data]))
        self.framer.processIncomingPacket(data, self.execute)
        self.stream.read_bytes(1,callback=self._on_data)

    def send(self, message):
        """ Send a request (string) to the network

        :param message: The unencoded modbus response
        """
        assert self._request, "Request closed"
        if message.should_respond:
            self.application.control.Counter.BusMessage += 1
            pdu = self.framer.buildPacket(message)
            if _logger.isEnabledFor(logging.DEBUG):
                _logger.debug('send: %s' % b2a_hex(pdu))
            return self.stream.write(pdu)

    def execute(self, request):
        """
        Executes the request and returns the result
        @param request The decoded request message
        """
        self._request = request
        try:
            context = self.application.store[request.unit_id]
            response = request.execute(context)
        except Exception, ex:
            _logger.debug("Datastore unable to fulfill request: %s" % ex)
            response = request.doException(merror.SlaveFailure)
        #self.framer.populateResult(response)
        response.transaction_id = request.transaction_id
        response.unit_id = request.unit_id
        self.send(response)

    @gen.coroutine
    def close(self):
        """ Closes the connection.
            Returns a `.Future` that resolves after the serving loop has exited.
        """
        self.stream.close()
        # Block until the serving loop is done, but ignore any exceptions
        # (start_serving is already responsible for logging them).
        #try:
        #    yield self._serving_future
        #except Exception:
        #    pass

class ModbusApplication(object):
    def __init__(self, store, framer=None, identity=None):
        """ Overloaded initializer for the modbus factory

        If the identify structure is not passed in, the ModbusControlBlock
        uses its own empty structure.

        :param store: The ModbusServerContext datastore
        :param framer: The framer strategy to use
        :param identity: An optional identify structure

        """
        self.decoder = ServerDecoder()
        if isinstance(framer, IModbusFramer):
            self.framer = framer
        else: self.framer = ModbusSocketFramer

        if isinstance(store, ModbusServerContext):
            self.store = store
        else: self.store = ModbusServerContext()

        self.control = ModbusControlBlock()
        self.access = ModbusAccessControl()

        if isinstance(identity, ModbusDeviceIdentification):
            self.control.Identity.update(identity)

#---------------------------------------------------------------------------# 
# Starting Factory
#---------------------------------------------------------------------------# 
def StartTcpServer(context, identity=None, address=None):
    """ Helper method to start the Modbus Async TCP server
    :param context: The server data context
    :param identify: The server identity to use
    """
    address = address or ("", Defaults.Port)
    framer = ModbusSocketFramer
    modbus_server = ModbusServer(ModbusApplication(store=context, framer=framer, identity=identity))
    _logger.info("Starting Modbus TCP Server on %s:%s" % address)
    modbus_server.listen(address[1],address=address[0])
    ioloop.IOLoop.current().start()

#--------------------------------------------------------------------------#
# Testing proc
#--------------------------------------------------------------------------#

def main():
    logging.basicConfig()
    #server_log   = logging.getLogger("pymodbus.server")
    #protocol_log = logging.getLogger("pymodbus.protocol")

    """ Server launcher """
    from optparse import OptionParser

    parser = OptionParser()
    parser.add_option("-D", "--debug",
                    help="Turn on to enable tracing",
                    action="store_true", dest="debug", default=False)
    (opt, arg) = parser.parse_args()

    # enable debugging information
    if opt.debug:
        try:
            _logger.setLevel(logging.DEBUG)
        except Exception:
            print "Logging is not supported on this system"

    # Create store context
    store = ModbusSlaveContext(
    di = ModbusSequentialDataBlock(0, [17]*100),
    co = ModbusSequentialDataBlock(0, [17]*100),
    hr = ModbusSequentialDataBlock(0, [17]*100),
    ir = ModbusSequentialDataBlock(0, [17]*100))
    context = ModbusServerContext(slaves=store, single=True)

    identity = ModbusDeviceIdentification()
    identity.VendorName  = 'Pymodbus'
    identity.ProductCode = 'PM'
    identity.VendorUrl   = 'http://unipi.technology'
    identity.ProductName = 'Pymodbus Server on IOLoop'
    identity.ModelName   = 'Pymodbus Server'
    identity.MajorMinorRevision = '1.0'

    StartTcpServer(context, identity=identity, address=("localhost", 5020)) 

if __name__ == '__main__':
    main()

