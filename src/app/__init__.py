from flask import Flask, url_for
from flask.ext.sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.debug = True
app.config.from_object('config')
db = SQLAlchemy(app)

from app import models, flask_app
global ip_data, image_locations, vm_types, unique_sequence
ip_data = []
image_locations=[]
vm_types = {}
unique_sequence=''