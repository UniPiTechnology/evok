'''
Created on 16 Oct 2017

'''
from typing import Dict, Tuple

owire_get_out_schema = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "title": "Neuron_Instruction",
    "type": "object",
    "additionalProperties": False,
    "properties": {}
}

owire_get_out_example = {"dev": "temp", "circuit": "1_01", "address": "abcdefgh", "typ": "DS9999"}

owire_post_inp_schema = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "title": "Neuron_Instruction",
    "type": "object",
    "additionalProperties": False,
    "properties": {}
}

owire_post_inp_example = {}

owire_post_out_schema = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "title": "Neuron_Instruction",
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "result": { "type": "object"},
        "error": { "type": "string"}
    }
}

owire_post_out_example = {"result": {"dev": "temp", "circuit": "1_01", "address": "abcdefgh", "typ": "DS9999"}}


neuron_get_out_schema = {
        "$schema": "http://json-schema.org/draft-04/schema#",
        "title": "Neuron_Instruction",
        "type": "object",
    "additionalProperties": False,
    "properties": {
            "dev": {
                "type": "string",
                "enum": [
                    "neuron"
                ]
            },
            "circuit": {
                "type": "string"
            },
            "model": {
                "type": "string"
            },
            "sn": {
                "type": "number",
                "minimum": 1
            },
            "ver2": {
                "type": "string"
            },
            "board_count": {
                "type": "number"
            },
            "glob_dev_id": {
                "type": "number"
            },
            "uart_circuit": {
                "type": "string"
            },
            "uart_port": {
                "type": "string"
            },
            "alias": {
                "type": "string"
            },
            "last_comm": {}
        },
        "required": [
            "dev",
            "circuit",
            "glob_dev_id"
        ]
}

neuron_get_out_example = {"circuit": "1", "dev": "neuron", "glob_dev_id": 1}

neuron_post_inp_schema = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "title": "Neuron_Instruction",
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "print_log": {
            "type": "number",
            "minimum": 0,
            "maximum": 1
        }
    },
    "required": [
        "print_log"
    ]
}

neuron_post_inp_example = {"print_log": '1'}

neuron_post_out_schema = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "title": "Neuron_Instruction",
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "result": { "type": "number"},
        "error": { "type": "array"},
        "success": { "type": "boolean"}
    },
    "required": ["success"]
}

neuron_post_out_example = {"result": 1, "success": True}

led_get_out_schema = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "title": "Neuron_Instruction",
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "dev": {
            "type": "string",
            "enum": [
                "led"
            ]
        },
        "circuit": {
            "type": "string"
        },
        "value": {
            "type": "number",
            "minimum": 0,
            "maximum": 1
        },
        "glob_dev_id": {
            "type": "number",
            "minimum": 0
        },
        "alias": {
            "type": "string"
        }
    },
    "required": [
        "dev",
        "circuit",
        "value",
        "glob_dev_id"
    ]
}

led_get_out_example = {"circuit": "1_01", "value": 1, "dev": "led"}

led_post_inp_schema = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "title": "Neuron_Instruction",
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "value": { "type": ["boolean", "string"] },
        "alias": {"type": "string"}
    },
}

led_post_inp_example = {"value": '1'}

led_post_out_schema = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "title": "Neuron_Instruction",
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "result": { "type": "number"},
        "error": { "type": "array"},
        "success": { "type": "boolean"}
    },
    "required": ["success"]
}

led_post_out_example = {"result": 1, "success": True}

