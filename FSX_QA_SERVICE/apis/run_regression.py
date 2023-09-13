import os

from flask import Flask, jsonify, send_file
import subprocess

app = Flask(__name__)


@app.route('/api/run_regression', methods=['GET'])
def run_regression():
    # 定义文件路径和文件名
    file_path = '../edp_regression_test'
    file_name = 'edp_regression_application.py'

    try:
        # 构建命令和参数列表
        command = ['python3', file_path + '/' + file_name]

        # 执行命令并获取输出
        output = subprocess.check_output(command, universal_newlines=True)

        # 返回执行结果
        return jsonify({'output': output})
    except subprocess.CalledProcessError as e:
        # 处理命令执行出错的情况
        return jsonify({'error': str(e)}), 500


@app.route('/api/download_logs', methods=['GET'])
def download_log_file():
    file_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + \
                '/edp_regression_test/logs/edp_report.log'
    return send_file(file_path, as_attachment=True)


@app.route('/api/download_reports', methods=['GET'])
def download_report_file():
    file_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + \
                '/edp_regression_test/report/edp_report.xlsx'
    return send_file(file_path, as_attachment=True)


if __name__ == '__main__':
    app.run()