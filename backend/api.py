from gevent import monkey; monkey.patch_all()
from gevent.pywsgi import WSGIServer
import flask
from flask import request, jsonify
import combined
import pdfscraper
import datetime
import os
import shutil
import numpy as np
import json
import comparer

host = '127.0.0.1'
port = 8800

app = flask.Flask(__name__)

@app.route('/getmainplans', methods=['GET'])
def mainPlans():
    if 'postcode' in request.args:
        postcode = request.args['postcode']
        return jsonify(combined.getMainPlans(newPostcode=postcode))
    else:
        return jsonify({'error': "Please provide a postcode"}) 


@app.route('/getsubplans', methods=['GET'])
def subPlans():
    if 'postcode' in request.args:
        postcode = request.args['postcode']
        return jsonify(combined.getSubPlans(newPostcode=postcode))
    else:
        return jsonify({'error': "Please provide a postcode"}) 


@app.route('/getbilldata', methods=['GET'])
def getbilldata():
    if 'dir' in request.args:
        try:
            ddir = "/".join(request.args['dir'].split("\\"))
            try:
                data = pdfscraper.extractData(ddir)
            except:
                newdir = ddir.split("/")
                fn = newdir[len(newdir)-1]
                newdir.remove(newdir[len(newdir)-1])
                newdir = "/".join(newdir)
                newdir += "/failure"
                shutil.copy2(ddir, newdir)
            os.remove(ddir)
            if data['postcode']:
                subplans = combined.getSubPlans(newPostcode=data['postcode'])
                '''subplans = None
                with open('newtest2000.json') as f:
                    subplans = json.load(f)'''
                return jsonify(comparer.getBestPlan(subplans, data))
            else:
                return jsonify({'error': "Corrupt or invalid PDF"}) 
        except:
            return jsonify({'error': "Corrupt or invalid PDF"}) 
        else:
            return jsonify({'error': "Postcode not found in PDF"}) 
    else:
        return jsonify({'error': "Please provide PDF"}) 


if __name__ == '__main__':
    server = WSGIServer((host, port), app)
    print("Listening on port %d.." %(port))
    server.serve_forever()