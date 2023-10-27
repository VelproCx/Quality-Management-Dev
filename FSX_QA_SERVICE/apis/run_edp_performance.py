# -*- coding:utf-8 -*-
import os
import time
import json
import random
import shutil
import tempfile
import threading
import subprocess
import tarfile
from flask_cors import CORS
from datetime import datetime, timedelta
from flask_jwt_extended import jwt_required
from FSX_QA_SERVICE.apis.Application import global_connection_pool
from flask import send_file, request, jsonify, Blueprint, make_response
app_run_edp_performance = Blueprint("run_edp_performance", __name__)
CORS(app_run_edp_performance, supports_credentials=True)


# 生成TaskId
def get_task_id():
    taskid = 1
    # 获取当前时间并且进行格式转换
    t = int(time.time())
    str1 = ''.join([str(i) for i in random.sample(range(0, 9), 2)])
    return str(t) + str1 + str(taskid).zfill(2)


# 避免重复代码
def process_row(row):
    # 将 datetime 对象 row['CreateTime'] 格式化为 %Y-%m-%d %H:%M:%S 的时间字符串
    formatted_create_time = row['createTime'].strftime("%Y-%m-%d %H:%M:%S")
    return {
        "createTime": formatted_create_time,
        "source": row["createUser"],
        "status": row["status"],
        "taskId": row["taskId"],
        "output": row["output"]
    }


