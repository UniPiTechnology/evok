# Evok APIs

For more information see our [API documentation](https://unipitechnology.stoplight.io/docs/evok/).

Evok APIs are listening on IP `127.0.0.1` and port `8080` by default. You can change this behavior in [configuration](./configs/evok_configuration.md).

**Comparison table:**

| API                         | multiple commands per request | Recommended usage    | Communication  |
|-----------------------------|-------------------------------|----------------------|----------------|
| [REST](#rest-doc)           | ❌                             | By hand              | client to Evok |
| [JSON](#json-doc)           | ❌                             | Automated            | client to Evok |
| [WebSocket](#websocket-doc) | ❌                             | Real-time automated  | both ways      |
| [BULK](#bulk-doc)           | ✅                             | Automated            | client to Evok |
| [Webhook](#webhook-doc)     | N/A                           | Listening to changes | Evok to client |
| [RPC](#rpc-doc)             | ❌                             | Automated            | client to Evok |

## REST ([doc](./apis/rest.md))

The REST API provides a simple interface for sending and receiving data in a stateless, cacheable communications.

## JSON ([doc](./apis/json.md))

Similar to the REST API, but in JSON format.

## WebSocket ([doc](./apis/websocket.md))

The WebSocket API allows for two-way communication between the client and the server over an open connection. Evok sends changes to every connected client. A list of reflected devices can be defined. It is suitable if you need to immediately react to events in your application.

## BULK ([doc](./apis/bulk.md))

The BULK API is designed to provide an efficient way for clients to update, create or delete large amounts of data.

## Webhook ([doc](./apis/webhook.md))

The Webhook API provides a mechanism for pushing real-time updates to clients. Evok sends the changes to the specified hostname and port. A list of reflected devices can be defined. It is suitable for collecting real-time information about the application.

## RPC ([doc](./apis/rpc.md))

The RPC (Remote Procedure Call) API is used for invoking procedures, functions or methods across a network.

# Device circuit

Circuit is the identifier of a concrete entity.
It must always be unique within a device type group.
Circuit is created at the initialization of the Evok and its creation depends on the device type for which it is defined.

**Circuit creation table:**

| Device type name    | Key            | Circuit format                                  |
|---------------------|----------------|-------------------------------------------------|
| Relay               | *ro*           | <device_name\>_<count\>                         |
| Digital Output      | *do*           | <device_name\>_<count\>                         |
| Digital Input       | *di*           | <device_name\>_<count\>                         |
| Analog Output       | *ao*           | <device_name\>_<count\>                         |
| Analog Input        | *ai*           | <device_name\>_<count\>                         |
| User LED            | *led*          | <device_name\>_<count\>                         |
| Master Watchdog     | *wd*           | <device_name\>_<count\>                         |
| 1-Wire bus          | *owbus*        | <device_name\>                                  |
| 1-Wire power        | *owpower*      | <device_name\>                                  |
| Temp sensor         | *temp*         | <device_name\>_<1-Wire_address\>                |
| Non-volatile memory | *nvsave*       | <device_name\>                                  |
| Modbus slave        | *modbus_slave* | <device_name\>                                  |
| Device info         | *device_info*  | <family_name\>\_<device_name\>_<serial_number\> |
| Data point          | *data_point*   | <device_name\>_<register_address\>              |
| Modbus register     | *register*     | <device_name\>_<register_address\>              |

- <device_name\>: Name defined in [Evok configuration].
    - examples: 1, 2, 3, IAQ, xS51, xS18.
- <count\>: Sequence number (is based on the 'count' parameter in the [HW definition]).
    - examples: 01, 02, 03, 04, 05, 06, 10, 11, 12.
- <1-Wire_address\>: 1-Wire device address without dots.
    - examples: 2895DCD509000035 (28.95DCD5090000.35),
- <register_address\>: Modbus register address (is based on the 'count' parameter in the [HW definition]).
    - examples: 0, 1, 12, 1000, 1100.

[Evok configuration]:./configs/evok_configuration.md#device-configuration
[HW definition]:./configs/hw_definitions.md#modbus_features
