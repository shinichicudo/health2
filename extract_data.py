

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function



import numpy as np


import collections
import csv
from csv_struct import CsvStruct
from tensorflow.python.platform import gfile
import datetime
import time
import arth as at
import dir_file as df
import config as cf
# train_x_y = collections.namedtuple('x_y', ['x', 'y'])
# test_x_y = collections.namedtuple('x_y', ['x', 'y'])
train_test = collections.namedtuple('train_test', ['train', 'test','regular'])
Flags = collections.namedtuple('Flags', ['train_data', 'test_data', 'predict_data'])
DATA_MIN_LENGTH = 128
ONE_DAY_DATA = 4
FlUCTUATION = [0.0,0.005,0.01,0.015,0.02,0.025,0.03,0.035,0.04,0.045,0.05]
FlUCTUATION_MINUS = [0.0,-0.005,-0.01,-0.015,-0.02,-0.025,-0.03,-0.035,-0.04,-0.045,-0.05]
FlUCTUATION_MINUS.reverse()
Y_LENGTH = 40
volume_dict = {'rb':0}

one_hand = 10
bail = 0.1

BEGIN_MONEY = 1000000




class DateSet(object):

    def __init__(self, data=None):
        self.data = data
        self.length = len(self.data[0])
        self.count = 0
    def next_batch(self,size):
        if self.length == 0:
            raise Exception('zhe data is empty')
        if self.length - self.count <= 0:
            self.count = 0
        if self.length - self.count <size:
            start = self.count
            end = self.length
            self.count = 0
            return self.subarray(start,end)
        if self.length - self.count >= size:
            start = self.count
            end = self.count + size
            self.count = end
            return self.subarray(start,end)

    def subarray(self,start,end):
        a = []
        for i in range(len(self.data)):
            a.append(self.data[i][start:end])
        return a

def getfluent(index):
    values = []

    a = FlUCTUATION[:]
    b = FlUCTUATION_MINUS[:]
    a.pop(0)
    b.pop(10)
    values.extend(b)
    values.extend(a)
    return values[index]


def kelly_criterion(p,r):
    pr = np.multiply(p,r)
    ps = np.sum(pr,1)
    rp = np.product(r,1)
    re = ps/rp*(-1)
    return re

def probability_cal(y_pp,marginRatioByMoney):
    values = []

    a = FlUCTUATION[:]
    b = FlUCTUATION_MINUS[:]
    # a.pop(0)
    # b.pop(10)
    values.extend(b)
    values.extend(a)
    #值
    np_v = np.array(values)
    #算出可能值乘以概率
    y_v = np.multiply(y_pp,np_v)
    y_ppp = np.reshape(y_pp,[-1,2,10])
    for i in range(len(y_ppp)):
        for j in range(len(y_ppp[i])):
            if j == 0:
                y_ppp[i][j][9] = 0.0
            if j == 1:
                y_ppp[i][j][0] = 0.0
    #概率值,分正负
    pro = np.sum(y_ppp,2)
    y_vv = np.reshape(y_v,[-1,2,10])
    y_vvv = np.sum(y_vv,2)
    y_vvvv = np.true_divide(y_vvv,pro)
    #真实波动值，分正负
    floatvalue = y_vvvv/marginRatioByMoney
    return pro,floatvalue



def datestr2num(s):
    #toordinal()将时间格式字符串转为数字
    strptime = datetime.datetime.strptime(s, '%Y-%m-%d %H:%M:%S')
    ans_time = time.mktime(strptime.timetuple())
    return ans_time

def mongodatestr2num(s):
    #toordinal()将时间格式字符串转为数字
    strptime = datetime.datetime.strptime(s, '%Y%m%d %H:%M:%S')
    ans_time = time.mktime(strptime.timetuple())
    return ans_time

def get_csv_data_dict(dirname):
    file_dict = df.file_dict(dirname)
    volume_keys = list(volume_dict.keys())
    data_dict = {}
    for i in range(len(volume_keys)):
        mer_dict = file_dict.get(volume_keys[i])
        mer_dict_keys = list(mer_dict.keys())
        mer_data_dict = {}
        for j in range(len(mer_dict_keys)):
            file_list = mer_dict.get(mer_dict_keys[j])
            d=[]
            for k in range(len(file_list)):
                d = load_csv_without_header(file_list[k],data=d)
            mer_data_dict[mer_dict_keys[j]] = d
        data_dict[volume_keys[i]] = mer_data_dict
    return data_dict

def load_mongo(mongo_data):
    if len(mongo_data) != DATA_MIN_LENGTH+2:
        raise Exception("mongo data length not right")
    data = []
    for i in range(len(mongo_data)):


        close = np.float32(mongo_data[i]['close'])
        low = np.float32(mongo_data[i]['low'])
        high = np.float32(mongo_data[i]['high'])
        ope = np.float32(mongo_data[i]['opend'])

        time = mongodatestr2num(mongo_data[i]['time'])

        treatycode = mongo_data[i]['instrumentID']
        marketcode = mongo_data[i]['commodity']
        csv_struct = CsvStruct(marketcode,treatycode,time,ope,high,low,close,0,0,0)
        data.append(csv_struct)
    return data

