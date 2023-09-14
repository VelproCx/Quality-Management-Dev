import json
import os

from flask import Flask, send_file, Response
import subprocess
import time
from datetime import datetime, timedelta
from flask_cors import CORS


# 使用 str() 函数将 timedelta 对象转换为可序列化的形式
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, timedelta):
            return str(obj)
        return super().default(obj)


app = Flask(__name__)
CORS(app)  # 允许跨域请求
# app.json_encoder = CustomJSONEncoder


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
        'success': success,
        'output': output,
        'execution_time': str(execution_time),
        'end_time': end_time.strftime("%Y-%m-%d %H:%M:%S")
    }
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


@app.route('/api/preview_edp_log')
def preview_edp_logs():
    log_file_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + \
                '/edp_fix_client/initiator/edp_regression_test/logs/edp_report.log'
    return send_file(log_file_path)


@app.route('/api/preview_edp_report')
def preview_edp_report():
    xlsx_file_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + \
                '/edp_fix_client/initiator/edp_regression_test/report/edp_report.xlsx'
    return send_file(xlsx_file_path, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                     as_attachment=False)


if __name__ == '__main__':
    app.run()