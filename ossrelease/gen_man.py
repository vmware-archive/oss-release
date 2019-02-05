# -*- coding: utf-8 -*-
'''
Generates the man pages for a given release
'''

import argparse
import re
import shutil
import subprocess
import os

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
    doc_dir = os.path.join(opts['SALT_REPO_PATH'], 'doc')
    man_build_dir = os.path.join(doc_dir, '_build', 'man')
    man_dir = os.path.join(doc_dir, 'man')
    branch = '.'.join(args.version.split('.')[:-1])

    print('Building man pages in directory: {0}'.format(doc_dir))

    # Check out master branch
    _cmd_run(['make', 'man', '-C', doc_dir])

    print('Copying new man files from {0} to {1}'.format(man_build_dir,
                                                         man_dir))
    for file_ in os.listdir(man_build_dir):
        file_path = man_build_dir + file_
        print('Copying file: {0}'.format(file_path))
        shutil.copy(file_path, man_dir)

    for file_ in os.listdir(man_dir):
        _replace_txt(man_dir + file_, old='"{0}.*" '.format(branch),
                     new='"{0}" '.format(args.version), regex=True)

        print('Adding Salt Version {0} to file: {1}'.format(args.version, file_))

def _replace_txt(file_name, old=None, new=None, regex=False):
    with open(file_name) as fh_:
        file_txt = fh_.read()
    if regex:
        find = re.search(old, file_txt)
        if not find:
            print('{0} not found in file: {1}'.format(old, file_name))
            return False
        else:
            old = find.group(0)

    with open(file_name, 'w') as fh_:
        fh_.write(file_txt.replace(old, new))

def parse_args():
    '''
    Parse the CLI options.
    '''
    # Define parser and set up basic options
    parser = argparse.ArgumentParser(
        description='Update the salt man pages'
    )
    parser.add_argument('--version',
                        help='Version of salt we are building man pages')

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
