import configparser
import json
import os
import platform
import signal
import tempfile
import threading
import time
import random
import traceback

from flask import Flask, send_file, Response, jsonify, request, Blueprint, stream_with_context, make_response
import subprocess
from datetime import datetime, timedelta
from flask_cors import CORS
from configparser import ConfigParser
from flasgger import Swagger, swag_from
from flask_jwt_extended import jwt_required

from FSX_QA_SERVICE.apis.Application import global_connection_pool
import pymysql

config = ConfigParser()
config.read('../config/settings.ini')
config_file = 'edp_fix_client/initiator/edp_smoke_test/edp_smoke_client.cfg'

# 获取当前日期
current_date = datetime.now().strftime("%Y-%m-%d")
log_filename = f"edp_report_{current_date}.log"
log_file_path = 'edp_fix_client/initiator/edp_smoke_test/logs/' + log_filename



class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, timedelta):
            return str(obj)
        return super().default(obj)


app_run_edp_smoke = Blueprint("run_edp_smoke", __name__)
CORS(app_run_edp_smoke)
taskId = 0


# tsak_id生成
def get_task_id():
    global taskId  # 全局变量
    taskId += 1
    # 获取当前时间并且进行格式转换
    t = int(time.time())
    str1 = ''.join([str(i) for i in random.sample(range(0, 9), 2)])
    return str(t) + str1 + str(taskId).zfill(2)


def insert_smoke_record(task_id, creator, status, create_time):
    # 从数据库池获取数据库连接
    connection = global_connection_pool.connection()
    # 创建游标
    cursor = connection.cursor()
    print(task_id, status, creator, create_time, )
    try:
        # 插入sql语句

        sql = "INSERT INTO SmokeRecord (taskId, status, CreateUser, CreateTime, type) VALUES (%s, %s, %s, %s, %s)"
        values = (task_id, status, creator, create_time, 1)

        # 执行语句
        cursor.execute(sql, values)
        connection.commit()

    except Exception as e:
        print("Error while inserting into the database:", e)

    finally:
        # 关闭游标
        cursor.close()
        # 关闭连接
        connection.close()


def update_smoke_record(task_id, status, output):
    # 从数据库池获取数据库连接
    connection = global_connection_pool.connection()
    # 创建游标
    cursor = connection.cursor()
    log_file = None

    # 检查描述字段的长度
    if len(output) > 255:
        output = output[:255]

    try:
        try:
            # 二进制读取log文件
            with open(log_file_path, 'rb') as file:
                log_file = file.read()
                # print(log_file)

        except FileNotFoundError as e:
            print("file error:", e)

        # 存在相同的taskid，更新
        update_sql = "UPDATE SmokeRecord SET status = %s, " \
                     "log_file = %s, output = %s, log_filename = %s " \
                     "WHERE taskId = %s"
        update_values = (
            status, log_file, output, log_filename, task_id)
        cursor.execute(update_sql, update_values)
        connection.commit()

    except Exception as e:
        print("Error while inserting into the database:", e)

    finally:
        # 关闭游标和连接
        cursor.close()
        connection.close()


def read_config(json_data):
    # 读取并修改配置文件
    config = configparser.ConfigParser(allow_no_value=True)
    config.optionxform = str  # 保持键的大小写
    config.read('edp_fix_client/initiator/edp_smoke_test/edp_smoke_client.cfg')
    Sender = json_data["sender"]
    Target = json_data["target"]
    Host = json_data["ip"]
    Port = json_data["port"]
    print(json_data)
    print(Sender)
    print(Target)
    print(Host)
    print(Port)

    config.set('SESSION', 'SenderCompID', Sender)
    config.set('SESSION', 'TargetCompID', Target)
    config.set('SESSION', 'SocketConnectHost', Host)
    config.set('SESSION', 'SocketConnectPort', Port)

    with open('edp_fix_client/initiator/edp_smoke_test/edp_smoke_client.cfg', 'w') as configfile:
        config.write(configfile)

