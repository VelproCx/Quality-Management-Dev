# -*- coding:utf-8 -*-
# Application.py
from flask import Blueprint
from dbutils.pooled_db import PooledDB
from flask import request
import pymysql.cursors
import json
from FSX_QA_SERVICE.config import Mysql_configs

# 使用数据库连接池的方式链接数据库
pool = PooledDB(
    creator=pymysql,
    host=Mysql_configs.MYSQL_HOST,
    port=Mysql_configs.MYSQL_PORT,
    user=Mysql_configs.MYSQL_USER,
    password=Mysql_configs.MYSQL_PASSWORD,
    database=Mysql_configs.MYSQL_DATABASE,
    charset='utf8mb4',
    mincached=2,
    maxcached=5,
    cursorclass=pymysql.cursors.DictCursor
)

# 设置全局变量，用于共享数据库连接池
global_connection_pool = pool

app_application = Blueprint('app_application', __name__)

# @app_application.route("/api/application/search", methods=['POST'])
# def searchBykey():
#     body = request.get_data()
#     body = json.load(body)
#
#     # 基础语句
#     sql = ""
#
#     # 获取pageSize和currentPage
#     pageSize = 10 if body["pageSize"] is None else body["pageSize"]
#     currentPage = 1 if body["currentPage"] is None else body["currentPage"]
