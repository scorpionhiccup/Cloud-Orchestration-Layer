from app import app, db, models
import json
from flask_app import to_json

@app.route("/pm/list")
def pm_list():
	return to_json('')

if __name__ == '__main__':
    app.debug= True
    app.run()