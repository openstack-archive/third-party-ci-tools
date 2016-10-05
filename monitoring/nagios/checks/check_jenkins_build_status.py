#!/usr/bin/env python

import argparse
import json
import sys
import re
import time
import os
import os.path
import logging

from pygerrit.client import GerritClient
from requests.exceptions import RequestException

working_dir = os.path.dirname(os.path.abspath(sys.argv[0]))

parser = argparse.ArgumentParser()
parser.add_argument('--mode', help="starts listening to gerrit event stream",
                    choices=["listen", "check"], action="store",
                    required=True, dest="mode")
parser.add_argument('--lastminutes', '-m',
                    help="last n minutes to check for failures",
                    action="store", dest="lastminutes", type=float, default=15)
parser.add_argument('--verbose', '-v', help="verbose output",
                    action="store_true", dest="verbose")
args = parser.parse_args()

gerrit_hostname = "review.openstack.org"

gerrit_query = "query --format JSON --current-patch-set --comments"
failures_file = working_dir + "/failures.json"
successes_file = working_dir + "/successes.json"
status_file = working_dir + "/status.json"
max_last_run_lag = 300  # in seconds
max_build_time = 7200   # in seconds
status = {}

gerrit_usernames_upstream = "jenkins"
gerrit_usernames = "intel-nfv-ci"

gerrit_projects = ["openstack/neutron", "openstack/nova"]

# the definition of job pairs for particular projects
# !!! IMPORTANT when new pair is added, the first must be job from upstream
# openstack/neutron
gerrit_jobs_neutron = [["gate-tempest-dsvm-neutron-full-ubuntu-xenial", "tempest-dsvm-ovsdpdk-nfv-networking-xenial"]]
# openstack/nova
gerrit_jobs_nova = [["gate-tempest-dsvm-full-ubuntu-xenial", "tempest-dsvm-full-nfv-xenial"],
                    ["gate-tempest-dsvm-neutron-full-ubuntu-xenial", "tempest-dsvm-ovsdpdk-nfv-networking-xenial"]]


def print_verbose(msg):
    if args.verbose:
        print ("%s") % msg


def get_version(client):
    version = client.gerrit_version()
    print_verbose("gerrit version: %s" % version)


def save_last_run(epoch_now):
    fh = open(status_file, "w")
    status["last_run"] = "%s" % epoch_now
    json.dump(status, fh)
    fh.write("\n")
    fh.close()
    return status


def check_last_run(epoch_now):
    try:
        fh = open(status_file, "r")
        status_json = json.load(fh)
        last_run = status_json["last_run"]
        last_run_lag = epoch_now - float(last_run)
        if last_run_lag > max_last_run_lag:
            status = "CRITICAL"
        else:
            status = "OK"

    except IOError:
        print "Could not open '%s' file" % status_file
        if args.mode == "listen":
            save_last_run(epoch_now)
            status = "OK"
        else:
            print "is '-mode listen' running?"
            status = "CRITICAL"

    return status


def get_event(client):
    print_verbose("\nwaiting for an event from the stream")
    event = client.get_event(timeout=15)
    return event

def start_event_listener():
    client = None
    try:
        print_verbose("start_event_listener")
        client = GerritClient(gerrit_hostname)
        get_version(client)
        client.start_event_stream()
    except:
        print "problem with start_event_listener"
    return client

def stop_event_listener(client):
    client.stop_event_stream()


