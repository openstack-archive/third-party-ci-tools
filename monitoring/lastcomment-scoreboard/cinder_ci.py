#!/usr/bin/env python

"""Take input from Cinder's generate_driver_list and run the cireporter."""

import argparse
import json
import sys

import cireporter


def read_cinder_input(input_file_name):
    """Read the input of the cinder/tools/generate_driver_list.py."""
    if input_file_name:
        # reading from a file, not stdin
        with open(input_file_name, "r") as input_file:
            info = json.loads(input_file.read())
            return info
    else:
        # read json from stdin
        return json.loads(sys.stdin.read())


def process_ci_name(name):
    """Convert the _ to spaces."""
    if name == "Cinder_Jenkins":
        return 'Jenkins'
    elif name:
        return name.replace('_', ' ')


def add_ci_entry(ci_info, entry):
    """Make sure every CI NAME is unique in the ci_info."""
    return list(set(ci_info)|set(entry))


def process_cinder_json(cinder_json):
    '''Convert the cinder driver list output to something usable.'''

    ci_info = []
    for driver in cinder_json:
        if 'ci_wiki_name' in driver and driver['ci_wiki_name']:
            if (type(driver['ci_wiki_name']) is list or
                    type(driver['ci_wiki_name']) is tuple):

                for entry in driver['ci_wiki_name']:
                    ci_info = add_ci_entry(ci_info,
                                           [process_ci_name(entry)])
            else:
                name = process_ci_name(driver['ci_wiki_name'])
                ci_info = add_ci_entry(ci_info, [name])

    # Make Jenkins first in the list
    ci_info = sorted(ci_info, key=lambda s: s.lower())
    if 'Jenkins' in ci_info:
        ci_info.remove('Jenkins')
        ci_info.insert(0, 'Jenkins')

    return ci_info


def main():
    parser = argparse.ArgumentParser(description='list most recent comment by '
                                     'reviewer')
    parser.add_argument('-c', '--count',
                        default=100,
                        type=int,
                        help='unique gerrit name of the reviewer')
    parser.add_argument('-i', '--input',
                        default=None,
                        help='json file containing output of cinder generate_'
                             'driver_list.py output.  Defaults to stdin.')
    parser.add_argument('-o', '--output',
                        default=None,
                        help='Write the output to a file. Defaults to stdout.')

    args = parser.parse_args()

    cinder_json = read_cinder_input(args.input)
    ci_names = process_cinder_json(cinder_json)

    print("Cinder 3rd Party CI Report: %s CI systems found" % len(ci_names))
    for name in ci_names:
        print("Checking CI: %s" % name)
        cireporter.generate_report(name, 250, 'openstack/cinder')


if __name__ == "__main__":
    main()
