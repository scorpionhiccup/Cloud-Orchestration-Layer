#! usr/bin/python

from flask import Flask, json, request, render_template, \
	jsonify, redirect, url_for
from sh import virsh
from app import app, db, models
import app as app_globals
import os, sys
#import src.run
#, virt-install
from flask.ext.sqlalchemy import SQLAlchemy
from models import PhysicalMachines, VirtualMachine
import random, libvirt, sys

vm_data = {}
vm_ids = []

def uniqueid():
	seed = random.getrandbits(32)
	while True:
		yield seed
		seed += 1

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
		instance_type=int(request.args.get('instance_type', 0))
	except Exception, e:
		return "instance_type must be of type int."
	
	try:
		image_id=int(request.args.get('image_id', 0))
	except Exception, e:
		return "image_id must be of type int."
	
	#global vm_ids, app_globals.unique_sequence, app_globals.ip_data
	if not any(item['tid'] == instance_type for item in app_globals.vm_types['types']):
		return "The instance_type is invalid"

	ret = -1
	for item in app_globals.image_locations:
		if item['id'] == image_id:
			ret = item
			break

	if ret==-1:
		return "The image_id is invalid"
	
	if len(vm_ids) == 0:
		try:
			connect = libvirt.open('qemu:///system')
			#libvirt.open('remote+ssh://') +app_globals.ip_data[0]+'/system')
			#names = connect.listDefinedDomains()
			cpu = app_globals.vm_types["types"][instance_type]["cpu"]
			ram = app_globals.vm_types["types"][instance_type]["ram"]
			str_out = create_xml("qemu", name, \
				cpu, 
				ram, \
				ret['name'], "/home/sash/temp.img")
			print str_out
			connect_xml = connect.defineXML(str(str_out))
			connect_xml.create()
		
			app_globals.unique_sequence=uniqueid()
			new_id = next(app_globals.unique_sequence)
			while new_id==0:
				new_id = next(app_globals.unique_sequence)

			VirtualMachine(name, cpu, ram)
			vm_ids.append(new_id)
			vm_data[str(new_id)]={
				'vmid': new_id
			}
			return to_json({'vmid': new_id})
		except Exception, e:
			return to_json({'vmid': 0})
	else:
		while True:
			temp = str(next(app_globals.unique_sequence))
			if temp not in vm_ids:
				try:
					connect = libvirt.open('qemu:///system')
					#connect = libvirt.open('remote+ssh://'+app_globals.ip_data[0]+'/system')
					#names = connect.listDefinedDomains()
					#print names
					vm_ids.append(temp)
					vm_data[temp]={
						'vmid': temp
					}
					break
				except Exception, e:
					print e
					return to_json({'vmid': 0})
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
		return to_json(output)
	
	#global vm_data

	try:
		status = destroy(vmid)
		if status == 1: 
			del vm_data[vmid]
		output['status']=status
	except Exception, e:
		output['status']=0

	return to_json(output)

@app.route("/vm/types")
def vm_types():
	return to_json(app_globals.vm_types)

@app.route("/pm/list")
def pm_list():
	return to_json('')

@app.route("/pm/<pmid>/listvms")
def pm_listvms(pmid):
	return to_json({'vmids':vm_data.keys()})

@app.route("/pm/<pmid>")
def pm_query(pmid):
	return to_json(pmid)

@app.route("/image/list")
def image_list():
	output={'images': []}
	for obj in app_globals.image_locations:
		output['images'].append({
			'id': obj['id'],
			'name': os.path.splitext(str(obj['name']).split('/')[-1])[0]})
	return to_json(output)

@app.errorhandler(404)
def page_not_found(e):
	return redirect(url_for('list_all_urls'))

@app.route("/test")
def list_virtual_machines():
	conn=libvirt.open("qemu:///system")

	domain_dict_1 = []
	for id in conn.listDomainsID():
		dom = conn.lookupByID(id)
		info = dom.info()
		domain_dict_1.append({
		  'name' : dom.name(),
		  'info' : dom.info()
		})


	domain_dict_2 = []
	for dom in conn.listAllDomains():
		info = dom.info()
		domain_dict_2.append({
		  'name' : dom.name(),
		  'info' : dom.info()
		})

	domain_dict = {
		'dict_1' : domain_dict_1,
		'dict_2' : domain_dict_2
	}
	return to_json(domain_dict)

def create_xml(arch, vm_name, memory, vcpu, image_location, storage_location):
	xml = "<domain type='" + str(arch) + "'>  \
			<name>" + str(vm_name) + "</name>  \
			<memory>" + str((memory*100000)/1024) + "</memory>  \
			<vcpu>" + str(vcpu) + "</vcpu>  \
			<os>  \
				<type arch='i686' machine='pc'>hvm</type>  \
				<boot dev='cdrom'/>  \
			</os>  \
			<devices>  \
				<emulator>/usr/bin/qemu-system-x86_64</emulator>  \
				<disk type='file' device='cdrom'>  \
				<source file='" + str(image_location)+ "'/>  \
			  <target dev='hdc'/>  \
			  <readonly/>  \
			</disk>  \
			<disk type='file' device='disk'>  \
				<source file='" + str(storage_location) + "'/>  \
				<target dev='hda'/>  \
			</disk>  \
			<interface type='network'>  \
				<source network='default'/>  \
			</interface>  \
			<on_poweroff>destroy</on_poweroff>			\
			<on_reboot>restart</on_reboot>				\
			<on_crash>restart</on_crash>				\
			<graphics type='vnc' port='-1'/>  \
		  </devices>  \
		</domain>"
	return xml	

def destroy(vmid):
	try:
		#instance_type, vm_name, machine_id

		connect = libvirt.open("remote+ssh://" + \
			app_globals.ip_data[0].split('@')[1] + '/system')
		
		try:
			temp = connect.lookupByName('test3')
		except Exception, e:
			return 0
		
		if temp.isActive():
			temp.destroy()

		temp.undefine()
		return 1
	except Exception, e:
		raise e
		return 0

def main(arguments):
	if len(arguments)!=3:
		raise SyntaxError('Expected Syntax: python flask_app.py pm_file image_file vm_types_file')
	#TODO: assign ID's
	ohysical_machines(arguments[0])
	get_image_locations(arguments[1])
	app_globals.vm_types(arguments[2])
	#app.run(debug=True) #TODO: Change 
	