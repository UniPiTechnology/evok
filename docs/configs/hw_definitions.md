# HW definitions

HW definitions is in '/etc/evok/hw_definitions/'.
Each file represents one modbus device.

# File structure

## type
The device code, which is then entered into the evok configuration.
Ideally, it matches the file name.

## modbus_register_blocks

Contains a list of modbus register groups.
These registers must be placed consecutively.
When reading the device, it is read in one command.
Each element contains the following parameters:
- start_reg
- count
- frequency

The frequency parameter represents the number by which the frequency is divided.
The actual frequency is then entered separately for each device.
Learn more in [Evok configuration](./evok_configuration.md).

### Example:
```yaml
modbus_register_blocks:
  - start_reg   : 0
    count       : 2
    frequency   : 1
  - start_reg   : 2
    count       : 3
    frequency   : 10
  - start_reg   : 5
    count       : 16
    frequency   : 1
  - start_reg   : 1000
    count       : 32
    frequency   : 5
```

## modbus_features
Contains a list of devices and their required parameters.
Each element contains the following parameters:

- type
  - Specify device type
  - You can find the supported device types below.
- count
  - Specifies the number of devices of this type.
  - Register addresses are incremented based on this number.
- ...
  - Other commands depend on the specific type of device.

Supported device types:

### DO

Documentation in progress

### RO

Documentation in progress

### DI

Documentation in progress

### AO

Documentation in progress

### BAO

Documentation in progress

### AI

Documentation in progress

### OWPOWER

Documentation in progress

### WD

Documentation in progress

### REGISTER

Documentation in progress

### UNIT_REGISTER

Documentation in progress

