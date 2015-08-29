#! usr/bin/python

from flask import Flask, json, request, render_template, jsonify, redirect, url_for
from sh import virsh
from flask.ext.sqlalchemy import SQLAlchemy
#, virt-install
import random, libvirt, sys

app = Flask(__name__)
	
def uniqueid():
	seed = random.getrandbits(32)
	while True:
	   yield seed
	   seed += 1

vm_ids = []
ip_data = []
unique_sequence=''
image_locations=[]
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
	
	global vm_ids, unique_sequence, ip_data

	if not any(item['tid'] == instance_type for item in vm_types['types']):
		return "The instance_type is invalid"

	if len(vm_ids) == 0:
		try:
			connect = libvirt.open('qemu:///system')
			#libvirt.open('remote+ssh://') +ip_data[0]+'/system')
			
			#names = connect.listDefinedDomains()
			#print names

			str_out = create_xml("qemu", name, 2048, 2048, 2, image_locations[0]['name'], "/home/sash/temp.img")
			import pprint
			pprint.pprint(str_out)
			#print str_out
			connect_xml = connect.defineXML(str(str_out))
			connect_xml.create()
		
			unique_sequence=uniqueid()
			new_id = next(unique_sequence)
			vm_ids.append(new_id)
			vm_data[str(new_id)]={
				'name': name,
				'instance_type': instance_type 
			}
		
		except Exception, e:
			raise e
	else:
		while True:
			temp = str(next(unique_sequence))
			if temp not in vm_ids:
				try:
					connect = libvirt.open('remote+ssh://'+ip_data[0]+'/system')
					names = connect.listDefinedDomains()
					print names
					vm_ids.append(temp)
					vm_data[temp]={
						'name': name,
						'instance_type': instance_type 
					}
					break
				except Exception, e:
					print e

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
	return to_json({'vmids':vm_data.keys()})

@app.route("/pm/<pmid>")
def pm_query(pmid):
	return to_json(pmid)

@app.route("/image/list")
def image_list():
	return to_json({'images':image_locations})

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

def ohysical_machines(pm_file):	
	global ip_data
	with open(pm_file,'r') as data_file:
		ip_data=data_file.read().splitlines() 

def vm_types(vm_types_file):
	global vm_types
	with open(vm_types_file, 'r') as data_file:
		vm_types=json.load(data_file)

def get_image_locations(image_files_location):
	global image_locations
	with open(image_files_location, 'r') as data_file:
		image_location_temp=data_file.read().splitlines()

	unique_sequence=uniqueid()
	for image_location in image_location_temp:
		image_locations.append({
			"id": next(unique_sequence), 
			"name": image_location,
			})

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

def main(arguments):
	if len(arguments)!=3:
		return 0

	#TODO: assign ID's
	ohysical_machines(arguments[0])
	get_image_locations(arguments[1])
	vm_types(arguments[2])
	
	return 1

if __name__ == '__main__':
	app.config.from_object('config')
	db = SQLAlchemy(app)
	ret = main(sys.argv[1:])

	if ret==1:
		app.run(debug=True) #TODO: Change 
	else:
		raise SyntaxError('Expected Syntax: python flask_app.py pm_file image_file vm_types_file')