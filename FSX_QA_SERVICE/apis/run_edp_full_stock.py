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
from flasgger import swag_from
from datetime import datetime
from FSX_QA_SERVICE.apis.Application import global_connection_pool
from flask import send_file, Response, request, jsonify, Blueprint, make_response

app_run_edp_full_stock = Blueprint("run_edp_full_stock", __name__)
CORS(app_run_edp_full_stock, supports_credentials=True)

taskId = 0


def process_row(row):
    return {
        "createdTime": row["start_date"],
        "source": row["createUser"],
        "status": row["status"]
    }


@app_run_edp_full_stock.route("/api/full_stock_list", methods=['GET'])
def edp_full_stock_list():
    connection = global_connection_pool.connection()
    cursor = connection.cursor()
    try:
        # 统计数据总数
        count_sql = "SELECT COUNT(*) as total_count FROM `qa_admin`.performance WHERE `type` = 1;"
        cursor.execute(count_sql)
        total_count = cursor.fetchone()["total_count"]

        # 查询数据
        sql = "SELECT `start_date`, `status`, `createUser` FROM `qa_admin`.`fullstock` WHERE `type` = 1;"
        cursor.execute(sql)
        rows = cursor.fetchall()
        data = [process_row(row) for row in rows]

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

