import asyncio
import json
import os
import platform
import signal
import tempfile
import time
import random
import traceback
from flask import Flask, send_file, Response, jsonify, request, Blueprint, stream_with_context, make_response
import subprocess
from datetime import datetime, timedelta
from flask_cors import CORS
from configparser import ConfigParser

from flask_jwt_extended import jwt_required

from FSX_QA_SERVICE.apis.Application import global_connection_pool
import pymysql

# 读取INI配置文件
config = ConfigParser()
config.read('../config/settings.ini')
config_file = 'rolx_fix_client/initiator/rolx_regression_test/rolx_regression_client.cfg'

# 获取当前日期
current_date = datetime.now().strftime("%Y-%m-%d")
report_filename = f"rolx_report_{current_date}.xlsx"
log_filename = f"rolx_report_{current_date}.log"

report_file_path = 'rolx_fix_client/initiator/rolx_regression_test/report/' + report_filename
log_file_path = 'rolx_fix_client/initiator/rolx_regression_test/logs/' + log_filename


# 使用 str() 函数将 timedelta 对象转换为可序列化的形式
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, timedelta):
            return str(obj)
        return super().default(obj)


app_run_rolx_regression = Blueprint("run_rolx_regression", __name__)
CORS(app_run_rolx_regression)  # 允许跨域请求
taskId = 0


# 生成task_id
def get_task_id():
    global taskId
    taskId += 1
    # 获取当前时间并且进行格式转换
    t = int(time.time())
    str1 = ''.join([str(i) for i in random.sample(range(0, 9), 2)])
    return str(t) + str1 + str(taskId).zfill(2)


# 将参数按照指定的编码方式解码为字符串
def _decode_bytes(_bytes):
    encodings = 'utf-8'
    return _bytes.decode(encodings)


# 将字节流（bytes）解码为字符串
def _decode_stream(stream):
    if not stream:
        return ''
    return _decode_bytes(stream.read())


def insert_response_data(response):
    # 从数据库池获取数据库连接
    connection = global_connection_pool.connection()
    # 创建游标
    cursor = connection.cursor()
    output = response.get('output', '')  # 获取response中的output字段，如果不存在则默认为空字符串

    # 检查描述字段的长度
    if len(output) > 255:
        output = output[:255]  # 截取前 255 个字符

    # 构建查询语句,查询是否存在相同的taskId
    query_sql = "SELECT COUNT(*) FROM RegressionRecord WHERE taskId = %s"
    cursor.execute(query_sql, (response["taskId"],))
    result = cursor.fetchone()
    row_count = result["COUNT(*)"]

    try:
        if row_count > 0:
            try:
                # 使用二进制读取log文件
                with open(log_file_path, 'rb') as file:
                    log_file = file.read()

                # 使用二进制读取xlsx文件
                with open(report_file_path, 'rb') as file:
                    excel_file = file.read()
            except FileNotFoundError:
                pass

            # 如果存在相同的taskId，则执行更新,更新任务状态,文件
            update_sql = "UPDATE RegressionRecord SET status = %s, " \
                         "log_file = %s, excel_file = %s, output = %s, report_filename = %s, log_filename = %s " \
                         "WHERE taskId = %s"
            update_values = (
                response['status'], log_file, excel_file, output, report_filename, log_filename, response['taskId'])
            cursor.execute(update_sql, update_values)
            connection.commit()
        else:
            # 构建插入SQL语句
            insert_sql = \
                "INSERT INTO RegressionRecord (taskId, status, type, CreateUser, CreateTime, output)" \
                "VALUES (%s, %s, %s, %s, %s, %s)"
            insert_values = (
                response['taskId'], response['status'], int(response['type']), response['source'],
                response['createTime'], output)

            # 执行插入操作
            cursor.execute(insert_sql, insert_values)
            connection.commit()

    except Exception as e:
        print("Error while inserting into the database:", e)

    finally:
        # 关闭游标和连接
        cursor.close()
        connection.close()


