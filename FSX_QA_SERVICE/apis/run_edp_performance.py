# -*- coding:utf-8 -*-
import json
import os
import subprocess
import time
import pymysql
from flask import Flask, send_file, Response, request, jsonify, Blueprint, make_response
from datetime import datetime, timedelta
from flask_cors import CORS
from FSX_QA_SERVICE.apis.Application import global_connection_pool

app_run_enp_performance = Blueprint("run_enp_performance", __name__)

CORS(app_run_enp_performance, supports_credentials=True)


@app_run_enp_performance.route('/api/run_edp_performance', methods=['POST'])
def run_edp_performance():
    # 获取参数并将其转换为json格式
    data = request.get_data()
    datas = json.loads(data)

    file_path = '/Users/zhenghuaimao/Desktop/FSX-DEV-QA/FSX_QA_SERVICE/edp_fix_client/initiator/edp_performance_test/edp_performance_application.py'
    try:
        for param in datas:
            # 构建shell命令
            shell_command = '''
                    python3 {file_path} --account {account} --Sender {Sender} --Target {Target} --Host {Host} --Port {Port} &
                    sleep 1
                    '''.format(file_path=file_path, **param)
            print(shell_command)

            # 执行shell命令
            result = subprocess.run(shell_command, shell=True, capture_output=True, text=True, timeout=1800)
            output = result.stdout.strip() if result.stdout else result.stderr.strip()
            success = True
    except subprocess.CalledProcessError as e:
        output = e.stderr.strip()
        success = False

    except subprocess.TimeoutExpired:
        output = "Execution time out"
        success = False

    response = make_response(jsonify({'output': output, 'success': success}))
    return response


