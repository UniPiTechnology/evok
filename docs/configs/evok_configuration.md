# EVOK configuration

Evok configuration is in '/etc/evok/config.yaml'.
The default configuration is installed using the debian package.

To apply the configuration, it is necessary to restart evok with the command `systemctl restart evok`.


# API settings

In this section you can configure address and port for APIs listening.
This setting will be applied to protocols:
 - REST
 - JSON
 - BULK
 - RPC
 - Websocket
  
More detailed settings of individual protocols can be found in separate sections.


# Hardware configuration

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
```
 - <bus_name>: Your choice, but cannot be duplicates!
 - <bus_type>:
   - MODBUSTCP (specific settings: [hostname, port])
   - MODBUSRTU (specific settings: [port, boudrate, parity])
 - <device_name>: Under this name, the device will be available in the API. Cannot be duplicates!
 - <model_id>:
   - Defines a modbus register map.
   - Source is in '.yaml' files in '/etc/evok/hw_definitions'.
   - examples: xS51, xS11,
   - For more information see [hw_definitions](./hw_definitions.md).

## Examples

Every example must be in section 'comm_channels'.

### Define xS51 on /dev/ttyNS0
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

### Define IAQ on TCP
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

# Autogen

If the Debian package 'unipi-os-configurator' is installed,
Evok can automatically create the hardware configuration for the running device.
This feature can be enabled using the 'autogen' parameter.
When this feature is enabled, Evok includes the file '/etc/evok/autogen.yaml'.
This file contains the hardware configuration of the running device.
'unipi-os-configurator' generates this file if a hardware change has been detected.
You can force the creation of this file using the command:
```bash
/opt/unipi/tools/os-configurator -f
````
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
