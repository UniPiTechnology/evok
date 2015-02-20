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

uninstall_pigpio() {
	sudo rm -f /usr/local/include/pigpio.h
	sudo rm -f /usr/local/include/pigpiod_if.h
	sudo rm -f /usr/local/lib/libpigpio.a
	sudo rm -f /usr/local/lib/libpigpiod_if.a
	sudo rm -f /usr/local/bin/pig2vcd
	sudo rm -f /usr/local/bin/pigpiod
	sudo rm -f /usr/local/bin/pigs
	sudo rm -f /usr/local/man/man1/pig*.1
	sudo rm -f /usr/local/man/man3/pig*.3
}

uninstall() {
    sudo service evok stop
    sudo service pigpiod stop
    sudo pip uninstall -y tornado toro jsonrpclib
    sudo apt-get remove -y python-ow
    uninstall_pigpio
    sudo rm -rf /usr/local/lib/python2.7/dist-packages/tornadorpc_evok
    sudo rm -rf /opt/evok
    sudo rm -f /etc/evok.conf
    update-rc.d -f pigpio remove
    update-rc.d -f evok remove
    sudo rm -f /etc/init.d/evok
    sudo rm -f /etc/init.d/pigpiod
    echo "Evok uninstalled sucessfully"
    echo "Do not forget to remove its www folder /var/www/evok"
}

if [ "$EUID" -ne 0 ]
  then echo "Please run this script as root"
  exit
fi

echo "Warning, the following packages will be removed: evok, pigpiod, python-ow, tornado, toro, jsonrpclib, tornadorpc-evok"
if ask "Are you sure you want to continue?"; then
    uninstall
else
    echo "Evok uninstallation aborted"
fi