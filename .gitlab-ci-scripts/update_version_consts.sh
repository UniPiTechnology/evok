#!/bin/bash

if [[ ! -z "${CI_COMMIT_TAG}" ]]; then
  EVOK_VERSION=${CI_COMMIT_TAG}
  BRANCH="master"
else
  EVOK_VERSION=$(/ci-scripts/generate-new-tag-for-test.sh)
  BRANCH="test"
fi

COMMIT=false
[ "${1}" = "WITH_COMMIT" ] && COMMIT=true

echo "Switching to branch..."
git checkout ${BRANCH}

#------------------ UPDATE VERSION STRING IN FILES ---------------------

#Pip package metainfo file
sed -i "s/version=.*/version=\\'${EVOK_VERSION}\\',/" setup.py

#Documentation markdown file used by web-interface of gitlab/github
sed -i "s/\\/evok\\/archive.*/\\/evok\\/archive\\/${EVOK_VERSION}.zip/" README.md
sed -i "s/unzip.*/unzip ${EVOK_VERSION}.zip/" README.md
sed -i "s/cd evok-.*/cd evok-${EVOK_VERSION}/" README.md

#File for displaying version on http://<ip address>:<port>/version
echo "${EVOK_VERSION}" > version.txt

#------------- COMMIT CHANGES (amend to the last commit) ---------------

if [ ${COMMIT} = true ] ; then
  echo "Committing autogenerated changes..."
  git add README.md
  git add setup.py
  git add version.txt
  git commit --amend --no-edit
fi