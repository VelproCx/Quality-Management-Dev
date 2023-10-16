import json
import random
import string
import time

from flask_cors import CORS
from flask import Flask, jsonify, request

app = Flask(__name__)

# 启用 CORS 支持，允许来自 localhost:5173 的请求
CORS(app, resources={r"/api/*": {"origins": "http://localhost:5173"}})


def get_task_id():
    taskid = 1
    # 获取当前时间并且进行格式转换
    t = int(time.time())
    str1 = ''.join([str(i) for i in random.sample(range(0, 9), 2)])
    return str(t) + str1 + str(taskid).zfill(2)


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


@app.route('/api/edp_performance_list', methods=['GET'])
def queryEdpPerformanceList():
    data_list = [
        {
            'createdTime': '2023-09-07 12:34:56',  # 请替换为实际的日期时间
            'source': random.choice(['xiang.chen', 'huaimao.zheng', 'taotao.zhang', 'miaolan.huang']),
            'status': random.choice(['progressing', 'completed', 'error']),
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


@app.route('/api/performance_list/create_performance_task', methods=['POST'])
def createEdpPerformanceTask():
    # 获取参数并将其转换为json格式
    recdata = request.get_data()
    datas = json.loads(recdata)
    print(datas)
    data = {
        'status': 'ok',
        'msg': '创建成功',
        'code': 20000
    }

    return jsonify(data)


@app.route('/api/edp_smoke_list', methods=['GET'])
def querySmokeList():
    data_list = [
        {
            'taskId': ''.join('1241252362362632'),
            'symbol': random.choice(['7203.EDP', '6758.EDP', '1311.EDP', '5110.EDP']),
            'ordType': random.choice(['Market', 'Limit']),
            'side': random.choice(['Buy', 'Sell']),
            'source': random.choice(['xiang.chen', 'huaimao.zheng', 'taotao.zhang', 'miaolan.huang']),
            'status': random.choice(['new', 'rejected', 'expired', 'filled', 'canceled', 'cancelRejected']),
            'createdTime': '2023-09-07 12:34:56',  # 请替换为实际的日期时间
        }
        # for _ in range(1)
    ]

    data = {
        'data': data_list,
        'status': 'ok',
        'msg': '请求成功',
        'code': 20000
    }

    return jsonify(data)


@app.route('/api/smoke_list/view_edp_smoke', methods=['GET'])
def ViewSmokeDetail():
    data_list = [
        {
            'taskId': ''.join('1241252362362632'),
            'symbol': random.choice(['7203.EDP', '6758.EDP', '1311.EDP', '5110.EDP']),
            'ordType': random.choice(['Market', 'Limit']),
            'side': random.choice(['Buy', 'Sell']),
            'source': random.choice(['xiang.chen', 'huaimao.zheng', 'taotao.zhang', 'miaolan.huang']),
            'status': random.choice(['new', 'rejected', 'expired', 'filled', 'canceled', 'cancelRejected']),
            'createdTime': '2023-09-07 12:34:56',  # 请替换为实际的日期时间
            "account": "RUAT_EDP_ACCOUNT_6",
            "market": "EDP",
            "actionType": "NewAck",
            "comment": "EDP_Market_NewAck",
            "orderQty": 100,
            "ordType": "2",
            "side": "2",
            "price": 851,
            "symbol": "2927",
            "timeInForce": "3",
            "crossingPriceType": "EDP",
            "rule80A": "P",
            "cashMargin": "1",
            "marginTransactionType": "0",
            "minQty": 0,
            "orderClassification": "3",
            "selfTradePreventionId": "0",
        }
        # for _ in range(1)
    ]

    data = {
        'data': data_list,
    }

    return jsonify(data)


@app.route('/api/user/search', methods=['GET'])
def queryUserList():
    data_list = [
        {
            'role': random.choice(['Admin', 'Operation', 'Market']),
            'email': random.choice(
                ['xiang.chen@farsightedyu.com', 'zhenghuaimao@farsightedyu.com', 'zhangtaotao@farsightedyu.com']),
            'name': random.choice(['xiang.chen', 'huaimao.zheng', 'taotao.zhang', 'miaolan.huang']),
            'id': i,
            'createdTime': '2023-10-16 12:34:56',  # 请替换为实际的日期时间
        }
        for i, _ in enumerate(range(10))
    ]

    data = {
        'data': data_list,
    }

    return jsonify(data)


@app.route('/api/user/create', methods=['POST'])
def createUser():
    data_list = [
        {
            'role': random.choice(['Admin', 'Operation', 'Market']),
            'email': random.choice(
                ['xiang.chen@farsightedyu.com', 'zhenghuaimao@farsightedyu.com', 'zhangtaotao@farsightedyu.com']),
            'name': random.choice(['xiang.chen', 'huaimao.zheng', 'taotao.zhang', 'miaolan.huang']),
            'id': random.choice(['xiang.chen', 'huaimao.zheng', 'taotao.zhang', 'miaolan.huang']),
            'createdTime': '2023-10-16 12:34:56',  # 请替换为实际的日期时间
        }
        for _ in range(10)
    ]

    data = {
        'data': data_list,
    }

    return jsonify(data)


@app.route('/api/user/delete', methods=['POST'])
def deleteUser():
    data = request.get_data()
    print(data)

    data = {
        'status': 'ok',
        'msg': '请求成功',
        'code': 20000
    }

    return jsonify(data)


@app.route('/api/user/update', methods=['POST'])
def updateUser():
    data = request.get_data()
    print(data)

    data_list = [
        {
            'role': random.choice(['Admin', 'Operation', 'Market']),
            'email': random.choice(
                ['xiang.chen@farsightedyu.com', 'zhenghuaimao@farsightedyu.com', 'zhangtaotao@farsightedyu.com']),
            'name': random.choice(['xiang.chen', 'huaimao.zheng', 'taotao.zhang', 'miaolan.huang']),
            'id': random.choice(['1']),
            'createdTime': '2023-10-16 12:34:56',  # 请替换为实际的日期时间
        }
    ]

    data = {
        'data': data_list,
    }

    return jsonify(data)



@app.route('/api/user/user-detail', methods=['POST'])
def getUserDetail():
    data = request.get_data()
    print(data)

    data_list = [
        {
            'role': random.choice(['Admin', 'Operation', 'Market']),
            'email': random.choice(
                ['xiang.chen@farsightedyu.com', 'zhenghuaimao@farsightedyu.com', 'zhangtaotao@farsightedyu.com']),
            'name': random.choice(['xiang.chen', 'huaimao.zheng', 'taotao.zhang', 'miaolan.huang']),
            'id': random.choice(['1']),
            'createdTime': '2023-10-16 12:34:56',  # 请替换为实际的日期时间
        }
    ]

    data = {
        'data': data_list,
    }

    return jsonify(data)

if __name__ == "__main__":
    app.run(debug=True, port=8080)
