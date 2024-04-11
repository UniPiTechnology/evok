import logging

import jsonschema

from .handlers_base import registered_devents
from .mqtt_client import MqttClient, ConfigurationStructure
from .log import logger
from .devices import devtype_names, Devices
from .schemas import schemas
from tornado.ioloop import IOLoop


class MqttHandler:
    """
    Komunikator ma na starosti komunikaci pomoci mqtt. Lze do neho
    registrovat vzdy na danny topic (endpoint) svoji callback funcki,
    kterou po prijeti zpravy na tento endpoint zavola.
    Umi posilat zpravy na prislusny topic (endpoint)
    """
    KEY_IN = 'cmd'
    KEY_OUT = 'event'

    def __init__(self, conf_data: dict, loop: IOLoop):
        """
        :param conf: configuracni struktura pro nastaveni komunikatoru
        """
        if 'address' not in conf_data:
            raise ValueError("Missing broker address configuration in mqtt!")
        mqtt_conf = ConfigurationStructure(
            hostname=conf_data['address'],
            port=conf_data.get('port', 1883),
            username=conf_data.get('username', ""),
            password=conf_data.get('password', ""),
            keepalive=conf_data.get('keepalive', 60),
            qos=conf_data.get('qos', 0),
        )
        self.client_id = conf_data['client-id']
        self.__client = MqttClient(conf=mqtt_conf, client_id=self.client_id, callback=self.on_message,
                                   topic=f"{self.client_id}/{self.KEY_IN}/#")
        self.async_loop = loop

    def on_event(self, device):
        outp = []
        try:
            devices = [device]
            if hasattr(device, 'changeset'):
                devices = device.changeset
            for dev in devices:
                topic = None
                try:
                    topic = f"{self.client_id}/{self.KEY_OUT}/{devtype_names[dev.devtype]}/{dev.circuit}"
                    self.async_loop.add_callback(lambda: self.__client.send_to(topic=topic, data=dev.full()))
                except Exception as E:
                    if topic is None:
                        logger.error(f"Error while generating topic: {E}")
                    else:
                        logger.error(f"Error while sending to {topic}: {E}")
        except Exception as e:
            logger.error("Exc: %s", str(e))
            pass

    def start(self):
        logger.debug("New WebSocket client connected")
        if not ("all" in registered_devents):
            registered_devents["all"] = set()
        registered_devents["all"].add(self)
        self.__client.start(self.async_loop)

    def _on_close(self):
        pass

    async def on_message(self, topic: str, data: dict):
        # usage: <client-id>/DEVICE/CIRCUIT
        #        or
        #        <client-id>/ALL
        topic_row = str(topic)
        topic = topic.split('/')[2:]
        if len(topic) == 1:
            if topic[0].upper() == 'ALL':
                await self.__client.send_to(topic=topic_row, data={"TODO": True})
            else:
                logger.warning(f"Invalid topic: {topic}")
        elif len(topic) == 2:
            try:
                dev, circuit = topic
                device = Devices.by_name(dev, circuit)
                schema, example = schemas[dev]
                jsonschema.validate(instance=data, schema=schema)
                self.async_loop.add_callback(lambda: device.set(**data))
            except Exception as E:
                logger.error(f"{str(type(E).__name__)}: {str(E)}")
        else:
            logger.warning(f"Invalid topic: {topic}")

