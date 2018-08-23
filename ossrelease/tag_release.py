# -*- coding: utf-8 -*-
'''
Tag the release at the HEAD of the branch. The branch name is determined
by the tag, or can be passed with the ``-b`` option.

Tags should start with a "v" and start with the year, then month, then the
release number. For example, ``v2018.3.0``.

Default behavior for this script is to tag the release and push to the
user's remote. Passing the ``--upstream`` flag will push the tag to
SaltStack's upstream.

Passing the ``--develop`` flag will create the <year.month> tag on the
``develop`` branch. This is useful for when creating the initial tag on the
``develop`` branch before creating a new feature release branch.

Example:

    python tag_release.py -t v2017.7.5
    python tag_release.py -t 2018.12 --develop
'''

import argparse
import subprocess
import time

REPO_PATH = '/Users/pinyon/SaltStack/salt'
REMOTE = 'rallytime'
SALT_UPSTREAM = 'upstream'


def main():
    '''
    Run!
    '''
    # Parse args and define some basic params
    args = parse_args()
    tag = args.tag
    branch = args.branch
    tag_upstream = args.upstream
    tag_develop = args.develop

    # Setup based git command
    git_cmd = [
        'git',
        '--git-dir={0}/.git'.format(REPO_PATH),
        '--work-tree={0}'.format(REPO_PATH)
    ]

    if not tag.startswith('v'):
        print('Error: Tag must start with the letter \'v\'.')
        return

    if args.delete:
        print('Deleting local tag {0}.'.format(tag))
        _cmd_run(git_cmd + ['tag', '-d', tag])

        print('Deleting remote tag {0} from upstream {1}.'.format(tag, REMOTE))
        _cmd_run(git_cmd + ['push', REMOTE, ':refs/tags/{0}'.format(tag)])
        return

    # Do some tag format error checking
    if tag_develop:
        if len(tag.split('.')) != 2:
            print('Error: Tag must start with the letter \'v\' and be in a '
                  '<year.month> format when tagging on the \'develop\' branch. '
                  'Exiting.')
            return

        # Set "develop" branch if passed and tag is in correct format
        print('Use of \'develop\' flag detected. Tagging on the \'develop\' branch.')
        branch = 'develop'

    elif len(tag.split('.')) != 3:
        print('Error: tag must start with the letter \'v\' and be in a '
              '<year.month.version> format. Exiting.')
        return

    # Fetch SaltStack upstream to ensure we're up-to-date
    print('Fetching SaltStack upstream.')
    _cmd_run(git_cmd + ['fetch', SALT_UPSTREAM])

    # Fetch SaltStack upstream tags, too.
    print('Fetching SaltStack upstream tags.')
    _cmd_run(git_cmd + ['fetch', SALT_UPSTREAM, '--tags'])

    # Check if tag is already present on system
    tags = _cmd_run(git_cmd + ['tag', '-l'])['stdout'].split('\n')
    if tag in tags:
        print('Error: Tag is already present on this system. Exiting.')
        return

    if branch is None:
        branch = tag[1:]
        print('Branch option not passed. Guessing branch: {0}'.format(branch))

    # Checkout the branch to tag
    print('Checking out branch: {0}'.format(branch))
    checkout = _cmd_run(git_cmd + ['checkout', branch])
    if checkout['retcode'] != 0:
        print('Error: {0}'.format(checkout['stdout']))
        return

    # Reset the local branch to upstream
    print('Resetting local branch to upstream: {0}/{1}'.format(
        SALT_UPSTREAM, branch)
    )
    branch_reset = _cmd_run(
        git_cmd + ['reset', '--hard', '{0}/{1}'.format(
            SALT_UPSTREAM, branch
        )]
    )
    if branch_reset['retcode'] != 0:
        print('Error: {0}'.format(checkout['stdout']))
        return

    # Tag the release
    print('Tagging release: {0}'.format(tag))
    _cmd_run(git_cmd + ['tag', '-a', tag, '-m', 'Version {0}'.format(tag[1:])])

    # Push up to relevant remote
    if tag_upstream:
        print('WARNING: Pushing to upstream Salt!!')
        print('...\n...\n...')
        print('Sleeping for 5 seconds before pushing.')
        time.sleep(5)
        _cmd_run(git_cmd + ['push', SALT_UPSTREAM, tag])
    else:
        print('Pushing tag to remote: {0}'.format(REMOTE))
        _cmd_run(git_cmd + ['push', REMOTE, tag])


def parse_args():
    '''
    Parse the CLI options.
    '''
    # Define parser and set up basic options
    parser = argparse.ArgumentParser(description='Tag the release.')
    parser.add_argument('tag', help='The tag name. Should start with \'v\'.')
    parser.add_argument('-b', '--branch', help='The branch to tag the release on. If this '
                                               'option is omitted, the branch will be guessed. '
                                               'This could lead to inaccurate results/errors.')
    parser.add_argument('--upstream', help='Flag to push the tag to SaltStack\'s upstream.')
    parser.add_argument('--develop', help='Flag to create a new tag on the develop branch. '
                                          'This provides the point to create a new feature '
                                          'release branch from.')
    parser.add_argument('--delete', help='Flag to delete a tag',
                        action='store_true')
    return parser.parse_args()


def _cmd_run(cmd_args):
    '''
    Runs the given command in a subprocess and returns a dictionary containing
    the subprocess pid, retcode, stdout, and stderr.

    cmd_args
        The list of program arguments constructing the command to run.
    '''
    ret = {}
    try:
        proc = subprocess.Popen(
            cmd_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )
    except (OSError, ValueError) as exc:
        ret['stdout'] = str(exc)
        ret['stderr'] = ''
        ret['retcode'] = 1
        ret['pid'] = None
        return ret

    ret['stdout'], ret['stderr'] = proc.communicate()
    ret['pid'] = proc.pid
    ret['retcode'] = proc.returncode
    return ret


if __name__ == '__main__':
    main()
