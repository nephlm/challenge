"""
Flask request routing.
"""

import flask
from flask import Flask, request
import os

import ccLib

OK = 'okay'

app = Flask(__name__, static_url_path='')
app.debug = True
app.config.from_object('config')
app.ccConfig = {}
app.ccState = {}

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
    workers = ccLib.getWorkers(app.session, app.aws)
    return flask.json.jsonify({'result': workers})

@app.route('/api/worker/<ip>')
def hello(ip):
    print('got hello: %s' % ip)
    return flask.json.jsonify({'result': ccLib.getMyIPAddress()})



#===============================
# Work/Jobs

@app.route('/api/work', methods=['GET'])
def getWorkQueue():
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
def finishWork(id):
    result = request.get_json()
    queue.finishJob(result.get('url'), result.get('id'), result.get('data'))
    return flask.json.jsonify({'result': OK})

@app.route('/api/work/fail', methods=['POST'])
def failWork(id):
    result = request.get_json()
    queue.failJob(result.get('url'), result.get('id'), result.get('data'))
    return flask.json.jsonify({'result': OK})



# Or specify port manually:
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
