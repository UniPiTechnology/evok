import asyncio
import time
import traceback
from typing import Any, Callable, Type, Tuple

from pymodbus.client import AsyncModbusSerialClient, AsyncModbusTcpClient
from pymodbus.datastore import ModbusServerContext
from pymodbus.datastore import ModbusSlaveContext
from pymodbus.datastore import ModbusSequentialDataBlock
from pymodbus.datastore.store import BaseModbusDataBlock
from pymodbus.device import ModbusDeviceIdentification
from pymodbus.framer import ModbusRtuFramer, ModbusFramer, ModbusSocketFramer

#---------------------------------------------------------------------------#
# Logging
#---------------------------------------------------------------------------#
from .log import *


class EvokModbusSerialClient(AsyncModbusSerialClient):
    instance_counter = 0

    def __init__(self, port: str, framer: Type[ModbusFramer] = ModbusRtuFramer, baudrate: int = 19200,
                 bytesize: int = 8, parity: str = "N", stopbits: int = 1, **kwargs: Any) -> None:
        if EvokModbusSerialClient.instance_counter > 0:
            raise Exception(f"DualAsyncModbusSerialClient: trying constructing multiple singleton object.")
        EvokModbusSerialClient.instance_counter += 1
        super().__init__(port, framer, baudrate, bytesize, parity, stopbits, reconnect_delay=None, retries=1, **kwargs)
        for method_name in ['read_holding_registers', 'read_input_registers', 'write_register', 'write_coil', 'connect']:
            setattr(self, method_name, self.__block(getattr(self, method_name)))
        self.lock = asyncio.Lock()
        self.stime = time.time()
        self.block_count = 0

    def __runtime(self):
        return int((time.time()-self.stime)*1000)

    def __block(self, operation: Callable):
        async def ret(*args, **kwargs):
            # opname = str(operation).split(' of ')[0].split(' ')[-1]
            # opname = opname.split('.')[1] if '.' in opname else opname
            # print(f"{self.block_count}\toperation prepare:\t {self.__runtime()}  \t  {opname}  \t  ({args}  \t  {kwargs})", flush=True)
            self.block_count += 1
            async with self.lock:
                self.block_count -= 1
                # print(f"{self.block_count}\toperation   start:\t {self.__runtime()}  \t  {opname}  \t  ({args}  \t  {kwargs})", flush=True)
                try:
                    aret = await operation(*args, **kwargs)
                    # print(f"{self.block_count}\toperation    done:\t {self.__runtime()}  \t  {opname}  \t  ({args}  \t  {kwargs})", flush=True)
                    return aret
                except Exception as E:
                    # print(f"{self.block_count}\toperation   error:\t {self.__runtime()}  \t  {opname}  \t  ({args}  \t  {kwargs})", flush=True)
                    traceback.print_exc()
                    raise E
        return ret


class EvokModbusTcpClient(AsyncModbusTcpClient):
    instance_counter = 0

    def __init__(self, host: str, port: int = 502, framer: Type[ModbusFramer] = ModbusSocketFramer,
                 source_address: Tuple[str, int] = None, **kwargs: Any) -> None:
        EvokModbusTcpClient.instance_counter += 1
        super().__init__(host, port, framer, source_address, **kwargs)
        for method_name in ['read_holding_registers', 'read_input_registers', 'write_register', 'write_coil', 'connect']:
            setattr(self, method_name, self.__block(getattr(self, method_name)))
        self.lock = asyncio.Lock()
        self.stime = time.time()
        self.block_count = 0

    def __block(self, operation: Callable):
        async def ret(*args, **kwargs):
            self.block_count += 1
            async with self.lock:
                self.block_count -= 1
                try:
                    aret = await operation(*args, **kwargs)
                    return aret
                except Exception as E:
                    traceback.print_exc()
                    raise E
        return ret

