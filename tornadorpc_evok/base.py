"""
============================
Base RPC Handler for Tornado
============================
This is a basic server implementation, designed for use within the
Tornado framework. The classes in this library should not be used
directly, but rather though the XML or JSON RPC implementations.
You can use the utility functions like 'private' and 'start_server'.
"""

from tornado.web import RequestHandler
import tornado.web
import tornado.ioloop
import tornado.httpserver
from tornado.concurrent import Future, TracebackFuture
from tornado import  gen
from tornado.stack_context import ExceptionStackContext, run_with_stack_context
import types
import traceback
from tornadorpc_evok.utils import getcallargs


# Configuration element
class Config(object):
    verbose = True
    short_errors = True

config = Config()

class BaseRPCParser(object):
    """
    This class is responsible for managing the request, dispatch,
    and response formatting of the system. It is tied into the
    _RPC_ attribute of the BaseRPCHandler (or subclasses) and
    populated as necessary throughout the request. Use the
    .faults attribute to take advantage of the built-in error
    codes.
    """
    content_type = 'text/plain'

    def __init__(self, library, encode=None, decode=None):
        # Attaches the RPC library and encode / decode functions.
        self.library = library
        if not encode:
            encode = getattr(library, 'dumps')
        if not decode:
            decode = getattr(library, 'loads')
        self.encode = encode
        self.decode = decode
        self.requests_in_progress = 0
        self.responses = []

    @property
    def faults(self):
        # Grabs the fault tree on request
        return Faults(self)


    def response(self, handler):
        """
        This is the callback for a single finished dispatch.
        Once all the dispatches have been run, it calls the
        parser library to parse responses and then calls the
        handler's async method.
        """
        handler._requests -= 1
        if handler._requests > 0:
            return
        # We are finished with requests, send response
        if handler._RPC_finished:
            # We've already sent the response
            raise Exception("Error trying to send response twice.")
        handler._RPC_finished = True
        responses = tuple(handler._results)
        response_text = self.parse_responses(responses)
        if type(response_text) not in types.StringTypes:
            # Likely a fault, or something messed up
            response_text = self.encode(response_text)
        # Calling the async callback
        handler.on_result(response_text)

    def traceback(self, method_name='REQUEST', params=[]):
        err_lines = traceback.format_exc().splitlines()
        err_title = "ERROR IN %s" % method_name
        if len(params) > 0:
            err_title = '%s - (PARAMS: %s)' % (err_title, repr(params))
        err_sep = ('-'*len(err_title))[:79]
        err_lines = [err_sep, err_title, err_sep]+err_lines
        if config.verbose:
            if len(err_lines) >= 7 and config.short_errors:
                # Minimum number of lines to see what happened
                # Plus title and separators
                print '\n'.join(err_lines[0:4]+err_lines[-3:])
            else:
                print '\n'.join(err_lines)
        # Log here
        return

    def parse_request(self, request_body):
        """
        Extend this on the implementing protocol. If it
        should error out, return the output of the
        'self.faults.fault_name' response. Otherwise,
        it MUST return a TUPLE of TUPLE. Each entry
        tuple must have the following structure:
        ('method_name', params)
        ...where params is a list or dictionary of
        arguments (positional or keyword, respectively.)
        So, the result should look something like
        the following:
        ( ('add', [5,4]), ('add', {'x':5, 'y':4}) )
        """
        return ([], [])

    def parse_responses(self, responses):
        """
        Extend this on the implementing protocol. It must
        return a response that can be returned as output to
        the client.
        """
        return self.encode(responses, methodresponse=True)

    def check_method(self, attr_name, obj):
        """
        Just checks to see whether an attribute is private
        (by the decorator or by a leading underscore) and
        returns boolean result.
        """
        assert(not attr_name.startswith('_'))
        attr = getattr(obj, attr_name)
        assert( not getattr(attr, 'private', False))
        return attr


