from flask import Flask, url_for
from flask.ext.sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config.from_object('config')
db = SQLAlchemy(app)

try:
	from src.app import models, flask_app
except Exception, e:
	from app import models, flask_app
