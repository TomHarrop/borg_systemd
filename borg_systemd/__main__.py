#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from email.message import EmailMessage
from pathlib import Path
from smtplib import SMTP
import argparse
import csv
import datetime
import os
import socket
import subprocess
import sys
import tempfile


#############
# FUNCTIONS #
#############

def find_email_address():
    my_fwd = Path(Path.home(), ".forward")
    try:
        with open(my_fwd, 'rt') as f:
            my_addr = [x.rstrip('\n') for x in f.readlines()][0]
            print(f'Sending email to {my_addr}')
    except FileNotFoundError as e:
        print(('Configure postfix and set up forward file at '
               f'{my_fwd.resolve().as_posix()}'))
        raise e
    return my_addr


def flatten_list(l):
    '''Works like `unlist()` in R'''
    for x in l:
        if hasattr(x, '__iter__') and not isinstance(x, str):
            for y in flatten_list(x):
                yield y
        else:
            yield x


def generate_archive_name():
    archive_time = now()
    host = socket.gethostname()
    return '_'.join([archive_time, host])


def now():
    return datetime.datetime.now().replace(
        microsecond=0).isoformat('_')


def list_borg_backups():
    '''
    List the backups and return a string
    '''
    list_command = list(flatten_list([
        'borg',
        'list']))
    # run the subprocess
    proc = subprocess.Popen(
        list_command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)
    out, err = proc.communicate()
    out_err = '{0}\n\n{1}'.format(out.decode(), err.decode())
    return(out_err)


