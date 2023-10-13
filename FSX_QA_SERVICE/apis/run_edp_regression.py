import asyncio
import json
import os
import platform
import signal
import time
import random

from flask import Flask, send_file, Response, jsonify, request, Blueprint, stream_with_context
import subprocess
from datetime import datetime, timedelta
from flask_cors import CORS
from configparser import ConfigParser
from FSX_QA_SERVICE.apis.Application import global_connection_pool
import pymysql

# 读取INI配置文件
config = ConfigParser()
config.read('../config/settings.ini')
config_file = 'edp_fix_client/initiator/edp_regression_test/edp_regression_client.cfg'


# 使用 str() 函数将 timedelta 对象转换为可序列化的形式
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, timedelta):
            return str(obj)
        return super().default(obj)


app_run_edp_regression = Blueprint("run_edp_regression", __name__)
CORS(app_run_edp_regression)  # 允许跨域请求
taskId = 0


def get_task_id():
    global taskId
    taskId += 1
    # 获取当前时间并且进行格式转换
    t = int(time.time())
    str1 = ''.join([str(i) for i in random.sample(range(0, 9), 2)])
    return str(t) + str1 + str(taskId).zfill(2)


def _decode_bytes(_bytes):
    encodings = 'utf-8'
    return _bytes.decode(encodings)


def _decode_stream(stream):
    if not stream:
        return ''
    return _decode_bytes(stream.read())


def execute_task(datas):
    creator = datas["source"]
    wait_timeout = 5
    cnt, maxcnt = 0, 4
    retcode = None  # 初始化 retcode
    stdout = ""
    stderr = ""
    status = "progressing"


    run_all_shell = []
    for param in datas['commands']:
        # 构建 shell命令
        shell_command = param['value'] + '&\n' + 'sleep 1\n'
        run_all_shell.append(shell_command)

    command = ''.join(run_all_shell)

    p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    returncode = p.poll()
    print(returncode)

    # 在等待时发送中间状态的响应给前端
    response = {
        'creator': creator,
        'status': status
    }
    yield 'data: {}\n\n'.format(json.dumps(response))

    # yield json.dumps({"status": status})  # 使用 json.dumps 将字典转换为 JSON 字符串

    while cnt < maxcnt:
        try:
            p.wait(timeout=wait_timeout)
        except Exception as e:
            print(f'attemp{cnt} -> wait error:{e}')
            cnt += 1
        finally:
            if p.returncode is not None:  # 查看是否有退出码,判断进程是否结束
                break

                # 更新响应字典的中间状态字段
        response['stderr'] = stderr
        response['status'] = status

        # 发送中间状态的响应给前端
        yield 'data: {}\n\n'.format(json.dumps(response))

    if p.returncode is None:
        print('[Error] retcode is None, maybe timeout, try kill process...')
        status = "error"
        if platform.system() == 'Windows':
            kill_proc_ret = subprocess.run(['taskkill', '/f', '/pid', str(p.pid)], capture_output=True)
            print(f'[KILLPROC]{_decode_bytes(kill_proc_ret.stdout)}')
        else:
            os.kill(p.pid, signal.SIGKILL)

    else:
        retcode, stdout, stderr = p.returncode, _decode_stream(p.stdout), _decode_stream(p.stderr)
        if stderr == "":
            print(f'[Error] stderr: {stderr}')
            retcode = 1  # 设置 retcode 为非零值，表示发生了错误,脚本没有执行成功

    if retcode == 0:
        status = "completed"
    else:
        status = "error"


    response = {
        'creator': creator,
        'stdout': stdout,
        'retcode': retcode,
        'stderr': stderr,
        'status': status
    }

    # 最后发送最终状态的响应给前端
    yield 'data: {}\n\n'.format(json.dumps(response))


@app_run_edp_regression.route('/api/edp_regression_list/run_edp_regression', methods=['POST'])
def run_edp_regression():
    data = request.get_data()
    datas = json.loads(data)
    if not data:
        return jsonify({"error": "Invalid request data"}), 400

    # 设置响应头，指定内容类型为text/event-stream
    headers = {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive'
    }

    # 将生成器转换为响应对象
    return Response(stream_with_context(execute_task(datas)), headers=headers)


