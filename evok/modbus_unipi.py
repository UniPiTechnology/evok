import asyncio
import time
from typing import Any, Callable, Type, Tuple

from pymodbus.client import AsyncModbusSerialClient, AsyncModbusTcpClient
from pymodbus.exceptions import ConnectionException
from pymodbus.framer import ModbusRtuFramer, ModbusFramer, ModbusSocketFramer

#---------------------------------------------------------------------------#
# Logging
#---------------------------------------------------------------------------#
from .log import *


class EvokModbusSerialClient(AsyncModbusSerialClient):
    def __init__(self, port: str, framer: Type[ModbusFramer] = ModbusRtuFramer, baudrate: int = 19200,
                 bytesize: int = 8, parity: str = "N", stopbits: int = 1, **kwargs: Any) -> None:
        super().__init__(port, framer, baudrate, bytesize, parity, stopbits, retries=0, **kwargs)
        for method_name in ['read_holding_registers', 'read_input_registers', 'write_register', 'write_coil']:
            setattr(self, method_name, self.__block(getattr(self, method_name)))
        self.lock = asyncio.Lock()
        self.stime = time.time()
        self.block_count = 0

    def __runtime(self):
        return int((time.time()-self.stime)*1000)

    def __block(self, operation: Callable):
        async def ret(*args, **kwargs):
            async with self.lock:
                try:
                    aret = await operation(*args, **kwargs)
                    return aret
                except ConnectionException:
                    await asyncio.sleep(self.reconnect_delay_current)
                    while not self.connected:
                        await asyncio.sleep(0.001)  # TODO
        return ret


class EvokModbusTcpClient(AsyncModbusTcpClient):
    instance_counter = 0

    def __init__(self, host: str, port: int = 502, framer: Type[ModbusFramer] = ModbusSocketFramer,
                 source_address: Tuple[str, int] = None, **kwargs: Any) -> None:
        EvokModbusTcpClient.instance_counter += 1
        super().__init__(host, port, framer, source_address, **kwargs)
        for method_name in ['read_holding_registers', 'read_input_registers', 'write_register', 'write_coil']:
            setattr(self, method_name, self.__block(getattr(self, method_name)))
        self.lock = asyncio.Lock()
        self.stime = time.time()
        self.block_count = 0

    def __block(self, operation: Callable):
        async def ret(*args, **kwargs):
            async with self.lock:
                aret = await operation(*args, **kwargs)
                return aret
        return ret

