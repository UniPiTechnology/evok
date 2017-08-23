**This documentation is automatically generated.**

**Output schemas only represent `data` and not the full output; see output examples and the JSend specification.**

# /json

    Content-Type: application/json

## POST


**Input Schema**
```json
{
    "$schema": "http://json-schema.org/draft-04/schema#",
    "properties": {
        "commands": {
            "items": {
                "properties": {
                    "command": {
                        "oneOf": [
                            {
                                "properties": {
                                    "command_name": {
                                        "enum": [
                                            "probe"
                                        ],
                                        "type": "string"
                                    }
                                },
                                "required": [
                                    "command_name"
                                ],
                                "type": "object"
                            },
                            {
                                "properties": {
                                    "command_name": {
                                        "enum": [
                                            "set"
                                        ],
                                        "type": "string"
                                    },
                                    "field": {
                                        "enum": [
                                            "Register",
                                            "DO",
                                            "DI",
                                            "AO",
                                            "AI",
                                            "RO"
                                        ],
                                        "type": "string"
                                    },
                                    "field_index": {
                                        "type": "number"
                                    },
                                    "value": {
                                        "type": "number"
                                    }
                                },
                                "required": [
                                    "command_name",
                                    "field",
                                    "value"
                                ],
                                "type": "object"
                            },
                            {
                                "properties": {
                                    "command_data": {
                                        "items": {
                                            "type": "number"
                                        },
                                        "type": "array"
                                    },
                                    "command_name": {
                                        "enum": [
                                            "send"
                                        ],
                                        "type": "string"
                                    }
                                },
                                "required": [
                                    "command_name",
                                    "command_data"
                                ],
                                "type": "object"
                            }
                        ],
                        "type": "object"
                    },
                    "dev_type": {
                        "type": "number"
                    },
                    "id": {
                        "type": "number"
                    }
                },
                "required": [
                    "id",
                    "dev_type",
                    "command"
                ],
                "type": "object"
            },
            "minItems": 1,
            "type": "array",
            "uniqueItems": true
        },
        "probe_all": {
            "enum": [
                true
            ],
            "type": "boolean"
        },
        "queries": {
            "items": {
                "properties": {
                    "dev_id": {
                        "type": "number"
                    },
                    "dev_type": {
                        "type": "string"
                    },
                    "field": {
                        "enum": [
                            "Name",
                            "Features",
                            "SWVersion",
                            "HWVersion",
                            "Register",
                            "DO",
                            "DI",
                            "AO",
                            "AI",
                            "RO"
                        ],
                        "type": "string"
                    },
                    "field_index": {
                        "type": "number"
                    }
                },
                "required": [
                    "dev_id",
                    "dev_type",
                    "field"
                ],
                "type": "object"
            },
            "minItems": 1,
            "type": "array",
            "uniqueItems": true
        }
    },
    "title": "Neuron_Instruction",
    "type": "object"
}
```


**Input Example**
```json
{}
```


