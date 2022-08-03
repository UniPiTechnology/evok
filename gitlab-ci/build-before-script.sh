#!/bin/bash

echo "Installing additional packages"
apt update && apt install -y dh-virtualenv dpkg-dev dh-exec build-essential fakeroot git python2.7 python libpython2-dev libow-dev

. $(basename "$0")/replace-version-consts.sh
