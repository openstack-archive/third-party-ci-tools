#!/usr/bin/env python

"""Print the last time a reviewer(bot) left a comment."""

import argparse
import calendar
import collections
import datetime
import json
import sys
import yaml
import pdb

import requests
import comment


def query_gerrit(name, count, project):
    # Include review messages in query
    search = "reviewer:\"%s\"" % name
    if project:
        search = search + (" AND project:\"%s\"" % project)
    query = ("https://review.openstack.org/changes/?q=%s&"
             "o=MESSAGES&o=DETAILED_ACCOUNTS" % search)
    r = requests.get(query)
    try:
        changes = json.loads(r.text[4:])
    except ValueError:
        print "query: '%s' failed with:\n%s" % (query, r.text)
        return []

    comments = []
    for change in changes:
        for date, message in comment.get_comments(change, name):
            if date is None:
                # no comments from reviewer yet. This can happen since
                # 'Uploaded patch set X.' is considered a comment.
                continue
            comments.append(comment.Comment(date, change['_number'],
                                            change['subject'], message))
    return sorted(comments, key=lambda comment: comment.date,
                  reverse=True)[0:count]


def vote(cmt, success, failure, log=False):
    for line in cmt.message.splitlines():
        if line.startswith("* ") or line.startswith("- "):
            if job.result == 'SUCCESS':
                success[job] += 1
            elif job.result == 'FAILRE':
                failure[job] += 1

            if log:
                print line


def generate_report(name, count, project):
    result = {'name': name, 'project': project}
    success = collections.defaultdict(int)
    failure = collections.defaultdict(int)

    comments = query_gerrit(name, count, project)

    if len(comments) == 0:
        print "didn't find anything"
        return None

    print "last seen: %s (%s old)" % (comments[0].date, comments[0].age())
    result['last'] = epoch(comments[0].date)

    for cmt in comments:
        vote(cmt, success, failure)

    total = sum(success.values()) + sum(failure.values())
    if total > 0:
        success_rate = str(int(sum(success.values()) /
                               float(total) * 100)) + "%"
        result['rate'] = success_rate
        print "success rate: %s" % success_rate
    return result


def print_last_comments(name, count, print_message, project, votes):
    success = collections.defaultdict(int)
    failure = collections.defaultdict(int)

    comments = query_gerrit(name, count, project)

    message = "last %s comments from '%s'" % (count, name)
    if project:
        message += " on project '%s'" % project
    print message
    # sort by time
    for i, comment in enumerate(comments):
        print "[%d] %s" % (i, comment)
        if print_message:
            print "message: \"%s\"" % comment.message
            print
        if votes:
            vote(comment, success, failure, log=True)

    if votes:
        print "success count by job:"
        for job in success.iterkeys():
            print "* %s: %d" % (job, success[job])
        print "failure count by job:"
        for job in failure.iterkeys():
            print "* %s: %d" % (job, failure[job])


def epoch(timestamp):
    return int(calendar.timegm(timestamp.timetuple()))


def main():
    parser = argparse.ArgumentParser(description='list most recent comment by '
                                     'reviewer')
    parser.add_argument('-n', '--name',
                        default="Elastic Recheck",
                        help='unique gerrit name of the reviewer')
    parser.add_argument('-c', '--count',
                        default=10,
                        type=int,
                        help='unique gerrit name of the reviewer')
    parser.add_argument('-f', '--file',
                        default=None,
                        help='yaml file containing list of names to search on'
                             'project: name'
                             ' (overwrites -p and -n)')
    parser.add_argument('-m', '--message',
                        action='store_true',
                        help='print comment message')
    parser.add_argument('-v', '--votes',
                        action='store_true',
                        help=('Look in comments for CI Jobs and detect '
                              'SUCCESS/FAILURE'))
    parser.add_argument('--json',
                        nargs='?',
                        const='lastcomment.json',
                        help=("Generate report to be stored in the json file "
                              "specified here. Ignores -v and -m "
                              "(default: 'lastcomment.json')"))
    parser.add_argument('-p', '--project',
                        help='only list hits for a specific project')

    args = parser.parse_args()
    names = {args.project: [args.name]}
    if args.file:
        with open(args.file) as f:
            names = yaml.load(f)

    if args.json:
        print "generating report %s" % args.json
        print "report is over last %s comments" % args.count
        report = {}
        timestamp = epoch(datetime.datetime.utcnow())
        report['timestamp'] = timestamp
        report['rows'] = []

    for project in names:
        print 'Checking project: %s' % project
        for name in names[project]:
            if name != 'Jenkins':
                url = ("https://wiki.openstack.org/wiki/ThirdPartySystems/%s" %
                       name.replace(" ", "_"))
                print 'Checking name: %s   -   %s' % (name, url)
            else:
                print('Checking name: %s' % name)
            try:
                if args.json:
                    report['rows'].append(generate_report(
                        name, args.count, project))
                else:
                    print_last_comments(name, args.count, args.message,
                                        project, args.votes)
            except Exception as e:
                print e
                pass

    if args.json:
        with open(args.json, 'w') as f:
            json.dump(report, f)


if __name__ == "__main__":
    main()
