#!/usr/bin/env python
"""
CI Status Tool

Used for a quick stats collection on Third Party CIs for various OpenStack
projects.

Example usage:
    $ ./ci-status.py -v -u datera-ci \\
            -k /home/user/.ssh/id_rsa \\
            -c "Datera CI" -a datera-dsvm-full -t 2 \\
            -j openstack/cinder \\
            --failures --number-of-reports --is-reporting \\
            --jenkins_disagreement

Output:
    Gerrit Query: ssh -i /home/user/.ssh/id_rsa -p 29418 dater
    a-ci@review.openstack.org "gerrit query --format=JSON --comments --current-
    patch-set project:openstack/cinder NOT age:2d  reviewer:Datera CI "

    ##### DATERA-DSVM-FULL #####

    ####### --number-of-reports arg result #######

    40 results in 2 days

    ###### --is-reporting arg result #######

    Review: 263026 --> 2016-07-07T17:02:15+00:00

    ###### --failures arg result #######

    20% failures

    ###### --jenkins-disagreement arg result #######

    0% -1 Jenkins && +1 CI
    20% +1 Jenkins && -1 CI

Minimal usage:
    $ ./ci-status.py -u datera-ci -k /home/user/.ssh/id_rsa \\
            -j openstack/cinder -c "Datera CI" -a datera-dsvm-full \\
            --is-reporting

Output:
    ##### DATERA-DSVM-FULL #####
    Review: 263026 --> 2016-07-07T17:02:15+00:00

Passthrough query usage:
    $ ./ci-status.py -u datera-ci -k /home/user/.ssh/id_rsa \\
            -q "reviewer:{Some Body} -j openstack/cinder"

Output:
    Will be a large dictionary

Config example:

    # In .gerritqueryrc file in your $HOME directory
    # (or passed in via config option)

    [DEFAULT]
    verbose=True
    host=review.openstack.org
    username=datera-ci
    port=29418
    query_project=openstack/cinder
    keyfile=/home/user/.ssh/id_rsa

    # I would not recommend putting any other flags into this config
    # file otherwise you could introduce silent errors
    # For example:

        # Adding these fields
        ci_account=datera-ci
        ci_runner_name=datera-dsvm-full

        # Then running this command
        $ ./ci-status.py -c mellanox-ci --is-reporting

        # Would report a false negative for Datera. A CI
        # will show as non-reporting if you provide the
        # ci_account name of one CI and the ci_runner_name of
        # a different CI.  The tool has no way to tell that
        # these values do not belong together and will just
        # report that the CI has not posted within the specified
        # timeframe.

The "--all" flag:
    # In order to use this flag, you must first run this command:
    $ ./ci-status.py --scrape-wiki --force -j openstack/your_project

    # It will fill your .gerritquerycache file with information about
    # the various CIs for your desired OpenStack project

    # Now you're free to run commands with the --all flag
    $ ./ci-status -j openstack/you_project --all --is-reporting


Python Requirements:
    arrow
    lxml
    requests
    simplejson
    oslo.config>=3.12.0
"""

from __future__ import print_function, unicode_literals

import re
import sys
import functools
import subprocess
import shlex
import os.path
import threading
import Queue
from urlparse import urljoin
from StringIO import StringIO

import arrow
import simplejson as json
import requests
from lxml import etree

from oslo_config import cfg

