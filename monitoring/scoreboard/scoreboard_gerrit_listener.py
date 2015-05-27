#!/usr/bin/env python

import datetime
import re
import threading

import config
import db_helper
from infra import gerrit
import logger
import users


class GerritCIListener():
    def __init__(self):
        self.ci_user_names = []
        self.cfg = config.Config()
        self.db = db_helper.DBHelper(self.cfg).get()
        logger.init(self.cfg)
        self.log = logger.get('scoreboard-gerrit-listener')

    def get_thirdparty_users(self):
        # TODO: figure out how to do the authentication..
        # thirdparty_group = '95d633d37a5d6b06df758e57b1370705ec071a57'
        # url = 'http://review.openstack.org/groups/%s/members' % thirdparty_group
        # members = eval(urllib.urlopen(url).read())
        members = users.third_party_group
        for account in members:
            username = account[u'username']
            self.ci_user_names.append(username)

    def is_ci_user(self, username):
        # TODO: query this from gerrit. Maybe save a copy in the db?
        return (username in self.ci_user_names) or (username == u'jenkins')

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

    def run(self):
        # TODO: Maybe split this into its own process? Its kind of annoying that
        # when modifying the UI portion of the project it stops gathering data..
        hostname = self.cfg.gerrit_hostname()
        username = self.cfg.gerrit_user()
        port = self.cfg.gerrit_port()
        keyfile = self.cfg.gerrit_key()

        g = gerrit.Gerrit(hostname, username, port=port, keyfile=keyfile)
        g.startWatching()

        self.get_thirdparty_users()

        while True:
            event = g.getEvent()
            try:
                self.handle_gerrit_event(event)
            except:
                self.log.exception('Failed to handle gerrit event: ')
            g.eventDone()


if __name__ == '__main__':
    listener = GerritCIListener()
    listener.run()