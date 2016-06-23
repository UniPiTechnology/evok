# Evok - the UniPi API

Evok is a main API and WEB interface for the [UniPi] (Raspberry Pi universal addon) board a successful [IndieGogo] project. It provides REST, JSON, and WebSocket interface to relays, digital and analog inputs, analog output.

It is still in very early development state so more testing is appreciated.

Access to GPIOs is done using the fantastic [PIGPIO] library. Make sure to install it first before use.

It also uses some other python libraries that are not installed on Raspbian by default:
* python-ow
* [tornado]
* [toro]
* modified version of [tornardorpc] available in this repo tornadorpc_evok
* [jsonrpclib]

# Installation

Download the latest revision from our repository using git client

    git clone https://github.com/UniPiTechnology/evok

or using wget:

    wget https://api.github.com/repos/UniPiTechnology/evok/zipball/master
    unzip master && mv UniPiTechnology-evok* evok  

And run the installation script and follow the given instructions

    cd evok
    chmod +x install-evok.sh uninstall-evok.sh
    sudo ./install-evok.sh

To uninstall it, run the installation script which is also located in `/opt/evok/` folder after installation

    sudo ./uninstall-evok.sh


If you need to change the folder or the listening port, do it in /etc/evok.conf file.

When done, simply start the daemon by executing `sudo service evok start`

The installation script also enables the I2C subsystem (if not enabled before) but the uninstallation script does not disable it back.

# Debugging

When reporting a bug or posting questions to our [our forum] please run evok by hand. To be able to do that, first stop the service by calling

    service evok stop

and then run it manually as root user by calling
    
    /opt/evok/evok.py

and see/paste the output of the script.


# API examples

There are many options of controlling the UniPi, the easiest is using a web browser (make sure to copy the www folder to your desired location and edit evok.conf file) and them simply visit

    http://your.pi.ip.address

It will show you something like this

todo: gif

The web face is using websocket to receive all events from the UniPi and controls the UniPi via REST api.

## REST API:
### HTTP GET
To get a state of a device HTTP GET request can be send to the evok

    GET /rest/DEVICE/CIRCUIT

or

    GET /rest/DEVICE/CIRCUIT/PROPERTY

Where DEVICE can be substituted by any of these: 'relay', 'di' or 'input', 'ai' or 'analoginput, 'ao' or 'analogoutput', 'sensor',  CIRCUIT is the number of circuit (in case of 1Wire sensor, it is its address) corresponding to the number in your configuration file and PROPERTY is mostly 'value'.

### HTTP POST
Simple example using wget to get status of devices:
* `wget -qO- http://your.pi.ip.address/rest/all` returns status of all devices configured in evok.conf
* `wget -qO- http://your.pi.ip.address/rest/relay/1` returns status of relay with circuit nr. 1
* `wget -qO- http://your.pi.ip.address/rest/relay/1/value` returns whether the relay 1 is on or of (1/0)
* `wget -qO- http://your.pi.ip.address/rest/ao/1/value` returns the value of analog output
* `wget -qO- http://your.pi.ip.address/rest/ai/1/value` returns the value of analog input

To control a device, all requests must be sent by HTTP POST. Here is a small example of controlling a relay:
* `wget -qO- http://your.pi.ip.address/rest/relay/3 --post-data='value=1'` sets relay on
* `wget -qO- http://your.pi.ip.address/rest/relay/3 --post-data='value=0'` sets relay off
* `wget -qO- http://your.pi.ip.address/rest/ao/1 --post-data='value=5'` set AO to 5V 

### Websocket
Register your client at ws://your.unipi.ip.address/ws to receive status messages. Once it is connected, you can also send various commands to the UniPi
All messages in websocket are sent in JSON string format, eg. {"dev":"relay", "circuit":"1", "value":"1"} to set Relay 1 On.
Check the wsbase.js in www/js/ folder to see example of controlling the UniPi using websocket.

