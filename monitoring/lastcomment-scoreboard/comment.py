#!/usr/bin/env python

"""Contains the Comments and Job classes."""

import datetime

TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


class Job(object):
    """This class describes a job that was discovered in a comment."""

    name = None
    time = None
    url = None

    # SUCCESS or FAILURE
    result = None

    # the raw job message line
    message = ''

    def __init__(self, name, time, url, result=None, message=None):
        self.name = name
        self.time = time
        self.url = url
        self.result = result
        self.message = message

    def __str__(self):
        return ("%s result='%s' in %s Logs = '%s' " % (
            self.name,
            self.result,
            self.time,
            self.url))

    @staticmethod
    def parse(job_str):
        """Parse out the raw job string and build the job obj."""
        job_split = job_str.split()
        job_name = job_split[1]
        if 'http://' in job_name or 'ftp://' in job_name:
            # we found a bogus entry w/o a name.
            return None

        url = job_split[2]
        result = job_split[4]
        time = None
        if result == 'SUCCESS' or result == 'FAILURE':
            if 'in' in job_str and job_split[5] == 'in':
                time = " ".join(job_split[6:])

        return Job(job_name, time, url, result, job_str)


class Comment(object):
    """Class that describes a gerrit Comment."""

    date = None
    number = None
    subject = None
    now = None

    def __init__(self, date, number, subject, message):
        super(Comment, self).__init__()
        self.date = date
        self.number = number
        self.subject = subject
        self.message = message
        self.now = datetime.datetime.utcnow().replace(microsecond=0)
        self.jobs = []

        self._vote()

    def _vote(self):
        """Try and parse the job out of the comment message."""
        for line in self.message.splitlines():
            if line.startswith("* ") or line.startswith("- "):
                job = Job.parse(line)
                self.jobs.append(job)


    def __str__(self):
        return ("%s (%s old) %s '%s' " % (
            self.date.strftime(TIME_FORMAT),
            self.age(),
            self.url(), self.subject))

    def age(self):
        return self.now - self.date

    def url(self):
        return "https://review.openstack.org/%s" % self.number

    def __le__(self, other):
        # self < other
        return self.date < other.date

    def __repr__(self):
        # for sorting
        return repr((self.date, self.number))


def get_comments(change, name):
    """Generator that returns all comments by name on a given change."""
    body = None
    for message in change['messages']:
        if 'author' in message and message['author']['name'] == name:
            if (message['message'].startswith("Uploaded patch set") and
               len(message['message'].split()) is 4):
                # comment is auto created from posting a new patch
                continue
            date = message['date']
            body = message['message']
            # https://review.openstack.org/Documentation/rest-api.html#timestamp
            # drop nanoseconds
            date = date.split('.')[0]
            date = datetime.datetime.strptime(date, TIME_FORMAT)
            yield date, body
