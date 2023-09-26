import json
import os
from flask import Flask, send_file, Response, jsonify, request
import subprocess
from datetime import datetime, timedelta
from flask_cors import CORS
from configparser import ConfigParser
from flasgger import Swagger, swag_from
from FSX_QA_SERVICE.apis.Application import global_connection_pool
import pymysql

# 读取INI配置文件
config = ConfigParser()
config.read('../config/settings.ini')
config_file = '../edp_fix_client/initiator/edp_regression_test/edp_regression_client.cfg'


# 使用 str() 函数将 timedelta 对象转换为可序列化的形式
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, timedelta):
            return str(obj)
        return super().default(obj)


app = Flask(__name__)
swagger = Swagger(app)
CORS(app)  # 允许跨域请求
# app.json_encoder = CustomJSONEncoder

config = ConfigParser()


# 运行 regression
@app.route('/api/run_edp_regression', methods=['POST'])
@swag_from('../swagger_doc.yaml')
def run_regression():
    title = request.form.get('title')  # 获取title
    creator = request.form.get('creator')  # 获取创建人

    # 定义文件路径和文件名
    file_path = '../edp_fix_client/initiator/edp_regression_test/edp_regression_application.py'

    start_time = datetime.now()  # 记录开始时间

    try:
        result = subprocess.run(['python3', file_path], capture_output=True, text=True, timeout=1800)
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

    # 构建插入SQL语句
    sql = "INSERT INTO regression (status, title, start_date, end_date, type, createUser) VALUES (%s, %s, %s, %s, %s, %s)"
    values = (response['status'], title, response['start_time'], end_time, int(response['type']), creator)
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
@app.route('/api/download_edp_logs', methods=['GET'])
@swag_from('../swagger_doc.yaml')
def download_log_file():
    log_file_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + \
                '/edp_fix_client/initiator/edp_regression_test/logs/edp_report.log'

    if os.path.exists(log_file_path):
        return send_file(log_file_path, as_attachment=True), 200
    else:
        return jsonify({'error': 'The file is not found'}), 404


# 下载 edp_report.xlsx
@app.route('/api/download_edp_reports', methods=['GET'])
@swag_from('../swagger_doc.yaml')
def download_report_file():
    report_file_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + \
                '/edp_fix_client/initiator/edp_regression_test/report/edp_report.xlsx'

    if os.path.exists(report_file_path):
        return send_file(report_file_path, as_attachment=True), 200
    else:
        return jsonify({'error': 'The file is not found'}), 404


# 预览edp_report.log
@app.route('/api/preview_edp_log', methods=['GET'])
@swag_from('../swagger_doc.yaml')
def preview_edp_logs():
    log_file_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + \
                '/edp_fix_client/initiator/edp_regression_test/logs/edp_report.log'

    if os.path.exists(log_file_path):
        return send_file(log_file_path), 200
    else:
        return jsonify({'error': 'The file is not found'}), 404


# 预览edp_report.xlsx
@app.route('/api/preview_edp_report', methods=['GET'])
@swag_from('../swagger_doc.yaml')
def preview_edp_report():
    xlsx_file_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + \
                '/edp_fix_client/initiator/edp_regression_test/report/edp_report.xlsx'
    if os.path.exists(xlsx_file_path):
        return send_file(xlsx_file_path, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                     as_attachment=False), 200
    else:
        return jsonify({'error': 'The file is not found'}), 404


# 在线编辑case
@app.route('/api/update_edp_testcases', methods=['POST'])
@swag_from('../swagger_doc.yaml')
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
@app.route('/api/update_edp_config', methods=['POST'])
@swag_from('../swagger_doc.yaml')
def update_edp_config():
    section = request.form.get('section')
    key = request.form.get('key')
    value = request.form.get('value')

    update_config(section, key, value)

    return jsonify({'message': f'Section "{section}", Key "{key}" updated successfully'}), 200


# 获取edp_regression运行历史列表
@app.route('/api/edp_regression_list', methods=['GET'])
@swag_from('../swagger_doc.yaml')
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


if __name__ == '__main__':
    app.run()