# -*- coding: utf-8 -*-
'''
Module for sending email to google groups
'''
import argparse
import os
import smtplib
import sys

# import ossrelease modules
import conf


def parse_args():
    '''
    Parse the CLI options.
    '''
    # Define parser and set up basic options
    parser = argparse.ArgumentParser(description='Send email notification for release.')
    parser.add_argument('--salt-ver', help='Specify salt version to use in email')
    parser.add_argument('--tag', help='Specify the tag used for new feature branch')
    parser.add_argument('--date', help='Specify a date for various notices related to a release')
    parser.add_argument('--msg', help='Specify which message to use.'
                                    'You can use --list-msg to see all options')
    parser.add_argument('--list-msg',
                        action='store_true',
                        help='List all message options you can send')
    parser.add_argument('--sender',
                        help='Specify email you want to send it from')
    parser.add_argument('--receiver',
                        nargs='*',
                        help='Specify email you want to send it to')

    return parser.parse_args()

def _get_subject(msg, version):
    if msg == 'live_soon':
        subject = '{0} Going Live Soon'.format(version)
    elif msg == 'branch':
        subject = '{0} Branch Creation'.format(version)
    elif msg == 'enterprise':
        subject = '{0} Ready for Testing'.format(version)
    elif msg in ('live_prev', 'live_latest', 'community_pkg'):
        subject = '{0} Released'.format(version)
    elif msg in ('feature_branch_complete'):
        subject = '{0} Branch and Feature Freeze Complete'.format(version)
    elif msg in ('feature_branch_notice'):
        subject = 'Feature Branch {0} Coming soon'.format(version)
    elif msg == 'test':
        subject = '{0} Test Message'.format(version)
    else:
        print('There is not a corresponding message for {0}. Check the msgs'
              ' directory'.format(msg))
        sys.exit(1)

    return subject

def send_email(msg, version, opts, args, sender='', receiver=''):
    '''
    send an email
    '''
    branch = '.'.join(version.split('.')[:-1])

    with open(os.path.join(opts['msg_dir'], msg), 'r') as f:
            body = f.read()
            body = body.replace('_salt_version_', version)
            body = body.replace('_branch_', branch)
            if args.date:
                body = body.replace('_date_', args.date)
            elif args.tag:
                body = body.replace('_tag_', args.tag)

    subject = _get_subject(msg, version)

    # confirm we want to send the email
    confirm = input('Sending email from: {0} to: {1}. The body of the'
                    'message will be:\n {2}. Are you sure you want to '
                    'continue: (y/n)'.format(sender, receiver, body))

    if confirm == 'y':
        pass
    else:
        sys.exit(1)

    server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
    server.ehlo()
    try:
        server.login(sender, opts['send_passwd'])
    except smtplib.SMTPAuthenticationError as e:
        print('Could not authenticate with mail server.')
        sys.exit(2)

    message = """From: %s\nTo: %s\nSubject: %s\n\n%s
        """ % (sender, receiver, subject, body)

    server.sendmail(sender, receiver, message)

def _list_msgs(opts):
    print('Here are the following message options available')
    files = os.listdir(opts['msg_dir'])
    for x in files:
        print(x)
    sys.exit()

def main():
    '''
    Run!
    '''
    # Parse args and define some basic params
    opts = conf.get_conf()
    args = parse_args()
    if args.list_msg:
        _list_msgs(opts)

    send_email(args.msg, args.salt_ver, opts, args,
               sender=args.sender,
               receiver=args.receiver)

if __name__ == '__main__':
    main()