def parse_changes(changes):
    """ parsing changes events were received from """
    print_verbose("parsing gerrit changes")
    failures = []
    successes = []
    current_change = ""

    for ch in changes:
        change = json.loads(ch)
        status = {}
        ctime = time.ctime()
        job_pairs = [[]]
        job_index = 0

        if type(change) is dict and "currentPatchSet" in change.keys():
            patch_set_no = change["currentPatchSet"].get("number",
                                                         "no_patchset_number")
            project = change["project"]
            url = change.get("url", "no_url")
            change_no = change.get("number", "no_change_number")
            current_change = "project: %s, url: %s , patch_set_no: %s" % \
                             (project, url, patch_set_no)
            print_verbose("- change - %s" % current_change)

            # condition for which project is patchset done
            # if needed, new project must be inserted
            if project == "openstack/nova":
                job_pairs = gerrit_jobs_nova
            elif project == "openstack/neutron":
                job_pairs = gerrit_jobs_neutron
            else:
                print_verbose("- No relevant project -")
                return ("", successes, failures)
            job_index = len(job_pairs)
            print_verbose("- selected job pair - %s" % job_pairs)
            print_verbose("- job index - %d" % job_index)
            #end if

        """ finding comments of gerrit_users and getting statuses of their
        jobs """
        if "comments" in change.keys():
            for comment in change["comments"]:
                if "message" in comment.keys() and \
                                "reviewer" in comment.keys():
                    username = comment["reviewer"].get("username",
                                                       "no_username")
                    print_verbose("-- comment username: %s" % username)
                    regex = "Patch Set " + patch_set_no + ":"
                    message = comment["message"]
                    if re.search(regex, message):
                        if username == gerrit_usernames_upstream:
                            print_verbose("gerrit_usernames_upstream comment message: %s" % message)
                            print_verbose("- job index - %d" % job_index)
                            for i in range(0, job_index):
                                job = job_pairs[i][0]
                                pattern = "Verified[+|-]1.*(%s)\ (http.*?)\ :\ (\w+)\ in\ (\w+)" \
                                    % job
                                print_verbose("---- pattern: %s" % pattern)
                                match = re.search(pattern,
                                    str(message),
                                    flags=re.IGNORECASE | re.DOTALL | re.VERBOSE)

                                if match:
                                    status[job] = match.group(3)
                                    print_verbose("status: %s" % status[job])

                        elif username == gerrit_usernames:
                            print_verbose("gerrit_usernames  comment message: %s" % message)
                            print_verbose("- job index - %d" % job_index)
                            for i in range(0, job_index):
                                job = job_pairs[i][1]
                                pattern = "(%s)\ (http.*?)\ :\ (\w+)" % job
                                print_verbose("---- pattern: %s" % pattern)
                                match = re.search(pattern,
                                    str(message),
                                    flags=re.IGNORECASE | re.DOTALL | re.VERBOSE)

                                if match:
                                    status[job] = match.group(3)
                                    print_verbose("status: %s" % status[job])

            (successes, failures) = \
                store_results(status, job_pairs, project, ctime, url, patch_set_no, change_no)


    print_verbose("- successes -")
    print_verbose(successes)
    print_verbose("- failures -")
    print_verbose(failures)
    return (current_change, successes, failures)


def store_results(status, job_pairs, project, ctime, url, patch_set_no, change_no):
    print_verbose("- store_results -")
    successes = []
    failures = []
    job = ""
    job_upstream = ""

    job_index = len(job_pairs)

    for i in range(0, job_index):
        job_upstream = job_pairs[i][0]
        job = job_pairs[i][1]

        if job_upstream not in status.keys() or job not in status.keys():
            continue
        print_verbose("job_upstream: %s" % job_upstream)
        print_verbose("job_upstream status: %s" % status[job_upstream])
        print_verbose("job: %s" % job)
        print_verbose("job status: %s" % status[job])
    
        key = ("<a href=%s/#/c/%s>%s/%s</a>" %
            (url, patch_set_no, change_no, patch_set_no))
        item = {
            ctime: key,
            "project": project,
            "job": job,
        }
        if status[job_upstream] == "SUCCESS" and \
                status[job] == "FAILURE":
            failures.append(item)
        else:
            successes.append(item)
    return (successes, failures)


def process_event(event):
    change_id = ""
    
    if 'change' in event.keys() and 'project' in event['change'].keys():
        project = event['change']['project']
        print_verbose("- event project: %s" % project)

        if project in gerrit_projects:
            if 'author' in event.keys() and 'username' in event['author'].keys():
                username = event['author']['username']
                print_verbose("-- event username: %s" % username)
                if username in (
                        gerrit_usernames_upstream,
                        gerrit_usernames):
                    if 'type' in event.keys():
                        print_verbose("--- event type: %s" % event['type'])
                        if event['type'] == "comment-added":
                            if 'change' in event.keys() and \
                                            'number' in event['change'].keys():
                                change_id = event['change']['number']
    else:
        print_verbose("skipping not a 'change' event: %s" % event)

    return change_id


def write_line_to_file(data_results, filename):
    fh = open(filename, "a")
    for item in data_results:
        json.dump(item, fh)
        fh.write("\n")
    fh.close()


def process_failures_in_stream(successes, failures):
    if successes.__len__() != 0:
        write_line_to_file(successes, successes_file)
    if failures.__len__() != 0:
        write_line_to_file(failures, failures_file)

    return 0


def process_failures_in_file(failures):
    if failures.__len__() != 0:
        status = "CRITICAL"
    else:
        status = "OK"

    return status


