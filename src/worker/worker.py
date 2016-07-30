"""
Flask request routing.
"""

import flask
from flask import Flask, request
import os

import workerLib

app = Flask(__name__, static_url_path='')
app.debug = True
app.config.from_object('config')

@app.route('/api/test')
def test():
    return flask.json.jsonify({'hello': 'goodbye'})

# Or specify port manually:
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 6000))
    app.run(host='0.0.0.0', port=port)
