#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import csv
import datetime
import os
import re
import socket
import sys
import subprocess
import tempfile


#############
# FUNCTIONS #
#############

def check_for_borg_job(job_name):
    '''
    Check if SLURM is currently running job_name, and return a tuple of
    (Logical, job_id)
    '''
    out, err = subprocess.Popen(
        ['squeue', '-n', job_name, '-o', '%A'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True).communicate()
    jobid = out.split('\n')[1]
    return (jobid != '', jobid)


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
        microsecond=0,
        second=0).isoformat('_')


def parse_commandline():
    # command line arguments
    parser = argparse.ArgumentParser(
        description=('python3 wrapper for borgbackup'),
        formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument(
        'config',
        help=('Path to a config file.\n'
              'Format is tab-delimited with no header.\n'
              'The following variables should be defined in the config file:\n'
              'BORG_BASE: working directory for running the backup\n'
              'BORG_EXCLUDE: paths to exclude (comma separated)\n'
              'BORG_PASSPHRASE\n'
              'BORG_PATH: paths to archive (comma separated)\n'
              'BORG_REMOTE_PATH: borg executable on the remote\n'
              'BORG_REPO: default repository location\n'
              'BORG_RSH: use this command instead of `ssh`'))
    parser.add_argument(
        '--log',
        help=('Path to write logs (default /var/log/borg)'),
        dest='logdir',
        default='/var/log/borg',
        type=str)
    args = vars(parser.parse_args())
    return args


def run_backup(path_list,
               exclude_list,
               borg_base,
               job_name,
               log_dir):
    '''
    Run the backup command and return a dict of job_id, stderr and stdout
    '''
    # construct the borg command
    archive_name = '::{0}'.format(generate_archive_name())
    borg_command = list(flatten_list([
        'salloc',
        '--job-name={0}'.format(job_name),
        '--cpus-per-task=1',
        '--nice=1',
#        '--output={0}'.format(os.path.join(log_dir, "slurm.log.txt")),
        'echo',
        'borg',
        'create',
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
    # get the jobid
    print(out, err)
    job_regex = re.compile(b'\d+')
    job_id_bytes = job_regex.search(err).group(0)
    job_id = job_id_bytes.decode("utf-8")
    # return useful info
    return {
        'job_id': job_id,
        'return_code': proc.returncode,
        'out_bytes': out,
        'err_bytes': err}


def send_mail(subject, text=None, attachment_list=None):
    mail_command = ['mail', '-s', subject]
    if attachment_list:
        for x in attachment_list:
            mail_command.append('-A')
            mail_command.append(x)
    mail_command.append(socket.gethostname())
    mail = subprocess.Popen(
        mail_command,
        stdin=subprocess.PIPE)
    if text:
        mail.communicate(input=text.encode())
    else:
        mail.communicate()


def set_borg_environment(config_file, allowed_variables):
    with open(config_file, 'rt') as csvfile:
        csvreader = csv.reader(csvfile, delimiter='\t')
        for row in csvreader:
            print(row)
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

# what to call the job on SLURM
job_name = 'borgbackup'

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

    # check if backup is already running
    running_backup = check_for_borg_job(job_name)
    if running_backup[0]:
        subject = ('[Tom@SLURM] Backup WARNING: '
                   'script still in squeue after two hours')
        text = 'Job {0} found with job_id {1}'.format(
            job_name, running_backup[1])
        send_mail(subject, text)
        sys.exit(0)

    # run backup
    start_time = now()
    results = run_backup(borg_path,
                         borg_exclude,
                         borg_base,
                         job_name,
                         log_dir)
    end_time = now()

    # check if backup was successful
    if results['return_code'] != 0:
        subject = ('[Tom@SLURM] Backup WARNING: '
                   'script failed with return_code {0}'.format(
                        results['return_code']))
        send_mail(subject)
        sys.exit(results['return_code'])

    # run prune

    # list current backups

    # mail output
    subject = '[Tom@SLURM] Backup script finished at {0}'.format(end_time)
    text = ('Backups started at {0} finished. '
            'Logs are attached.'.format(start_time))
    with tempfile.TemporaryDirectory() as tmpdir:
        errfile = os.path.join(tmpdir, 'borgbackup.err.txt')
        with open(errfile, 'wb') as f:
            f.write(results['err_bytes'])
        outfile = os.path.join(tmpdir, 'borgbackup.out.txt')
        with open(outfile, 'wb') as f:
            f.write(results['out_bytes'])
        send_mail(subject, text, [errfile, outfile])


if __name__ == '__main__':
    main()