### Python using JsonRPC
You can also control the UniPi using Python library [jsonrpclib]. See the list of all available methods below.

    from jsonrpclib import Server
    s=Server("http://your.pi.ip.address/rpc")
    s.relay_set(1,1)
    s.relay_get(1)
    s.relay_set(1,0)
    s.relay_get(0)
    s.ai_get(1)

### Python using WebSocket

    import websocket
    import json

    url = "ws://your.unipi.ip.address/ws"

    def on_message(ws, message):
        obj = json.loads(message)
        dev = obj['dev']
        circuit = obj['circuit']
        value = obj['value']
        print message

    def on_error(ws, error):
        print error

    def on_close(ws):
        print "Connection closed"

    #receiving messages
    ws = websocket.WebSocketApp(url, on_message = on_message, on_error = on_error, on_close = on_close)
    ws.run_forever()

    #sending messages
    ws = websocket.WebSocket()
    ws.connect(url)
    ws.send('{"cmd":"set","dev":"relay","circuit":"3","value":"1"}')
    ws.close()

### Perl using JsonRPC
A simple example of controlling the UniPi via RPC
    use JSON::RPC::Client;

    use JSON::RPC::Client;

    my $client = new JSON::RPC::Client;
    my $url    = 'http://your.pi.ip.address/rpc';

    $client->prepare($url, ['relay_set']);
    $client->relay_set(1,1);

There is also a [websocket client library for Perl] to get more control.

##List of available devices:
* `relay` - relay
* `input` or `di` - digital input 
* `ai` - analog input
* `ao` - analog output
* `ee` - onboard eeprom
* `sensor` - 1wire sensor
* the rest can be found in devices.py 

##List of available methods:

* Digital Inputs
    * `input_get(circuit)` - get all information of input by circuit number
    * `input_get_value(circuit)` - get actual state f input by circuit number, returns 0=off/1=on
    * `input_set(circuit)` - sets the debounce timeout
* Relays
    * `relay_get(circuit)` - get state of relay by circuit number
    * `relay_set(circuit, value)` - set relay by circuit number according value 0=off, 1=on
    * `relay_set_for_time(circuit, value, timeout)` - set relay by circuit number according value 0=off, 1=on for time(seconds) timeout
* Analog Inputs
    * `ai_get(circuit)` - get value of analog input by circuit number
    * `input_get`
* Analog Output
    * `ao_set_value(circuit, value)` - set the value(0-10) of Analog Output by circuit number
* 1-Wire bus
    * `owbus_scan(circuit)` - force to scan 1Wire network for new devices
* 1-Wire sensors
    * `sensor_get(circuit)` - returns all information in array [value, is_lost, timestamp_of_value, scan_interval] of sensor by given circuit or 1Wire address
    * `sensor_get_value(circuit)` - returns value of a circuit by given circuit or 1Wire address

More methods can be found in the src file evok.py or owclient.py.

Todo list:
============
* authentication

Known issues/bugs
============
* todo

Development
============
Want to contribute? Have any improvements or ideas? Great! We are open to all ideas. Contact us on info at unipi DOT technology

License
============
Apache License, Version 2.0

----
Raspberry Pi is a trademark of the Raspberry Pi Foundation

[IndieGogo]:https://www.indiegogo.com/projects/unipi-the-universal-raspberry-pi-add-on-board
[UniPi]:http://www.unipi.technology
[PIGPIO]:http://abyz.co.uk/rpi/pigpio/
[tornado]:https://pypi.python.org/pypi/tornado/
[toro]:https://pypi.python.org/pypi/toro/
[tornardorpc]:https://github.com/joshmarshall/tornadorpc
[jsonrpclib]:https://github.com/joshmarshall/jsonrpclib
[websocket client library for Perl]:https://metacpan.org/pod/AnyEvent::WebSocket::Client
[websocket Python library]:https://pypi.python.org/pypi/websocket-client/
[our forum]:http://forum.unipi.technology/