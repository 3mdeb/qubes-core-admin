======
qvm-ls
======

NAME
====
qvm-ls - list VMs and various information about their state

:Date:   2012-04-03

SYNOPSIS
========
| qvm-ls [options] <vm-name>

OPTIONS
=======
-h, --help
    Show help message and exit
-n, --network
    Show network addresses assigned to VMs
-c, --cpu
    Show CPU load
-m, --mem
    Show memory usage
-d, --disk
    Show VM disk utilization statistics
-i, --ids
    Show Qubes and Xen id
-k, --kernel
    Show VM kernel options
-b, --last-backup
    Show date of last VM backup
--raw-list
    List only VM names one per line
--raw-data
    Display specify data of specified VMs. Intended for bash-parsing.
--list-fields
    List field names valid for --raw-data

AUTHORS
=======
| Joanna Rutkowska <joanna at invisiblethingslab dot com>
| Rafal Wojtczuk <rafal at invisiblethingslab dot com>
| Marek Marczykowski <marmarek at invisiblethingslab dot com>
