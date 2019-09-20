#!/bin/bash

echo "Switching to branch..."
git checkout test

if [[ ! -z "${CI_COMMIT_TAG}" ]]; then
  EVOK_VERSION=${CI_COMMIT_TAG}
else
  EVOK_VERSION=$(/ci-scripts/generate-new-tag-for-test.sh)
fi

#Pip package metainfo file
sed -i "s/version=.*/version=\\'${EVOK_VERSION}\\',/" setup.py

#Documentation markdown file used by web-interface of gitlab/github
sed -i "s/\\/evok\\/archive.*/\\/evok\\/archive\\/${EVOK_VERSION}.zip/" README.md
sed -i "s/unzip.*/unzip ${EVOK_VERSION}.zip/" README.md
sed -i "s/cd evok-.*/cd evok-${EVOK_VERSION}/" README.md

echo "Committing autogenerated changes..."
git add README.md
git add setup.py
git commit --amend --no-edit

#File version.txt for displaying version on http://<ip address>:<port>/version

echo ${EVOK_VERSION} > version.txt

#version.txt file is edited by .git hooks