**Output Schema**
```json
{
    "$schema": "http://json-schema.org/draft-04/schema#",
    "properties": {
        "commands": {
            "items": {
                "properties": {
                    "command": {
                        "oneOf": [
                            {
                                "properties": {
                                    "command_name": {
                                        "enum": [
                                            "probe"
                                        ],
                                        "type": "string"
                                    }
                                },
                                "required": [
                                    "command_name"
                                ],
                                "type": "object"
                            },
                            {
                                "properties": {
                                    "command_name": {
                                        "enum": [
                                            "set"
                                        ],
                                        "type": "string"
                                    },
                                    "field": {
                                        "enum": [
                                            "Register",
                                            "DO",
                                            "DI",
                                            "AO",
                                            "AI",
                                            "RO"
                                        ],
                                        "type": "string"
                                    },
                                    "field_index": {
                                        "type": "number"
                                    },
                                    "value": {
                                        "type": "number"
                                    }
                                },
                                "required": [
                                    "command_name",
                                    "field",
                                    "value"
                                ],
                                "type": "object"
                            },
                            {
                                "properties": {
                                    "address": {
                                        "type": "number"
                                    },
                                    "command_data": {
                                        "items": {
                                            "type": "number"
                                        },
                                        "type": "array"
                                    },
                                    "command_name": {
                                        "enum": [
                                            "send"
                                        ],
                                        "type": "string"
                                    }
                                },
                                "required": [
                                    "command_name",
                                    "command_data"
                                ],
                                "type": "object"
                            }
                        ],
                        "type": "object"
                    },
                    "dev_type": {
                        "type": "number"
                    },
                    "id": {
                        "type": "number"
                    },
                    "performed": {
                        "type": "boolean"
                    }
                },
                "required": [
                    "id",
                    "dev_type",
                    "command",
                    "performed"
                ],
                "type": "object"
            },
            "minItems": 1,
            "type": "array",
            "uniqueItems": true
        },
        "probe_all": {
            "items": {
                "properties": {
                    "HWVersion": {
                        "type": "string"
                    },
                    "Name": {
                        "type": "string"
                    },
                    "SWVersion": {
                        "type": "string"
                    },
                    "dev_id": {
                        "type": "number"
                    },
                    "dev_type": {
                        "type": "string"
                    },
                    "features": {
                        "oneOf": [
                            {
                                "properties": {
                                    "field": {
                                        "enum": [
                                            "DO"
                                        ],
                                        "type": "string"
                                    },
                                    "index_major": {
                                        "type": "number"
                                    },
                                    "index_minor": {
                                        "type": "number"
                                    },
                                    "max_v": {
                                        "type": "number"
                                    },
                                    "min_v": {
                                        "type": "number"
                                    }
                                }
                            },
                            {
                                "properties": {
                                    "field": {
                                        "enum": [
                                            "DI"
                                        ],
                                        "type": "string"
                                    },
                                    "index_major": {
                                        "type": "number"
                                    },
                                    "index_minor": {
                                        "type": "number"
                                    },
                                    "max_v": {
                                        "type": "number"
                                    },
                                    "trig_v_max": {
                                        "type": "number"
                                    },
                                    "trig_v_min": {
                                        "type": "number"
                                    }
                                }
                            },
                            {
                                "properties": {
                                    "field": {
                                        "enum": [
                                            "AO"
                                        ],
                                        "type": "string"
                                    },
                                    "index_major": {
                                        "type": "number"
                                    },
                                    "index_minor": {
                                        "type": "number"
                                    },
                                    "max_a": {
                                        "type": "number"
                                    },
                                    "max_v": {
                                        "type": "number"
                                    },
                                    "min_a": {
                                        "type": "number"
                                    },
                                    "min_v": {
                                        "type": "number"
                                    },
                                    "modes": {
                                        "items": {
                                            "enum": [
                                                "Voltage",
                                                "Current"
                                            ],
                                            "type": "string"
                                        },
                                        "type": "array"
                                    }
                                }
                            },
                            {
                                "properties": {
                                    "field": {
                                        "enum": [
                                            "AI"
                                        ],
                                        "type": "string"
                                    },
                                    "index_major": {
                                        "type": "number"
                                    },
                                    "index_minor": {
                                        "type": "number"
                                    },
                                    "max_a": {
                                        "type": "number"
                                    },
                                    "max_v": {
                                        "type": "number"
                                    },
                                    "min_a": {
                                        "type": "number"
                                    },
                                    "min_v": {
                                        "type": "number"
                                    },
                                    "modes": {
                                        "items": {
                                            "enum": [
                                                "Voltage, Current"
                                            ],
                                            "type": "string"
                                        },
                                        "type": "array"
                                    }
                                }
                            },
                            {
                                "properties": {
                                    "field": {
                                        "enum": [
                                            "RO"
                                        ],
                                        "type": "string"
                                    },
                                    "index_major": {
                                        "type": "number"
                                    },
                                    "index_minor": {
                                        "type": "number"
                                    },
                                    "max_a": {
                                        "type": "number"
                                    },
                                    "max_v": {
                                        "type": "number"
                                    },
                                    "modes": {
                                        "items": {
                                            "enum": [
                                                "Simple",
                                                "Counter",
                                                "DirectSwitch"
                                            ],
                                            "type": "string"
                                        },
                                        "type": "array"
                                    }
                                }
                            },
                            {
                                "properties": {
                                    "field": {
                                        "enum": [
                                            "Sensor"
                                        ],
                                        "type": "string"
                                    },
                                    "index_major": {
                                        "type": "number"
                                    },
                                    "index_minor": {
                                        "type": "number"
                                    },
                                    "max_val": {
                                        "type": "number"
                                    },
                                    "min_val": {
                                        "type": "number"
                                    },
                                    "val_name": {
                                        "type": "string"
                                    }
                                }
                            },
                            {
                                "properties": {
                                    "end": {
                                        "type": "number"
                                    },
                                    "field": {
                                        "enum": [
                                            "Register"
                                        ],
                                        "type": "string"
                                    },
                                    "index_major": {
                                        "type": "number"
                                    },
                                    "start": {
                                        "type": "number"
                                    },
                                    "writable": {
                                        "type": "boolean"
                                    }
                                }
                            },
                            {
                                "properties": {
                                    "field": {
                                        "enum": [
                                            "Channel"
                                        ],
                                        "type": "string"
                                    },
                                    "protocol": {
                                        "enum": [
                                            "I2C",
                                            "DALI",
                                            "SPI",
                                            "RS485",
                                            "1WIRE"
                                        ],
                                        "type": "string"
                                    }
                                }
                            }
                        ],
                        "type": "object"
                    }
                },
                "type": "object"
            },
            "type": "array"
        },
        "queries": {
            "items": {
                "oneOf": [
                    {
                        "properties": {
                            "dev_id": {
                                "type": "number"
                            },
                            "dev_type": {
                                "type": "string"
                            },
                            "field": {
                                "enum": [
                                    "Name",
                                    "Features",
                                    "SWVersion",
                                    "HWVersion"
                                ],
                                "type": "string"
                            },
                            "field_index": {
                                "type": "number"
                            },
                            "performed": {
                                "type": "boolean"
                            },
                            "reply": {
                                "type": "string"
                            }
                        },
                        "required": [
                            "dev_id",
                            "dev_type",
                            "field",
                            "performed"
                        ]
                    },
                    {
                        "properties": {
                            "dev_id": {
                                "type": "number"
                            },
                            "dev_type": {
                                "type": "string"
                            },
                            "field": {
                                "enum": [
                                    "Register",
                                    "Sensor",
                                    "DO",
                                    "DI",
                                    "AO",
                                    "AI",
                                    "RO"
                                ],
                                "type": "string"
                            },
                            "field_index": {
                                "type": "number"
                            },
                            "performed": {
                                "type": "boolean"
                            },
                            "reply": {
                                "type": "number"
                            }
                        },
                        "required": [
                            "dev_id",
                            "dev_type",
                            "field",
                            "performed"
                        ]
                    },
                    {
                        "properties": {
                            "dev_id": {
                                "type": "number"
                            },
                            "dev_type": {
                                "type": "string"
                            },
                            "field": {
                                "enum": [
                                    "Channel"
                                ],
                                "type": "string"
                            },
                            "field_index": {
                                "type": "number"
                            },
                            "performed": {
                                "type": "boolean"
                            },
                            "reply": {
                                "type": "string"
                            }
                        },
                        "required": [
                            "dev_id",
                            "dev_type",
                            "field",
                            "performed"
                        ]
                    }
                ],
                "type": "object"
            },
            "minItems": 1,
            "type": "array",
            "uniqueItems": true
        }
    },
    "title": "Neuron_Reply",
    "type": "object"
}
```


