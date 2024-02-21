#!/bin/sh

ls /etc/evok/config.yaml
cat /etc/evok/config.yaml
[ ! -s /etc/evok/config.yaml ] && cat /evok.default > /etc/evok/config.yaml
python3 -m evok
