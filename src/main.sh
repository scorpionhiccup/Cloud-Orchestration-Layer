source /usr/local/bin/virtualenvwrapper.sh
workon cloud_project
pip install -r ../requirements.txt
python db_create.py
python db_migrate.py
#python app/flask_app.py app/ips.txt app/image_location_files.txt app/types.json
#sudo mkdir -p /var/lib/libvirt/save
#mkdir -p ./srv/ceph/{osd,mon,mds}