opts = [
    cfg.BoolOpt('verbose',
                short='v',
                default=False),
    cfg.StrOpt('host',
               short='s',
               default=None,
               help=('Eg. review.openstack.org')),
    cfg.StrOpt('username',
               short='u',
               default=None,
               help=('Gerrit CI username')),
    cfg.StrOpt('keyfile',
               short='k',
               default=None,
               help=('Gerrit CI ssh private keyfile')),
    cfg.StrOpt('port',
               short='p',
               default=None,
               help=('Gerrit CI ssh port')),
    cfg.StrOpt('query-project',
               short='j',
               default=None,
               help=('Gerrit CI project to query')),
    cfg.IntOpt('time',
               short='t',
               default=2,
               help=('Time in days for query, default=2')),
    cfg.StrOpt('query',
               short='q',
               default='',
               help=('Passthrough Query')),
    cfg.StrOpt('ci-account',
               short='c',
               default='',
               help=('Filter result by this CI account (name or username)'
                     'eg. "Datera CI" or "datera-ci"')),
    cfg.StrOpt('ci-runner-name',
               short='a',
               default='',
               help=("Specific CI runner (eg. datera-dsvm-full) "
                     "to use for filtering results.  Useful if a "
                     "single CI account posts results for multiple "
                     "drivers. Can only be used if '--all' is NOT used")),
    cfg.BoolOpt('is-reporting',
                default=False,
                help=('Report if the CI specified by "-c/--ci-account"'
                      'reported within the time specified by "-t/--time"')),
    cfg.BoolOpt('number-of-reports',
                default=False,
                help=("Show number of reports within the last "
                      "'-t/--time' days")),
    cfg.BoolOpt('failures',
                default=False,
                help=("Show number and percentage of failures for last "
                      "'-t/--time' days")),
    cfg.BoolOpt('jenkins-disagreement',
                default=False,
                help=("Print percentage of disagreements between "
                      "CI and Jenkins")),
    cfg.BoolOpt('number-of-rechecks',
                default=False,
                help=("Print number of rechecks for a ci within the last"
                      "'-t/--time' days.  Heavily relies on information from "
                      "the ThirdPartyWiki.  Should only be used for "
                      "heruistic purposes")),
    cfg.BoolOpt('show-contacts',
                default=False,
                help=("Print contacts for each CI displayed")),
    cfg.BoolOpt('contact-list',
                default=False,
                help=("Print all contacts in project cache")),
    cfg.BoolOpt('contact-list-compact',
                default=False,
                help=("Print all contacts in project cache compactly")),
    cfg.BoolOpt('not-reporting-list',
                default=False,
                help=("Print all CIs for the project that have NOT reported "
                      "in the last '-t/--time' days")),
    cfg.BoolOpt('scrape-wiki',
                default=False,
                help=("Scrapes the wiki for CIs matching the project "
                      "specified by '-j/--query-project'.  Use '-f/--force' "
                      "to update from wiki instead of displaying cache")),
    cfg.BoolOpt('force',
                short='f',
                default=False,
                help=("Forces cache update")),
    cfg.BoolOpt('all',
                default=False,
                help=("Forces switches to be run on all detected CIs")),
]


CONF = cfg.ConfigOpts()
CONF.register_opts(opts)
CONF.register_cli_opts(opts)

CONFIG_FILE_NAME = os.path.join(os.path.expanduser("~"), '.gerritqueryrc')
CACHE_FILE_NAME = os.path.join(os.path.expanduser("~"), '.gerritquerycache')
WIKI_BASE_URL = "http://wiki.openstack.org"
THIRD_PARTY_WIKI_URL = urljoin(WIKI_BASE_URL, "/wiki/ThirdPartySystems")
WORKERS = 5

# From emailregex.com.  Should be fine for heuristically extracting emails
# we're not doing any validation :)
EMAIL_REGEX = r"([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)"


