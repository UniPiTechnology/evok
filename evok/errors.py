class ModbusSlaveError(Exception):
    pass

class ENoCacheRegister(ModbusSlaveError):
    pass
