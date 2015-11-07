from app import db


class PhysicalMachines(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	username = db.Column(db.String(25))
	ip_addr = db.Column(db.String(50))
	hardware = db.Column(db.Integer)
	vcpu = db.Column(db.Integer)
	free_space = db.Column(db.String(20))
	ram = db.Column(db.Integer)

	def __repr__(self):
		return '<PM_ID: %d ==> %s@%s>' % (self.id, self.username, self.ip_addr)

	def __init__(self, ip, hardware, vcpu, ram, free_space):
		self.username, self.ip_addr = ip.split('@')
		self.hardware = hardware
		self.ram = ram
		self.vcpu = vcpu
		self.free_space = free_space

class VirtualMachine(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	ram = db.Column(db.Integer)
	pmid = db.Column(db.Integer)
	uuid = db.Column(db.String(120), index=True, unique=True)
	#, db.ForeignKey('Physical_Machines.id')
	name = db.Column(db.String(100))
	cpu = db.Column(db.Integer)
	ip_pm = db.Column(db.String(50))
	instance_type = db.Column(db.Integer)

	def __repr__(self):
		return '<VM_ID: %d, PM_ID: %d, RAM: %d, Name: %s>' % (
			self.id,  self.pmid, \
			self.ram, self.name)

	def __init__(self, name, cpu, ram, pmid, ip_pm, _uuid, instance_type):
		self.cpu = cpu
		self.name = name
		self.ram = ram
		self.pmid = pmid
		self.ip_pm = ip_pm
		self.uuid = _uuid
		self.instance_type = instance_type

class Volume(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	name = db.Column(db.String(50))
	vmid = db.Column(db.String(50))