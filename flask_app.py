#! usr/bin/python

from flask import Flask
from flask import json, request, render_template, jsonify
import random

app = Flask(__name__)

def uniqueid():
    seed = random.getrandbits(32)
    while True:
       yield seed
       seed += 1

vm_ids = []
unique_sequence=''
vm_data = {}
vm_types = {}

def to_json(var):
	if type(var)==list:
		return jsonify(*var)
	elif type(var)==dict:
		return jsonify(**var)
	else:
		return jsonify(var)

@app.route("/")
def list_all_urls():
	routes = []
	for rule in app.url_map.iter_rules():
		if "GET" in rule.methods:
			url = rule.rule
			routes.append(url)
	return render_template('routes.html', routes=routes)

@app.route("/vm/create")
def vm_creation():
	name=request.args.get('name', '')
	try:
		instance_type=int(request.args.get('instance_type', 1))
	except Exception, e:
		return "instance_type must be of type int."
	
	global vm_ids, unique_sequence 

	if not any(item['tid'] == instance_type for item in vm_types['types']):
		return "The instance_type is invalid"

	if len(vm_ids) == 0:
		unique_sequence=uniqueid()
		new_id = next(unique_sequence)
		vm_ids.append(new_id)
		vm_data[str(new_id)]={
			'name': name,
			'instance_type': instance_type 
		}
	else:
		while True:
			temp = str(next(unique_sequence))
			if temp not in vm_ids:
				vm_ids.append(temp)
				vm_data[temp]={
					'name': name,
					'instance_type': instance_type 
				}
				break

	return to_json([vm_data])

@app.route("/vm/query")
def vm_query():
	vmid=str(request.args.get('vmid', '1'))

	if vmid not in vm_data:
		return 'No Such ID exists'
	else:
		output={"vmid": vmid}
		output.update(vm_data[vmid])
		return to_json(output)

@app.route("/vm/destroy")
def vm_destroy():
	output = {}
	try:
		vmid=str(request.args.get('vmid'))
	except Exception, e:
		output['status']=0
	
	global vm_data

	try:
		del vm_data[vmid]
		output['status']=1
	except Exception, e:
		output['status']=0

	return to_json(output)

@app.route("/vm/types")
def vm_types():
	return to_json(vm_types)

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
	with open('types.json') as data_file:
		vm_types=json.load(data_file)
	app.run()