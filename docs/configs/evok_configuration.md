# Evok configuration

Evok configuration is located in `/etc/evok/config.yaml`. The default configuration is installed by the debian package. To apply the configuration, it is necessary to restart Evok with the command `systemctl restart evok`.

## API settings

In this section you can configure address and port for APIs listening. This setting will be applied to protocols:

- [REST](../apis/rest.md)
- [JSON](../apis/json.md)
- [BULK](../apis/bulk.md)
- [RPC](../apis/rpc.md)
- [Webhook](../apis/webhook.md)
- [WebSocket](../apis/websocket.md)

!!! info

    More detailed settings of individual protocols can be found in separate sections.

### Websocket

- enabled - to enable/disable websocket API
    - options: true / false
- all_filtered - 'all' WebSocket requests will be subject to the filtering set by 'filter'
    - Options: true / false

### Webhook

- enabled - to enable/disable webhook notifications
    - Options: true / false
- address - address (with port) to which notifications should be sent
- device_mask
    - Address (with port) to which notifications should be sent
    - List of device types to notify on (written as a JSON list)
- complex_events - Evok will send POST requests with the same data as WebSocket, rather than an empty GET request

## Hardware configuration

The hardware configuration is represented by a device tree with this structure:

```yaml
comm_channels:
    <bus_name>:
        type: <bus_type>
        ....: <specific settings>
    devices:
        <device_name>:
            slave-id: <slave_id>
            model: <model_id
            scan_frequency: 50
```

#### Bus configuration:

- <bus_name\>: Your choice, but can not have duplicates!
- <bus_type\>:
    - MODBUSTCP
        - hostname: Modbus TCP hostname
        - port: Modbus TCP port (default: 502)
    - MODBUSRTU
        - port: tty device path
        - boudrate: Serial baud-rate
        - parity: Serial parity (default: 'N')
    - OWBUS
        - interval: Interval for updating values (default: 60)
        - scan_interval: Internal for scan new devices (default: 300)
        - owpower: Circuit of owpower device (for restarting bus; optional parameter)

#### Device configuration:
- <device_name\>: Under this name, the device will be available in the API. Can not have duplicates!

##### MODBUSTCP & MODBUSRTU device configuration:
- <model_id\>:
    - Defines a modbus register map.
    - Source is located in '.yaml' files in '/etc/evok/hw_definitions'.
    - examples: xS51, xS11,
    - For more information see [hw_definitions](./hw_definitions.md).
- <slave_id\>: Address of the modbus device.
- scan_frequency:
    - An optional parameter that determines how often values are read from the device.
    - Default value is 50.
      
##### OWBUS device configuration:

- type: 1W sensor type. Options: ["DS2408", "DS2406", "DS2404", "DS2413"]
- address: 1W device address

### Examples

Every example must be in section 'comm_channels'.

#### Define xS51 on /dev/ttyNS0

```yaml
RS485_1:
  type: MODBUSRTU
  port: /dev/ttyNS0
  baudrate: 19200
  parity: 'N'
  devices:
    xS51:
      slave-id: 1
      model: xS51
```

#### Define IAQ on TCP

```yaml
TCP_EXT:
  type: MODBUSTCP
  hostname: 192.168.0.54
  port: 502
  devices:
    myIAQ:
      slave-id: 1
      model: IAQ
```

## Autogen

If the Debian package `unipi-os-configurator` is installed, Evok can automatically create the hardware configuration for the running device. You can enable this feature with `autogen: true` in config. If this feature is enabled, Evok includes the file `/etc/evok/autogen.yaml`. This file contains the hardware configuration of the running device. `unipi-os-configurator` generates this file if a hardware change has been detected. You can force the creation of this file using the command:

```bash
/opt/unipi/tools/os-configurator -f
```

Autogen example:

```yaml
comm_channels:
  LOCAL_TCP:
    type: MODBUSTCP
    hostname: 127.0.0.1
    port: 502
    device_info:
      family: Neuron
      model: L533
      sn: 0
      board_count: 3
    devices:
      1:
        slave-id: 1
        model: 00
      2:
        slave-id: 2
        model: 13
      3:
        slave-id: 3
        model: 13
  OWFS:
    type: OWBUS
    interval: 10
    scan_interval: 60
    owpower: 1
```
