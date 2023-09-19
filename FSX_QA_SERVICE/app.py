# -*- coding:utf-8 -*-
from flask import Flask
from apis.user import app_user
from flask_cors import CORS
from FSX_QA_SERVICE.common import Mysql_configs
from flask import make_response, render_template

app = Flask(__name__, template_folder="/Users/zhenghuaimao/Desktop/FSX-DEV-QA/templates")
CORS(app, supports_credentials=True)

app.register_blueprint(app_user)

@app.route('/')
def index():
    return render_template("index.html")

if __name__ == '__main__':
    app.run(debug=True)