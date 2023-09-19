# -*- coding:utf-8 -*-
from flask import request, redirect, jsonify
from FSX_QA_SERVICE.common import Mysql_configs
import pymysql
from flask import Blueprint
import json

app_user = Blueprint("app_user", __name__)

# 创建数据库连接池
db_config = {
    "host": Mysql_configs.MYSQL_HOST,
    "port": Mysql_configs.MYSQL_PORT,
    "user": Mysql_configs.MYSQL_USER,
    "password": Mysql_configs.MYSQL_PASSWORD,
    "database": Mysql_configs.MYSQL_DATABASE,
    "charset": 'utf8mb4'
}

conn = pymysql.connect(**db_config)
cursor = conn.cursor()

@app_user.route("/api/user/login", methods=['POST'])
def login():
    # 获取post请求body数据
    data = request.get_data()
    # 将字符串转换成json
    js_data = json.loads(data)
    username = js_data['username']
    password = js_data['password']

    try:
        # 执行查询用户语句
        sql = "SELECT * FROM users WHERE username = %s AND password = %s"
        cursor.execute(sql, (username, password))

        # 获取查询结果
        result = cursor.fetchone()

        if result:
            return jsonify({'message': 'login succeed Wellcome to QA_test_admin'}), 200
        else:
            return jsonify({'message': 'login failed Please Check the user name or password'}), 401

    except Exception as e:
        # 处理异常
        return jsonify({'message': 'login failed !!', 'error': str(e)})

    finally:
        # 关闭游标和连接
        cursor.close()
        conn.close()

    # 验证成功，重定向到管理后台
    # return redirect('/admin')

@app_user.route("/api/user/create", methods=['POST'])
def create_user():
    # 获取数据
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    # 校验字段
    if not username or not email or not password:
        return jsonify({'message': 'Required fields cannot be empty'}), 400

    # 执行sql
    sql = "SELECT * FROM users WHERE username = %s "
    cursor.execute(sql, username)
    result = cursor.fetchone()
    try:
        if result:
            return jsonify({'message': 'User exists '}), 400
        else:
            create_user_sql = "INSERT INTO users (username, email, password) VALUES (%s, %s, %s)"
            cursor.execute(create_user_sql, (username, email, password))
            conn.commit()
            return jsonify({'message': 'create user succeed'})
    except pymysql.Error as e:
        return jsonify({'message': 'Create user fail', 'error': str(e)}), 500

    finally:
        # 关闭游标和连接
        cursor.close()
        conn.close()

# @app_user.route("/api/user/delete", methods=['DEL'])
# def delete_user