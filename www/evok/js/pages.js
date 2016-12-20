var pages_descr = [
    {
        name: "Main",
        shortcut: "main",
        params: [
            {
                variable: "webname",
                type: "text",
                label: "Web name"
            },
            {
                variable: "staticfiles",
                type: "text",
                label: "Static files path"
            },
            {
                variable: "secret",
                type: "text",
                label: "Secret key"
            },
            {
                variable: "port",
                type: "text",
                label: "HTTP port"
            },
            {
                variable: "enable_cors",
                type: "select",
                label: "Cross-origin HTTP(CORS)",
                values: [
                    {
                        name: "True",
                        text: "Enabled"
                    },
                    {
                        name: "False",
                        text: "Disabled"
                    }
                ]

            },
            {
                variable: "cors_domains",
                type: "text",
                label: "CORS domains"
            }
        ]
    },
    {
        name: "Edit 1Wire bus",
        shortcut: "owbus",
        params: [
            {
                variable: "circuit",
                type: "text",
                label: "Circuit number"
            },
            {
                variable: "owbus",
                type: "text",
                label: "OWFS device/server path"
            },
            {
                variable: "interval",
                type: "text",
                label: "Read interval"
            },
            {
                variable: "scan_interval",
                type: "text",
                label: "scan_interval"
            }
        ]
    },
    {
        name: "Edit 1Wire device",
        shortcut: "1wdevice",
        params: [
            {
                variable: "circuit",
                type: "text",
                label: "Circuit number"
            },
            {
                variable: "bus",
                type: "text",
                label: "1Wire bus number"
            },
            {
                variable: "address",
                type: "text",
                label: "1Wire device address"
            },
            {
                variable: "type",
                type: "select",
                label: "Device(sensor) type",
                values: [
                    {
                        name: "DS18B20",
                        text: "DS18B20"
                    },
                    {
                        name: "DS18S20",
                        text: "DS18S20"
                    },
                    {
                        name: "DS2408",
                        text: "DS2408"
                    },
                    {
                        name: "DS2406",
                        text: "DS2406"
                    }
                ]
            }
        ]
    },
    {
        name: "Edit I2C bus",
        shortcut: "i2cbus",
        params: [
            {
                variable: "circuit",
                type: "text",
                label: "Circuit number"
            },
            {
                variable: "busid",
                type: "text",
                label: "Bus id(/dev/i2c-X)"
            }
        ]
    },
    {
        name: "Edit EEPROM",
        shortcut: "eprom",
        params: [
            {
                variable: "circuit",
                type: "text",
                label: "Circuit number"
            },
            {
                variable: "i2cbus",
                type: "text",
                label: "I2C bus number"
            },
            {
                variable: "address",
                type: "text",
                label: "I2C address(hex)"
            },
            {
                variable: "size",
                type: "text",
                label: "Memory size (bytes)"
            }
        ]
    },
    {
        name: "Edit MCP23008/16",
        shortcut: "mcp",
        params: [
            {
                variable: "circuit",
                type: "text",
                label: "Circuit number"
            },
            {
                variable: "i2cbus",
                type: "text",
                label: "I2C bus number"
            },
            {
                variable: "address",
                type: "text",
                label: "I2C address(hex)"
            }
        ]
    },
    {
        name: "Edit AnalogInput Chip",
        shortcut: "aichip",
        params: [
            {
                variable: "circuit",
                type: "text",
                label: "Circuit number"
            },
            {
                variable: "i2cbus",
                type: "text",
                label: "I2C bus number"
            },
            {
                variable: "address",
                type: "text",
                label: "I2C address(hex)"
            }
        ]
    },
    {
        name: "Edit Analog Input",
        shortcut: "ai",
        params: [
            {
                variable: "circuit",
                type: "text",
                label: "Circuit number"
            },
            {
                variable: "chip",
                type: "text",
                label: "Analog input chip number"
            },
            {
                variable: "channel",
                type: "text",
                label: "AI channel"
            },
            {
                variable: "bits",
                type: "text",
                label: "AI precision(bits)"
            },
            {
                variable: "gain",
                type: "text",
                label: "AI gain"
            },
            {
                variable: "correction",
                type: "text",
                label: "AI manual correction"
            },
            {
                variable: "corr_rom",
                type: "text",
                label: "AI correction EEPROM number"
            },
            {
                variable: "corr_addr",
                type: "text",
                label: "AI correction address in EEPROM"
            },
            {
                variable: "interval",
                type: "text",
                label: "AI read interval(s)"
            }
        ]
    },
    {
        name: "Edit GPIO bus",
        shortcut: "gpiobus",
        params: [
            {
                variable: "circuit",
                type: "text",
                label: "Circuit number"
            }
        ]
    },
    {
        name: "Edit Analog Output",
        shortcut: "ao",
        params: [
            {
                variable: "circuit",
                type: "text",
                label: "Circuit number"
            },
            {
                variable: "gpiobus",
                type: "text",
                label: "GPIO bus number"
            },
            {
                variable: "frequency",
                type: "text",
                label: "PWM frequency"
            }
        ]
    },
    {
        name: "Edit PCA9685",
        shortcut: "pca9685",
        params: [
            {
                variable: "circuit",
                type: "text",
                label: "Circuit number"
            },
            {
                variable: "i2cbus",
                type: "text",
                label: "I2C bus number"
            },
            {
                variable: "address",
                type: "text",
                label: "I2C address (hex)"
            }
        ]
    },
    {
        name: "Edit 1Wire Relay",
        shortcut: "1wrelay",
        params: [
            {
                variable: "circuit",
                type: "text",
                label: "Circuit number"
            },
            {
                variable: "sensor",
                type: "text",
                label: "1Wire device number"
            },
            {
                variable: "pin",
                type: "text",
                label: "1Wire device pin"
            }
        ]
    },
    {
        name: "Edit 1Wire Input",
        shortcut: "1winput",
        params: [
            {
                variable: "circuit",
                type: "text",
                label: "Circuit number"
            },
            {
                variable: "sensor",
                type: "text",
                label: "1Wire device number"
            },
            {
                variable: "pin",
                type: "text",
                label: "1Wire device pin"
            }
        ]
    },
    {
        name: "Edit Relay",
        shortcut: "relay",
        params: [
            {
                variable: "circuit",
                type: "text",
                label: "Circuit number"
            },
            {
                variable: "mcp",
                type: "text",
                label: "MCP23008/16 number"
            },
            {
                variable: "pin",
                type: "text",
                label: "MCP23008/16 PIO pin"
            }
        ]
    },
    {
        name: "Edit Digital Input",
        shortcut: "di",
        params: [
            {
                variable: "circuit",
                type: "text",
                label: "Circuit number"
            },
            {
                variable: "gpiobus",
                type: "text",
                label: "GPIO bus number"
            },
            {
                variable: "pin",
                type: "text",
                label: "GPIO pin"
            },
            {
                variable: "debounce",
                type: "text",
                label: "Debounce time [ms]"
            },
            {
                variable: "counter_mode",
                type: "select",
                label: "Counter mode",
                values: [
                    {
                        name: "rising",
                        text: "Rising edge"
                    },
                    {
                        name: "falling",
                        text: "Falling edge"
                    },
                    {
                        name: "disabled",
                        text: "Disabled"
                    }
                ]
            }
        ]
    },
];

