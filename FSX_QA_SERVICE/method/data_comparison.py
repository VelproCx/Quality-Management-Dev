import json
import logging

logfix = logging.getLogger('logfix')


def compare_field_values(json_file1, json_file2, field_name):
    resList = []
    with open(json_file1, 'r') as f1, open(json_file2, 'r') as f2:
        data1 = json.load(f1)
        data2 = json.load(f2)
    records1 = data1['testCase']
    records2 = data2
    # 判断记录数量是否相同
    if len(records1) == len(records2):
        for i, (record1, record2) in enumerate(zip(records1, records2), 1):
            if record1[field_name] == ['8'] and record2[field_name] == ['8']:
                # 逐组比较字段值并输出结果
                if record1["errorCode"] in record2["errorCode"]:
                    resList.append('success')
                else:
                    logfix.info(f"第 {i} 条数据的指定字段值不相同" + "," + "exc_errorCode:" + str(
                        record1['errorCode']) + ' , ' + "recv_errorCode:" + str(record2['errorCode']))
                    resList.append('failed')
                    logfix.info(
                        "Except:" + str(record1[field_name]) + " ，" + "ordStatus: " + str(record2[field_name]))
            elif record1[field_name] == record2[field_name]:
                resList.append("success")
            else:
                logfix.info(f"第 {i} 组数据的指定字段值不相同" + "," + "clordId:" + str(record2['clordId']))
                resList.append('failed')
                logfix.info("Except:" + str(record1[field_name]) + " ，" + "ordStatus: " + str(record2[field_name]))
    else:
        logfix.info("两个文件记录数量不一致，预期数量：{}，实际数量：{}！".format(len(records1), len(records2)))
    return resList
