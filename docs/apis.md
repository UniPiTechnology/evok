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

Circuit is a unique identifier of a particular entity (input, output, or function) of each device.
The circuit is created automatically during initialization of Evok according to the table below.

**Circuit creation table:**

| Device type name    | Key            | Circuit format                                  | Examples                          |
|---------------------|----------------|-------------------------------------------------|-----------------------------------|
| Relay               | *ro*           | <device_name\>_<number\>                        | `2_01`, `xS11_02`                 |
| Digital Output      | *do*           | <device_name\>_<number\>                        | `1_01`, `1_02`                    |
| Digital Input       | *di*           | <device_name\>_<number\>                        | `1_01`, `xS11_02`                 |
| Analog Output       | *ao*           | <device_name\>_<number\>                        | `1_01`, `xS51_02`                 |
| Analog Input        | *ai*           | <device_name\>_<number\>                        | `1_01`, `xS51_02`                 |
| User LED            | *led*          | <device_name\>_<number\>                        | `1_01`, `2_02`                    |
| Master Watchdog     | *wd*           | <device_name\>_<number\>                        | `1_01`, `1_02`                    |
| 1-Wire bus          | *owbus*        | <device_name\>                                  | `1`                               |
| 1-Wire power        | *owpower*      | <device_name\>                                  | `1`                               |
| Temp sensor         | *temp*         | <1-Wire_address\>                               | `2895DCD509000035`                | 
| Non-volatile memory | *nvsave*       | <device_name\>                                  | `1`, `2`, `xS51`                  |
| Modbus slave        | *modbus_slave* | <device_name\>                                  | `1`, `2`, `IAQ`                   |
| Device info         | *device_info*  | <family_name\>\_<device_name\>_<serial_number\> | `Neuron_L533_0`, `Patron_S167_81` |
| Data point          | *data_point*   | <device_name\>_<register_address\>              | `IAQ_0`, `IAQ_6`, `IAQ_10`        |
| Modbus register     | *register*     | <device_name\>_<register_address\>              | `1_0`, `1_1`, `1_1000`            |

- *<device_name\>*: Name defined in [Evok configuration].
    - examples: `1`, `2`, `3`, `IAQ`, `xS51`, `xS18`.
- *<number\>*: Sequence number (is based on the 'count' parameter in the [HW definition]).
    - examples: `01`, `02`, `03`, `04`, `05`, `06`, `10`, `11`, `12`.
- *<1-Wire_address\>*: 1-Wire device address without dots.
    - examples: `2895DCD509000035` (from 1-Wire address: `28.95DCD5090000.35`),
- *<register_address\>*: Modbus register address (is based on the 'count' parameter in the [HW definition]).
    - examples: `0`, `1`, `12`, `1000`, `1100`.

[Evok configuration]:./configs/evok_configuration.md#device-configuration
[HW definition]:./configs/hw_definitions.md#modbus_features