all_get_out_schema = {
    "type": "array",
    "items": {
            "anyOf": [
                {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "dev": {
                            "type": "string",
                            "enum": [
                                "input"
                            ]
                        },
                        "circuit": {
                            "type": "string"
                        },
                        "value": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": 1
                        },
                        "debounce": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": 65535
                        },
                        "counter_mode": {},
                        "counter_modes": {
                            "type": "array",
                            "description": "\"rising\",\"disabled\" and \"falling\" applies only to the UniPi 1.1",
                            "items": {
                                "type": "string",
                                "enum": [
                                    "Disabled",
                                    "Enabled",
                                    "rising",
                                    "disabled",
                                    "falling"
                                ]
                            }
                        },
                        "counter": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": 4294967295
                        },
                        "mode": {
                            "type": "string",
                            "enum": [
                                "Simple",
                                "DirectSwitch"
                            ]
                        },
                        "modes": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "enum": [
                                    "Simple",
                                    "DirectSwitch"
                                ]
                            }
                        },
                        "ds_mode": {
                            "type": "string",
                            "enum": [
                                "Simple",
                                "Inverted",
                                "Toggle"
                            ]
                        },
                        "ds_modes": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "enum": [
                                    "Simple",
                                    "Inverted",
                                    "Toggle"
                                ]
                            }
                        },
                        "glob_dev_id": {
                            "type": "number",
                            "minimum": 0
                        },
                        "alias": {
                            "type": "string"
                        },
                        "bitvalue": {
                            "description": "Only for the UniPi 1.1"
                        },
                        "time": {
                            "description": "Only for the UniPi 1.1"
                        }
                    },
                    "required": [
                        "dev",
                        "circuit",
                        "value",
                        "debounce",
                        "counter_mode",
                        "glob_dev_id"
                    ]
                },
                {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "dev": {
                            "type": "string",
                            "enum": [
                                "relay"
                            ]
                        },
                        "relay_type": {
                            "type": "string",
                            "enum": [
                                "digital",
                                "physical"
                            ]
                        },
                        "circuit": {
                            "type": "string"
                        },
                        "value": {
                            "type": "number"
                        },
                        "pending": {
                            "type": "boolean"
                        },
                        "mode": {
                            "type": "string"
                        },
                        "modes": {
                            "type": "array",
                            "items": {
                                "type": "string"
                            }
                        },
                        "glob_dev_id": {
                            "type": "number",
                            "minimum": 0
                        },
                        "pwm_freq": {
                            "type": "number",
                            "minimum": 0.1,
                            "maximum": 48000000
                        },
                        "pwm_duty": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": 100
                        },
                        "alias": {
                            "type": "string"
                        }
                    },
                    "required": [
                        "dev",
                        "circuit",
                        "value",
                        "pending",
                        "glob_dev_id"
                    ]
                },
                {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "dev": {
                            "type": "string",
                            "enum": [
                                "ai"
                            ]
                        },
                        "circuit": {
                            "type": "string"
                        },
                        "value": {
                            "type": "number"
                        },
                        "unit": {
                            "type": "string",
                            "enum": [
                                "V",
                                "mA",
                                "Ohm"
                            ]
                        },
                        "glob_dev_id": {
                            "type": "number",
                            "minimum": 0
                        },
                        "mode": {
                            "type": "string",
                            "enum": [
                                "Voltage",
                                "Current",
                                "Resistance",
                                "Simple"
                            ],
                            "description": "Simple is valid only for the UniPi 1.1"
                        },
                        "modes": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "enum": [
                                    "Voltage",
                                    "Current",
                                    "Resistance",
                                    "Simple"
                                ],
                                "description": "Simple is valid only for the UniPi 1.1"
                            }
                        },
                        "range": {
                            "type": "string",
                            "enum": [
                                "0.0",
                                "2.5",
                                "10.0",
                                "20.0",
                                "100.0",
                                "1960.0"
                            ]
                        },
                        "range_modes": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "enum": [
                                    "0.0",
                                    "2.5",
                                    "10.0",
                                    "20.0",
                                    "100.0",
                                    "1960.0"
                                ]
                            }
                        },
                        "alias": {
                            "type": "string"
                        },
                        "time": {
                            "description": "Only for the UniPi 1.1"
                        },
                        "interval": {
                            "description": "Only for the UniPi 1.1"
                        },
                        "bits": {
                            "description": "Only for the UniPi 1.1"
                        },
                        "gain": {
                            "description": "Only for the UniPi 1.1"
                        }
                    },
                    "required": [
                        "dev",
                        "circuit",
                        "value",
                        "glob_dev_id"
                    ]
                },
                {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "dev": {
                            "type": "string",
                            "enum": [
                                "ao"
                            ]
                        },
                        "circuit": {
                            "type": "string"
                        },
                        "mode": {
                            "type": "string",
                            "enum": [
                                "Voltage",
                                "Current",
                                "Resistance"
                            ]
                        },
                        "modes": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "enum": [
                                    "Voltage",
                                    "Current",
                                    "Resistance"
                                ]
                            }
                        },
                        "glob_dev_id": {
                            "type": "number",
                            "minimum": 0
                        },
                        "value": {
                            "type": "number"
                        },
                        "unit": {
                            "type": "string",
                            "enum": [
                                "V",
                                "mA",
                                "Ohm"
                            ]
                        },
                        "alias": {
                            "type": "string"
                        },
                        "frequency": {
                            "description": "Only for the UniPi 1.1"
                        }
                    },
                    "required": [
                        "dev",
                        "circuit",
                        "glob_dev_id",
                        "value"
                    ]
                },
                {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "dev": {
                            "type": "string",
                            "enum": [
                                "extension"
                            ]
                        },
                        "circuit": {
                            "type": "string"
                        },
                        "model": {
                            "type": "string",
                        },
                        "glob_dev_id": {
                            "type": "number",
                            "minimum": 1
                        },
                        "uart_port": {
                            "type": "string"
                        },
                        "last_comm": {
                            "type": "number"
                        },
                        "alias": {
                            "type": "string"
                        }
                    },
                    "required": [
                        "dev",
                        "circuit",
                        "glob_dev_id",
                        "uart_port"
                    ]
                },
                { 
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "dev": { 
                            "type": "string",
                            "enum": [
                                "ext_config"
                            ]
                        },
                        "circuit": {
                            "type": "string"
                        },
                        "address": {
                            "type": "number",
                            "minimum" : 1,
                            "maximum" : 247
                        },
                        "glob_dev_id": {
                            "type": "number",
                            "minimum": 1
                        }
                    },
                    "required": [
                        "dev",
                        "circuit",
                    ]
                },
                {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "dev": {
                            "type": "string",
                            "enum": [
                                "unit_register"
                            ]
                        },
                        "value": {
                            "type": "number"
                        },
                        "name": {
                            "type": "string",
                        },
                        "glob_dev_id": {
                            "type": "number",
                            "minimum": 1
                        },
                        "circuit": {
                            "type": "string"
                        },
                        "unit": {
                            "type": "string"
                        },
                        "alias": {
                            "type": "string"
                        }
                    },
                    "required": [
                        "dev",
                        "circuit",
                        "glob_dev_id",
                        "name",
                        "value"
                    ]
                },
                {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "dev": {
                            "type": "string",
                            "enum": [
                                "led"
                            ]
                        },
                        "circuit": {
                            "type": "string"
                        },
                        "value": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": 1
                        },
                        "glob_dev_id": {
                            "type": "number",
                            "minimum": 0
                        },
                        "alias": {
                            "type": "string"
                        }
                    },
                    "required": [
                        "dev",
                        "circuit",
                        "value",
                        "glob_dev_id"
                    ]
                },
                {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "dev": {
                            "type": "string",
                            "enum": [
                                "wd"
                            ]
                        },
                        "circuit": {
                            "type": "string"
                        },
                        "value": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": 1
                        },
                        "timeout": {
                            "type": "number",
                            "minimum": 0
                        },
                        "was_wd_reset": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": 1
                        },
                        "nv_save": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": 1
                        },
                        "glob_dev_id": {
                            "type": "number",
                            "minimum": 0
                        },
                        "alias": {
                            "type": "string"
                        }
                    },
                    "required": [
                        "dev",
                        "circuit",
                        "value",
                        "timeout",
                        "was_wd_reset",
                        "nv_save",
                        "glob_dev_id"
                    ]
                },
                {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "dev": {
                            "type": "string",
                            "enum": [
                                "neuron"
                            ]
                        },
                        "circuit": {
                            "type": "string"
                        },
                        "model": {
                            "type": "string"
                        },
                        "sn": {
                            "type": "number",
                            "minimum": 1
                        },
                        "ver2": {
                            "type": "string"
                        },
                        "board_count": {
                            "type": "number"
                        },
                        "glob_dev_id": {
                            "type": "number"
                        },
                        "uart_circuit": {
                            "type": "string"
                        },
                        "uart_port": {
                            "type": "string"
                        },
                        "alias": {
                            "type": "string"
                        },
                        "last_comm": {}
                    },
                    "required": [
                        "dev",
                        "circuit",
                        "glob_dev_id"
                    ]
                },
                {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "dev": {
                            "type": "string",
                            "enum": [
                                "register"
                            ]
                        },
                        "circuit": {
                            "type": "string"
                        },
                        "value": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": 65535
                        },
                        "glob_dev_id": {
                            "type": "number",
                            "minimum": 0
                        },
                        "alias": {
                            "type": "string"
                        }
                    },
                    "required": [
                        "dev",
                        "circuit",
                        "value",
                        "glob_dev_id"
                    ]
                },
                {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "dev": {
                            "type": "string",
                            "enum": [
                                "sensor",
                                "temp",
                                "1wdevice",
                                "ds2408",
                                "owbus"
                            ]
                        }
                    }
                },
                {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "dev": {
                            "type": "string",
                            "enum": [
                                "uart"
                            ]
                        },
                        "circuit": {
                            "type": "string"
                        },
                        "conf_value": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": 65535
                        },
                        "parity_modes": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "enum": [
                                    "Odd",
                                    "Even",
                                    "None"
                                ]
                            }
                        },
                        "parity_mode": {
                            "type": "string",
                            "enum": [
                                "Odd",
                                "Even",
                                "None"
                            ]
                        },
                        "speed_modes": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "enum": [
                                    "2400bps",
                                    "4800bps",
                                    "9600bps",
                                    "19200bps",
                                    "38400bps",
                                    "57600bps",
                                    "115200bps"
                                ]
                            }
                        },
                        "speed_mode": {
                            "type": "string",
                            "enum": [
                                "2400bps",
                                "4800bps",
                                "9600bps",
                                "19200bps",
                                "38400bps",
                                "57600bps",
                                "115200bps"
                            ]
                        },
                        "stopb_modes": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "enum": [
                                    "One",
                                    "Two"
                                ]
                            }
                        },
                        "stopb_mode": {
                            "type": "string",
                            "enum": [
                                "One",
                                "Two"
                            ]
                        },
                        "glob_dev_id": {
                            "type": "number",
                            "minimum": 0
                        },
                        "sw_address": {
                            "type": "number"
                        },
                        "alias": {
                            "type": "string"
                        }
                    },
                    "required": [
                        "dev",
                        "circuit",
                        "parity_modes",
                        "parity_mode",
                        "speed_modes",
                        "speed_mode",
                        "stopb_modes",
                        "stopb_mode",
                        "glob_dev_id"
                    ]
                },
                {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "dev": {
                            "type": "string",
                            "enum": [
                                "wifi"
                            ]
                        },
                        "circuit": {
                            "type": "string"
                        },
                        "ap_state": {
                            "type": "string",
                            "enum": [
                                "Enabled",
                                "Disabled"
                            ]
                        },
                        "eth0_masq": {
                            "type": "string",
                            "enum": [
                                "Enabled",
                                "Disabled"
                            ]
                        },
                        "glob_dev_id": {
                            "type": "number",
                            "minimum": 0
                        },
                        "alias": {
                            "type": "string"
                        }
                    },
                    "required": [
                        "dev",
                        "circuit",
                        "ap_state",
                        "eth0_masq",
                        "glob_dev_id"
                    ]
                },
                {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "dev": {
                            "type": "string",
                            "enum": [
                                "light_channel"
                            ]
                        },
                        "circuit": {
                            "type": "string"
                        },
                        "broadcast_commands": {
                            "type": "array",
                            "items": {
                                "type": [
                                    "string"
                                ],
                                "enum": [
                                    "recall_max_level",
                                    "recall_min_level",
                                    "off",
                                    "up",
                                    "down",
                                    "step_up",
                                    "step_down",
                                    "step_down_and_off",
                                    "turn_on_and_step_up",
                                    "DAPC",
                                    "reset",
                                    "identify_device",
                                    "DTR0",
                                    "DTR1",
                                    "DTR2"
                                ]
                            }
                        },
                        "group_commands": {
                            "type": "array",
                            "items": {
                                "type": [
                                    "string"
                                ],
                                "enum": [
                                    "recall_max_level",
                                    "recall_min_level",
                                    "off",
                                    "up",
                                    "down",
                                    "step_up",
                                    "step_down",
                                    "step_down_and_off",
                                    "turn_on_and_step_up",
                                    "DAPC",
                                    "reset",
                                    "identify_device"
                                ]
                            }
                        },
                        "glob_dev_id": {
                            "type": "number",
                            "minimum": 0
                        },
                        "alias": {
                            "type": "string"
                        },
                        "scan_types": {
                            "type": "array",
                            "items": {
                                "type": [
                                    "string"
                                ],
                                "enum": [
                                    "assigned",
                                    "unassigned"
                                ]
                            }
                        }
                    },
                    "required": [
                        "dev",
                        "circuit",
                        "group_commands",
                        "glob_dev_id"
                    ]
                }
            ]
        }
}

