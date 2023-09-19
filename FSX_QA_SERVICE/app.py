from flask import Flask, render_template, request, redirect, jsonify
from common import Mysql_configs
import cryptography
import pymysql



app = Flask(__name__, template_folder='/Users/zhenghuaimao/Desktop/FSX-DEV-QA/templates')


# 创建数据库连接池
db_config = {
    "host": Mysql_configs.MYSQL_HOST,
    "port": Mysql_configs.MYSQL_PORT,
    "user": Mysql_configs.MYSQL_USER,
    "password": Mysql_configs.MYSQL_PASSWORD,
    "database": Mysql_configs.MYSQL_DATABASE,
    "charset": 'utf8mb4'
}


# 设计主页路由
@app.route('/')
def index():
    return render_template('index.html')


# 设计登录路由
@app.route('/login', methods=['POST', 'GET'])
def login():
    if request.method == 'POST':
        # 处理登录逻辑
        username = request.form['username']
        password = request.form['password']
        # 从连接池创建连接对象
        conn = pymysql.connect(**db_config)
        cursor = conn.cursor()

        try:
            # 执行查询用户的SQL语句
            query = "SELECT * FROM users WHERE username = %s AND password = %s"
            cursor.execute(query, (username, password))

            # 获取查询结果
            result = cursor.fetchone()

            if result:
                # 登录成功
                return jsonify({'message': '登录成功'})
            else:
                # 登录失败
                return jsonify({'message': '用户名或密码错误'})

        except Exception as e:
            # 处理异常
            return jsonify({'message': '登录失败', 'error': str(e)})

        finally:
            # 关闭游标和连接
            cursor.close()
            conn.close()

        # 验证成功，重定向到管理后台
        return redirect('/admin')
    else:
        # 显示登录表单
        return render_template('login.html')


# 设计管理后台路由
@app.route('/admin')
def admin():
    # 在管理后台中执行必要的逻辑
    # 例如从数据库中获取数据并传递给模板进行渲染

    return render_template('admin.html')


if __name__ == '__main__':
    app.run(debug=True)