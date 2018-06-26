# -*- coding: utf-8 -*-
'''
Update the release version in the doc/conf.py file for each specified branch.
'''

import argparse
import subprocess

# import ossrelease modules
import conf


def main():
    '''
    Run!
    Prints results to the screen.
    '''
    # Parse args and define some basic params
    opts = conf.get_conf()
    args = parse_args()
    new_stable = args.new_latest
    old_stable = args.old_latest
    new_prev = args.new_previous
    old_prev = args.old_previous

    git_dir = '--git-dir={0}/.git'.format(opts['SALT_REPO_PATH'])
    work_tree = '--work-tree={0}'.format(opts['SALT_REPO_PATH'])
    file_name = '{0}/doc/conf.py'.format(opts['SALT_REPO_PATH'])

    for branch in opts['SALT_BRANCHES']:
        print('Updating release version for {0}'.format(branch))

        # Check out base branch
        _cmd_run(['git', git_dir, work_tree, 'checkout', branch])

        # Create a new branch
        branch_name = 'update_version_doc_{0}'.format(branch)
        _cmd_run(['git', git_dir, work_tree, 'checkout', '-b', branch_name])
        print('New branch: {0}'.format(branch_name))

        # Update release version for "latest"
        if new_stable:
            print('Replacing {0} with {1} in branch {2}'.format(old_stable, new_stable, branch))
            _replace_txt(file_name, old_stable, new_stable)

        # Update release version for "previous"
        if new_prev:
            print('Replacing {0} with {1} in branch {2}'.format(old_prev, new_prev, branch))
            _replace_txt(file_name, old_prev, new_prev)

        # Set the commit title
        commit_msg = 'Update release versions for the {0} branch'.format(branch)

        # Add files to git
        _cmd_run(['git', git_dir, work_tree, 'add', 'doc/conf.py'])

        print('Committing change and pushing branch {0} to {1}\n'.format(branch_name, opts['USER_REMOTE']))
        _cmd_run(['git', git_dir, work_tree, 'commit', '-m', commit_msg])
        _cmd_run(['git', git_dir, work_tree, 'push', opts['USER_REMOTE'], branch_name])


def parse_args():
    '''
    Parse the CLI options.
    '''
    # Define parser and set up basic options
    parser = argparse.ArgumentParser(description='Update the release version numbers for doc/conf.py in Salt')
    parser.add_argument('-n', '--new-latest', help='Set the new "latest" release version. '
                                                   'Must be a <year.month.version> format.')
    parser.add_argument('-o', '--old-latest', help='The old "latest" version the new release will replace. '
                                                   'Must be a <year.month.version> format.')
    parser.add_argument('-x', '--new-previous', help='Set the new "previous" release version. '
                                                     'Must be a <year.month.version> format.')
    parser.add_argument('-y', '--old-previous', help='The old "previous" version the new release will replace. '
                                                     'Must be a <year.month.version> format.')

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