all_get_out_example = [{"circuit": "1_01", "debounce": 50, "counter": 0, "value": 0, "dev": "input", "counter_mode": "Disabled", "glob_dev_id": 1},
                          {"circuit": "1_02", "debounce": 50, "counter": 0, "value": 0, "dev": "input", "counter_mode": "Disabled", "glob_dev_id": 1},
                          {"circuit": "1_03", "debounce": 50, "counter": 0, "value": 0, "dev": "input", "counter_mode": "Disabled", "glob_dev_id": 1},
                          {"circuit": "1_04", "debounce": 50, "counter": 0, "value": 0, "dev": "input", "counter_mode": "Disabled", "glob_dev_id": 1},
                          {"value": 0, "pending": False, "circuit": "1_01", "dev": "relay", "glob_dev_id": 1},
                          {"value": 0, "pending": False, "circuit": "1_02", "dev": "relay", "glob_dev_id": 1},
                          {"value": 0, "pending": False, "circuit": "1_03", "dev": "relay", "glob_dev_id": 1},
                          {"value": 0, "pending": False, "circuit": "1_04", "dev": "relay", "glob_dev_id": 1},
                          {"value": 0.004243475302661791, "unit": "V", "circuit": "1_01", "dev": "ai", "glob_dev_id": 1},
                          {"value": 0.006859985867523581, "unit": "V", "circuit": "1_02", "dev": "ai", "glob_dev_id": 1},
                       {"value": -0.0001, "unit": "V", "circuit": "1_01", "dev": "ao", "glob_dev_id": 1}]

