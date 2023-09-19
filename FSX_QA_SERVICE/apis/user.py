# -*- coding:utf-8 -*-
import json
import pymysql
from flask import request, jsonify
from flask_cors import CORS
from flask import Blueprint
from FSX_QA_SERVICE.apis.Application import global_connection_pool

app_user = Blueprint("app_user", __name__)
# 允许跨域请求
CORS(app_user, supports_credentials=True)

@app_user.route("/api/user/login", methods=['POST'])
def login():
    # 获取post请求body数据
    data = request.get_data()
    # 将字符串转换成json
    js_data = json.loads(data)
    username = js_data['username']
    password = js_data['password']

    # 从数据库池获取数据库连接
    connection = global_connection_pool.connection()

    # 创建游标
    cursor = connection.cursor()

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
        connection.close()

    # 验证成功，重定向到管理后台
    # return redirect('/admin')

@app_user.route("/api/user/create", methods=['POST'])
def create_user():
    # 获取数据
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    # 从数据库池获取数据库连接
    connection = global_connection_pool.connection()

    # 创建游标
    cursor = connection.cursor()

    # 校验字段是否为空
    if not username or not email or not password:
        return jsonify({'message': 'Required fields cannot be empty'}), 400

    # 执行SQL
    sql = "SELECT * FROM users WHERE username = %s "
    cursor.execute(sql, username)

    # 获取查询结果
    result = cursor.fetchone()

    try:
        if result:
            return jsonify({'message': 'User exists '}), 400
        else:
            create_user_sql = "INSERT INTO users (username, email, password) VALUES (%s, %s, %s)"
            cursor.execute(create_user_sql, (username, email, password))
            connection.commit()
            return jsonify({'message': 'create user succeed'})
    except pymysql.Error as e:
        return jsonify({'message': 'Create user fail', 'error': str(e)}), 500

    finally:
        # 关闭游标和连接
        cursor.close()
        connection.close()

# @app_user.route("/api/user/delete", methods=['DEL'])
# def delete_user