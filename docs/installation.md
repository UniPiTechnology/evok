# Installation guide


## Installation process on Unipi controllers using pre-build OS images (recommended)


The latest images for Unipi controllers, including those with Evok pre-installed,
can be downloaded from the 
[Unipi Technology Knowledge Base](https://kb.unipi.technology/en:files:software:os-images:00-start).

All necessary APT Unipi repositories are already preconfigured in the OS images.
Therefore, all that's required is to login to the controller via SSH.
The default username for our images is "unipi" and the default password is "unipi.technology".

```bash
sudo su
apt-get update
apt-get install -y evok
reboot
```

It is possible that some (or all) of the above steps have already been finished previously
In that case simply continue on with the next steps.
Performing all the steps will ensure you have the latest version of the software installed.

You can use the same commands to update your EVOK package distribution to a new version.


## Installation process on Neuron/Unipi1.X family controllers with fresh RaspberryPi OS

*Warning: if you have previously used the shell script install method noted below you will need to use a clean image!*

In order to install EVOK on Neuron/Unipi1.X you will need an SD card with a standard (Lite) RaspberryPi OS.
We recommended enable SSH via RaspberryPi OS imager.

To install EVOK itself first connect to your controller using SSH.
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

It is possible that some (or all) of the above steps have already been finished previously
In that case simply continue on with the next steps.
Performing all the steps will ensure you have the latest version of the software installed.

You can use the following commands to update your EVOK package distribution to a new version:

```bash
sudo su
apt-get update
apt-get install -y evok
reboot
```


## Uninstallation

To uninstall EVOK please remove the evok package using the following apt command

```bash
sudo apt-get remove evok
reboot
```

Note that after uninstalling Evok you have to reboot your device to ensure all the files and settings are gone.


----
Raspberry Pi is a trademark of the Raspberry Pi Foundation

[PUTTY]:http://www.putty.org/
[our forum]:http://forum.unipi.technology/
[evok-web]:https://github.com/UniPiTechnology/evok-web

