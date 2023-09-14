#!/usr/bin/python
# -*- coding: utf8 -*-
"""FIX Application"""
import difflib
import random
import sys

import quickfix as fix
import time
import logging
from datetime import datetime, timedelta
from model.logger import setup_logger
import json
import math
# import sys
# sys.path.append("../method")
from importlib.machinery import SourceFileLoader
import os

# 获取当前所在目录绝对路径
current_path = os.path.abspath(os.path.dirname(__file__))
# 将当前目录的路径，获取上级目录的绝对路径
Parent_path = os.path.abspath(os.path.join(current_path, "../../method"))
# 获取上级目录中一个文件的路径
generation_path = os.path.join(Parent_path, "file_generation.py")
#获取data_comparison
data_comparison_path = os.path.join(Parent_path, "data_comparison.py")


__SOH__ = chr(1)

from openpyxl import load_workbook

# report
setup_logger('logfix', 'logs/rex_report.log')
logfix = logging.getLogger('logfix')


class Application(fix.Application):  # 定义一个类并继承‘fix.Application’类，主要用于处理收到的消息和事件
    execID = 0
    ORDERS_DICT = []
    PTF_CANCEL_LIST = []
    Success = 0
    Fail = 0
    Total = 0
    REX_PROP_BPS_BUY = 0.0022
    REX_PROP_BPS_SELL = 0.0022
    Result = []
    ReceveRes = []
    order_new = 0
    order_expired = 0
    order_accepted = 0
    order_rejected = 0
    order_filled = 0
    order_partially_filled = 0

    def __init__(self):
        # 初始化sessionID = None
        super().__init__()
        self.sessionID = None

    def onCreate(self, sessionID):
        # 服务器启动时候调用此方法创建
        # 服务器启动时，读取配置文件中的【SESSION】部份，将读取到的sessionID传给self.sessionID,并打印出来
        self.sessionID = sessionID
        print("onCreate : Session ({})".format(sessionID.toString()))
        return

    def onLogon(self, sessionID):
        # "客户端登陆成功时候调用此方法"
        self.sessionID = sessionID
        print("Successful Logon to session '{}'.".format(sessionID.toString()))
        return

    def onLogout(self, sessionID):
        # 主要功能是在客户端断开连接时进行日志检查，将接收到的响应结果写入到文件中，
        # 并将响应结果与预期结果进行比较。比较结果将保存在self.Result属性中。
        # 然后，使用日志记录器logfix输出比较结果的统计信息，包括总数、成功数和失败数。
        # 在控制台上输出一个字符串，表示会话已经结束。最后，调用self.writeResExcel方法，将比较结果写入到Excel文件rex_report.xlsx中
        # "客户端断开连接时候调用此方法"
        self.logsCheck()
        json_data = json.dumps(self.ReceveRes)

        module_name = "compare_field_values"
        module_path = data_comparison_path
        # 导入具有完整文件路径的模块
        module1 = SourceFileLoader(module_name, module_path).load_module()
        # 将JSON数据写入文件中
        with open('logs/recv_data.json', 'w') as file:
            file.write(json_data)
        self.Result = module1.compare_field_values('../../testcases/REX_Functional_Test_Matrix.json',
                                                'logs/recv_data.json',
                                                'ordstatus')  # 为了比较ordstatus字段的值
        print("Session ({}) logout !".format(sessionID.toString()))

        ordstatus_list = []
        errorCode_list = []
        # 循环ReceveRes并将value添加到列表里
        for i in self.ReceveRes:
            ordstatus_list.append(str(i['ordstatus']))
            if 'errorCode' in i:
                errorCode_list.append(str(i['errorCode']))

            # ReceveRes 没有'errorCode'字段时,添加空字符串到列表里
            else:
                errorCode_list.append(" ")

        # report文件里写入字段
        self.writeResExcel('report/rex_report.xlsx', ordstatus_list, 2, 'J')
        self.writeResExcel('report/rex_report.xlsx', errorCode_list, 2, 'K')
        self.writeResExcel('report/rex_report.xlsx', self.Result, 2, 'L')
        return

    def toAdmin(self, message, sessionID):
        # 该方法的主要功能是将待发送的消息转换为字符串格式，并使用logfix日志记录器输出该消息。
        # 在输出消息之前，使用replace方法将消息中的特殊符号__SOH__替换为|，
        # 以确保消息的格式正确。最后，该方法使用return语句结束执行，并没有返回任何值。
        # 这是因为该方法主要是用于输出日志，而不需要返回结果
        # "发送会话消息时候调用此方法"
        msg = message.toString().replace(__SOH__, "|")  # 特殊符号转化
        logfix.info("(Core) S >> {}".format(msg))  # 日志记录器
        return

    def toApp(self, message, sessionID):
        # 这段代码是将发送的消息转换为字符串格式，便于后续处理。它首先使用toString()方法将收到的消息转换为字符串格式。
        # 由于FIX协议中使用ASCII码的SOH（Start of Header）作为分隔符，
        # 因此使用replace()方法将SOH替换为管道符号“|”，方便后续处理。将处理后的字符串赋给变量msg
        # "发送业务消息时候调用此方法"
        logfix.info("-------------------------------------------------------------------------------------------------")
        msgType = message.getHeader().getField(35)  # 从消息头（Header）中获取35号字段的值，35号字段表示消息类型。将这个值赋给变量msgType
        msg = message.toString().replace(__SOH__, "|")
        # 7.1 New Order Single
        if msgType == "D":
            orderQty = message.getField(38)  # 订单数量
            ordType = message.getField(40)  # 订单类型
            clOrdID = message.getField(11)  # 编号
            side = message.getField(54)  # 买卖
            symbol = message.getField(55)  # 证券代码
            transactTime = message.getField(60)  # 交易时间
            if (clOrdID, orderQty, ordType,
                side, symbol, transactTime,
                ) != "":
                logfix.info("(sendMsg) New Ack >> {}".format(msg))
                self.order_new += 1
            else:
                logfix.info("(sendMsg) New Ack >> {}".format(msg) + 'New Order Single FixMsg Error!')
        # 7.4 Order Cancel Request
        elif msgType == "F":
            clOrdID = message.getField(11)
            side = message.getField(54)
            symbol = message.getField(55)
            transactTime = message.getField(60)
            if (clOrdID, side, symbol, transactTime) != "":
                logfix.info("(sendMsg) Cancel Ack >> {}".format(msg))
            else:
                logfix.info("(sendMsg) Cancel Ack >> {}".format(msg) + 'Order Cancel Request FixMsg Error!')
        return

    def fromAdmin(self, message, sessionID):
        msg = message.toString().replace(__SOH__, "|")
        logfix.info("(Core) R << {}".format(msg))
        return

    def fromApp(self, message, sessionID):
        logfix.info("-------------------------------------------------------------------------------------------------")
        # "接收业务消息时调用此方法"
        msgType = message.getHeader().getField(35)

        if msgType == 'h':
            tradingSessionID = message.getField(336)
            tradSesMode = message.getField(339)
            tradSesStatus = message.getField(340)
            msg = message.toString().replace(__SOH__, "|")
            if (tradingSessionID, tradSesMode, tradSesStatus) != '':
                logfix.info("(recvMsg) Trading Session << {}".format(msg))
            else:
                logfix.info("(recvMsg) Trading Session Error")
        # Business Message Reject
        elif msgType == 'j':
            refSeqNum = message.getField(45)
            text = message.getField(58)
            refMsgType = message.getField(372)
            businessRejectRefID = message.getField(379)
            msg = message.toString().replace(__SOH__, "|")
            if (refSeqNum, text, refMsgType, businessRejectRefID) != '':
                logfix.info("(recvMsg) Business Message << {}".format(msg))
            else:
                logfix.info("(recvMsg) Business Message Error")
        else:
            clOrdID = message.getField(11)
            orderID = message.getField(37)
            ordStatus = message.getField(39)
            transactTime = message.getField(60)
            fsxTransactTime = message.getField(8169)

            if ordStatus == '4':
                symbol = message.getField(55)  # 使用getField方法获取消息中的55字段的值
                print(symbol)
                if symbol == '1311':  # 如果symbol字段的值为1311，则将clOrdID字段的值加1，并将其转换为字符串类型，赋值给变量new_clOrdID和clOrdID
                    new_clOrdID = int(clOrdID) + 1
                    clOrdID = str(new_clOrdID)

            # 模糊匹配方法，判断收到fix消息体中的clordId是否在列表中，true则更新status，false则新增一条数据
            # 设置匹配的阈值
            threshold = 1
            # 使用difflib模块的get_close_matches函数进行模糊匹配，在self.ReceveRes列表中查找与clOrdID最相似的元素，提取组成新的列表
            matches = difflib.get_close_matches(clOrdID, [item['clordId'] for item in self.ReceveRes], n=1,
                                                cutoff=threshold)  # n=1表示只返回一个匹配项，cutoff=threshold表示只返回匹配程度大于等于threshold的项
            # 如果有匹配结果
            if matches:
                matched_clordId = matches[0]
                # 拿到clordId去数组里循环比对
                for item in self.ReceveRes:
                    # 判断当前收到的消息体clordid是否在数组里
                    if item['clordId'] == matched_clordId:
                        # 更新该组数据的ordstatus
                        item['ordstatus'].append(str(ordStatus))
            else:
                if ordStatus != '8':
                    # 添加新的数据到数组中
                    self.ReceveRes.append({'clordId': clOrdID, 'ordstatus': [ordStatus]})

                else:
                    text = message.getField(58)
                    self.ReceveRes.append({'clordId': clOrdID, 'ordstatus': [ordStatus], 'errorCode': text})

            # 因CancelRej消息体与其他消息体共用字段少，为减少代码量，将msgType == '9'的消息体做单独处理
            if msgType != '9':
                # 消息体共用tag
                avgPx = message.getField(6)  # 平均价格
                CumQty = message.getField(14)  # 累计成交数量
                execID = message.getField(17)  # 执行编号
                execTransType = message.getField(20)  # 执行事务类型
                orderQty = message.getField(38)  # 订单数量
                ordType = message.getField(40)  # 订单类型
                rule80A = message.getField(47)  # 规则80A
                side = message.getField(54)  # 买卖
                symbol = message.getField(55)
                timeInForce = message.getField(59)
                clientID = message.getField(109)
                execType = message.getField(150)  # 执行类型
                leavesQty = message.getField(151)  # 剩余数量
                cashMargin = message.getField(544)
                crossingPriceType = message.getField(8164)  # 交叉价格类型
                marginTransactionType = message.getField(8214)
                if symbol == '5076':
                    self.PTF_CANCEL_LIST.append(message.getField(11))  # 添加订单号
                elif symbol == '1311' or symbol == '6954':
                    self.ORDERS_DICT = message.getField(11)  # 订单信息
                msg = message.toString().replace(__SOH__, "|")
                # 7.2 Execution Report – Order Accepted
                if ordStatus == "0":
                    execBroker = message.getField(76)  # 执行经济商
                    lastShares = message.getField(32)  # 最新成交量
                    lastPx = message.getField(31)  # 最新成交价
                    clOrdID = message.getField(11)
                    # 判断tag是否存在
                    if (
                            avgPx, clOrdID, CumQty, execID, execTransType, lastPx, lastShares, orderID, orderQty,
                            ordType,
                            rule80A,
                            side, symbol, timeInForce, transactTime, execBroker, clientID, execType, leavesQty,
                            cashMargin,
                            crossingPriceType, fsxTransactTime, marginTransactionType) != "":
                        logfix.info("(recvMsg) Order Accepted << {}".format(msg) + "ordStatus = " + str(ordStatus))
                        logfix.info("Result : Order Accepted ," + "ordStatus =" + ordStatus)
                        self.order_accepted += 1
                    else:
                        logfix.info("(recvMsg) Order Accepted << {}".format(msg) + 'Order Accepted FixMsg Error!')
                    if execType != ordStatus:  # 如果不相等，记录错误日志
                        logfix.info(
                            "(recvMsg) Order execType error,orderStatus = {},execType = {}".format(ordStatus, execType))
                # 7.3 Execution Report – Order Rejected
                elif ordStatus == "8":
                    text = message.getField(58)  # 附加信息
                    ordRejReason = message.getField(103)  # 拒单原因
                    lastShares = message.getField(32)  # 最新成交
                    lastPx = message.getField(31)  # 最新成价
                    clOrdID = message.getField(11)
                    # 判断tag是否存在
                    if (
                            avgPx, clOrdID, CumQty, execID, execTransType, lastPx, lastShares, orderID, orderQty,
                            ordType,
                            rule80A,
                            side, symbol, timeInForce, transactTime, clientID, execType, leavesQty, cashMargin,
                            crossingPriceType,
                            fsxTransactTime, marginTransactionType, text, ordRejReason) != "":
                        logfix.info("(recvMsg) Order Rej << {}".format(msg) + "RejRes = " + str(text))
                        self.order_rejected += 1
                    else:
                        logfix.info("(recvMsg) Order Rejected << {}".format(msg) + 'Order Rejected FixMsg Error!')
                    if execType != ordStatus:
                        logfix.info(
                            "(recvMsg) Order execType error,orderStatus = {},execType = {}".format(ordStatus, execType))
                # 7.6 Execution Report – Order Canceled
                elif ordStatus == "4":
                    origClOrdID = message.getField(41)
                    execBroker = message.getField(76)
                    clOrdID = message.getField(11)
                    # 判断tag是否存在
                    if (avgPx, clOrdID, CumQty, execID, execTransType, orderID, orderQty, ordType, rule80A,
                        side, symbol, timeInForce, transactTime, clientID, execType, leavesQty, cashMargin,
                        crossingPriceType,
                        fsxTransactTime, marginTransactionType, origClOrdID, execBroker) != "":
                        logfix.info("(recvMsg) Order Canceled << {}".format(msg) + "ordStatus = " + str(ordStatus))
                    else:
                        logfix.info("(recvMsg) Order Canceled << {}".format(msg) + 'Order Canceled FixMsg Error!')
                    if execType != ordStatus:
                        logfix.info(
                            "(recvMsg) Order execType error,orderStatus = {},execType = {}".format(ordStatus, execType))
                # 7.7 Execution Report – Trade
                elif ordStatus == "1" or ordStatus == "2":  # 部分成交
                    lastPx = float(message.getField(31))
                    lastShares = message.getField(32)
                    execBroker = message.getField(76)  # 执行经纪商
                    primaryLastPx = float(message.getField(8031))
                    routingDecisionTime = message.getField(8051)  # 通用时间
                    propExecPrice = message.getField(8165)
                    PropExecID = message.getField(8166)
                    clOrdID = message.getField(11)
                    # 公式计算期望值 FillPrice
                    adjustLastPxBuy = math.ceil(primaryLastPx * (1 + self.REX_PROP_BPS_BUY))
                    adjustLastPxSell = math.floor(primaryLastPx * (1 - self.REX_PROP_BPS_SELL))
                    # 判断tag是否存在
                    if (
                            avgPx, clOrdID, CumQty, execID, execTransType, lastPx, lastShares, orderID, orderQty,
                            ordType,
                            rule80A,
                            side, symbol, timeInForce, transactTime, execBroker, clientID, execType, leavesQty,
                            cashMargin,
                            crossingPriceType, fsxTransactTime, marginTransactionType, primaryLastPx,
                            routingDecisionTime,
                            propExecPrice, PropExecID) != "":
                        logfix.info(
                            "(recvMsg) Order Filled << {}".format(msg) + 'Side: ' + str(
                                side) + ',' + "Fill Price: " + str(
                                lastPx) + ',' + "AdjustLastPx Of Buy: " + str(
                                adjustLastPxBuy) + ',' + "AdjustLastPx Of Sell: " + str(
                                adjustLastPxSell) + ',' + "Order Type:" + str(ordType))
                        logfix.info("Result : Order Filled ," + "ordStatus =" + ordStatus)
                        if ordStatus == "1":
                            self.order_partially_filled += 1
                        else:
                            self.order_filled += 1
                    else:
                        logfix.info("(recvMsg) Order Filled << {}".format(msg) + "Order Trade FixMsg Error!")
                    if execType != ordStatus:
                        logfix.info(
                            "(recvMsg) Order execType error,orderStatus = {},execType = {}".format(ordStatus, execType))
                        # Fill Price Check
                    if ordType == '1':  # 部分成交
                        if side == "1":
                            adjustLastPx = math.ceil(primaryLastPx * (1 + self.REX_PROP_BPS_BUY))
                            # 期望值与获取的fillPrice进行比对
                            if adjustLastPx == lastPx:
                                return True
                            else:
                                logfix.info(
                                    'Market Price is not matching,' + 'clOrdID：' + clOrdID + ',' + 'symbol：' + symbol + ',' + 'adjustLastPx：' + str(
                                        adjustLastPx) + ',' + 'lastPx:' + str(lastPx))
                        elif side == "2":
                            adjustLastPx = math.floor(primaryLastPx * (1 - self.REX_PROP_BPS_SELL))
                            # 期望值与获取的fillPrice进行比对
                            if adjustLastPx == lastPx:
                                return True
                            else:
                                logfix.info(
                                    'Market Price is not matching,' + 'clOrdID：' + clOrdID + ',' + 'symbol：' + symbol + ',' + 'adjustLastPx：' + str(
                                        adjustLastPx) + ',' + 'lastPx:' + str(lastPx))
                #  7.8 Execution Report – End of Day Expired
                elif ordStatus == "C":  # 过期订单
                    text = message.getField(58)
                    execBroker = message.getField(76)
                    origClOrdID = message.getField(41)
                    clOrdID = message.getField(11)
                    # 判断tag是否存在
                    if (avgPx, clOrdID, CumQty, execID, execTransType, orderID, orderQty, ordType, rule80A,
                        side, symbol, timeInForce, transactTime, execBroker, clientID, execType, leavesQty, cashMargin,
                        crossingPriceType, fsxTransactTime, marginTransactionType, execBroker, origClOrdID, text) != "":
                        logfix.info("(recvMsg) Order Expired << {}".format(msg) + "ExpireRes = " + str(text))
                        logfix.info("Result : Order Expired ," + "ordStatus =" + ordStatus)
                        self.order_expired += 1
                    else:
                        logfix.info("(recvMsg) Order Expired << {}".format(msg) + "Order Expired FixMsg Error!")
                    if execType != ordStatus:
                        logfix.info(
                            "(recvMsg) Order execType error,orderStatus = {},execType = {}".format(ordStatus, execType))
            else:
                origClOrdID = message.getField(41)
                text = message.getField(58)
                cxlRejReason = message.getField(102)
                cxlRejResponseTo = message.getField(434)
                clOrdID = message.getField(11)
                msg = message.toString().replace(__SOH__, "|")
                # 判断tag是否存在
                if (clOrdID, orderID, transactTime, fsxTransactTime, origClOrdID, text,
                    cxlRejReason, cxlRejResponseTo) != "":
                    logfix.info("(recvMsg) Order Canceled << {}".format(msg) + "ordStatus = " + str(ordStatus))
                else:
                    logfix.info("(recvMsg) Order Canceled << {}".format(msg) + 'Order Canceled FixMsg Error!')

            self.onMessage(message, sessionID)
        return

    def onMessage(self, message, sessionID):
        """Processing application message here"""
        pass
        # 数据比对的方法

    # 在掉出登陆时调用logscheck方法，判断是否有这些错误打印，
    def logsCheck(self):
        response = ['ps:若列表存在failed数据，请查看report.log文件']
        self.writeResExcel('report/rex_report.xlsx', response, 2, 'M')
        with open('logs/rex_report.log', 'r') as f:
            content = f.read()
        if 'Market Price is not matching' in content:
            logfix.info('Market Price is NG')
            response = ['Market Price is NG']
            self.writeResExcel('report/rex_report.xlsx', response, 5, 'M')
        else:
            logfix.info('Market Price is OK')
            response = ['Market Price is OK']
            self.writeResExcel('report/rex_report.xlsx', response, 3, 'M')
        if 'FixMsg Error' in content:
            logfix.info('FixMsg is NG')
            response = ['FixMsg is NG']
            self.writeResExcel('report/rex_report.xlsx', response, 6, 'M')
        else:
            logfix.info('FixMsg is OK')
            response = ['FixMsg is OK']
            self.writeResExcel('report/rex_report.xlsx', response, 4, 'M')
        if 'Order execType error' in content:
            logfix.info("execType is NG")
            response = ['execType is NG']
            self.writeResExcel('report/rex_report.xlsx', response, 7, "M")
        else:
            logfix.info("execType is OK")
            response = ['execType is OK']
            self.writeResExcel('report/rex_report.xlsx', response, 8, "M")

    def writeResExcel(self, filename, data, row, column):
        # 打开现有的Excel文件或者创建新的Workbook
        workbook = load_workbook(filename)  # load_workbook指打开现有文件或新的对象
        #     指定要写入数据的工作表
        sheet = workbook.active
        # 指定要写入的列号
        start_row = row  # 行号
        start_column = column  # 列号
        # 写入数据到指定列
        for row, value in enumerate(data, start=start_row):
            sheet[start_column + str(row)] = value

        # 保持并关闭工作簿
        workbook.save(filename)

    def getClOrdID(self):
        # "随机数生成ClOrdID"
        self.execID += 1
        # 获取当前时间并且进行格式转换
        t = int(time.time())
        str1 = ''.join([str(i) for i in random.sample(range(0, 9), 4)])
        return str(t) + str1 + str(self.execID).zfill(6)

    def insert_order_request(self, row):
        # 构造一个FIX协议消息（NewOrderSingle消息）并设置消息中的各个字段值
        msg = fix.Message()  # 创建一个空的FIX消息对象msg
        header = msg.getHeader()  # 获取消息头
        header.setField(fix.MsgType(fix.MsgType_NewOrderSingle))  # 消息类型字段（MsgType）设为NewOrderSingle（D）
        header.setField(fix.MsgType("D"))
        msg.setField(fix.Account(row["Account"]))
        msg.setField(fix.ClOrdID(self.getClOrdID()))
        msg.setField(fix.OrderQty(row["OrderQty"]))
        msg.setField(fix.OrdType(row["OrdType"]))
        msg.setField(fix.Side(row["Side"]))
        msg.setField(fix.Symbol(row["Symbol"]))
        # msg.setField(fix.HandlInst('1'))  # 处理方式
        ClientID = msg.getField(11)
        msg.setField(fix.ClientID(ClientID))
        # 判断订单类型,限价单读取case中的price并且设置，市价单则不设置价格
        if row["OrdType"] == "2":
            msg.setField(fix.Price(row["Price"]))  # 如果值是2，表示是限价单，要设置价格

        # 5个非必填的字段
        if row["TimeInForce"] != "":
            msg.setField(fix.TimeInForce(row["TimeInForce"]))

        if row["Rule80A"] != "":
            msg.setField(fix.Rule80A(row["Rule80A"]))

        if row["CashMargin"] != "":
            msg.setField(fix.CashMargin(row["CashMargin"]))

        # 自定义Tag
        if row["CrossingPriceType"] != "":
            msg.setField(8164, row["CrossingPriceType"])

        if row["MarginTransactionType"] != "":
            msg.setField(8214, row["MarginTransactionType"])

        # 获取TransactTime
        trstime = fix.TransactTime()
        trstime.setString(datetime.utcnow().strftime("%Y%m%d-%H:%M:%S.%f"))
        msg.setField(trstime)

        fix.Session.sendToTarget(msg, self.sessionID)  # 发送请求
        return msg  # 返回消息体

    def order_cancel_request(self, row):
        if row["Symbol"] == '5076' and row["OrdType"] == "1":
            clOrdId = self.PTF_CANCEL_LIST[0]
        elif row["Symbol"] == '5076' and row["OrdType"] == "2":
            clOrdId = self.PTF_CANCEL_LIST[1]
        else:
            clOrdId = self.ORDERS_DICT

        time.sleep(1)
        msg = fix.Message()
        header = msg.getHeader()
        header.setField(fix.MsgType(fix.MsgType_OrderCancelRequest))
        header.setField(fix.BeginString("FIX.4.2"))
        header.setField(fix.MsgType("F"))
        msg.setField(fix.OrigClOrdID(clOrdId))
        msg.setField(fix.ClOrdID(self.getClOrdID()))
        msg.setField(fix.Symbol(row["Symbol"]))
        msg.setField(fix.Side(row["Side"]))

        trstime = fix.TransactTime()
        trstime.setString(datetime.utcnow().strftime("%Y%m%d-%H:%M:%S.%f"))
        msg.setField(trstime)
        fix.Session.sendToTarget(msg, self.sessionID)
        return msg

    def runTestCase(self, row):
        # 判断case是下单还是取消订单
        action = row["ActionType"]
        if action == 'NewAck':
            self.insert_order_request(row)
        elif action == 'CancelAck':
            self.order_cancel_request(row)

    def load_test_case(self):
        module_name = "generation"
        module_path = generation_path
        # 导入具有完整文件路径的模块
        module1 = SourceFileLoader(module_name, module_path).load_module()

        generation = module1.generation
        """Run"""
        with open('../../testcases/REX_Functional_Test_Matrix.json', 'r') as f_json:
            # 生成报告模版
            generation('../../testcases/REX_Functional_Test_Matrix.json', 'report/rex_report.xlsx')
            case_data_list = json.load(f_json)
            time.sleep(2)
            # 循环所有用例，并把每条用例放入runTestCase方法中，
            for row in case_data_list["testCase"]:
                if row['Id'] == "1":
                    self.insert_order_request(row)
                    time.sleep(60)
                if row["Symbol"] == '5076' and row["OrdType"] == "1" and row["Comment"] == "CancelAck":
                    time.sleep(120)
                    self.runTestCase(row)
                else:
                    time.sleep(1)
                    self.runTestCase(row)


def main():
    try:
        settings = fix.SessionSettings("rex_regression_client.cfg")
        application = Application()
        storefactory = fix.FileStoreFactory(settings)
        logfactory = fix.FileLogFactory(settings)
        initiator = fix.SocketInitiator(application, storefactory, settings, logfactory)

        initiator.start()
        application.load_test_case()
        # 执行完所有测试用例后等待时间
        sleep_duration = timedelta(minutes=5)
        end_time = datetime.now() + sleep_duration
        while datetime.now() < end_time:
            time.sleep(1)
        initiator.stop()

    except (fix.ConfigError, fix.RuntimeError) as e:
        print(e)
        sys.exit()


if __name__ == '__main__':
    main()