# 运行 regression
@app_run_edp_regression.route('/api/run_edp_regression', methods=['POST'])
def run_regression():
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

        command = ''.join(run_all_shell)
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

    except KeyboardInterrupt:
        output = "Execution interrupted"
        result = "Fail"

    end_time = datetime.now()  # 记录结束时间
    execution_time = end_time - start_time  # 计算执行时间
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

    # 构建插入SQL语句
    sql = "INSERT INTO regression (taskId, status, type, start_date, end_date, createUser) VALUES (%s, %s, %s, %s, %s, %s)"
    values = (taskId, response['status'], int(response['type']), response['start_time'], response['end_time'],
              response['creator'])
    try:
        # 执行插入操作
        cursor.execute(sql, values)
        connection.commit()
    except Exception as e:
        print("Error while inserting into the database:", e)

    finally:
        # 关闭游标和连接
        cursor.close()
        connection.close()

    json_response = json.dumps(response)
    return Response(json_response, mimetype='application/json'), 200


# 下载 edp_report.log
@app_run_edp_regression.route('/api/download_edp_logs', methods=['GET'])
def download_log_file():
    log_file_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + \
                    '/edp_fix_client/initiator/edp_regression_test/logs/edp_report.log'

    if os.path.exists(log_file_path):
        return send_file(log_file_path, as_attachment=True), 200
    else:
        return jsonify({'error': 'The file is not found'}), 404


# 下载 edp_report.xlsx
@app_run_edp_regression.route('/api/download_edp_reports', methods=['GET'])
def download_report_file():
    report_file_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + \
                       '/edp_fix_client/initiator/edp_regression_test/report/edp_report.xlsx'

    if os.path.exists(report_file_path):
        return send_file(report_file_path, as_attachment=True), 200
    else:
        return jsonify({'error': 'The file is not found'}), 404


# 预览edp_report.log
@app_run_edp_regression.route('/api/preview_edp_log', methods=['GET'])
def preview_edp_logs():
    log_file_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + \
                    '/edp_fix_client/initiator/edp_regression_test/logs/edp_report.log'

    if os.path.exists(log_file_path):
        return send_file(log_file_path), 200
    else:
        return jsonify({'error': 'The file is not found'}), 404


# 预览edp_report.xlsx
@app_run_edp_regression.route('/api/preview_edp_report', methods=['GET'])
def preview_edp_report():
    xlsx_file_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + \
                     '/edp_fix_client/initiator/edp_regression_test/report/edp_report.xlsx'
    if os.path.exists(xlsx_file_path):
        return send_file(xlsx_file_path, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                         as_attachment=False), 200
    else:
        return jsonify({'error': 'The file is not found'}), 404


# 在线编辑case
@app_run_edp_regression.route('/api/update_edp_testcases', methods=['POST'])
def update_edp_testcases():
    data = request.get_json()  # 获取请求中的json数据

    # 读取json文件
    with open('../edp_fix_client/testcases/test.json', 'r') as file:
        json_data = json.load(file)

    # 更新json数据
    json_data.update(data)

    # 保存更新后的json数据到文件
    with open('../edp_fix_client/testcases/test.json', 'w') as file:
        json.dump(json_data, file, indent=4)

    return jsonify({'message': 'JSON file updated and saved successfully'}), 200


def update_config(section, key, value):
    config = ConfigParser(allow_no_value=True)
    config.optionxform = str  # 保持键的大小写

    # 读取原始文件的内容
    with open(config_file, 'r') as file:
        config.read_file(file)

    # 修改配置
    config.set(section, key, value)

    # 保存修改后的配置
    with open(config_file, 'w') as file:
        config.write(file, space_around_delimiters=False)


# 编辑配置文件
@app_run_edp_regression.route('/api/update_edp_config', methods=['POST'])
def update_edp_config():
    # section = request.form.get('section')
    key = request.form.get('key')
    value = request.form.get('value')

    update_config('SESSION', key, value)

    return jsonify({'message': f' Key "{key}" updated successfully'}), 200


# 获取edp_regression运行历史列表
@app_run_edp_regression.route('/api/edp_regression_list', methods=['GET'])
def edp_regression_list():
    try:
        connection = global_connection_pool.connection()
        cursor = connection.cursor()

        sql = "SELECT title, status, createUser, execution_time, start_date, end_date FROM qa_admin.regression where type = 1;"
        cursor.execute(sql)
        rows = cursor.fetchall()

        # 构建响应数据
        data = []
        for row in rows:
            data.append(
                {
                    'title': row['title'],
                    'status': row['status'],
                    'createUser': row['createUser'],
                    'execution_time': str(row['execution_time']),
                    'start_date': row['start_date'].strftime("%Y-%m-%d %H:%M:%S"),
                    'end_date': row['end_date'].strftime("%Y-%m-%d %H:%M:%S")
                }
            )
        response = {
            'data': data
        }
        return jsonify(response), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    finally:
        # 关闭数据库
        cursor.close()
        connection.close()

# if __name__ == '__main__':
#     app.run()
