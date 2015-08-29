from app import db

class Physical_Machines(db.Model):
	id = db.Column(db.Integer, primary_key=True)

	def __repr__(self):
		 return '<PM ID: UUID: %r>' % (self.id)

	def __init__(self, id):
		self.id = id

class Temp(db.Model):
	id = db.Column(db.Integer, primary_key=True)

	def __repr__(self):
		 return '<PM ID: UUID: %r>' % (self.body)

	def __init__(self, id):
		self.id = id
