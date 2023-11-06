import asyncio
import time
from typing import Any, Callable, Type

from pymodbus.client import AsyncModbusSerialClient
from pymodbus.datastore import ModbusServerContext
from pymodbus.datastore import ModbusSlaveContext
from pymodbus.datastore import ModbusSequentialDataBlock
from pymodbus.datastore.store import BaseModbusDataBlock
from pymodbus.device import ModbusDeviceIdentification
from pymodbus.framer import ModbusRtuFramer, ModbusFramer

#---------------------------------------------------------------------------#
# Logging
#---------------------------------------------------------------------------#
from log import *


class EvokModbusSerialClient(AsyncModbusSerialClient):
    instance_counter = 0

    def __init__(self, port: str, framer: Type[ModbusFramer] = ModbusRtuFramer, baudrate: int = 19200,
                 bytesize: int = 8, parity: str = "N", stopbits: int = 1, **kwargs: Any) -> None:
        if EvokModbusSerialClient.instance_counter > 0:
            raise Exception(f"DualAsyncModbusSerialClient: trying constructing multiple singleton object.")
        EvokModbusSerialClient.instance_counter += 1
        super().__init__(port, framer, baudrate, bytesize, parity, stopbits, **kwargs)
        for method_name in ['read_holding_registers', 'read_input_registers', 'write_register', 'write_coil']:
            setattr(self, method_name, self.__block(getattr(self, method_name)))
        self.lock = asyncio.Lock()
        self.stime = time.time()
        self.block_count = 0

    def __runtime(self):
        return int((time.time()-self.stime)*1000)

    def __block(self, operation: Callable):
        async def ret(*args, **kwargs):
            opname = str(operation).split(' of ')[0].split(' ')[-1]
            opname = opname.split('.')[1] if '.' in opname else opname
            print(f"{self.block_count}\toperation prepare:\t {self.__runtime()}  \t  {opname}  \t  ({args}  \t  {kwargs})", flush=True)
            self.block_count += 1
            async with self.lock:
                self.block_count -= 1
                print(f"{self.block_count}\toperation   start:\t {self.__runtime()}  \t  {opname}  \t  ({args}  \t  {kwargs})", flush=True)
                try:
                    aret = await operation(*args, **kwargs)
                    print(f"{self.block_count}\toperation    done:\t {self.__runtime()}  \t  {opname}  \t  ({args}  \t  {kwargs})", flush=True)
                except Exception as E:
                    print(f"{self.block_count}\toperation   error:\t {self.__runtime()}  \t  {opname}  \t  ({args}  \t  {kwargs})", flush=True)
                    await asyncio.sleep(0.03)
                    raise E
                return aret
        return ret



#---------------------------------------------------------------------------#
# Data type transformations
#---------------------------------------------------------------------------#

def float_to_32(value):
    """ convert float value into fixed exponent (16) number
        returns (int_part,frac_part)
            int_part is integer part (16 bit) of value
            frac_part is fraction part (16 bit) of value """
    value = int(round(value*0x10000,0))
    return ((value & 0xffff0000) >> 16, value & 0x0000ffff)

def float_to_16(value):
    """ convert float value into fixed exponent (8) number
        returns 16 bit integer, as value * 256
    """
    value = int(round(value*0x100,0))
    return value & 0xffff

def float_to_1000(value):
    """ convert float value into fixed exponent (8) number
        returns 16 bit integer, as value * 256
    """
    value = int(round(value*1000,0))
    return value & 0xffff


#---------------------------------------------------------------------------#
# Device handlers
#
#    sync (device, bitdatastore, registerdatastore)
#    set_bit (register_address, value, device)
#    set_reg (register_address, value, device)
#---------------------------------------------------------------------------#

class Devset(set):
    pass


class DevHandle:

    def __init__(self, max_cnt):
        self.max_cnt = max_cnt

    #@classmethod
    def get_index(self, device):
        """ maps device to modbus index """
        index = int(device.circuit)
        if 0 < index <= self.max_cnt: return index
        return 0


