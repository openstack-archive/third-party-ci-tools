#!/usr/bin/env python

import datetime

from bson import json_util
from flask import Flask, request, render_template, send_from_directory
import pymongo

import config
import db_helper
import logger


cfg = config.Config()

app = Flask(__name__)
app.debug = True

logger.init(cfg)

db = db_helper.DBHelper(cfg).get()


@app.route('/')
def index():
    return render_template('index.html', host=request.host)


@app.route('/static/<path:path>')
def send_js(path):
    # TODO: We should probably use a real webserver for this..
    return send_from_directory('static', path)


@app.route('/ci-accounts', methods=['GET'])
def ci_accounts():
    return json_util.dumps(db.ci_accounts.find())


@app.route('/results', methods=['GET'])
def results():
    # TODO: We should have a cache for these requests
    # so we don't get hammered by reloading pages
    project = request.args.get('project', None)
    username = request.args.get('user', None)
    count = request.args.get('count', None)
    start = request.args.get('start', None)
    timeframe = request.args.get('timeframe', None)

    return query_results(project, username, count, start, timeframe)


def query_results(project, user_name, count, start, timeframe):
    query = {}
    if project:
        query['project'] = project
    if user_name:
        query['results.' + user_name] = {'$exists': True, '$ne': None}
    if timeframe:
        num_hours = int(timeframe)
        current_time = datetime.datetime.utcnow()
        start_time = current_time - datetime.timedelta(hours=num_hours)
        query['created'] = {'$gt': start_time}
    records = db.test_results.find(query).sort('created', pymongo.DESCENDING)
    return json_util.dumps(records)


if __name__ == '__main__':
    app.run(host='0.0.0.0')
