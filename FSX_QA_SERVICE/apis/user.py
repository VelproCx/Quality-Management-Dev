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
    # 从数据库池获取数据库连接
    connection = global_connection_pool.connection()
    # 创建游标
    cursor = connection.cursor()
    # 获取post请求body数据
    data = request.get_data()
    try:
        # 将字符串转换成json
        js_data = json.loads(data)
        username = js_data['username']
        password = js_data['password']
        if username == '' or password == '':
            return jsonify({'message': 'The account password cannot be empty'})
        else:
            # 执行查询用户语句
            sql = "SELECT * FROM `users` WHERE `username` = %s AND `password` = %s"
            cursor.execute(sql, (username, password))
            # 获取查询结果
            result = cursor.fetchone()
            if result:
                return jsonify({'message': 'login succeed Wellcome to QA_admin'}), 200
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
    # 从数据库池获取数据库连接
    connection = global_connection_pool.connection()
    # 创建游标
    cursor = connection.cursor()
    # 获取数据
    data = request.get_json()
    try:
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        # 校验字段是否为空
        if not username or not email or not password:
            return jsonify({'message': 'Required fields cannot be empty'}), 400
        # 执行SQL
        sql = "SELECT * FROM `users` WHERE `username` = %s "
        cursor.execute(sql, username)
        # 获取查询结果
        result = cursor.fetchone()

        if result:
            return jsonify({'message': 'User exists '}), 400
        else:
            create_user_sql = "INSERT INTO `users` (`username`, `email`, `password`) VALUES (%s, %s, %s)"
            cursor.execute(create_user_sql, (username, email, password))
            connection.commit()
            return jsonify({'message': 'Create user succeed'})
    except pymysql.Error as e:
        return jsonify({'message': 'Create user fail', 'error': str(e)}), 500
    except json.JSONDecodeError as je:
        return jsonify({'decoding error': str(je)})

    finally:
        # 关闭游标和连接
        cursor.close()
        connection.close()

@app_user.route("/api/user/delete", methods=['DELETE'])
def delete_user():
    data = request.get_data()
    js_data = json.loads(data)
    username = js_data['username']
    # 从数据库池获取数据库连接
    connection = global_connection_pool.connection()
    # 创建游标
    cursor = connection.cursor()
    # 执行SQL
    sql = "SELECT * FROM `users` WHERE `username` = %s "
    cursor.execute(sql, username)
    # 获取查询结果
    result = cursor.fetchone()
    try:
        if result:
            delete_user_sql = "DELETE FROM `users` WHERE `username` = %s"
            cursor.execute(delete_user_sql, username)
            connection.commit()
            return jsonify({'message': 'Delete user succeed'})
        else:
            return jsonify({'message': 'User does not exist'})
    except pymysql.Error as e:
        return jsonify({'message': 'Delete user fail', 'error': str(e)})

    finally:
        cursor.close()
        connection.close()

@app_user.route("/api/user/search", methods=['GET'])
def search_user():
    data = request.get_data()
    js_data = json.loads(data)
    sql = ' SELECT `id`, `username`, `user_status` FROM `users` WHERE `user_status` = 1 '

    if 'id' in js_data and js_data['id'] != '':
        sql += 'AND `id` = "{}"'.format(js_data['id'])
    if 'username' in js_data and js_data['username'] != '':
        sql += 'AND `username` = "{}"'.format(js_data['username'])
    if 'email' in js_data and js_data['email'] != '':
        sql += 'AND `email` = "{}"'.format(js_data['email'])
    # 从数据库池获取数据库连接
    connection = global_connection_pool.connection()
    # 创建游标
    cursor = connection.cursor()
    cursor.execute(sql)
    result = cursor.fetchone()
    try:
        if result:
            # 将结果转换为 JSON 格式
            json_result = json.dumps(result)
            return json_result

        else:
            return jsonify({'message': 'Data does not exist'})

    except pymysql.Error as e:
        return jsonify({'message': 'Search error', 'error': str(e)})

    finally:
        cursor.close()
        connection.close()


