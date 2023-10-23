# -*- coding:utf-8 -*-
# Application.py
import json
import pymysql
import pymysql.cursors
from datetime import datetime
from dbutils.pooled_db import PooledDB
from FSX_QA_SERVICE.config import Mysql_configs
from flask import request, jsonify
from flask_cors import CORS
from flask import Blueprint, Flask
from flask_jwt_extended import JWTManager, jwt_required, create_access_token

app = Flask(__name__)
app.config['JWT_SECRET_KEY'] = 'your_secret_key'
jwt = JWTManager(app)

app_application = Blueprint('app_application', __name__)


# 使用数据库连接池的方式链接数据库
pool = PooledDB(
    creator=pymysql,
    host=Mysql_configs.MYSQL_HOST,
    port=Mysql_configs.MYSQL_PORT,
    user=Mysql_configs.MYSQL_USER,
    password=Mysql_configs.MYSQL_PASSWORD,
    database=Mysql_configs.MYSQL_DATABASE,
    charset='utf8mb4',
    mincached=2,
    maxcached=5,
    cursorclass=pymysql.cursors.DictCursor
)

# 设置全局变量，用于共享数据库连接池
global_connection_pool = pool


def process_row(row):
    # 将 datetime 对象 row['CreateTime'] 格式化为 %Y-%m-%d %H:%M:%S 的时间字符串
    formatted_create_time = row['createTime'].strftime("%Y-%m-%d %H:%M:%S")
    return {
        "id": row["id"],
        "name": row["name"],
        "status": row["status"],
        "email": row["email"],
        "createTime": formatted_create_time,
        "isDelete": row["isDelete"],
        "role": row["role"],
        "access_token": row["token"]
    }


def get_token_by_email(email):
    connection = global_connection_pool.connection()
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT * FROM qa_admin.UsersRecord WHERE `email` = {};".format(email))
        result = cursor.fetchone()
        data = process_row(result)
        return data["token"]
    except pymysql.Error as e:
        return jsonify({"error": str(e)})
    finally:
        cursor.close()
        connection.close()
