# -*- coding:utf-8 -*-
import secrets
from flask import Flask, request, jsonify
from apis.run_edp_regression import app_run_edp_regression
from apis.Application import app_application
from apis.user import app_user
from apis.run_edp_performance import app_run_edp_performance
from apis.run_edp_full_stock import app_run_edp_full_stock
from apis.edp_test_case import app_edp_test_case
from flask_cors import CORS
from flask import render_template
from flask_jwt_extended import JWTManager, jwt_required, create_access_token
from FSX_QA_SERVICE.apis.Application import global_connection_pool, process_row

app = Flask(__name__)

# 配置 CORS，允许来自指定 origin 的跨域请求
CORS(app, resources={r"/api/*": {"origins": "http://localhost:5173"}})

# 生成一个包含 32 个随机十六进制字符的字符串作为 JWT 密钥
jwt_secret_key = secrets.token_hex(32)
app.config['JWT_SECRET_KEY'] = jwt_secret_key
jwt = JWTManager(app)
# 允许跨域请求
CORS(app, supports_credentials=True)

app.register_blueprint(app_application)
app.register_blueprint(app_user)
app.register_blueprint(app_run_edp_performance)
app.register_blueprint(app_run_edp_full_stock)
app.register_blueprint(app_run_edp_regression)
app.register_blueprint(app_edp_test_case)


@app.route('/')
def index():
    return render_template("index.html")


# 用于存储已失效的令牌，可以存储在数据库或缓存中
blacklisted_tokens = set()


@app.route("/api/user/login", methods=['POST'])
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


@app.route("/api/user/logout", methods=['POST'])
@jwt_required()
def logout():
    token = request.headers.get('Authorization')
    if token:
        # current_user = get_jwt_identity()
        # 将令牌加入黑名单
        blacklisted_tokens.add(token)
        return jsonify({'message': 'Logged out successfully'}), 200
    else:
        return jsonify({"error": "logout failed. Missing Authorization Header"}), 401


# 每个接口调用前校验该方法
@app.before_request
def check_blacklist():
    # 获取当前请求的端点（即路由）
    endpoint = request.endpoint
    # 忽略登录接口的检查
    if endpoint == 'login':
        return
    token = request.headers.get('Authorization')
    if request.method != 'OPTIONS':
        if token:
            if token in blacklisted_tokens:
                return jsonify({'message': 'Invalid token'}), 401
        else:
            return jsonify({'error': 'Invalid request data'}), 400
    else:
        return


if __name__ == '__main__':
    app.run(debug=True, port=8080)
