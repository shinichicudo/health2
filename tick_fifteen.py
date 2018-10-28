import datetime
import time
import saveEngine as se
import threading
import logconfig as lc
import threadpool
from threading import Thread
import calculate as cc
import math
import tracemalloc
import traceback
import extract_data as ed
import numpy as np
import config as cf
import predict as pd
import predict as ks
from keras.models import load_model
import os
time_slice = {'rb':[['09:00:00','09:15:00'],['09:15:01','09:30:00'],['09:30:01','09:45:00'],['09:45:01','10:00:00'],['10:00:01','10:15:00'],['10:30:00','10:45:00'],
                    ['10:45:01','11:00:00'],['11:00:01','11:15:00'],['11:15:01','11:30:00'],['13:30:00','13:45:00'],['13:45:01','14:00:00'],['14:00:01','14:15:00'],
                    ['14:15:01','14:30:00'],['14:30:01','14:45:00'],['14:45:01','15:00:00'],
                    ['21:00:00','21:15:00'],['21:15:01','21:30:00'],['21:30:01','21:45:00'],['21:45:01','22:00:00'],
                    ['22:00:01','22:15:00'],['22:15:01','22:30:00'],['22:30:01','22:45:00'],['22:45:01','23:00:00']]}
id_list =['hc','bu','zn','ru','al','cu','rb','ni','sn','p','pp','jd','i','jm','v','l','y','c','m','j','cs','ZC','FG','MA','CF','RM','TA','SR']
#主力
order_time = [['14:55:01','15:00:00'],['21:00:00','21:05:00']]
predict_time = [['14:50:00','14:55:00'],['20:40:00','20:50:00']]
class TickFifteen:
    def __init__(self,main_engine):
        self.main_engine = main_engine
        self.d = {}
        self.r = []
        self.one_time_slice_max_order_time = 5
        self.once_order_volume = {}
        self.current_thread = threading.current_thread()
        self.mongo_engine = se.MongoEngine(self.r,self.d)
        self.mongo_thread = None
        self.account_and_position_thread = None
        self.order_thread = None
        self.y_tuple_dict = {}
        self.y_tuple_genernate_mutex = threading.Lock()
        self.inquiry_cal_order_mutex = {}
        self.new_one_time_slice_order_start = True
        self.order_time_section = 600
        self.gnerate_y_tuple_section = 60
        self.last_order_time = 0
        self.dict_account = None
        self.dict_position = None
        self.order_engine_start_run_thread = True
        self.do_order_flag = 1
        self.model = pd.create_keras_model()
        x_test = np.random.rand(64)
        x_test = np.reshape(x_test,[-1,64,1])
        y_test = self.model.predict(x_test)
        print(y_test)

    def mongo_engine_start(self):
        lc.loger.info(threading.current_thread())
        lc.loger.info("start mongo_engine_start")
        self.mongo_thread = Thread(target = self.mongo_engine.start)
        self.mongo_thread.start()
        lc.loger.info("started mongo_engine_start")
    def account_and_position_engine_start(self):
        lc.loger.info(threading.current_thread())
        lc.loger.info("start account_and_position_engine_start")
        self.account_and_position_thread = Thread(target = self.main_engine.account_and_position_start)
        self.account_and_position_thread.start()
        lc.loger.info("started account_and_position_engine_start")
    def order_engine_start(self):
        lc.loger.info(threading.current_thread())
        lc.loger.info("start order_engine_start")
        self.order_thread = Thread(target = self.order_start)
        self.order_thread.start()
    def order_start(self):
        lc.loger.info("started order_engine_start")
        while self.order_engine_start_run_thread:
            lc.loger2.info("下单线程正常运行中......"+str(threading.current_thread()))
            try:
                self.get_instrument_and_start_order()
            except:
                lc.loger2.error("下单线程异常中止"+str(threading.current_thread()))
                traceback.print_exc()
                msg = traceback.format_exc()
                lc.loger2.error(msg)
                raise Exception("下单线程异常中止"+str(threading.current_thread()))
            time.sleep(10)
        else:
            lc.loger2.info("下单线程正常停止中......"+str(threading.current_thread()))
    def get_instrument_and_start_order(self):
        brunt = self.main_engine.brunt
        brunt_keys_list =  list(brunt.keys())
        for i in range(len(brunt_keys_list)):
            one_product = brunt[brunt_keys_list[i]]
            for j in range(min(len(one_product),self.main_engine.brunt_order_settle)):
                self.start_instrumentID_order(brunt_keys_list[i],one_product[j]['InstrumentID'])
                time.sleep(0.1)
    def start_instrumentID_order(self,commodity,instrumentID):
        if self.isYtupleGenerated(commodity,instrumentID) == False and self.isGenerateYtupleTime(commodity):
            self.y_tuple_genernate_mutex.acquire()

            time.sleep(2)
            while(True):
                one_time_slice = self.getTimeSliceByNowTime(commodity)
                if one_time_slice is None:
                    break
                if commodity not in self.d or instrumentID not in self.d[commodity] or one_time_slice not in self.d[commodity][instrumentID]:
                    print("等待行情数据。。。")
                    self.main_engine.md.subscribe(instrumentID)
                    time.sleep(10)
                else:
                    break

            if self.isYtupleGenerated(commodity,instrumentID) == False and self.isGenerateYtupleTime(commodity):
                if self.generate_y_tuple(commodity,instrumentID) == False:
                    return
                self.new_one_time_slice_order_start = True
            self.y_tuple_genernate_mutex.release()
        if self.isOrderTime(commodity) and self.isYtupleGenerated(commodity,instrumentID):
            lc.loger.info(threading.current_thread())
            lc.loger.info("start do_order " + instrumentID)
            self.do_order(commodity,instrumentID)
    def do_order(self,commodity,instrumentID):
        if self.do_order_flag == 0:
            self.inquiry_cal_order(commodity,instrumentID)
            self.do_order_flag = 1
        else:
            self.cancel_order()
            self.do_order_flag = 0
    def isYtupleGenerated(self,commodity,instrumentID):
        if commodity not in self.y_tuple_dict:
            return False
        if instrumentID not in self.y_tuple_dict[commodity]:
            return False
        if 'time' not in self.y_tuple_dict[commodity][instrumentID]:
            return False
        now_time = time.time()
        now_date = self.Time2ISOString(now_time)
        ts = str.split(now_date)
        hms = ts[1]

        for i in range(len(predict_time)):
            if hms<=order_time[i][1] and hms>=predict_time[i][0]:
                td = ts[0] + ' ' + predict_time[i][1]
                if td == self.y_tuple_dict[commodity][instrumentID]['time']:
                    return True
                else:
                    return False
        return False
    def generate_y_tuple(self,commodity,instrumentID):
        if commodity not in self.y_tuple_dict:
            self.y_tuple_dict[commodity] = {}
        if instrumentID not in self.y_tuple_dict[commodity]:
            self.y_tuple_dict[commodity][instrumentID] = {}
        now_time = time.time()
        now_date = self.Time2ISOString(now_time)
        ts = str.split(now_date)
        hms = ts[1]

        tarray = predict_time



        if hms<=tarray[0][1] and hms>=tarray[0][0]:
            tb = ts[0]
            if 'time' not in self.y_tuple_dict[commodity][instrumentID] or self.y_tuple_dict[commodity][instrumentID]['time'] != tb:
                flag1 = self.predictday(self.y_tuple_dict[commodity][instrumentID],True,instrumentID,64,commodity)
                flag2 = self.predictday(self.y_tuple_dict[commodity][instrumentID],True,instrumentID,128,commodity)
                return flag1 and flag2
        if hms<=tarray[1][1] and hms>=tarray[1][0]:
            tb = ts[0]
            if 'time' not in self.y_tuple_dict[commodity][instrumentID] or self.y_tuple_dict[commodity][instrumentID]['time'] != tb:
                flag1 = self.predictday(self.y_tuple_dict[commodity][instrumentID],False,instrumentID,64,commodity)
                flag2 = self.predictday(self.y_tuple_dict[commodity][instrumentID],False,instrumentID,128,commodity)
                return flag1 and flag2



    def predictday(self,dict,flag,instrumentID,count,commodity):
        d = {"instrumentID":instrumentID}
        datas = self.mongo_engine.findLast(d,count)
        if len(datas)<count:
            return False
        day_time = datas[0]['time']
        now_time = time.time()
        now_date = self.Time2ISOString(now_time)
        ts = str.split(now_date)
        if flag == False:
            if day_time != ts[0]:
                return False
        if flag == True:
            if day_time >= ts[0]:
                return False
        data_close = []
        for i in range(len(datas)):
            data_close.append(datas[i]["close"])
        if flag == True:
            pre_time = predict_time[0]
        else:
            pre_time =predict_time[1]
        tarray = pre_time
        td = ts[0] + ' ' + tarray[1]
        if flag == True:
            one_time_slice = self.getTimeSliceByNowTime(commodity)
            last_data = self.d[commodity][instrumentID][one_time_slice][-1]['Price']
            data_close.insert(0,last_data["close"])
            data_close.pop(-1)
        data_c = np.array(data_close)
        data_c = data_c[::-1]
        data_c = np.reshape(data_c,[-1,count])
        if count == 64:
            mean = np.mean(data_c,axis=1)
            mean = np.reshape(mean,[-1,1])
            data_c = (data_c-mean)/mean
            data_c = np.reshape(data_c,[-1,cf.FIX_ROW_LENGTH,1])
            pred = self.model.predict(data_c)
            self.y_tuple_dict[commodity][instrumentID][64] = pred
            self.y_tuple_dict[commodity][instrumentID]['time'] = td
            return True
        if count == 128:
            data_c = np.reshape(data_c,[-1,cf.FIX_ROW_LENGTH,2])
            data_c = np.mean(data_c,axis=2)
            data_c = np.reshape(data_c,[-1,cf.FIX_ROW_LENGTH])
            mean = np.mean(data_c,axis=1)
            mean = np.reshape(mean,[-1,1])
            data_c = (data_c-mean)/mean/2
            data_c = np.reshape(data_c,[-1,cf.FIX_ROW_LENGTH,1])
            pred = self.model.predict(data_c)
            self.y_tuple_dict[commodity][instrumentID][128] = pred
            self.y_tuple_dict[commodity][instrumentID]['time'] = td
            return True




    def inquiry_cal_order(self,commodity,instrumentID):
        if instrumentID not in self.inquiry_cal_order_mutex:
            self.inquiry_cal_order_mutex[instrumentID] = threading.Lock()
        self.inquiry_cal_order_mutex[instrumentID].acquire()
        cashmoney,last_hand,hand_list,other_hands_list = self.inquiry(instrumentID)
        one_time_slice = self.getTimeSliceByNowTime(commodity)
        if commodity not in self.d or instrumentID not in self.d[commodity] or one_time_slice not in self.d[commodity][instrumentID]:
            return
        one_timeslice_list = self.d[commodity][instrumentID][one_time_slice]
        price = one_timeslice_list[len(one_timeslice_list)-1]['Price']
        if cashmoney is not None:
            yp128 = self.y_tuple_dict[commodity][instrumentID][128]
            yp64 = self.y_tuple_dict[commodity][instrumentID][64]
            longMarginRatioByMoney = ed.bail
            shortMarginRatioByMoney = ed.bail
            volumeMultiple = ed.one_hand
            commodity = self.main_engine.getCommoditybyInstrumentID(instrumentID)
            for i in range(len(self.main_engine.brunt[commodity])):
                if self.main_engine.brunt[commodity][i]['InstrumentID'] == instrumentID:
                    if 'LongMarginRatioByMoney' in self.main_engine.brunt[commodity][i]:
                        longMarginRatioByMoney = self.main_engine.brunt[commodity][i]['LongMarginRatioByMoney']
                    if 'ShortMarginRatioByMoney' in self.main_engine.brunt[commodity][i]:
                        shortMarginRatioByMoney = self.main_engine.brunt[commodity][i]['ShortMarginRatioByMoney']
                    if 'VolumeMultiple' in self.main_engine.brunt[commodity][i]:
                        volumeMultiple = self.main_engine.brunt[commodity][i]['VolumeMultiple']

            want_hand = self.calculate(yp64,yp128,cashmoney,price,last_hand,volumeMultiple,longMarginRatioByMoney)
            if want_hand < 0:
                marginRatioByMoney = shortMarginRatioByMoney
            else:
                marginRatioByMoney = longMarginRatioByMoney
            want_hand = self.calculate(yp64,yp128,cashmoney,price,last_hand,volumeMultiple,marginRatioByMoney)

            if self.new_one_time_slice_order_start == True:
                self.once_order_volume[instrumentID] = int(math.ceil(abs(want_hand-last_hand)/self.one_time_slice_max_order_time))
                self.new_one_time_slice_order_start = False
            for k in range(len(other_hands_list)):
                intrum = other_hands_list[k]['InstrumentID']
                lasth = other_hands_list[k]['other_one_lasthand']
                handl = other_hands_list[k]['other_one_hand_list']
                if intrum in self.d[commodity] and one_time_slice in self.d[commodity][intrum]:
                    otl = self.d[commodity][intrum][one_time_slice]
                    if len(otl) > 0:
                        pr = otl[len(otl)-1]['Price']
                        self.order_clear_other(intrum,handl,lasth,self.clear_other_order_hands_num(lasth),pr)
            self.order(instrumentID,hand_list,last_hand,want_hand,price)
        self.inquiry_cal_order_mutex[instrumentID].release()
    def clear_other_order_hands_num(self,lasth):
        reduce_num = 0
        if lasth > 10:
            reduce_num = 10
        elif  lasth<-10:
            reduce_num = -10
        else:
            reduce_num = lasth
        return lasth - reduce_num
    def inquiry(self,instrumentID):
        # td = self.main_engine.td
        # if time.time() - self.main_engine.dict_account_time > 2:
        #     td.getAccount()
        # if time.time() - self.main_engine.dict_position_time > 2:
        #     td.getPosition()
        # i = 0
        # while (time.time() - self.main_engine.dict_account_time > 2 or time.time() - self.main_engine.dict_position_time > 2) and i < 10:
        #     i = i + 1
        #     time.sleep(0.2)
        if time.time() - self.main_engine.dict_account_time <= 10 and time.time() - self.main_engine.dict_position_time <= 10 and self.dict_account is not None and self.dict_position is not None:
            cashmoney = self.dict_account["Available"]
            lasthand = 0
            hand_list = []
            other_hands_list = []
            for i in range(len(self.dict_position)):
                if instrumentID == self.dict_position[i]["InstrumentID"]:
                    p_hand = self.dict_position[i]["Position"]
                    tp_hand = self.dict_position[i]["TodayPosition"]
                    yp_hand = self.dict_position[i]["YdPosition"]
                    direction = self.dict_position[i]["PosiDirection"]
                    shortFrozen = self.dict_position[i]["ShortFrozen"]
                    longFrozen = self.dict_position[i]["LongFrozen"]
                    if direction == "Short":
                        p_hand = p_hand
                        hand_dict = {"p_hand":p_hand-longFrozen,"direction":-1,"yp_hand":p_hand-tp_hand,"tp_hand":tp_hand-longFrozen}
                        lasthand = lasthand + p_hand * -1
                    else:
                        hand_dict = {"p_hand":p_hand-shortFrozen,"direction":1,"yp_hand":p_hand-tp_hand,"tp_hand":tp_hand-shortFrozen}
                        lasthand = lasthand + p_hand
                    hand_list.append(hand_dict)
            for i in range(len(self.dict_position)):
                other_one_lasthand = 0
                commodity = self.main_engine.getCommoditybyInstrumentID(instrumentID)
                com = self.main_engine.getCommoditybyInstrumentID(self.dict_position[i]["InstrumentID"])
                if instrumentID != self.dict_position[i]["InstrumentID"] and commodity == com:


                    p_hand = self.dict_position[i]["Position"]
                    tp_hand = self.dict_position[i]["TodayPosition"]
                    yp_hand = self.dict_position[i]["YdPosition"]
                    direction = self.dict_position[i]["PosiDirection"]
                    shortFrozen = self.dict_position[i]["ShortFrozen"]
                    longFrozen = self.dict_position[i]["LongFrozen"]
                    if direction == "Short":
                        p_hand = p_hand
                        hand_dict = {"p_hand":p_hand-longFrozen,"direction":-1,"yp_hand":p_hand-tp_hand,"tp_hand":tp_hand-longFrozen}
                        other_one_lasthand = other_one_lasthand + p_hand * -1
                    else:
                        hand_dict = {"p_hand":p_hand-shortFrozen,"direction":1,"yp_hand":p_hand-tp_hand,"tp_hand":tp_hand-shortFrozen}
                        other_one_lasthand = other_one_lasthand + p_hand

                    flag = False
                    for j in range(len(other_hands_list)):
                        if self.dict_position[i]['InstrumentID'] == other_hands_list[j]['InstrumentID']:
                            other_hands_list[j]['other_one_lasthand'] = other_hands_list[j]['other_one_lasthand'] + other_one_lasthand
                            other_hands_list[j]['other_one_hand_list'].append(hand_dict)
                            flag = True
                    if flag == False:
                        new_one_instrument = {}
                        new_one_instrument['other_one_lasthand'] = other_one_lasthand
                        new_one_instrument['other_one_hand_list'] = [hand_dict]
                        new_one_instrument['InstrumentID'] = self.dict_position[i]['InstrumentID']
                        other_hands_list.append(new_one_instrument)


            return cashmoney,lasthand,hand_list,other_hands_list
        else:
            return None,None,None

    def calculate(self,yp64,yp128,cashmoney,price,lasthand,volumeMultiple,marginRatioByMoney):
        want_hand = cc.calculate_hand(yp64,yp128,cashmoney,price,lasthand,volumeMultiple,marginRatioByMoney)
        return want_hand
    def order(self,instrumentID,hand_list,last_hand,want_hand,price):
        order_volume = min(self.once_order_volume[instrumentID],abs(want_hand - last_hand))
        if want_hand - last_hand > 0:
            self.plus(instrumentID,hand_list,price,order_volume)
        if want_hand - last_hand < 0:
            self.minus(instrumentID,hand_list,price,order_volume)
    def order_clear_other(self,instrumentID,hand_list,last_hand,want_hand,price):
        order_volume = abs(want_hand - last_hand)
        if want_hand - last_hand > 0:
            self.plus(instrumentID,hand_list,price,order_volume)
        if want_hand - last_hand < 0:
            self.minus(instrumentID,hand_list,price,order_volume)
    def plus(self,instrumentID,hand_list,price,order_volume):
        for i in range(len(hand_list)):
            if hand_list[i]["direction"] == -1:
                if hand_list[i]["tp_hand"] > 0 and order_volume>0:
                    self.covertoday(instrumentID,price,min(order_volume,hand_list[i]["tp_hand"]))
                    order_volume = order_volume - min(order_volume,hand_list[i]["tp_hand"])
                    time.sleep(0.1)
        for i in range(len(hand_list)):
            if hand_list[i]["direction"] == -1:
                if hand_list[i]["yp_hand"] > 0 and order_volume>0:
                    self.cover(instrumentID,price,min(order_volume , hand_list[i]["yp_hand"]))
                    order_volume = order_volume - min(order_volume,hand_list[i]["yp_hand"])
                    time.sleep(0.1)
        if order_volume > 0:
            self.buy(instrumentID,price,order_volume)

    def minus(self,instrumentID,hand_list,price,order_volume):
        for i in range(len(hand_list)):
            if hand_list[i]["direction"] == 1:
                if hand_list[i]["tp_hand"] > 0 and order_volume>0:
                    self.selltoday(instrumentID,price,min(order_volume,hand_list[i]["tp_hand"]))
                    order_volume = order_volume - min(order_volume,hand_list[i]["tp_hand"])
                    time.sleep(0.1)
        for i in range(len(hand_list)):
            if hand_list[i]["direction"] == 1:
                if hand_list[i]["yp_hand"] > 0 and order_volume>0:
                    self.sell(instrumentID,price,min(order_volume , hand_list[i]["yp_hand"]))
                    order_volume = order_volume - min(order_volume,hand_list[i]["yp_hand"])
                    time.sleep(0.1)
        if order_volume > 0:
            self.short(instrumentID,price,order_volume)


    def order_old(self,instrumentID,hand_list,want_hand,price):
        self.last_order_time = time.time()
        deal = False
        if want_hand == 0:
            for i in range(len(hand_list)):
                if hand_list[i]["direction"] == -1:
                    if hand_list[i]["yp_hand"] != 0:
                        self.cover(instrumentID,price,hand_list[i]["yp_hand"])
                    if hand_list[i]["p_hand"] - hand_list[i]["yp_hand"] != 0:
                        self.covertoday(instrumentID,price,hand_list[i]["p_hand"] - hand_list[i]["yp_hand"])
                if hand_list[i]["direction"] == 1:
                    if hand_list[i]["yp_hand"] != 0:
                        self.sell(instrumentID,price,hand_list[i]["yp_hand"])
                    if hand_list[i]["p_hand"] - hand_list[i]["yp_hand"] != 0:
                        self.selltoday(instrumentID,price,hand_list[i]["p_hand"] - hand_list[i]["yp_hand"])
        if want_hand >0:
            for i in range(len(hand_list)):
                if hand_list[i]["direction"] == -1:
                    if hand_list[i]["yp_hand"] != 0:
                        self.cover(instrumentID,price,hand_list[i]["yp_hand"])
                    if hand_list[i]["p_hand"] - hand_list[i]["yp_hand"] != 0:
                        self.covertoday(instrumentID,price,hand_list[i]["p_hand"] - hand_list[i]["yp_hand"])
                        #
                if hand_list[i]["direction"] == 1:
                    if hand_list[i]["p_hand"] > want_hand:
                        if hand_list[i]["yp_hand"] <= want_hand and hand_list[i]["p_hand"] > want_hand:
                            self.selltoday(instrumentID,price,hand_list[i]["p_hand"] - want_hand)
                        if hand_list[i]["yp_hand"] >want_hand:
                            self.selltoday(instrumentID,price,hand_list[i]["p_hand"] - hand_list[i]["yp_hand"])
                            self.sell(instrumentID,price,hand_list[i]["yp_hand"] - want_hand)
                    if hand_list[i]["p_hand"] < want_hand:
                        self.buy(instrumentID,price,want_hand - hand_list[i]["p_hand"])
                    deal = True
        if want_hand >0 and deal == False:
            self.buy(instrumentID,price,want_hand)
        if want_hand <0:
            for i in range(len(hand_list)):
                if hand_list[i]["direction"] == 1:
                    if hand_list[i]["yp_hand"] != 0:
                        self.sell(instrumentID,price,hand_list[i]["yp_hand"])
                    if hand_list[i]["p_hand"] - hand_list[i]["yp_hand"] != 0:
                        self.selltoday(instrumentID,price,hand_list[i]["p_hand"] - hand_list[i]["yp_hand"])
                        #
                if hand_list[i]["direction"] == -1:
                    if hand_list[i]["p_hand"] > want_hand * -1:
                        if hand_list[i]["yp_hand"] <= want_hand * -1 and hand_list[i]["p_hand"] > want_hand * -1:
                            self.covertoday(instrumentID,price,hand_list[i]["p_hand"] - want_hand * -1)
                        if hand_list[i]["yp_hand"] >want_hand * -1:
                            self.covertoday(instrumentID,price,hand_list[i]["p_hand"] - hand_list[i]["yp_hand"])
                            self.cover(instrumentID,price,hand_list[i]["yp_hand"] - want_hand * -1)
                    if hand_list[i]["p_hand"] < want_hand * -1:
                        self.short(instrumentID,price,want_hand * -1 - hand_list[i]["p_hand"])
                    deal = True
        if want_hand <0 and deal == False:
            self.short(instrumentID,price,want_hand)
        return
    def buy(self, symbol, price, vol):  # 买开多开
        lc.loger_order.info("买开多开"+ " symbol:"+str(symbol)+" price:"+str(price)+" vol:" +str(vol))
        td = self.main_engine.td
        td.buy(symbol, price, vol)
        time.sleep(1)
        return
    def sell(self, symbol, price, vol):  # 多平
        lc.loger_order.info("多平"+ " symbol:"+str(symbol)+" price:"+str(price)+" vol:" +str(vol))
        td = self.main_engine.td
        td.sell(symbol, price, vol)
        time.sleep(1)
        return
    def selltoday(self, symbol, price, vol):  # 平今多
        lc.loger_order.info("平今多"+ " symbol:"+str(symbol)+" price:"+str(price)+" vol:" +str(vol))
        td = self.main_engine.td
        td.selltoday(symbol, price, vol)
        time.sleep(1)
        return
    def short(self, symbol, price, vol):  # 卖开空开
        lc.loger_order.info("卖开空开"+ " symbol:"+str(symbol)+" price:"+str(price)+" vol:" +str(vol))
        td = self.main_engine.td
        td.short(symbol, price, vol)
        time.sleep(1)
        return
    def cover(self, symbol, price, vol):  # 空平
        lc.loger_order.info("空平"+ " symbol:"+str(symbol)+" price:"+str(price)+" vol:" +str(vol))
        td = self.main_engine.td
        td.cover(symbol, price, vol)
        time.sleep(1)
        return

    def covertoday(self, symbol, price, vol):  # 平今空
        lc.loger_order.info("平今空"+ " symbol:"+str(symbol)+" price:"+str(price)+" vol:" +str(vol))
        td = self.main_engine.td
        td.covertoday(symbol, price, vol)
        time.sleep(1)
        return


    def isOrderTime(self,commodity):
        if time.time() - self.last_order_time < 10:
            return False
        for i in range(len(order_time)):
            now_time = time.time()
            now_date = self.Time2ISOString(now_time)
            ts = str.split(now_date)
            limit_date = ts[0] + ' ' + order_time[i][1]
            start_date = ts[0] + ' ' + order_time[i][0]
            start_time = self.ISOString2Time(start_date)
            limit_time = self.ISOString2Time(limit_date)
            if limit_time > now_time and start_time <now_time:
                return True
        return False
    def getTimeSliceByNowTime(self,commodity):
        if commodity in time_slice:
            com_times = time_slice[commodity]
            for i in range(len(com_times)):
                now_time = time.time()
                now_date = self.Time2TickString(now_time)
                ts = str.split(now_date)
                if ts[0] + ' ' + com_times[i][1] > now_date and ts[0] + ' ' + com_times[i][0] < now_date:
                    return ts[0] + ' ' + com_times[i][1]
        return None
    def isGenerateYtupleTime(self,commodity):
        for i in range(len(predict_time)):
            now_time = time.time()
            now_date = self.Time2ISOString(now_time)
            ts = str.split(now_date)
            limit_date = ts[0] + ' ' + predict_time[i][1]
            start_date = ts[0] + ' ' + predict_time[i][0]
            start_time = self.ISOString2Time(start_date)
            limit_time = self.ISOString2Time(limit_date)
            if limit_time > now_time and start_time <now_time:
                return True
        return False
    def insertTick(self,dict):
        self.mongo_engine.mutex.acquire()
        #time = self.Time2ISOString(dict['Time'])
        ts = str.split(dict['Time'])
        hms = ts[1]
        tarray = time_slice[dict['Commodity']]
        for i in range(len(tarray)):
            taa = tarray[i]
            if taa[0]<=hms and hms<= taa[1]:
                if dict['Commodity'] not in self.d.keys():
                    self.d[dict['Commodity']] = {}
                if dict['InstrumentID'] not in self.d[dict['Commodity']].keys():
                    self.d[dict['Commodity']][dict['InstrumentID']] = {}
                if ts[0]+' '+taa[1] not in self.d[dict['Commodity']][dict['InstrumentID']].keys():
                    self.d[dict['Commodity']][dict['InstrumentID']][ts[0]+' '+taa[1]] = []
                j = 0
                while j<=len(self.d[dict['Commodity']][dict['InstrumentID']][ts[0]+' '+taa[1]]):
                    if len(self.d[dict['Commodity']][dict['InstrumentID']][ts[0]+' '+taa[1]]) == 0 or self.d[dict['Commodity']][dict['InstrumentID']][ts[0]+' '+taa[1]][j-1]['Time']>dict['Time'] or j == len(self.d[dict['Commodity']][dict['InstrumentID']][ts[0]+' '+taa[1]]):
                        self.d[dict['Commodity']][dict['InstrumentID']][ts[0]+' '+taa[1]].insert(j,dict)
                        break
                    j = j + 1
        self.mongo_engine.mutex.release()
    # def generateFifteen(self):
    #     for cindex,commodity in enumerate(self.d.keys()):
    #         for iindex,instrumentID in enumerate(self.d[commodity].keys()):
    #             for tindex,time in enumerate(self.d[commodity][instrumentID].keys()):
    #                 a = {}
    #                 a['opend'] = self.d[commodity][instrumentID][time][0]['Price']
    #                 a['close'] = self.d[commodity][instrumentID][time][len(self.d[commodity][instrumentID][time])-1]['Price']
    #                 minValue = self.d[commodity][instrumentID][time][0]['Price']
    #                 maxValue = self.d[commodity][instrumentID][time][0]['Price']
    #                 for i in range(len(self.d[commodity][instrumentID][time])):
    #                     minValue = min(self.d[commodity][instrumentID][time][i]['Price'],minValue)
    #                     maxValue = max(self.d[commodity][instrumentID][time][i]['Price'],maxValue)
    #                 a['low'] = minValue
    #                 a['high'] = maxValue
    #                 a['commodity'] = commodity
    #                 a['instrumentID'] = instrumentID
    #                 a['time'] = time
    #                 flag = False
    #                 for i in range(len(self.r)):
    #                     if self.r[i]['time'] == a['time']:
    #                         self.r[i]['low'] = min(self.r[i]['low'],a['low'])
    #                         self.r[i]['high'] = max(self.r[i]['high'],a['high'])
    #                         self.r[i]['close'] = a['close']
    #                         flag = True
    #                         break
    #                 if flag == False:
    #                     self.r.append(a)


    def search_130(self,commodity,instrumentID):
        return self.mongo_engine.search_130(commodity,instrumentID)
    def save_or_update_order(self,order):
        self.mongo_engine.save_or_update_order(order)
    def save_or_update_trader(self,trade):
        self.mongo_engine.save_or_update_trader(trade)
    def cancel_order(self):
        order_list = self.main_engine.find_not_cancel_instrumentID()
        for i in range(len(order_list)):
            lc.loger_order.info("撤单")
            lc.loger_order.info(order_list[i])
            self.main_engine.cancelOrder(order_list[i])
            time.sleep(0.1)
    def ISOString2Time(self, s ):
        d=datetime.datetime.strptime(s,"%Y-%m-%d %H:%M:%S")
        return time.mktime(d.timetuple())

    def Time2ISOString(self, s ):
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime( float(s) ) )
    def Time2TickString(self, s ):
        return time.strftime("%Y%m%d %H:%M:%S", time.localtime( float(s) ) )

    def Release(self):
        self.order_engine_start_run_thread = False
        self.mongo_engine.Release()
        if self.mongo_thread is not None:
            self.mongo_thread.join()
            lc.loger.info(threading.current_thread())
            lc.loger.info("mongo_thread_stop")
        if self.account_and_position_thread is not None:
            self.account_and_position_thread.join()
            lc.loger.info(threading.current_thread())
            lc.loger.info("account_and_position_thread_stop")
        if self.order_thread is not None:
            self.order_thread.join()
            lc.loger.info(threading.current_thread())
            lc.loger.info("order_thread_stop")


if __name__ == '__main__':
    a =1
    tf = TickFifteen(a)
    mongo_data = tf.search_130('rb','rb1801')
    #添加tensorflow代码
    yp = dn.run_dnn(mongo_data)
    print(yp)
