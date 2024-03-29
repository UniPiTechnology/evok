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
        read -r -p "$1 [$prompt] " REPLY

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
	if [ -d ./pigpio ]; then
		cd pigpio
                make uninstall
	else
		rm -f /usr/local/include/pigpio.h
		rm -f /usr/local/include/pigpiod_if.h
		rm -f /usr/local/lib/libpigpio.a
		rm -f /usr/local/lib/libpigpiod_if.a
		rm -f /usr/local/bin/pig2vcd
		rm -f /usr/local/bin/pigpiod
		rm -f /usr/local/bin/pigs
		rm -f /usr/local/man/man1/pig*.1
		rm -f /usr/local/man/man3/pig*.3
	fi
}

uninstall() {
    service evok stop
    service pigpio stop
    pip uninstall -y tornado toro jsonrpclib python-dali onewire
    apt-get remove -y python3-distutils libow-dev
    uninstall_pigpio
    rm -rf /usr/local/lib/python2.7/dist-packages/tornadorpc_evok
    rm -rf /opt/evok
    rm -f /etc/evok.conf
    update-rc.d -f pigpio remove
    update-rc.d -f evok remove
    rm -f /etc/init.d/evok
    rm -f /etc/init.d/pigpiod
    echo "Evok uninstalled sucessfully"
    echo "Do not forget to remove its www folder /var/www/evok"
}

if [ "$EUID" -ne 0 ]
  then echo "Please run this script as root"
  exit
fi

echo "Warning, the following packages will be removed: evok, pigpiod, onewire, libow-dev, tornado, toro, jsonrpclib, tornadorpc-evok python3-distutils"
if ask "Are you sure you want to continue?"; then
    uninstall
else
    echo "Evok uninstallation aborted"
fi
