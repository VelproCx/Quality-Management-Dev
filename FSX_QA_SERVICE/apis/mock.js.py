import random
import string
from flask_cors import CORS
from flask import Flask, jsonify

app = Flask(__name__)

# 启用 CORS 支持，允许来自 localhost:5173 的请求
CORS(app, resources={r"/api/*": {"origins": "http://localhost:5173"}})


@app.route('/api/list/policy', methods=['GET'])
def queryPolicyList():
    data_list = [
        {
            'id': ''.join(random.choices(string.ascii_uppercase + string.ascii_lowercase + '-', k=8)) + ''.join(
                random.choices(string.digits, k=1)),
            'taskName': ''.join(random.choices(string.ascii_uppercase, k=random.randint(4, 8))),
            'handler': random.choice(['xiang.chen', 'huaimao.zheng', 'taotao.zhang', 'miaolan.huang']),
            'status': random.choice(['planning', 'progressing', 'completed']),
            'createdTime': '2023-09-07 12:34:56',  # 请替换为实际的日期时间
        }
        for _ in range(55)
    ]

    data = {
        'data': data_list,
        'status': 'ok',
        'msg': '请求成功',
        'code': 20000
    }

    return jsonify(data)


@app.route('/api/edp_regression_list', methods=['GET'])
def queryEdpRegressionList():
    data_list = [
        {
            'createdTime': '2023-09-07 12:34:56',  # 请替换为实际的日期时间
            'source': random.choice(['xiang.chen', 'huaimao.zheng', 'taotao.zhang', 'miaolan.huang']),
            'status': random.choice(['progressing', 'completed']),
        }
        for _ in range(10)
    ]

    data = {
        'data': data_list,
        'status': 'ok',
        'msg': '请求成功',
        'code': 20000
    }

    return jsonify(data)


@app.route('/api/edp_regression_list/create_regression_task', methods=['POST'])
def createEdpRegressionTask():
    data = {
        'status': 'ok',
        'msg': '创建成功',
        'code': 20000
    }

    return jsonify(data)


if __name__ == "__main__":
    app.run(debug=True, port=8080)
