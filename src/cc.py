"""
Flask request routing.
"""

import flask
from flask import Flask, request
import os

from apscheduler.schedulers.background import BackgroundScheduler

import logging
logging.basicConfig()

import ccLib

OK = 'okay'

app = Flask(__name__, static_url_path='')
app.debug = True
app.config.from_object('config')
app.ccConfig = {}
app.ccState = {}
app.state = {'ip': ccLib.getMyIPAddress()}

app.aws = ccLib.AWS()
app.aws.createKeypairs()
app.aws.pushSecurityGroups('worker')

app.queue = ccLib.Job

app.session = ccLib.initDB()

@app.route('/')
def index():
    """ Return the main html page. """
    # return 'hello'
    return app.send_static_file('index.html')


#===================================
# Workers/Nodes/AWS

@app.route('/api/regions')
def regions():
    return flask.json.jsonify({'result': app.aws.getRegions()})

@app.route('/api/start/<region>')
def startWorker(region):
    app.aws.startWorker(region)
    workers = ccLib.getWorkers(app.session, app.aws, force=True)
    return flask.json.jsonify({'result': workers})

@app.route('/api/<region>/<id>/stop')
def stopWorker(region, id):
    app.aws.stopWorker(region, id)
    workers = ccLib.getWorkers(app.session, app.aws, force=True)
    return flask.json.jsonify({'result': workers})

@app.route('/api/worker')
def getWorkers():
    print('in the url')
    workers = ccLib.Worker.getAll(app.session)
    return flask.json.jsonify({'result': workers})

@app.route('/api/worker/<ip>')
def hello(ip):
    print('got hello: %s' % ip)
    ccLib.Worker.gotHello(app.session, ip)
    return flask.json.jsonify({'result': app.state['ip']})



#===============================
# Work/Jobs

@app.route('/api/work', methods=['GET'])
def getWorkQueue():
    print('get the q')
    jobs = app.queue.getJobs(app.session, 20)
    return flask.json.jsonify({'result': jobs})

@app.route('/api/work', methods=['DELETE'])
def clearWork():
    """
    Completely empty the work queue.
    """
    app.queue.delete(app.session)
    return flask.json.jsonify({'result': OK})

@app.route('/api/work', methods=['POST'])
def addWork():
    work = request.get_json()
    print work['urls']
    app.queue.add(app.session, work['urls'])
    return flask.json.jsonify({'result': OK})

@app.route('/api/work/<ip>')
def getWork(ip):
    work = app.queue.claim(app.session, ip)
    return flask.json.jsonify({'result': work})

@app.route('/api/work/finish', methods=['POST'])
def finishWork():
    result = request.get_json()
    app.queue.finishJob(app.session, result.get('url'),
                result.get('id'), result.get('data'))
    return flask.json.jsonify({'result': OK})

@app.route('/api/work/fail', methods=['POST'])
def failWork():
    result = request.get_json()
    app.queue.failJob(app.session, result.get('url'),
                result.get('id'), result.get('data'))
    return flask.json.jsonify({'result': OK})

def tick():
    print('Wakeup Scheduler')
    # New thread, so it needs it's own session
    session = ccLib.initDB()
    ccLib.getWorkers(session, app.aws)

def interval():
    scheduler = BackgroundScheduler()
    scheduler.add_job(tick, 'interval', seconds=10)
    scheduler.start()
    print('Scheduler Started')

# Or specify port manually:
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8317))
    interval()
    app.run(host='0.0.0.0', port=port)
