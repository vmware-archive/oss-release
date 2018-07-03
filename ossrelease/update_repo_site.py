# -*- coding: utf-8 -*-
'''
Update the repo.saltstack.com site with new versions
'''

import argparse
import os
import subprocess
import sys

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

    # replace versions
    repo_dir = opts['REPO_SALTSTACK_DIR']
    file_dir = os.path.join(repo_dir, 'content', 'repo')
    if args.replace:
        branch = '.'.join(args.version.split('.')[:-1])
        pre_ver = branch + '.' + str(int(args.version[-1]) -1)
        fed_pre_ver = branch + '.' + str(int(args.version[-1]) -2)
        if branch == '2017.7':
            file = '2017.7.md'
        elif branch == '2018.3':
            file = 'index.md'

        edit_file = os.path.join(file_dir, file)

        # now commit and push changes
        git_dir = '--git-dir={0}/.git'.format(opts['SSE_DIR'])
        work_tree = '--work-tree={0}'.format(opts['SSE_DIR'])

        git_cmd = ['git', git_dir, work_tree]

        # Check out master branch
        _cmd_run(git_cmd + ['checkout', 'master'])

        branch_name = 'repo_update_{0}-2'.format(args.version)
        _cmd_run(git_cmd + ['checkout', '-b', branch_name])
        print('New branch: {0}'.format(branch_name))

        # new date
        if args.date:
            _replace_txt(edit_file, old=pre_ver,
                         new=args.date, replace_line='set release_date')

        _replace_txt(edit_file, old=pre_ver, new=args.version)

        # replace fedora versions for latest
        if 'index' in file:
            _replace_txt(edit_file, old=fed_pre_ver, new=pre_ver)

        commit_msg = 'Update release version and date for repo landing to {0}'.format(args.version)
        _cmd_run(git_cmd + ['add', edit_file])
        print('Committing change and pushing branch {0} to {1}\n'.format(branch_name, opts['FORK_REMOTE']))
        _cmd_run(git_cmd + ['commit', '-m', commit_msg])
        _cmd_run(git_cmd + ['push', opts['FORK_REMOTE'], branch_name])

    if args.build:
        print('Building Docs')
        print(_cmd_run(['acrylamid', 'co'], cwd=repo_dir))


    if args.staging:
        print('Pushing to staging')
        upload = opts['REPO_UPLOAD_SCRIPT']


        # check we have the appropriate command
        ret = _cmd_run(['bash', upload])

        # deploy
        ssh_cmd = ['ssh', '-i', opts['REPO_DEPLOY_KEY'],
                   '{0}@{1}'.format(opts['REPO_DEPLOY_SRV_USR'],
                                    opts['REPO_DEPLOY_SRV']),]
        ret = _cmd_run(ssh_cmd + ["/root/deploy_staging_only.sh"])


def parse_args():
    '''
    Parse the CLI options.
    '''
    # Define parser and set up basic options
    parser = argparse.ArgumentParser(
        description='Update the release version numbers for print.sls in saltstack/builddocs'
    )
    parser.add_argument('-v', '--version',
                        help='Set the salt version you are updating')
    parser.add_argument('-s', '--staging',
                        action='store_true',
                        help='Push to staging')
    parser.add_argument('-b', '--build',
                        action='store_true',
                        help='Build Docs')
    parser.add_argument('-r', '--replace',
                        action='store_true',
                        help='Replace salt versions in repo.saltstack.com web file')
    parser.add_argument('-d', '--date',
                        help='Replace release date in repo.saltstack.com web file')

    return parser.parse_args()


def _replace_txt(file_name, old=None, new=None, replace_line=None):
    if replace_line:
        with open(file_name) as fh_:
            file_txt = fh_.read().splitlines()
            for line in file_txt:
                if replace_line in line:
                    old = line.split('\'')[-2]

    if not os.path.isfile(file_name):
        print('{0} file does not exist'.format(file_name))
        sys.exit(1)

    with open(file_name) as fh_:
        file_txt = fh_.read()

    with open(file_name, 'w') as fh_:
        fh_.write(file_txt.replace(old, new))


def _cmd_run(cmd_args, cwd=None):
    '''
    Runs the given command in a subprocess and returns a dictionary containing
    the subprocess pid, retcode, stdout, and stderr.

    cmd_args
        The list of program arguments constructing the command to run.
    '''
    ret = {}

    def _check_retcode(cmd_args, ret):
        if ret != 0:
            print('The cmd: {0} failed'.format(cmd_args))
            sys.exit(1)

    kwargs = {}
    if cwd:
        kwargs['cwd'] = cwd

    try:
        proc = subprocess.Popen(
            cmd_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            **kwargs
        )
    except (OSError, ValueError) as exc:
        ret['stdout'] = str(exc)
        ret['stderr'] = ''
        ret['retcode'] = 1
        ret['pid'] = None
        _check_retcode(cmd_args, ret['retcode'])
        return ret

    ret['stdout'], ret['stderr'] = proc.communicate()
    ret['pid'] = proc.pid
    ret['retcode'] = proc.returncode
    _check_retcode(cmd_args, ret['retcode'])

    return ret


if __name__ == '__main__':
    main()