def execute_task(command_args, task_id):
    try:
        p = subprocess.Popen(command_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        time.sleep(2)
        p.wait()
        outputs = p.communicate()
        stderr = outputs[1].decode("utf-8")
        # 当进程为空时
        if stderr == "":
            status = "error"
            output = "connect error, please check the config"

        # 当进程错误时
        elif "Error:" in stderr:
            status = "error"
            output = stderr.split("Error:", 1)[-1].strip()
        else:
            status = "completed"
            output = " "
    except Exception as e:
        print("Error executing subprocess:", e)
        output = e  # 使用异常信息作为错误信息
        status = "error"

    print(task_id, status, output)
    # 更新数据库
    update_smoke_record(task_id, status, output)



# 运行edp_smoke
@app_run_edp_smoke.route('/api/edp_smoke_list/run_edp_smoke', methods=['POST'])
# @jwt_required()
def run_edp_smoke(script_path="/Users/tendy/Documents/FSX-DEV-QA/FSX_QA_SERVICE/edp_fix_client/initiator/edp_smoke_test/edp_smoke_application.py"):
    Data = request.get_data()
    # Data = {
    #     "source": "your_source",
    #     "ip": "54.250.107.1",
    #     "port": "5007",
    #     "sender": "RSIT_EDP_7",
    #     "target": "FSX_SIT_EDP",
    #     "Account": "RSIT_EDP_ACCOUNT_7",
    #     "Market": "EDP",
    #     "ActionType": "NewAck",
    #     "OrderQty": 100,
    #     "OrdType": "1",
    #     "Side": "2",
    #     "Symbol": "5110",
    #     "TimeInForce": "3",
    #     "CrossingPriceType": "EDP",
    #     "Rule80A": "P",
    #     "CashMargin": "1",
    #     "MarginTransactionType": "0",
    #     "MinQty": 0,
    #     "OrderClassification": "3",
    #     "SelfTradePreventionId": "0 "
    # }
    if not Data or Data == b'':
        return jsonify({"error": "Invalid request data"}), 400
    # 解析为python字符串
    datas = json.loads(Data)
    task_id = get_task_id()
    creator = datas["source"]
    create_time = datetime.now().isoformat()  # 获取当前时间并转换为字符串
    read_config(datas)
    # 将Data数据转换为json格式
    json_data_with_quotes = json.dumps(datas)
    run_all_shell = []
    # 构建命令参数列表
    command_args = ['python3', script_path, '--Data', json_data_with_quotes]
    run_all_shell.append(command_args)

    thread = threading.Thread(target=execute_task, args=(command_args, task_id))
    thread.start()
    status = "progressing"

    response = {
        'creator': creator,
        'taskId': task_id,
        'status': status,
        'createTime': create_time
    }

    insert_smoke_record(task_id, status, creator, create_time)
    return jsonify(response), 200


# 加载列表
@app_run_edp_smoke.route('/api/edp_smoke_list', methods=['GET'])
# @jwt_required()
def edp_smoke_list():
    try:
        # 从数据库池获取数据库连接
        connection = global_connection_pool.connection()
        # 创建游标
        cursor = connection.cursor()

        # 获取前端数据
        source = request.args.get('source')
        status = request.args.get('status')
        taskId = request.args.get('taskId')
        start_time = request.args.get('start_time')
        end_time = request.args.get('end_time')

        if not (source or status or taskId or start_time or end_time):
            sql = "SELECT taskId, status, CreateUser, CreateTime, output " \
                  "FROM qa_admin.SmokeRecord WHERE type = 1 ORDER BY CreateTime DESC"
            # 执行语句
            cursor.execute(sql)

        else:
            sql = "SELECT taskId, status, CreateUser, CreateTime, output " \
                  "FROM qa_admin.SmokeRecord WHERE type = 1"
            params = []
            if source:
                sql += "AND CreateUser=%S"
                params.append(source)
            if status:
                sql += "AND status=%S"
                params.append(status)
            if taskId:
                sql += "AND taskId=%S"
            if start_time and end_time:
                # 解析字符串类型的日期时间值为datetime 对象
                start_time = datetime.strptime(start_time, "%Y-%m-%d")
                end_time = datetime.strptime(end_time, "%Y-%m-%d")
                sql += " AND CreateTime >= %s AND CreateTime < %s"
                params.extend([start_time, end_time])

            sql += " ORDER BY CreateTime DESC"

            cursor.execute(sql, params)

        rows = cursor.fetchall()

        # 响应数据
        data = []
        for row in rows:
            # 将 datetime 对象 row['CreateTime'] 格式化为 %Y-%m-%d %H:%M:%S 的时间字符串
            format_create_time = row['CreateTime'].strftime("%Y-%m-%d %H:%M:%S")
            data.append(
                {
                    'taskId': row['taskId'],
                    'createTime': format_create_time,
                    'source': row['CreateUser'],
                    'status': row['status'],
                    'output': row['output']
                }
            )
        response = {
            'data': data
        }
        return jsonify(response), 200

    except Exception as e:
        error_message = str(e)
        traceback_details = traceback.format_exc()
        error_response = {'error': error_message,
                          'traceback': traceback_details}
        return jsonify(error_response), 500


    finally:
        cursor.close()
        connection.close()


@app_run_edp_smoke.route('/api/edp_smoke_list/download_edp_log', methods=['POST'])
# @jwt_required()
def download_log():
    Data = request.get_data()
    Datas = json.loads(Data)


    if Data is None or "taskId" not in Datas:
        return 'Invalid data', 400

    task_id = Datas["taskId"]

    try:
        # 从数据库池获取数据库连接
        connection = global_connection_pool.connection()
        # 创建游标
        cursor = connection.cursor()

        # 查询指定任务的log_file
        query = 'SELECT log_file,log_filename FROM qa_admin.SmokeRecord WHERE taskId = %s'
        cursor.execute(query, (task_id,))
        result = cursor.fetchone()

        if result is None:
            return 'File net found', 404

        if result['log_file'] is None or result['log_filename'] is None:
            return 'log file content not found', 400

        log_filename = result['log_filename']
        log_file_content = result['log_file']

        # 保存日志内容到临时文件
        log_temp_file = tempfile.NamedTemporaryFile(delete=False)
        log_temp_file.write(log_file_content)
        log_temp_file.close()

        # 创建响应对象
        response = make_response(
            send_file(log_temp_file.name, mimetype='text/plain', as_attachment=True, download_name='log_file.log'))
        # 设置响应头，指定文件名
        response.headers['Content-Disposition'] = f'attachment; filename={log_filename}'

        # 返回响应
        return response
    except Exception as e:
        return str(e), 500

    finally:
        cursor.close
        connection.close()