var syspages_descr = [
    {
        name: "SSH",
        shortcut: "ssh",
        params: [
            {
                variable: "sshenable",
                type: "select",
                label: "Service SSH enabled",
                values: [{
                        name: "True",
                        text: "Yes"
                    },{
                        name: "False",
                        text: "No"
                    }]
            },
            {
                variable: "password",
                type: "text",
                label: "Set new root password"
            },
            {
                variable: "retype",
                type: "text",
                label: "Retype password"
            }
       ]
    },
    {
        name: "Wired network",
        shortcut: "wired",
        params: [
            {
                variable: "eth0-mode",
                type: "select",
                label: "Mode",
                values: [{
                        name: "dhcp",
                        text: "DHCP"
                    },{
                        name: "static",
                        text: "Static"
                    },{
                        name: "disable",
                        text: "Disable"
                    }]
            },
            {
                variable: "eth0-address",
                type: "text",
                label: "IPv4 address"
            },
            {
                variable: "eth0-netmask",
                type: "text",
                label: "Netmask"
            }
       ]
    },
    {
        name: "Wireless network",
        shortcut: "wireless",
        params: [
            {
                variable: "wlan0-mode",
                type: "select",
                label: "Mode",
                values: [{
                        name: "dhcp",
                        text: "DHCP"
                    },{
                        name: "static",
                        text: "Static"
                    },{
                        name: "bridge",
                        text: "Bridge with wired"
                    },{
                        name: "disable",
                        text: "Disable"
                    }]
            },
            {
                variable: "wlan0-address",
                type: "text",
                label: "IPv4 address"
            },
            {
                variable: "wlan0-netmask",
                type: "text",
                label: "Netmask"
            },
            {
                variable: "wlan0-wlmode",
                type: "select",
                label: "Wl mode",
                values: [{
                        name: "station",
                        text: "Station"
                    },{
                        name: "ap",
                        text: "Wireless AP"
                    }]
            },
            {
                variable: "ssid",
                type: "text",
                label: "SSID"
            },
            {
                variable: "channel",
                type: "text",
                label: "Wl channel (1-13)"
            },
            {
                variable: "wlkey",
                type: "text",
                label: "WPA2 shared key"
            },
       ]
    }
];

