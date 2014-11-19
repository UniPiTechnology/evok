# Evok - the UniPi API

Evok is a main API and WEB interface for the [UniPi] (Raspberry Pi universal addon) board a sucessfull [IngieGogo] project. It provides REST, JSON, and WebSocket interface to relays, digital and analog inputs, analog output.

It is still in very early development state so more testing is appreciated.

Access to GPIOs is done using the fantastic [PIGPIO] library. Make sure to install it first before use.

It also uses some other python libraries that are not installed on Raspbian by default:
* python-ow
* [tornado]
* [toro]
* modified version of [tornardorpc] available in this repo tornadorpc_evok
* [jsonrpclib]


Installation
============
Download the latest revision from our repository using git client

    git clone https://github.com/UniPiTechnology/evok
    cd evok

or using wget:

    wget https://api.github.com/repos/UniPiTechnology/evok/zipball/master
    unzip master
    cd UniPiTechnology-evok-xxxxxxx

And run the installation script

    ./install-evok.sh

To uninstall it, run the installation script which is also located in `/opt/evok/` fodler after installation

    ./uninstall-evok.sh

After the installation, do not forget to copy the content of www folder to eg. `/var/www/` (default location for searching static files).

    sudo cp -r www/ /var/

If you need to change the folder or the listening port, do it in /etc/evok.conf file.

When done simply start the daemon by executing `sudo service evok start`

The installation script also enables the I2C subsystem (if not enabled before) but the uninstallation script does not disable it back.

API examples
============
There are many options of controlling the UniPi, the easiest is using a web browser (make sure to copy the www folder to your desired location and edit evok.conf file) and them simply visit

    http://your.pi.ip.address

It will show you something like this

todo: gif

The web face is using websocket to receive all event from the UniPi and controlls the UniPi via REST api.

Examples of REST API usage:

    GET /rest/DEVICE/CIRCUIT

or

    GET /rest/DEVICE/CIRCUIT/PROPERTY

Where DEVICE can be substituted by any of these: 'relay', 'di' or 'input', 'ai' or 'analoginput, 'ao' or 'analogoutput', 'sensor',  CIRCUIT is the number of circuit (in case of 1Wire sensor, it is its address) corresponding to the number in your configuration file and PROPERTY is mostly 'value'.

Simple example using wget to get status of devices:
* `wget -qO- http://your.pi.ip.address/rest/all` returns status of all devices configured in evok.conf
* `wget -qO- http://your.pi.ip.address/rest/relay/1` returns status of relay with circuit nr. 1
* `wget -qO- http://your.pi.ip.address/rest/relay/1/value` returns whether the relay 1 is on or of (1/0)

To control a device, all requests must be sent by HTTP POST. Here is a small example of controlling a relay:
* `wget -qO- http://your.pi.ip.address/rest/relay/3 --post-data='value=1'` sets relay on
* `wget -qO- http://your.pi.ip.address/rest/relay/3 --post-data='value=0'` sets relay off

You can also control the UniPi using the [jsonrpclib]. Below is a simple example, for more information check the evok.py, and unipig.py files.

    from jsonrpclib import Server
    s=Server("http://your.pi.ip.address/rpc")
    s.relay_set(1,1)
    s.relay_get(1)
    s.relay_set(1,0)
    s.relay_get(0)
    s.ai_get(1)

Check the wsbase.js in www/js/ folder to see example of controlling the UniPi using websocket.


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

[IngieGogo]:https://www.indiegogo.com/projects/unipi-the-universal-raspberry-pi-add-on-board
[UniPi]:http://www.unipi.technology
[PIGPIO]:http://abyz.co.uk/rpi/pigpio/
[tornado]:https://pypi.python.org/pypi/tornado/
[toro]:https://pypi.python.org/pypi/toro/
[tornardorpc]:https://github.com/joshmarshall/tornadorpc
[jsonrpclib]:https://github.com/joshmarshall/jsonrpclib