json_post_inp_schema = {
        "$schema": "http://json-schema.org/draft-04/schema#",
        "title": "Neuron_Instruction",
        "type": "object",
    "additionalProperties": False,
    "properties": {

        }
}

json_post_out_schema = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "title": "Neuron_Instruction",
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "group_queries": {
            "type": "array",
            "items": all_get_out_schema
        },
        "group_assignments": {
            "type": "array",
            "items": all_get_out_schema
        },
        "individual_assignments": {
            "type": "array",
            "items": all_get_out_schema
        }
    }
}

json_post_inp_example = {}

json_post_out_example = {"group_queries": [all_get_out_example]}


relay_get_out_schema = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "title": "Neuron_Instruction",
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "dev": {
            "type": "string",
            "enum": [
                "relay"
            ]
        },
        "relay_type": {
            "type": "string",
            "enum": [
                "digital",
                "physical"
            ]
        },
        "circuit": {
            "type": "string"
        },
        "value": {
            "type": "number"
        },
        "pending": {
            "type": "boolean"
        },
        "mode": {
            "type": "string"
        },
        "modes": {
            "type": "array",
            "items": {
                "type": "string"
            }
        },
        "glob_dev_id": {
            "type": "number",
            "minimum": 0
        },
        "pwm_freq": {
            "type": "number",
            "minimum": 0.1,
            "maximum": 48000000
        },
        "pwm_duty": {
            "type": "number",
            "minimum": 0,
            "maximum": 100
        },
        "alias": {
            "type": "string"
        }
    },
    "required": [
        "dev",
        "circuit",
        "value",
        "pending",
        "glob_dev_id"
    ]
}

