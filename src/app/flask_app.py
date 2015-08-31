#! usr/bin/python

from flask import Flask, json, request, render_template, \
	jsonify, redirect, url_for
from app import app, db, models
import app as app_globals
import uuid
#import src.run
#, virt-install
from flask.ext.sqlalchemy import SQLAlchemy
from models import PhysicalMachines, VirtualMachine
import os, random, libvirt, sys

vm_data = {}

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
	'''
	try:
		db.session.query(VirtualMachine).delete()
		db.session.commit()
	except Exception, e:
		db.session.rollback()
	'''

	routes = []
	for rule in app.url_map.iter_rules():
		if "GET" in rule.methods:
			url = rule.rule
			routes.append(url)
	return render_template('routes.html', routes=routes)

def create_xml(_uuid, arch, vm_name, memory, vcpu, image_location, storage_location):
	xml = "<domain type='" + str(arch) + "'>  \
			<uuid>" + str(_uuid)+ "</uuid> \
			<name>" + str(vm_name) + "</name>  \
			<memory>" + str(memory) + "</memory>  \
			<vcpu>" + str(vcpu) + "</vcpu>  \
			<os>  \
				<type arch='x86_64' machine='pc'>hvm</type>  \
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
			<on_crash>restart</on_crash>				\
			<graphics type='vnc' port='-1'/>  \
		  </devices>  \
		</domain>"
	return xml	

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
	
	#global app_globals.unique_sequence, app_globals.ip_data
	if not any(item['tid'] == instance_type for item in app_globals.vm_types['types']):
		return "The instance_type is invalid"

	ret = -1
	for item in app_globals.image_locations:
		if item['id'] == image_id:
			ret = item
			break

	if ret==-1:
		return "The image_id is invalid"
	
	cpu = app_globals.vm_types["types"][instance_type]["cpu"]
	ram = app_globals.vm_types["types"][instance_type]["ram"]
	
	output = PhysicalMachines.query.filter(
		PhysicalMachines.vcpu>=cpu, 
		PhysicalMachines.free_ram >= ram).first()
	if not output:
		return to_json({'vmid': 0})
	else:
		pmid = output.id

	ip_pm = '@'.join([output.username, output.ip_addr])
	connect = libvirt.open(
		'remote+ssh://' +  ip_pm + '/system')

	temp = str(uuid.uuid4())
	str_out = create_xml(
		temp, \
		"qemu", name, \
		ram, cpu, \
		ret['name'], "/home/sash/temp.img")
	
	connect_xml = connect.defineXML(str(str_out))
	connect_xml.create()

	try:
		vm_obj = VirtualMachine(name, cpu, ram, output.id, ip_pm, temp, instance_type)
		try:
			db.session.add(vm_obj)
			obj = db.session.query(VirtualMachine).order_by(VirtualMachine.id.desc()).first()
			db.session.commit()
			return to_json({'vmid': obj.id})
		except Exception, e:
			db.session.rollback()
	except Exception, e:
		print e

	return to_json({'vmid': 0})
	
		
@app.route("/vm/query")
def vm_query():
	try:
		vmid=int(str(request.args.get('vmid')))
	except Exception, e:
		return "Link: /vm/query?vmid=vm_id"

	obj = VirtualMachine.query.filter_by(id=vmid).first() 
	output={}

	if obj:
		output['vmid']=obj.id
		output['name']=obj.name
		output['instance_type'] = obj.instance_type
		output['pmid'] = obj.pmid
	else:
		output['vmid']='null'
		output['name']=''
		output['instance_type'] = 0
		output['pmid'] = 0
	
	return to_json(output)

@app.route("/vm/destroy")
def vm_destroy():
	output = {}
	try:
		vmid=int(str(request.args.get('vmid')))
	except Exception, e:
		output['status']=0
		return to_json(output)
	
	try:
		status = destroy(vmid)
		output['status']=status
	except Exception, e:
		output['status']=0

	return to_json(output)

@app.route("/vm/types")
def vm_types():
	return to_json(app_globals.vm_types)

@app.route("/pm/list")
def pm_list():
	output = db.session.query(PhysicalMachines).all()
	json_out = {'pmids': [item.id for item in output]}	
	return to_json(json_out)

@app.route("/pm/listvms")
def pm_listvms():
	output={'vmids':0}
	try:
		pmid=int(str(request.args.get('pmid')))
	except Exception, e:
		return to_json(output)

	phy_obj = PhysicalMachines.query.filter_by(id=pmid).first()
	if phy_obj:		
		vir_objs = VirtualMachine.query.all() 
		if not vir_objs:
			return to_json(output)
		
		output['vmids'] = []
		for obj in vir_objs:
			if obj.pmid == pmid:
				output['vmids'].append(obj.id)

	return to_json(output)

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

def destroy(vmid):
	try:
		try:
			obj = VirtualMachine.query.filter_by(id=vmid).first()
			if obj:
				connect = libvirt.open("remote+ssh://" + \
					obj.ip_pm + '/system')
				temp = connect.lookupByUUIDString(obj.uuid)
				if temp.isActive():
					temp.destroy()
				temp.undefine()
				db.session.delete(obj)
				db.session.commit()
				return 1
			else:
				return 0
		except Exception, e:
			return 0
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
	