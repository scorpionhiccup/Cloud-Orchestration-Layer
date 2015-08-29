source /usr/local/bin/virtualenvwrapper.sh
workon cloud_project
pip install -r requirements.txt
python flask_app.py ips.txt image_location_files.txt types.json
#sudo apt-get install python-virtinst
sudo mkdir -p /var/lib/libvirt/save
#mkdir -p ./srv/ceph/{osd,mon,mds}