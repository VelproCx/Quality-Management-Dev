import json
import tempfile
import threading
import time
import random
import traceback
from flask import send_file, jsonify, request, Blueprint, make_response
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
config_file = 'edp_fix_client/initiator/edp_regression_test/edp_regression_client.cfg'

# 获取当前日期
current_date = datetime.now().strftime("%Y-%m-%d")
report_filename = f"edp_report_{current_date}.xlsx"
log_filename = f"edp_report_{current_date}.log"

report_file_path = 'edp_fix_client/initiator/edp_regression_test/report/' + report_filename
log_file_path = 'edp_fix_client/initiator/edp_regression_test/logs/' + log_filename


# 使用 str() 函数将 timedelta 对象转换为可序列化的形式
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, timedelta):
            return str(obj)
        return super().default(obj)


app_run_edp_regression = Blueprint("run_edp_regression", __name__)
CORS(app_run_edp_regression)  # 允许跨域请求
taskId = 0


# 生成task_id
def get_task_id():
    global taskId
    taskId += 1
    # 获取当前时间并且进行格式转换
    t = int(time.time())
    str1 = ''.join([str(i) for i in random.sample(range(0, 9), 2)])
    return str(t) + str1 + str(taskId).zfill(2)


def update_regression_record(task_id, status, output):
    # 从数据库池获取数据库连接
    connection = global_connection_pool.connection()
    # 创建游标
    cursor = connection.cursor()
    log_file = None
    excel_file = None  # 初始化 excel_file 变量

    # 检查描述字段的长度
    if len(output) > 255:
        output = output[:255]  # 截取前 255 个字符

    try:
        try:
            # 使用二进制读取log文件
            with open(log_file_path, 'rb') as file:
                log_file = file.read()

            # 使用二进制读取xlsx文件
            with open(report_file_path, 'rb') as file:
                excel_file = file.read()
        except FileNotFoundError as e:
            print("file error:", e)

        # 如果存在相同的taskId，则执行更新,更新任务状态,文件
        update_sql = "UPDATE RegressionRecord SET status = %s, " \
                     "log_file = %s, excel_file = %s, output = %s, report_filename = %s, log_filename = %s " \
                     "WHERE taskId = %s"
        update_values = (
            status, log_file, excel_file, output, report_filename, log_filename, task_id)
        cursor.execute(update_sql, update_values)
        connection.commit()


    except Exception as e:
        print("Error while inserting into the database:", e)

    finally:
        # 关闭游标和连接
        cursor.close()
        connection.close()


def insert_regression_record(task_id, creator, status, create_time):
    # 从数据库池获取数据库连接
    connection = global_connection_pool.connection()
    # 创建游标
    cursor = connection.cursor()
    try:
        # 构建插入SQL语句
        insert_sql = \
            "INSERT INTO RegressionRecord (taskId, status, CreateUser, CreateTime, type)" \
            "VALUES (%s, %s, %s, %s, %s)"
        insert_values = (task_id, status, creator, create_time, 1)

        # 执行插入操作
        cursor.execute(insert_sql, insert_values)
        connection.commit()

    except Exception as e:
        print("Error while inserting into the database:", e)

    finally:
        # 关闭游标和连接
        cursor.close()
        connection.close()