relay_get_out_example = {"value": 0, "pending": False, "circuit": "1_01", "dev": "relay"}

relay_post_inp_schema = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "title": "Neuron_Instruction",
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "value": { "type": ["boolean", "string"] },
        "mode": {"type": "string"},
        "timeout": {"type": "string"},
        "pwm_freq": {"type": ["number", "string"]},
        "pwm_duty": {"type": ["number", "string"]},
        "alias": {"type": "string"}
    },
}

relay_post_inp_example = {"value": "1"}

relay_post_out_schema = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "title": "Neuron_Instruction",
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "result": { "type": "number"},
        "error": { "type": "array"},
        "success": { "type": "boolean"}
    },
    "required": ["success"]
}

relay_post_out_example = {"result": 1, "success": True}


ao_get_out_schema = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "title": "Neuron_Instruction",
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "dev": {
            "type": "string",
            "enum": [
                "ao"
            ]
        },
        "circuit": {
            "type": "string"
        },
        "mode": {
            "type": "string",
            "enum": [
                "Voltage",
                "Current",
                "Resistance"
            ]
        },
        "modes": {
            "type": "array",
            "items": {
                "type": "string",
                "enum": [
                    "Voltage",
                    "Current",
                    "Resistance"
                ]
            }
        },
        "glob_dev_id": {
            "type": "number",
            "minimum": 0
        },
        "value": {
            "type": "number"
        },
        "unit": {
            "type": "string",
            "enum": [
                "V",
                "mA",
                "Ohm"
            ]
        },
        "alias": {
            "type": "string"
        },
        "frequency": {
            "description": "Only for the UniPi 1.1"
        }
    },
    "required": [
        "dev",
        "circuit",
        "glob_dev_id",
        "value"
    ]
}