def main():
    CONF(default_config_files=[CONFIG_FILE_NAME])

    nargs = CONF
    pname = nargs.query_project.split("/")[-1]
    gquery = functools.partial(_gquery_base,
                               nargs.verbose,
                               nargs.keyfile,
                               nargs.port,
                               nargs.username,
                               nargs.host,
                               nargs.query_project,
                               nargs.time)

    # ###############################################
    # ############ Argument Handling ################
    # ###############################################

    if nargs.scrape_wiki:
        if nargs.verbose:
            print("\n####### --scrape-wiki result ######\n")
        from pprint import pprint
        pprint(get_reporting_dict(
               pname,
               force_update=nargs.force))

    if nargs.contact_list or nargs.contact_list_compact:
        contacts = []
        cis = get_reporting_dict(
                  pname,
                  force_update=nargs.force).keys()
        for ci in cis:
            contacts.extend(get_email_contacts(ci, pname))
        curr = contacts[0].split('@')[1]
        prev = curr
        for c in sorted(contacts, key=lambda x: x.split('@')[1]):
            prev = curr
            curr = c.split('@')[1]
            if prev != curr and not nargs.contact_list_compact:
                print()
            print(c)

    if not any((nargs.query,
                nargs.is_reporting,
                nargs.failures,
                nargs.jenkins_disagreement,
                nargs.number_of_reports,
                nargs.number_of_rechecks,
                nargs.show_contacts,
                nargs.not_reporting_list)):
        exit(0)

    # Handle defaults depending on if --all is passed
    if not nargs.all:
        cis = [(nargs.ci_account, nargs.ci_runner_name)]
        runner = nargs.ci_runner_name
        results = gquery(
                 " ".join((nargs.query,
                           "reviewer:{}".format(nargs.ci_account))))
    else:
        # We don't want to hit the wiki twice this one should always
        # be from the cache
        cis = [(k, v['name']) for (k, v) in get_reporting_dict(
                pname, force_update=False).items()]
        runner = ''
        results = gquery(
                 " ".join((nargs.query)))

    for ci, name in sorted(cis, key=lambda x: x[1]):
        if not nargs.not_reporting_list:
            print("\n##### {} #####".format(name.upper()))
        if nargs.number_of_reports:
            if nargs.verbose:
                print("\n####### --number-of-reports arg result #######\n")
            print_number_of_reports(results,
                                    ci,
                                    runner,
                                    nargs.time)

        if nargs.is_reporting:
            if nargs.verbose:
                print("\n###### --is-reporting arg result #######\n")
            print_is_reporting(results,
                               ci,
                               runner,
                               nargs.time)

        if nargs.failures:
            if nargs.verbose:
                print("\n###### --failures arg result #######\n")
            print_failure_results(results,
                                  ci,
                                  runner,
                                  nargs.time)

        if nargs.jenkins_disagreement:
            if nargs.verbose:
                print("\n###### --jenkins-disagreement arg result #######\n")
            print_jenkins_disagreement(results,
                                       ci,
                                       runner,
                                       nargs.time)

        if nargs.number_of_rechecks:
            if nargs.verbose:
                print("\n###### --number-of-rechecks arg result #######\n")
            print_number_of_rechecks(results,
                                     ci,
                                     runner,
                                     nargs.time,
                                     pname)

        if nargs.show_contacts:
            if nargs.verbose:
                print("\n####### --show-contacts result ######\n")
            print_email_contacts(ci, pname)

        if nargs.query:
            if nargs.verbose:
                print("\n####### --query result ######\n")
            print(gquery(nargs.query))

    if nargs.not_reporting_list and nargs.all:
        if nargs.verbose:
            print("\n####### --not-reporting-list result ######\n")
        not_reporting = []
        for ci, name in cis:
            result = get_is_reporting(results, ci, runner, nargs.time)
            if all(result):
                not_reporting.append(name)
        print("These CIs have not reported in {} days".format(nargs.time))
        for nr in not_reporting:
            print(nr.upper())
    # #######################################################

    exit(0)


def _base(keyfile, port, username, host):
    return 'ssh -i {keyfile} -p {port} {username}@{host}'.format(
        keyfile=keyfile, port=port, username=username, host=host)


