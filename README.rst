borg_slurm
==========

python3 wrapper to submit borg backup jobs for remote repository to SLURM workload manager

Requirements
------------

* ``slurm-wlm`` 16.05.9

Installation
------------

``pip3 install git+git://github.com/tomharrop/borg_slurm.git``

Usage
-----

.. code::

    usage: borg_slurm [-h] [--log LOGDIR] config

    python3 wrapper for borgbackup

    positional arguments:
      config        Path to a config file.
                    Format is tab-delimited with no header.
                    
                    The following variables should be defined in the config file:
                    BORG_BASE: working directory for running the backup
                    BORG_EXCLUDE: paths to exclude (comma separated)
                    BORG_PASSPHRASE
                    BORG_PATH: paths to archive (comma separated)
                    BORG_REMOTE_PATH: borg executable on the remote
                    BORG_REPO: default repository location
                    BORG_RSH: use this command instead of `ssh`

    optional arguments:
      -h, --help    show this help message and exit
      --log LOGDIR  Path to write logs (default /var/log/borg)



