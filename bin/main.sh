#source /usr/local/bin/virtualenvwrapper.sh
#workon cloud_project
pip install -r ../requirements.txt
python ../src/db_create.py
python ../src/db_migrate.py
#To run the app:
#python ../src/app/flask_app.py ../src/app/ips.txt ../src/app/image_location_files.txt ../src/app/types.json
#sudo mkdir -p /var/lib/libvirt/save