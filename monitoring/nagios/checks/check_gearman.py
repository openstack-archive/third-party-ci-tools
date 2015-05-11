#!/usr/bin/env python

import argparse

import utils


def check_gearman_status(job_name):
    """Returns a tuple of exit code and message string

    Exit codes are either 2 -> critical or 0 -> OK
    There are no warnings with gearman job checker
    """
    try:
        gearadmin_status = utils.run_command_local('(echo status ; sleep 0.1) | netcat 127.0.0.1 4730 -w 1')
        if job_name not in gearadmin_status:
            return 2, 'Failed to find job registered with gearman!\nstatus:\n%s' % gearadmin_status
    except Exception, e:
        return 2, 'Failed to check gearman status' + e.message

    return 0, job_name + ' is registered with gearman'

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Check gearman job status.')
    parser.add_argument('--job', required=True, type=str, help='the job name to check for')
    args = parser.parse_args()
    code, message = check_gearman_status(args.job)
    print message
    exit(code)