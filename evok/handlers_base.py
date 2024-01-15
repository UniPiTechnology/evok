import json
from .schemas import schemas

import jsonschema
import tornado

from .devices import *
from .log import logger

SCHEMA_VALIDATE = True


class EvokWebHandlerBase(tornado.web.RequestHandler):
    def initialize(self):
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Headers", "x-requested-with")
        self.set_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')

    def _get_kw(self) -> dict:
        raise NotImplementedError("'_get_kw' not implemented!")

    # usage: GET /rest/DEVICE/CIRCUIT
    #        or
    #        GET /rest/DEVICE/CIRCUIT/PROPERTY
    @tornado.web.authenticated
    def get(self, dev, circuit, prop):
        try:
            device = Devices.by_name(dev, circuit)
            if prop:
                if prop[0] in ('_',):
                    raise Exception('Invalid property name')
                result = {prop: getattr(device, prop)}
            else:
                result = device.full()
            self.write(json.dumps(result))
        except Exception as E:
            logger.error(f"Error while processing get: {str(type(E).__name__)}: {str(E)}")
            self.write(json.dumps({'success': False, 'errors': {str(type(E).__name__): str(E)}}))
        self.finish()

    async def post(self, dev, circuit, prop):
        try:
            device = Devices.by_name(dev, circuit)
            schema, example = schemas[dev]
            kw = self._get_kw()
            if SCHEMA_VALIDATE:
                jsonschema.validate(instance=kw, schema=schema)
            result = await device.set(**kw)
            self.write(json.dumps({'success': True, 'result': result}))
        except Exception as E:
            logger.error(f"Error while processing post: {str(type(E).__name__)}: {str(E)}")
            self.write(json.dumps({'success': False, 'errors': {str(type(E).__name__): str(E)}}))
        self.set_header('Content-Type', 'application/json')
        await self.finish()

    def _get_all(self):
        result = list(map(lambda dev: dev.full(), Devices.by_int(INPUT)))
        result += map(lambda dev: dev.full(), Devices.by_int(RELAY))
        result += map(lambda dev: dev.full(), Devices.by_int(OUTPUT))
        result += map(lambda dev: dev.full(), Devices.by_int(AI))
        result += map(lambda dev: dev.full(), Devices.by_int(AO))
        result += map(lambda dev: dev.full(), Devices.by_int(SENSOR))
        result += map(lambda dev: dev.full(), Devices.by_int(LED))
        result += map(lambda dev: dev.full(), Devices.by_int(WATCHDOG))
        result += map(lambda dev: dev.full(), Devices.by_int(MODBUS_SLAVE))
        result += map(lambda dev: dev.full(), Devices.by_int(UART))
        result += map(lambda dev: dev.full(), Devices.by_int(REGISTER))
        result += map(lambda dev: dev.full(), Devices.by_int(WIFI))
        result += map(lambda dev: dev.full(), Devices.by_int(LIGHT_CHANNEL))
        result += map(lambda dev: dev.full(), Devices.by_int(UNIT_REGISTER))
        result += map(lambda dev: dev.full(), Devices.by_int(EXT_CONFIG))
        result += map(lambda dev: dev.full(), Devices.by_int(DEVICE_INFO))
        return result

    def options(self):
        self.set_status(204)
        self.finish()
