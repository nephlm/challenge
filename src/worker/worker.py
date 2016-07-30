"""
Flask request routing.
"""

import flask
from flask import Flask, request

import requests

import os
import time

import logging
logging.basicConfig()

from apscheduler.schedulers.background import BackgroundScheduler

import workerLib

app = Flask(__name__, static_url_path='')
app.debug = False
app.config.from_object('config')
print(app.config['CC_IP'])
app.state = {'hello': False, 'ip': workerLib.getMyIPAddress()}

def hello():
    try:
        url = 'http://' + app.config['CC_IP'] + ':5000/api/worker/' + app.state['ip']
        resp = requests.get(url, timeout=2)
        resp.raise_for_status()
        app.state['hello'] = True
    except (requests.ConnectionError, requests.HTTPError):
        print('hello fail')
        pass

def tick():
    print('tick')
    if not app.state.get('hello'):
        hello()
    with open('/tmp/tick', 'a') as fp:
        fp.write(str(time.time()) + '\n')

app.scheduler = BackgroundScheduler()
app.scheduler.add_job(tick, 'interval', seconds=10)
app.scheduler.start()


@app.route('/api/hello')
def test():
    return flask.json.jsonify({'hello': 'goodbye'})

# Or specify port manually:
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 6000))
    app.run(host='0.0.0.0', port=port)

