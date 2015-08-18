#! usr/bin/python

from flask import Flask
from flask import json, request
app = Flask(__name__)

def to_json(var):
	return json.dumps(var, indent=4, separators=(',', ': '))

@app.route("/")
def hello():
	return to_json("Root Url of the Page")

@app.route("/vm/create")
def vm_creation():
	name=request.args.get('name', '')
	instance_type=request.args.get('instance_type', 1)
	return to_json([name, instance_type])

@app.route("/vm/query")
def vm_query():
	vmid=request.args.get('vmid', '1')
	return to_json(vmid)

@app.route("/vm/destroy")
def vm_destroy():
	vmid=request.args.get('vmid', '1')
	return to_json(vmid)

@app.route("/vm/types")
def vm_types():
	return to_json('')

@app.route("/pm/list")
def pm_list():
	return to_json('')

@app.route("/pm/<pmid>/listvms")
def pm_listvms(pmid):
	return to_json(pmid)

@app.route("/pm/<pmid>")
def pm_query(pmid):
	return to_json(pmid)

@app.route("/image/list")
def image_list():
	list_images = [{'id':1, 'name':'Ubuntu-12.04-amd64'}]
	return to_json({'images':list_images})

if __name__ == '__main__':
    app.debug= True
    app.run()