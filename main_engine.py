# encoding: UTF-8
"""
CTP的底层接口来自'HaiFeng'-PY-AT
简化封装采用VN.PY的结构
"""
import datetime
import re
import time
import traceback

import pandas as pd
import tick_fifteen as tfif
from py_ctp.eventEngine import *
from py_ctp.eventType import *

from md_api import MdApi
from td_api import TdApi

import threading
import logconfig as lc
import tracemalloc
import gc
import config as cf
import crawler as cl
import objgraph as og
tracemalloc.start()
########################################################################

class MainEngine:
    """主引擎，负责对API的调度"""

    #----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        self.last_get_data_time = 0 #最后获取数据时间
        self.last_show_market_data_time = {} #最后显示获取数据时间

        self.d=[]
        self.lastTime = time.time()//900*900   #初始化当前时间
        self.ee = EventEngine()         # 创建事件驱动引擎
        self.md = MdApi(self.ee)    # 创建API接口
        self.td = TdApi(self.ee)
        self.ee.start()                 # 启动事件驱动引擎
        self.ee.register(EVENT_LOG, self.p_log)  # 打印测试
        self.ee.register(EVENT_INSTRUMENT, self.insertInstrument)
        self.list_instrument = []#保存合约资料
        self.ee.register(EVENT_MARKETDATA, self.insertMarketData)
        self.list_marketdata = []#保存合约资料
        self.ee.register(EVENT_INSTRUMENT_MAGIN_RATE,self.insertInstrumentMarginRate)
        self.list_marginRate = []#保存合约保证金率

        # 循环查询持仓和账户相关
        self.countGet = 0  # 查询延时计数
        self.lastGet = 'Position'  # 上次查询的性质，先查询账户
        #持仓和账户
        self.ee.register (EVENT_ACCOUNT,self.account)
        self.ee.register (EVENT_POSITION,self.position)
        #持仓和账户数据
        self.dict_account = None
        self.dict_position = []
        #持仓和账户数据确认
        self.dict_account_time = 0
        self.dict_position_time = 0
        #订阅主力：
        self.brunt = {'rb':[]}
        #self.brunt_settle = 1
        self.brunt_sub_settle = 1
        self.brunt_order_settle = 1
        # 委托事件
        self.ee.register (EVENT_ORDER,self.order)
        self.dict_order={}#报单数据
        # 成交事件
        self.ee.register (EVENT_TRADE,self.trader)
        self.dict_trade={}#成交数据
        #下单列表
        self.order_list = []

        self.account_and_position_engine_mutex = threading.Lock()
        self.not_cancel_order_list_mutex = threading.Lock()
        self.tick_fifteen = tfif.TickFifteen(self)
        self.account_and_position_engine_run_thread = True
        self.crawler_thread = Thread(target = self.crawler_start)
        #self.ee.register(EVENT_TIMER, self.tick_fifteen.mongo_engine_start)
    #----------------------------------------------------------------------
    def login(self):
        """登陆"""
        self.md.login()
        self.td.login()


    def logout(self):

        self.md.logout()
        self.td.logout()
    def release(self):
        self.ee.stop()
        self.account_and_position_engine_run_thread = False
        self.tick_fifteen.Release()
        self.tick_fifteen.main_engine = None
        self.tick_fifteen = None
        self.md.release()
        self.td.release()


    def p_log(self,event):
        lc.loger.info(event.dict_['log'])
    def getCommoditybyInstrumentID(self,InstrumentID):
        merchandise = re.findall('^[a-zA-Z]+',InstrumentID)
        if len(merchandise) == 0 :
            return None
        commodity = merchandise.pop(0)
        return commodity
    def deepdata(self,event):
        edata = event.dict_['data']
        dd = {}
        dd['InstrumentID'] =edata['InstrumentID']

        st = self.Time2DateString(time.time())

        stime = str.split(st)[0] + ' ' + edata['UpdateTime']
        dd['Time'] = stime
        dd['Ts'] = self.datestr2num(stime)
        dd['Price']=edata['LastPrice']
        instrumentID = edata['InstrumentID']
        commodity = self.getCommoditybyInstrumentID(edata['InstrumentID'])
        dd['Commodity']= commodity
        now_time = time.time()
        self.last_get_data_time = now_time
        #lc.loger.info(threading.current_thread())
        if instrumentID not in self.last_show_market_data_time:
            self.last_show_market_data_time[instrumentID] = 0
        if self.last_show_market_data_time[instrumentID] <= now_time - 60:
            lc.loger_market_data.info(dd)
            self.last_show_market_data_time[instrumentID] = now_time
        try:
            self.tick_fifteen.insertTick(dd)
        except:
            traceback.print_exc()
            lc.loger.info("insert")
            raise Exception("insert")



    def Time2DateString(self, s ):
        return time.strftime("%Y%m%d %H:%M:%S", time.localtime( float(s) ) )


    def datestr2num(self,s):
        #toordinal()将时间格式字符串转为数字
        strptime = datetime.datetime.strptime(s, '%Y%m%d %H:%M:%S')
        ans_time = time.mktime(strptime.timetuple())
        return ans_time
    def DepthMarketDataField(self, var):
        tmp = {}
        tmp["交易日"] = var["TradingDay"]
        tmp["合约代码"] = var["InstrumentID"]
        tmp["交易所代码"] = var["ExchangeID"]
        tmp["最新价"] = var["LastPrice"]
        tmp["昨收盘"] = var["PreClosePrice"]
        tmp["昨持仓量"] = var["PreOpenInterest"]
        tmp["今开盘"] = var["OpenPrice"]
        tmp["最高价"] = var["HighestPrice"]
        tmp["最低价"] = var["LowestPrice"]
        tmp["成交量"] = var["Volume"]
        tmp["成交金额"] = var["Turnover"]
        tmp["持仓量"] = var["OpenInterest"]
        tmp["今收盘"] = var["ClosePrice"]
        tmp["本次结算价"] = var["SettlementPrice"]
        tmp["时间"] = var["UpdateTime"]
        tmp["申买价一"] = var["BidPrice1"]
        tmp["申买量一"] = var["BidVolume1"]
        tmp["申卖价一"] = var["AskPrice1"]
        tmp["申卖量一"] = var["AskVolume1"]
        tmp["当日均价"] = var["AveragePrice"]
        lc.loger.info(var)
        return tmp


    def insertInstrument(self,  event):
        """插入合约对象"""
        data = event.dict_['data']
        last = event.dict_['last']
        self.list_instrument.append(data)
        if last:#最后一条数据
            # 将查询完成的合约信息保存到本地文件，今日登录可直接使用不再查询
            event = Event(type_=EVENT_LOG)
            log = '合约信息查询完成'
            event.dict_['log'] = log
            self.ee.put(event)
            lc.loger.info("insertInstrument")
            lc.loger.info(data)
            # self.ee.register(EVENT_TIMER, self.getAccountPosition)
            # ret = pd.DataFrame(self.list_instrument)
            # ret = ret.set_index('InstrumentID')
            # ret.to_pickle('Instrument')
            # event = Event(type_=EVENT_LOG)
            # log = '合约信息已经保存'
            # event.dict_['log'] = log
            # self.ee.put(event)
            # lc.loger.info(ret)

    def insertMarketData(self, event):
        data = event.dict_['data']
        last = event.dict_['last']
        self.list_marketdata.append(data)
        if last:
            event = Event(type_=EVENT_LOG)
            log = '合约截面数据查询完成'
            event.dict_['log'] = log
            self.ee.put(event)
            lc.loger.info("insertMarketData")
            lc.loger.info(data)

            event = Event(type_=EVENT_LOG)
            log = '合约截面数据已经保存'
            event.dict_['log'] = log
            self.ee.put(event)

           # self.getInstrumentMarginRate('rb1801')
            time.sleep(1)
            self.calBrunt()#计算主力合约



            #self.ee.register(EVENT_TIMER, self.getAccountPosition)
    def getInstrumentMarginRate(self):
        print(2)
        instrumentID = None
        flag = False
        for commodity in self.brunt.keys():
            for i in range(len(self.brunt[commodity])):
                if 'LongMarginRatioByMoney' not in self.brunt[commodity][i]:
                    instrumentID = self.brunt[commodity][i]['InstrumentID']
                    flag = True
                    break
            if flag == True:
                break
        if instrumentID is not None and flag == True:
            self.td.getInstrumentMarginRate(instrumentID)
        else:
            print(self.brunt)
            event = Event(type_=EVENT_LOG)
            log = '合约保证金率数据查询完成'
            event.dict_['log'] = log
            self.ee.put(event)
            print("instrumentMarginRate")
            self.regist_and_subscribe_and_start_thread()

    def insertInstrumentMarginRate(self, event):
        print(3)
        data = event.dict_['data']
        last = event.dict_['last']
        # self.list_marginRate.append(data)
        commodity = self.getCommoditybyInstrumentID(data['InstrumentID'])
        for i in range(len(self.brunt[commodity])):
            if self.brunt[commodity][i]['InstrumentID'] == data['InstrumentID']:
                self.brunt[commodity][i]['LongMarginRatioByMoney'] = data['LongMarginRatioByMoney']
                self.brunt[commodity][i]['ShortMarginRatioByMoney'] = data['ShortMarginRatioByMoney']
        time.sleep(10)
        self.getInstrumentMarginRate()





    def calBrunt(self):#计算主力合约，在下单的时候要用，涨跌停板价是市价下单用
        brunt_keys_list = list(self.brunt.keys())
        for i in range(len(brunt_keys_list)):
            one_instrument_list = []
            for j in range(len(self.list_instrument)):
                if self.list_instrument[j]['ProductID'] == brunt_keys_list[i]:
                    new_one_instrument = {}
                    new_one_instrument['InstrumentID'] = self.list_instrument[j]['InstrumentID']
                    new_one_instrument['InstrumentName'] = self.list_instrument[j]['InstrumentName']
                    new_one_instrument['VolumeMultiple'] = self.list_instrument[j]['VolumeMultiple']
                    new_one_instrument['ExchangeID'] = self.list_instrument[j]['ExchangeID']
                    new_one_instrument['PriceTick'] = self.list_instrument[j]['PriceTick']

                    for k in range(len(self.list_marketdata)):
                        if self.list_marketdata[k]['InstrumentID'] == new_one_instrument['InstrumentID']:
                            new_one_instrument['UpperLimitPrice'] = self.list_marketdata[k]['UpperLimitPrice']
                            new_one_instrument['LowerLimitPrice'] = self.list_marketdata[k]['LowerLimitPrice']
                            new_one_instrument['OpenInterest'] = self.list_marketdata[k]['OpenInterest']
                    one_instrument_list.append(new_one_instrument)
                    if len(one_instrument_list)>0:
                        one_instrument_list = sorted(one_instrument_list,key=lambda one:one['OpenInterest'],reverse=True)
                        one_instrument_list = one_instrument_list[:self.brunt_sub_settle]
                    if cf.test_reverse == True:
                        one_instrument_list = sorted(one_instrument_list,key=lambda one:one['OpenInterest'],reverse=False)
            self.brunt[brunt_keys_list[i]] = one_instrument_list
            time.sleep(2)
            print(1)
            self.getInstrumentMarginRate()
        # self.regist_and_subscribe_and_order()
        #zlinfo["合约名称"] =var_I.ix[ index_1]["InstrumentName"]
        # zlinfo['合约代码'] = index_1
        # zlinfo['市场代码'] = var_I.ix[ index_1]['ExchangeID']
        # zlinfo['合约乘数'] = var_I.ix[ index_1]['VolumeMultiple']
        # zlinfo['合约跳价'] =var_I.ix[ index_1]['PriceTick']
        # zlinfo['涨停板价'] = var_M.ix[ index_1]['UpperLimitPrice']
        # zlinfo['跌停板价'] = var_M.ix[ index_1]['LowerLimitPrice']
        # zlinfo['主力持仓'] = var_M.ix[ index_1]['OpenInterest']
        # zlinfo['次月合约'] = index_2
        # zlinfo['次月持仓'] = var_M.ix[ index_2]['OpenInterest']
        # zlinfo['次月涨停'] = var_M.ix[ index_2]['UpperLimitPrice']
        # zlinfo['次月跌停'] = var_M.ix[ index_2]['LowerLimitPrice']
    def regist_and_subscribe_and_start_thread(self):
        for i in range(len(list(self.brunt.keys()))):
            one_product = self.brunt[(list(self.brunt.keys()))[i]]
            for j in range(min(len(one_product),self.brunt_sub_settle)):
                #注册TICK行情
                self.ee.register(EVENT_MARKETDATA_CONTRACT + one_product[j]['InstrumentID'], self.deepdata)
                #订阅TICK行情
                self.md.subscribe(one_product[j]['InstrumentID'])
                time.sleep(0.1)
        ti_fi = self.tick_fifteen

        # order = {'UserForceClose': 0, 'VolumeCondition': 'AV', 'TimeCondition': 'GFD', 'InstallID': 1, 'CancelTime': '', 'GTDDate': '', 'ActiveTime': '', 'LimitPrice': 3853.0, 'IPAddress': '', 'InsertDate': '20171213', 'OrderType': '', 'SuspendTime': '', 'VolumeTotalOriginal': 100, 'ContingentCondition': 'Immediately', 'UpdateTime': '', 'CurrencyID': '', 'BranchID': '', 'SessionID': 675190686, 'OrderSubmitStatus': 'Accepted', 'NotifySequence': 1, 'VolumeTotal': 100, 'ForceCloseReason': 'NotForceClose', 'UserProductInfo': '', 'SettlementID': 1, 'IsAutoSuspend': 0, 'MinVolume': 1, 'CombOffsetFlag': '1', 'ExchangeID': 'SHFE', 'ActiveUserID': '', 'Direction': 'Sell', 'ActiveTraderID': '9999cac', 'AccountID': '', 'InsertTime': '21:17:11', 'OrderStatus': 'NoTradeQueueing', 'MacAddress': '', 'StopPrice': 0.0, 'ExchangeInstID': 'rb1805', 'BrokerOrderSeq': 31201, 'BrokerID': '9999', 'TraderID': '9999cac', 'StatusMsg': '未成交', 'UserID': '108483', 'RelativeOrderSysID': '', 'RequestID': 0, 'OrderLocalID': '       33585', 'TradingDay': '20171214', 'IsSwapOrder': 0, 'ClientID': '9999108463', 'OrderRef': '           3', 'InstrumentID': 'rb1805', 'SequenceNo': 28561, 'InvestUnitID': '', 'ZCETotalTradedVolume': 0, 'ParticipantID': '9999', 'CombHedgeFlag': '1', 'VolumeTraded': 0, 'OrderPriceType': 'LimitPrice', 'BusinessUnit': '9999cac', 'OrderSysID': '       18985', 'InvestorID': '108483', 'FrontID': 1, 'ClearingPartID': '', 'OrderSource': ''}
        # self.cancelOrder(order)
        # time.sleep(1)
        ti_fi.order_engine_start()#启动下单线程
        ti_fi.mongo_engine_start()#启动mongo储存线程
        ti_fi.account_and_position_engine_start() #启动获取account信息和position信息线程

    def account_and_position_start(self):
        while self.account_and_position_engine_run_thread:
            lc.loger2.info("账户信息更新线程正常运行中......"+str(threading.current_thread()))
            self.account_and_position_engine_mutex.acquire()
            try:
                self.getAccountPosition()
            except:
                lc.loger2.error("账户信息更新线程异常中止"+str(threading.current_thread()))
                traceback.print_exc()
                msg = traceback.format_exc()
                lc.loger2.error(msg)
                raise Exception("账户信息更新线程异常中止"+str(threading.current_thread()))
            self.account_and_position_engine_mutex.release()
            time.sleep(1)
        else:
            lc.loger2.info("账户信息更新线程正常停止中......"+str(threading.current_thread()))
    def account(self,event):#处理账户事件数据
        self.dict_account  = event.dict_['data']
        lc.loger_account_position.info("account")
        lc.loger_account_position.info(self.TradingAccountField(event.dict_['data']))
        lc.loger_cash_account.info('现在资金为：')
        lc.loger_cash_account.info(self.dict_account['CurrMargin'] + self.dict_account['Available'] )
        self.dict_account_time = time.time()
        self.tick_fifteen.dict_account = self.dict_account
    def TradingAccountField(self,var):
        tmp = {}
        tmp["CurrMargin"] = var["CurrMargin"]
        tmp["Commission"] = var["Commission"]
        tmp["Balance"] = var["Balance"]
        tmp["Available"] = var["Available"]
        tmp["WithdrawQuota"] = var["WithdrawQuota"]
        return tmp
    def position(self, event):#处理持仓事件数据
        data = self.InvestorPositionField(event.dict_['data'])
        last = event.dict_['last']
        self.dict_position.append(event.dict_['data'])
        lc.loger_account_position.info("position")
        lc.loger_account_position.info(data)
        if last:
            self.tick_fifteen.dict_position = self.dict_position
            self.dict_position = []
            self.dict_position_time = time.time()







    def InvestorPositionField(self,var):
        tmp={}
        tmp["InstrumentID"]=var["InstrumentID"]
        tmp["PosiDirection"]=var["PosiDirection"]
        tmp["YdPosition"]=var["YdPosition"]
        tmp["Position"]=var["Position"]
        tmp["LongFrozen"]=var["LongFrozen"]
        tmp["ShortFrozen"]=var["ShortFrozen"]
        tmp["OpenVolume"]=var["OpenVolume"]
        tmp["CloseVolume"]=var["CloseVolume"]
        tmp["OpenCost"]=var["OpenCost"]
        tmp["TodayPosition"]=var["TodayPosition"]
        return tmp


    def order(self, event):
        data = self.OrderField(event.dict_['data'])
        self.tick_fifteen.save_or_update_order(event.dict_['data'])
        lc.loger_order.info(data)
        self.save_or_update_order_status(event.dict_['data'])
    def save_or_update_order_status(self,order):
        self.not_cancel_order_list_mutex.acquire()
        flag = False
        for i in range(len(self.order_list)):
            if self.order_list[i]['FrontID'] == order['FrontID'] and self.order_list[i]['SessionID'] == order['SessionID'] and self.order_list[i]['OrderRef'] == order['OrderRef']:
                self.order_list[i] = order
                flag = True
                break
        if flag == False:
            self.order_list.append(order)
        self.not_cancel_order_list_mutex.release()
    def find_not_cancel_instrumentID(self):
        self.not_cancel_order_list_mutex.acquire()
        not_cancel_order_list = []
        # find = {'InstrumentID':instrumentID,'OrderStatus':'NoTradeQueueing'}
        for i in range(len(self.order_list)):
            if self.order_list[i]['OrderStatus'] == 'NoTradeQueueing':
                not_cancel_order_list.append(self.order_list[i])
        self.not_cancel_order_list_mutex.release()
        return not_cancel_order_list
    def OrderField(self, var):
        tmp = {}
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
        tmp["InstrumentID"] = var["InstrumentID"]
        tmp["OrderRef"] = var["OrderRef"]
        tmp["Direction"] = var["Direction"]
        tmp["StatusMsg"] = var["StatusMsg"]
        tmp["OrderStatus"] = var["OrderStatus"]

        return tmp

    def trader(self, event):
        data = self.TradeField(event.dict_['data'])
        self.tick_fifteen.save_or_update_trader(event.dict_['data'])
        lc.loger_trader.info(data)


    def TradeField(self, var):
        tmp = {}
        # tmp["合约代码"] = var["InstrumentID"]
        # tmp["报单引用"] = var["OrderRef"]
        # tmp["交易所代码"] = var["ExchangeID"]
        # tmp["成交编号"] = var["TradeID"]
        # tmp["买卖方向"] = var["Direction"]
        # tmp["报单编号"] = var["OrderSysID"]
        # tmp["合约在交易所的代码"] = var["ExchangeInstID"]
        # tmp["开平标志"] = var["OffsetFlag"]
        # tmp["价格"] = var["Price"]
        # tmp["数量"] = var["Volume"]
        # tmp["成交时期"] = var["TradeDate"]
        # tmp["成交时间"] = var["TradeTime"]
        # tmp["本地报单编号"] = var["OrderLocalID"]
        # tmp["交易日"] = var["TradingDay"]
        tmp["InstrumentID"] = var["InstrumentID"]
        tmp["Direction"] = var["Direction"]
        tmp["OffsetFlag"] = var["OffsetFlag"]
        tmp["Price"] = var["Price"]
        tmp["Volume"] = var["Volume"]
        return tmp

    def getAccountPosition(self):
        """循环查询账户和持仓"""
        self.countGet = self.countGet + 1
        # 每5秒发一次查询
        if self.countGet > 2:
            self.countGet = 0  # 清空计数

            if self.lastGet == 'Account':
                self.getPosition()
                self.lastGet = 'Position'
            else:
                self.getAccount()
                self.lastGet = 'Account'
    def getAccount(self):
        """查询账户"""
        self.td.getAccount()
    # ----------------------------------------------------------------------
    def getPosition(self):
        """查询持仓"""
        self.td.getPosition()

    def buy(self, symbol, price, vol):  # 买开多开
        self.td.buy(symbol, price, vol)

    def sell(self, symbol, price, vol):  # 多平
        self.td.sell(symbol, price, vol)

    def selltoday(self, symbol, price, vol):  # 平今多

        self.td.selltoday(symbol, price, vol)

    def short(self, symbol, price, vol):  # 卖开空开

        self.td.short(symbol, price, vol)

    def cover(self, symbol, price, vol):  # 空平

        self.td.cover(symbol, price, vol)

    def covertoday(self, symbol, price, vol):  # 平今空

        self.td.covertoday(symbol, price, vol)

    def cancelOrder(self, order):#撤单

        self.td.cancelOrder(order)

    def crawler_start(self):
        t = time.time()
        iost = self.tick_fifteen.Time2ISOString(t)
        io = str.split(iost)
        if io[1]<"20:30:00" and io[1]>"19:00:00":
            c = cl.DataCrawler()
            c.start()
        else:
            time.sleep(1800)

