# -*- coding:utf-8 -*-
import json
import pymysql
from datetime import datetime
from flask import request, jsonify
from flask_cors import CORS
from flask import Blueprint, Flask
from FSX_QA_SERVICE.apis.Application import global_connection_pool, process_row
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity

app = Flask(__name__)
app.config['JWT_SECRET_KEY'] = 'your_secret_key'
jwt = JWTManager(app)

app_user = Blueprint("app_user", __name__)
# 允许跨域请求
CORS(app_user, supports_credentials=True)

# 用于存储已失效的令牌，可以存储在数据库或缓存中
blacklisted_tokens = set()


@app_user.route("/api/user/login", methods=['POST'])
def login():
    # 从数据库池获取数据库连接
    connection = global_connection_pool.connection()
    # 创建游标
    cursor = connection.cursor()
    # 获取post请求body数据
    data = request.get_json()
    try:
        email = data['email']
        password = data['password']
        if email == '' or password == '':
            return jsonify({'message': 'The account password cannot be empty'}), 404
        else:
            # 执行查询用户语句
            sql = "SELECT * FROM `qa_admin`.`UsersRecord` WHERE `email` = %s AND `password` = %s"
            cursor.execute(sql, (email, password))
            # 获取查询结果
            result = cursor.fetchone()
            if result:
                if result["isDelete"]:
                    return jsonify({'message': "User does not exist"})
                else:
                    if result['status'] == 0:
                        return jsonify({'message': 'User not activated. Please contact the administrator'}), 404
                    if result['status'] == 1:
                        user_datas = process_row(result)
                        identity = user_datas["id"]
                        # 在登录成功时生成token
                        token_value = create_access_token(identity=identity)
                        # 拼接token
                        token = "Bearer {}".format(token_value)
                        # 拼接sql用户更新用户token
                        update_token_sql = "UPDATE qa_admin.UsersRecord SET token = %s WHERE id = %s"
                        # 执行sql并提交
                        cursor.execute(update_token_sql, (token_value, identity))
                        connection.commit()
                        # 拼接sql查询出最新的用户数据并前端返回
                        sql = "SELECT * FROM `qa_admin`.UsersRecord WHERE id = %s"
                        cursor.execute(sql, identity)
                        userdata = cursor.fetchone()

                        response = process_row(userdata)
                        response = jsonify(response)
                        response.headers['Authorization'] = token
                        return response, 200
                    if result['status'] == 2:
                        return jsonify({'message': 'The user has been frozen. Please contact the administrator'}), 404
            else:
                return jsonify({'message': 'login failed Please Check the user name or password'}), 401
    except Exception as e:
        # 处理异常
        return jsonify({'message': 'login failed !!', 'error': str(e)})

    finally:
        # 关闭游标和连接
        cursor.close()
        connection.close()


@app_user.route("/api/user/logout", methods=['POST'])
@jwt_required()
def logout():
    token = request.headers.get('Authorization')
    if token:
        current_user = get_jwt_identity()
        # 将令牌加入黑名单
        blacklisted_tokens.add(token)
        return jsonify({'message': 'Logged out successfully'}), 200
    else:
        return jsonify({"error": "logout failed. Missing Authorization Header"}), 401


@app_user.before_request
def check_blacklist():
    # 获取当前请求的端点（即路由）
    endpoint = request.endpoint
    # 忽略登录接口的检查
    if endpoint == 'app_user.login':
        return
    token = request.headers.get('Authorization')
    if token:
        if token in blacklisted_tokens:
            return jsonify({'message': 'Invalid token'}), 401
    else:
        return jsonify({'error': 'Invalid request data'}), 400


@app_user.route("/api/user/user_list", methods=['GET'])
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
        return jsonify({"Error": "Invalid file path"}), 400


@app_user.route("/api/user/create-user", methods=['POST'])
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


@app_user.route("/api/user/info", methods=["GET"])
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
