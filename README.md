![alt text](https://github.com/UniPiTechnology/evok/raw/master/www/evok/js/jquery/images/Uni_pi_logo_new.svg?sanitize=true "UniPi logo")

# EVOK - the UniPi API

EVOK is the primary Web API for [NEURON] and [UniPi 1.1] devices. It provides a RESTful interface over HTTP, a JSON-RPC interface, a WebSocket interface a SOAP interface and a bulk JSON interface to UniPi devices.

Evok is still in active development, so any testing, feedback and contributions are very much welcome and appreciated.

APIs included in EVOK:

- RESTful WebForms API
- RESTful JSON API
- Bulk request JSON API
- WebSocket API
- SOAP API
- JSON-RPC API

EVOK also supports sending notifications via webhook.

### For more information see our documentation at [api-docs.io].

## Installation process for the latest (2.X.X) EVOK version on Neuron

*Warning: if you have previously used the shell script install method noted below you will need to use a clean image!*

In order to install EVOK on Neuron you will need an SD card with a standard ***Raspbian Jessie*** or ***Raspbian Stretch*** image. It is also necessary to enable SSH on the image by creating an empty file named "ssh" in the boot partition of your SD card (the partition should be visible on all systems which support FAT16, which includes Windows, Linux and OSX among others).

To install EVOK itself first connect to your Neuron using SSH (there is a large number of clients you can use, for windows we recommend using [PUTTY]). The default username for Raspbian is "pi" and the default password is "raspberry". After you connect to your Neuron execute the following commands: 

*NOTE: The installation process will overwrite default server configuration for NGINX*

    sudo su
    echo "deb https://repo.unipi.technology/debian stretch main" >> /etc/apt/sources.list
    wget https://repo.unipi.technology/debian/unipi_pub.gpg -O - | apt-key add
    apt-get update
    apt-get upgrade
    apt-get install nginx
    rm -f /etc/nginx/sites-enabled/default
    apt-get install unipi-modbus-tools
    apt-get install evok
    systemctl enable evok
    reboot
    
It is possible that some (or all) of the above steps will already have been finished previously; in that case simply continue on with the next steps. Performing all the steps will ensure you have the latest version of the software installed.

You can use the following commands to update your EVOK package distribution to a new version:

    sudo su
    apt-get update
    apt-get upgrade
    apt-get install unipi-modbus-tools
    reboot

## Legacy installation process using a shell script (REQUIRED FOR UNIPI 1.1!)

In order to install EVOK on Neuron you will need an SD card with a standard ***Raspbian Jessie*** or ***Raspbian Stretch*** image. It is also necessary to enable SSH on the image by creating an empty file named "ssh" in the boot partition of your SD card (the partition should be visible on all systems which support FAT16, which includes Windows, Linux and OSX among others).

To install EVOK itself first connect to your Neuron using SSH (there is a large number of clients you can use, for windows we recommend using [PUTTY]). The default username for Raspbian is "pi" and the default password is "raspberry". After you connect to your Neuron execute the following commands:

    sudo su
    wget https://github.com/UniPiTechnology/evok/archive/v.2.0.7c.zip
    unzip v.2.0.7c.zip
    cd evok-v.2.0.7c
    bash install-evok.sh

The installation script should take care of everything else, but be aware there may be some issues with limited and/or broken functionality. Please report any bugs you find on the [github repository].

## Installing EVOK on AXON PLCs

EVOK is installed slightly differently on Axon PLCs than on Neuron PLCs. The Axon installation process is based entirely around premade packages which are already enabled on the device, all that's required is to login to the PLC via SSH (there is a large number of clients you can use, for windows we recommend using [PUTTY]). The default username for Axon PLCs is "unipi" and the default password is "unipi.technology". After you connect to your Axon PLC execute the following commands:

    sudo su
    apt-get update
    apt-get upgrade
    apt-get install unipi-modbus-tools
    apt-get install evok
    systemctl enable evok
    reboot

It is possible that some (or all) of the above steps will already have been finished previously; in that case simply continue on with the next steps. Performing all the steps will ensure you have the latest version of the software installed.

You can use the following commands to update your EVOK package distribution to a new version:

    sudo su
    apt-get update
    apt-get upgrade
    reboot

## Installation process for Evok v.1.X.X

Access to GPIOs is done using the fantastic [PIGPIO] library. Make sure to install it first before use.

_**EVOK v.1.X.X**_ also requires a few other python libraries that are not installed on Raspbian by default:
* python-ow
* [tornado]
* [toro]
* modified version of [tornardorpc] available in this repo tornadorpc_evok
* [jsonrpclib]

Download the latest release from our repository via wget (alternatively you can clone the repository using git):

    wget https://github.com/UniPiTechnology/evok/archive/v.1.0.2.tar.gz
    tar -zxvf v.1.0.2.tar.gz && mv evok-* evok  

Please note that the folder that you downloaded the package into is not used later and can be safely deleted after the installation. Configuration files are installed directly into /etc/, /opt/ and /boot/

Run the installation script using the following instructions

    cd evok
    chmod +x install-evok.sh uninstall-evok.sh
    sudo ./install-evok.sh

# Instructions for use

The EVOK API can be accessed in several different ways, including SOAP, REST, Bulk JSON, JSON, WebSocket et al.

### For details on how to do so please see our documentation at [api-docs.io].

## Debugging

When reporting a bug or posting questions to [our forum] please set proper logging levels in /etc/evok.conf, restart your device and check the log file (/var/log/evok.log). For more detailed log information you can also run evok by hand. To do that you need to first stop the service by executing the

    sudo systemctl stop evok

command and then run it manually as root user 
    
    sudo python /opt/evok/evok.py

and look through/paste the output of the script.

## Uninstallation

To uninstall EVOK please run the uninstallation script which is located in the `/opt/evok/` folder.

    sudo su
    bash uninstall-evok.sh

Note that after uninstalling Evok you have to reboot your device to ensure all the files and settings are gone. 

The installation script also enables the I2C subsystem (if it is not otherwise enabled before), but the uninstallation script does not disable it again.

## Developer Note

Do you feel like contributing to EVOK, or perhaps have a neat idea for an improvement to our system? Great! We are open to all ideas. Get in touch with us via email to info at unipi DOT technology

License
============
Apache License, Version 2.0

----
Raspberry Pi is a trademark of the Raspberry Pi Foundation

[api-docs.io]:https://evok-9.api-docs.io/1.08/
[PUTTY]:http://www.putty.org/
[github repository]:https://github.com/UniPiTechnology/evok
[OpenSource image]:https://files.unipi.technology/s/public?path=%2FSoftware%2FOpen-Source%20Images
[IndieGogo]:https://www.indiegogo.com/projects/unipi-the-universal-raspberry-pi-add-on-board
[NEURON]:http://www.unipi.technology
[UniPi 1.1]:https://www.unipi.technology/products/unipi-1-1-19?categoryId=1&categorySlug=unipi-1-1
[PIGPIO]:http://abyz.co.uk/rpi/pigpio/
[tornado]:https://pypi.python.org/pypi/tornado/
[toro]:https://pypi.python.org/pypi/toro/
[tornardorpc]:https://github.com/joshmarshall/tornadorpc
[websocket Python library]:https://pypi.python.org/pypi/websocket-client/
[our forum]:http://forum.unipi.technology/
[intructions below]:https://github.com/UniPiTechnology/evok#installing-evok-for-neuron
[jsonrpclib]:https://github.com/joshmarshall/jsonrpclib