def execute_task(datas):
    creator = datas["source"]
    wait_timeout = 5
    cnt, maxcnt = 0, 2
    retcode = None  # 初始化 retcode
    stderr = ""
    output = None
    taskId = get_task_id()
    status = "progressing"
    create_time = datetime.now().isoformat()  # 获取当前时间并转换为字符串

    run_all_shell = []
    for param in datas['commands']:
        # 构建 shell命令
        shell_command = param['value'] + '&\n' + 'sleep 1\n'
        run_all_shell.append(shell_command)

    command = ''.join(run_all_shell)

    try:
        p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)

        # 在等待时发送中间状态的响应给前端
        response = {
            'taskId': taskId,
            'source': creator,
            'status': status,
            'createTime': create_time,
            'type': 2
        }
        yield 'data: {}\n\n'.format(json.dumps(response))
        # 插入数据库
        insert_response_data(response)

        while cnt < maxcnt:
            try:
                p.wait(timeout=wait_timeout)

            except Exception as e:
                print(f'attemp{cnt} -> wait error:{e}')
                cnt += 1
            finally:
                if p.returncode is not None:  # 查看是否有退出码,判断进程是否结束
                    break

        # 进程没有超时或没有完成时,杀掉进程
        if p.returncode is None:
            print('[Error] retcode is None, maybe timeout, try kill process...')
            if platform.system() == 'Windows':
                kill_proc_ret = subprocess.run(['taskkill', '/f', '/pid', str(p.pid)], capture_output=True)
                print(f'[KILLPROC]{_decode_bytes(kill_proc_ret.stdout)}')
            else:
                os.kill(p.pid, signal.SIGKILL)

        else:
            retcode, output, stderr = p.returncode, _decode_stream(p.stdout), _decode_stream(p.stderr)
            if stderr == "":  # 进程为空
                output = "connect error, please check the config"
                retcode = 1  # 设置 retcode 为非零值，表示发生了错误,脚本没有执行成功

            elif 'Error:' in stderr:  # 进程执行信息有错误
                output = stderr.split('Error:', 1)[-1].strip()
                retcode = 1

    # 进程出错被中断
    except Exception as e:
        print("Error executing subprocess:", e)
        retcode = 1  # 设置错误码为非零值
        output = e  # 使用异常信息作为错误信息

    if retcode == 0:
        status = "completed"
        response = {
            'taskId': taskId,
            'source': creator,
            'createTime': create_time,
            'retcode': retcode,
            'status': status,
            'type': 2
        }

    else:
        status = "error"
        response = {
            'taskId': taskId,
            'source': creator,
            'createTime': create_time,
            'retcode': retcode,
            'status': status,
            'output': output,
            'type': 2
        }

    # 最后发送最终状态的响应给前端
    yield 'data: {}\n\n'.format(json.dumps(response))
    # 插入数据库
    insert_response_data(response)


@app_run_rolx_regression.route('/api/rolx_regression_list/run_rolx_regression', methods=['POST'])
@jwt_required()
def run_rolx_regression():
    data = request.get_data()
    datas = json.loads(data)
    if not data:
        return jsonify({"error": "Invalid request data, check the commands"}), 400

    # 设置响应头，指定内容类型为text/event-stream
    headers = {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive'
    }

    # 将生成器转换为响应对象
    return Response(stream_with_context(execute_task(datas)), headers=headers), 200