def _gquery_base(verbose, keyfile, port, username, host, project, time, query):
    """
    Makes a large bulk-query to gerrit that can be further filtered
    after-the-fact so we play nice and don't hammer gerrit

    The size of the query largly depends on the "time" argument.  It's used
    to determine how many days old results can be.

        Eg.  time == 1  --> Only results >= 1 day old

    The time argument is also reliant on the "last modified" date, not
    "creation date".  So a review created six months ago, but modified two
    days ago will show up in a "time == 2" query
    """
    cmd = " ".join((_base(keyfile, port, username, host),
                   ("\"gerrit query --format=JSON --comments "
                    "--current-patch-set project:{} NOT age:{}d".format(
                        project, time)),
                    query,
                    "\""))
    if verbose:
        print("Gerrit Query: {}".format(cmd))
    # Strip the last result line which is just query metadata
    result = subprocess.check_output(shlex.split(cmd)).splitlines()[:-1]
    return [json.loads(elem) for elem in result]


def get_ci_comments(result, ci):
    """
    Returns a list of comments that match the specified CI as the reviewer in
    either name or username
    """
    return filter(
        lambda x: ci.upper() in (x['reviewer'].get('username', "").upper(),
                                 x['reviewer'].get('name', "").upper()),
        result['comments'])


def get_recheck_comments(result, ci_check):
    """
    ci_check is the recheck/rerun string for a specific ci as listed on
    its wiki page

    Makes the assumption that CI reviewer names will end with CI and
    filters out those comments to ensure we're not accidentally counting
    a comment made by a CI

    For example: Mellanox CI n the following example post a comment
    containing their recheck syntax, so this would be a false positive
    recheck request if we did not filter out all CI comments:

        "Build succeeded.  Cinder-ISER-ISCSI SUCCESS in 35m 11s
         Cinder-ISER-LIO SUCCESS in 35m 10s To re-run the job post
         'recheck cinder-mlnx' comment. For more information visit
         https://wiki.openstack.org/wiki/ThirdPartySystems/Mellanox_CI"
    """
    return filter(
        lambda x: (not x['reviewer']['name'].upper().endswith("CI") and
                   ci_check in x['message']),
        result['comments'])


def most_recent_ci_comment_timestamp(result, ci):
    """ Returns (review_id, timestamp, message) if comments exist for the CI
        Otherwise returns (review_id, timestamp(0), '')"""
    filtered = get_ci_comments(result, ci)
    try:
        body = sorted(filtered,
                      key=lambda x: x['timestamp'],
                      reverse=True)[0]

        return (result['number'],
                arrow.get(body['timestamp']),
                body['message'])

    except IndexError:
        return (result['number'],
                arrow.get(0),
                '')

# ###############################################
# ############# Report Functions ################
# ###############################################

"""
The 'results' argument accepted by these functions is an array of dicts
with these keys:

    ['status',
     'topic',
     'currentPatchSet',
     'url',
     'commitMessage',
     'createdOn',
     'number',
     'lastUpdated',
     'project',
     'comments',
     'branch',
     'owner',
     'open',
     'id',
     'subject']

This array is pulled directly from the Gerrit server via the constructed
query above.  Most of the logic is done on the 'comments' section of the
data structure since Third-Party CI results are left as comments on gerrit
reviews.

Only the most recent comments of any CI including Jenkins are taken into
account for printed statistics.  This might be beefed up in the future but for
not it's the easiest implementation
"""


def get_number_of_reports(results, ci, runner, argtime):
    """
    Report generator for --number-of-reports cli option
    """
    count = 0
    for result in results:
        review, tstamp, message = most_recent_ci_comment_timestamp(
            result, ci)
        if (arrow.now() - tstamp <=
                arrow.now() - arrow.now().replace(days=-argtime) and
                runner in message):
            count += 1
    return count


def get_is_reporting(results, ci, runner, argtime):
    """
    Report generator for --is-reporting cli option
    """
    if not results:
        return None
    rtstamp = arrow.get(0)
    rreview = 0
    for result in results:
        review, tstamp, message = most_recent_ci_comment_timestamp(
            result, ci)
        if tstamp > rtstamp:
            rtstamp = tstamp
            rreview = review
    return (rreview, rtstamp, message)


