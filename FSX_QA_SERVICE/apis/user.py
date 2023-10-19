# -*- coding:utf-8 -*-
import json
import bcrypt
import pymysql
from datetime import datetime
from flask import request, jsonify
from flask_cors import CORS
from flask import Blueprint
from FSX_QA_SERVICE.apis.Application import global_connection_pool, process_row
from flask_jwt_extended import jwt_required, create_access_token
# from flask_jwt_extended import JWTManager, get_jwt_identity

app_user = Blueprint("app_user", __name__)
# 允许跨域请求
CORS(app_user, supports_credentials=True)


@app_user.route("/api/user/user_list", methods=['GET'])
@jwt_required()
# 用户列表+查询
def search_user():
    # 从数据库池获取数据库连接
    connection = global_connection_pool.connection()
    # 创建游标
    cursor = connection.cursor()
    # 获取数据
    data = request.args.to_dict()
    # 初始化sql语句
    sql = ""
    # 判空处理
    if data is not None and data != '':
        if "name" in data and data["name"] != "":
            sql += " AND `name` LIKE '%{}%'".format(data["name"])
        elif "name" in data and data["name"] == '':
            sql = ""
        else:
            # 如果没有传参，则返回所有isDelete = 0 的数据
            try:
                # 统计数据总数
                cursor.execute('SELECT COUNT(*) as total_count FROM `qa_admin`.`UsersRecord` '
                               'WHERE `isDelete` = 0 ')
                total_count = cursor.fetchone()
                # 查询数据
                cursor.execute("SELECT * FROM `qa_admin`.UsersRecord WHERE `isDelete` = 0 ")
                search_result = cursor.fetchall()
                if search_result:
                    data = [process_row(row) for row in search_result]
                    response = {
                        "total_count": total_count,
                        "data": data
                    }
                    return jsonify(response), 200

                else:
                    return jsonify({'message': 'Data does not exist'})
            except pymysql.Error as e:
                return jsonify({'message': 'Search error', 'error': str(e)})

            finally:
                cursor.close()
                connection.close()

        sql += ' ORDER BY `id` DESC;'
        try:
            # 统计数据总数
            cursor.execute('SELECT COUNT(*) as total_count FROM `qa_admin`.`UsersRecord` '
                           'WHERE `isDelete` = 0 {}'.format(sql))
            total_count = cursor.fetchone()
            # 查询数据
            cursor.execute("SELECT * FROM `qa_admin`.UsersRecord WHERE `isDelete` = 0 {}".format(sql))
            search_result = cursor.fetchall()
            # 如果查询结果存在，则循环将数据循环输出
            if search_result:
                data = [process_row(row) for row in search_result]
                response = {
                    "total_count": total_count,
                    "data": data
                }
                return jsonify(response), 200
            else:
                return jsonify({'message': 'Data does not exist'})

        except pymysql.Error as e:
            return jsonify({'message': 'Search error', 'error': str(e)})

        finally:
            cursor.close()
            connection.close()
    else:
        return jsonify({"Error": "Invalid request data"}), 400


@app_user.route("/api/user/create-user", methods=['POST'])
@jwt_required()
# 新增用户
def create_user():
    # 从数据库池获取数据库连接
    connection = global_connection_pool.connection()
    # 创建游标
    cursor = connection.cursor()
    # 获取数据
    data = request.get_json()
    try:
        # 数据判空处理
        if 'name' in data and data['name'] != '':
            name = data.get('name')
        else:
            return jsonify({'message': 'name cannot be empty'}), 400
        if 'email' in data and data['email'] != '':
            email = data.get('email')
        else:
            return jsonify({'message': 'email cannot be empty'}), 400
        if 'password' in data and data['password'] != '':
            password = data.get('password')
        else:
            return jsonify({'message': 'password cannot be empty'}), 400

        # 执行SQL
        sql = "SELECT * FROM `UsersRecord` WHERE `email` = %s "
        cursor.execute(sql, email)
        # 获取查询结果
        result = cursor.fetchone()

        if result:
            return jsonify({'message': 'User exists '}), 400
        else:
            created_time = datetime.now()
            create_user_sql = \
                "INSERT INTO `UsersRecord` (`name`, `email`, `password`, `createdTime`, `role`) " \
                "VALUES (%s, %s, %s, %s, %s)"
            cursor.execute(create_user_sql, (name, email, password, created_time, data["role"]))
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


