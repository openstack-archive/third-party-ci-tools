#!/usr/bin/env python

"""Generate a report on CI comments and jobs."""

import argparse
import calendar
import datetime
import json
import yaml

import requests

import comment


def query_gerrit(name, count, project, quiet=False):
    """Query gerrit and fetch the comments."""
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
        if not quiet:
            print("query: '%s' failed with:\n%s" % (query, r.text))
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


def get_votes(comments):
    """Get the stats for all of the jobs in all comments."""
    last_success = None
    votes = {'success': 0, 'failure': 0}
    for cmt in comments:
        if cmt.jobs:
            for job in cmt.jobs:
                if job.result == "SUCCESS":
                    if job.name not in votes:
                        votes[job.name] = {'success': 1, 'failure': 0,
                                           'last_success': cmt}
                    elif votes[job.name]['success'] == 0:
                        votes[job.name]['success'] += 1
                        votes[job.name]['last_success'] = cmt
                    else:
                        votes[job.name]['success'] += 1

                    votes['success'] += 1
                    if not last_success:
                        last_success = cmt
                elif job.result == 'FAILURE':
                    if job.name not in votes:
                        votes[job.name] = {'success': 0, 'failure': 1,
                                           'last_success': None}
                    else:
                        votes[job.name]['failure'] += 1

                    votes['failure'] += 1
                else:
                    # We got something other than
                    # SUCCESS or FAILURE
                    # for now, mark it as a failure
                    if job.name not in votes:
                        votes[job.name] = {'success': 0, 'failure': 1,
                                           'last_success': None}
                    else:
                        votes[job.name]['failure'] += 1
                    votes['failure'] += 1
                    #print("Job %(name)s result = %(result)s" %
                    #      {'name': job.name,
                    #       'result': job.result})
    return votes, last_success


def generate_report(name, count, project, quiet=False):
    """Process all of the comments and generate the stats."""
    result = {'name': name, 'project': project}
    last_success = None

    comments = query_gerrit(name, count, project)
    if not comments:
        print("No comments found. CI SYSTEM UNKNOWN")
        return

    votes, last_success = get_votes(comments)
    result['last_seen'] = {'date': epoch(comments[0].date),
                           'age': str(comments[0].age()),
                           'url': comments[0].url()}
    last = len(comments) - 1
    result['first_seen'] = {'date': epoch(comments[last].date),
                            'age': str(comments[last].age()),
                            'url': comments[last].url()}
    if not quiet:
        print("  first seen: %s (%s old) %s" % (comments[last].date,
                                                comments[last].age(),
                                                comments[last].url()))
        print("  last seen: %s (%s old) %s" % (comments[0].date,
                                               comments[0].age(),
                                               comments[0].url()))
    if last_success:
        result['last_success'] = {'date': epoch(comments[0].date),
                                  'age': str(comments[0].age()),
                                  'url': comments[0].url()}
        if not quiet:
            print("  last success: %s (%s old) %s" % (last_success.date,
                                                      last_success.age(),
                                                      last_success.url()))
    else:
        result['last_success'] = None
        if not quiet:
            print("  last success:  None")

    result['jobs'] = []
    jobs = dict.fromkeys(votes, 0)
    jobs.pop('success', None)
    jobs.pop('failure', None)
    for job in jobs:
        reported_comments = votes[job]['success'] + votes[job]['failure']
        if votes[job]['failure'] == 0:
            success_rate = 100
        else:
            success_rate = int(votes[job]['success'] /
                               float(reported_comments) * 100)

        if not quiet:
            print("  Job %(job_name)s %(success_rate)s%% success out of "
                  "%(comments)s comments S=%(success)s, F=%(failures)s"
                  % {'success_rate': success_rate,
                     'job_name': job,
                     'comments': reported_comments,
                     'success': votes[job]['success'],
                     'failures': votes[job]['failure']})

        # Only print the job's last success rate if the succes rate
        # is low enough to warrant showing it.
        if votes[job]['last_success'] and success_rate <= 60 and not quiet:
            print("      last success: %s (%s old) %s" %
                  (votes[job]['last_success'].date,
                   votes[job]['last_success'].age(),
                   votes[job]['last_success'].url()))

        job_entry = {'name': job, 'success_rate': success_rate,
                     'num_success': votes[job]['success'],
                     'num_failures': votes[job]['failure'],
                     'comments': reported_comments,
                     }
        if votes[job]['last_success']:
            job_entry['last_success'] = {
                'date': epoch(votes[job]['last_success'].date),
                'age': str(votes[job]['last_success'].age()),
                'url': votes[job]['last_success'].url()}
        else:
            job_entry['last_success'] = None

        result['jobs'].append(job_entry)

    total = votes['success'] + votes['failure']
    if total > 0:
        success_rate = int(votes['success'] / float(total) * 100)
        result['success_rate'] = success_rate
        if not quiet:
            print("Overall success rate: %s%% of %s comments" %
                  (success_rate, len(comments)))

    return result


def epoch(timestamp):
    return int(calendar.timegm(timestamp.timetuple()))


def main():
    parser = argparse.ArgumentParser(description='list most recent comment by '
                                     'reviewer')
    parser.add_argument('-n', '--name',
                        default="Jenkins",
                        help='unique gerrit name of the reviewer')
    parser.add_argument('-c', '--count',
                        default=10,
                        type=int,
                        help='number of records to evaluate')
    parser.add_argument('-i', '--input',
                        default=None,
                        help='yaml file containing list of names to search on'
                             'project: name'
                             ' (overwrites -p and -n)')
    parser.add_argument('-o', '--output',
                        default=None,
                        help='write the output to a file. Defaults to stdout.')
    parser.add_argument('-j', '--json',
                        default=False,
                        action="store_true",
                        help=("generate report output in json format."))
    parser.add_argument('-p', '--project',
                        help='only list hits for a specific project '
                             '(ie: openstack/cinder)')

    args = parser.parse_args()
    names = {args.project: [args.name]}

    quiet = False
    if args.json and not args.output:
        # if we are writing json data to stdout
        # we shouldn't be outputting anything else
        quiet = True

    if args.input:
        with open(args.input) as f:
            names = yaml.load(f)

    if args.json:
        if not quiet:
            print "generating report %s" % args.json
            print "report is over last %s comments" % args.count
        report = {}
        timestamp = epoch(datetime.datetime.utcnow())
        report['timestamp'] = timestamp
        report['rows'] = []

    for project in names:
        if not quiet:
            print 'Checking project: %s' % project
        for name in names[project]:
            if name != 'Jenkins':
                url = ("https://wiki.openstack.org/wiki/ThirdPartySystems/%s" %
                       name.replace(" ", "_"))
                if not quiet:
                    print 'Checking name: %s   -   %s' % (name, url)
            else:
                if not quiet:
                    print('Checking name: %s' % name)
            try:
                report_result = generate_report(name, args.count, project,
                                                quiet)
                if args.json:
                    report['rows'].append(report_result)
            except Exception as e:
                print e
                pass

    if args.json:
        if not args.output:
            print(json.dumps(report))
        else:
            with open(args.output, 'w') as f:
                json.dump(report, f)


if __name__ == "__main__":
    main()
