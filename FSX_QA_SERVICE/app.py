# -*- coding:utf-8 -*-
from flask import Flask
from apis.Application import app_application
from apis.user import app_user
from apis.run_edp_performance import app_run_enp_performance
from flask_cors import CORS
from flask import render_template

# 调试使用，正式部署请将template_folder="/Users/zhenghuaimao/Desktop/FSX-DEV-QA/templates"去掉
app = Flask(__name__, template_folder="/Users/zhenghuaimao/Desktop/FSX-DEV-QA/templates")
# 允许跨域请求
CORS(app, supports_credentials=True)

app.register_blueprint(app_application)
app.register_blueprint(app_user)
app.register_blueprint(app_run_enp_performance)

@app.route('/')
def index():
    return render_template("index.html")

if __name__ == '__main__':
    app.run(debug=True)