# 获取 rolx_regression 运行列表
@app_run_rolx_regression.route('/api/rolx_regression_list', methods=['GET'])
@jwt_required()
def rolx_regression_list():
    try:
        connection = global_connection_pool.connection()
        cursor = connection.cursor()

        # 获取前端传回的参数
        source = request.args.get('source')
        status = request.args.get('status')
        taskId = request.args.get('taskId')
        start_time = request.args.get('startTime')
        end_time = request.args.get('endTime')

        # 构建查询语句和参数
        sql = "SELECT taskId, status, CreateUser, CreateTime, output " \
              "FROM qa_admin.RegressionRecord WHERE type = 2"

        params = []
        if source:
            sql += " AND CreateUser = %s"
            params.append(source)
        if status:
            sql += " AND status = %s"
            params.append(status)
        if taskId:
            sql += " AND taskId = %s"
            params.append(taskId)
        if start_time and end_time:
            # 假设前端传回的时间字符串格式为 "%Y-%m-%d %H:%M:%S"
            start_time = datetime.strptime(start_time, "%Y-%m-%d")
            end_time = (datetime.strptime(end_time, "%Y-%m-%d")) + timedelta(days=1)
            sql += " AND CreateTime >= %s AND CreateTime < %s"
            params.extend([start_time, end_time])

        sql += " ORDER BY CreateTime DESC"

        cursor.execute(sql, params)
        rows = cursor.fetchall()

        # 构建响应数据
        data = []
        for row in rows:
            # 将 datetime 对象 row['CreateTime'] 格式化为 %Y-%m-%d %H:%M:%S 的时间字符串
            formatted_create_time = row['CreateTime'].strftime("%Y-%m-%d %H:%M:%S")
            data.append(
                {
                    'taskId': row['taskId'],
                    'createTime': formatted_create_time,
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
        traceback_details = traceback.format_exc()  # 抛出异常详细描述
        error_response = {
            'error': error_message,
            'traceback': traceback_details
        }
        return jsonify(error_response), 500

    finally:
        # 关闭数据库
        cursor.close()
        connection.close()


# 下载 rolx_report.log
@app_run_rolx_regression.route('/api/rolx_regression_list/download_rolx_log/<task_id>', methods=['GET'])
@jwt_required()
def download_log_file(task_id):
    if not task_id:
        return 'task_id is missing', 400

    try:
        # 连接数据库
        connection = global_connection_pool.connection()
        cursor = connection.cursor()

        # 查询指定任务的 log_file
        query = "SELECT log_file FROM qa_admin.RegressionRecord WHERE taskId = %s"
        cursor.execute(query, (task_id,))
        result = cursor.fetchone()

        if result is None:
            return 'File not found', 404

        log_file_content = result['log_file']

        # 保存日志内容到临时文件
        temp_file = tempfile.NamedTemporaryFile(delete=False)
        temp_file.write(log_file_content)
        temp_file.close()

        # 创建响应对象
        response = make_response(
            send_file(temp_file.name, mimetype='text/plain', as_attachment=True, download_name='log_file.log'))

        # 设置响应头，指定文件名
        response.headers['Content-Disposition'] = f'attachment; filename={log_filename}'

        # 返回响应
        return response

    except pymysql.Error as e:
        return str(e), 500

    finally:
        cursor.close()
        connection.close()


# 下载 rolx_report.xlsx
@app_run_rolx_regression.route('/api/rolx_regression_list/download_rolx_report/<task_id>', methods=['GET'])
@jwt_required()
def download_report_file(task_id):
    if not task_id:
        return 'task_id is missing', 400
    try:
        # 连接数据库
        connection = global_connection_pool.connection()
        cursor = connection.cursor()

        # 查询指定任务的 log_file
        query = "SELECT excel_file FROM qa_admin.RegressionRecord WHERE taskId = %s"
        cursor.execute(query, (task_id,))
        result = cursor.fetchone()

        if result is None:
            return 'File not found', 404

        excel_file_content = result['excel_file']

        # 保存日志内容到临时文件
        excel_temp_file = tempfile.NamedTemporaryFile(delete=False)
        excel_temp_file.write(excel_file_content)
        excel_temp_file.close()

        # 创建响应对象
        response = make_response(
            send_file(excel_temp_file.name, mimetype='text/plain', as_attachment=True, download_name='report.xlsx'))

        # 设置响应头，指定文件名
        response.headers['Content-Disposition'] = f'attachment; filename={report_filename}'

        # 返回响应
        return response

    except pymysql.Error as e:
        return str(e), 500

    finally:
        cursor.close()
        connection.close()


# 在线编辑case
@app_run_rolx_regression.route('/api/update_rolx_testcases', methods=['POST'])
@jwt_required()
def update_rolx_testcases():
    data = request.get_json()  # 获取请求中的json数据

    # 读取json文件
    with open('../rolx_fix_client/testcases/test.json', 'r') as file:
        json_data = json.load(file)

    # 更新json数据
    json_data.update(data)

    # 保存更新后的json数据到文件
    with open('../rolx_fix_client/testcases/test.json', 'w') as file:
        json.dump(json_data, file, indent=4)

    return jsonify({'message': 'JSON file updated and saved successfully'}), 200