def mongo_data_2_array_data(mongoDataSet):

    mongoDataSet.sort(key=lambda x: float(x.time),reverse=False)
    data = []
    value = []
    for i in range(len(mongoDataSet)):
        datarow = []
        if i == 0:
            continue
        else:
            datarow.append(mongoDataSet[i].open/mongoDataSet[i-1].close - 1)
        datarow.append(mongoDataSet[i].high/mongoDataSet[i].open - 1)
        datarow.append(mongoDataSet[i].low/mongoDataSet[i].open - 1)
        datarow.append(mongoDataSet[i].close/mongoDataSet[i-1].close - 1)
        data.append(datarow)

        if i == len(mongoDataSet) - 1:
            valueclose = []
            valueclose.append(mongoDataSet[i].close)
            valueclose.append(mongoDataSet[i].close)
            value.append(valueclose)

    return data,value


def load_csv_without_header(filename,
                            target_column=-1,data = None):
    """Load dataset from CSV file without a header row."""
    with open(filename,encoding='GBK') as csv_file:
        data_file = csv.reader(csv_file)
        if data is None:
            data = []
        i = 0
        for row in data_file:
            if i == 0:
                i = i + 1
                continue
            openinterest = np.float32(row.pop(target_column))
            volumeprice = np.float32(row.pop(target_column))
            volume = np.float32(row.pop(target_column))
            # if volume == 0 or volumeprice == 0:
            #     continue

            close = np.float32(row.pop(target_column))
            low = np.float32(row.pop(target_column))
            high = np.float32(row.pop(target_column))
            ope = np.float32(row.pop(target_column))

            time = datestr2num(row.pop(target_column))

            treatycode = row.pop(target_column)
            marketcode = row.pop(target_column)
            csv_struct = CsvStruct(marketcode,treatycode,time,ope,high,low,close,volume,volumeprice,openinterest)
            data.append(csv_struct)
    return data

def csv_data_2_array_data(csvDataSet):

    csvDataSet.sort(key=lambda x: float(x.time),reverse=False)
    data = []
    value = []
    for i in range(len(csvDataSet)-1):
        datarow = []
        if i == 0:
            datarow.append(0.0)
        else:
            datarow.append(csvDataSet[i].open/csvDataSet[i-1].close - 1)
        datarow.append(csvDataSet[i].high/csvDataSet[i].open - 1)
        datarow.append(csvDataSet[i].low/csvDataSet[i].open - 1)
        if i == 0:
            datarow.append(0.0)
        else:
            datarow.append(csvDataSet[i].close/csvDataSet[i-1].close - 1)
        data.append(datarow)

        if i >= DATA_MIN_LENGTH-1:
            valueclose = []
            valueclose.append(csvDataSet[i].close)
            valueclose.append(csvDataSet[i+1].close)
            value.append(valueclose)

    return data,value

