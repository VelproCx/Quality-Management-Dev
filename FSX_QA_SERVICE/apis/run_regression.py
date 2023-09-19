import json
import os
from flask import Flask, send_file, Response
import subprocess
import time
from datetime import datetime, timedelta
from flask_cors import CORS
import mysql.connector
from mysql.connector import Error
from mysql.connector import pooling
from configparser import ConfigParser

# 读取INI配置文件
config = ConfigParser()
config.read('../config/settings.ini')

# 从配置文件中获取数据库连接信息
hostname = config.get('MySQL', 'MYSQL_HOST')
port = config.get('MySQL', 'MYSQL_PORT')
username = config.get('MySQL', 'MYSQL_USER')
password = config.get('MySQL', 'MYSQL_PASSWORD')
database = config.get('MySQL', 'MYSQL_DATABASE')

# 创建数据库连接池
pool = pooling.MySQLConnectionPool(
    pool_name="my_pool",
    pool_size=5,
    host=hostname,
    port=port,
    user=username,
    password=password,
    database=database
)


# 使用 str() 函数将 timedelta 对象转换为可序列化的形式
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, timedelta):
            return str(obj)
        return super().default(obj)


app = Flask(__name__)
CORS(app)  # 允许跨域请求
# app.json_encoder = CustomJSONEncoder

config = ConfigParser()


# 运行 regression
@app.route('/api/run_edp_regression', methods=['GET'])
def run_regression():
    # 定义文件路径和文件名
    file_path = '../edp_fix_client/initiator/edp_regression_test/edp_regression_application.py'

    start_time = datetime.now()  # 记录开始时间

    try:
        result = subprocess.run(['python3', file_path], capture_output=True, text=True, timeout=1800)
        output = result.stdout.strip() if result.stdout else result.stderr.strip()
        success = True

    except subprocess.CalledProcessError as e:
        output = e.stderr.strip()
        success = False

    except subprocess.TimeoutExpired:
        output = "Execution time out"
        success = False

    end_time = datetime.now()  # 记录结束时间
    execution_time = end_time - start_time  # 计算执行时间

    response = {
        'status': success,
        'output': output,
        'start_time': start_time.strftime("%Y-%m-%d %H:%M:%S"),
        'execution_time': str(execution_time),
        'end_time': end_time.strftime("%Y-%m-%d %H:%M:%S"),
        'type': 1
    }
    conn = pool.get_connection()
    cursor = conn.cursor()

    # 构建插入SQL语句
    sql = "INSERT INTO regression (status, title, start_date, end_date, type) VALUES (%s, %s, %s, %s, %s)"
    values = (response['status'], "test", response['start_time'], end_time, int(response['type']))
    try:
        # 执行插入操作
        cursor.execute(sql, values)
        conn.commit()

    except Exception as e:
        print("Error while inserting into the database:", e)

    finally:
        # 关闭游标和连接
        cursor.close()
        conn.close()

    json_response = json.dumps(response)
    return Response(json_response, mimetype='application/json')


# 下载 edp_report.log
@app.route('/api/download_edp_logs', methods=['GET'])
def download_log_file():
    file_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + \
                '/edp_fix_client/initiator/edp_regression_test/logs/edp_report.log'
    return send_file(file_path, as_attachment=True)


# 下载 edp_report.xlsx
@app.route('/api/download_edp_reports', methods=['GET'])
def download_report_file():
    file_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + \
                '/edp_fix_client/initiator/edp_regression_test/report/edp_report.xlsx'
    return send_file(file_path, as_attachment=True)


# 预览edp_report.log
@app.route('/api/preview_edp_log')
def preview_edp_logs():
    log_file_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + \
                '/edp_fix_client/initiator/edp_regression_test/logs/edp_report.log'
    return send_file(log_file_path)


# 预览edp_report.xlsx
@app.route('/api/preview_edp_report')
def preview_edp_report():
    xlsx_file_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + \
                '/edp_fix_client/initiator/edp_regression_test/report/edp_report.xlsx'
    return send_file(xlsx_file_path, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                     as_attachment=False)


if __name__ == '__main__':
    app.run()