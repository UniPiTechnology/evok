from .devices import *
import tornado.httpclient
import json

from .handlers_base import registered_devents


class WebhookHandler:
    def __init__(self, url, allowed_types, complex_events):
        self.http_client = tornado.httpclient.AsyncHTTPClient()
        self.url = url
        self.allowed_types = allowed_types
        self.complex_events = complex_events

    def open(self):
        logger.debug(f"New WebHook connected {self.url}")
        if not ("all" in registered_devents):
            registered_devents["all"] = set()
        registered_devents["all"].add(self)

    def on_event(self, device):
        dev_all = device.full()
        outp = []
        for single_dev in dev_all:
            if single_dev['dev'] in self.allowed_types:
                outp += [single_dev]
        try:
            if len(outp) > 0:
                if not self.complex_events:
                    self.http_client.fetch(self.url, method="GET", headers={"Content-Type": "application/json"})
                else:
                    self.http_client.fetch(self.url, method="POST", headers={"Content-Type": "application/json"},
                                           body=json.dumps(outp))
        except Exception as E:
            logger.error(f"WhHandler error in event: {E}")
            if logger.level == logging.DEBUG:
                traceback.print_exc()
