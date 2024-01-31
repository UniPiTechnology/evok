![unipi logo](https://github.com/UniPiTechnology/evok/raw/master/www/evok/js/jquery/images/unipi-logo-short-cmyk.svg?sanitize=true "UniPi logo")

# EVOK - the Unipi API

EVOK is the primary Web-services API for [NEURON], [PATRON] and [UniPi 1.1] devices.
It provides a RESTful interface over HTTP, a JSON-RPC interface,
a WebSocket interface a SOAP interface and a bulk JSON interface to UniPi devices.

We have webapp for evok, see [evok-web] for more information.

Evok is still in active development, so any testing, feedback and contributions are very much welcome and appreciated.

APIs included in EVOK:

- RESTful WebForms API
- RESTful JSON API
- Bulk request JSON API
- WebSocket API
- JSON-RPC API

EVOK also supports sending notifications via webhook.

### For more information see our documentation at [api-docs.io].

## Installation process on Unipi PLCs using pre-build OS images (recommended)

The latest images for Unipi controllers can be downloaded from:

[Unipi.technology Knowledge Base](https://kb.unipi.technology/en:files:software:os-images:)

*NOTE: In Node-RED OS is evok preinstalled. 

All necessary APT Unipi repositories are already preconfigured in the OS images.
Therefore, all that's required is to login to the PLC via SSH
(there is a large number of clients you can use, for windows we recommend using [PUTTY]).
The default username for our images is "unipi" and the default password is "unipi.technology".

```bash
sudo su
apt-get update
apt-get install evok
systemctl enable evok
reboot
```

It is possible that some (or all) of the above steps will already have been finished previously.
In that case simply continue on with the next steps.
Performing all the steps will ensure you have the latest version of the software installed.

You can use the following commands to update your EVOK package distribution to a new version:

```bash
sudo su
apt-get update
apt-get install -y evok
reboot
```


## Installation process on Neuron/Unipi1.X family controllers with fresh RaspberryPi OS

*Warning: if you have previously used the shell script install method noted below you will need to use a clean image!*

In order to install EVOK on Neuron/Unipi1.X you will need an SD card with a standard (Lite) RaspberryPi OS.
We recommended enable SSH via RaspberryPi OS imager.

To install EVOK itself first connect to your controller using SSH
(there is a large number of clients you can use, for windows we recommend using [PUTTY]).
The username and password for Raspberry Pi OS are set using the Raspberry Pi OS Imager.
After you connect to your controller execute the following commands: 

For Neuron:
```bash
sudo su
wget -qO - https://repo.unipi.technology/debian/raspberry-neuron.sh | bash
apt-get install -y evok
reboot
```

For Unipi1.X:
```bash
sudo su
wget -qO - https://repo.unipi.technology/debian/raspberry-unipi1.sh | bash
apt-get install -y evok
reboot
```
    
It is possible that some (or all) of the above steps will already have been finished previously.
In that case simply continue on with the next steps.
Performing all the steps will ensure you have the latest version of the software installed.

You can use the following commands to update your EVOK package distribution to a new version:

```bash
sudo su
apt-get update
apt-get install -y evok
reboot
```

# Instructions for use

The EVOK API can be accessed in several different ways, including REST, Bulk JSON, JSON, WebSocket et al.

### For details on how to do so please see our documentation at [api-docs.io].

## Debugging

When reporting a bug or posting questions to [our forum] please set proper logging levels in '/etc/evok/config.yaml',
restart your device and check the logs with command `journalctl -eu evok`.
For more detailed log information you can also run evok by hand.
To do that you need to first stop the service by executing the following command:

```bash
systemctl stop evok
```

Run evok manually by executing the following command:

```bash
/opt/evok/bin/evok -d
```
    
You can then look through/paste the output of the script.

## Uninstallation

To uninstall EVOK please remove the evok package using the following apt command

```bash
sudo apt-get remove evok
reboot
```

Note that after uninstalling Evok you have to reboot your device to ensure all the files and settings are gone. 

## Developer Note

Do you feel like contributing to EVOK, or perhaps have a neat idea for an improvement to our system? Great! We are open to all ideas. Get in touch with us via email to info at unipi DOT technology

License
============
Apache License, Version 2.0

----
Raspberry Pi is a trademark of the Raspberry Pi Foundation

[api-docs.io]:https://kb.unipi.technology/en:sw:02-apis:01-evok:apidoc
[PUTTY]:http://www.putty.org/
[github repository]:https://github.com/UniPiTechnology/evok
[OpenSource image]:https://files.unipi.technology/s/public?path=%2FSoftware%2FOpen-Source%20Images
[IndieGogo]:https://www.indiegogo.com/projects/unipi-the-universal-raspberry-pi-add-on-board
[NEURON]:https://www.unipi.technology/products/unipi-neuron-3?categoryId=2
[PATRON]:https://www.unipi.technology/products/unipi-patron-374?categoryId=30&categorySlug=unipi-patron
[UniPi 1.1]:https://www.unipi.technology/products/unipi-1-1-1-1-lite-19?categoryId=1
[PIGPIO]:http://abyz.co.uk/rpi/pigpio/
[tornado]:https://pypi.python.org/pypi/tornado/
[toro]:https://pypi.python.org/pypi/toro/
[tornardorpc]:https://github.com/joshmarshall/tornadorpc
[websocket Python library]:https://pypi.python.org/pypi/websocket-client/
[our forum]:http://forum.unipi.technology/
[intructions below]:https://github.com/UniPiTechnology/evok#installing-evok-for-neuron
[jsonrpclib]:https://github.com/joshmarshall/jsonrpclib
[evok-web]:https://github.com/UniPiTechnology/evok-web

