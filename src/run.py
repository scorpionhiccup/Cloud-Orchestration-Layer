#!usr/bin/python
from app import app, db
import sys
from app.models import PhysicalMachines
import random, json

ip_data = []
image_locations=[]
vm_types = {}

def uniqueid():
	seed = random.getrandbits(32)
	while True:
		yield seed
		seed += 1

def ohysical_machines(pm_file):	
	global ip_data
	with open(pm_file,'r') as data_file:
		ip_data=data_file.read().splitlines()

	for obj in ip_data:
		pm_obj = PhysicalMachines(obj)
		db.session.add(pm_obj)
		db.session.commit()

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
	print image_locations

def main(arguments):
	if len(arguments)!=3:
		raise SyntaxError('Expected Syntax: python flask_app.py pm_file image_file vm_types_file')
	#TODO: assign ID's
	ohysical_machines(arguments[0])
	get_image_locations(arguments[1])
	vm_types(arguments[2])
	
if __name__ == '__main__':
	main(sys.argv[1:])
	app.run(debug = True)
