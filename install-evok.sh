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
        echo -e '\ni2c-bcm2708' >> /etc/modules
    fi

    if ! grep -q 'i2c-dev' /etc/modules ;then
        echo -e '\ni2c-dev' >> /etc/modules
    fi

    #load modules manually
    modprobe i2c-bcm2708
    modprobe i2c-dev
}

install_unipi_1() {
    #load UniPi 1.x EEPROM
    if ! grep -q 'unipi_eprom' /etc/modules ;then
        echo "unipi_eprom" >> /etc/modules
    fi

    #load UniPi RTC
    if ! grep -q 'unipi_rtc' /etc/modules ;then
        echo "unipi_rtc" >> /etc/modules
    fi

    if [ "$(pidof pigpiod)" ]
    then
        service pigpiod stop
        kill $(pidof pigpiod)
    fi

    #install pigpio
    cd pigpio
    make -j4
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

    chmod +x /opt/evok/evok.py

    manager=$(cat /proc/1/comm)
    if [ "$manager" == "systemd" ]; then
        sed -i '/Requires=neurontcp.service/s/^/#/g' etc/systemd/system/evok.service
        cp etc/systemd/system/pigpio.service /etc/systemd/system/
        cp etc/systemd/system/evok.service /etc/systemd/system/
        systemctl daemon-reload
        systemctl enable pigpiod
        systemctl enable evok
    else
        cp etc/init.d/evok /etc/init.d/
        cp etc/init.d/pigpiod /etc/init.d/
        chmod +x /etc/init.d/evok
        chmod +x /etc/init.d/pigpiod
        update-rc.d pigpiod defaults
        update-rc.d evok defaults
    fi

    #backup uninstallation script
    cp uninstall-evok.sh /opt/evok/

    echo "Evok installed sucessfully."
    echo "Info:"
    echo "     1. Edit /etc/evok.conf file according to your choice."
    echo "        If you are running Apache or other daemon at port 80, you must set either evok or apache port different than the other."
    echo "     2. Run 'service evok start/restart/stop' to control the daemon."
    echo "     (3. To uninstall evok run /opt/evok/uninstall-evok.sh)"

    if ask "Is it OK to reboot now?"; then
        reboot
    else
        echo 'Remember to reboot your Raspberry Pi in order to start using Evok'
        service pigpiod start
        service evok start
    fi
    echo ' '
}

install_unipi_neuron() {
    #load UniPi2 EEPROM
    if ! grep -q 'unipi2_eprom' /etc/modules ;then
        echo "unipi2_eprom" >> /etc/modules
    fi

    #load UniPi2 RTC
    if ! grep -q 'unipi_rtc' /etc/modules ;then
        echo "unipi_rtc" >> /etc/modules
    fi

    #install neuron tcp server
    wget https://github.com/UniPiTechnology/neuron_tcp_modbus_overlay/archive/v1.0.0.zip
    unzip v1.0.0.zip
    cd neuron_tcp_modbus_overlay-1.0.0
    yes n | bash $PWD/install.sh
    cd ..
    #copy tornadorpc
    cp -r tornadorpc_evok /usr/local/lib/python2.7/dist-packages/

    #copy evok
    cp -r evok/ /opt/
    mkdir -p /var/www/evok && cp -r www/* /var/www/

    #copy default config file and init scipts
    if [ -f /etc/evok-neuron.conf ]; then
        echo "/etc/evok-neuron.conf file already exists"
        if ask "Do you want to overwrite your /etc/evok-neuron.conf file?"; then
            cp etc/evok-neuron.conf /etc/
        else
            echo "Your current config file was not overwritten."
            echo "Please see a diff between the new and your current config file."
        fi
    else
        cp etc/evok-neuron.conf /etc/
    fi

    chmod +x /opt/evok/evok.py

    manager=$(cat /proc/1/comm)
    if [ "$manager" == "systemd" ]; then
        sed -i '/Requires=pigpio.service/s/^/#/g' etc/systemd/system/evok.service
        cp etc/systemd/system/evok.service /etc/systemd/system/
        systemctl daemon-reload
        systemctl enable evok
    else
        cp etc/init.d/evok /etc/init.d/
        chmod +x /etc/init.d/evok
        update-rc.d evok defaults
    fi

    #backup uninstallation script
    cp uninstall-evok.sh /opt/evok/

    echo "Evok installed sucessfully."
    echo "Info:"
    echo "     1. If you are running Apache or other daemon at port 80, you must set either evok or apache port different than the other."
    echo "     2. Run 'service evok start/restart/stop' to control the daemon."
    echo "     (3. To uninstall evok run /opt/evok/uninstall-evok.sh)"

    if ask "Is it OK to reboot now?"; then
        reboot
    else
        echo 'Remember to reboot your Raspberry Pi in order to start using Evok'
    fi
    echo ' '
}

if [ "$EUID" -ne 0 ]; then
    echo "Please run this script as root"
    exit
fi

echo "Installing evok..."
enable_ic2

cp -r etc/modprobe.d /etc/
cp -r etc/opt /etc/

apt-get update
apt-get install -y python-ow python-pip make python-dev
pip install tornado toro jsonrpclib pymodbus

#detect version of UniPi
echo 'Please choose version of UniPi you are using:'
PS3="Your model:"
options=(
    "UniPi 1.x"
    "UniPi Neuron series"
)
select option in "${options[@]}"; do
    case "$REPLY" in
        1)
            echo "Installing evok for UniPi 1.x"
            install_unipi_1
            break
            ;;
        2)
            echo "Installing evok for UniPi Neuron series including Neuron TCP Modbus Server"
            install_unipi_neuron
            break
            ;;
        *)
            echo "Invalid option"
    esac
done