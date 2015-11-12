#!/usr/bin/python
from flask import Flask, json, request, render_template, \
	jsonify, redirect, url_for
from flask import make_response
from app import app, db, models
import app as app_globals
import uuid
from flask.ext.sqlalchemy import SQLAlchemy
from models import PhysicalMachines, VirtualMachine, Volume
import os, random, libvirt, sys
import rados, rbd
from sh import ceph
from xml.etree import ElementTree
global rbdInstance, rados_ioctx

POOL_NAME = 'cloud-project'
CONF_FILE = '/etc/ceph/ceph.conf'

def establishConnection():
	radosConnection = rados.Rados(conffile=CONF_FILE)
	radosConnection.connect()

	if POOL_NAME not in radosConnection.list_pools():                                
		radosConnection.create_pool(POOL_NAME)
	
	global rbdInstance, rados_ioctx
	rados_ioctx = radosConnection.open_ioctx(POOL_NAME)
	rbdInstance = rbd.RBD()
	return rados_ioctx

establishConnection()

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


@app.route("/volume/create", methods=['POST', 'GET'])
def volume_creation():
	name=str(request.args.get('name', ''))
	size=float(request.args.get('size', 0))
	#size = (1024) * size

	try:
		global rbdInstance, rados_ioctx
		rbdInstance.create(rados_ioctx, name, int((1024**3) * size))
		os.system('sudo rbd map %s --pool %s --name client.admin'%(name, POOL_NAME))

		vol_obj = Volume(name, size, 0, 0)
		try:
			db.session.add(vol_obj)
			obj = db.session.query(Volume).order_by(Volume.id.desc()).first()
			db.session.commit()
			return to_json({'volumeid': obj.id})
		except Exception, e:
			print 'HERE', e
			db.session.rollback()
	except Exception, e:
		print e
		return to_json({'volumeid':0})

	return to_json({'volumeid': 0})

@app.route("/volume/query", methods=['POST', 'GET'])
def volume_query():
	output = {}
	try:
		volumeId=int(str(request.args.get('volumeid')))
	except Exception, e:
		output['error'] = "volumeid : %s does not exist" % (volumeId)
		return to_json(output)

	obj = Volume.query.filter_by(id=volumeId).first() 

	if obj and obj.status==0:
		output['volumeId']=volumeId
		output['name']=obj.name
		output['size']=obj.size
		output['status']="available"
	elif obj and obj.status==1:
		output['volumeId']=obj.volumeId
		output['name']=obj.name
		output['size']=obj.size
		output['status']="attached"
		output['vmid']=obj.vmid
	else:
		output['error'] = "volumeid : %s does not exist" % (volumeId)
	
	return to_json(output)


@app.route("/volume/destroy", methods=['POST', 'GET'])
def volume_delete():
	output = {}
	try:
		volumeId=int(str(request.args.get('volumeid')))
	except Exception, e:
		output['status']=0
		return to_json(output)

	try:		
		obj = Volume.query.filter_by(id=volumeId, status=0).first()
		if obj:
			name=str(obj.name)
		else:
			output['status']=0
			return to_json(output)

		global rbdInstance, rados_ioctx
		print name
		os.system('sudo rbd unmap /dev/rbd/%s/%s'%(POOL_NAME, name))
		rbdInstance.remove(rados_ioctx, name)
			
		obj.status=2
		#db.session.delete(obj)
		db.session.commit()
	
		output['status']=1
		return to_json(output)
	except Exception, e:
		print e
		raise e
		output['status']=0
		return to_json(output)

def getBlockXML(xmlFile, imageName, deviceName):
	tree = ElementTree.parse(xmlFile)
	root = tree.getroot()
	imageName = POOL_NAME + '/' + imageName
	root.find('source').attrib['name'] = imageName
	root.find('source').find('host').attrib['name'] = str(eval(ceph('mon_status').stdout)['monmap']['mons'][0]['name'])
	#root.find('target').attrib['dev'] = deviceName

	return ElementTree.tostring(root)
	
