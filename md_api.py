from py_ctp.eventEngine import  *
from py_ctp.eventType import  *
from py_ctp.quote import Quote
import threading
import logconfig as lc
import time
import config as cf
########################################################################
class MdApi:
    """
    Demo中的行情API封装
    封装后所有数据自动推送到事件驱动引擎中，由其负责推送到各个监听该事件的回调函数上

    对用户暴露的主动函数包括:
    登陆 login
    订阅合约 subscribe
    """
    #----------------------------------------------------------------------
    def __init__(self, eventEngine):
        """
        API对象的初始化函数
        """
        # 事件引擎，所有数据都推送到其中，再由事件引擎进行分发
        self.__eventEngine = eventEngine
        self.q = Quote()

        # 请求编号，由api负责管理
        self.__reqid = 0

        # 以下变量用于实现连接和重连后的自动登陆
        self.__userid = cf.userid
        self.__password = cf.password
        self.__brokerid = cf.brokerid

        api = self.q.CreateApi()
        spi = self.q.CreateSpi()
        self.q.RegisterSpi(spi)
        self.q.OnFrontConnected = self.onFrontConnected  # 交易服务器登陆相应
        self.q.OnRspUserLogin = self.onRspUserLogin  # 用户登陆
        self.q.OnFrontDisconnected = self.onFrontDisconnected
        self.q.OnRspError = self.onRspError
        self.q.OnRspSubMarketData = self.OnRspSubMarketData
        self.q.OnRtnDepthMarketData = self.onRtnDepthMarketData
        self.q.OnRspUserLogout = self.OnRspUserLogout

        self.q.RegCB()

        self.login_status = False  #登录状态

    def login(self):
        if self.login_status == False:
            self.q.RegisterFront('tcp://180.168.146.187:10010')
            self.q.Init()
    def logout(self):
        if self.login_status == True:
            self.q.ReqUserLogout(self.__brokerid,self.__userid)
    def release(self):
        self.q.Release()
        self.q = None

    def put_log_event(self, log):  # log事件注册
        event = Event(type_=EVENT_LOG)
        event.dict_['log'] = log
        self.__eventEngine.put(event)

    def onFrontConnected(self):
        """服务器连接"""
        lc.loger.info(threading.current_thread())
        self.put_log_event('行情服务器连接成功')
        time.sleep(3)
        self.q.ReqUserLogin(BrokerID=self.__brokerid, UserID=self.__userid, Password=self.__password)

    def  onFrontDisconnected(self, n):
        """服务器断开"""
        lc.loger.info(threading.current_thread())
        self.put_log_event('行情服务器连接断开')
        time.sleep(3)
        self.login_status = False

    def onRspError(self, error, n, last):
        """错误回报"""
        log = '行情错误回报，错误代码：' + str(error.__dict__['ErrorID']) + '错误信息：' + + str(error.__dict__['ErrorMsg'])
        self.put_log_event(log)

    def onRspUserLogin(self, data, error, n, last):
        """登陆回报"""
        if error.__dict__['ErrorID'] == 0:
            self.login_status = True
            log =  '行情服务器登陆成功'
        else:
            self.login_status = False
            log = '登陆回报，错误代码：' + str(error.__dict__['ErrorID']) + ',   错误信息：' + str(error.__dict__['ErrorMsg'])
        self.put_log_event(log)

    def OnRspUserLogout(self, data, error, n, last):
        """登出回报"""
        lc.loger.info(threading.current_thread())
        if error.__dict__['ErrorID'] == 0:
            self.login_status = False
            log =  '行情服务器登出成功'
        else:
            self.login_status = True
            log = '登出回报，错误代码：' + str(error.__dict__['ErrorID']) + ',   错误信息：' + str(error.__dict__['ErrorMsg'])
        self.put_log_event(log)

    def OnRspSubMarketData(self, data, info, n, last):
        pass

    def onRtnDepthMarketData(self, data):
        """行情推送"""
        # 特定合约行情事件
        #lc.loger.info(threading.current_thread())
        #lc.loger.info("get")
        event2 = Event(type_=(EVENT_MARKETDATA_CONTRACT + data.__dict__['InstrumentID']))
        event2.dict_['data'] = data.__dict__
        self.__eventEngine.put(event2)

    # ----------------------------------------------------------------------
    def subscribe(self, instrumentid):
        """订阅合约"""
        self.q.SubscribeMarketData(pInstrumentID=instrumentid)

    def unsubscribe(self, instrumentid):
        """退订合约"""
        self.q.UnSubscribeMarketData(pInstrumentID=instrumentid)