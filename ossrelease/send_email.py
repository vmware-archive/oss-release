# -*- coding: utf-8 -*-
'''
Module for sending email to google groups
'''
import argparse
import os
import smtplib
import sys

MSG_DIR = '/home/ch3ll/git/oss-release/ossrelease/msgs/'
SEND_EMAIL = ''
SEND_PASSWD = ''
RCV_EMAIL = ''


def parse_args():
    '''
    Parse the CLI options.
    '''
    # Define parser and set up basic options
    parser = argparse.ArgumentParser(description='Send email notification for release.')
    parser.add_argument('--salt-ver', help='Specify salt version to use in email')
    parser.add_argument('--msg', help='Specify which message to use.'
                                    'You can use --list-msg to see all options')
    parser.add_argument('--list-msg',
                        action='store_true',
                        help='List all message options you can send')

    return parser.parse_args()

def _get_subject(msg, version):
    if msg == 'live_soon':
        subject = '{0} Going Live Soon'.format(version)
    elif msg == 'branch':
        subject = '{0} Branch Creation'.format(version)
    elif msg == 'test':
        subject = '{0} Test Message'.format(version)

    return subject

def send_email(msg, version):
    '''
    send an email
    '''
    branch = '.'.join(version.split('.')[:-1])

    with open(os.path.join(MSG_DIR, msg), 'r') as f:
            body = f.read()
            body = body.replace('_salt_version_', version)
            body = body.replace('_branch_', branch)

    subject = _get_subject(msg, version)

    # confirm we want to send the email
    confirm = input('Sending email from: {0} to: {1}. The body of the'
                    'message will be:\n {2}. Are you sure you want to '
                    'continue: (y/n)'.format(SEND_EMAIL, RCV_EMAIL, body))

    if confirm == 'y':
        pass
    else:
        sys.exit(1)

    server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
    server.ehlo()
    try:
        server.login(SEND_EMAIL, SEND_PASSWD)
    except smtplib.SMTPAuthenticationError as e:
        print('Could not authenticate with mail server.')
        sys.exit(2)

    message = """From: %s\nTo: %s\nSubject: %s\n\n%s
        """ % (SEND_EMAIL, RCV_EMAIL, subject, body)

    server.sendmail(SEND_EMAIL, RCV_EMAIL, message)

def _list_msgs():
    print('Here are the following message options available')
    files = os.listdir(MSG_DIR)
    for x in files:
        print(x)
    sys.exit()

def main():
    '''
    Run!
    '''
    # Parse args and define some basic params
    args = parse_args()
    if args.list_msg:
        _list_msgs()

    send_email(args.msg, args.salt_ver)

if __name__ == '__main__':
    main()
