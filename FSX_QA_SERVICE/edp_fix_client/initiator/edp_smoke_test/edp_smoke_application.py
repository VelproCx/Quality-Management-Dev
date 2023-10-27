#!/usr/bin/python
# -*- coding: utf8 -*-
"""FIX Application"""
import argparse
import configparser
import random
import sys
import quickfix as fix
import time
import logging
from datetime import datetime, timedelta
from model.logger import setup_logger
import json

__SOH__ = chr(1)



class Application(fix.Application):
    orderID = 0
    execID = 0

    def __init__(self):
        super().__init__()
        self.sessionID = None

    def onCreate(self, sessionID):
        # "服务器启动时候调用此方法创建"
        self.sessionID = sessionID
        print("onCreate : Session ({})".format(sessionID.toString()))
        return

    def onLogon(self, sessionID):
        # "客户端登陆成功时候调用此方法"
        self.sessionID = sessionID
        print("Successful Logon to session '{}'.".format(sessionID.toString()))
        return

    def onLogout(self, sessionID):
        print("Session (%s) logout !" % sessionID.toString())
        return

    def toAdmin(self, message, sessionID):
        # "发送会话消息时候调用此方法"
        msg = message.toString().replace(__SOH__, "|")
        logfix.info("(Core) S >> {}".format(msg))
        return

    def toApp(self, message, sessionID):
        # "发送业务消息时候调用此方法"
        logfix.info("-------------------------------------------------------------------------------------------------")
        msgType = message.getHeader().getField(35)
        msg = message.toString().replace(__SOH__, "|")
        # 7.1 New Order Single
        if msgType == "D":
            orderQty = message.getField(38)
            ordType = message.getField(40)
            clOrdID = message.getField(11)
            side = message.getField(54)
            symbol = message.getField(55)
            transactTime = message.getField(60)

            if (clOrdID, orderQty, ordType, side, symbol, transactTime,) != "":
                logfix.info("(sendMsg) New Ack >> {}".format(msg))
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
        # "接收会话类型消息时调用此方法"
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

            if msgType != '9':
                avgPx = message.getField(6)
                CumQty = message.getField(14)
                execID = message.getField(17)
                execTransType = message.getField(20)
                orderQty = message.getField(38)
                ordType = message.getField(40)
                rule80A = message.getField(47)
                side = message.getField(54)
                symbol = message.getField(55)
                timeInForce = message.getField(59)
                clientID = message.getField(109)
                execType = message.getField(150)
                leavesQty = message.getField(151)
                cashMargin = message.getField(544)
                crossingPriceType = message.getField(8164)
                marginTransactionType = message.getField(8214)
                # Added tag to the EDP project
                MinQty = message.getField(110)
                OrderClassification = message.getField(8060)
                SelfTradePreventionId = message.getField(8174)

                msg = message.toString().replace(__SOH__, "|")
                # 7.2 Execution Report – Order Accepted
                if ordStatus == "0":
                    execBroker = message.getField(76)
                    lastShares = message.getField(32)
                    lastPx = message.getField(31)
                    clOrdID = message.getField(11)
                    if (
                            avgPx, clOrdID, CumQty, execID, execTransType, lastPx, lastShares, orderID, orderQty,
                            ordType, rule80A,
                            side, symbol, timeInForce, transactTime, execBroker, clientID, execType, leavesQty,
                            cashMargin,
                            crossingPriceType, fsxTransactTime, marginTransactionType, MinQty, OrderClassification,
                            SelfTradePreventionId) != "":
                        logfix.info("(recvMsg) Order Accepted << {}".format(msg) + "ordStatus = " + str(ordStatus))
                        logfix.info("Result : Order Accepted ," + "ordStatus =" + ordStatus)
                    else:
                        logfix.info("(recvMsg) Order Accepted << {}".format(msg) + 'Order Accepted FixMsg Error!')
                    if execType != ordStatus:
                        logfix.info(
                            "(recvMsg) Order execType error,orderStatus = {},execType = {}".format(ordStatus, execType))
                # 7.3 Execution Report – Order Rejected
                elif ordStatus == "8":
                    text = message.getField(58)
                    ordRejReason = message.getField(103)
                    lastShares = message.getField(32)
                    lastPx = message.getField(31)
                    clOrdID = message.getField(11)
                    if (
                            avgPx, clOrdID, CumQty, execID, execTransType, lastPx, lastShares, orderID, orderQty,
                            ordType, rule80A,
                            side, symbol, timeInForce, transactTime, clientID, execType, leavesQty, cashMargin,
                            crossingPriceType,
                            fsxTransactTime, marginTransactionType, text, ordRejReason, MinQty, OrderClassification,
                            SelfTradePreventionId) != "":
                        logfix.info("(recvMsg) Order Rej << {}".format(msg) + "RejRes = " + str(text))
                    else:
                        logfix.info("(recvMsg) Order Rejected << {}".format(msg) + 'Order Rejected FixMsg Error!')
                    if execType != ordStatus:
                        logfix.info(
                            "(recvMsg) Order execType error,orderStatus = {},execType = {}".format(ordStatus, execType))
                elif ordStatus == "4":
                    #  7.8 Execution Report – Order Canceled / IOC Expired / ToSTNeT Rejection
                    execBroker = message.getField(76)
                    text = message.getField(58)
                    origClOrdID = message.getField(41)
                    clOrdID = message.getField(11)
                    # Execution Report – IOC Expired
                    if 'ERROR_00010051,Order rejected due to IoC expired.' == text:
                        primaryLastPx = message.getField(8031)
                        primaryBidPx = message.getField(8032)
                        primaryAskPx = message.getField(8033)
                        print(primaryLastPx, primaryBidPx, primaryAskPx)
                        # routingDecisionTime = message.getField(8051)
                        if (
                                avgPx, clOrdID, CumQty, execID, execTransType, orderID, orderQty, ordType, rule80A,
                                side, symbol, timeInForce, transactTime, execBroker, clientID, execType, leavesQty,
                                cashMargin, crossingPriceType, fsxTransactTime, marginTransactionType, origClOrdID,
                                text) != "" and primaryLastPx != "0" or primaryBidPx != "0" or primaryAskPx != "0":
                            logfix.info("(recvMsg) Order Expired << {}".format(msg))
                            logfix.info("Result : Order Expired ," + "ordStatus =" + ordStatus)
                        else:
                            logfix.info("(recvMsg) Order Expired FixMsg Error! << {}".format(msg))
                    # Execution Report – Order Canceled
                    elif 'ERROR_00010052,Order canceled due to client cancel request.' == text:
                        if (
                                avgPx, clOrdID, CumQty, execID, execTransType, orderID, orderQty, ordType, rule80A,
                                side, symbol, timeInForce, transactTime, clientID, execType, leavesQty, cashMargin,
                                crossingPriceType, fsxTransactTime, marginTransactionType, origClOrdID, execBroker,
                                MinQty, OrderClassification, SelfTradePreventionId, text) != "":
                            logfix.info("(recvMsg) Order Canceled << {}".format(msg))
                            logfix.info("Result : Order Canceled ," + "ordStatus =" + ordStatus)
                        else:
                            logfix.info("(recvMsg) Order Canceled << {}".format(msg) + 'Order Canceled FixMsg Error!')
                    # Execution Report – ToSTNeT Rejection
                    else:
                        if (
                                avgPx, clOrdID, CumQty, execID, execTransType, orderID, orderQty, ordType, rule80A,
                                side, symbol, timeInForce, transactTime, execBroker, clientID, execType, leavesQty,
                                cashMargin, crossingPriceType, fsxTransactTime, marginTransactionType, origClOrdID,
                                text) != "":
                            logfix.info("(recvMsg)ToSTNeT Rejection << {}".format(msg))
                            logfix.info("Result:ToSTNeT Rejection ," + "ordStatus =" + ordStatus)
                        else:
                            logfix.info(
                                "(recvMsg)ToSTNeT Rejection << {}".format(msg) + 'EDP ToSTNeT Rejection FixMsg Error!')
                # 7.7 Execution Report – Trade
                elif ordStatus == "1" or ordStatus == "2":
                    lastPx = float(message.getField(31))
                    lastShares = message.getField(32)
                    execBroker = message.getField(76)
                    primaryLastPx = float(message.getField(8031))
                    primaryBidPx = float(message.getField(8032))
                    primaryAskPx = float(message.getField(8033))
                    routingDecisionTime = message.getField(8051)
                    # price = message.getField(44)
                    # Added tag to the EDP project
                    lastLiquidityind = message.getField(851)
                    if execTransType == "0":
                        if (
                                avgPx, clOrdID, CumQty, execID, execTransType, lastPx, lastShares, orderID, orderQty,
                                ordType, rule80A, side, symbol, timeInForce, transactTime, execBroker, clientID,
                                execType, leavesQty, cashMargin, crossingPriceType, fsxTransactTime,
                                marginTransactionType, primaryLastPx, primaryBidPx, primaryAskPx, routingDecisionTime,
                                MinQty, OrderClassification, SelfTradePreventionId, lastLiquidityind) != "":
                            logfix.info(
                                "(recvMsg) Order Filled << {}".format(msg))
                            if ordStatus == '2':
                                logfix.info("Result : EP3 Order Filled ," + "ordStatus =" + ordStatus)
                            else:
                                logfix.info("Result : EP3 Order Partially Filled ," + "ordStatus =" + ordStatus)

                        else:
                            logfix.info("(recvMsg) EP3 Order Filled << {}".format(msg) + "Order Trade FixMsg Error!")

                    elif execTransType == '2':
                        execRefID = message.getField(19)
                        lastLiquidityInd = message.getField(851)
                        toSTNeTOrderID = message.getField(8101)
                        toSTNeTExecutionID = message.getField(8102)
                        toSTNeTTransactionTime = message.getField(8106)
                        SecondaryOrderID = message.getField(198)
                        ContraBroker = message.getField(375)
                        SecondaryExecID = message.getField(527)
                        if (
                                avgPx, clOrdID, CumQty, execID, execTransType, lastPx, lastShares, orderID,
                                orderQty, ordType, rule80A, side, symbol, timeInForce, transactTime, execBroker,
                                clientID, execType, leavesQty, cashMargin, crossingPriceType, fsxTransactTime,
                                marginTransactionType, primaryLastPx, primaryBidPx, primaryAskPx, routingDecisionTime,
                                MinQty, OrderClassification, SelfTradePreventionId, execRefID, lastLiquidityInd,
                                toSTNeTOrderID, toSTNeTTransactionTime, SecondaryOrderID, ContraBroker, SecondaryExecID,
                                toSTNeTExecutionID) != "":
                            logfix.info(
                                "(recvMsg)ToSTNeT Confirmation << {}".format(msg))
                        else:
                            logfix.info(
                                "(recvMsg)ToSTNeT Confirmation << {}".format(
                                    msg) + 'EDP ToSTNeT Confirmation FixMsg Error!')

            else:
                origClOrdID = message.getField(41)
                text = message.getField(58)
                cxlRejReason = message.getField(102)
                cxlRejResponseTo = message.getField(434)
                clOrdID = message.getField(11)
                msg = message.toString().replace(__SOH__, "|")
                if (clOrdID, orderID, transactTime, fsxTransactTime, origClOrdID, text,
                    cxlRejReason, cxlRejResponseTo) != "":
                    logfix.info("(recvMsg) Order Cancel Reject << {}".format(msg) + "ordStatus = " + str(ordStatus))
                else:
                    logfix.info("(recvMsg) Order Cancel Reject << {}".format(msg) + 'Order Cancel Reject FixMsg Error!')

            self.onMessage(message, sessionID)
        return

    def onMessage(self, message, sessionID):
        """Processing application message here"""
        pass

    def getClOrdID(self):
        # "随机数生成ClOrdID"
        self.execID += 1
        # 获取当前时间并且进行格式转换
        t = int(time.time())
        str1 = ''.join([str(i) for i in random.sample(range(0, 9), 4)])
        return str(t) + str1 + str(self.execID).zfill(6)

    def insert_order_request(self, Data):
        msg = fix.Message()
        header = msg.getHeader()
        header.setField(fix.MsgType(fix.MsgType_NewOrderSingle))
        header.setField(fix.MsgType("D"))
        msg.setField(fix.Account(Data['Account']))
        msg.setField(fix.ClOrdID(self.getClOrdID()))
        msg.setField(fix.OrderQty(Data["OrderQty"]))
        msg.setField(fix.OrdType(Data["OrdType"]))
        msg.setField(fix.Side(Data["Side"]))
        msg.setField(fix.Symbol(Data["Symbol"]))
        # ClientID = msg.getField(11)

        # 判断订单类型
        if Data["OrdType"] == "2":
            msg.setField(fix.Price(Data["Price"]))

        if Data["TimeInForce"] != "":
            msg.setField(fix.TimeInForce(Data["TimeInForce"]))

        if Data["Rule80A"] != "":
            msg.setField(fix.Rule80A(Data["Rule80A"]))

        if Data["CashMargin"] != "":
            msg.setField(fix.CashMargin(Data["CashMargin"]))

        # 自定义Tag
        if Data["CrossingPriceType"] != "":
            msg.setField(8164, Data["CrossingPriceType"])

        if Data["MarginTransactionType"] != "":
            msg.setField(8214, Data["MarginTransactionType"])

        # EDP

        if Data["MinQty"] != "":
            msg.setField(fix.MinQty(Data["MinQty"]))

        if Data["OrderClassification"] != "":
            msg.setField(8060, Data["OrderClassification"])

        if Data["SelfTradePreventionId"] != "":
            msg.setField(8174, Data["SelfTradePreventionId"])

        # 获取TransactTime
        trstime = fix.TransactTime()
        trstime.setString(datetime.utcnow().strftime("%Y%m%d-%H:%M:%S.%f"))
        msg.setField(trstime)

        fix.Session.sendToTarget(msg, self.sessionID)

        return msg

    def order_cancel_request(self, row):
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

    # def read_config(self, Sender, Target, Host, Port):
    #     # 读取并修改配置文件
    #     config = configparser.ConfigParser(allow_no_value=True)
    #     config.optionxform = str  # 保持键的大小写
    #     config.read('/Users/tendy/Documents/FSX-DEV-QA/FSX_QA_SERVICE/edp_fix_client/initiator/edp_smoke_test/edp_smoke_client.cfg')
    #     config.set('SESSION', 'SenderCompID', Sender)
    #     config.set('SESSION', 'TargetCompID', Target)
    #     config.set('SESSION', 'SocketConnectHost', Host)
    #     config.set('SESSION', 'SocketConnectPort', Port)
    #
    #     with open('/Users/tendy/Documents/FSX-DEV-QA/FSX_QA_SERVICE/edp_fix_client/initiator/edp_smoke_test/edp_smoke_client.cfg', 'w') as configfile:
    #         config.write(configfile)


