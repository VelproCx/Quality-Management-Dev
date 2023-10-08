# -*- coding:utf-8 -*-
import json
import os
import subprocess
import time
import pymysql
from flask_cors import CORS
from datetime import datetime, timedelta
from FSX_QA_SERVICE.apis.Application import global_connection_pool
from flask import Flask, send_file, Response, request, jsonify, Blueprint, make_response


app_run_enp_performance = Blueprint("run_enp_performance", __name__)

CORS(app_run_enp_performance, supports_credentials=True)


@app_run_enp_performance.route('/api/run_edp_performance', methods=['POST'])
def run_edp_performance():
    # 获取参数并将其转换为json格式
    data = request.get_data()
    datas = json.loads(data)

    file_path = 'edp_fix_client/initiator/edp_performance_test/edp_performance_application.py'
    try:
        run_all_shell = []
        for param in datas:
            # 构建shell命令
            shell_command = '''
    python3 {file_path} --account {account} --Sender {Sender} --Target {Target} --Host {Host} --Port {Port} & sleep 1
                    '''.format(file_path=file_path, **param)
            run_all_shell.append(shell_command)

        # 执行shell命令
        command = ' '.join(run_all_shell)
        # 记录shell脚本开始执行的时间
        start_time = datetime.now()
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=1800)
        output = result.stdout.strip() if result.stdout else result.stderr.strip()
        result = "Success"

    except subprocess.CalledProcessError as e:
        output = e.stderr.strip()
        result = "Fail"

    except subprocess.TimeoutExpired:
        output = "Execution time out"
        result = "Fail"

    end_time = datetime.now()  # 记录结束时间
    execution_time = end_time - start_time  # 计算执行时间

    response = {
        'result': result,
        'output': output,
        'start_time': start_time.strftime("%Y-%m-%d %H:%M:%S"),
        'execution_time': str(execution_time),
        'end_time': end_time.strftime("%Y-%m-%d %H:%M:%S"),
        'type': 1
    }
    return response
