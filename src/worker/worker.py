"""
Flask request routing.
"""

import flask
from flask import Flask, request

import os
import time

from apscheduler.schedulers.background import BackgroundScheduler

import workerLib

app = Flask(__name__, static_url_path='')
app.debug = True
app.config.from_object('config')
app.state = {'hello': False}

def hello():
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


@app.route('/api/test')
def test():
    return flask.json.jsonify({'hello': 'goodbye'})

# Or specify port manually:
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 6000))
    app.run(host='0.0.0.0', port=port)
