# Evok - the Unipi API

Evok is the primary API for accessing I/Os of [NEURON], [PATRON], [GATE] and [Unipi 1.1] devices including [Extension modules] by [Unipi technology].

It provides multiple ways to easily access the I/Os of the devices, including:

- RESTful WebForms API
- RESTful JSON API
- Bulk request JSON API
- WebSocket API
- JSON-RPC API

Besides that, Evok also supports sending notifications via webhook.

[evok-web] is a simple demo web application using Evok demonstrating its usage and allowing easy control of the devices configured in Evok.

## Documentation

Evok documentation can be found [here](https://evok.readthedocs.io/).

Our API can be found [here](https://unipitechnology.stoplight.io/docs/evok/nufpnwh01hk75-evok).

## Major changes between Evok v2 and v3

- Evok v3 is based on Python3.
- Updating Evok from v2 to v3 is unsupported.
- Migration from Debian 10 is unsupported and it's recommended to start from a fresh operating system.
- The configuration of Evok has been completely rewritten to yaml. Hardware configuration is using tree structure. See more information in the [Evok configuration](https://evok.readthedocs.io/en/latest/configs/evok_configuration/).
- Evok can communicate with more Modbus TCP servers.
- The device names in the API now match the name in the configuration. For more information see [evok configuration](https://evok.readthedocs.io/en/latest/configs/evok_configuration/).
- [Aliases](https://evok.readthedocs.io/en/latest/configs/aliases/) system of I/Os has been rewritten and are saved 5 mins after change, not immediately. Saving can be forced via API.
- Structure of the aliases configuration file has been changed. Evok automatically updates the configuration file if an old version is loaded.
- Added option 'all' instead of circuit using API (/rest/relay/all).
- RO and DO were split into separate endpoints in the API (/rest/relay & /rest/output).
- The mod switching method for AO and AI has been changed. Now the measured value and the range are not set separately, but one mode represents a combination of both properties.
- Modbus RTU durability has been improved. Loss of communication with one device will not affect the functionality of the entire bus.
- evok-web was split into separate [repository](https://github.com/UniPiTechnology/evok-web-jq) and has to be installed manually.

## Developer Note

Do you feel like contributing to Evok, or perhaps have a neat idea for an improvement to our system? Feel free to contribute to this repository.

## License

Apache License, Version 2.0

[NEURON]:https://www.unipi.technology/products/unipi-neuron-3?categoryId=2
[PATRON]:https://www.unipi.technology/products/unipi-patron-374
[GATE]:https://www.unipi.technology/products/unipi-gate-388
[Unipi 1.1]:https://www.unipi.technology/products/unipi-1-1-1-1-lite-19?categoryId=1
[Evok-web]:https://github.com/UniPiTechnology/evok-web-jq
[Extension modules]:https://www.unipi.technology/products?category=32
[Unipi technology]:https://www.unipi.technology/