def tst(shell_commands, task_id):
    try:
        # 将shell_commands用Popen方法执行
        process = subprocess.Popen(shell_commands, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        # 创建两个空数组用来存放shell命令的执行结果（status）还有执行输出（outputs）
        statuses = []
        outputs = []
        process.wait()
        status = process.returncode
        outputs_stdout, outputs_stderr = process.communicate()
        statuses.append(status)
        # 将outputs_stdout转换成
        outputs.append((outputs_stdout, outputs_stderr))
        opts = outputs_stdout.decode('utf-8')
        stderr = outputs_stderr.decode('utf-8')
        output = opts

        if 'Successful Logon to session' in opts and 'logout' in opts:
            result = "completed"

        elif stderr == '':
            result = "error"
            output = "connect error, please check the script"

        else:
            result = "error"
            output = stderr.split('Error:', 1)[-1].strip()

    except Exception as e:
        result = "error"
        response = {
            "result": result,
            "output": str(e)
        }
        return response

    except subprocess.CalledProcessError as e:
        output = e.stderr.strip()
        result = "error"
        response = {
            "result": result,
            "error": str(e),
            "output": output
        }
        return response
        # 修改成return之后没有调试

    except subprocess.TimeoutExpired:
        output = "Execution time out"
        result = "error"
        response = {
            "result": result,
            "error": "TimeoutExpired",
            "output": output
        }
        return response
        # 修改成return之后没有调试

    update_performance_record(task_id, result, output)


# 向PerformanceRecord插入数据
def insert_performance_record(task_id, creator, status):
    # 从数据库池获取数据库连接
    connection = global_connection_pool.connection()
    # 创建游标
    cursor = connection.cursor()

    # 构建SQL语句
    sql = "INSERT INTO `qa_admin`.PerformanceRecord (`taskId`, `type`, `createUser`, `status`) " \
          "VALUES (%s, %s, %s, %s)"
    values = (task_id, 1, creator, status)

    try:
        cursor.execute(sql, values)
        connection.commit()
    except Exception as e:
        print("Error while inserting into the database:", e)
        return jsonify({"error": str(e)})
    finally:
        cursor.close()
        connection.close()


def update_performance_record(task_id, status, output):
    # 从数据库池获取数据库连接
    connection = global_connection_pool.connection()
    # 创建游标
    cursor = connection.cursor()
    # 构建sql语句
    sql = "UPDATE `qa_admin`.PerformanceRecord SET `status` = %s , `output` = %s WHERE `taskId` = %s"
    values = (status, output, task_id)
    try:
        cursor.execute(sql, values)
        connection.commit()
    except Exception as e:
        print("Error while updating the database:", e)
        raise
    finally:
        cursor.close()
        connection.close()


@app_run_edp_performance.route('/api/edp_performance_list/run_edp_performance', methods=['POST'])
@jwt_required()
def run_edp_performance():
    # 从请求体中获取数据
    data = request.get_data()
    if not data or data == b'':
        return jsonify({"error": "Invalid request data"}), 400
    # 数据转换
    datas = json.loads(data)
    task_id = get_task_id()
    creator = datas["source"]
    create_time = datetime.now().isoformat()

    # 创建一个空数组用于存放shell命令
    commands = []
    # 循环从请求体中将shell命令读取出来
    for command in datas["commands"]:
        shell = command["value"] + " --TaskId {}".format(task_id) + " &\n" + "sleep 1\n"
        commands.append(shell)
    # 格式化数组中的shell命令
    shell_commands = ''.join(commands)

    thread = threading.Thread(target=tst, args=(shell_commands, task_id))
    thread.start()

    result = "progressing"

    response = {
        'creator': creator,
        'taskId': task_id,
        'status': result,
        'createTime': create_time,
        'type': 1
    }
    # 将压力测试任务创建成功返回给接口，然后继续等待压力测试脚本执行结果
    insert_performance_record(task_id, creator, result)
    return jsonify(response), 200


@app_run_edp_performance.route('/api/edp_performance_list/download_performance_logs', methods=['POST'])
@jwt_required()
def download_performance_log_file():
    data = request.get_data()
    # 判断传参是否为空
    if data is None:
        return jsonify({"Error": "Invalid file path"}), 400

    # 创建一个空数组用于存放所有日志的路径
    file_paths = []
    datas = json.loads(data)
    taskid = datas["taskId"]
    # 日志地址
    log_path = "edp_fix_client/initiator/edp_performance_test/logs"
    # 遍历日志目录下的所有文件
    for filename in os.listdir(log_path):
        if taskid in filename:
            log_filepath = os.path.join(log_path, filename)
            file_paths.append(log_filepath)
    if not file_paths:
        return jsonify({"Error": "The file is not found"}), 404
    # 创建临时目录用于存放压缩文件
    temp_dir = tempfile.mkdtemp()

    # 记录打包时间
    tar_time = datetime.now()
    tar_name = "performance_logs_{}.zip".format(tar_time.strftime("%Y-%m-%d_%H-%M-%S"))
    tar_file_path = os.path.join(temp_dir, tar_name)
    # 创建一个 Tar 文件
    with tarfile.open(tar_file_path, 'w') as tar:
        # 将每个日志文件添加到 Tar 文件中
        for log_file in file_paths:
            file_path = os.path.join(log_file)
            arc_name = os.path.basename(log_file)  # 获取文件的基本名称
            tar.add(file_path, arcname=arc_name)

    # 创建响应对象
    response = make_response(send_file(tar_file_path, as_attachment=True))

    # 设置 Content-Disposition 头部字段
    response.headers['Content-Disposition'] = 'attachment; filename={}'.format(tar_name)

    # 删除临时目录及其内容
    shutil.rmtree(temp_dir)

    return response, 200


@app_run_edp_performance.route('/api/edp_performance_list', methods=['GET'])
@jwt_required()
def edp_performance_list():
    connection = global_connection_pool.connection()
    cursor = connection.cursor()
    data = request.args.to_dict()
    if data is not None and data != '':
        sql = ""
        if "source" in data and data["source"] != "":
            sql += " AND `createUser` = '{}'".format(data["source"])
        if "status" in data and data["status"] != "":
            sql += " AND `status` = '{}'".format(data["status"])
        if "startTime" in data and data["startTime"] != "":
            start_time = datetime.strptime(data["startTime"], "%Y-%m-%d")
            sql += " AND `createTime` >= '{}' ".format(start_time)
        if "endTime" in data and data["endTime"] != "":
            end_time = (datetime.strptime(data["endTime"], "%Y-%m-%d")) + timedelta(days=1)
            sql += " AND `createTime` < '{}'".format(end_time)
        if "taskId" in data and data["taskId"] != "":
            sql += " AND `taskId` LIKE '%{}%'".format(data["taskId"])
        sql = sql + ' ORDER BY `createTime` DESC'
        try:
            # 统计数据总数
            cursor.execute('SELECT COUNT(*) as total_count FROM `qa_admin`.PerformanceRecord '
                           'WHERE `type` = 1 {}'.format(sql))
            total_count = cursor.fetchone()["total_count"]
            # 查询数据
            cursor.execute("SELECT * FROM `qa_admin`.PerformanceRecord WHERE `type` = 1 {}".format(sql))
            search_result = cursor.fetchall()
            data = [process_row(row) for row in search_result]
            response = {
                "total_count": total_count,
                "data": data
            }
            return jsonify(response), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

        finally:
            cursor.close()
            connection.close()
    else:
        try:
            # 统计数据总数
            count_sql = "SELECT COUNT(*) as total_count FROM `qa_admin`.PerformanceRecord WHERE `type` = 1;"
            cursor.execute(count_sql)
            total_count = cursor.fetchone()["total_count"]
            # 查询数据
            data_sql = "SELECT `createTime`, `status`, `createUser`, `taskId` " \
                       "FROM `qa_admin`.PerformanceRecord " \
                       "WHERE `type` = 1;"
            cursor.execute(data_sql)
            rows = cursor.fetchall()
            data = []
            for row in rows:
                data.append(
                    {
                        "taskId": row["taskId"],
                        "createTime": row["createDate"],
                        "source": row["createUser"],
                        "status": row["status"]
                    }
                )
            response = {
                'total_count': total_count,
                'data': data
            }
            return jsonify(response), 200
        except Exception as e:
            return jsonify({"Error": str(e)}), 500
        finally:
            cursor.close()
            connection.close()
