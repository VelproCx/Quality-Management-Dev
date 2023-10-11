#!/usr/bin/python
# -*- coding: utf8 -*-
"""FIX Application"""
import difflib
import random
import sys
import threading
import time
import logging
import quickfix as fix
from datetime import datetime, timedelta
from model.logger import setup_logger
import json

__SOH__ = chr(1)

# report
setup_logger('logfix', 'edp_fix_client/initiator/edp_full_stock_test/cgw101/logs/edp_fullstock_report.log')
logfix = logging.getLogger('logfix')


class Application(fix.Application):
    execID = 0
    symbol_list = []
    Result = []
    order_new = 0
    order_ioc_expired = 0
    order_accepted = 0
    order_rejected = 0
    order_edp_indication = 0
    order_tostnet_confirmation = 0
    order_tostnet_rejection = 0
    order_num = 0

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
        logfix.info("Result: order_new = {}（ order_accepted = {}, order_rejected = {}）".format(self.order_new,
                                                                                               self.order_accepted,
                                                                                               self.order_rejected, ))
        logfix.info(
            "Result: order_edp_indication = {}（ order_tostnet_confirmation = {}, order_tostnet_rejection = {}）".format(
                self.order_edp_indication,
                self.order_tostnet_confirmation,
                self.order_tostnet_rejection
            ))
        logfix.info("Result: order_ioc_expired = {}".format(
            self.order_ioc_expired
        ))
        print("Session ({}) logout !".format(sessionID.toString()))
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
            if (clOrdID, orderQty, ordType,
                side, symbol, transactTime,
                ) != "":
                logfix.info("(sendMsg) New Ack >> %s" % msg)
                self.order_new += 1
            else:
                logfix.info("(sendMsg) New Ack >> %s" % msg + 'New Order Single FixMsg Error!')
        return

    def fromAdmin(self, message, sessionID):
        # "接收会话类型消息时调用此方法"
        msg = message.toString().replace(__SOH__, "|")
        logfix.info("(Core) R << %s" % msg)
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
                        self.order_accepted += 1
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
                        self.order_rejected += 1
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
                        # routingDecisionTime = message.getField(8051)
                        if (
                                avgPx, clOrdID, CumQty, execID, execTransType, orderID, orderQty, ordType, rule80A,
                                side, symbol, timeInForce, transactTime, execBroker, clientID, execType, leavesQty,
                                cashMargin, crossingPriceType, fsxTransactTime, marginTransactionType, origClOrdID,
                                text) != "" and primaryLastPx != "0" or primaryBidPx != "0" or primaryAskPx != "0":
                            self.order_ioc_expired += 1
                            logfix.info("(recvMsg) Order Expired << {}".format(msg))
                            logfix.info("Result : Order Expired ," + "ordStatus =" + ordStatus)
                        else:
                            logfix.info("(recvMsg) Order Expired FixMsg Error! << {}".format(msg))
                    # Execution Report – Order Canceled
                    elif 'ERROR_20010052,Order canceled due to client cancel request.' == text:
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
                            self.order_tostnet_rejection += 1
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
                            self.order_edp_indication += 1
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
                            self.order_tostnet_confirmation += 1
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

    # 判断log文件中是否存在 Market Price is not matching
    def logsCheck(self):
        with open('edp_fullstock_report.log', 'r') as f:
            content = f.read()
        if 'FixMsg Error' in content:
            logfix.info('FixMsg is NG')
        else:
            logfix.info('FixMsg is OK')
        if 'Order execType error' in content:
            logfix.info("execType is NG")
        else:
            logfix.info("execType is OK")

    def getClOrdID(self):
        # "随机数生成ClOrdID"
        self.execID += 1
        # 获取当前时间并且进行格式转换
        t = int(time.time())
        str1 = ''.join([str(i) for i in random.sample(range(0, 9), 4)])
        return str(t) + str1 + str(self.execID).zfill(6)

    # Order Qty 随机生成
    def getOrderQty(self):
        # 随机生成Qty1-5
        orderQty = random.randint(1, 5)
        return orderQty

    def insert_order_request(self, row):
        global orderNum
        msg = fix.Message()
        header = msg.getHeader()
        header.setField(fix.MsgType(fix.MsgType_NewOrderSingle))
        header.setField(fix.MsgType("D"))
        msg.setField(fix.Account("RSIT_EDP_ACCOUNT_8"))
        msg.setField(fix.ClOrdID(self.getClOrdID()))
        msg.setField(fix.OrderQty(row["OrderQty"]))
        msg.setField(fix.OrdType("1"))
        msg.setField(fix.Symbol(row["Symbol"]))
        if (self.order_num % 2) == 0:
            msg.setField(fix.Side("1"))
        else:
            msg.setField(fix.Side("2"))

        # 获取TransactTime
        trstime = fix.TransactTime()
        trstime.setString(datetime.utcnow().strftime("%Y%m%d-%H:%M:%S.%f"))
        msg.setField(trstime)
        fix.Session.sendToTarget(msg, self.sessionID)
        return msg

    # 加载用例文件
    def load_test_case(self):
        """Run"""
        with open('../../../testcases/full_stock_List.json', 'r') as f_json:
            case_data_list = json.load(f_json)
            time.sleep(2)
            # 循环所有用例，并把每条用例放入runTestCase方法中，
            while self.order_num < 1:
                self.order_num += 1
                for row in case_data_list["testCase"]:
                    self.insert_order_request(row)
                    time.sleep(0.04)

    def gen_thread(self):
        threads = []
        for _ in range(5):
            t = threading.Thread(target=self.load_test_case())
            threads.append(t)
        for t in threads:
            t.start()


def main():
    try:
        settings = fix.SessionSettings("edp_fullstock_client.cfg")
        application = Application()
        storefactory = fix.FileStoreFactory(settings)
        logfactory = fix.FileLogFactory(settings)
        initiator = fix.SocketInitiator(application, storefactory, settings, logfactory)

        initiator.start()
        application.gen_thread()
        # 执行完所有测试用例后等待时间
        sleep_duration = timedelta(minutes=2)
        end_time = datetime.now() + sleep_duration
        while datetime.now() < end_time:
            time.sleep(1)
        initiator.stop()

    except (fix.ConfigError, fix.RuntimeError) as e:
        print(e)
        sys.exit()


if __name__ == '__main__':
    main()
