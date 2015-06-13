#!/usr/bin/env python

import argparse
import re

import utils


def check_nodepool_image_status(warning_threshold, critial_threshold, image):
    """Returns a tuple of exit code and message string

    Exit codes are either 2 -> critical or 0 -> OK
    """
    try:
        image_list_raw = utils.run_command_local('sudo /usr/local/bin/nodepool dib-image-list')
        image_list_lines = image_list_raw.split('\n')
        newest_image_age = None

        for line in image_list_lines:
            if re.search('\|\s+' + image + '\s+\|', line):
                match = re.search('\|\s+(\w+)\s+\|\s+(\d+:\d+:\d+:\d+)\s+\|$', line)
                if match:
                    status = match.group(1)
                    if status == 'ready':
                        age_parts = match.group(2).split(':')
                        age_in_hours = (int(age_parts[0]) * 24) + int(age_parts[1])
                        if (newest_image_age is None) or (age_in_hours < newest_image_age):
                            newest_image_age = age_in_hours

        if newest_image_age is None:
            return 2, 'Error running command, output: ' + image_list_raw

        exit_code = 0
        if newest_image_age > critial_threshold:
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
    parser.add_argument('-i', required=True, type=str, help='name of image')
    args = parser.parse_args()
    code, message = check_nodepool_image_status(args.w, args.c, args.i)
    print message
    exit(code)