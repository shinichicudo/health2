import random
import time

from py_ctp.ctp_struct import *
from py_ctp.eventEngine import *
from py_ctp.eventType import *
from py_ctp.trade import Trade
import threading
import logconfig as lc
import config as cf
class TdApi:
    """
    Demo中的交易API封装
    主动函数包括：
    login 登陆
    getInstrument 查询合约信息
    getAccount 查询账号资金
    getInvestor 查询投资者
    getPosition 查询持仓
    sendOrder 发单
    cancelOrder 撤单
    """

    #----------------------------------------------------------------------
    def __init__(self, eventEngine):
        """API对象的初始化函数"""
        # 事件引擎，所有数据都推送到其中，再由事件引擎进行分发
        self.__eventEngine = eventEngine
        self.t = Trade()

        # 请求编号，由api负责管理
        self.__reqid = 0

        # 报单编号，由api负责管理
        self.__orderref = random.randrange(start=1000,stop=9000,step=random.randint(10,100)  )
        self.SessionID = None
        self.FrontID = None

        # 以下变量用于实现连接和重连后的自动登陆
        self.__userid = cf.userid
        self.__password = cf.password
        self.__brokerid = cf.brokerid

        api = self.t.CreateApi()
        spi = self.t.CreateSpi()
        self.t.RegisterSpi(spi)
        self.t.OnFrontConnected = self.onFrontConnected  # 交易服务器登陆相应
        self.t.OnRspUserLogin = self.onRspUserLogin  # 用户登陆
        self.t.OnErrRtnOrderInsert = self.onErrRtnOrderInsert
        self.t.OnRspUserLogout = self.OnRspUserLogout
        self.t.OnRtnInstrumentStatus = self.OnRtnInstrumentStatus
        self.t.OnFrontDisconnected = self.onFrontDisconnected
        self.t.OnRspSettlementInfoConfirm = self.onRspSettlementInfoConfirm  # 结算单确认
        self.t.OnRspQryInstrument = self.onRspQryInstrument  # 查询全部交易合约
        self.t.OnRspQryDepthMarketData = self.onRspQryDepthMarketData  # tick截面数据
        self.t.OnRspQryInvestorPosition = self.onRspQryInvestorPosition#查询持仓
        self.t.OnRspQryTradingAccount = self.onRspQryTradingAccount#查询账户
        self.t.OnRtnOrder = self.onRtnOrder#报单
        self.t.OnRtnTrade = self.onRtnTrade#成交
        self.t.OnRspQryInstrumentMarginRate = self.OnRspQryInstrumentMarginRate #获取保证金率
        #——————错误事件
        self.t.OnRspOrderInsert = self.onRspOrderInsert
        self.t.OnRspOrderAction =self.onRspOrderAction
        self.t.OnRspError = self.onRspError

        self.t.RegCB()
        self.login_status = False  #登录状态

    def login(self):
        if self.login_status == False:
            self.t.RegisterFront('tcp://180.168.146.187:10000')
            self.t.Init()
    def logout(self):
        if self.login_status == True:
            self.t.ReqUserLogout(self.__brokerid,self.__userid)
    def release(self):
        self.t.Release()
        self.t = None

    def put_log_event(self, log):  # log事件注册
        event = Event(type_=EVENT_LOG)
        event.dict_['log'] = log
        self.__eventEngine.put(event)

    def onFrontConnected(self):
        """服务器连接"""
        lc.loger.info(threading.current_thread())
        self.put_log_event('交易服务器连接成功')
        time.sleep(3)
        self.t.ReqUserLogin(BrokerID=self.__brokerid, UserID=self.__userid, Password=self.__password)

    def OnRtnInstrumentStatus(self, data):
        pass
    def  onFrontDisconnected(self, n):
        """服务器断开"""
        lc.loger.info(threading.current_thread())
        self.put_log_event('交易服务器连接断开')
        self.login_status = False
        time.sleep(3)
    def onRspUserLogin(self, data, error, n, last):
        """登陆回报"""
        if error.__dict__['ErrorID'] == 0:
            self.Investor = data.__dict__['UserID']
            self.BrokerID = data.__dict__['BrokerID']
            self.FrontID = data.__dict__['FrontID']
            self.SessionID = data.__dict__['SessionID']
            self.__orderref = int(data.__dict__['MaxOrderRef'])
            lc.loger.info(data.__dict__)
            self.login_status = True
            log = data.__dict__['UserID'] + '交易服务器登陆成功'
            self.t.ReqSettlementInfoConfirm(self.BrokerID, self.Investor)  # 对账单确认
        else:
            self.login_status = False
            log = '登陆回报，错误代码：' + str(error.__dict__['ErrorID']) + ',   错误信息：' + str(error.__dict__['ErrorMsg'])
        self.put_log_event(log)
    def OnRspUserLogout(self, data, error, n, last):
        """登出回报"""
        lc.loger.info(threading.current_thread())
        if error.__dict__['ErrorID'] == 0:
            self.login_status = False
            log =  '交易服务器登出成功'
        else:
            self.login_status = True
            log = '登出回报，错误代码：' + str(error.__dict__['ErrorID']) + ',   错误信息：' + str(error.__dict__['ErrorMsg'])
        self.put_log_event(log)


    def onRspSettlementInfoConfirm(self, data, error, n, last):
        """确认结算信息回报"""
        log = '结算信息确认完成'
        self.put_log_event(log)
        time.sleep(1)
        self.getInstrument()  # 查询合约资料
        #self.short('rb1801',4422,1)
        #self.sell('rb1801',4431,1)
        #self.getPosition()


    def onRspQryInstrument(self, data, error, n, last):
        """
        合约查询回报
        由于该回报的推送速度极快，因此不适合全部存入队列中处理，
        选择先储存在一个本地字典中，全部收集完毕后再推送到队列中
        （由于耗时过长目前使用其他进程读取）
        """
        if error.__dict__['ErrorID'] == 0:
            event = Event(type_=EVENT_INSTRUMENT)
            event.dict_['data'] = data.__dict__
            event.dict_['last'] = last
            self.__eventEngine.put(event)
            if last == True:
                time.sleep(2)
                self.t.ReqQryDepthMarketData()  # 查询合约截面数据
        else:
            log = '合约投资者回报，错误代码：' + str(error.__dict__['ErrorID']) + ',   错误信息：' + str(error.__dict__['ErrorMsg'])
            self.put_log_event(log)



    def onRspQryDepthMarketData(self, data, error, n, last):
        # 常规行情事件
        event = Event(type_=EVENT_MARKETDATA)
        event.dict_['data'] = data.__dict__
        event.dict_['last'] = last
        self.__eventEngine.put(event)


    def getInstrumentMarginRate(self,instrumentID):
        self.t.ReqQryInstrumentMarginRate(BrokerID=self.__brokerid,InvestorID=self.__userid,InstrumentID=instrumentID)  # 查询合约保证金率

    def OnRspQryInstrumentMarginRate(self, data, error, n, last):
        # 合约保证金
        event = Event(type_=EVENT_INSTRUMENT_MAGIN_RATE)
        event.dict_['data'] = data.__dict__
        event.dict_['last'] = last
        self.__eventEngine.put(event)
    def onRspQryInvestorPosition(self, data, error, n, last):
        """持仓查询回报"""
        if error.__dict__['ErrorID'] == 0:
            event = Event(type_=EVENT_POSITION)
            event.dict_['data'] = data.__dict__
            event.dict_['last'] = last
            self.__eventEngine.put(event)
        else:
            log = ('持仓查询回报，错误代码：'  +str(error.__dict__['ErrorID']) + ',   错误信息：' +str(error.__dict__['ErrorMsg']))
            self.put_log_event(log)

    # ----------------------------------------------------------------------
    def onRspQryTradingAccount(self, data, error, n, last):
        """资金账户查询回报"""
        if error.__dict__['ErrorID'] == 0:
            event = Event(type_=EVENT_ACCOUNT)
            event.dict_['data'] = data.__dict__
            self.__eventEngine.put(event)
        else:
            log = ('账户查询回报，错误代码：' +str(error.__dict__['ErrorID']) + ',   错误信息：' +str(error.__dict__['ErrorMsg']))
            self.put_log_event(log)

    def onRtnTrade(self, data):
        """成交回报"""
        # 常规成交事件
        event1 = Event(type_=EVENT_TRADE)
        event1.dict_['data'] = data.__dict__
        self.__eventEngine.put(event1)

    def onRtnOrder(self, data):
        """报单回报"""
        # 更新最大报单编号
        newref = data.__dict__['OrderRef']
        self.__orderref = max(self.__orderref, int(newref))
        # 常规报单事件
        event1 = Event(type_=EVENT_ORDER)
        event1.dict_['data'] = data.__dict__
        self.__eventEngine.put(event1)

    def onRspOrderInsert(self, data, error, n, last):
        """发单错误（柜台）"""
        log = data.__dict__['InstrumentID'] + ' 发单错误回报，错误代码：' + str(error.__dict__['ErrorID']) + ',   错误信息：' + str(
            error.__dict__['ErrorMsg'])
        # self.put_log_event(log)
        lc.loger_order.info('onRspOrderInsert')
        lc.loger_error.info(log)
        lc.loger_order.info(data.__dict__)

    def onErrRtnOrderInsert(self, data, error):
        """发单错误回报（交易所）"""
        log = data.__dict__['InstrumentID'] + '发单错误回报，错误代码：' + str(error.__dict__['ErrorID']) + ',   错误信息：' + str(
            error.__dict__['ErrorMsg'])
        # self.put_log_event(log)
        lc.loger_error.info('onErrRtnOrderInsert')
        lc.loger_error.info(log)
        lc.loger_error.info(data.__dict__)

    def onRspError(self, error, n, last):
        """错误回报"""
        log = '交易错误回报，错误代码：' + str(error.__dict__['ErrorID']) + ',   错误信息：' + str(error.__dict__['ErrorMsg'])
        # self.put_log_event(log)
        lc.loger_error.info('onRspError')
        lc.loger_error.info(log)
        lc.loger_error.info(error.__dict__)
    # ----------------------------------------------------------------------
    def onRspOrderAction(self, data, error, n, last):
        """撤单错误（柜台）"""
        log = '撤单错误回报，错误代码：' + str(error.__dict__['ErrorID']) + ',   错误信息：' + str(error.__dict__['ErrorMsg'])
        # self.put_log_event(log)
        lc.loger_error.info('onRspOrderAction')
        lc.loger_error.info(log)
        lc.loger_error.info(data.__dict__)
    # ----------------------------------------------------------------------
    def onErrRtnOrderAction(self, data, error):
        """撤单错误回报（交易所）"""
        event = Event(type_=EVENT_LOG)
        log = data['合约代码'] + '  撤单错误回报，错误代码：' + str(error.__dict__['ErrorID']) + ',   错误信息：' + str(
            error.__dict__['ErrorMsg'])
        event.dict_['log'] = log
        # self.__eventEngine.put(event)
        lc.loger_error.info('onErrRtnOrderAction')
        lc.loger_error.info(log)
        lc.loger_error.info(data.__dict__)

    def getInstrument(self):
        """查询合约"""
        self.__reqid = self.__reqid + 1
        self.t.ReqQryInstrument()
    def getAccount(self):
        """查询账户"""
        self.__reqid = self.__reqid + 1
        self.t.ReqQryTradingAccount(self.__brokerid , self.__userid )
    # ----------------------------------------------------------------------
    def getPosition(self):
        """查询持仓"""
        self.__reqid = self.__reqid + 1
        self.t.ReqQryInvestorPosition(self.__brokerid , self.__userid )

    def sendorder(self, instrumentid, price, vol, direction, offset):
        """发单"""
        self.__reqid = self.__reqid + 1
        self.__orderref = self.__orderref + 1
        # 限价
        self.t.ReqOrderInsert(BrokerID=self.__brokerid,
                              InvestorID=self.__userid,
                              InstrumentID=instrumentid,
                              OrderRef='{0:>12}'.format(self.__orderref),
                              UserID=self.__userid,
                              OrderPriceType=OrderPriceTypeType.LimitPrice,
                              Direction=direction,
                              CombOffsetFlag=offset,
                              CombHedgeFlag=HedgeFlagType.Speculation.__char__(),
                              LimitPrice=price,
                              VolumeTotalOriginal=vol,
                              TimeCondition=TimeConditionType.GFD,
                              VolumeCondition=VolumeConditionType.AV,
                              MinVolume=1,
                              ForceCloseReason=ForceCloseReasonType.NotForceClose,
                              ContingentCondition=ContingentConditionType.Immediately)
        return self.__orderref
        # 返回订单号，便于某些算法进行动态管理
        # OrderPriceType--LimitPrice 限价单
        # CombHedgeFlag--投机套保标记，默认投机单Speculation
        # TimeConditionType是一个有效期类型类型#当日有效--GFD
        # VolumeConditionType是一个成交量类型类型#任何数量--VolumeConditionType.AV
        # ContingentConditionType是一个触发条件类型，#立即ContingentConditionType.Immediately

    def buy(self, symbol, price, vol):  # 买开多开
        direction = DirectionType.Buy
        offset = OffsetFlagType.Open.__char__()
        self.sendorder(symbol, price, vol, direction, offset)

    def sell(self, symbol, price, vol):  # 多平
        direction = DirectionType.Sell
        offset = OffsetFlagType.Close.__char__()
        self.sendorder(symbol, price, vol, direction, offset)

    def selltoday(self, symbol, price, vol):  # 平今多
        direction = DirectionType.Sell
        offset = OffsetFlagType.CloseToday.__char__()
        self.sendorder(symbol, price, vol, direction, offset)

    def short(self, symbol, price, vol):  # 卖开空开
        direction = DirectionType.Sell
        offset = OffsetFlagType.Open.__char__()
        self.sendorder(symbol, price, vol, direction, offset)

    def cover(self, symbol, price, vol):  # 空平
        direction = DirectionType.Buy
        offset = OffsetFlagType.Close.__char__()
        self.sendorder(symbol, price, vol, direction, offset)

    def covertoday(self, symbol, price, vol):  # 平今空
        direction = DirectionType.Buy
        offset = OffsetFlagType.CloseToday.__char__()
        self.sendorder(symbol, price, vol, direction, offset)

    # ----------------------------------------------------------------------
        # tmp["合约代码"] = var["InstrumentID"]
        # tmp["交易所代码"] = var["ExchangeID"]
        # tmp["报单引用"] = var["OrderRef"]
        # tmp["买卖方向"] = var["Direction"]
        # tmp["组合开平标志"] = var["CombOffsetFlag"]
        # tmp["价格"] = var["LimitPrice"]
        # tmp["数量"] = var["VolumeTotalOriginal"]
        # tmp["请求编号"] = var["RequestID"]
        # tmp["本地报单编号"] = var["OrderLocalID"]
        # tmp["报单编号"] = var["OrderSysID"]
        # tmp["今成交数量"] = var["VolumeTraded"]
        # tmp["剩余数量"] = var["VolumeTotal"]
        # tmp["报单日期"] = var["InsertDate"]
        # tmp["委托时间"] = var["InsertTime"]
        # tmp["前置编号"] = var["FrontID"]
        # tmp["会话编号"] = var["SessionID"]
        # tmp["状态信息"] = var["StatusMsg"]
        # tmp["序号"] = var["SequenceNo"]
    def cancelOrder(self, order):
        """撤单"""
        # lc.loger.info(order)
        self.__reqid = self.__reqid + 1
        self.t.ReqOrderAction(BrokerID=self.__brokerid,
                              InvestorID=self.__userid,
                              OrderRef=order['OrderLocalID'],
                              FrontID=int(order['FrontID']),
                              SessionID=int(order['SessionID']),
                              OrderSysID=order['OrderSysID'],
                              ActionFlag=ActionFlagType.Delete,
                              ExchangeID=order["ExchangeID"],
                              InstrumentID=order['InstrumentID'])
