'''
Created on 16 Oct 2017

'''

owire_get_out_schema = {
	"$schema": "http://json-schema.org/draft-04/schema#",
	"title": "Neuron_Instruction",
	"type": "object",
	"properties": {}
}

owire_get_out_example = {"dev": "temp", "circuit": "1_01", "address": "abcdefgh", "typ": "DS9999"}

owire_post_inp_schema = {
	"$schema": "http://json-schema.org/draft-04/schema#",
	"title": "Neuron_Instruction",
	"type": "object",
	"properties": {}
}

owire_post_inp_example = {}

owire_post_out_schema = {
	"$schema": "http://json-schema.org/draft-04/schema#",
	"title": "Neuron_Instruction",
	"type": "object",
	"properties": {
		"result": { "type": "object"},
		"error": { "type": "string"}
	}
}

owire_post_out_example = {"result": {"dev": "temp", "circuit": "1_01", "address": "abcdefgh", "typ": "DS9999"}}

uart_get_out_schema = {
	"$schema": "http://json-schema.org/draft-04/schema#",
	"title": "Neuron_Instruction",
    "type": "object",
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
            "type": "string"
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
}

uart_get_out_example = {
			"glob_dev_id": 1,
			"conf_value": 15,
			"stopb_modes": [
				"One",
				"Two"
			],
			"stopb_mode": "One",
			"circuit": "1_01",
			"speed_modes": [
				"2400bps",
				"4800bps",
				"9600bps",
				"19200bps",
				"38400bps",
				"57600bps",
				"115200bps"
			],
			"parity_modes": [
				"None",
				"Odd",
				"Even"
			],
			"parity_mode": "None",
			"dev": "uart",
			"speed_mode": "38400bps"
		}

uart_post_inp_schema = {
	"$schema": "http://json-schema.org/draft-04/schema#",
	"title": "Neuron_Instruction",
	"type": "object",
	"properties": {
		"conf_value": {
			"type": "number",
			"minimum": 0,
			"maximum": 65535
		},
		"parity_mode": {
			"type": "string",
			"enum": [
				"None",
				"Odd",
				"Even"
			]
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
		"stopb_mode": {
			"type": "string",
			"enum": [
				"One",
				"Two"
			]
		},
        "sw_address": {
            "type": "string"
        },
		"alias": {
			"type": "string"
		}
	}
}

uart_post_inp_example = {"parity_mode": "Even"}

uart_post_out_schema = {
	"$schema": "http://json-schema.org/draft-04/schema#",
	"title": "Neuron_Instruction",
	"type": "object",
	"properties": {
		"result": { "type": "object"},
		"error": { "type": "string"}
	}
}

uart_post_out_example = {
			"glob_dev_id": 1,
			"conf_value": 15,
			"stopb_modes": [
				"One",
				"Two"
			],
			"stopb_mode": "One",
			"circuit": "1_01",
			"speed_modes": [
				"2400bps",
				"4800bps",
				"9600bps",
				"19200bps",
				"38400bps",
				"57600bps",
				"115200bps"
			],
			"parity_modes": [
				"None",
				"Odd",
				"Even"
			],
			"parity_mode": "None",
			"dev": "uart",
			"speed_mode": "38400bps"
		}

neuron_get_out_schema = {
		"$schema": "http://json-schema.org/draft-04/schema#",
		"title": "Neuron_Instruction",
		"type": "object",
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
			}
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
	"properties": {
		"value": { "type": "string"}
	},
}

led_post_inp_example = {"value": '1'}

led_post_out_schema = {
	"$schema": "http://json-schema.org/draft-04/schema#",
	"title": "Neuron_Instruction",
	"type": "object",
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
						"counter_mode": {
							"type": "string",
							"description": "\"rising\",\"disabled\" and \"falling\" applies only to the UniPi 1.1",
							"enum": [
								"Disabled",
								"Enabled",
								"rising",
								"falling",
								"disabled"
							]
						},
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
							"maximum": 65535
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
						}
					},
					"required": [
						"dev",
						"circuit",
						"glob_dev_id"
					]
				},
				{
					"type": "object",
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
                            "type": "string"
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
		"properties": {

		}
}

json_post_out_schema = {
	"$schema": "http://json-schema.org/draft-04/schema#",
	"title": "Neuron_Instruction",
	"type": "object",
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
	"properties": {
		"value": { "type": "string"},
		"mode": {"type": "string"},
		"timeout": {"type": "string"},
		"pwm_freq": {"type": "number"},
		"pwm_duty": {"type": "number"},
		"alias": {"type": "string"}
	},
}

relay_post_inp_example = {"value": "1"}

relay_post_out_schema = {
	"$schema": "http://json-schema.org/draft-04/schema#",
	"title": "Neuron_Instruction",
	"type": "object",
	"properties": {
		"result": { "type": "number"},
		"error": { "type": "array"},
		"success": { "type": "boolean"}
	},
	"required": ["success"]
}

