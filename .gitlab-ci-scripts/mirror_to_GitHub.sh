#!/bin/bash

if [[ ! -z "${CI_COMMIT_TAG}" ]]; then
  EVOK_VERSION=${CI_COMMIT_TAG}
else
  EVOK_VERSION=$(/ci-scripts/generate-new-tag-for-test.sh)
fi

BRANCH=$(git branch | grep "\\*" | cut -d ' ' -f2)
echo "Current branch is ${BRANCH}"

echo "Current GIT status before filtering:"
git status

#Filter files
echo "Filtering unnecessary files..."
git filter-branch -f --index-filter 'git rm -r --cached --ignore-unmatch .project .gitlab-ci.yml .pydevproject .gitlab-ci-scripts' HEAD || exit 1

#Filter tags containing test string
echo "Filtering tags for testing branch..."
git tag | grep "test" | xargs -n 1 -I% git tag -d % || exit 1

echo "Removing current tag...will be added again later..."
git tag -d "${EVOK_VERSION}"

[[ -d ~/.ssh ]] || mkdir ~/.ssh

echo "$GITHUB_SSH_KEY" | tr -d '\r' > ~/.ssh/github_ssh_key
chmod 600 ~/.ssh/github_ssh_key
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/github_ssh_key

ssh-keyscan -H "github.com" >> ~/.ssh/known_hosts

echo "Mirroring..."
git push --mirror git@github.com:UniPiTechnology/evok

echo "Tagging..."
git tag "${EVOK_VERSION}"

echo "Pushing tag"
if [[ ! -z "${CI_COMMIT_TAG}" ]]; then
  git push git@github.com:UniPiTechnology/evok "${CI_COMMIT_TAG}"
fi
