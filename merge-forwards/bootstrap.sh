#!/bin/sh
#=============================================================================================
# vim: softtabstop=4 shiftwidth=4 expandtab fenc=utf-8 spell spelllang=en cc=120
#=============================================================================================
#
#   FILE: bootstrap.sh
#
#   DESCRIPTION: Automate the branch merge-forward process for SaltStack/salt-bootstrap.git
#
#=============================================================================================

# Display usage/help text
usage() {
cat << EOF
usage: $0 options

Automate the branch merge-forward process for SaltStack/salt-bootstrap.git

There are only two branches in the salt-bootstrap repository: "develop" and "stable".
The "develop" branch should always be merged into the "stable" branch, therefore,
there are not script options in this file.

OPTIONS:
   -h      Show this help message.
EOF
}

while getopts "h" OPTION
do
    case ${OPTION} in
        h)
            usage
            exit 1
            ;;
        \?)
            echo "Invalid option: -$OPTARG" >&2
            exit 1
            ;;
    esac
done

cd ~/SaltStack/salt-bootstrap

# Check if there are any unstaged changes
if [ -n "$(git status --porcelain)" ]; then
    git status
    echo "\nChanges present - Exiting.";
    exit 1
fi

UPSTREAM_BR="stable"
DOWNSTREAM_BR="develop"

# Checkout the branch we're merging forward to
git checkout ${UPSTREAM_BR}

# Create a new merge branch and check it out
git checkout -b merge-${UPSTREAM_BR}

# Reset the branch to upstream repo, just in case.
git reset --hard upstream/${UPSTREAM_BR}

# Print out which branch we're on for debugging
git branch

# Set the commit title
TOP_LINE_MSG="Merge branch '$DOWNSTREAM_BR' into '$UPSTREAM_BR'"

# Check for a clean merge
git merge ${DOWNSTREAM_BR} -m "$TOP_LINE_MSG" --no-commit

# If the merge is clean, commit the result with a "No conflicts"
# addition to the underlying commit message and push to "rallytime".
RET_CODE=$?
if [ ${RET_CODE} -eq 0 ]; then
    git commit -m "$TOP_LINE_MSG" -m "No conflicts."
    git push rallytime merge-${UPSTREAM_BR}
fi