# 直接运行脚本可以进行测试
if __name__ == '__main__':
    import sys
    from PyQt5.QtCore import QCoreApplication
    app = QCoreApplication(sys.argv)

    try:

        main = MainEngine()
        main.crawler_thread.start()
        #main.login()
        while True:
            i = 0

            if main.last_get_data_time>=time.time()-30:
                lc.loger.info(threading.current_thread())
                lc.loger.info("上次获取数据时间：")
                lc.loger.info(main.last_get_data_time)
                lc.loger.info("现在时间：")
                lc.loger.info(time.time())
            while main.last_get_data_time<time.time()-30:
            # while True:
                # lc.loger.info("logouting")
                # main.logout()
                #
                # lc.loger.info("logouted")
                # lc.loger.info("disconnecting")
                main.release()
                gc.collect()
                # snapshot = tracemalloc.take_snapshot()
                # top_stats = snapshot.statistics('lineno')
                # for stat in top_stats[:5]:
                #     print(stat)
                print("==========================================================")
                # lc.loger.info("disconnected")
                main = MainEngine()
                lc.loger.info("loginning")
                main.login()
                lc.loger.info("logined")
                i = i + 1
                lc.loger.info(i)
                og.show_growth()
                og.show_chain(
                    og.find_backref_chain(
                        og.by_type('tuple'),
                        og.is_proper_module
                    ),
                    filename='obj_chain.dot'
                )
                # og.show_backrefs(og.by_type('tuple')[0], extra_ignore=(id(gc.garbage),),  max_depth = 10, filename = 'tuple.dot')
                time.sleep(main.brunt_sub_settle*20)
            time.sleep(10)

    except:
        traceback.print_exc()
        raise Exception("a")

#    main.logout()
#    main.disconnect()
    app.exec_()