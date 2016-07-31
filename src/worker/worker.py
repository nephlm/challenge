"""
Flask request routing.
"""

import flask
from flask import Flask, request

import requests
from apscheduler.schedulers.background import BackgroundScheduler

import os
import time

import logging
logging.basicConfig()

import workerLib

LOCAL_DEV = False

app = Flask(__name__, static_url_path='')
app.debug = False
app.config.from_object('config')
app.config['CC_PORT'] = 8317
app.state = {'hello': False,
            'ip': workerLib.getMyIPAddress(),
            'failedJobs': []}
if LOCAL_DEV:
    app.config['CC_IP'] = '127.0.0.1'
    app.state['ip'] = '127.0.0.1'
    print(app.config['CC_IP'])

app.state['baseUrl'] = 'http://%s:%s' % (app.config['CC_IP'], app.config['CC_PORT'])

def hello():
    try:
        url = '%s/api/worker/%s' % (app.state['baseUrl'],
                    app.state['ip'])
        # url = 'http://' + app.config['CC_IP'] + ':' + str(app.state['cc_port']) + '/api/worker/' + app.state['ip']
        resp = requests.get(url, timeout=2)
        resp.raise_for_status()
        app.state['hello'] = True
    except (requests.ConnectionError, requests.HTTPError):
        print('Failed to Send Hello Message')
        pass

def getWork():
    jobUrl = ''
    try:
        reqUrl = '%s/api/work/%s' % (app.state['baseUrl'],
                    app.state['ip'])
        jobReq = requests.get(reqUrl, timeout=2)
        jobReq.raise_for_status()
        jobUrl = flask.json.loads(jobReq.text)['result']
        if jobUrl:
            jobData = requests.get(jobUrl, timeout=4)
            jobData.raise_for_status()
            r = finishOrFail('finish', jobUrl, app.state['ip'], jobData.text)
            r.raise_for_status()
    except (requests.ConnectionError, requests.HTTPError, requests.RequestException):
        # Try to fail the job
        try:
            finishOrFail('fail', jobUrl, app.state['ip'], None)
        except (requests.ConnectionError, requests.HTTPError, requests.RequestException):
            if jobUrl:
                app.state['failedJobs'].append(jobUrl)

def finishOrFail(op, jobUrl, id, data):
    """
    """
    if op not in ('finish', 'fail'):
        op = 'fail' #safer
    completionUrl = '%s/api/work/%s' % (app.state['baseUrl'], op)
    postData = {
        'url': jobUrl,  # The url that specified in the job request.
        'id': id,  # id of worker, (e.g. ip address)
        'data': data  # Raw return or None
    }
    r = requests.post(completionUrl, json=postData)
    r.raise_for_status()
    return r

def failQueue():
    """
    Make a new attempt to report failure to CC for any jobs that
    couldn't be completed.
    """
    newQueue = []
    for job in app.state['failedJobs']:
        try:
            finishOrFail('fail', job, app.state['ip'], None)
        except (requests.ConnectionError, requests.HTTPError):
            newQueue.append(job)
    app.state['failedJobs'] = newQueue


def tick():
    print('Wakeup Scheduler')
    if not app.state.get('hello'):
        hello()
    failQueue()
    getWork()

def interval():
    scheduler = BackgroundScheduler()
    scheduler.add_job(tick, 'interval', seconds=10)
    scheduler.start()
    print('Scheduler Started')


@app.route('/api/hello')
def getHello():
    return flask.json.jsonify({'hello': 'goodbye'})

# Or specify port manually:
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 6000))
    interval()
    app.run(host='0.0.0.0', port=port)

