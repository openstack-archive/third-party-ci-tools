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

PER_PAGE = 25

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
    count = request.args.get('count', None)
    skip = request.args.get('skip', None)
    timeframe = request.args.get('timeframe', None)
    start = request.args.get('start', None)
    end = request.args.get('end', None)

    return query_results(project, count, skip, timeframe, start, end)

def query_results(project, count, skip, timeframe, start, end):
    query = {}
    date_format = '%Y-%m-%d'
    if project:
        query['project'] = project

    page_size = int(skip) if skip else PER_PAGE
    current_page = int(count) if count else 1

    if timeframe:
        num_hours = int(timeframe)
        current_time = datetime.datetime.utcnow()
        start_time = current_time - datetime.timedelta(hours=num_hours)
        query['created'] = {'$gt': start_time}
    elif start and end:
        start = datetime.datetime.strptime(start, date_format)
        end = datetime.datetime.strptime(end, date_format)
        query['created'] = {'$gte': start, '$lt': end}

    records = db.test_results.find(query).sort('created', pymongo.DESCENDING).skip(page_size*(current_page-1)).limit(page_size)
    total = {'total': db.test_results.find(query).count()}
    response = {'total': total, 'records': records}

    return json_util.dumps(response)


if __name__ == '__main__':
    app.run(host='0.0.0.0')