ao_get_out_example = {"value": -0.0001, "unit": "V", "circuit": "1_01", "dev": "ao"}

ao_post_inp_schema = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "title": "Neuron_Instruction",
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "value": {
            "type": ["string", "number"],
            "minimum": 0
        },
        "mode": {
            "type": "string",
            "enum": [
                "Voltage",
                "Current",
                "Resistance"
            ]
        },
        "alias": {
            "type": "string"
        },
        "frequency": {
            "description": "Only for the UniPi 1.1"
        }
    }
}

ao_post_inp_example = {"value": 1}

ao_post_out_schema = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "title": "Neuron_Instruction",
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "result": { "type": "number"},
        "error": { "type": "array"},
        "success": { "type": "boolean"}
    },
    "required": ["success"]
}

ao_post_out_example = {"result": 1, "success": True}

ai_get_out_schema = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "title": "Neuron_Instruction",
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "dev": {
            "type": "string",
            "enum": [
                "ai"
            ]
        },
        "circuit": {
            "type": "string"
        },
        "value": {
            "type": "number"
        },
        "unit": {
            "type": "string",
            "enum": [
                "V",
                "mA",
                "Ohm"
            ]
        },
        "glob_dev_id": {
            "type": "number",
            "minimum": 0
        },
        "mode": {
            "type": "string",
            "enum": [
                "Voltage",
                "Current",
                "Resistance",
                "Simple"
            ],
            "description": "Simple is only valid for the UniPi 1.1"
        },
        "modes": {
            "type": "array",
            "items": {
                "type": "string",
                "enum": [
                    "Voltage",
                    "Current",
                    "Resistance",
                    "Simple"
                ],
                "description": "Simple is only valid for the UniPi 1.1"
            }
        },
        "range": {
            "type": "string",
            "enum": [
                "0.0",
                "2.5",
                "10.0",
                "20.0",
                "100.0",
                "1960.0"
            ]
        },
        "range_modes": {
            "type": "array",
            "items": {
                "type": "string",
                "enum": [
                    "0.0",
                    "2.5",
                    "10.0",
                    "20.0",
                    "100.0",
                    "1960.0"
                ]
            }
        },
        "alias": {
            "type": "string"
        },
        "time": {
            "description": "Only for the UniPi 1.1"
        },
        "interval": {
            "description": "Only for the UniPi 1.1"
        },
        "bits": {
            "description": "Only for the UniPi 1.1"
        },
        "gain": {
            "description": "Only for the UniPi 1.1"
        }
    },
    "required": [
        "dev",
        "circuit",
        "value",
        "glob_dev_id"
    ]
}

ai_get_out_example = {"value": 0.004243475302661791, "unit": "V", "circuit": "1_01", "dev": "ai"}

ai_post_inp_schema = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "title": "Neuron_Instruction",
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "mode": {
            "type": "string",
            "enum": [
                "Voltage",
                "Current",
                "Resistance",
                "Simple"
            ],
            "description": "Simple is only valid for the UniPi 1.1"
        },
        "range": {
            "type": "string",
            "enum": [
                "0.0",
                "2.5",
                "10.0",
                "20.0",
                "100.0",
                "1960.0"
            ]
        },
        "alias": {
            "type": "string"
        },
        "bits": {
            "description": "Only for the UniPi 1.1"
        },
        "gain": {
            "description": "Only for the UniPi 1.1"
        },
        "interval": {
            "description": "Only for the UniPi 1.1"
        }
    }
}