def get_failure_results(results, ci, runner, argtime):
    """
    Report generator for --failure cli option
    """
    count = 0
    fail_count = 0
    for result in results:
        review, tstamp, message = most_recent_ci_comment_timestamp(
            result, ci)
        if (arrow.now() - tstamp <=
                arrow.now() - arrow.now().replace(days=-argtime) and
                runner in message):
            count += 1
            if "FAILURE" in message:
                fail_count += 1
    return (count, fail_count)


def get_jenkins_disagreement(results, ci, runner, argtime):
    count = 0
    negative_disagree_count = 0
    positive_disagree_count = 0
    for result in results:
        jenkins_failure = False
        _, jtstamp, jmessage = most_recent_ci_comment_timestamp(
            result, 'jenkins')
        review, tstamp, message = most_recent_ci_comment_timestamp(
            result, ci)

        # Rough way of determining that both Jenkins and CI are referring
        # to the same patchset
        if tstamp >= jtstamp:

            # We only care if the result is within '-t' time
            if (arrow.now() - tstamp <=
                    arrow.now() - arrow.now().replace(days=-argtime) and
                    runner in message):
                count += 1

                # Filter out non-voting/stylistic/unit checks
                # 3rd party CIs don't run these checks, so we don't
                # care if they disagree
                jmessages = [elem for elem in jmessage.splitlines()
                             if not any([f in elem for f in ("non-voting",
                                                             "python",
                                                             "pylint",
                                                             "pep8",
                                                             "docs",)])]
                if any("FAILURE" in jm for jm in jmessages):
                    jenkins_failure = True

                if "FAILURE" not in message and jenkins_failure:
                    positive_disagree_count += 1

                if "FAILURE" in message and not jenkins_failure:
                    negative_disagree_count += 1
    return (count, negative_disagree_count, positive_disagree_count)


def get_rechecks(results, ci, runner, argtime, project):
    check = get_reporting_dict(project)[ci].get('retry')
    if not check:
        return None, None
    rechecks = 0
    for result in results:
        comments = get_recheck_comments(result, check)
        for comment in comments:
            tstamp = arrow.get(comment['timestamp'])
            if (arrow.now() - tstamp <=
                    arrow.now() - arrow.now().replace(days=-argtime)):
                rechecks += 1
    return (rechecks, check)


def get_email_contacts(ci, project):
    return get_reporting_dict(project)[ci].get('contact')


def get_reporting_dict(project, force_update=False):
    """
    Report generator for --scrape-wiki cli option
    """
    # Handle cache creation and loading
    cache = {}
    if os.path.exists(CACHE_FILE_NAME):
        with open(CACHE_FILE_NAME) as f:
            cache = json.load(f)
    else:
        with open(CACHE_FILE_NAME, 'w') as f:
            json.dump(cache, f)

    # By default we're just going to return the cache
    if not force_update:
        return cache.get(project)

    # Heavy update requests depending on wiki page links
    with requests.session() as c:
        resp = c.get(THIRD_PARTY_WIKI_URL)
        parser = etree.HTMLParser()
        root = etree.parse(StringIO(resp.text), parser).getroot()
        links = root.xpath('//a')

        # Now that we have all the links, we'll spawn a bunch of
        # worker threads and request them in parallel
        q = Queue.Queue()
        [q.put(urljoin(WIKI_BASE_URL, elem.attrib['href']))
         for elem in links
         if elem.text and elem.text.upper().endswith("CI")]
        workers = []
        results = {}
        for _ in xrange(WORKERS):
            workers.append(
                threading.Thread(target=_link_checker,
                                 args=(project, c, parser, q, results)))
        for thread in workers:
            thread.daemon = True
            thread.start()

        q.join()
        cache[project] = results

        # Truncate file since we're writing the whole cache
        with open(CACHE_FILE_NAME, 'w') as f:
            json.dump(cache, f)
        return results


