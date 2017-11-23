from pymodbus.client.sync import ModbusTcpClient as pyRtu
from pymodbus.client.sync import ModbusSerialClient as pySerial
from hwnames import hwnames


import ctypes as C
class fi(C.Union):
  _fields_ = [("i", C.c_uint),("f",C.c_float)]

def reg2_float(r1,r2):
    x = fi()
    x.i = (r2 << 16) | r1
    return x.f

def float2reg(f):
    x = fi()
    x.f = f
    return (x.i & 0xffff), (x.i >> 16)

def u32i(low, high):
    val = low | (high << 16)
    if val <= 0x7fffffff: return val
    return (val - 0x100000000)

def i32u(val):
    if val < 0: val = val + 0x100000000
    return (val & 0xffff, val >> 16)


def u2i(val):
    if val <= 0x7fff: return val
    return (val - 0x10000)

def i2u(val):
    if val >= 0: return val
    return (val + 0x10000)



class RemoteArm:

    def  __init__(self, host, unit = 1, baud = 19200, timeout = 1):
        if (host.startswith('/')):
            self.pymc=pySerial(method='rtu', port=host, baudrate=baud, timeout=timeout)
        else:
            self.pymc=pyRtu(host=host, port=502)
        self.unit = unit

    def set_speed(self, x):
        pass

    def close(self):
        self.pymc.close()


    def write_regs(self, reg, values, unit = -1):
        try:
            len(values)
            return self.pymc.write_registers(reg,values,unit=self.unit if unit==-1 else unit)
        except TypeError:
            pass
        return self.pymc.write_register(reg,values,unit=self.unit if unit==-1 else unit)

    def read_regs(self, reg, cnt, unit = -1):
        rr = self.pymc.read_holding_registers(reg,cnt,unit=self.unit if unit==-1 else unit)
        return rr.registers

    def write_coil(self, reg, val, unit = -1):
        return self.pymc.write_coil(reg,val,unit=self.unit if unit==-1 else unit)

    def reboot(self, unit = -1):
        self.pymc.write_coil(1002,1,unit=self.unit if unit==-1 else unit)

    def showver(self):
        reg = self.read_regs(1000, 4)
        ver = reg[0]
        swver = ver >> 8
        if (swver) < 4:
            hw = (ver & 0xff) >> 4
            hwver = ver & 0xf
            swsub = 0
        else:
            hw    = reg[3] >> 8
            hwver = reg[3] & 0xff
            swsub = ver & 0xff
        try:
            hwname = hwnames[hw]
        except IndexError:
            hwname = 'UNKNOWN'
        print "SW v%d.%d HW %s v%d" % (swver, swsub, hwname, hwver)
        print "hwconfig:        %d x DI, %d x DO, %d x AI, %d x AO, %d x RS485" % (reg[1] >> 8, reg[1]&0xff,reg[2]>>8,(reg[2]>>4)&0x0f,reg[2]&0x0f)

    def Vref(self):
        # find reference voltage
        rr = self.read_regs(5, 1)
        self.vr1 = rr[0]
        rr = self.read_regs(1009, 1)
        self.vr2 = rr[0]
        return 3.3*self.vr2/self.vr1