ai_post_inp_example = {"mode": "Voltage"}

ai_post_out_schema = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "title": "Neuron_Instruction",
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "result": { "type": "object"},
        "error": { "type": "array"},
    }
}

ai_post_out_example = {"result": {}}


di_get_out_schema = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "title": "Neuron_Instruction",
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "dev": {
            "type": "string",
            "enum": [
                "input"
            ]
        },
        "circuit": {
            "type": "string"
        },
        "value": {
            "type": "number",
            "minimum": 0,
            "maximum": 1
        },
        "debounce": {
            "type": "number",
            "minimum": 0,
            "maximum": 65535
        },
        "counter_mode": {},
        "counter_modes": {
            "type": "array",
            "description": "\"rising\",\"disabled\" and \"falling\" applies only to the UniPi 1.1",
            "enum": [
                "Disabled",
                "Enabled",
                "rising",
                "disabled",
                "falling"
            ],
            "items": {
                "type": "string"
            }
        },
        "counter": {
            "type": "number",
            "minimum": 0,
            "maximum": 4294967295
        },
        "mode": {
            "type": "string",
            "enum": [
                "Simple",
                "DirectSwitch"
            ]
        },
        "modes": {
            "type": "array",
            "enum": [
                "Simple",
                "DirectSwitch"
            ],
            "items": {
                "type": "string"
            }
        },
        "ds_mode": {
            "type": "string",
            "enum": [
                "Simple",
                "Inverted",
                "Toggle"
            ]
        },
        "ds_modes": {
            "type": "array",
            "enum": [
                "Simple",
                "Inverted",
                "Toggle"
            ],
            "items": {
                "type": "string"
            }
        },
        "glob_dev_id": {
            "type": "number",
            "minimum": 0
        },
        "alias": {
            "type": "string"
        },
        "bitvalue": {
            "description": "Only for the UniPi 1.1"
        },
        "time": {
            "description": "Only for the UniPi 1.1"
        }
    },
    "required": [
        "dev",
        "circuit",
        "value",
        "debounce",
        "counter_mode",
        "counter",
        "glob_dev_id"
    ]
}

di_get_out_example = {"circuit": "1_01", "debounce": 50, "counter": 0, "value": 0, "dev": "input", "counter_mode": "disabled"}

di_post_inp_schema = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "title": "Neuron_Instruction",
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "value": { "type": ["number", "string"]},
        "counter": {
            "type": ["number", "string"],
            "minimum": 0,
            "maximum": 4294967295
        },
        "counter_mode": {},
        "debounce": {"type": ["number", "string"]},
        "mode": {"type": "string"},
        "alias": {"type": "string"}
    },
}

di_post_inp_example = {"value": 1}

di_post_out_schema = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "title": "Neuron_Instruction",
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "result": { "type": "object"},
        "error": { "type": "array"},
    }
}

di_post_out_example = {"result": {}}

register_get_out_schema = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "title": "Neuron_Instruction",
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "dev": {
            "type": "string",
            "enum": [
                "register"
            ]
        },
        "circuit": {
            "type": "string"
        },
        "value": {
            "type": "number",
            "minimum": 0,
            "maximum": 65535
        },
        "glob_dev_id": {
            "type": "number",
            "minimum": 0
        },
        "alias": {
            "type": "string"
        }
    },
    "required": [
        "dev",
        "circuit",
        "value",
        "glob_dev_id"
    ]
}

register_get_out_example = {"circuit": "1_01", "value": 1, "dev": "register", "glob_dev_id": 1}

register_post_inp_schema = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "title": "Neuron_Instruction",
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "value": {
            "type": "number",
            "minimum": 0,
            "maximum": 65535
        },
        "alias": {
            "type": "string"
        }
    }
}

register_post_inp_example = {"value": '1'}

register_post_out_schema = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "title": "Neuron_Instruction",
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "result": { "type": "object"},
        "error": { "type": "array"},
    }
}

register_post_out_example = {"result": {}}


