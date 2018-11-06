#!/bin/sh

# This script pulls any new changes from Saltstack/salt-jenkins.git to local
# repo and then pushes those changes to rallytime/salt-jenkins.git.

cd ~/SaltStack/salt-jenkins/

# Check if there are any unstaged changes
if [ -n "$(git status --porcelain)" ]; then 
    git status
    echo "\nChanges present - Exiting.";
else 
    # Update all relevant, constant branches
    for branch in 2017.7 2018.3 fluorine master
    do
        git checkout $branch
        git pull upstream $branch
        git push rallytime $branch
    done
fi