def main():
    global logfix
    global Data
    try:
        # 使用argparse的add_argument方法进行传参
        parser = argparse.ArgumentParser()  # 创建对象
        parser.add_argument('--account', default='RSIT_EDP_ACCOUNT_1', help='choose account to use for test')
        # parser.add_argument('--Sender', default='RSIT_EDP_1', help='choose Sender to use for test')
        # parser.add_argument('--Target', default='FSX_SIT_EDP', help='choose Target to use for test')
        # parser.add_argument('--Host', default='54.250.107.1', help='choose Host to use for test')
        # parser.add_argument('--Port', default='5001', help='choose Port to use for test')
        parser.add_argument('--Data', help='please enter send data')

        args = parser.parse_args()  # 解析参数
        account = args.account
        # Sender = args.Sender
        # Target = args.Target
        # Host = args.Host
        # Port = args.Port

        if args.Data:
            Data = json.loads(args.Data)
        else:
            Data = {}

        # report
        setup_logger('logfix', 'edp_fix_client/initiator/edp_smoke_test/logs/edp_smoke_test_Report.log')
        logfix = logging.getLogger('logfix')

        cfg = Application()
        # cfg.Sender = Sender
        # cfg.Target = Target
        # cfg.Host = Host
        # cfg.Port = Port
        # cfg.read_config(Sender, Target, Host, Port)

        settings = fix.SessionSettings("edp_fix_client/initiator/edp_smoke_test/edp_smoke_client.cfg")
        application = Application()
        application.account = account
        store_factory = fix.FileStoreFactory(settings)
        log_factory = fix.FileLogFactory(settings)
        initiator = fix.SocketInitiator(application, store_factory, settings, log_factory)

        initiator.start()
        time.sleep(2)
        if Data["ActionType"] == "NewAck":
            application.insert_order_request(Data)
        elif Data["ActionType"] == "CancelAck":
            application.order_cancel_request(Data)
        sleep_duration = timedelta()
        end_time = datetime.now() + sleep_duration
        while datetime.now() < end_time:
            time.sleep(1)
        initiator.stop()

    except (fix.ConfigError, fix.RuntimeError) as e:
        print(e)
        sys.exit()


if __name__ == '__main__':
    main()
