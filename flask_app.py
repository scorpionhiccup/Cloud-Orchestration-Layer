#! usr/bin/python

from flask import Flask
#from flask import json, jsonify, request
app = Flask(__name__)

@app.route("/")
def hello():
    return "Hello World"


if __name__ == '__main__':
    app.debug= True
    app.run()