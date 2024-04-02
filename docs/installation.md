# Installation guide

## Installation process on Unipi controllers using pre-build OS images (recommended)

The latest images for Unipi controllers, including those with Evok pre-installed, can be downloaded from the [Unipi Technology Knowledge Base](https://kb.unipi.technology/os-images).

All necessary APT Unipi repositories are already preconfigured in the OS images. Therefore, all that's required is to login to the controller via SSH. The default username for our images is "unipi" and the default password is "unipi.technology".

```bash title="Installing Evok"
sudo su
apt-get update
apt-get install -y evok
reboot
```

It is possible that some (or all) of the above steps have already been finished previously. In that case simply continue on with the next steps. Performing all the steps will ensure you have the latest version of the software installed. You can use the same commands to update your Evok package distribution to a new version.

## Installation process on Neuron/Unipi1.X family controllers with fresh RaspberryPi OS

In order to install Evok on Neuron/Unipi1.X you will need an SD card with a standard (Lite) RaspberryPi OS. We recommended enable SSH via RaspberryPi OS imager.

To install Evok itself first connect to your controller using SSH. The username and password for Raspberry Pi OS are set using the Raspberry Pi OS Imager. After you connect to your controller execute the following commands:

=== "For Neuron"

    ```bash
    sudo su
    wget -qO - https://repo.unipi.technology/debian/raspberry-neuron.sh | bash
    apt-get install -y evok
    reboot
    ```

=== "For Unipi1.X"

    ```bash
    sudo su
    wget -qO - https://repo.unipi.technology/debian/raspberry-unipi1.sh | bash
    apt-get install -y evok
    reboot
    ```

It is possible that some (or all) of the above steps have already been finished previously. In that case simply continue on with the next steps. Performing all the steps will ensure you have the latest version of the software installed.

You can use the following commands to update your Evok package distribution to a new version:

```bash
sudo su
apt-get update
apt-get install -y evok
reboot
```

### Beta version

!!! danger
    Do not use in production environment, use solely for development.
    Beta version includes new features.
    These features may change or be removed during development.

There are several ways of getting beta version.

#### Switching to beta repository

You can switch to the beta version of Evok by adding the repository to apt sources:

=== "Neuron"

    ```bash
    echo "deb https://repo.unipi.technology/debian betaevok:bookworm main neuron-main neuron-test test" >> /etc/apt/sources.list.d/unipi.list
    apt update
    apt install -y evok
    ```

=== "Patron"

    ```bash
    echo "deb https://repo.unipi.technology/debian betaevok:bookworm main patron-main patron-test test" >> /etc/apt/sources.list.d/unipi.list
    apt update
    apt install -y evok
    ```

=== "Gate"

    ```bash
    echo "deb https://repo.unipi.technology/debian betaevok:bookworm main g1-main g1-test test" >> /etc/apt/sources.list.d/unipi.list
    apt update
    apt install -y evok
    ```

=== "Unipi 1.1"

    ```bash
    echo "deb https://repo.unipi.technology/debian betaevok:bookworm main unipi1-main unipi1-test test" >> /etc/apt/sources.list.d/unipi.list
    apt update
    apt install -y evok
    ```

#### Installing beta OS image

You can install Unipi image with beta sources.
We recommend updating evok after beta image installation using:

```bash title="Updating Evok"
apt update
apt install -y evok
```

##### Node-RED beta OS images

- [Neuron](https://kb.unipi.technology/files:software:os-images:neuron-node-red-hidden)
- [Patron](https://kb.unipi.technology/files:software:os-images:patron-node-red-hidden)
- [Gate](https://kb.unipi.technology/files:software:os-images:g1-node-red-hidden)
- [Unipi1](https://kb.unipi.technology/files:software:os-images:unipi1-node-red-hidden)

## Uninstallation

```bash title="Uninstalling Evok"
sudo apt-get remove evok
reboot
```

!!! note

    After uninstalling Evok, you have to reboot your device to ensure all the files and settings are gone.

----

Raspberry Pi is a trademark of the Raspberry Pi Foundation
