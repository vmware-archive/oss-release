# -*- coding: utf-8 -*-
'''
Update the release version in the builddocs/print.sls file.
'''

import argparse
import subprocess

REPO_PATH = '/Users/pinyon/SaltStack/builddocs'
REMOTE = 'rallytime'


def main():
    '''
    Run!
    Prints results to the screen.
    '''
    # Parse args and define some basic params
    args = parse_args()
    new_stable = args.new_latest
    old_stable = args.old_latest
    update_stable = args.latest_branch

    new_prev = args.new_previous
    old_prev = args.old_previous
    update_previous = args.previous_branch

    git_dir = '--git-dir={0}/.git'.format(REPO_PATH)
    work_tree = '--work-tree={0}'.format(REPO_PATH)
    file_name = '{0}/builddocs/print.sls'.format(REPO_PATH)

    git_cmd = ['git', git_dir, work_tree]

    print('Updating release version for in builddocs/print.sls')

    # Check out master branch
    _cmd_run(git_cmd + ['checkout', 'master'])

    # Create a new branch
    branch_name = 'update_print_version'
    _cmd_run(git_cmd + ['checkout', '-b', branch_name])
    print('New branch: {0}'.format(branch_name))

    # Update release version for "latest"
    if new_stable:
        print('Replacing latest version {0} with {1}'.format(old_stable, new_stable))
        _replace_txt(file_name, old_stable, new_stable)

        # Update the base branch for "latest"
        if update_stable:
            new_base = new_stable.rsplit('.', 1)[0]
            old_base = old_stable.rsplit('.', 1)[0]
            print('Updating latest stable branch {0} with {1}'.format(old_base, new_base))
            _replace_txt(file_name, old_base, new_base)

    # Update release version for "previous"
    if new_prev:
        print('Replacing previous version {0} with {1}'.format(old_prev, new_prev))
        _replace_txt(file_name, old_prev, new_prev)

        # Update the base branch for "previous"
        if update_previous:
            new_base = new_stable.rsplit('.', 1)[0]
            old_base = old_stable.rsplit('.', 1)[0]
            print('Updating previous stable branch {0} with {1}'.format(old_base, new_base))
            _replace_txt(file_name, old_base, new_base)

    # Set the commit title
    commit_msg = 'Update release version in print.sls file'

    # Add files to git
    _cmd_run(git_cmd + ['add', 'builddocs/print.sls'])

    # Commit changes and push up the branch
    print('Committing change and pushing branch {0} to {1}\n'.format(branch_name, REMOTE))
    _cmd_run(git_cmd + ['commit', '-m', commit_msg])
    _cmd_run(git_cmd + ['push', REMOTE, branch_name])


def parse_args():
    '''
    Parse the CLI options.
    '''
    # Define parser and set up basic options
    parser = argparse.ArgumentParser(
        description='Update the release version numbers for print.sls in saltstack/builddocs'
    )
    parser.add_argument('-n', '--new-latest',
                        help='Set the new "latest" release version. Must be a <year.month.version> format.')
    parser.add_argument('-o', '--old-latest',
                        help='The old "latest" version the new release will replace. '
                             'Must be a <year.month.version> format.')
    parser.add_argument('-l', '--latest-branch', action='store_true',
                        help='Update the latest base branch as well as the release version.')

    parser.add_argument('-x', '--new-previous',
                        help='Set the new "previous" release version. Must be a <year.month.version> format.')
    parser.add_argument('-y', '--old-previous',
                        help='The old "previous" version the new release will replace.'
                             'Must be a <year.month.version> format.')
    parser.add_argument('-p', '--previous-branch', action='store_true',
                        help='Update the previous base branch as well as the release version.')

    return parser.parse_args()


def _replace_txt(file_name, old=None, new=None):
    with open(file_name) as fh_:
        file_txt = fh_.read()

    with open(file_name, 'w') as fh_:
        fh_.write(file_txt.replace(old, new))


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