class RelayHandle(DevHandle):
    """ :bitoffset - position of first relay in bit_data_block
        :regoffset - position of first relay in register_data_block
        :max_cnt - max number of relays in regiser_data_block
    """

    def __init__(self, max_cnt, bitoffset, regoffset):
        self.max_cnt = max_cnt
        self.bitoffset = bitoffset
        self.regoffset = regoffset

    def join(self, index, device, proxybits, proxyregs):
        """ join handle to device
                precomputed data are stored to device object instance
                self is stored to device._modbus_handle
                device is registered to proxymaps for write_regs/write_coils functions
        """
        index -= 1   # relay are counted from 1 
        device.__modbus_mask = 1 << ((index % 16))
        device.__bitindex = index + self.bitoffset + (index / 16) # position in bit_data_block
        device.__regindex = self.regoffset + (index / 16)         # position in register_data_block
        device._modbus_handle = self 
        # can be changed by write_coil(s)
        proxybits.map[device.__bitindex] = device
        # and also by write_reg(s) - need device set (multiple devices on one register)
        devset = proxyregs.map[device.__regindex]
        if not devset:
            devset = Devset()
            devset._modbus_handle = self 
            proxyregs.map[device.__regindex] = devset
        devset.add(device)
    

    def sync(self, device, bits, regs):
        bits.setValues(device.__bitindex, device.value)
        """ set/reset bit in register store"""
        svalue = regs.getValues(device.__regindex)[0]
        if device.value:
            svalue |= device.__modbus_mask
        else:
            svalue &= ~device.__modbus_mask
        regs.setValues(device.__regindex, svalue)

    def set_bit(self, address, value, device):
        device.set_state(value)

    def set_reg(self, address, value, devicelist):
        mcps = set()
        for relay in devicelist:
            if not(relay.mcp in mcps):
                mcps.add(relay.mcp)
                relay.mcp.__newbitmap = 0
                relay.mcp.__newmask = 0
            relay.mcp.__newmask |= relay._mask
            if relay.__modbus_mask & value:
                relay.mcp.__newbitmap |= relay._mask
        for mcp in mcps:
            mcp.set_bitmap(mcp.__newmask, mcp.__newbitmap)

class InputHandle(DevHandle):
    """ :counter_regoffset - position of first counter in register_data_block
    """

    def __init__(self, max_cnt, bitoffset, regoffset, counter_regoffset):
        self.max_cnt = max_cnt
        self.bitoffset = bitoffset
        self.regoffset = regoffset
        self.counter_regoffset = counter_regoffset

    def join(self, index, device, proxybits, proxyregs):
        # one coil
        # one bit in register
        # one 32-bit counter register
        index -= 1              # counted from 1 
        device.__modbus_mask = 1 << ((index % 16))
        device.__bitindex = self.bitoffset + index + (index / 16)       # position in bit_data_block
        device.__regindex = self.regoffset + (index / 16)               # position in register_data_block
        device.__counterindex = self.counter_regoffset + (2*index)      # position of counter in register_data_block
        device.__highvalue = None
        device._modbus_handle = self 
        # counters is writeable  32bits register
        proxyregs.map[device.__counterindex] = device
        proxyregs.map[device.__counterindex+1] = device
    

    def sync(self, device, bits, regs):
        bits.setValues(device.__bitindex, device.bitvalue)
        """ set/reset bit in register store"""
        svalue = regs.getValues(device.__regindex)[0]
        if device.bitvalue: 
            svalue |= device.__modbus_mask
        else:
            svalue &= ~device.__modbus_mask
        regs.setValues(device.__regindex, svalue)
        if device.counter_mode != 'disabled' :
            regs.setValues(device.__counterindex, (device.value & 0xffff0000) >> 16)
            regs.setValues(device.__counterindex+1, device.value & 0xffff)

    def set_reg(self, address, value, device):
        """ value is 32bit, change after setting second registr """
        if device.counter_mode == 'disabled':
            return
        if address == device.__counterindex:
            device.__highvalue = value << 16
        elif not(device.__highvalue is None):
            value = device.__highvalue | value
            device.set(counter = value)
            device.__highvalue = None

class AoHandle(DevHandle):

    def __init__(self, max_cnt, bitoffset, regoffset):
        self.max_cnt = max_cnt
        self.bitoffset = bitoffset
        self.regoffset = regoffset

    def join(self, index, device, proxybits, proxyregs):
        index -= 1              # counted from 1 
        device.__regindex = self.regoffset + index       # position in register_data_block
        device._modbus_handle = self 
        #  single register to write
        proxyregs.map[device.__regindex] = device

    def sync(self, device, bits, regs):
        """ store float into 16bit register as value*1000 """
        regs.setValues(device.__regindex,float_to_1000(device.value))

    def set_reg(self, address, value, device):
        """ value is 16bit integer as voltage*1000 """
        device.set_value(float(value)/1000)


class AiHandle(DevHandle):

    def __init__(self, max_cnt, bitoffset, regoffset):
        self.max_cnt = max_cnt
        self.bitoffset = bitoffset
        self.regoffset = regoffset

    def join(self, index, device, proxybits, proxyregs):
        # one 32-bit register
        index = index - 1                             # counted from 1 
        device.__regindex = self.regoffset + 2*index  # position in register_data_block
        device._modbus_handle = self 
        #  no register to write
    
    def sync(self, device, bits, regs):
        """ store float into 2 registers
                Lower reg is int part (16 bit) of value
                Higher reg is fraction part (16 bit) of value * 65536
        """
        ival,fraction = float_to_32(device.value)
        regs.setValues(device.__regindex, ival)
        regs.setValues(device.__regindex+1, fraction)


