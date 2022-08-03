#!/bin/bash

echo "Installing additional packages by command ${0}"

UNWANTED_VIRTUALENV="/usr/local/bin/virtualenv"

if [ -x "${UNWANTED_VIRTUALENV}" ]; then
  echo "Removing unwanted virtualenv..."
  rm -f "${UNWANTED_VIRTUALENV}"
fi

if [ "$DEBIAN_VERSION" == "stretch" ]; then
  apt update && apt install -y dh-virtualenv dpkg-dev dh-exec build-essential fakeroot git python libpython-dev libow-dev
else
  apt update && apt install -y dh-virtualenv dpkg-dev dh-exec build-essential fakeroot git python2.7 python libpython2-dev libow-dev
fi


. "$(pwd)/gitlab-ci/replace-version-consts.sh"

