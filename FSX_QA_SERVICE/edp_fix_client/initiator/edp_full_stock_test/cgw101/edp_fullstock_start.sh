#!/bin/sh
#cd /app/data/qa-tools/edp_fix_client/initiator/edp_full_stock_test/cgw101
#sleep 5
#python3 /app/data/qa-tools/edp_fix_client/initiator/edp_full_stock_test/cgw101/edp_fullstock_client.py /app/data/qa-tools/edp_fix_client/initiator/edp_full_stock_test/cgw101/edp_fullstock_client.cfg



#本地
#cd /Users/zhenghuaimao/Desktop/qa-tools/gRpc_py
#python3 sit_client.py
#sleep 10

#cd /Users/zhenghuaimao/Desktop/qa-tools/edp_fix_client/initiator/edp_full_stock_test/cgw101
#sleep 5
#python3 edp_fullstock_client.py edp_fullstock_client.cfg


#JenKins
#cd /var/jenkins_home/workspace/edp_fullstock_test/gRpc_py
#python3 sit_client.py
#sleep 10

cd /var/jenkins_home/workspace/edp_fullstock_test/edp_fix_client/initiator/edp_full_stock_test/cgw101
sleep 6
python3 edp_fullstock_client.py edp_fullstock_client.cfg