def array_data_2_tuple_data(data):
    if len(data)<DATA_MIN_LENGTH:
        return None
    x = []
    y = []
    weight_y = []
    before_x = []
    current_x = []
    for i in range(DATA_MIN_LENGTH,len(data)):
        if i == DATA_MIN_LENGTH:
            for j in range(DATA_MIN_LENGTH):
                d = data[j]
                for k in range(ONE_DAY_DATA):
                    current_x.append(d[k])
        else:
            current_x = before_x
            for j in range(ONE_DAY_DATA):
                current_x.pop(0)

            for k in range(ONE_DAY_DATA):
                current_x.append(data[i-1][k])
        x.append(current_x)
        before_x = current_x[:]


        dd0 = data[i][0]
        dd3 = data[i][3]
        d0_y = 0
        d3_y = Y_LENGTH//2
        for j in range(len(FlUCTUATION)-1):
            if dd0>= FlUCTUATION[j] and dd0< FlUCTUATION[j+1]:
                d0_y = j+Y_LENGTH//4*1
                break
        if dd0>= FlUCTUATION[Y_LENGTH//4*1-1]:
            d0_y = Y_LENGTH//4*2-1
        if dd0<= FlUCTUATION_MINUS[0]:
            d0_y = 0
        for j in range(len(FlUCTUATION_MINUS)-1):
            if dd0> FlUCTUATION_MINUS[j] and dd0<= FlUCTUATION_MINUS[j+1]:
                d0_y = j
                break
        for j in range(len(FlUCTUATION)-1):
            if dd3>= FlUCTUATION[j] and dd3< FlUCTUATION[j+1]:
                d3_y = j+Y_LENGTH//4*3
                break
        if dd3>= FlUCTUATION[Y_LENGTH//4*1-1]:
            d3_y = Y_LENGTH-1
        if dd3<= FlUCTUATION_MINUS[0]:
            d3_y = Y_LENGTH//2
        for j in range(len(FlUCTUATION_MINUS)-1):
            if dd3> FlUCTUATION_MINUS[j] and dd3<= FlUCTUATION_MINUS[j+1]:
                d3_y = j+Y_LENGTH//2 + 1
                break
        current_y,wa = set_current_y(d0_y,d3_y)
        y.append(current_y)
        weight_y.append(wa)

    np_x = np.array(x)
    np_y = np.array(y)
    np_weight_y = np.array(weight_y)
    x_y = []
    x_y.append(np_x)
    x_y.append(np_y)
    x_y.append(np_weight_y)
    return x_y
def array_mongo_2_tuple_data(data):
    if len(data)<DATA_MIN_LENGTH:
        return None
    x = []

    current_x = []

    for j in range(len(data) - DATA_MIN_LENGTH,len(data)):
        d = data[j]
        for k in range(ONE_DAY_DATA):
            current_x.append(d[k])

    x.append(current_x)





    np_x = np.array(x)
    x_y = []
    x_y.append(np_x)
    return x_y

def mongo_tensorflow_data_generate(mongo_data):
    mongo_data_set = load_mongo(mongo_data)
    data_tuple_data = mongo_data_machining(mongo_data_set)
    return data_tuple_data
def mongo_data_machining(mongo_data_set):
    data_array_data, data_array_value = mongo_data_2_array_data(mongo_data_set)
    data_tuple_value = np.array(data_array_value)
    data_tuple_data = array_mongo_2_tuple_data(data_array_data)
    if data_tuple_data is None:
        return None
    data_tuple_data.append(data_tuple_value)
    return data_tuple_data


def data_machining(data_set):
    data_array_data, data_array_value = csv_data_2_array_data(data_set)
    data_tuple_value = np.array(data_array_value)
    data_tuple_data = array_data_2_tuple_data(data_array_data)
    if data_tuple_data is None:
        return None
    data_tuple_data.append(data_tuple_value)
    return data_tuple_data

def mutiple_data_deal(one_data_dict):
    one_tuple_data = None
    one_keys_list = list(one_data_dict.keys())
    for i in range(len(one_keys_list)):
        dict = one_data_dict.get(one_keys_list[i])
        dict_keys_list = list(dict.keys())
        for j in range(len(dict_keys_list)):
            data_set = dict.get(dict_keys_list[j])

            one_tuple_data_p = data_machining(data_set)
            if one_tuple_data_p is None:
                continue
            if one_tuple_data is None:
                one_tuple_data = one_tuple_data_p
            else:
                for k in range(len(one_tuple_data)):
                    one_tuple_data[k] = np.append(one_tuple_data[k],one_tuple_data_p[k],0)
    return one_tuple_data

def mongo_data_deal(mongo_data):
    data_tuple_data = mongo_tensorflow_data_generate(mongo_data)
    train_test.regular = DateSet(data_tuple_data)
    return train_test

def data_deal(FLAGS):

    # Training examples
    train_dir = FLAGS.train_data
    if train_dir is None:
        train_test.train = None
    else:
        train_data_dict = get_csv_data_dict(dirname=train_dir)
        training_tuple_data = mutiple_data_deal(train_data_dict)
        train_test.train = DateSet(training_tuple_data)

    # Test examples
    test_dir = FLAGS.test_data
    if test_dir is None:
        train_test.test = None
    else:
        test_data_dict = get_csv_data_dict(dirname=test_dir)
        test_tuple_data = mutiple_data_deal(test_data_dict)
        train_test.test = DateSet(test_tuple_data)

    return train_test

def set_current_y(d0_y,d3_y):
    current_y =  []

    for i in range(Y_LENGTH//2):
        current_y.append(0.0)
    position = d3_y-Y_LENGTH//2
    current_y[position] = 1.0
    wa = at.weightarray(Y_LENGTH//2,position)
    return current_y,wa



def extract(training_url,test_url,predict_url):
    FLAGS = Flags(train_data = training_url,test_data = test_url, predict_data = predict_url)
    train_test = data_deal(FLAGS)
    return train_test

#计算凯利公式，这个是tensorflow算出来的值,根据前128次的走势预测的接下来的一次走势的值，并用了凯利公式计算投资额度
def cal_kalley(vv,marginRatioByMoney):
    s,ss = probability_cal(vv,marginRatioByMoney)
    re = kelly_criterion(s,ss)
    return re



# if __name__ == "__main__":
#     train_test = extract(cf.train_dir,cf.test_dir, ' ')
#     print("ha")
    # a = []
    # b = []
    # v = []
    # a1 = 0.0025
    # d = 0.005
    # an = 0.0975
    # for i in range(20):
    #     a.append(a1)
    #     a1 = a1 + d
    # b =a[:]
    # b.reverse()
    # v.append(a)
    # v.append(b)
    # vv = np.array(v)
    #
    # s,ss = probability_cal(vv)
    # re = kelly_criterion(s,ss)
    # print(s)
    # print(ss)
    # print(re)

