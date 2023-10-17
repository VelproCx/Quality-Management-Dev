# -*- coding:utf-8 -*-
from flask import Flask
import asyncio

from apis.run_edp_regression import app_run_edp_regression
from apis.Application import app_application
from apis.user import app_user
from apis.run_edp_performance import app_run_edp_performance
from apis.run_edp_full_stock import app_run_edp_full_stock
from flask_cors import CORS
from flask import render_template
from flask_jwt_extended import JWTManager, jwt_required, create_access_token

# 调试使用，正式部署请将template_folder="/Users/zhenghuaimao/Desktop/FSX-DEV-QA/templates"去掉
app = Flask(__name__, template_folder="/Users/zhenghuaimao/Desktop/FSX-DEV-QA/templates")
app.config['JWT_SECRET_KEY'] = 'your_secret_key'
jwt = JWTManager(app)
# 允许跨域请求
CORS(app, supports_credentials=True)

app.register_blueprint(app_application)
app.register_blueprint(app_user)
app.register_blueprint(app_run_edp_performance)
app.register_blueprint(app_run_edp_full_stock)
app.register_blueprint(app_run_edp_regression)


@app.route('/')
def index():
    return render_template("index.html")


if __name__ == '__main__':
    app.run(debug=True, port=8080)
