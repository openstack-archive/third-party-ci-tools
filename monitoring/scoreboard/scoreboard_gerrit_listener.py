#!/usr/bin/env python

import datetime
import re
import threading

import config
import db_helper
from infra import gerrit
import logger

USERS_UPDATE_INTERVAL = 60 * 5  # Seconds

class GerritCIListener():
    def __init__(self):
        self.ci_users = {}
        self.cfg = config.Config()
        self.db = db_helper.DBHelper(self.cfg).get()
        logger.init(self.cfg)
        self.log = logger.get('scoreboard-gerrit-listener')
        self.g = None

    def is_ci_user(self, username):
        return username in self.ci_users

    def determine_result(self, event):
        approvals = event.get(u'approvals', None)
        if approvals:
            for approval in approvals:
                vote = approval.get(u'value', 0)
                if int(vote) > 0:
                    return 'SUCCESS'

        comment = event[u'comment']
        if re.search('FAILURE|FAILED', comment, re.IGNORECASE):
            return 'FAILURE'
        elif re.search('ERROR', comment, re.IGNORECASE):
            return 'ERROR'
        elif re.search('NOT_REGISTERED', comment, re.IGNORECASE):
            return 'NOT_REGISTERED'
        elif re.search('ABORTED', comment, re.IGNORECASE):
            return 'ABORTED'
        elif re.search('merge failed', comment, re.IGNORECASE):
            return 'MERGE FAILED'
        elif re.search('SUCCESS|SUCCEEDED', comment, re.IGNORECASE):
            return 'SUCCESS'
        else:
            return 'UNKNOWN'

    def handle_gerrit_event(self, event):
        # We only care about comments on reviews
        if event[u'type'] == u'comment-added' and \
                self.is_ci_user(event[u'author'][u'username']):

            # special case for jenkins, it comments other things too, ignore those
            if event[u'author'][u'username'] == u'jenkins':
                if re.search('elastic|starting|merged',
                             event[u'comment'], re.IGNORECASE):
                    return

            # Lazy populate account info the in the db
            user_name = event[u'author'][u'username']
            ci_account = self.db.ci_accounts.find_one({'_id': user_name})
            if not ci_account:
                ci_account = {
                    '_id': user_name,
                    'user_name_pretty': event[u'author'][u'name']
                }
                self.db.ci_accounts.insert(ci_account)

            review_num_patchset = '%s,%s' % (event[u'change'][u'number'],
                                           event[u'patchSet'][u'number'])
            patchset = self.db.test_results.find_one({'_id': review_num_patchset})
            if patchset:
                self.log.info('Updating %s' % review_num_patchset)
                patchset['results'][user_name] = self.determine_result(event)
                self.db.test_results.save(patchset)
            else:
                patchset = {
                    '_id': review_num_patchset,
                    'results': {
                        user_name: self.determine_result(event)
                    },
                    'project': event[u'change'][u'project'],
                    'created': datetime.datetime.utcnow(),
                }
                self.log.info('Inserting %s' % review_num_patchset)
                self.db.test_results.insert(patchset)

    def periodic_query_users(self):
        self.log.info('Updating Third-Party CI user list')

        # Query for the most up to date list of users
        raw_members = self.g.lsMembers('Third-Party CI')

        # Cut off the first line, we don't care about the column headers
        del raw_members[0]

        current_members = {}

        # Format the results for easier consumption
        for line in raw_members:
            if line:
                id, user_name, full_name, email = line.split('\t')
                current_members[user_name] = {
                    'gerrit_id': id,
                    'full_name': full_name,
                    'email': email,
                }

        # Add a special one for jenkins, its not part of the group but
        # we want to count it too.
        current_members['jenkins'] = {
            'gerrit_id': -1,
            'full_name': 'jenkins',
            'email': ''
        }

        self.ci_users = current_members

        self.log.debug('Updated ci group members: ' + str(self.ci_users))

        # Schedule to re-run again
        threading.Timer(USERS_UPDATE_INTERVAL, self.periodic_query_users).start()

    def run(self):
        hostname = self.cfg.gerrit_hostname()
        username = self.cfg.gerrit_user()
        port = self.cfg.gerrit_port()
        keyfile = self.cfg.gerrit_key()
        keepalive = self.cfg.gerrit_keepalive()

        self.g = gerrit.Gerrit(hostname, username, port=port,
                               keyfile=keyfile, keepalive=keepalive)
        self.g.startWatching()

        self.periodic_query_users()

        while True:
            event = self.g.getEvent()
            try:
                self.handle_gerrit_event(event)
            except:
                self.log.exception('Failed to handle gerrit event: ' + str(event))
            self.g.eventDone()

if __name__ == '__main__':
    listener = GerritCIListener()
    listener.run()
