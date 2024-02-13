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

The default register type is 'holding'.
You can change the register type to 'input' by setting the parameter 'type' to 'input'.
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

Digital output.

#### Parameters:
  - val_reg
    - Value register address
    - bitmask
  - pwm_reg
    - PWM duty register address
  - pwm_ps_reg
    - PWM prescale register address
  - pwm_c_reg
    - PWM cycle register address
  - val_coil
    - DO coil address
  - modes
    - List of available DO modes
    - Supported: [Simple, PWM]

#### Example:
```yaml
  - type        : DO
    count       : 4
    modes       :
      - Simple
      - PWM
    val_reg     : 1
    val_coil    : 0
    pwm_reg     : 16
    pwm_ps_reg  : 1017
    pwm_c_reg   : 1018
```

### RO

Relay output.

#### Parameters:
  - val_reg
    - Value register address
    - bitmask
  - val_coil
    - RO coil address

#### Example:
```yaml
  - type        : RO
    count       : 5
    val_reg     : 1
    val_coil    : 0
```

### DI

Digital input.

#### Parameters:
  - val_reg
    - Value register address
    - bitmask
  - counter_reg
    - Counter register address
    - Double register
  - deboun_reg
    - Debounce register address
  - modes
    - List of available DI modes
    - Supported: [Simple, DirectSwitch]
  - ds_modes
    - List of available direct switch modes
    - Supported: [Simple, Inverted, Toggle]
  - direct_reg
    - Direct switch register address
  - polar_reg
    - Polarity register address
  - toggle_reg
    - Toggle register address

#### Example:
```yaml
  - type        : DI
    count       : 4
    modes       :
      - Simple
      - DirectSwitch
    ds_modes    :
      - Simple
      - Inverted
      - Toggle
    val_reg     : 0
    counter_reg : 16
    direct_reg  : 1016
    deboun_reg  : 1010
    polar_reg   : 1017
    toggle_reg  : 1018
```

### AO

Analog output.

#### Parameters:
  - val_reg
    - Value register address
  - modes 
    - List of available modes
    - Every mode must define following parameters:
      - unit
        - Measure unit
      - range
        - Min and max measure values define in array
  - mode_reg
    - Mode register address

#### Example:
```yaml
  - type        : AO
    count       : 4
    modes       :
      Voltage:
        unit: 'V'
        range: [0, 10]
    min_v       : 0
    max_v       : 10
    val_reg     : 2
```

### AI

Analog input.

#### Parameters:
- val_reg
  - Value register address
- mode_reg
    - Mode register address
- modes
  - List of available modes
  - Every mode must define following parameters:
    - value
      - Value in mode_reg
    - unit
      - Measure unit
    - range
      - Min and max measure values define in array

#### Example:
```yaml
- type        : AI
  count       : 4
  val_reg     : 6
  mode_reg    : 1019
  modes       :
    Disabled:
      value: 0
    Voltage10:
      value: 1
      unit: 'V'
      range: [0, 10]
    Voltage2V5:
      value: 2
      unit: 'V'
      range: [0, 2.5]
    Current20m:
      value: 3
      unit: 'mA'
      range: [0, 20]
    Resistance3W:
      value: 4
      unit: 'Ohm'
      range: [0, 1960]
    Resistance2W:
      value: 5
      unit: 'Ohm'
      range: [0, 100000]
```

### WD

Watchdog

#### Parameters:
- val_reg
  - Value register address
- timeout_reg
  - timeout register address
- nv_save_coil
    - nv save coil address
- reset_coil
    - reset coil address

#### Example:
```yaml
  - type        : WD
    count       : 1
    val_reg     : 6
    timeout_reg : 1008
    nv_sav_coil : 1003
    reset_coil  : 1002
```

### REGISTER

Modbus register

#### Parameters:
- start_reg
  - Start modbus register address

#### Example:
```yaml
  - type        : REGISTER
    count       : 21
    start_reg   : 0
```

### UNIT_REGISTER

Modbus unit register

#### Parameters:
- name
  - Value name
- unit
  - Value unit
- value_reg
  - Value register address
- datatype
  - value data type
  - supported: [null, float32]

#### Example:
```yaml
- type        : UNIT_REGISTER
  name        : "temperature"
  count       : 1
  value_reg   : 0
  unit        : "°C"
  datatype    : float32
```
