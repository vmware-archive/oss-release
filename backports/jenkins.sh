#!/bin/sh
#=============================================================================================
# vim: softtabstop=4 shiftwidth=4 expandtab fenc=utf-8 spell spelllang=en cc=120
#=============================================================================================
#	
#   FILE: backports.sh
#
#   DESCRIPTION: Automate the Pull Request back-port process for SaltStack/salt-jenkins.git
#
#=============================================================================================

#=============================================================================================
#  Environment variables taken into account.
#---------------------------------------------------------------------------------------------
#   * PR:              The pull request number to back-port to an older branch. 
#   * BRANCH:          The branch name to back-port the pull request to.
#   * COMMIT:          The commit sha from the oldest commit in the pull request.
#=============================================================================================

for env_var in "${SALT_JENKINS_REPO}" "${ORIGIN}"; do
  if [[ -z "${env_var}" ]] ; then
      echo "Missing environment variable"
      exit 1;
  fi
done

PR=
BRANCH=
COMMIT=

# Display usage/help text
usage() {
cat << EOF
usage: $0 options

Automate the Pull Request back-port process for SaltStack/salt-jenkins.git

OPTIONS:
   -h      Show this help message.
   -b      The branch bane to back-port the pull request to.
   -c      The commit sha from the oldest commit referenced in the pull request to be back-ported.
   -p      The pull request number to back-port to an older branch.
EOF
}

# Parse and Assign CLI Options
while getopts "hb:c:p:" OPTION
do
    case $OPTION in
        h)
            usage
            exit 1
            ;;
        b) 
            BRANCH=$OPTARG
            ;;
        c)
            COMMIT=$OPTARG
            ;;
        p)
            PR=$OPTARG 
            ;;
        \?)
            echo "Invalid option: -$OPTARG" >&2
            exit 1
            ;;
        :)
            echo "Option -$OPTARG requires an argument." >&2
            exit 1
            ;;
    esac
done

cd ${SALT_JENKINS_REPO}

# Perform the backport!
git fetch upstream pull/$PR/head:bp-$PR
git rebase --onto $BRANCH $COMMIT~1 bp-$PR && \
git push ${ORIGIN} bp-$PR
