# Introduction

Evok is the primary API for accessing I/Os of [NEURON], [PATRON], [GATE] and [Unipi 1.1] devices including [Extension modules] by [Unipi technology]. Evok is a translation layer between its provided APIs and Modbus, which Unipi PLCs use, you can look at their [reference](https://kb.unipi.technology/en:sw:02-apis:02-modbus-tcp). You can also checkout [Evok API documentation](https://unipitechnology.stoplight.io/docs/evok).

It provides multiple ways to easily access the I/Os of the devices, including:

- RESTful WebForms API
- RESTful JSON API
- Bulk request JSON API
- WebSocket API
- JSON-RPC API

Besides that, Evok also supports sending notifications via webhook.

[evok-web](https://github.com/UniPiTechnology/evok-web-jq) is a simple demo web application using Evok demonstrating its usage and allowing easy control of the devices configured in Evok.

[NEURON]:https://www.unipi.technology/products/unipi-neuron-3?categoryId=2
[PATRON]:https://www.unipi.technology/products/unipi-patron-374
[GATE]:https://www.unipi.technology/products/unipi-gate-388
[Unipi 1.1]:https://www.unipi.technology/products/unipi-1-1-1-1-lite-19?categoryId=1
[Extension modules]:https://www.unipi.technology/products?category=32
[Unipi technology]:https://www.unipi.technology/