@app_user.route("/api/user/delete-user", methods=['POST'])
# 删除用户（软删除）
def delete_user():
    # 从数据库池获取数据库连接
    connection = global_connection_pool.connection()
    # 创建游标
    cursor = connection.cursor()
    data = request.get_data()
    js_data = json.loads(data)
    if "id" in js_data and js_data['id'] != "":
        user_id = js_data['id']
        # 执行SQL
        sql = "SELECT * FROM `UsersRecord` WHERE `id` = %s "
        cursor.execute(sql, user_id)
        # 获取查询结果
        result = cursor.fetchone()
        try:
            if result:
                delete_user_sql = "UPDATE `UsersRecord` SET `isDelete`= TRUE  WHERE `id` = %s"
                cursor.execute(delete_user_sql, user_id)
                connection.commit()
                return jsonify({'message': 'Delete user succeed'})
            else:
                return jsonify({'message': 'User does not exist'})
        except pymysql.Error as e:
            return jsonify({'message': 'Delete user fail', 'error': str(e)})
        finally:
            cursor.close()
            connection.close()
    else:
        return jsonify({"error": "User does not exist"})


@app_user.route("/api/user/user-info", methods=["GET"])
@jwt_required()
# 用户详情
def user_details():
    data = request.args.to_dict()
    if data is not None and data != "":
        if "id" in data and data["id"] != "":
            user_id = data["id"]
            connection = global_connection_pool.connection()
            cursor = connection.cursor()
            try:
                sql = "SELECT * FROM `qa_admin`.UsersRecord WHERE `id` = {}".format(user_id)
                cursor.execute(sql)
                result = cursor.fetchone()
                if result:
                    details = process_row(result)
                    response = {
                        'data': details
                    }
                    return jsonify(response), 200
            except pymysql.Error as e:
                return jsonify({'message': 'Description Failed to view user details', 'error': str(e)})
            finally:
                cursor.close()
                connection.close()
        else:
            return jsonify({"error": "The user id is not in the data"})
    else:
        return jsonify({"error": "The received user id is empty"})


@app_user.route("/api/user/update-user", methods=["POST"])
@jwt_required()
# 修改用户（只支持修改用户名字和邮箱）
def update_user():
    connection = global_connection_pool.connection()
    cursor = connection.cursor()
    data = request.get_data()
    if data is not None and data != "":
        js_data = json.loads(data)
        sql = ""
        if "id" in js_data and js_data["id"] != "":
            user_id = js_data["id"]
            # 验证用户id与传参是否匹配
            cursor.execute("SELECT * FROM `qa_admin`.UsersRecord WHERE `id` = {}".format(user_id))
            result = cursor.fetchone()
            if result:
                if "name" in js_data and js_data["name"] != "":
                    sql += " `name` = '{}',".format(js_data["name"])
                if "email" in js_data and js_data["email"] != "":
                    sql += " `email` = '{}',".format(js_data["email"])
                # if "password" in js_data and js_data["password"] != "":
                #     sql += " `password` = {},".format(js_data["password"])
                try:
                    update_time = datetime.now()
                    sql += " `updateTime` = '{}'".format(update_time)
                    cursor.execute("UPDATE `qa_admin`.`UsersRecord` SET {} WHERE `id` = {};".format(sql, user_id))
                    connection.commit()
                    return jsonify({'message': 'Update user details succeed'}), 200
                except pymysql.Error as e:
                    return jsonify({'message': 'Update user fail', 'error': str(e)})
                finally:
                    cursor.close()
                    connection.close()
            else:
                return jsonify({"error": "The user could not be found"}), 404
    else:
        return jsonify({"error": "The user id is empty"}), 500
