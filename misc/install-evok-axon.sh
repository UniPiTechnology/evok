#!/bin/bash

# python-pip make python-dev nginx vim
apt-get update
apt-get install -y python-ow 
apt-get install -y python-tornado python-toro
apt-get install -y python-jsonrpclib python-yaml 
apt-get install -y python-usb owfs

#pip install tornado_json tornado-webservices python-dali
#pip install pymodbus==1.4.0


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

kernelget() {
	kver=$(uname -r|cut -d '-' -f1|tr -d '+'| tr -d '[:alpha:]')
	# Echo "Verze '$1 $kver'"
	if [[ "$1" == "$kver" ]]
	then
		return 1
	fi
	local IFS=.
	local i ver1 ver2
	read -r -a ver1 <<< "$1"
	read -r -a ver2 <<< "$kver"
	# Fill empty fields in ver1 with zeros
	for ((i=${#ver1[@]}; i<${#ver2[@]}; i++))
	do
		ver1[i]=0
	done
	for ((i=0; i<${#ver1[@]}; i++))
	do
		if [[ -z ${ver2[i]} ]]
		then
			# Fill empty fields in ver2 with zeros
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
	# Enable i2c for kernel after 3.18.5
	if kernelget 3.18.5 ;then
		echo '####################################'
		echo '## Using kernel newer than 3.18.5 ##'
		echo '####################################'
		if ! grep -q 'device_tree_param=i2c1=on' /boot/config.txt ;then
			echo -e "$(cat /boot/config.txt) \\n\\n#Enable i2c bus 1\\ndevice_tree_param=i2c1=on\\ndtoverlay=i2c-rtc,mcp7941x\\ndtoverlay=unipiee\\ndtoverlay=neuronee\\n" > /boot/config.txt
		fi
	else # Comment out blacklisted i2c on kernel < 3.18.5
		echo '####################################'
		echo '## Using kernel older than 3.18.5 ##'
		echo '####################################'
		if ! grep -q '#blacklist i2c-bcm2708' /etc/modprobe.d/raspi-blacklist.conf ;then
			sed -i '/blacklist i2c-bcm2708/s/^/#/g' /etc/modprobe.d/raspi-blacklist.conf
		fi
	fi

	if kernelget 4.9.0 ;then
		echo '############################'
		echo '# Using device tree kernel #'
		echo '############################'
		if ! grep -q 'i2c-dev' /etc/modules ;then
			echo -e '\ni2c-dev' >> /etc/modules
		fi	
		modprobe i2c-dev
	else
		echo '######################'
		echo '# Using older kernel #'
		echo '######################'
		# Load modules
		if ! grep -q 'i2c-bcm2708' /etc/modules ;then
			echo -e '\ni2c-bcm2708' >> /etc/modules
		fi
		
		if ! grep -q 'i2c-dev' /etc/modules ;then
			echo -e '\ni2c-dev' >> /etc/modules
		fi	
		# Load modules manually
		modprobe i2c-bcm2708
		modprobe i2c-dev
	fi
}

install_unipi_1() {
	if kernelget 4.9.0 ;then
		echo '############################'
		echo '# Using device tree kernel #'
		echo '############################'
	else
		echo '######################'
		echo '# Using older kernel #'
		echo '######################'
		# Load UniPi 1.x EEPROM
		if ! grep -q 'unipi_eprom' /etc/modules ;then
			echo "unipi_eprom" >> /etc/modules
		fi
		
		# Load UniPi RTC
		if ! grep -q 'unipi_rtc' /etc/modules ;then
			echo "unipi_rtc" >> /etc/modules
		fi
	fi
	
	if [ "$(pidof pigpiod)" ]
	then
		service pigpiod stop
		kill "$(pidof pigpiod)"
	fi
	
	# Install pigpio
	cd pigpio || exit
	make -j4
	make install
	cd ..
	
	# Copy tornadorpc
	cp -r tornadorpc_evok /usr/local/lib/python2.7/dist-packages/
	
	# Setup wifi
	echo "############################################################################"
	echo "## !!! POTENTIALLY DANGEROUS: Do you wish to install WiFi AP support? !!! ##"
	echo "## !!! DO NOT USE WITH CUSTOM NETWORK CONFIGURATION                   !!! ##"
	echo "## !!! USE ONLY WITH PLAIN RASPBIAN STRETCH                           !!! ##"
	echo "############################################################################"
	echo ' '
	if ask "(Install WiFi?)"; then
		apt-get install -y hostapd dnsmasq iproute2
		systemctl disable hostapd dnsmasq
		systemctl stop hostapd dnsmasq
		sed -i -e 's/option domain-name/#option domain-name/' /etc/dhcp/dhcpd.conf
		sed -i -e 's/option domain-name-servers/#option domain-name-servers/' /etc/dhcp/dhcpd.conf
		sed -i -e 's/#authoritative/authoritative/' /etc/dhcp/dhcpd.conf
		sed -i -e 's/#net.ipv4.ip_forward=1/net.ipv4.ip_forward=1/' /etc/sysctl.conf
		sed -i -e 's/wifi_control_enabled = False/wifi_control_enabled = True/' etc/evok-unipi1.1.conf
	else
		ifconfig wlan0 down
	fi
	
	# Copy evok
	cp -r evok/ /opt/
	cp version.txt /opt/evok/
	mkdir -p /var/www/evok && cp -r www/* /var/www/
	mkdir -p /var/evok && cp -r var/* /var/evok/
	mkdir -p /opt && cp -r opt/* /opt/
	cp -r opt/unipiap/systemd/* /etc/systemd/system/
	systemctl daemon-reload
	systemctl disable unipiap
	systemctl disable unipidns
	chmod -R a+rx /var/www
	chmod -R a+rx /var/evok
	
	# Copy default config file and init scipts
	if [ -f /etc/evok.conf ]; then
        echo '#####################################################'
        echo '## The "/etc/evok-neuron.conf" file already exists ##'
        echo '#####################################################'
		if ask "Do you want to overwrite your /etc/evok.conf file?"; then
			cp etc/evok-unipi1.1.conf /etc/evok.conf
		else
        echo '#####################################################################'
        echo '## Your current config file was not overwritten.                   ##'
        echo '## Please do a diff between your new and previous config file.     ##'
        echo '#####################################################################'
		fi
	else
		cp etc/evok-unipi1.1.conf /etc/evok.conf
	fi
	
	chmod +x /opt/evok/evok.py
	
	manager=$(cat /proc/1/comm)
	if [ "$manager" == "systemd" ]; then
		sed -i '/Requires=neurontcp.service/s/^/#/g' etc/systemd/system/evok.service
		cp etc/systemd/system/pigpio.service /etc/systemd/system/
		cp etc/systemd/system/evok.service /etc/systemd/system/
		systemctl daemon-reload
		systemctl enable pigpio
		systemctl enable evok
	else
		cp etc/init.d/evok /etc/init.d/
		cp etc/init.d/pigpiod /etc/init.d/
		chmod +x /etc/init.d/evok
		chmod +x /etc/init.d/pigpiod
		update-rc.d pigpiod defaults
		update-rc.d evok defaults
	fi
	
	sed -i -e "s/port = 8080/port = ${internal_port_number}/" /etc/evok.conf
	
	# Backup uninstallation script
	cp uninstall-evok.sh /opt/evok/
	
	echo '##################################'
	echo '## Evok installed sucessfully.  ##'
	echo '## Info:                        ##'
	echo '## 1. Edit /etc/evok.conf file  ##'
	echo '## according to your choice.    ##'
	echo '## If you are running Apache or ##'
	echo '## other daemon at port 80, you ##'
	echo '## must set either evok or      ##'
	echo '## apache port different than   ##'
	echo '## the other.                   ##'
	echo '## 2. Run "service evok         ##'
	echo '## [start|restart|stop]" to     ##'
	echo '## control the daemon.          ##'
	echo '## (3. To uninstall evok run    ##'
	echo '## /opt/evok/uninstall-evok.sh) ##'
	echo '##################################'
	if ask "Is it OK to reboot now?"; then
		reboot
	else
		echo '################################################'
		echo '## Remember to reboot your Raspberry Pi in    ##'
		echo '## order to start using Evok                  ##'
		echo '################################################'
		service pigpiod start
		service evok start
	fi
	echo ' '
}

install_unipi_lite_1() {
	if kernelget 4.9.0 ;then
		echo '############################'
		echo '# Using device tree kernel #'
		echo '############################'
	else
		echo '######################'
		echo '# Using older kernel #'
		echo '######################'
		# Load UniPi 1.x EEPROM
		if ! grep -q 'unipi_eprom' /etc/modules ;then
		    echo "unipi_eprom" >> /etc/modules
		fi
	fi
	
	if [ "$(pidof pigpiod)" ]
	then
		service pigpiod stop
		kill "$(pidof pigpiod)"
	fi

	# Install pigpio
	cd pigpio || exit
	make -j4
	make install
	cd ..
	
	# Copy tornadorpc
	cp -r tornadorpc_evok /usr/local/lib/python2.7/dist-packages/
	
	# Setup wifi
	echo "############################################################################"
	echo "## !!! POTENTIALLY DANGEROUS: Do you wish to install WiFi AP support? !!! ##"
	echo "## !!! DO NOT USE WITH CUSTOM NETWORK CONFIGURATION                   !!! ##"
	echo "## !!! USE ONLY WITH PLAIN RASPBIAN STRETCH                           !!! ##"
	echo "############################################################################"
	echo ' '
	if ask "(Install WiFi?)"; then
		apt-get install -y hostapd dnsmasq iproute2
		systemctl disable hostapd dnsmasq
		systemctl stop hostapd dnsmasq
		sed -i -e 's/option domain-name/#option domain-name/' /etc/dhcp/dhcpd.conf
		sed -i -e 's/option domain-name-servers/#option domain-name-servers/' /etc/dhcp/dhcpd.conf
		sed -i -e 's/#authoritative/authoritative/' /etc/dhcp/dhcpd.conf
		sed -i -e 's/#net.ipv4.ip_forward=1/net.ipv4.ip_forward=1/' /etc/sysctl.conf
		sed -i -e 's/wifi_control_enabled = False/wifi_control_enabled = True/' etc/evok-lite.conf
	else
		ifconfig wlan0 down
	fi
	
	# Copy evok
	cp -r evok/ /opt/
	cp version.txt /opt/evok/
	mkdir -p /var/www/evok && cp -r www/* /var/www/
	mkdir -p /var/evok && cp -r var/* /var/evok/
	mkdir -p /opt && cp -r opt/* /opt/
	cp -r opt/unipiap/systemd/* /etc/systemd/system/
	systemctl daemon-reload
	systemctl disable unipiap
	systemctl disable unipidns
	chmod -R a+rx /var/www
	chmod -R a+rx /var/evok
	
	# Copy default config file and init scipts
	if [ -f /etc/evok.conf ]; then
		echo '#####################################################'
		echo '## The "/etc/evok-neuron.conf" file already exists ##'
		echo '#####################################################'
		if ask "Do you want to overwrite your /etc/evok.conf file?"; then
			cp etc/evok-lite.conf /etc/evok.conf
		else
		echo '#####################################################################'
		echo '## Your current config file was not overwritten.                   ##'
		echo '## Please do a diff between your new and previous config file.     ##'
		echo '#####################################################################'
		fi
	else
		cp etc/evok-lite.conf /etc/evok.conf
	fi
	
	chmod +x /opt/evok/evok.py
	
	manager=$(cat /proc/1/comm)
	if [ "$manager" == "systemd" ]; then
		sed -i '/Requires=neurontcp.service/s/^/#/g' etc/systemd/system/evok.service
		cp etc/systemd/system/pigpio.service /etc/systemd/system/
		cp etc/systemd/system/evok.service /etc/systemd/system/
		systemctl daemon-reload
		systemctl enable pigpio
		systemctl enable evok
	else
		cp etc/init.d/evok /etc/init.d/
		cp etc/init.d/pigpiod /etc/init.d/
		chmod +x /etc/init.d/evok
		chmod +x /etc/init.d/pigpiod
		update-rc.d pigpiod defaults
		update-rc.d evok defaults
	fi
	
	sed -i -e "s/port = 8080/port = ${internal_port_number}/" /etc/evok.conf
	
	# Backup uninstall script
	cp uninstall-evok.sh /opt/evok/
	
	echo '##################################'
	echo '## Evok installed sucessfully.  ##'
	echo '## Info:                        ##'
	echo '## 1. Edit /etc/evok.conf file  ##'
	echo '## according to your choice.    ##'
	echo '## If you are running Apache or ##'
	echo '## other daemon at port 80, you ##'
	echo '## must set either evok or      ##'
	echo '## apache port different than   ##'
	echo '## the other.                   ##'
	echo '## 2. Run "service evok         ##'
	echo '## [start|restart|stop]" to     ##' 
	echo '## control the daemon.          ##'
	echo '## (3. To uninstall evok run    ##'
	echo '## /opt/evok/uninstall-evok.sh) ##'
	echo '##################################'
	if ask "Is it OK to reboot now?"; then
		reboot
	else
		echo '################################################'
		echo '## Remember to reboot your Raspberry Pi in    ##'
		echo '## order to start using Evok                  ##'
		echo '################################################'
		service pigpiod start
		service evok start
	fi
	echo ' '
}

install_unipi_neuron() {
	if kernelget 4.9.0 ;then
		echo '############################'
		echo '# Using device tree kernel #'
		echo '############################'
	else
		echo '######################'
		echo '# Using older kernel #'
		echo '######################'
		# Load UniPi2 EEPROM
		if ! grep -q 'unipi2_eprom' /etc/modules ;then
			echo "unipi2_eprom" >> /etc/modules
		fi
		
		# Load UniPi2 RTC
		if ! grep -q 'unipi_rtc' /etc/modules ;then
			echo "unipi_rtc" >> /etc/modules
		fi
		
	fi
	
	
	# Install neuron_tcp_server 1.0.1
	wget https://github.com/UniPiTechnology/neuron-tcp-modbus-overlay/archive/v1.0.1.zip
	unzip v1.0.1.zip
	cd neuron-tcp-modbus-overlay-1.0.1 || exit
	yes n | bash "$PWD"/install.sh
	cd ..
	
	# Copy tornadorpc
	cp -r tornadorpc_evok /usr/local/lib/python2.7/dist-packages/
	
	# Setup wifi
	echo "############################################################################"
	echo "## !!! POTENTIALLY DANGEROUS: Do you wish to install WiFi AP support? !!! ##"
	echo "## !!! DO NOT USE WITH CUSTOM NETWORK CONFIGURATION                   !!! ##"
	echo "## !!! USE ONLY WITH PLAIN RASPBIAN STRETCH                           !!! ##"
	echo "############################################################################"
	echo ' '
	if ask "(Install WiFi?)"; then
		apt-get install -y hostapd dnsmasq iproute2
		systemctl disable hostapd dnsmasq
		systemctl stop hostapd dnsmasq
		sed -i -e 's/option domain-name/#option domain-name/' /etc/dhcp/dhcpd.conf
		sed -i -e 's/option domain-name-servers/#option domain-name-servers/' /etc/dhcp/dhcpd.conf
		sed -i -e 's/#authoritative/authoritative/' /etc/dhcp/dhcpd.conf
		sed -i -e 's/#net.ipv4.ip_forward=1/net.ipv4.ip_forward=1/' /etc/sysctl.conf
		sed -i -e 's/wifi_control_enabled = False/wifi_control_enabled = True/' etc/evok-neuron.conf
	else
		ifconfig wlan0 down
	fi
	
	# Copy evok
	cp -r evok/ /opt/
	cp version.txt /opt/evok/
	mkdir -p /var/www/evok && cp -r www/* /var/www/
	mkdir -p /var/evok && cp -r var/* /var/evok/
	mkdir -p /opt && cp -r opt/* /opt/
	cp -r opt/unipiap/systemd/* /etc/systemd/system/
	systemctl daemon-reload
	systemctl disable unipiap
	systemctl disable unipidns
	chmod -R a+rx /var/www
	chmod -R a+rx /var/evok
	
	# Copy default config file and init scipts
	if [ -f /etc/evok-neuron.conf ]; then
		echo '#####################################################'
			echo '## The "/etc/evok-neuron.conf" file already exists ##'
			echo '#####################################################'
		if ask "Do you want to overwrite your /etc/evok-neuron.conf file?"; then
			cp etc/evok-neuron.conf /etc/evok.conf
		else
			echo '#####################################################################'
			echo '## Your current config file was not overwritten.                   ##'
			echo '## Please do a diff between your new and previous config file.     ##'
			echo '#####################################################################'
		fi
	else
		cp etc/evok-neuron.conf /etc/evok.conf
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
	
	sed -i -e "s/port = 8080/port = ${internal_port_number}/" /etc/evok.conf
	
	# Backup uninstallation script
	cp uninstall-evok.sh /opt/evok/
	echo '##############################################################'
	echo '## Evok installed sucessfully.                              ##'
	echo '## Info:                                                    ##'
	echo '## 1. If you are running Apache or other daemon at port 80, ##'
	echo '## you must set either evok or apache port to be different  ##'
	echo '## from each other.                                         ##'
	echo "## 2. Run 'service evok start/restart/stop' to control the  ##"
	echo '## daemon.                                                  ##'
	echo '## (3. To uninstall evok run /opt/evok/uninstall-evok.sh)   ##'
	echo '##############################################################'
	echo ' '
	if ask "Is it OK to reboot now?"; then
		reboot
	else
		echo '#######################################################################'
		echo '## Remember to reboot your Raspberry Pi in order to start using EVOK ##'
		echo '#######################################################################'
	fi
		echo ' '
}

if [ "$EUID" -ne 0 ]; then
	echo '####################################'
	echo '## Please run this script as root ##'
	echo '####################################'
	exit
fi

echo '########################'
echo '## Installing EVOK... ##'
echo '########################'
cp -r boot/overlays /boot/

enable_ic2

cp -r etc/modprobe.d /etc/
cp -r etc/opt /etc/

apt-get update
apt-get install -y python-ow python-pip make python-dev nginx vim
pip install pymodbus==1.4.0
pip install tornado==4.5.3
pip install toro jsonrpclib pyyaml tornado_json tornado-webservices pyusb python-dali
ln -sf /etc/nginx/sites-enabled/evok /etc/evok-nginx.conf

cp -r etc/hw_definitions /etc/
cp -r etc/nginx/sites-enabled /etc/nginx/

rm -rf /etc/nginx/sites-enabled/default

echo '#########################################################################'
echo '#########################################################################'
echo '## Please select which port you wish the built-in web interface to use ##' 
echo '## (will also proxy request to the API port);                          ##'
echo '## (use 80 if you do not know what this means, can be later changed in ##'
echo '## /etc/nginx/sites-enabled/evok)                                      ##'
echo '## IMPORTANT WARNING: !!!This port cannot be the same as the internal  ##'
echo '## API port in the next section!!!                                     ##' 
echo '## WARNING: If you wish to use another web server, you may have to     ##'
echo '## disable NGINX by deleting the /etc/nginx/sites-enabled/evok file    ##'
echo '#########################################################################'
echo '#########################################################################'
echo ' '
read -r -p 'Website Port to use: >' external_port_number
echo ' '
echo '#########################################################################'
echo '## Please select which port you wish the internal API to use           ##'
echo '## (use 8080 if you do not know what this means, can be changed in     ##'
echo '## "/etc/evok.conf" later)                                             ##'
echo '#########################################################################'
echo ' '
read -r -p 'API Port to use: >' internal_port_number
echo ' '
sed -i -e "s/listen 80/listen ${external_port_number}/" /etc/nginx/sites-enabled/evok
sed -i -e "s/localhost:8080/localhost:${internal_port_number}/" /etc/nginx/sites-enabled/evok
echo ' '
echo '###################################################'
echo '## Please choose the type of your UniPi product: ##'
echo '###################################################'
echo ' ' 
PS3="Your model: >"
options=(
	"UniPi Neuron"
	"UniPi Lite 1.x"
	"UniPi 1.x"
)
echo ''
select platform in "${options[@]}"; do
	case "$platform" in
		"UniPi Neuron")
			echo '################################################################################'
			echo '## Installing EVOK for UniPi Neuron series including Neuron TCP Modbus Server ##'
			echo '################################################################################'
			install_unipi_neuron
			break
			;;
		"UniPi Lite 1.x")
			echo '########################################'
			echo '## Installing EVOK for UniPi Lite 1.x ##'
			echo '########################################'
			install_unipi_lite_1
			break
			;;
		"UniPi 1.x")
			echo '###################################'
			echo '## Installing EVOK for UniPi 1.x ##'
			echo '###################################'
			install_unipi_1
			break
			;;
		*)
			echo '####################'
			echo '## Invalid option ##'
			echo '####################'
	esac
done