# ###############################################
# ####### CommandLine Print Functions ###########
# ###############################################


def print_failure_results(results, ci, runner, argtime):
    count, fail_count = get_failure_results(results, ci, runner, argtime)
    if count > 0:
        print("{}% failures".format(
            int(float(fail_count)/count * 100)))


def print_is_reporting(results, ci, runner, argtime):
    try:
        rreview, rtstamp, message = \
            get_is_reporting(results, ci, runner, argtime)
    except ValueError:
        print("No results found, ci: {}".format(ci))
        return

    if (arrow.now() - rtstamp <=
            arrow.now() - arrow.now().replace(days=-argtime) and
            runner in message):
        print("Review: {} --> {}".format(
            rreview, arrow.get(rtstamp)))
    else:
        print("{}+ days".format(argtime))


def print_number_of_reports(results, ci, runner, argtime):
    count = get_number_of_reports(results, ci, runner, argtime)
    print("{} results in {} days".format(
        count, argtime))


def print_jenkins_disagreement(results, ci, runner, argtime):
    count, negative_disagree_count, positive_disagree_count = \
        get_jenkins_disagreement(results, ci, runner, argtime)
    if count > 0:
        print("{}% -1 Jenkins && +1 CI".format(
            int(float(positive_disagree_count)/count * 100)))
        print("{}% +1 Jenkins && -1 CI".format(
            int(float(negative_disagree_count)/count * 100)))


def print_number_of_rechecks(results, ci, runner, argtime, project):
    recheck_count, check = get_rechecks(results, ci, runner, argtime, project)
    if recheck_count is None:
        print("No recheck string found on Wiki page")
    else:
        print("{} rechecks in {} days, recheck string: {}".format(
            recheck_count, argtime, check))


def print_email_contacts(ci, project):
    print("Contact: {}".format(get_email_contacts(ci, project)))

# ###############################################


# Used for Thread workers
def _link_checker(project, session, parser, q, results):
    while True:
        try:
            link = q.get()
            resp = session.get(link)
            root = etree.parse(StringIO(resp.text), parser).getroot()
            # Grab all the table data entries
            tds = root.xpath("//td/b")
            try:
                # Filter for supported openstack services
                text = [elem.tail for elem in tds
                        if elem.text.upper() == "OPENSTACK PROGRAMS"][0]
                # Filter for gerrit account name
                if project.upper() in text.upper():
                    name = [elem.tail for elem in tds
                            if elem.text.upper() == "GERRIT ACCOUNT"][0]
                    # Handle oddly formatted names
                    name = name.lstrip(": ").split()[0].split("@")[0]
                    results[name] = {}
                    results[name]['name'] = link.split("/")[-1].upper()
                    # Try and get a retry syntax from the page
                    try:
                        # Ugly stripping to handle the weird inconsistent
                        # formats used on the wiki
                        retry_elem = root.xpath(
                            "//p/b")[0].tail.strip().strip(
                                    "\"'").split("(")[0].strip().strip("\"")
                        for char in (":", "="):
                            if char in retry_elem:
                                retry_elem = retry_elem.split(
                                    char)[1].strip().strip("\"")
                        # Any CI with this sting hasn't updated
                        # their wiki page with a retry syntax
                        if "please update" not in retry_elem.lower():
                            results[name]['retry'] = retry_elem
                    except IndexError:
                        pass
                    # Try and get maintaner info from the page
                    try:
                        contact_elem = [
                            elem.tail for elem in tds
                            if elem.text.upper() == "CONTACT INFORMATION"][0]
                        emails = re.findall(EMAIL_REGEX, contact_elem)
                        results[name]['contact'] = emails
                    except IndexError:
                        pass
            except IndexError:
                print("No 'OpenStack Programs' or 'Gerrit Account' field",
                      link)
            q.task_done()
        except Queue.Empty:
            return

if __name__ == "__main__":
    sys.exit(main())
