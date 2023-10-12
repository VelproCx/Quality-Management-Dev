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
from datetime import datetime
from FSX_QA_SERVICE.apis.Application import global_connection_pool
from flask import send_file, Response, request, jsonify, Blueprint, make_response, copy_current_request_context
app_run_edp_performance = Blueprint("run_edp_performance", __name__)
CORS(app_run_edp_performance, supports_credentials=True)


# 生成TaskId
def get_task_id():
    taskid = 1
    # 获取当前时间并且进行格式转换
    t = int(time.time())
    str1 = ''.join([str(i) for i in random.sample(range(0, 9), 2)])
    return str(t) + str1 + str(taskid).zfill(2)


# 避免重复代码
def process_row(row):
    return {
        "createdTime": row["start_date"],
        "source": row["createUser"],
        "status": row["status"],
        "taskId": row["taskId"]
    }


# 日志压缩
def create_zip_archive(file_paths, zip_file_path):
    with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_path in file_paths:
            zipf.write(file_path, os.path.basename(file_path))


# 压力测试等待子进程结束方法
def wait_and_handle_subprocess(processes):
    statuses = []
    outputs = []
    for process in processes:
        process.wait()
        status = process.returncode
        output_stdout, output_stderr = process.communicate()
        statuses.append(status)
        outputs.append((output_stdout, output_stderr))

    for status, output in zip(statuses, outputs):
        output_stdout, output_stderr = output
        print("这是output_stdout：", output_stdout)
        # 处理输出，可以根据需要进行处理
        print("这是output_stderr：", output_stderr)


# 压力测试异步处理--Flask 的异步任务处理机制
@copy_current_request_context
def send_progress_message(task_id, creator):
    # 在此处向前端发送"压力测试进行中"的消息
    # 可以使用 WebSocket 或其他实时通信机制
    # 从数据库池获取数据库连接
    connection = global_connection_pool.connection()
    # 创建游标
    cursor = connection.cursor()

    response = {

    }
    pass

@app_run_edp_performance.route('/api/edp_performance_list/run_edp_performance', methods=['POST'])
def run_edp_performance():
    # 获取参数并将其转换为json格式
    data = request.get_data()
    if not data:
        return jsonify({"error": "Invalid request data"}), 400
    datas = json.loads(data)
    creator = datas["source"]
    taskid = get_task_id()
    run_all_shell = []
    for param in datas['commands']:
        # 构建shell命令
        shell_command = param['value'] + " &\n" + "sleep 1\n"
        run_all_shell.append(shell_command)
    try:
        processes = []
        command = ''.join(run_all_shell)
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        processes.append(process)
        # 获取子进程的执行状态码和输出
        statuses = []
        outputs = []
        status_code = process.poll()
        if status_code is None:
            result = "progressing"
            # 向前端发送压力测试进行中的msg，并让接口后台运行，等待子进程结束
            pass
        for process in processes:
            process.wait()
            result = "completed"
            status = process.returncode
            output_stdout, output_stderr = process.communicate()
            statuses.append(status)
            outputs.append((output_stdout, output_stderr))

        for status, output in zip(statuses, outputs):
            output_stdout, output_stderr = output
            print("这是output_stdout：", output_stdout)
            # 处理输出，可以根据需要进行处理
            print("这是output_stderr：", output_stderr)

    except subprocess.CalledProcessError as e:
        output = e.stderr.strip()
        result = "error"
        print(output, result)

    except subprocess.TimeoutExpired:
        output = "Execution time out"
        result = "error"
        print(output, result)

    response = {
        'creator': creator,
        'taskId': taskid,
        'status': result,
        # 'output': output,
        # 'start_time': start_time.strftime("%Y-%m-%d %H:%M:%S"),
        # 'execution_time': str(execution_time),
        # 'end_time': end_time.strftime("%Y-%m-%d %H:%M:%S"),
        'type': 1
    }

    # 从数据库池获取数据库连接
    connection = global_connection_pool.connection()
    # 创建游标
    cursor = connection.cursor()

    # 构建SQL语句
    sql = "INSERT INTO `PerformanceRecord` (`taskId`, `type`, `createUser`, `status`) " \
          "VALUES (%s, %s, %s, %s)"
    values = (taskid, response['type'], creator, response["status"])

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


@app_run_edp_performance.route('/api/edp_performance_list/download_performance_logs', methods=['GET'])
def download_performance_log_file():
    date = request.args.to_dict()
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


@app_run_edp_performance.route('/api/edp_performance_list/view_edp_performance_case', methods=['GET'])
def view_edp_performance_case():
    data = request.args.to_dict()
    if data is None or data == '':
        return jsonify({"Error": "Invalid request data"}), 400
    file_name = data["filename"]
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
def edp_performance_list():
    connection = global_connection_pool.connection()
    cursor = connection.cursor()
    data = request.args.to_dict()
    if data is not None and data != '':
        # if 'pageSize' in data and data['pageSize'] != "":
        #     str_pageSize = data["pageSize"]
        #     pageSize = int(str_pageSize)
        # else:
        #     pageSize = 10
        #
        # if 'current' in data and data['current'] != "":
        #     str_current = data["current"]
        #     current = int(str_current)
        # else:
        #     current = 1
        sql = ""
        if "source" in data and data["source"] != "":
            sql += " AND `createUser` = '{}'".format(data["source"])
        if "status" in data and data["status"] != "":
            sql += " AND `status` = '{}'".format(data["status"])
        if "createdTime" in data and data["createdTime"] != "":
            sql += " AND `start_date` LIKE '%{}%'".format(data["createdTime"])
        if "taskId" in data and data["taskId"] != "":
            sql += " AND `taskId` LIKE '%{}%'".format(data["taskId"])
        sql = sql + ' ORDER BY `start_date` DESC'
        try:
            # 统计数据总数
            cursor.execute("SELECT COUNT(*) as total_count FROM `qa_admin`.PerformanceRecord WHERE `type` = 1" + sql)
            total_count = cursor.fetchone()["total_count"]
            # 查询数据
            cursor.execute("SELECT * FROM `qa_admin`.PerformanceRecord WHERE `type` = 1" + sql)
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
            # 统计数据总数
            count_sql = "SELECT COUNT(*) as total_count FROM `qa_admin`.PerformanceRecord WHERE `type` = 1;"
            cursor.execute(count_sql)
            total_count = cursor.fetchone()["total_count"]
            # 查询数据
            data_sql = "SELECT `start_date`, `status`, `createUser`, `taskId` " \
                       "FROM `qa_admin`.PerformanceRecord " \
                       "WHERE `type` = 1;"
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
