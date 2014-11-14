# Evok - the UniPi API

Evok is a main API and WEB interface for the [UniPi] (Raspberry Pi universal addon) board a sucessfull [IngieGogo] project. It provides REST, JSON, and WebSocket interface to relays, digital and analog inputs, analog output.

It is still in very early development state so more testing is appreciated.

Access to GPIOs is done using the fantastic [PIGPIO] library. Make sure to install it first before use.

It also uses some other python libraries that are not installed on Raspbian by default:
* python-ow
* [tornado]
* [toro]
* modified version of [tornardorpc] available in our repo [tornadorpc-unipi]
* [jsonrpclib]


### Installation
This is a todo section but basically everything that is needed is functional I2C subsystem (guide can be found on our wiki at www.unipi.technology/wiki), following libraries, installed and running pigpiod.
The evok folder should be located in /opt/, the example configuration can be found in etc/evok.conf and should be placed in that folder.
### Todo list:
 * todo

### Known issues/bugs
* todo

### Todo list:
* automatic installation script
* authentication
* this readme 

### Development
Want to contribute? Have any improvements or ideas? Great! We are open to all ideas. Contact us on info at unipi DOT technology

### License
----
Apache License, Version 2.0


Raspberry Pi is a trademark of the Raspberry Pi Foundation

[IngieGogo]:https://www.indiegogo.com/projects/unipi-the-universal-raspberry-pi-add-on-board
[UniPi]:http://www.unipi.technology
[PIGPIO]:http://abyz.co.uk/rpi/pigpio/
[tornado]:https://pypi.python.org/pypi/tornado/
[toro]:https://pypi.python.org/pypi/toro/
[tornardorpc]:https://github.com/joshmarshall/tornadorpc
[jsonrpclib]:https://github.com/joshmarshall/jsonrpclib
[tornadorpc-unipi]:https://github.com/UniPiTechnology/tornadorpc-unipi