wd_get_out_schema = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "title": "Neuron_Instruction",
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "dev": {
            "type": "string",
            "enum": [
                "wd"
            ]
        },
        "circuit": {
            "type": "string"
        },
        "value": {
            "type": ["number", "string"],
            "minimum": 0,
            "maximum": 1
        },
        "timeout": {
            "type": ["number", "string"],
            "minimum": 0
        },
        "was_wd_reset": {
            "type": ["number", "string"],
            "minimum": 0,
            "maximum": 1
        },
        "nv_save": {
            "type": ["number", "string"],
            "minimum": 0,
            "maximum": 1
        },
        "glob_dev_id": {
            "type": "number",
            "minimum": 0
        },
        "alias": {
            "type": "string"
        }
    },
    "required": [
        "dev",
        "circuit",
        "value",
        "timeout",
        "was_wd_reset",
        "nv_save",
        "glob_dev_id"
    ]
}

wd_get_out_example = {
                      "circuit": "1_01",
                      "value": 0,
                      "glob_dev_id": 1,
                      "dev": "wd",
                      "timeout": 5000,
                      "was_wd_reset": 0,
                        "nv_save": 0
}

wd_post_inp_schema = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "title": "Neuron_Instruction",
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "value": {
            "type": ["string", "number"]
        },
        "timeout": {
            "type": ["string", "number"]
        },
        "reset": {
            "type": ["string", "number"]
        },
        "nv_save": {
            "type": ["string", "number"]
        },
        "alias": {
            "type": "string"
        }
    }
}

wd_post_inp_example = {"value": '1'}

wd_post_out_schema = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "title": "Neuron_Instruction",
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "result": { "type": "object"},
        "error": { "type": "array"},
    }
}

wd_post_out_example = {"result": {}}


owbus_get_out_schema = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "title": "Neuron_Instruction",
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "dev": {
            "type": "string",
            "enum": [
                "owbus"
            ]
        },
        "circuit": {
            "type": "string"
        },
        "bus": {
            "type": "string",
        },
        "interval": {
            "type": "number",
            "minimum": 0
        },
        "scan_interval": {
            "type": "number",
            "minimum": 0
        },
        "do_scan": {
            "type": "boolean",
        }
    },
    "required": [
        "dev",
        "circuit",
        "bus",
        "interval",
        "scan_interval",
        "do_scan"
    ]
}

owbus_get_out_example = {
                      "bus": "/dev/i2c-0",
                      "interval": 3.0,
                      "scan_interval": 120.0,
                      "dev": "owbus",
                      "circuit": 1,
                      "do_scan": False
}

owbus_post_inp_schema = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "title": "Neuron_Instruction",
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "do_scan": {
            "type": "boolean"
        },
        "do_reset": {
            "type": "boolean"
        },
        "interval": {
            "type": ["number", "string"]
        },
        "scan_interval": {
            "type": ["number", "string"]
        },
        "circuit": {
            "type": "string"
        }
    }
}

owbus_post_inp_example = {"do_reset": True, "do_scan": True}

owbus_post_out_schema = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "title": "Neuron_Instruction",
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "result": { "type": "object",
            "properties" : {"bus" : {"type": "string"},
                              "interval" : {"type": "number"},
                             "scan_interval" : {"type": "number"},
                             "do_scan" : {"type": "boolean"}
                            }
        }
    }
}

owbus_post_out_example = {"result": {"bus": "/dev/i2c-0", "interval": 300.0, "dev": "owbus", "scan_interval": 0.0, "reset_bus": False, "circuit": "1", "do_scan": False}}


schemas: Dict[str, Tuple[dict, dict]] = {
    'input': (di_post_inp_schema, di_post_inp_example),
    'output': (relay_post_inp_schema, relay_post_inp_example),
    'register': (register_post_inp_schema, register_post_inp_example),
    'ai': (ai_post_inp_schema, ai_post_inp_example),
    'ao': (ao_post_inp_schema, ao_post_inp_example),
    'led': (led_post_inp_schema, led_post_inp_example),
    'watchdog': (wd_post_inp_schema, wd_post_inp_example),
    '1wdevice': (owire_post_inp_schema, owire_post_inp_example),
    'owbus': (owbus_post_inp_schema, owbus_post_inp_example),
}
schemas['di'] = schemas['input']
schemas['do'] = schemas['output']
schemas['relay'] = schemas['output']
schemas['analoginput'] = schemas['ai']
schemas['analogoutput'] = schemas['ao']
schemas['wd'] = schemas['watchdog']
schemas['temp'] = schemas['1wdevice']
schemas['sensor'] = schemas['1wdevice']
