from app import db


class PhysicalMachines(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	username = db.Column(db.String(25))
	ip_addr = db.Column(db.String(50))


	def __repr__(self):
		return '<PM_ID: %d ==> %s@%s>' % (self.id, self.username, self.ip_addr)

	def __init__(self, ip):
		self.username, self.ip_addr = ip.split('@')

class VirtualMachine(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	ram = db.Column(db.Integer)
	pmid = db.Column(db.Integer, db.ForeignKey('Physical_Machines.id'))
	name = db.Column(db.String(100))
	cpu = db.Column(db.Integer)

	def __repr__(self):
		return '<VM_ID: %d, PM_ID: %d, RAM: %d, Name: %s>' % (
			self.id,  self.pmid, \
			self.ram, self.name)

	def __init__(self, cpu, ram, name, pmid):
		self.cpu = cpu
		self.name = name
		self.ram = ram
		self.pmid = pmid
