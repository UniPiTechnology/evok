

class ModbusCacheMap(object):

    last_comm_time = 0

    def __init__(self, modbus_reg_map, channel):
        self.modbus_reg_map = modbus_reg_map
        self.neuron = neuron
        self.sem = Semaphore(1)
        self.registered = {}
        self.frequency = {}
        for m_reg_group in modbus_reg_map:
            self.frequency[m_reg_group['start_reg']] = 10000001    # frequency less than 1/10 million are not read on start
            for index in range(m_reg_group['count']):
                if 'type' in m_reg_group and m_reg_group['type'] == 'input':
                    self.registered_input[(m_reg_group['start_reg'] + index)] = None
                else:
                    self.registered[(m_reg_group['start_reg'] + index)] = None

    def get_register(self, count, index, slave=0, is_input=False):

        def raiseifNull(val, register):
            if val!=None: return val
            raise Exception('No cached value of register %d' % register)

        try:
            if is_input:
                _slice = (raiseifNull(self.registered_input[index+i], index+1) for i in range(count))
            else:
                _slice = (raiseifNull(self.registered[index+i], index+1) for i in range(count))
            return list(_slice)
        except KeyError as E:
            raise Exception('Unknown register %d' % E.args[0])


    async def do_scan(self, slave=0, initial=False):
        if initial:
            await self.sem.acquire()
        changeset = []
        for m_reg_group in self.modbus_reg_map:
            if (self.frequency[m_reg_group['start_reg']] >= m_reg_group['frequency']) or (self.frequency[m_reg_group['start_reg']] == 0):    # only read once for every [frequency] cycles
                try:
                    val = None
                    if 'type' in m_reg_group and m_reg_group['type'] == 'input':
                        val = await self.neuron.client.read_input_registers(m_reg_group['start_reg'], m_reg_group['count'], slave=slave)
                    else:
                        val = await self.neuron.client.read_holding_registers(m_reg_group['start_reg'], m_reg_group['count'], slave=slave)
                    if not isinstance(val, ExceptionResponse) and not isinstance(val, ModbusIOException) and not isinstance(val, ExceptionResponse):
                        self.last_comm_time = time.time()
                        if 'type' in m_reg_group and m_reg_group['type'] == 'input':
                            for index in range(m_reg_group['count']):
                                if (m_reg_group['start_reg'] + index) in self.neuron.datadeps and self.registered_input[(m_reg_group['start_reg'] + index)] != val.registers[index]:
                                    for ddep in self.neuron.datadeps[m_reg_group['start_reg'] + index]:
                                        if (not ((isinstance(ddep, Input) or isinstance(ddep, ULED)))) or ddep.value_delta(val.registers[index]):
                                            changeset += [ddep]
                                self.registered_input[(m_reg_group['start_reg'] + index)] = val.registers[index]
                                self.frequency[m_reg_group['start_reg']] = 1
                        else:
                            for index in range(m_reg_group['count']):
                                if (m_reg_group['start_reg'] + index) in self.neuron.datadeps and self.registered[(m_reg_group['start_reg'] + index)] != val.registers[index]:
                                    for ddep in self.neuron.datadeps[m_reg_group['start_reg'] + index]:
                                        if (not ((isinstance(ddep, Input) or isinstance(ddep, ULED) or isinstance(ddep, Relay) or isinstance(ddep, Watchdog)))) or ddep.value_delta(val.registers[index]):
                                            changeset += [ddep]
                                self.registered[(m_reg_group['start_reg'] + index)] = val.registers[index]
                                self.frequency[m_reg_group['start_reg']] = 1
                except Exception as E:
                    logger.debug(str(E))
            else:
                self.frequency[m_reg_group['start_reg']] += 1
        if len(changeset) > 0:
            proxy = Proxy(set(changeset))
            devents.status(proxy)
        if initial:
            self.sem.release()

    async def set_register(self, count, index, inp, slave=0, is_input=False):
        if len(inp) < count:
            raise Exception('Insufficient data to write into registers')
        for counter in range(count):
            if is_input:
                if index + counter not in self.registered_input:
                    raise Exception('Unknown register %d' % index + counter)
                await self.neuron.client.write_register(index + counter, 1, inp[counter], slave=slave)
                self.registered_input[index + counter] = inp[counter]
            else:
                if index + counter not in self.registered:
                    raise Exception('Unknown register %d' % index + counter)
                await self.neuron.client.write_register(index + counter, 1, inp[counter], slave=slave)
                self.registered[index + counter] = inp[counter]

    def has_register(self, index, is_input=False):
        if is_input:
            return index not in self.registered_input
        else:
            return index not in self.registered

    async def get_register_async(self, count, index, slave=0, is_input=False):
        if is_input:
            for counter in range(index,count+index):
                if counter not in self.registered_input:
                    raise Exception('Unknown register')
            val = await self.neuron.client.read_input_registers(index, count, slave=slave)
        else:
            for counter in range(index,count+index):
                if counter not in self.registered:
                    raise Exception('Unknown register')
            val = await self.neuron.client.read_holding_registers(index, count, slave=slave)
        for counter in range(len(val.registers)):
            self.registered[index+counter] = val.registers[counter]
        return val.registers


    async def set_register_async(self, count, index, inp, slave=0, is_input=False):
        if is_input:
            if len(inp) < count:
                raise Exception('Insufficient data to write into registers')
            for counter in range(count):
                if index + counter not in self.registered_input:
                    raise Exception('Unknown register')
                await self.neuron.client.write_register(index + counter, 1, inp[counter], slave=slave)
                self.registered_input[index + counter] = inp[counter]
        else:
            if len(inp) < count:
                raise Exception('Insufficient data to write into registers')
            for counter in range(count):
                if index + counter not in self.registered:
                    raise Exception('Unknown register')
                await self.neuron.client.write_register(index + counter, 1, inp[counter], slave=slave)
                self.registered[index + counter] = inp[counter]
