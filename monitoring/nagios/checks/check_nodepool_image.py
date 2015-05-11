#!/usr/bin/env python

import argparse
import re

import utils


def check_nodepool_image_status(warning_threshold, critial_threshold):
    """Returns a tuple of exit code and message string

    Exit codes are either 2 -> critical or 0 -> OK
    There are no warnings with gearman job checker
    """
    try:
        image_list_raw = utils.run_command_local('sudo /usr/local/bin/nodepool image-list')
        image_list_lines = image_list_raw.split('\n')
        newest_image_age = None

        for line in image_list_lines:
            match = re.search('\|\s+(\w+)\s+\|\s+(\d+\.\d+)\s+\|$', line)
            if match:
                status = match.group(1)
                age = float(match.group(2))
                if status == 'ready':
                    if (newest_image_age is None) or (age < newest_image_age):
                        newest_image_age = age

        if not newest_image_age:
            return 2, 'Error running command, output: ' + image_list_raw

        exit_code = 0
        if newest_image_age > warning_threshold:
            exit_code = 2
        elif newest_image_age > warning_threshold:
            exit_code = 1
        return exit_code, 'Nodepool image age (hours): ' + str(newest_image_age)

    except Exception, e:
        return 2, 'Error checking nodepool images: %s' + str(e)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Check nodepool image status.')
    parser.add_argument('-w', required=True, type=int, help='warning threshold for age of the image in hours')
    parser.add_argument('-c', required=True, type=int, help='critical threshold for age of the image in hours')
    args = parser.parse_args()
    code, message = check_nodepool_image_status(args.w, args.c)
    print message
    exit(code)