relay_post_out_example = {"result": 1, "success": True}

light_channel_get_out_schema = {
	"$schema": "http://json-schema.org/draft-04/schema#",
	"title": "Neuron_Instruction",
	"type": "object",
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

light_channel_get_out_example = {"scan_types": ["assigned","unassigned"], "broadcast_commands": ["recall_max_level", "recall_min_level", "off", "up", "down", "step_up", "step_down", "step_down_and_off", 
								   "turn_on_and_step_up", "DAPC", "reset", "identify_device", "DTR0", "DTR1", "DTR2"],
							    "group_commands": ["recall_max_level", "recall_min_level", "off", "up", "down", "step_up", "step_down", "step_down_and_off", 
							   "turn_on_and_step_up", "DAPC", "reset", "identify_device"], "circuit": "2_01", "dev": "light_channel", "glob_dev_id": 1}

light_channel_post_inp_schema = {
	"$schema": "http://json-schema.org/draft-04/schema#",
	"title": "Neuron_Instruction",
	"type": "object",
	"properties": {
		"broadcast_command": {
			"type": "string"
		},
		"broadcast_argument": {
			"type": "number"
		},
		"group_command": {
			"type": "string"
		},
		"group_address": {
			"type": "number",
			"minimum": 0,
			"maximum": 63
		},
		"group_argument": {
			"type": "number"
		},
		"alias": {
			"type": "string"
		},
		"scan": {
			"type": "string",
			"enum": [
				"unassigned",
				"assigned"
			]
		}
	}
}

light_channel_post_inp_example = {"alias": "abc"}

light_channel_post_out_schema = {
	"$schema": "http://json-schema.org/draft-04/schema#",
	"title": "Neuron_Instruction",
	"type": "object",
	"properties": {
		"result": { "type": "number"},
		"error": { "type": "array"},
		"success": { "type": "boolean"}
	},
	"required": ["success"]
}

light_channel_post_out_example = {"result": 1, "success": True}


ao_get_out_schema = {
	"$schema": "http://json-schema.org/draft-04/schema#",
	"title": "Neuron_Instruction",
	"type": "object",
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
	"properties": {
		"value": {
			"type": "number",
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
	"properties": {
		"mode": {
			"type": "string",
			"enum": [
				"Voltage",
				"Current",
				"Resistance"
			]
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
	"properties": {
		"result": { "type": "object"},
		"error": { "type": "array"},
	}
}

ai_post_out_example = {"result": {}}


wifi_get_out_schema = {
	"$schema": "http://json-schema.org/draft-04/schema#",
	"title": "Neuron_Instruction",
	"type": "object",
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
}

wifi_get_out_example = {"value": 0.004243475302661791, "unit": "V", "circuit": "1_01", "dev": "ai"}

wifi_post_inp_schema = {
	"$schema": "http://json-schema.org/draft-04/schema#",
	"title": "Neuron_Instruction",
	"type": "object",
	"properties": {
		"value": { "type": "string"},
		"mode": {"type": "string"}
	},
}


wifi_post_inp_example = {"value": 1}

wifi_post_out_schema = {
	"$schema": "http://json-schema.org/draft-04/schema#",
	"title": "Neuron_Instruction",
	"type": "object",
	"properties": {
		"result": { "type": "object"},
		"error": { "type": "array"},
	}
}

wifi_post_out_example = {"result": 1, "success": True}

di_get_out_schema = {
	"$schema": "http://json-schema.org/draft-04/schema#",
	"title": "Neuron_Instruction",
	"type": "object",
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
		"counter_mode": {
			"type": "string",
			"description": "\"rising\",\"disabled\" and \"falling\" applies only to the UniPi 1.1",
			"enum": [
				"Disabled",
				"Enabled",
				"rising",
				"falling",
				"disabled"
			]
		},
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
			"maximum": 65535
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
	"properties": {
		"value": { "type": "number"},
		"counter": {
			"type": "number"
		},
		"counter_mode": {
			"type": "string",
			"enum": ["disabled", "Disabled", "Enabled", "rising", "falling"]
		},
		"debounce": {"type": "number"}
	},
}

di_post_inp_example = {"value": 1}

di_post_out_schema = {
	"$schema": "http://json-schema.org/draft-04/schema#",
	"title": "Neuron_Instruction",
	"type": "object",
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
	"properties": {
		"value": {
			"type": "number"
		},
		"timeout": {
			"type": "number"
		},
		"reset": {
			"type": "number"
		},
		"nv_save": {
			"type": "number"
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
	"properties": {
		"result": { "type": "object"},
		"error": { "type": "array"},
	}
}

wd_post_out_example = {"result": {}}