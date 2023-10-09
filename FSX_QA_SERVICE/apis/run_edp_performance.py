# -*- coding:utf-8 -*-
import json
import os
import shutil
import subprocess
import zipfile
import tempfile
import time
import pymysql
from flask_cors import CORS
from flasgger import Swagger, swag_from
from datetime import datetime, timedelta
from FSX_QA_SERVICE.apis.Application import global_connection_pool
from flask import Flask, send_file, Response, request, jsonify, Blueprint, make_response

app_run_enp_performance = Blueprint("run_enp_performance", __name__)

CORS(app_run_enp_performance, supports_credentials=True)


@app_run_enp_performance.route('/api/run_edp_performance', methods=['POST'])
@swag_from('../swagger_doc.yaml')
def run_edp_performance():
    '''
    [
    # {"title" : "test_performance"},
    {"creator": "zhenghuaimao"},
    {"account": "RSIT_EDP_ACCOUNT_1", "Sender": "RSIT_EDP_1", "Target": "FSX_SIT_EDP", "Host": "54.250.107.1", "Port": "5001"}
    ]
    '''

    # 获取参数并将其转换为json格式
    data = request.get_data()
    datas = json.loads(data)
    # title = request.form.get('title')  # 获取title
    # creator = request.form.get('creator')  # 获取创建人
    # title = datas[0]["title"]
    creator = datas[0]["creator"]

    file_path = 'edp_fix_client/initiator/edp_performance_test/edp_performance_application.py'
    try:
        run_all_shell = []
        for param in datas[1:]:
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
        print(result)
        result = "Success"

    except subprocess.CalledProcessError as e:
        output = e.stderr.strip()
        result = "Fail"

    except subprocess.TimeoutExpired:
        output = "Execution time out"
        result = "Fail"
    # 记录结束时间
    end_time = datetime.now()
    # 计算执行时间
    execution_time = end_time - start_time

    response = {
        'creator': creator,
        'status': result,
        'output': output,
        'start_time': start_time.strftime("%Y-%m-%d %H:%M:%S"),
        'execution_time': str(execution_time),
        'end_time': end_time.strftime("%Y-%m-%d %H:%M:%S"),
        'type': 1
    }

    # 从数据库池获取数据库连接
    connection = global_connection_pool.connection()
    # 创建游标
    cursor = connection.cursor()

    # 构建SQL语句
    sql = "INSERT INTO `performance` (`status`, `start_date`, `end_date`, `type`, `createUser`) VALUES (%s, %s, %s, %s, %s)"
    values = (response['status'], response['start_time'], response['end_time'], response['type'], creator)
    print(response, creator)

    try:
        cursor.execute(sql, values)
        connection.commit()
    except Exception as e:
        print("Error while inserting into the database:", e)

    finally:
        cursor.close()
        connection.close()
    json_response = json.dumps(response)

    return Response(json_response, mimetype='application/json'), 200


@app_run_enp_performance.route('/api/download_performance_logs', methods=['GET'])
@swag_from('../swagger_doc.yaml')
def download_performance_log_file():
    '''
    {
    "account":[
        "RSIT_EDP_ACCOUNT_1",
        "RSIT_EDP_ACCOUNT_5"
    ]
    }
    '''

    date = request.get_json()
    # 判断传参是否为空
    if date is None or date == '':
        return jsonify({"Error": "Invalid file path"}), 400

    # 创建一个空数组用于存放所有日志的路径
    file_paths = []
    accounts = date["account"]
    # 循环从参数中读取account，并拼接日志地址
    for account in accounts:
        log_path = "edp_fix_client/initiator/edp_performance_test/logs/{}_Report.log".format(account)
        # 如果日志不存在，抛出错误
        if not os.path.exists(log_path):
            return jsonify({"Error": "The file is not found"}), 404

        file_paths.append(log_path)

    # 创建临时目录用于存放压缩文件
    temp_dir = tempfile.mkdtemp()

    # 记录打包时间
    zip_time = datetime.now()
    zip_name = "performance_logs_{}.zip".format(zip_time.strftime("%Y-%m-%d_%H-%M-%S"))
    zip_file_path = os.path.join(temp_dir, zip_name)
    # 创建压缩文件
    create_zip_archive(file_paths, zip_file_path)

    # 创建响应对象
    response = make_response(send_file(zip_file_path, as_attachment=True))

    # 设置 Content-Disposition 头部字段
    response.headers['Content-Disposition'] = 'attachment; filename={}'.format(zip_name)

    # 删除临时目录及其内容
    shutil.rmtree(temp_dir)

    return response
def create_zip_archive(file_paths, zip_file_path):
    with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_path in file_paths:
            zipf.write(file_path, os.path.basename(file_path))
