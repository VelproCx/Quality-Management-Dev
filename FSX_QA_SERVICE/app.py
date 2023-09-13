from flask import Flask, render_template, request, redirect
from dbutils.pooled_db import PooledDB
import pymysql
from common import Mysql_configs
from flask_sqlalchemy import SQLAlchemy


app = Flask(__name__, template_folder='/Users/zhenghuaimao/Desktop/FSX-DEV-QA/templates')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'

# 创建数据库连接池
pool = PooledDB(
    creator=pymysql,
    maxconnections=10,  # 最大连接数
    mincached=2,        # 初始化时的最小空闲连接数
    maxcached=5,        # 最大空闲连接数
    host=Mysql_configs.MYSQL_HOST,
    post=Mysql_configs.MYSQL_PORT,
    user=Mysql_configs.MYSQL_USER,
    password=Mysql_configs.MYSQL_PASSWORD,
    database=Mysql_configs.MYSQL_DATABASE,
    charset='utf8mb4'
)

# 设计主页路由
@app.route('/')
def index():
    return render_template('index.html')


# 设计登录路由
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # 处理登录逻辑
        username = request.form['username']
        password = request.form['password']
        # 从连接池创建连接对象
        connection = pool.connection()

        try:
            with connection.cursor() as cursor:
                # 查询数据库中的用户信息
                sql = "SELECT * FROM `users` WHERE `username`=%s AND `password`=%s"

                cursor.execte(sql, (username,password))
                result = cursor.fetchone()

                if result:
                    # 验证成功，重定向到管理后台
                    return redirect('/admin')
                else:
                    # 验证失败，返回登录页面
                    return render_template('login.heml')
        finally:
            connection.close()

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