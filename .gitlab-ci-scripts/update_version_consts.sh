#!/bin/bash

#Pip package metainfo file
sed -i "s/version=.*/version='${1}',/" setup.py

#Documentation markdown file used by web-interface of gitlab/github
sed -i "s/\/evok\/archive.*/\/evok\/archive\/${1}.zip/" README.md
sed -i "s/unzip.*/unzip ${1}.zip/" README.md
sed -i "s/cd evok-.*/cd evok-${1}/" README.md

#version.txt file is edited by .git hooks