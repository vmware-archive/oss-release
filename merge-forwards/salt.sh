#!/bin/sh
#=============================================================================================
# vim: softtabstop=4 shiftwidth=4 expandtab fenc=utf-8 spell spelllang=en cc=120
#=============================================================================================
#
#   FILE: merge-forward.sh
#
#   DESCRIPTION: Automate the branch merge-forward process for SaltStack/salt.git
#
#=============================================================================================

#=============================================================================================
#  Environment variables taken into account.
#---------------------------------------------------------------------------------------------
#   * EASY_UPSTREAM_BR: The upstream branch to merge changes into. The downstream branch is
#                       set automatically to the previous release branch in Salt, relative to
#                       the "easy upstream branch" that is provided. For example, if
#                       "-b 2016.11" is specified, the downstream branch will be automatically
#                       set to "2016.3". This option is incompatible with the "-d" and "-u"
#                       upstream options. The "-b" option will override these other settings.
#   * DOWNSTREAM_BR:    The older branch that will be merged-forward into the new branch.
#   * UPSTREAM_BR:      The newer branch that will have the older branch merged into it.
#=============================================================================================

DOWNSTREAM_BR=
UPSTREAM_BR=
EASY_UPSTREAM_BRANCH=

# Display usage/help text
usage() {
cat << EOF
usage: $0 options

Automate the branch merge-forward process for SaltStack/salt.git

OPTIONS:
   -h      Show this help message.
   -b      The upstream branch to merge changes into. The downstream branch is set
           automatically to be the previous release branch in Salt, relative to the "easy
           upstream branch" that is provided. For example, if "-b 2016.11" is specified,
           the downstream branch will be set to "2016.3". This option is incompatible with
           "-d" and "-u". The "-b" option will override these other settings.
   -d      The downstream branch that will be merged-forward into the new branch.
   -u      The upstream branch that will have the older branch merged into it.
EOF
}

while getopts "hb:d:u:" OPTION
do
    case ${OPTION} in
        h)
            usage
            exit 1
            ;;
        b)
            EASY_UPSTREAM_BRANCH=$OPTARG
            ;;
        d)
            DOWNSTREAM_BR=$OPTARG
            ;;
        u)
            UPSTREAM_BR=$OPTARG
            ;;
        \?)
            echo "Invalid option: -$OPTARG" >&2
            exit 1
            ;;
    esac
done

cd ~/SaltStack/salt

# Check if there are any unstaged changes
if [ -n "$(git status --porcelain)" ]; then
    git status
    echo "\nChanges present - Exiting.";
    exit 1
fi

setup_branch_names() {
    UPSTREAM_BR=${EASY_UPSTREAM_BRANCH}

    if [ ${EASY_UPSTREAM_BRANCH} == "develop" ]; then
        DOWNSTREAM_BR="2018.3"
    elif [ ${EASY_UPSTREAM_BRANCH} == "2018.3" ]; then
        DOWNSTREAM_BR="2017.7"
    elif [ ${EASY_UPSTREAM_BRANCH} == "2017.7" ]; then
        DOWNSTREAM_BR="2016.11"
    elif [ ${EASY_UPSTREAM_BRANCH} == "2016.11" ]; then
        DOWNSTREAM_BR="2016.3"
    else
        echo "Invalid option. Easy release branch names are only supported for "
        echo "newer branches, beginning with \'2016.11\'."
        echo "Please use the '-d' and '-u' options instead."
        exit 1
    fi

}

# When using the -b option, we set up the branch values instead of needing to provide an
# upstream or downstream branch name. We'll set up the correct workflow here.
if [ ! -z ${EASY_UPSTREAM_BRANCH} ]; then
    setup_branch_names
fi

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
