"""
Flask request routing.

Functions as the web front end accepts any communication from the
workers.  In practice all important communication originates from
the workers so this is were all the events trigger.
"""

import flask
from flask import Flask, request
import os

# from apscheduler.schedulers.background import BackgroundScheduler

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
    """
    Get the list of regions
    """
    return flask.json.jsonify({'result': app.aws.getRegions()})

@app.route('/api/start/<region>')
def startWorker(region):
    """
    start a worker in the specified region.
    """
    app.aws.startWorker(region)
    workers = ccLib.getWorkers(app.session, app.aws, force=True)
    return flask.json.jsonify({'result': workers})

@app.route('/api/<region>/<id>/stop')
def stopWorker(region, id):
    """
    Stop the worker with the given id in the given region.
    """
    app.aws.stopWorker(region, id)
    workers = ccLib.getWorkers(app.session, app.aws, force=True)
    return flask.json.jsonify({'result': workers})

@app.route('/api/worker')
def getWorkers():
    """
    Get a list of all workers.
    """
    workers = ccLib.Worker.getAll(app.session)
    return flask.json.jsonify({'result': workers})

@app.route('/api/worker/<ip>')
def hello(ip):
    """
    Receive the Hello message from the worker.
    """
    ccLib.Worker.gotHello(app.session, ip)
    return flask.json.jsonify({'result': app.state['ip']})



#===============================
# Work/Jobs

@app.route('/api/work', methods=['GET'])
def getWorkQueue():
    """
    Get next 20 (or less) items from the queue.
    """
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
    """
    submit a list of URLs to be processed.

    Post data should have a `urls` key associated with a
    list of strings.
    """
    work = request.get_json()
    app.queue.add(app.session, work['urls'])
    return flask.json.jsonify({'result': OK})

@app.route('/api/work/<ip>')
def getWork(ip):
    """
    Request a segment of work.  Respond with a URL to
    process.
    """
    work = app.queue.claim(app.session, ip)
    return flask.json.jsonify({'result': work})

@app.route('/api/work/finish', methods=['POST'])
def finishWork():
    """
    Turn in work.

    Post data:
        {
        'url': The url that was assigned,
        'id': IP address of worker,
        'data': the results
        }
    """
    result = request.get_json()
    app.queue.finishJob(app.session, result.get('url'),
                result.get('id'), result.get('data'))
    return flask.json.jsonify({'result': OK})

@app.route('/api/work/fail', methods=['POST'])
def failWork():
    """
    Worker failed to complete the task and is returning it.

    Post data:
        {
        'url': The url that was assigned,
        'id': IP address of worker,
        'data': may contain information about the failure
        }

    """
    result = request.get_json()
    app.queue.failJob(app.session, result.get('url'),
                result.get('id'), result.get('data'))
    return flask.json.jsonify({'result': OK})

# def tick():
#     print('Wakeup Scheduler')
#     # New thread, so it needs it's own session
#     session = ccLib.initDB()
#     ccLib.getWorkers(session, app.aws)

# def interval():
#     scheduler = BackgroundScheduler()
#     scheduler.add_job(tick, 'interval', seconds=10)
#     scheduler.start()
#     print('Scheduler Started')

# Or specify port manually:
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8317))
    # interval()
    app.run(host='0.0.0.0', port=port)