def parse_commandline():
    # command line arguments
    parser = argparse.ArgumentParser(
        description=('python3 wrapper for borgbackup'),
        formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument(
        'config',
        help=('Path to a config file.\n'
              'Format is tab-delimited with no header.\n\n'
              'The following variables should be defined in the config file:\n'
              'BORG_BASE: working directory for running the backup\n'
              'BORG_EXCLUDE: paths to exclude (comma separated)\n'
              'BORG_PASSPHRASE\n'
              'BORG_PATH: paths to archive (comma separated)\n'
              'BORG_REMOTE_PATH: borg executable on the remote\n'
              'BORG_REPO: default repository location\n'
              'BORG_RSH: use this command instead of `ssh`\n'))
    parser.add_argument(
        '--log',
        help=('Path to write logs (default /var/log/borg)'),
        dest='logdir',
        default='/var/log/borg',
        type=str)
    args = vars(parser.parse_args())
    return args


def prune_backup(borg_base):
    prune_command = list(flatten_list([
        'borg',
        'prune',
        '--verbose', '--list', '--stats',
        '--keep-within=1d',
        '--keep-daily=7',
        '--keep-weekly=4',
        '--keep-monthly=3']))
    # run the subprocess
    proc = subprocess.Popen(
        prune_command,
        cwd=borg_base,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)
    out, err = proc.communicate()
    # return useful info
    return {
        'return_code': proc.returncode,
        'out_bytes': out,
        'err_bytes': err}


def run_backup(path_list,
               exclude_list,
               borg_base,
               log_dir):
    '''
    Run the backup command and return a dict of job_id, stderr and stdout
    '''
    # construct the borg command
    archive_name = '::{0}'.format(generate_archive_name())
    borg_command = list(flatten_list([
        'borg',
        'create',
        '--verbose',
        '--compression', 'auto,lz4',
        [['--exclude', x] for x in exclude_list],
        archive_name,
        [x for x in path_list]]))
    # run the subprocess
    proc = subprocess.Popen(
        borg_command,
        cwd=borg_base,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)
    out, err = proc.communicate()
    # return useful info
    return {
        'return_code': proc.returncode,
        'out_bytes': out,
        'err_bytes': err}


def send_borg_results(borg_results, subject, text=None, address=None):
    '''
    Write the borg_results stderr and stdout to text files and attach to
    send_mail with subject and text
    '''
    with tempfile.TemporaryDirectory() as tmpdir:
        attachment_list = []
        if 'err_bytes' in borg_results:
            if len(borg_results['err_bytes']) > 0:
                errfile = os.path.join(tmpdir, 'borgbackup.err.txt')
                attachment_list.append(errfile)
                with open(errfile, 'wb') as f:
                    f.write(borg_results['err_bytes'])
        if 'out_bytes' in borg_results:
            if len(borg_results['out_bytes']) > 0:
                outfile = os.path.join(tmpdir, 'borgbackup.out.txt')
                attachment_list.append(outfile)
                with open(outfile, 'wb') as f:
                    f.write(borg_results['out_bytes'])
        # if we have prune results, attach them as well
        if 'prune_out' in borg_results:
            if len(borg_results['prune_out']) > 0:
                prune_out = os.path.join(tmpdir, 'prune.out.txt')
                attachment_list.append(prune_out)
                with open(prune_out, 'wb') as f:
                    f.write(borg_results['prune_out'])
        if 'prune_err' in borg_results:
            if len(borg_results['prune_err']) > 0:
                prune_err = os.path.join(tmpdir, 'prune.err.txt')
                attachment_list.append(prune_err)
                with open(prune_err, 'wb') as f:
                    f.write(borg_results['prune_err'])
        # send the email with attachments
        send_mail(subject, text, attachment_list, address)


def send_mail(subject, text=None, attachment_list=None, address=None):
    # configure email
    email = EmailMessage()
    email['Subject'] = subject
    email['From'] = address
    email['To'] = address
    # set the body
    email.set_content(text)
    # add the attachments
    if attachment_list:
        for att in attachment_list:
            with open(att, 'rb') as f:
                my_attachment = f.read()
                email.add_attachment(
                    my_attachment,
                    maintype='text',
                    subtype='plain',
                    filename=Path(att).name)
    # send the mail
    with SMTP() as smtp:
        smtp.connect('localhost')
        smtp.send_message(email)


def set_borg_environment(config_file, allowed_variables):
    with open(config_file, 'rt') as csvfile:
        csvreader = csv.reader(csvfile, delimiter='\t')
        for row in csvreader:
            if row[0] in allowed_variables:
                os.environ[row[0]] = row[1]
            else:
                raise ValueError(
                    '{0} is not an allowed variable'.format(row[0]))


###########
# GLOBALS #
###########

# list of allowed environment variables
allowed_variables = [
    'BORG_BASE',
    'BORG_EXCLUDE',
    'BORG_PASSPHRASE',
    'BORG_PATH',
    'BORG_REMOTE_PATH',
    'BORG_REPO',
    'BORG_RSH',
    ]


########
# MAIN #
########

def main():
    args = parse_commandline()

    set_borg_environment(args['config'], allowed_variables)

    # variables for run_backup
    borg_path = os.getenv('BORG_PATH').split(',')
    borg_exclude = os.getenv('BORG_EXCLUDE').split(',')
    borg_base = os.getenv('BORG_BASE')
    log_dir = args['logdir']

    # run backup
    start_time = now()
    results = run_backup(borg_path,
                         borg_exclude,
                         borg_base,
                         log_dir)

    # get email address
    my_addr = find_email_address()

    # check if backup was successful
    if results['return_code'] != 0:
        subject = ('[borg-systemd] Backup WARNING: '
                   'script failed with return_code {0}'.format(
                        results['return_code']))
        text = 'Backups started at {0} failed.'.format(start_time)
        send_borg_results(
            borg_results=results,
            subject=subject,
            text=text,
            address=my_addr)
        sys.exit(results['return_code'])

    # run prune and add results to borg results
    prune_results = prune_backup(borg_base)
    results['prune_out'] = prune_results['out_bytes']
    results['prune_err'] = prune_results['err_bytes']

    # list current backups
    current_backups = list_borg_backups()

    # mail output
    end_time = now()
    subject = '[borg-systemd] Backup script finished at {0}'.format(end_time)
    text = ('Backups started at {0} finished. '
            'Logs are attached.\n\n'
            'Current backups:\n{1}'.format(start_time, current_backups))
    send_borg_results(
        borg_results=results,
        subject=subject,
        text=text,
        address=my_addr)


if __name__ == '__main__':
    main()
