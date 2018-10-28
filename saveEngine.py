from threading import Thread
from pymongo import MongoClient
import datetime
import time
import threading
import traceback
import logconfig as lc
# 第三方模块
from PyQt5.QtCore import QTimer
import logging
class MongoEngine(object):
    def __init__(self,mongo_data,orinal_data):
        self.mongo_data = mongo_data
        self.orinal_data = orinal_data
        self.run_thread = True
        # mongoDB
        self.conn = MongoClient('localhost', 27017)
        self.db = self.conn.mydb  #连接mydb数据库，没有则自动创建
        self.fifteen = self.db.fifteen
        self.collection = self.db.daily
        self.order = self.db.order
        self.trader = self.db.trader

        # # 事件处理线程
        # self.__thread = Thread(target = self.__run)

        # 计时器，用于触发计时器事件
        # self.__timer = QTimer()
        # self.__timer.timeout.connect(self.onTimer)
        self.mutex = threading.Lock()
        lc.loger.info("mongo timer set")
    def save_or_update_order(self,order):
        find = {'FrontID':order['FrontID'],'SessionID':order['SessionID'],'ExchangeID':order['ExchangeID'],'InstrumentID':order['InstrumentID'],'OrderRef':order['OrderRef']}
        data = self.order.find_one(find)

        if data is None:
            self.order.insert(order)
        else:

            self.order.update(find, {"$set":order})

    def save_or_update_trader(self,trade):
        find = {'ExchangeID':trade['ExchangeID'],'OrderSysID':trade['OrderSysID']}
        data = self.trader.find_one(find)

        if data is None:
            self.trader.insert(trade)
        else:

            self.trader.update(find, {"$set":trade})
    def onTimer(self):
        while self.run_thread:
            lc.loger2.info("mongo存储线程正常运行中......"+str(threading.current_thread()))
            self.mutex.acquire()
            try:
                self.generateFifteen()
                self.save2mongo()
            except:
                lc.loger2.error("mongo存储线程异常中止"+str(threading.current_thread()))
                traceback.print_exc()
                msg = traceback.format_exc()
                lc.loger2.error(msg)
                raise Exception("mongo存储线程异常中止"+str(threading.current_thread()))
            self.mutex.release()
            time.sleep(5)
        else:
            lc.loger2.info("mongo存储线程正常停止中......"+str(threading.current_thread()))
    def start(self):
        lc.loger.info(threading.current_thread())
        lc.loger.info("start mongo_timer")
        self.onTimer()
        #self.__timer.start(10000)
    def Release(self):
        self.conn.close()
        self.conn = None
        self.run_thread = False

    #
    # def __run(self):
    #     self.generateFifteen()
    #     self.save2mongo()

    def save2mongo(self):
        i = 0
        while i < len(self.mongo_data):

            find = {'commodity':self.mongo_data[i]['commodity'],'instrumentID':self.mongo_data[i]['instrumentID'],'time':self.mongo_data[i]['time']}

            data = self.fifteen.find_one(find)

            if data is None:
                self.fifteen.insert(self.mongo_data[i])
            else:
                self.mongo_data[i]['opend'] = data['opend']
                self.mongo_data[i]['high'] = max(self.mongo_data[i]['high'],data['high'])
                self.mongo_data[i]['low'] = min(self.mongo_data[i]['low'],data['low'])
                self.fifteen.update(find, {"$set":self.mongo_data[i]})

            tls = self.ISOString2Time(self.mongo_data[i]['time'])

            time = list(self.orinal_data[self.mongo_data[i]['commodity']][self.mongo_data[i]['instrumentID']].keys())

            for j in range(len(time)):

                tln = self.ISOString2Time(time[j])
                if tln + 60*60 <= tls:
                    self.orinal_data[self.mongo_data[i]['commodity']][self.mongo_data[i]['instrumentID']].pop(time[j])
            self.mongo_data.remove(self.mongo_data[i])


    def ISOString2Time(self, s ):
        d=datetime.datetime.strptime(s,"%Y%m%d %H:%M:%S")
        return time.mktime(d.timetuple())

    def Time2ISOString(self, s ):
        return time.strftime("%Y%m%d %H:%M:%S", time.localtime( float(s) ) )

    def getLastFifteen(self,last_n,commodity,instrumentID):
        find = {'commodity':commodity,'instrumentID':instrumentID}
        return self.fifteen.find(find).sort([("time",-1)]).limit(last_n) #要改的地方，找最新的条数
    def search_130(self,commodity,instrumentID):
        mongo_find_data = self.getLastFifteen(130,commodity,instrumentID)
        mongo_data = self.com_data_deal(mongo_find_data)
        mongo_data.reverse()
        return mongo_data


    def com_data_deal(self,mongo_data):
        a = []
        for row in mongo_data:
            #print(row)
            a.append(row)
        return a
    def generateFifteen(self):
    #    lc.loger.info(self.orinal_data)
    #    lc.loger.info(self.orinal_data.keys())
        for cindex,commodity in enumerate(self.orinal_data.keys()):
    #       lc.loger.info(commodity)
    #       lc.loger.info(self.orinal_data[commodity])
            for iindex,instrumentID in enumerate(self.orinal_data[commodity].keys()):
                for tindex,time in enumerate(self.orinal_data[commodity][instrumentID].keys()):
                    a = {}
                    a['opend'] = self.orinal_data[commodity][instrumentID][time][0]['Price']
                    a['close'] = self.orinal_data[commodity][instrumentID][time][len(self.orinal_data[commodity][instrumentID][time])-1]['Price']
                    minValue = self.orinal_data[commodity][instrumentID][time][0]['Price']
                    maxValue = self.orinal_data[commodity][instrumentID][time][0]['Price']
                    for i in range(len(self.orinal_data[commodity][instrumentID][time])):
                        minValue = min(self.orinal_data[commodity][instrumentID][time][i]['Price'],minValue)
                        maxValue = max(self.orinal_data[commodity][instrumentID][time][i]['Price'],maxValue)
                    a['low'] = minValue
                    a['high'] = maxValue
                    a['commodity'] = commodity
                    a['instrumentID'] = instrumentID
                    a['time'] = time
                    flag = False
                    for i in range(len(self.mongo_data)):
                        if self.mongo_data[i]['time'] == a['time'] and self.mongo_data[i]['instrumentID'] == a['instrumentID']:
                            self.mongo_data[i]['low'] = min(self.mongo_data[i]['low'],a['low'])
                            self.mongo_data[i]['high'] = max(self.mongo_data[i]['high'],a['high'])
                            self.mongo_data[i]['close'] = a['close']
                            flag = True
                            break
                    if flag == False:
                        self.mongo_data.append(a)
    def findLast(self,dict,last_count):
        mongo_data = self.collection.find(dict).sort([("time",-1)]).limit(last_count)
        return self.com_data_deal(mongo_data)

    def find_selective(self,dict):
        mongo_data = self.collection.find(dict)
        return self.com_data_deal(mongo_data)


    def getAllData(self):
        mongo_data = self.collection.find()
        return self.com_data_deal(mongo_data)

    def update_chance_type(self,dict,chanceType):
        self.collection.update(dict,{'$set' : {'chanceType':chanceType}})

    def find_one(self,dict):
        return self.collection.find_one(dict)


    def find_post_one(self,instrumentID,time):
        list = self.collection.find({'instrumentID':instrumentID,'time':{'$gt':time}}).sort([('time',1)])
        try:
            return list.next()
        except StopIteration:
            return None
    def find_pos_pre_list(self,instrumentID,time,last_count):
        list = self.collection.find({'instrumentID':instrumentID,'time':{'$lte':time}}).sort([('time',-1)]).limit(last_count)
        return self.com_data_deal(list)
if __name__ == '__main__':
    import sys
    from PyQt5.QtCore import QCoreApplication
    app = QCoreApplication(sys.argv)
    orinal_data = {'Time': '20171113 15:22:07', 'InstrumentID': 'rb1801', 'Ts': 1510557727.0, 'Price': 3894.0, 'Commodity': 'rb'}
    main = MongoEngine(mongo_data=[],orinal_data={})
    list1 = main.search_130('rb','rb1801')
    print(list1)
    app.exec_()