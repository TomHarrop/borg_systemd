# borg_systemd

python3 wrapper to run borg backup to remote repository

## Installation

1. Install the borg_systemd wrapper:  
`pip3 install git+git://github.com/tomharrop/borg_systemd.git`
2. Copy the example systemd service and replace the paths in `ExecStart` with the virtualenv where borg_systemd is installed and the config file  
`cp config/borg-systemd.service.example config/borg-systemd.service`
3. Install the systemd service and timer  
`sudo cp config/borg-systemd.timer config/borg-systemd.service /etc/systemd/user/`
4. Start the service  
`systemctl --user enable borg-systemd.timer`  
`systemctl --user start borg-systemd.timer`

## Usage

```{bash}
usage: borg_systemd [-h] [--log LOGDIR] config

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
```