**Output Example**
```json
{}
```




<br>
<br>

# /rest/all/?

    Content-Type: application/json

## GET


**Input Schema**
```json
null
```



**Output Schema**
```json
{
    "$schema": "http://json-schema.org/draft-04/schema#",
    "items": {
        "anyOf": [
            {
                "properties": {
                    "circuit": {
                        "type": "string"
                    },
                    "counter": {
                        "type": "number"
                    },
                    "counter_mode": {
                        "enum": [
                            "disabled"
                        ],
                        "type": "string"
                    },
                    "debounce": {
                        "type": "number"
                    },
                    "dev": {
                        "enum": [
                            "input"
                        ],
                        "type": "string"
                    },
                    "value": {
                        "type": "number"
                    }
                },
                "required": [
                    "dev",
                    "circuit",
                    "value",
                    "counter",
                    "counter_mode",
                    "debounce"
                ],
                "type": "object"
            },
            {
                "properties": {
                    "circuit": {
                        "type": "string"
                    },
                    "dev": {
                        "enum": [
                            "relay"
                        ],
                        "type": "string"
                    },
                    "pending": {
                        "type": "boolean"
                    },
                    "value": {
                        "type": "number"
                    }
                },
                "required": [
                    "dev",
                    "circuit",
                    "value",
                    "pending"
                ],
                "type": "object"
            },
            {
                "properties": {
                    "circuit": {
                        "type": "string"
                    },
                    "dev": {
                        "enum": [
                            "ai"
                        ],
                        "type": "string"
                    },
                    "unit": {
                        "type": "string"
                    },
                    "value": {
                        "type": "number"
                    }
                },
                "required": [
                    "dev",
                    "circuit",
                    "unit",
                    "value"
                ],
                "type": "object"
            },
            {
                "properties": {
                    "circuit": {
                        "type": "string"
                    },
                    "dev": {
                        "enum": [
                            "ao"
                        ],
                        "type": "string"
                    },
                    "unit": {
                        "type": "string"
                    },
                    "value": {
                        "type": "number"
                    }
                },
                "required": [
                    "dev",
                    "circuit",
                    "unit",
                    "value"
                ],
                "type": "object"
            }
        ]
    },
    "title": "Neuron_Instruction",
    "type": "array"
}
```


