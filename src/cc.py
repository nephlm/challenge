"""
Flask request routing.
"""

import flask
from flask import Flask, request
import os

import ccLib

app = Flask(__name__, static_url_path='')
app.debug = True
app.config.from_object('config')
app.ccConfig = {}
app.ccState = {}

app.aws = ccLib.AWS()
app.aws.createKeypairs()
app.aws.pushSecurityGroups()

app.queue = ccLib.Job

app.session = ccLib.initDB()

@app.route('/')
def index():
    """ Return the main html page. """
    # return 'hello'
    return app.send_static_file('index.html')

@app.route('/api/regions')
def regions():
    # aws = ccLib.AWS()
    #print(aws.getRegions())
    return flask.json.jsonify({'result': app.aws.getRegions()})

@app.route('/api/start/<region>')
def startWorker(region):
    # aws = ccLib.AWS()
    app.aws.startWorker(region)
    return flask.json.jsonify({'result': app.aws.getWorkers()})

@app.route('/api/<region>/<id>/stop')
def stopWorker(region, id):
    # aws = ccLib.AWS()
    app.aws.stopWorker(region, id)
    return flask.json.jsonify({'result': app.aws.getWorkers()})

@app.route('/api/work', methods=['POST'])
def addWork():
    work = request.get_json()
    print work['urls']
    app.queue.submit(app.session, work['urls'])
    return flask.json.jsonify({'result': 'okay'})

@app.route('/api/work/<id>')
def getWork(id):
    work = queue.claim(id)
    return flask.json.jsonify({'result': work})

@app.route('/api/work/finish', methods=['POST'])
def finishWork(id):
    result = request.get_json()
    queue.finishJob(result.get('url'), result.get('id'), result.get('data'))
    return flask.json.jsonify({'result': 'okay'})

@app.route('/api/work/fail', methods=['POST'])
def failWork(id):
    result = request.get_json()
    queue.failJob(result.get('url'), result.get('id'), result.get('data'))
    return flask.json.jsonify({'result': 'okay'})


@app.route('/api/worker')
def getWorkers():
    print('getWorker()')
    return flask.json.jsonify({'result': app.aws.getWorkers()})

@app.route('/api/worker/<id>')
def hello(id):
    return flask.json.jsonify({'result': ccLib.getMyIPAddress()})


# Or specify port manually:
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
