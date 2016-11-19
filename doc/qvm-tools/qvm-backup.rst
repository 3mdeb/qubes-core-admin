==========
qvm-backup
==========

NAME
====
qvm-backup

:Date:   2012-04-10

SYNOPSIS
========
| qvm-backup [options] <backup-dir-path>

OPTIONS
=======
-h, --help
    Show this help message and exit
-x EXCLUDE_LIST, --exclude=EXCLUDE_LIST
    Exclude the specified VM from backup (might be repeated)
--force-root
    Force to run with root privileges
-d, --dest-vm
    Specify the destination VM to which the backup will be set (implies -e)
-e, --encrypt
    Encrypt the backup
--no-encrypt
    Skip encryption even if sending the backup to a VM
-p, --passphrase-file
    Read passphrase from a file, or use '-' to read from stdin
-E, --enc-algo
    Specify a non-default encryption algorithm. For a list of supported algorithms, execute 'openssl list-cipher-algorithms' (implies -e)
-H, --hmac-algo
    Specify a non-default HMAC algorithm. For a list of supported algorithms, execute 'openssl list-message-digest-algorithms'
-z, --compress
    Compress the backup
-Z, --compress-filter
	Specify a non-default compression filter program (default: gzip)
--tmpdir
    Specify a temporary directory (if you have at least 1GB free RAM in dom0, use of /tmp is advised) (default: /var/tmp)
--debug
    Enable (a lot of) debug output
	
AUTHORS
=======
| Joanna Rutkowska <joanna at invisiblethingslab dot com>
| Rafal Wojtczuk <rafal at invisiblethingslab dot com>
| Marek Marczykowski <marmarek at invisiblethingslab dot com>
