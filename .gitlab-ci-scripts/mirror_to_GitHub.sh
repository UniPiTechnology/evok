#!/bin/bash

pwd

echo "Script will be there...maybe..."

echo "Printuju commit message ${CI_COMMIT_MESSAGE}"

echo "Printuju vse"

env

#Filter
git filter-branch -f --index-filter 'git rm -r --cached --ignore-unmatch .project .gitlab-ci.yml .pydevproject .gitlab-ci-scripts' HEAD

#Push
git push --mirror git@github.com:martyy665/ekvok.git
