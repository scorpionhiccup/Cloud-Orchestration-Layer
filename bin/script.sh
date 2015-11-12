ceph-deploy purge mon1
ceph-deploy purgedata mon1
ceph-deploy forgetkeys
ceph-deploy new mon1
printf 'osd_pool_default_size = 2\nosd crush chooseleaf type = 0\n' >> ceph.conf
ceph-deploy install mon1
ceph-deploy mon create-initial
ceph-deploy disk zap /var/local/osd0 /var/local/osd1
sudo rm -rf /var/local/osd*
sudo mkdir /var/local/osd0 /var/local/osd1
ceph-deploy osd prepare mon1:/var/local/osd0 mon1:/var/local/osd1
ceph-deploy osd activate mon1:/var/local/osd0 mon1:/var/local/osd1
ceph-deploy admin mon1
sudo chmod +r /etc/ceph/ceph.client.admin.keyring
for i in `seq 0 1`;do ceph osd crush reweight osd.$i 1;done
ceph health
