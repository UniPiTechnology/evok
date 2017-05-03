from collections import deque
import time
from log import *
import devices

# Controls = {}
ComputeMap = {}
ToCompute = deque()  #queue of control, which must be recomputed
mainloop = None


def compute():
    #global ComputeMap
    #global ToCompute
    cnt = 0
    while len(ToCompute) > 0:
        control = ToCompute.popleft()
        #print type(control)
        cnt += 1
        if control.compute() and (control in ComputeMap):
            for dep_control in ComputeMap[control]:
                if not (dep_control in ToCompute):
                    #print "  %s ADD" % type(dep_control)
                    ToCompute.append(dep_control)
                    #else: print "  %s" % type(dep_control)

                    #print "computed %d steps" %cnt


def add_computes(device):
    #global ComputeMap
    #global ToCompute
    do_compute = False
    if device in ComputeMap:
        for dep_control in ComputeMap[device]:
            if not (dep_control in ToCompute):
                ToCompute.append(dep_control)
                do_compute = True
    return do_compute


class Control(object):
    #changed = False
    _value = None

    @property
    def value(self):
        return self._value

    def compute(self):
        pass

    def inverted(self):
        return int(not (bool(self._value)))

    def eval_later(self, name, fun):
        if type(fun) is str:  # problem if fun=DEVICE.value and that is string!!
            # search in devices
            try:
                dev, circuit, prop = fun.split()
                #try: circuit = int(circuit) 
                #except: pass
                obj = devices.Devices.by_name(dev, circuit)
                fun = getattr(obj, prop)
                #print "%s %s" % (type(obj),prop)
                if callable(fun):
                    setattr(self, name, fun)
                else:
                    setattr(self, name, lambda: getattr(obj, prop))
            except Exception, E:
                logger.debug(str(E))
                #TODO doplnit vyhledani Controls
                raise Exception('Cannot eval function')
        else:
            #print type(fun)
            if isinstance(fun, Control):
                #print "fun is Control"
                setattr(self, name, lambda: fun.value)
            elif callable(fun):
                #print "fun is function"
                setattr(self, name, fun)
            else:
                #print "fun is something"
                setattr(self, name, lambda: fun)
        realfun = getattr(self, name)
        return realfun()  #eval the real function

    def eval_later_output(self, name, fun, value):
        if type(fun) is str:  # problem if fun=DEVICE.value and that is string!!
            # search in devices
            try:
                dev, circuit, prop = fun.split()
                #try: circuit = int(circuit) 
                #except: pass
                obj = devices.Devices.by_name(dev, circuit)
                fun = getattr(obj, prop)
                #print "%s %s" % (type(obj),prop)
                if not callable(fun):
                    raise Exception('Output must be function')
            except Exception, E:
                logger.debug(str(E))
                #TODO doplnit vyhledani Controls
                raise Exception('Cannot eval function')
        else:
            if not callable(fun):
                raise Exception('Output must be function')
        setattr(self, name, fun)
        return fun(value)  #eval the real function


class Hysteresis(Control):
    """ Controls binary result with hystereresis
           
    """
    _setpoint = 28.0
    dtplus = 0.1
    dtminus = 0.1
    _value = 0

    def __init__(self, get_input):
        self.input1 = lambda: self.eval_later('input1', get_input)

    @property
    def setpoint(self):
        return self._setpoint

    @setpoint.setter
    def setpoint(self, nvalue):
        if nvalue != self._setpoint:
            self._setpoint = nvalue
            self.compute()
            add_computes(self)

    def compute(self):
        inp = self.input1()
        #print "%s %s %s" % (inp,self._setpoint,self._value)
        if inp <= self._setpoint - self.dtminus:
            nvalue = 0
        elif inp < self._setpoint + self.dtplus:
            nvalue = self._value
        else:
            nvalue = 1
        #print "%s %s %s" % (inp,self._setpoint,nvalue)
        if nvalue != self._value:
            self._value = nvalue
            return True


class Switch(Control):
    """ Switch can be set by user(web) to 0/1 state
    """
    _value = 0

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, nvalue):
        if nvalue != self._value:
            self._value = nvalue
            add_computes(self)


class Xor(Control):
    """ Binary result
             - is input1       if input2 == 0 
             - is not(input1)  if input2 == 1
        (and vice versa)
    """

    def __init__(self, get_input1, get_input2):
        self.input1 = lambda: self.eval_later('input1', get_input1)
        self.input2 = lambda: self.eval_later('input2', get_input2)

    def compute(self):
        nvalue = int(not (bool(self.input1()) == bool(self.input2())))
        if nvalue != self._value:
            self._value = nvalue
            return True


