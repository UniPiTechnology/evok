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

kernelget() {
    kver=$(uname -r|cut -d\- -f1|tr -d '+'| tr -d '[A-Z][a-z]')
    #echo "Verze '$1 $kver'"
    if [[ $1 == $kver ]]
    then
        return 1
    fi
    local IFS=.
    local i ver1=($1) ver2=($kver)
    # fill empty fields in ver1 with zeros
    for ((i=${#ver1[@]}; i<${#ver2[@]}; i++))
    do
        ver1[i]=0
    done
    for ((i=0; i<${#ver1[@]}; i++))
    do
        if [[ -z ${ver2[i]} ]]
        then
            # fill empty fields in ver2 with zeros
            ver2[i]=0
        fi
        if ((10#${ver1[i]} > 10#${ver2[i]}))
        then
            return 1
        fi
        if ((10#${ver1[i]} < 10#${ver2[i]}))
        then
            return 0
        fi
    done
    return 1
}

enable_ic2() {
    #enable i2c for kernel after 3.18.5
    if kernelget 3.18.5 ;then
        echo "Using kernel newer than 3.18.5"
        if ! grep -q 'device_tree_param=i2c1=on' /boot/config.txt ;then
            echo -e "$(cat /boot/config.txt) \n\n#Enable i2c bus 1\ndevice_tree_param=i2c1=on" > /boot/config.txt
        fi
    else #comment out blacklisted i2c on kernel < 3.18.5
        echo "Using kernel older than 3.18.5"
        if ! grep -q '#blacklist i2c-bcm2708' /etc/modprobe.d/raspi-blacklist.conf ;then
            sed -i '/blacklist i2c-bcm2708/s/^/#/g' /etc/modprobe.d/raspi-blacklist.conf
        fi
    fi

    #load modules
    if ! grep -q 'i2c-bcm2708' /etc/modules ;then
        echo i2c-bcm2708 >> /etc/modules
    fi

    if ! grep -q 'i2c-dev' /etc/modules ;then
        echo i2c-dev >> /etc/modules
    fi

    #load modules manually
    modprobe i2c-bcm2708
    modprobe i2c-dev
}


if [ "$EUID" -ne 0 ]; then
    echo "Please run this script as root"
    exit
fi

echo "Installing evok..."
enable_ic2

apt-get update
apt-get install -y python-ow python-pip make
pip install tornado toro jsonrpclib

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
cp -r tornadorpc_evok /usr/local/lib/python2.7/dist-packages/

#copy evok
cp -r evok/ /opt/
mkdir -p /var/www/evok && cp -r www/* /var/www/

#copy default config file and init scipts
if [ -f /etc/evok.conf ]; then
    echo "/etc/evok.conf file already exists"
    if ask "Do you want to overwrite your /etc/evok.conf file?"; then
        cp etc/evok.conf /etc/
    else
        echo "Your current config file was not overwritten."
        echo "Please see a diff between the new and your current config file."
    fi
else
    cp etc/evok.conf /etc/
fi

cp etc/init.d/evok /etc/init.d/
cp etc/init.d/pigpiod /etc/init.d/
chmod +x /etc/init.d/evok
chmod +x /etc/init.d/pigpiod
chmod +x /opt/evok/evok.py

update-rc.d pigpiod defaults
update-rc.d evok defaults

#backup uninstallation script
cp uninstall-evok.sh /opt/evok/

service pigpiod start
#service evok start

echo "Evok installed sucessfully."
echo "Info:"
echo "     1. Edit /etc/evok.conf file according to your choice."
echo "        If you are running Apache, you must set either evok or apache port different than the other."
echo "     2. Run 'service evok start/restart/stop' to control the daemon."
echo "     (3. To uninstall evok run /opt/evok/uninstall-evok.sh)"

if ask "Is it OK to reboot now?"; then
    reboot
else
    echo 'Remember to reboot your Raspberry Pi in order to start using Evok'
fi
echo ' '
