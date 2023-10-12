# -*- coding:utf-8 -*-
import json
import os
import shutil
import subprocess
import zipfile
import time
import random
import tempfile
from flask_cors import CORS
from flasgger import swag_from
from datetime import datetime
from FSX_QA_SERVICE.apis.Application import global_connection_pool
from flask import send_file, Response, request, jsonify, Blueprint, make_response

app_run_edp_performance = Blueprint("run_edp_performance", __name__)
CORS(app_run_edp_performance, supports_credentials=True)
taskId = 0


def get_task_id():

    global taskId
    taskId += 1
    # 获取当前时间并且进行格式转换
    t = int(time.time())
    str1 = ''.join([str(i) for i in random.sample(range(0, 9), 2)])
    return str(t) + str1 + str(taskId).zfill(2)


def process_row(row):
    return {
        "createdTime": row["start_date"],
        "source": row["createUser"],
        "status": row["status"]
    }


@app_run_edp_performance.route('/api/performance_list/run_edp_performance', methods=['POST'])
@swag_from('../swagger_doc.yaml')
def run_edp_performance():
    '''
    {
    "source": "Admin",
    "commands": [
        {
            "value": "python3 edp_fix_client/initiator/edp_performance_test/edp_performance_application.py --account RSIT_EDP_ACCOUNT_1 --Sender RSIT_EDP_1 --Target FSX_SIT_EDP --Host 54.250.107.1 --Port 5001"
        },
        {
            "value": "python3 edp_fix_client/initiator/edp_performance_test/edp_performance_application.py --account RSIT_EDP_ACCOUNT_8 --Sender RSIT_EDP_8 --Target FSX_SIT_EDP --Host 54.250.107.1 --Port 5008"
        }
    ]
    }
    '''

    # 获取参数并将其转换为json格式
    data = request.get_data()
    if not data:
        return jsonify({"error": "Invalid request data"}), 400
    datas = json.loads(data)
    creator = datas["source"]
    start_time = None
    try:
        run_all_shell = []
        for param in datas['commands']:
            # 构建shell命令
            shell_command = param['value'] + " &\n" + "sleep 1\n"
            run_all_shell.append(shell_command)

        # 执行shell命令
        command = ''.join(run_all_shell)
        # 记录shell脚本开始执行的时间
        start_time = datetime.now()
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=1800)
        print(result)
        output = result.stdout.strip() if result.stdout else result.stderr.strip()
        result = "progressing"

    except subprocess.CalledProcessError as e:
        output = e.stderr.strip()
        result = "error"

    except subprocess.TimeoutExpired:
        output = "Execution time out"
        result = "error"

    # 记录结束时间
    end_time = datetime.now()

    # 计算执行时间
    execution_time = end_time - start_time
    taskId = get_task_id()

    response = {
        'creator': creator,
        'taskId': taskId,
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
    sql = "INSERT INTO `performance` (`status`, `taskId`, `start_date`, `end_date`, `type`, `createUser`) " \
          "VALUES (%s, %s, %s, %s, %s, %s)"
    values = (response['status'], taskId, response['start_time'], response['end_time'], response['type'], creator)

    try:
        cursor.execute(sql, values)
        connection.commit()
    except Exception as e:
        print("Error while inserting into the database:", e), 500

    finally:
        cursor.close()
        connection.close()
    json_response = json.dumps(response)

    return Response(json_response, mimetype='application/json'), 200


@app_run_edp_performance.route('/api/performance_list/download_performance_logs', methods=['GET'])
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
        log_path = "edp_fix_client/initiator/edp_performance_test/report/{}_Report.log".format(account)
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

    return response, 200


def create_zip_archive(file_paths, zip_file_path):
    with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_path in file_paths:
            zipf.write(file_path, os.path.basename(file_path))


@app_run_edp_performance.route('/api/performance_list/view_edp_performance_case', methods=['GET'])
@swag_from("../swagger_doc.yaml")
def view_edp_performance_case():

    '''
    {
    "filename":"topix400_case"
    }
    '''

    data = request.get_data()
    if data is None or data == '':
        return jsonify({"Error": "Invalid request data"}), 400

    datas = json.loads(data)
    file_name = datas["filename"]
    case_file_path = 'edp_fix_client/testcases/{}.json'.format(file_name)

    if os.path.exists(case_file_path):
        # 读取json文件
        with open(case_file_path, "r") as file:
            file_content = file.read()
            date = json.loads(file_content)
        # 获取testCase列表
        test_cases = date["testCase"]
        # 统计Symbol数量
        symbol_count = len([test_case["Symbol"] for test_case in test_cases])
        response = {
            "case_count": symbol_count,
            "file_content": file_content
        }
        return jsonify(response), 200
    else:
        return jsonify({"Error": "The file is not found"}), 404


@app_run_edp_performance.route('/api/edp_performance_list', methods=['GET'])
@swag_from("../swagger_doc.yaml")
def edp_performance_list():
    connection = global_connection_pool.connection()
    cursor = connection.cursor()
    try:
        # 统计数据总数
        count_sql = "SELECT COUNT(*) as total_count FROM `qa_admin`.performance WHERE `type` = 1;"
        cursor.execute(count_sql)
        total_count = cursor.fetchone()["total_count"]

        # 查询数据
        data_sql = "SELECT `start_date`, `status`, `createUser`, `taskId` FROM `qa_admin`.performance WHERE `type` = 1;"
        cursor.execute(data_sql)
        rows = cursor.fetchall()

        data = []
        for row in rows:
            data.append(
                {
                    "taskId": row["taskId"],
                    "createdTime": row["start_date"],
                    "source": row["createUser"],
                    "status": row["status"]
                }
            )
        response = {
            'total_count': total_count,
            'data': data
        }
        return jsonify(response), 200

    except Exception as e:
        return jsonify({"Error": str(e)}), 500

    finally:
        cursor.close()
        connection.close()


@app_run_edp_performance.route('/api/performance_list/search_performance_task', methods=['GET'])
@swag_from("../swagger_doc.yaml")
def search_performance_task():
    connection = global_connection_pool.connection()
    cursor = connection.cursor()

    data = request.get_data()

    if data is not None and data != b'':
        datas = json.loads(data)

        if 'pageSize' in datas and datas['pageSize'] != "":
            pageSize = datas["pageSize"]
        else:
            pageSize = 10

        if 'current' in datas and datas['current'] != "":
            current = datas["current"]
        else:
            current = 1

        sql = ""

        if "source" in datas and datas["source"] != "":
            sql += " AND `createUser` = '{}'".format(datas["source"])

        if "status" in datas and datas["status"] != "":
            sql += " AND `status` = '{}'".format(datas["status"])

        if "createdTime" in datas and datas["createdTime"] != "":
            sql += " AND `start_date` LIKE '%{}%'".format(datas["createdTime"])

        sql = sql + ' ORDER BY `start_date` DESC LIMIT {},{}'.format((current - 1) * pageSize, pageSize)

        try:
            # 统计数据总数
            count_sql = "SELECT COUNT(*) as total_count FROM `qa_admin`.performance WHERE `type` = 1" + sql
            print(count_sql)
            cursor.execute("SELECT COUNT(*) as total_count FROM `qa_admin`.performance WHERE `type` = 1" + sql)
            total_count = cursor.fetchone()["total_count"]

            # 查询数据
            cursor.execute("SELECT * FROM `qa_admin`.performance WHERE `type` = 1" + sql)
            search_result = cursor.fetchall()

            data = [process_row(row) for row in search_result]

            response = {
                "total_count": total_count,
                "data": data
            }

            return jsonify(response), 200

        except Exception as e:
            return jsonify({"error": str(e)}), 500

        finally:
            cursor.close()
            connection.close()

    else:
        try:
            print("kong ")
            # 统计数据总数
            cursor.execute("SELECT COUNT(*) as total_count FROM `qa_admin`.performance WHERE `type` = 1;")
            total_count = cursor.fetchone()["total_count"]

            # 查询数据
            cursor.execute("SELECT * FROM `qa_admin`.performance WHERE `type` = 1;")
            search_result = cursor.fetchall()

            data = [process_row(row) for row in search_result]

            response = {
                "total_count": total_count,
                "data": data
            }

            return jsonify(response), 200

        except Exception as e:
            return jsonify({"error": str(e)}), 500

        finally:
            cursor.close()
            connection.close()
