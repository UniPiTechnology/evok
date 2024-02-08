![unipi logo](https://github.com/UniPiTechnology/evok/raw/master/www/evok/js/jquery/images/unipi-logo-short-cmyk.svg?sanitize=true "Unipi logo")

# EVOK - the Unipi API

EVOK is the primary Web-services API for [NEURON], [PATRON], [GATE] and [Unipi 1.1] devices.
It provides a RESTful interface over HTTP, a JSON-RPC interface,
a WebSocket interface and a bulk JSON interface to Unipi devices.

We have webapp for evok, see [evok-web] for more information.

Evok is still in active development, so any testing, feedback and contributions are very much welcome and appreciated.

APIs included in EVOK:

- RESTful WebForms API
- RESTful JSON API
- Bulk request JSON API
- WebSocket API
- JSON-RPC API

EVOK also supports sending notifications via webhook.

---

# Getting started
- [Installation instructions](./docs/installation.md) - How to install evok on Unipi controllers
- [Debugging](./docs/debugging.md) - How to debugging evok
- [APIs](./docs/apis.md) - List of supported evok apis
  - [REST API](./docs/apis/rest.md)
  - [JSON API](./docs/apis/json.md)
  - [BULK API](./docs/apis/bulk.md)
  - [Websocket](./docs/apis/websocket.md)
  - [RPC API](./docs/apis/rpc.md)
  - [Webhook](./docs/apis/webhook.md)
- Configurations:
  - [Evok configuration](./docs/configs/evok_configuration.md) - How to configure evok devices and apis
  - [HW_definitions](./docs/configs/hw_definitions.md) - How to configure Modbus map definitions
  - [Aliases](./docs/configs/aliases.md) - How Evok aliases works


License
============
Apache License, Version 2.0

[PUTTY]:http://www.putty.org/
[github repository]:https://github.com/UniPiTechnology/evok
[OpenSource image]:https://files.unipi.technology/s/public?path=%2FSoftware%2FOpen-Source%20Images
[IndieGogo]:https://www.indiegogo.com/projects/unipi-the-universal-raspberry-pi-add-on-board
[NEURON]:https://www.unipi.technology/products/unipi-neuron-3?categoryId=2
[PATRON]:https://www.unipi.technology/products/unipi-patron-374
[GATE]:https://www.unipi.technology/products/unipi-gate-388
[Unipi 1.1]:https://www.unipi.technology/products/unipi-1-1-1-1-lite-19?categoryId=1
[tornado]:https://pypi.python.org/pypi/tornado/
[toro]:https://pypi.python.org/pypi/toro/
[tornardorpc]:https://github.com/joshmarshall/tornadorpc
[websocket Python library]:https://pypi.python.org/pypi/websocket-client/
[our forum]:http://forum.unipi.technology/
[intructions below]:https://github.com/UniPiTechnology/evok#installing-evok-for-neuron
[jsonrpclib]:https://github.com/joshmarshall/jsonrpclib
[evok-web]:https://github.com/UniPiTechnology/evok-web

