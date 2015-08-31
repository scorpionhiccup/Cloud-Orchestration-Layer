#!usr/bin/python
from app import app, db, ip_data, image_locations, vm_types, unique_sequence
import app as app_globals
from app.models import PhysicalMachines
import sys, random, json, libvirt, os
from sh import uname, nproc, tail, head, free, df

def uniqueid():
	seed = random.getrandbits(32)
	while True:
		yield seed
		seed += 1

def ohysical_machines(pm_file):	
	with open(pm_file,'r') as data_file:
		app_globals.ip_data=data_file.read().splitlines()
	
	try:
		db.session.query(PhysicalMachines).delete()
		db.session.commit()
	except Exception, e:
		db.session.rollback()

	for obj in app_globals.ip_data:
		data = obj.split('@')
		try:
			connect = libvirt.open("remote+ssh://" + obj + "/system")
		except Exception, e:
			print "SSH Daemon either not running or the port is not open"
			raise e
		
		try:
			hardware=32
			if str(uname('-m')).rsplit()[0]=='x86_64':
				hardware=64
			else:
				hardware=32

			vcpu = int(str(nproc()).rsplit()[0])
			free_ram = str(tail(head(free('-m'), '-n2'), '-n1').split()[3])
			free_space = str(df('-h').split('\n')[1].split()[3])
		except Exception, e:
			raise e

		if not PhysicalMachines.query.filter_by(
			username=obj.split('@')[0], 
			ip_addr=obj.split('@')[1]).all():
			pm_obj = PhysicalMachines(obj, hardware, vcpu, free_ram, free_space)
			try:
				db.session.add(pm_obj)
				db.session.commit()
			except Exception, e:
				db.session.rollback()

	'''
	for item in PhysicalMachines.query.all():
		print item
	'''
	

def load_vm_types(vm_types_file):
	global vm_types
	with open(vm_types_file, 'r') as data_file:
		app_globals.vm_types=json.load(data_file)

def get_image_locations(image_files_location):
	global image_locations
	with open(image_files_location, 'r') as data_file:
		image_location_temp=data_file.read().splitlines()

	app_globals.unique_sequence=uniqueid()
	for image_location in image_location_temp:
		app_globals.image_locations.append({
			"id": next(app_globals.unique_sequence), 
			"name": image_location,
			})

def main(arguments):
	if len(arguments)!=3:
		raise SyntaxError('Expected Syntax: python flask_app.py pm_file image_file vm_types_file')
	#TODO: assign ID's
	ohysical_machines(arguments[0])
	get_image_locations(arguments[1])
	load_vm_types(arguments[2])
	
if __name__ == '__main__':
	main(sys.argv[1:])
	app.run(debug = True)
