#!/bin/bash

#Filter
echo "Current GIT status before filtering:"
git status

echo "Filtering unnecessary files..."
git filter-branch -f --index-filter 'git rm -r --cached --ignore-unmatch .project .gitlab-ci.yml .pydevproject .gitlab-ci-scripts' HEAD

#Push
[[ -d ~/.ssh ]] || mkdir ~/.ssh

echo "$GITHUB_SSH_KEY" | tr -d '\r' > ~/.ssh/github_ssh_key
chmod 600 ~/.ssh/github_ssh_key
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/github_ssh_key

ssh-keyscan -H "github.com" >> ~/.ssh/known_hosts
#git push --mirror git@github.com:martyy665/ekvok.git


echo "Mirroring..."
git push --mirror git@github.com:martyy665/ekvok.git

echo "Pushing tag"
if [[ ! -z "${CI_COMMIT_TAG}" ]]; then
  git push git@github.com:martyy665/ekvok.git "${CI_COMMIT_TAG}"
fi
