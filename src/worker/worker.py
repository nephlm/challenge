"""
Worker processing.  This file only services a single endpoint used
to verify communication.  The majority of the work originates from
the scheduler.
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
    # For dev on a machine running both cc.py and worker.py
    app.config['CC_IP'] = '127.0.0.1'
    app.state['ip'] = '127.0.0.1'

app.state['baseUrl'] = 'http://%s:%s' % (app.config['CC_IP'], app.config['CC_PORT'])

def hello():
    """
    Try and send the Hello message to CC.
    """
    try:
        url = '%s/api/worker/%s' % (app.state['baseUrl'],
                    app.state['ip'])
        resp = requests.get(url, timeout=2)
        resp.raise_for_status()
        app.state['hello'] = True
    except (requests.ConnectionError, requests.HTTPError):
        print('Failed to Send Hello Message')
        pass

def getWork():
    """
    Request a job from CC and process it.  If any network communication
    issues arise fail the job.  If the job can't be failed (can't talk
    to CC), queue for failing later.
    """
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
        # Some sort of issue (bad URl, network, results, etc)
        # Try to fail the job
        try:
            finishOrFail('fail', jobUrl, app.state['ip'], None)
        except (requests.ConnectionError, requests.HTTPError, requests.RequestException):
            if jobUrl:
                # queue it for later failing.
                app.state['failedJobs'].append(jobUrl)

def finishOrFail(op, jobUrl, id, data):
    """
    Send a message to CC with success or failure information.

    @param op: string -- 'fail' or 'finish'
    @param jobUrl: string -- The URL that was processed (or failed)
    @param id: string -- IP of the worker.
    @param data: The result of the processing.  None if the job failed.

    @returns: The request.

    @Note: This process doesn't catch any errors, that's left to the
    caller.
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
        except (requests.ConnectionError, requests.HTTPError, requests.RequestException):
            newQueue.append(job)
    app.state['failedJobs'] = newQueue


def tick():
    """
    Scheduler callback.  Entry point into the worker.
    """
    if not app.state.get('hello'):
        hello()
    failQueue()
    getWork()

def interval():
    """
    Setup the scheduler.
    """
    scheduler = BackgroundScheduler()
    scheduler.add_job(tick, 'interval', seconds=10)
    scheduler.start()
    print('Scheduler Started')


@app.route('/api/hello')
def getHello():
    """
    The one end point.  Replies with a static method.
    """
    return flask.json.jsonify({'hello': 'goodbye'})

# Or specify port manually:
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 6000))
    interval()
    app.run(host='0.0.0.0', port=port)

