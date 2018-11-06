#!/bin/sh

# This script pulls any new changes from Saltstack/salt-bootstrap.git to local repo
# And then pushes those changes to rallytime/salt-bootstrap.git.

cd ~/SaltStack/salt-bootstrap/

# Check if there are any unstaged changes
if [ -n "$(git status --porcelain)" ]; then 
    git status
    echo "\nChanges present - Exiting.";
else 
    # Update all relevant, constant branches
    for branch in stable develop
    do
        git checkout $branch
        git pull upstream $branch
        git push rallytime $branch
    done
fi

