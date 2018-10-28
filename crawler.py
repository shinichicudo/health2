#encoding=utf-8
from bs4 import BeautifulSoup
import requests
import xlwt
# import MySQLdb
import sys,io,re,time,json
from pymongo import MongoClient
import datetime
import json

#解决输出中文乱码的问题
# reload(sys)
# sys.setdefaultencoding('utf-8')

#期货历史数据爬虫
class DataCrawler:
    future_list =['hc','bu','zn','ru','al','cu','rb','ni','sn','p','pp','jd','i','jm','v','l','y','c','m','j','cs','ZC','FG','MA','CF','RM','TA','SR','ag','au','b','AP']
    # future_list=['ag']
    start_urls = []
    base_url_daily = "http://stock2.finance.sina.com.cn/futures/api/json.php/IndexService.getInnerFuturesDailyKLine?symbol="
    # base_url_daily = "http://stock2.finance.sina.com.cn/futures/api/json.php/IndexService.getInnerFuturesMiniKLine15m?symbol="

    # mongoDB
    conn = MongoClient('localhost', 27017)
    db = conn.mydb  #连接mydb数据库，没有则自动创建
    end_date= ''
    collection = db.daily
    date_save = db.datesave
    start_date = ''
    start_year = '18'
    start_month ='01'
    end_month = '13'
    def __init__(self):
        self.session = requests.Session()
        sd = self.date_save.find_one({'the':1})
        if sd is not None:
            self.start_date = sd['time']
            self.start_year = self.start_date.split('-')[0][2:4]
        else:
            self.start_year = '08'

        self.start_month ='01'
        self.end_month = '13'

        self.end_date = (datetime.datetime.now() + datetime.timedelta(weeks=104)).strftime('%Y-%m-%d')
        end_year = self.end_date.split('-')[0][2:4]

        self.new_start_date = datetime.datetime.now().strftime('%Y-%m-%d')
        dict = {'the':1}
        self.last_crawl_time = self.date_save.find_one(dict)
        if self.last_crawl_time is not None:
            self.date_save.update(dict,{'$set' : {'time':self.new_start_date}})
        else:
            dict['time']=self.new_start_date
            self.date_save.insert(dict)


        for  i in range(len(self.future_list)):
            current_year = self.start_year
            while(int(current_year) != int(end_year)):
                current_month = self.start_month
                while(int(current_month)!=int(self.end_month)):
                    symbol =self.future_list[i] + current_year + current_month
                    self.start_urls.append(self.base_url_daily+symbol)
                    current_month = str(int(current_month) + 1).zfill(2)
                current_year = str(int(current_year) + 1).zfill(2)
        

    #获取数据
    def getPageDate(self):
        for url in self.start_urls:
            response = self.session.get(url)
            self.parse(response)


    def parse(self, response):
        instrumentID = response.url.split("symbol=")[1]
        commodity = instrumentID[:-4]
        data = str(response.content, encoding = "utf-8")
        if data == 'null':
            return
        else:
            ar = json.loads(data)
            array = []
            for a in ar:
                if a[0]>=self.start_date:
                    array.append(a)
            for i in range(len(array)):
                dic = {}
                dic['instrumentID'] = instrumentID
                dic['commodity'] = commodity
                dic['time'] = array[i][0]
                if dic['time'] == self.start_date:
                    self.collection.delete_one(dic)

                for j in range(len(array[i])):
                    if j == 0:
                        None
                    elif j == 1:
                        dic['opend'] = float(array[i][j])
                    elif j == 2:
                        dic['high'] = float(array[i][j])
                    elif j == 3:
                        dic['low'] = float(array[i][j])
                    elif j == 4:
                        dic['close'] = float(array[i][j])
                    elif j == 5:
                        dic['volume'] = int(array[i][j])
                dic['chanceType'] = 100
                self.collection.insert(dic)
        print(instrumentID)


    #执行
    def start(self):
        if self.last_crawl_time['time'] == self.new_start_date:
            return
        self.getPageDate()


if __name__ == '__main__':
    c = DataCrawler()
    c.start()