class BaseRPCHandler(RequestHandler):
    """
    This is the base handler to be subclassed by the actual
    implementations and by the end user.
    """
    _RPC_ = None
    #_requests = 1
    rpcrequests = None
    _error = None
    _RPC_finished = False

    def prepare(self):
        """
        Parse request_body, prepares self.rpcrequest
        On error call finish or set self._error - to be serialized by export procedure
        """
        try:
            requests = self._RPC_.parse_request(self.request.body)
            if not isinstance(requests, types.TupleType):
                # SHOULD be the result of a fault call,
                # according tothe parse_request spec below.
                if isinstance(requests, basestring):
                    # Should be the response text of a fault
                    # This will break in Python 3.x
                    self.finish(requests)
                elif hasattr(requests, 'response'):
                    # Fault types should have a 'response' method
                    self.finish(requests.response())
                elif hasattr(requests, 'faultCode'):
                    # XML-RPC fault types need to be properly dispatched. This
                    # should only happen if there was an error parsing the
                    self._error = requests
                else:
                    # No idea, hopefully the handler knows what it is doing.
                    self.finish(requests)
                return
            self.rpcrequests = requests

        except (AttributeError,Exception):
            self._RPC_.traceback()
            self._error = self._RPC_.faults.parse_error()

    #@tornado.web.asynchronous
    @gen.coroutine
    def post(self):
        # Dispatches request methods
        # rpcrequests are prepared in self.prepare()
        if self._error:
            responses = (self._error,)
        else:
            futures = [self._dispatch(method, args) for method,args in self.rpcrequests ]
            if len(futures) == 1:
                response = yield futures[0]
                responses = (response,)
            else:
                responses = yield futures
                responses = tuple(responses)

        response_text = self._RPC_.parse_responses(responses)
        self.set_header('Content-Type', self._RPC_.content_type)
        self.finish(response_text)

        #self._RPC_.run(self, request_body)


    @gen.coroutine
    def _dispatch(self, method_name, params):
        """
        This method walks the attribute tree in the method
        and passes the parameters, either in positional or
        keyword form, into the appropriate method on the
        Handler class. Currently supports only positional
        or keyword arguments, not mixed.
        """
        try:
            assert(not hasattr(RequestHandler, method_name))
            print method_name
            method = self
            method_list = dir(method)
            method_list.sort()
            attr_tree = method_name.split('.')
            for attr_name in attr_tree:
                method = self._RPC_.check_method(attr_name, method)
            assert(callable(method))
            assert(not method_name.startswith('_'))
            assert(not getattr(method, 'private', False))
        except Exception,e :
            raise gen.Return(self._RPC_.faults.method_not_found())

        args = []
        kwargs = {}
        try:
            if isinstance(params, dict):
                # The parameters are keyword-based
                kwargs = params
            elif type(params) in (list, tuple):
                # The parameters are positional
                args = params
            else:
                # Bad argument formatting?
                raise Exception()
            # Validating call arguments
            final_kwargs, extra_args = getcallargs(method, *args, **kwargs)
        except Exception:
            raise gen.Return(self._RPC_.faults.invalid_params())

        try:
            if getattr(method, 'coroutine', False):
               method=tornado.gen.coroutine(method)
               response = yield method(*extra_args, **final_kwargs)
            else:
               response = method(*extra_args, **final_kwargs)

        except Exception:
            self._RPC_.traceback(method_name, params)
            raise gen.Return(self._RPC_.faults.internal_error())

        raise gen.Return(response)


class FaultMethod(object):
    """
    This is the 'dynamic' fault method so that the message can
    be changed on request from the parser.faults call.
    """
    def __init__(self, fault, code, message):
        self.fault = fault
        self.code = code
        self.message = message

    def __call__(self, message=None):
        if message:
            self.message = message
        return self.fault(self.code, self.message)


class Faults(object):
    """
    This holds the codes and messages for the RPC implementation.
    It is attached (dynamically) to the Parser when called via the
    parser.faults query, and returns a FaultMethod to be called so
    that the message can be changed. If the 'dynamic' attribute is
    not a key in the codes list, then it will error.

    USAGE:
        parser.fault.parse_error('Error parsing content.')

    If no message is passed in, it will check the messages dictionary
    for the same key as the codes dict. Otherwise, it just prettifies
    the code 'key' from the codes dict.

    """
    codes = {
        'parse_error': -32700,
        'method_not_found': -32601,
        'invalid_request': -32600,
        'invalid_params': -32602,
        'internal_error': -32603
    }

    messages = {}

    def __init__(self, parser, fault=None):
        self.library = parser.library
        self.fault = fault
        if not self.fault:
            self.fault = getattr(self.library, 'Fault')

    def __getattr__(self, attr):
        message = 'Error'
        if attr in self.messages.keys():
            message = self.messages[attr]
        else:
            message = ' '.join(map(str.capitalize, attr.split('_')))
        fault = FaultMethod(self.fault, self.codes[attr], message)
        return fault


"""
Utility Functions
"""


def private(func):
    """
    Use this to make a method private.
    It is intended to be used as a decorator.
    If you wish to make a method tree private, just
    create and set the 'private' variable to True
    on the tree object itself.
    """
    func.private = True
    return func


#def async(func):
#    """
#    Use this to make a method asynchronous
#    It is intended to be used as a decorator.
#    Make sure you call "self.result" on any
#    async method. Also, trees do not currently
#    support async methods.
#    """
#    func.async = True
#    return func

def coroutine(func):
    func.coroutine = True
    return func


def start_server(handlers, route=r'/', port=8080):
    """
    This is just a friendly wrapper around the default
    Tornado instantiation calls. It simplifies the imports
    and setup calls you'd make otherwise.
    USAGE:
        start_server(handler_class, route=r'/', port=8181)
    """
    if type(handlers) not in (types.ListType, types.TupleType):
        handler = handlers
        handlers = [(route, handler)]
        if route != '/RPC2':
            # friendly addition for /RPC2 if it's the only one
            handlers.append(('/RPC2', handler))
    application = tornado.web.Application(handlers)
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(port)
    loop_instance = tornado.ioloop.IOLoop.instance()
    """ Setting the '_server' attribute if not set """
    for (route, handler) in handlers:
        try:
            setattr(handler, '_server', loop_instance)
        except AttributeError:
            handler._server = loop_instance
    loop_instance.start()
    return loop_instance


"""
The following is a test implementation which should work
for both the XMLRPC and the JSONRPC clients.
"""


class TestMethodTree(object):
    def power(self, x, y=2):
        return pow(x, y)

    @private
    def private(self):
        # Shouldn't be called
        return False


class TestRPCHandler(BaseRPCHandler):

    _RPC_ = None

    def add(self, x, y):
        return x+y

    def ping(self, x):
        return x

    def noargs(self):
        return 'Works!'

    tree = TestMethodTree()

    def _private(self):
        # Shouldn't be called
        return False

    @private
    def private(self):
        # Also shouldn't be called
        return False
