# -*- coding:utf-8 -*-
import os
import json
import time
import pymysql
from flask_cors import CORS
from datetime import datetime
from FSX_QA_SERVICE.apis.Application import global_connection_pool
from flask_jwt_extended import jwt_required
from flask import send_file, Response, request, jsonify, Blueprint, make_response
app_edp_test_case = Blueprint("edp_test_case", __name__)
CORS(app_edp_test_case, supports_credentials=True)


def process_row(row):
    # 将 datetime 对象 row['CreateTime'] 格式化为 %Y-%m-%d %H:%M:%S 的时间字符串
    formatted_create_time = row['updateTime'].strftime("%Y-%m-%d %H:%M:%S")
    return {
        "source": row["source"],
        "caseName": row["caseName"],
        "updateTime": formatted_create_time
    }


# 读取文件夹中所有文件
def get_case_list(path):
    file_list = []
    for file_name in os.listdir(path):
        if file_name.endswith(".json"):
            file_list.append(file_name)
    return file_list


def insert_test_case_record(case_file):
    connect = global_connection_pool.connection()
    cursor = connect.cursor()
    try:
        # 查询出数据库中所有已记录的case
        db_case_file = []
        update_time = datetime.now()
        select = "SELECT `caseName` From `qa_admin`.TesecaseRecord"
        cursor.execute(select)
        rows = cursor.fetchall()
        for row in rows:
            case_name = row["caseName"]
            db_case_file.append(case_name)
        # 循环判断testcase中的case文件是否已录入数据库
        if case_file == db_case_file:
            pass
        else:
            # 循环将未记录的数据库存入数据库
            for cf in case_file:
                if cf not in db_case_file:
                    insert = "INSERT INTO `qa_admin`.TesecaseRecord (`caseName`, `updateTime`) " \
                             "VALUES (%s, %s)"
                    values = (cf, update_time)

                    cursor.execute(insert, values)
                    connect.commit()

    except Exception as e:
        print("Error while inserting into the database:", e)
        return jsonify({"error": str(e)})

    finally:
        cursor.close()
        connect.close()


@app_edp_test_case.route('/api/edp_test_case', methods=['GET'])
@jwt_required()
def edp_test_case_list():
    case_path = "edp_fix_client/testcases"
    # 获取testcase中的所有case文件
    testcase = get_case_list(case_path)
    # 检查testcase中文件是否已经写入db，如果没有，则先写入db
    insert_test_case_record(testcase)
    connect = global_connection_pool.connection()
    cursor = connect.cursor()
    try:
        slt = "SELECT * FROM `qa_admin`.TesecaseRecord"
        cursor.execute(slt)
        result = cursor.fetchall()
        data = [process_row(row) for row in result]
        response = {
            "data": data
        }
        return jsonify(response), 200
    except Exception as e:
        print("Error while inserting into the database:", e)
        return jsonify({"error": str(e)})
    finally:
        cursor.close()
        connect.close()


@app_edp_test_case.route('/api/edp_test_case/view', methods=['GET'])
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


@app_edp_test_case.route('/api/edp_test_case/edit', methods=['POST'])
@jwt_required()
def edit_edp_case():
    connection = global_connection_pool.connection()
    cursor = connection.cursor()
    try:
        datas = request.get_json()
        file_name = datas["file_name"]
        file_path = "edp_fix_client/testcases/{}.json".format(file_name)
        if os.path.exists(file_path):
            # 如果文件存在，将数据保存到文件中
            data = datas["data"]
            with open(file_path, "w") as file:
                json.dump(data, file)
            update_time = datetime.now()
            update = "UPDATE `qa_admin`.TesecaseRecord SET `updateTime` = %s" \
                     "WHERE `caseName` = %s"
            value = (update_time, file_name)
            cursor.execute(update, value)
            connection.commit()
            return jsonify({"msg": "Test case save successfully"}), 200
        else:
            return jsonify({"msg": "File does not exist"}), 404
    except IOError:
        return jsonify({"error": "Internal Server Error"}), 500
    finally:
        cursor.close()
        connection.close()


@app_edp_test_case.route('/api/edp_test_case/delete', methods=["POST"])
@jwt_required()
def delete_case():
    connection = global_connection_pool.connection()
    cursor = connection.cursor()
    datas = request.get_data()
    data = json.loads(datas)
    if "file_name" in data and data["file_name"] != "":
        file_name = data["file_name"]
        try:
            sql = "SELECT * FROM `qa_admin`.TesecaseRecord WHERE caseName = '{}.json'".format(file_name)
            cursor.execute(sql)
            result = cursor.fetchall()
            if result:
                delete_sql = "UPDATE 'qa_admin'.TesecaseRecord SET `isDelete`= TRUE " \
                             "WHERE `caseName` = '{}.json'".format(file_name)
                cursor.execute(delete_sql)
                connection.commit()
                return jsonify({"msg": "Delete case succeed"}), 200
        except pymysql.Error as e:
            return jsonify({'msg': 'Delete case fail', 'error': str(e)}), 500
        finally:
            cursor.close()
            connection.close()
    else:
        return jsonify({"error": "Case does not exist"}), 400