**Output Example**
```json
[
    {
        "circuit": "1_01",
        "counter": 0,
        "counter_mode": "disabled",
        "debounce": 50,
        "dev": "input",
        "value": 0
    },
    {
        "circuit": "1_02",
        "counter": 0,
        "counter_mode": "disabled",
        "debounce": 50,
        "dev": "input",
        "value": 0
    },
    {
        "circuit": "1_03",
        "counter": 0,
        "counter_mode": "disabled",
        "debounce": 50,
        "dev": "input",
        "value": 0
    },
    {
        "circuit": "1_04",
        "counter": 0,
        "counter_mode": "disabled",
        "debounce": 50,
        "dev": "input",
        "value": 0
    },
    {
        "circuit": "1_01",
        "dev": "relay",
        "pending": false,
        "value": 0
    },
    {
        "circuit": "1_02",
        "dev": "relay",
        "pending": false,
        "value": 0
    },
    {
        "circuit": "1_03",
        "dev": "relay",
        "pending": false,
        "value": 0
    },
    {
        "circuit": "1_04",
        "dev": "relay",
        "pending": false,
        "value": 0
    },
    {
        "circuit": "1_01",
        "dev": "ai",
        "unit": "V",
        "value": 0.004243475302661791
    },
    {
        "circuit": "1_02",
        "dev": "ai",
        "unit": "V",
        "value": 0.006859985867523581
    },
    {
        "circuit": "1_01",
        "dev": "ao",
        "unit": "V",
        "value": -0.0001
    }
]
```


**Notes**

aaa