def execute_task(shell_commands, task_id):
    try:
        p = subprocess.Popen(shell_commands, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        p.wait()
        outputs = p.communicate()
        stderr = outputs[1].decode('utf-8')

        if stderr == "":  # 进程为空
            status = "error"
            output = "connect error, please check the config"

        elif 'Error:' in stderr:  # 进程执行信息有错误
            status = "error"
            output = stderr.split('Error:', 1)[-1].strip()
        else:
            status = "completed"
            output = " "

    # 进程出错被中断
    except Exception as e:
        print("Error executing subprocess:", e)
        output = e  # 使用异常信息作为错误信息
        status = "error"

    # 更新数据库
    update_regression_record(task_id, status, output)


@app_run_edp_regression.route('/api/edp_regression_list/run_edp_regression', methods=['POST'])
@jwt_required()
def run_edp_regression():
    # 从请求体中获取数据
    data = request.get_data()
    if not data or data == b'':
        return jsonify({"error": "Invalid request data"}), 400
    # 数据转换
    datas = json.loads(data)
    task_id = get_task_id()
    creator = datas["source"]
    create_time = datetime.now().isoformat()  # 获取当前时间并转换为字符串

    # 创建一个空数组用于存放shell命令
    commands = []
    # 循环从请求体中将shell命令读取出来
    for command in datas["commands"]:
        shell = command["value"] + " &\n" + "sleep 1\n"
        commands.append(shell)
    # 格式化数组中的shell命令
    shell_commands = ''.join(commands)

    thread = threading.Thread(target=execute_task, args=(shell_commands, task_id))
    thread.start()

    status = "progressing"

    response = {
        'creator': creator,
        'taskId': task_id,
        'status': status,
        'createTime': create_time,
    }

    insert_regression_record(task_id, creator, status, create_time)
    return jsonify(response), 200


# 获取 edp_regression 运行列表
@app_run_edp_regression.route('/api/edp_regression_list', methods=['GET'])
@jwt_required()
def edp_regression_list():
    try:
        connection = global_connection_pool.connection()
        cursor = connection.cursor()

        # 获取前端传回的参数
        source = request.args.get('source')
        status = request.args.get('status')
        taskId = request.args.get('taskId')
        start_time = request.args.get('startTime')
        end_time = request.args.get('endTime')
        # 检查是否有传递任何参数
        if not (source or status or taskId or start_time or end_time):
            # 如果没有传递任何参数，则默认显示所有数据
            sql = "SELECT taskId, status, CreateUser, CreateTime, output " \
                  "FROM qa_admin.RegressionRecord WHERE type = 1 " \
                  "ORDER BY CreateTime DESC"
            cursor.execute(sql)
        else:
            # 构建查询语句和参数
            sql = "SELECT taskId, status, CreateUser, CreateTime, output " \
                  "FROM qa_admin.RegressionRecord WHERE type = 1"
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


# 下载 edp_report.log
@app_run_edp_regression.route('/api/edp_regression_list/download_edp_log', methods=['POST'])
@jwt_required()
def download_log_file():
    data = request.get_data()
    datas = json.loads(data)

    if data is None or "taskId" not in datas:
        return 'Invalid data', 400

    task_id = datas["taskId"]
    try:
        # 连接数据库
        connection = global_connection_pool.connection()
        cursor = connection.cursor()

        # 查询指定任务的 log_file
        query = "SELECT log_file, log_filename FROM qa_admin.RegressionRecord WHERE taskId = %s"
        cursor.execute(query, (task_id,))
        result = cursor.fetchone()

        if result is None:
            return 'File not found', 404

        if result['log_file'] is None or result['log_filename'] is None:
            return 'Log file content not found', 404

        log_filename = result['log_filename']
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


# 下载 edp_report.xlsx
@app_run_edp_regression.route('/api/edp_regression_list/download_edp_report', methods=['POST'])
@jwt_required()
def download_report_file():
    data = request.get_data()
    datas = json.loads(data)
    if data is None or "taskId" not in datas:
        return 'Invalid data', 400

    task_id = datas["taskId"]
    if data is None:
        return 'Invalid file path', 400
    try:
        # 连接数据库
        connection = global_connection_pool.connection()
        cursor = connection.cursor()

        # 查询指定任务的 log_file
        query = "SELECT excel_file,report_filename FROM qa_admin.RegressionRecord WHERE taskId = %s"
        cursor.execute(query, (task_id,))
        result = cursor.fetchone()
        if result is None:
            return 'File not found', 404

        if result['report_filename'] is None or result['excel_file'] is None:
            return 'report file content not found', 404

        report_filename = result['report_filename']
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
