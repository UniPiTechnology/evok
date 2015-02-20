#!/bin/bash

ask() {
    # http://djm.me/ask
    while true; do

        if [ "${2:-}" = "Y" ]; then
            prompt="Y/n"
            default=Y
        elif [ "${2:-}" = "N" ]; then
            prompt="y/N"
            default=N
        else
            prompt="y/n"
            default=
        fi

        # Ask the question
        read -p "$1 [$prompt] " REPLY

        # Default?
        if [ -z "$REPLY" ]; then
            REPLY=$default
        fi

        # Check if the reply is valid
        case "$REPLY" in
            Y*|y*) return 0 ;;
            N*|n*) return 1 ;;
        esac

    done
}

kernelgt() {
    kver=$(uname -r|cut -d\- -f1|tr -d '.+'| tr -d '[A-Z][a-z]')
    kver=${kver:0:4}
    if [ $kver -ge $1 ] ; then
	    return 0;
    else
    	return 1;
    fi
}

enable_ic2() {
    #enable i2c for kernel after 3.18.5
    if kernelgt 3185 ;then
        echo "Using kernel newer than 3.18.5"
        if ! grep -q 'device_tree_param=i2c1=on' /boot/cmdline.txt ;then
            sudo echo "$(cat /boot/cmdline.txt) device_tree_param=i2c1=on" > /boot/cmdline.txt
        fi
    else #comment out blacklisted i2c on kernel < 3.18.5
        echo "Using kernel older than 3.18.5"
        if ! grep -q '#blacklist i2c-bcm2708' /etc/modprobe.d/raspi-blacklist.conf ;then
            sudo sed -i '/blacklist i2c-bcm2708/s/^/#/g' /etc/modprobe.d/raspi-blacklist.conf
        fi
    fi

    #load modules
    if ! grep -q 'i2c-bcm2708' /etc/modules ;then
        sudo echo i2c-bcm2708 >> /etc/modules
    fi

    if ! grep -q 'i2c-dev' /etc/modules ;then
        sudo echo i2c-dev >> /etc/modules
    fi

    #load modules manually
    sudo modprobe i2c-bcm2708
    sudo modprobe i2c-dev
}


if [ "$EUID" -ne 0 ]; then
    echo "Please run this script as root"
    exit
fi

echo "Installing evok..."
enable_ic2

sudo apt-get install -y python-ow python-pip
sudo pip install tornado toro jsonrpclib

if [ "$(pidof pigpiod)" ]
then
    kill $(pidof pigpiod)
fi

#install pigpio
cd pigpio
make
make install
cd ..

#copy tornadorpc
sudo cp -r tornadorpc_evok /usr/local/lib/python2.7/dist-packages/

#copy evok
sudo cp -r evok/ /opt/
sudo mkdir -p /var/www/evok && sudo cp -r www/* /var/www/

#copy default config file and init scipts
if [ -f /etc/evok.conf ]; then
    echo "/etc/evok.conf file already exists"
    if ask "Do you want to overwrite your /etc/evok.conf file?"; then
        sudo cp etc/evok.conf /etc/
    else
        echo "Your current config file was not overwritten."
        echo "Please see a diff between the new and your current config file."
    fi
else
    sudo cp etc/evok.conf /etc/
fi

sudo cp etc/init.d/evok /etc/init.d/
sudo cp etc/init.d/pigpiod /etc/init.d/
sudo chmod +x /etc/init.d/evok
sudo chmod +x /etc/init.d/pigpiod
sudo chmod +x /opt/evok/evok.py

update-rc.d pigpiod defaults
update-rc.d evok defaults

#backup uninstallation script
sudo cp uninstall-evok.sh /opt/evok/

sudo service pigpiod start
#sudo service evok start

echo "Evok installed sucessfully."
echo "!REBOOT MIGHT BE NECESSARY FOR  THE CHANGES TO TAKE EFFECT!"
echo "Then:"
echo "     1. Edit /etc/evok.conf file according to your choice."
echo "        If you are running Apache, you must set either evok or apache port different than the other."
echo "     2. Run 'sudo service evok start/restart/stop' to control the daemon."
echo "     (3. To uninstall evok run /opt/evok/uninstall-evok.sh)"
