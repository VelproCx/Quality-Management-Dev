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
from flask_jwt_extended import jwt_required
from flask import send_file, Response, request, jsonify, Blueprint, make_response, stream_with_context
app_edp_test_case = Blueprint("edp_test_case", __name__)
CORS(app_edp_test_case, supports_credentials=True)


# 读取文件夹中所有文件
def get_case_file_list(path):
    file_list = []
    for file_name in os.listdir(path):
        file_path = os.path.join(path, file_name)
        if os.path.isfile(file_path):
            file_list.append(file_path)
    return file_list


@app_edp_test_case.route('/api/edp_test_case', methods=['POST'])
# @jwt_required()
def edp_test_case_list():
    case_path = "edp_fix_client/testcases"
    testcase = get_case_file_list(case_path)
    return testcase


@app_edp_test_case.route('/api/edp_test_case/read_write_case', methods=['GET'])
@jwt_required()
def view_edp_case():
    data = request.args.to_dict()
    if data is None or data == '':
        return jsonify({"Error": "Invalid request data"}), 400
    file_name = data["filename"]
    case_file_path = 'edp_fix_client/testcases/{}.json'.format(file_name)
    if os.path.exists(case_file_path):
        # 读取json文件
        with open(case_file_path, "r") as file:
            file_content = file.read()
            data = json.loads(file_content)
        # 获取testCase列表
        test_cases = data["testCase"]
        # 统计Symbol数量
        symbol_count = len([test_case["Symbol"] for test_case in test_cases])
        case_count = "case_count: {}".format(symbol_count)
        response = []
        for test_case in test_cases:
            result = {
                "case_content": test_case
            }
            response.append(result)

        return jsonify(case_count, response), 200

    else:
        return jsonify({"Error": "The file is not found"}), 404


@app_edp_test_case.route('/api/edp_test_case/read_write_case', methods=['POST'])
@jwt_required()
def edit_edp_case():
    try:
        datas = request.get_json()
        file_name = datas["file_name"]
        file_path = "edp_fix_client/testcases/{}.json".format(file_name)
        if os.path.exists(file_path):
            # 如果文件存在，将数据保存到文件中
            data = datas["data"]
            with open(file_path, "w") as file:
                json.dump(data, file)
            return jsonify({"msg": "Test case save successfully"}), 200
        else:
            # 如果文件不存在，则询问是否新增文件
            result = datas["operation"]
            if result == "Yes":
                with open(file_path, "a") as file:
                    data = datas["data"]
                    file.write(data)
                return jsonify({"msg": "New case file created and data added"}), 200
            elif result == "No":
                return jsonify({"msg": "No new case file created"}), 200
            else:
                return jsonify({"msg": "The file does not exist and the modification has been abandoned"}), 200

    except IOError:
        return jsonify({"error": "Internal Server Error"}), 500