class And(Control):
    """ Result is input1 AND input2
    """

    #def __init__(self, *args):
    #    if len(args) < 1: raise Exception("AND control needs at least 1 input")
    #    for inp in args:
    #        self.input1 = lambda : self.eval_later('input1',get_input1)
    def __init__(self, get_input1, get_input2):
        self.input1 = lambda: self.eval_later('input1', get_input1)
        self.input2 = lambda: self.eval_later('input2', get_input2)

    def compute(self):
        nvalue = int(bool(self.input1()) and bool(self.input2()))
        if nvalue != self._value:
            self._value = nvalue
            return True


class Or(Control):
    """ Result is input1 OR input2
    """

    def __init__(self, get_input1, get_input2):
        self.input1 = lambda: self.eval_later('input1', get_input1)
        self.input2 = lambda: self.eval_later('input2', get_input2)

    def compute(self):
        nvalue = int(bool(self.input1()) or bool(self.input2()))
        if nvalue != self._value:
            self._value = nvalue
            return True


class Not(Control):
    def __init__(self, get_input):
        self.input = lambda: self.eval_later('input', get_input)

    def compute(self):
        nvalue = int(not bool(self.input()))
        if nvalue != self._value:
            self._value = nvalue
            return True


class Set(Control):
    """ Result is input1 and input2
    """

    def __init__(self, get_input, set_output):
        self.input = lambda: self.eval_later('input', get_input)
        self.output = lambda x: self.eval_later_output('output', set_output, x)

    def compute(self):
        nvalue = int(bool(self.input()))
        if nvalue != self._value:
            self._value = nvalue
            self.output(nvalue)
            #TODO mozna vystup nechat az na dokonceni vypocetniho cyklu
            #self.changed = True


RISING = 0
FALLING = 1


class Pulse(Control):
    """ Generate pulse from rising/falling edge of input
           - supresses prolongation in case of double rise/fall
    """

    def __init__(self, edge, pulse, get_input):
        self._edge = edge
        self._pulse = pulse
        self.input = lambda: self.eval_later('input', get_input)
        self._value = 0  # result on start is always 0
        self._last_input = 1 if edge == FALLING else 0
        self.generation = 0

    def callback(self):
        if not self._value: return  # weird situation
        self._value = 0
        add_computes(self)
        compute()


    def compute(self):
        ninput = int(bool(self.input()))
        if ninput is None: return
        if self._edge == FALLING: ninput = int(not ninput)  # convert it to rising
        nvalue = int(ninput and not self._last_input)  # rising detected
        self._last_input = ninput
        if nvalue and not self._value:  # supress double pulse
            self._value = 1
            # if mainloop:
            # mainloop.call_later(self._pulse, self.callback)
            return True


# HYST_FAN = Hysteresis('sensor 1 value')
# SWITCH_ON = Switch()
# SWITCH_HEAT = Switch()
#
# FAN_HEATCOOL = Xor(SWITCH_HEAT, HYST_FAN)
# FAN_ONOFF = And(SWITCH_ON, FAN_HEATCOOL)
#
# PULSE_LATE = Pulse(RISING, 2, FAN_ONOFF)
# FAN_LATE = And(PULSE_LATE.inverted, FAN_ONOFF, )
#
# PULSE_MIN = Pulse(RISING, 5, FAN_LATE)
# FAN_MIN = Or(PULSE_MIN, FAN_LATE, )
#
# FAN = Set(FAN_MIN, 'relay 1 set_state')
# LIGHT = Set(SWITCH_ON, 'relay 2 set_state')

#TODO add all controls to ToCompute for initialization

# RELAY_LEFT_NOT = Not('relay 3 value')
# BUTTON_LEFT = And(RELAY_LEFT_NOT, 'input 1 value')
#
# RELAY_RIGHT_NOT = Not('relay 2 value')
# BUTTON_RIGHT = And(RELAY_LEFT_NOT, 'input 2 value')
# ENGINE_RIGHT = Set(BUTTON_RIGHT, 'relay 3 set_state')


ComputeMap.update({
    # RELAY_LEFT_NOT: (BUTTON_LEFT, ),
    # ENGINE_LEFT: (BUTTON_LEFT,),
    #
    # BUTTON_LEFT: (ENGINE_LEFT,),
    # BUTTON_RIGHT: (ENGINE_RIGHT,),
})




# ComputeMap.update({
# HYST_FAN: (FAN_HEATCOOL,),
# SWITCH_ON: (FAN_ONOFF, LIGHT),
#     SWITCH_HEAT: (FAN_HEATCOOL,),
#     FAN_HEATCOOL: (FAN_ONOFF,),
#     FAN_ONOFF: (PULSE_LATE, FAN_LATE,),
#     PULSE_LATE: (FAN_LATE,),
#     FAN_LATE: (PULSE_MIN, FAN_MIN,),
#     PULSE_MIN: (FAN_MIN,),
#     FAN_MIN: (FAN,),
# })