def process_exit(status):
    if status == "OK":
        exit(0)
    elif status == "WARNING":
        exit(1)
    elif status == "CRITICAL":
        exit(2)
    else:
        exit(3)


def process_check_status(status, failures):
    print "%s: %s" % (status, failures)
    process_exit(status)

def check_last_build(epoch_now, client):
    new_client = None
    if os.path.isfile(successes_file) and os.path.isfile(failures_file):
        stat_success = os.stat(successes_file)
        stat_fail = os.stat(failures_file)
    else:
        print_verbose("successes.json or failures.json doesn't exist")
        return new_client
    delta_success = epoch_now - float(stat_success.st_mtime)
    print_verbose("delta_success: %d" % delta_success)
    delta_fail = epoch_now - float(stat_fail.st_mtime)
    print_verbose("delta_fail: %d" % delta_fail)

    if delta_success > max_build_time and delta_fail > max_build_time: 
        print_verbose("restore_gerrit")
        new_client = restore_gerrit(client)
        os.utime(successes_file, None)
    return new_client

def restore_gerrit(client):
    stop_event_listener(client)
    time.sleep( 5 )
    new_client = start_event_listener()
    return new_client

def main():

    if args.mode == "listen":
        gerrit_client = None
        while True:
            gerrit_client = start_event_listener()
            if gerrit_client is None:
                print "connection to gerrit broken, another try in 5 seconds"
                time.sleep( 5 )
            else:
                break

        try:
            while True:
                epoch_now = time.time()
                event = None
                change_id = None
                successes = {}
                failures = {}
                current_change = ""
                gerrit_change = []
                e = get_event(gerrit_client)
                """ checking whether change is related to what we're looking
                for """
                if e:
                    event = e.json
                    change_id = process_event(event)
                    print_verbose("change_id: %s, event: %s" %
                                  (change_id, event))
                    if change_id != "":
                        print_verbose("gerrit_query:" + gerrit_query +
                                                      " change:" +
                                                      change_id)
                        stream = gerrit_client.run_command(gerrit_query +
                                                           " change:" +
                                                           change_id)
                        stream_json = stream.stdout.read()
                        for line in stream_json.splitlines():
                            gerrit_change.append(line)

                        print_verbose("gerrit_change: %s" % gerrit_change)
                        (current_change, successes, failures) = \
                            parse_changes(gerrit_change)
                        if current_change:
                            process_failures_in_stream(successes, failures)

                save_last_run(epoch_now)
                new_client = check_last_build(epoch_now, gerrit_client)
                if new_client is not None:
                    gerrit_client = new_client

        except KeyboardInterrupt:
            print "Interrupted by user"
        finally:
            stop_event_listener(gerrit_client)

    elif args.mode == "check":
        failures_file_check = "fail" # assuming check fails unless checked ok
        epoch_now = time.time()
        status = check_last_run(epoch_now)

        # short-circuit if last check in 'listen' mode was done long time ago
        if status != "OK":
            process_check_status(status,
                {epoch_now: "last check done a long time ago, "
                "is '--mode listen' running?"})

        check_period = epoch_now - (args.lastminutes * 60)
        h = 24 # hours
        failures_file_check_period = epoch_now - (h * 60 * 60)

        last_failures = []
        status = ""

        # mode to check for any recent failures
        # (saved in file by 'listen' mode)
        try:
            failures_json = []
            fh = open(failures_file, "r")
            for l in fh.readlines():
                failures_json.append(json.loads(l))

            # checking last n number of lines in the file
            # (the most recent ones)
            n = 1000
            co = 0
            for failure in failures_json.__reversed__():
                if co < n:
                    print_verbose("%s: line: %s" % (co, failure))
                    for key in failure.keys():
                        if key != 'project' and key != 'job':
                            epoch_failure = time.mktime(time.strptime(key))
                            if epoch_failure > check_period:
                                last_failures.append(failure)

                            if epoch_failure > failures_file_check_period:
                                failures_file_check = "OK"

            # if failures_file_check != "OK":
            #     print "failures file seems old, no failure reported " \
            #           "in last %s hours" % h
            #     process_exit("WARNING")

            status = process_failures_in_file(last_failures)
            process_check_status(status, last_failures)

        except IOError:
            print "No '%s' file. Did you run %s --mode listen?" % \
                  (failures_file, sys.argv[0])
            process_exit("CRITICAL")


if __name__ == '__main__':
    sys.exit(main())
