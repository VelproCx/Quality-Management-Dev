#!/usr/bin/python
# -*- coding: utf8 -*-
"""FIX Application"""
import argparse
import configparser
import sys
import quickfix as fix
import time
import logging
from datetime import datetime, timedelta
from model.logger import setup_logger
import json
import random

__SOH__ = chr(1)

class Application(fix.Application):
    execID = 0

    def __init__(self):
        super().__init__()
        self.sessionID = None
        self.account = None
        self.Sender = None
        self.Target = None
        self.Host = None
        self.Port = None

        self.order_new = 0
        self.order_ioc_expired = 0
        self.order_accepted = 0
        self.order_rejected = 0
        self.order_fill_indication = 0
        self.order_tostnet_confirmation = 0
        self.order_tostnet_rejection = 0

    def onCreate(self, sessionID):
        # "服务器启动时候调用此方法创建"
        self.sessionID = sessionID
        print("onCreate : Session (%s)" % sessionID.toString())
        return

    def onLogon(self, sessionID):
        # "客户端登陆成功时候调用此方法"
        self.sessionID = sessionID
        print("Successful Logon to session '%s'." % sessionID.toString())
        return

    def onLogout(self, sessionID):
        logfix.info("Result: order_new = {}（ order_accepted = {}, order_rejected = {}）".format(
            self.order_new,
            self.order_accepted,
            self.order_rejected, ))
        logfix.info(
            "Result: order_edp_indication = {}（ order_tostnet_confirmation = {}, order_tostnet_rejection = {}）".format(
                self.order_fill_indication,
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
        logfix.info("(Core) S >> %s" % msg)
        return

    def toApp(self, message, sessionID):

        # "发送业务消息时候调用此方法"
        msgtype = message.getHeader().getField(35)
        msg = message.toString().replace(__SOH__, "|")
        logfix.info("(sendMsg) S >> %s" % msg)
        if msgtype == "D":
            self.order_new += 1
        return

    def fromAdmin(self, message, sessionID):
        # "接收会话类型消息时调用此方法"
        msg = message.toString().replace(__SOH__, "|")
        logfix.info("(Core) R << %s" % msg)
        return

    def fromApp(self, message, sessionID):
        # "接收业务消息时调用此方法"
        # 使用quickFix框架getField方法提取clOrdId、ordStatus
        ordStatus = message.getField(39)
        msg = message.toString().replace(__SOH__, "|")
        execTransType = message.getField(20)
        if execTransType == "2":
            self.order_tostnet_confirmation += 1
            logfix.info("(recvMsg)ToSTNeT Confirmation << {}".format(msg))
        else:
            if ordStatus == "0":
                self.order_accepted += 1
                logfix.info("(recvMsg) Order Accepted << {}".format(msg))
            elif ordStatus == "8":
                self.order_rejected += 1
                logfix.info("(recvMsg) Order Rejected << {}".format(msg))
            elif ordStatus == "4":
                text = message.getField(58)
                if 'ERROR_00010051,Order rejected due to IoC expired.' == text:
                    self.order_ioc_expired += 1
                    logfix.info("(recvMsg) Order IOC Expired << {}".format(msg))
                else:
                    self.order_tostnet_rejection += 1
                    logfix.info("(recvMsg)ToSTNeT Rejection << {}".format(msg))
            elif ordStatus == "1" or ordStatus == "2":
                self.order_fill_indication += 1
                logfix.info("(recvMsg) Order Filled Indication<< {}".format(msg))
        self.onMessage(message, sessionID)
        return (
            self.order_ioc_expired,
            self.order_accepted,
            self.order_rejected,
            self.order_tostnet_confirmation,
            self.order_tostnet_rejection
        )

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

    def insert_order_request(self, row, account, order_num):
        msg = fix.Message()
        header = msg.getHeader()
        header.setField(fix.MsgType(fix.MsgType_NewOrderSingle))
        header.setField(fix.MsgType("D"))
        msg.setField(fix.Account(account))
        msg.setField(fix.ClOrdID(self.getClOrdID()))
        msg.setField(fix.OrderQty(100))
        msg.setField(fix.OrdType("1"))
        msg.setField(fix.Symbol(row["Symbol"]))
        # msg.setField(fix.Side(row["Side"]))

        if (order_num % 2) == 0:
            msg.setField(fix.Side("2"))
        else:
            msg.setField(fix.Side("1"))

        # 获取TransactTime
        trstime = fix.TransactTime()
        trstime.setString(datetime.utcnow().strftime("%Y%m%d-%H:%M:%S.%f"))
        msg.setField(trstime)

        fix.Session.sendToTarget(msg, self.sessionID)
        return msg

    def load_test_case(self, account):
        order_num = 0
        """Run"""
        # with open('../../testcases/topix400_case.json', 'r') as f_json:
        with open('edp_fix_client/initiator/edp_performance_test/uat_test_with_hrt.json', 'r') as f_json:
            case_data_list = json.load(f_json)
            time.sleep(2)
            # 循环所有用例，并把每条用例放入runTestCase方法中，
            while order_num < 1:
                order_num += 1
                for row in case_data_list["testCase"]:
                    self.insert_order_request(row, account, order_num)
                    time.sleep(0.0025)

    def read_config(self, Sender, Target, Host, Port):
        # 读取并修改配置文件
        config = configparser.ConfigParser()
        config.read('edp_fix_client/initiator/edp_performance_test/edp_performance_client.cfg')
        config.set('SESSION', 'SenderCompID', Sender)
        config.set('SESSION', 'TargetCompID', Target)
        config.set('SESSION', 'SocketConnectHost', Host)
        config.set('SESSION', 'SocketConnectPort', Port)

        with open('edp_fix_client/initiator/edp_performance_test/edp_performance_client.cfg', 'w') as configfile:
            config.write(configfile)


def main():
    global logfix
    try:
        # 使用argparse的add_argument方法进行传参
        parser = argparse.ArgumentParser()  # 创建对象
        parser.add_argument('--account', default='RSIT_EDP_ACCOUNT_7', help='choose account to use for test')
        parser.add_argument('--Sender', default='RSIT_EDP_7', help='choose Sender to use for test')
        parser.add_argument('--Target', default='FSX_SIT_EDP', help='choose Target to use for test')
        parser.add_argument('--Host', default='54.250.107.1', help='choose Host to use for test')
        parser.add_argument('--Port', default='5007', help='choose Port to use for test')

        args = parser.parse_args()  # 解析参数
        account = args.account
        Sender = args.Sender
        Target = args.Target
        Host = args.Host
        Port = args.Port

        # report
        setup_logger('logfix', 'edp_fix_client/initiator/edp_performance_test/logs/{}_Report.log'.format(account))
        logfix = logging.getLogger('logfix')

        cfg = Application()
        cfg.Sender = Sender
        cfg.Target = Target
        cfg.Host = Host
        cfg.Port = Port
        cfg.read_config(Sender, Target, Host, Port)

        settings = fix.SessionSettings("edp_fix_client/initiator/edp_performance_test/edp_performance_client.cfg")
        application = Application()
        application.account = account
        store_factory = fix.FileStoreFactory(settings)
        log_factory = fix.FileLogFactory(settings)
        initiator = fix.SocketInitiator(application, store_factory, settings, log_factory)

        initiator.start()
        application.load_test_case(account)
        # sleep_duration = timedelta(minutes=1)
        # end_time = datetime.now() + sleep_duration
        # while datetime.now() < end_time:
        #     time.sleep(1)
        initiator.stop()

    except (fix.ConfigError, fix.RuntimeError) as e:
        print(e)
        sys.exit()


if __name__ == '__main__':
    main()
