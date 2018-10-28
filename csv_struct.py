class CsvStruct:
    def __init__(self,marketcode,treatycode,time,open,high,low,close,volume,volumeprice,openinterest):
        self.marketcode = marketcode     # 市场代码
        self.treatycode = treatycode     # 合约代码
        self.time = time     # 交易时间
        self.open = open       # 开盘价格
        self.high = high       #最高价格
        self.low = low        #最低价格
        self.close = close      #收盘价格
        self.volume = volume      #成交量
        self.volumeprice = volumeprice #成交额
        self.openinterest = openinterest #持仓量


# def test():
#     a = CsvStruct() # 定义结构对象
#     a.name = 'cup'
#     a.size = 8
#     a.list.append('water')
#     print(a.name,a.size,a.list)
#
# if __name__ == "__main__":
#     test()