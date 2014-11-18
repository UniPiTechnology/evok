#!/bin/bash

enable_ic2() {
    #todo: comment out snd-bcm from modules in case of conflict?
    #sed -i '/snd-bcm2835/s/^/#/g' /etc/module

    if ! grep -q 'i2c-bcm2708' /etc/modules ;then
        sudo echo i2c-bcm2708 >> /etc/modules
    fi

    if ! grep -q 'i2c-dev' /etc/modules ;then
        sudo echo i2c-dev >> /etc/modules
    fi
    #comment out blacklisted i2c
    if ! grep -q '#blacklist i2c-bcm2708' /etc/modprobe.d/raspi-blacklist.conf ;then
        sudo sed -i '/blacklist i2c-bcm2708/s/^/#/g' /etc/modprobe.d/raspi-blacklist.conf
    fi

    #load modules manually
    sudo modprobe i2c-bcm2708
    sudo modprobe i2c-dev
}


if [ "$EUID" -ne 0 ]
  then echo "Please run this script as root"
  exit
fi

echo "Installing evok..."
enable_ic2

sudo apt-get install -y python-ow python-pip
sudo pip install tornado toro jsonrpclib

#install pigpio
cd pigpio
make
make install
cd ..

#copy tornadorpc
sudo cp -r tornadorpc_evok /usr/local/lib/python2.7/dist-packages/

#copy evok
sudo cp -r evok/ /opt/
#sudo cp www /var/

#copy default config file and init scipts
sudo cp etc/evok.conf /etc/
sudo cp etc/init.d/evok /etc/init.d/
sudo cp etc/init.d/pigpiod /etc/init.d/
sudo chmod +x /etc/init.d/evok
sudo chmod +x /etc/init.d/pigpiod

update-rc.d pigpiod defaults
update-rc.d evok defaults

#backup uninstallation script
sudo cp uninstall-evok.sh /opt/evok/

sudo service pigpiod start
#sudo service evok start

echo "Please copy www folder to your destination eg. /var/ and edit /etc/evok.conf file according to your choice."
echo "Then run sudo service evok start to run the daemon."
echo "Execute /opt/evok/uninstall-evok.sh to uninstall it."
echo "Evok installed sucessfully."
