#!/bin/bash

if [[ ! -z "${CI_COMMIT_TAG}" ]]; then
  export PACKAGE_VERSION=${CI_COMMIT_TAG}
else
  export PACKAGE_VERSION=$(/ci-scripts/generate-new-tag-for-test.sh)
fi

echo "Patching version constants with $PACKAGE_VERSION"

#Pip package metainfo file
sed -i "s/version=.*/version=\\'${PACKAGE_VERSION}\\',/" setup.py

#Documentation markdown file used by web-interface of gitlab/github
sed -i "s/\\/evok\\/archive.*/\\/evok\\/archive\\/${PACKAGE_VERSION}.zip/" README.md
sed -i "s/unzip.*/unzip ${PACKAGE_VERSION}.zip/" README.md
sed -i "s/cd evok-.*/cd evok-${PACKAGE_VERSION}/" README.md
sed -i "s/version =.*/version = \"${PACKAGE_VERSION}\"/" pyproject.toml

#File for displaying version on http://<ip address>:<port>/version
echo "${PACKAGE_VERSION}" > version.txt