class TempHandle(DevHandle):

    def __init__(self, max_cnt, bitoffset, regoffset):
        self.max_cnt = max_cnt
        self.bitoffset = bitoffset
        self.regoffset = regoffset

    def join(self, index, device, proxybits, proxyregs):
        # one 16-bit register
        index = index - 1   # inputs are counted from 1 
        device.__regindex = self.regoffset + (index)       # position in register_data_block
    
    def sync(self, device, bits, regs):
        """ store float into 16bit register as value*256 """
        regs.setValues(device.__regindex,float_to_16(device.value))

#----------------------------------------------------
# Proxy DataStores
#   - for actions on write_coil, write_register
#----------------------------------------------------
class ProxyDataBlock(BaseModbusDataBlock):

    def __init__(self, p_block):
        self._block = p_block
        self.map = [None] * (len(p_block.values)+1)

    @property
    def values(self):
        return self._block.values

    @property
    def address(self):
        return self._block.address

    @property
    def default_value(self):
        return self._block.default_value
    
    def validate(self, address, count=1):
        return self._block.validate(address, count)

    def getValues(self, address, count=1):
        return self._block.getValues(address, count)


class UnipiCoilBlock(ProxyDataBlock):

    def setValues(self, address, values):
        for value in values:
            try:
                device = self.map[address]
                if device:
                    device._modbus_handle.set_bit(address, value, device)
            except Exception:
                pass
            address += 1


class UnipiRegsBlock(ProxyDataBlock):

    def setValues(self, address, values):
        for value in values:
            try:
                device = self.map[address]
                if device:
                    device._modbus_handle.set_reg(address, value, device)
            except Exception:
                pass
            address += 1



class EForeigner(Exception):
    pass



class UnipiContext(ModbusServerContext):

    devicemap = {
    'relay' : (RelayHandle(8, 1, 1),),
    'input' : (InputHandle(16,9, 2, 28),),
    'ao'    : (AoHandle   (1, 0, 3),),
    'ai'    : (AiHandle   (2, 0, 4),),
    'temp'  : (TempHandle (20,0, 8),)
    }

    def __init__(self):
        bits = ModbusSequentialDataBlock(1, [0]*(8+16))
        regs = ModbusSequentialDataBlock(1, [0]*(1+1+2+2*2+20+16*2))
        proxybits = UnipiCoilBlock(bits)
        proxyregs = UnipiRegsBlock(regs)
        store = ModbusSlaveContext(di = bits, co = proxybits, 
                                   ir = regs, hr = proxyregs)
        ModbusServerContext.__init__(self,slaves=store, single=True)
        self.bits = bits
        self.regs = regs
        self.proxybits = proxybits
        self.proxyregs = proxyregs
        self.foreigners = set()

    def config_callback(self, device):
        try:
            if device in self.foreigners: return
            if not hasattr(device, '_modbus_handle'):
                # check if device is our modbus device or foreigner
                dev_type=device.full()['dev']
                try:
                    template = self.devicemap[dev_type]
                    Handle = template[0]
                    index = Handle.get_index(device)
                    if not(index): raise EForeigner("Foreigner")
                    Handle.join(index, device, self.proxybits, self.proxyregs)
                    device._modbus_handle = Handle
                except Exception as e:
                    self.foreigners.add(device)
                    raise

            self.status_callback(device)
        except (EForeigner, KeyError):
            pass
        except Exception as E:
            logger.debug(str(E))
            pass

    def status_callback(self, device):
        try:
            device._modbus_handle.sync(device, self.bits, self.regs)
        except AttributeError:
            pass
        except Exception as e :
            #print str(e)
            pass


## small version of Modbus map, limited to Gpio devices
class UnipiContextGpio(UnipiContext):

    devicemap = { # count coil-pos reg-pos  alt-reg-pos 
    'ao'    : (AoHandle   (1,      0,      1),),
    'input' : (InputHandle(14,     1,      2,      3),),
    }

identity = ModbusDeviceIdentification()
identity.VendorName  = 'Unipi Technology'
identity.ProductCode = 'Evok'
identity.VendorUrl   = 'http://unipi.technology'
identity.ProductName = 'Evok Modbus/TCP Server on Tornado'
identity.ModelName   = 'Evok Modbus'
identity.MajorMinorRevision = '1.1'