@app.route("/volume/attach", methods=['POST', 'GET'])
def volume_attach():
	output={}
	try:
		vmId = int(str(request.args.get('vmid','0')))
		volumeId = int(str(request.args.get('volumeid','0')))
	except Exception, e:
		output['status']=0
		return to_json(output)

	vm_obj = VirtualMachine.query.filter_by(id=vmId).first()
	vol_obj = Volume.query.filter_by(id=volumeId).first()

	if vm_obj and vol_obj:
		connect = libvirt.open("remote+ssh://" + vm_obj.ip_pm + '/system')
		domain = connect.lookupByUUIDString(vm_obj.uuid)
		configXML = getBlockXML('app/block_config.xml', vol_obj.name, vm_obj.name)
		print configXML
		domain.attachDevice(configXML)
		connect.close()

		vol_obj.status=1
		vol_obj.vmid=str(vmId)
		db.session.commit()

		output['status']=1
		return to_json(output)
	else:
		'''
		try:
			connect.close()
		except Exception, e:
			print e
		'''
		print vol_obj
		print vm_obj
		output['status']=0
		return to_json(output)

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
		PhysicalMachines.ram >= ram).first()
	if not output:
		return to_json({'vmid': 0})
	else:
		pmid = output.id

	ip_pm = '@'.join([output.username, output.ip_addr])

	#print output.username, output.ip_addr

	if not app_globals.DEBUG:
		setup(ret['name'], output.username, output.ip_addr)
	
	connect = libvirt.open('remote+ssh://' +  ip_pm + '/system')

	temp = str(uuid.uuid4())

	#print output.username, output.ip_addr
	try:
	
		str_out = create_xml(
			temp, \
			connect.getType().lower(), name, \
			ram, cpu, \
			ret['name'], "/home/" + output.username + "/Images/linux.img")
		
		#print str_out
		connect_xml = connect.defineXML(str(str_out))
		connect_xml.create()
		connect.close()
	
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
	
def setup(image_path, username, ip):
	'''
		Copies the ISO file for the VM creation
	'''
	#print "PHEW", username, ip
	os.system("scp " + str(image_path) + " " + str(ip) + ":/home/" + str(username) + "/Images/" + os.path.basename(image_path))

		
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

@app.route("/pm/query")
def pm_query():
	output={
		'pmid':0,
		'vms': 0,
	}

	try:
		pmid=int(str(request.args.get('pmid')))
	except Exception, e:
		return to_json(output)

	phy_obj = PhysicalMachines.query.filter_by(id=pmid).first()
	if phy_obj:
		output['capacity'] = {
			'cpu': phy_obj.vcpu,
			'ram': phy_obj.ram,
			'disk': int(str(phy_obj.free_space)[:-1])
		}
		output['vms'] = VirtualMachine.query.filter_by(pmid=pmid).count()
		output['pmid']=pmid

		obj = '@'.join([phy_obj.username, phy_obj.ip_addr])
		
		os.system("ssh " + obj + " \"cat /proc/cpuinfo | awk '/^processor/{print $3}' | tail -1 \" > proc.txt")
		with open("proc.txt") as data_file:
			vcpu = int(str(data_file.read().splitlines()[0]).split()[2])
		
		#print vcpu
		
		os.system("ssh " + obj + " 'free -m | head -n2 | tail -n1' > proc.txt")
		with open("proc.txt") as data_file:
			ram = int(str(data_file.read().splitlines()[0].split()[3]))

		os.system("ssh " + obj + " 'df -h' > proc.txt")
		with open("proc.txt") as data_file:
			free_space = str(data_file.read().splitlines()[1].split()[3])

		output['free'] = {
			'cpu': vcpu,
			'ram': ram,
			'disk': int(str(free_space)[:-1])
		}
	return to_json(output)

@app.route("/image/list")
def image_list():
	output={'images': []}
	for obj in app_globals.image_locations:
		output['images'].append({
			'id': obj['id'],
			'name': os.path.splitext(str(obj['name']).split('/')[-1])[0]})
	return to_json(output)

'''
@app.errorhandler(404)
def page_not_found(e):
	return redirect(url_for('list_all_urls'))
'''

@app.errorhandler(404)
def not_found(error):
	return make_response(jsonify({ 'Error': 'URL not found' } ), 404)

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
				domain = connect.lookupByUUIDString(obj.uuid)
				if domain.isActive():
					domain.destroy()
				domain.undefine()
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
	