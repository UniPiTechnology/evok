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


Todo list:
============
 * todo

Known issues/bugs
============
* todo

Todo list:
============
* authentication

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