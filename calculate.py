import extract_data as ed
import numpy as np
import math
import config as cf
#cashmoney 现有现金
#price 现在这个时刻该商品期货的价格
#lasthand 现有期货手数，带正负表明多空
def calculate_hand(yp64,yp128,cashmoney,price,lasthand,volumeMultiple,marginRatioByMoney):
    # print(price)
    # print(ed.one_hand)
    # print(ed.bail)
    # print(abs(lasthand))
    handmoney = math.floor(price*volumeMultiple*marginRatioByMoney*abs(lasthand))
    money = cashmoney + handmoney
    if money <0:
        return lasthand
    y64 = np.argmax(yp64,axis=1)
    y128 = np.argmax(yp128,axis=1)
    # y64[0] = 3
    # y128[0] = 3

    ka = 0
    if cf.DAY64_PREDICT and cf.DAY128_PREDICT == False:
        if y64[0] == 0:
            return 0
        if y64[0] == 1:
            ka = ( cf.GAIN_RATIO_64_p * yp64[0][1] - cf.LOSS_RATIO_64_p * yp64[0][3])/cf.GAIN_RATIO_64_p /cf.LOSS_RATIO_64_p*marginRatioByMoney
        # if y64[0] == 2:
        #     ka = ( cf.PROFIT_AND_LOSS_RATIO * yp64[0][2] - yp64[0][3] )/cf.PROFIT_AND_LOSS_RATIO
        if y64[0] == 3:
            ka = ( cf.GAIN_RATIO_64_n * yp64[0][3] - cf.LOSS_RATIO_64_n * yp64[0][1])/cf.GAIN_RATIO_64_n /cf.LOSS_RATIO_64_n*marginRatioByMoney
            ka = ka * -1
    if cf.DAY64_PREDICT == False and cf.DAY128_PREDICT:
        if y128[0] == 0:
            return 0
        if y128[0] == 1:
            ka = ( cf.GAIN_RATIO_128_p * yp128[0][1] - cf.LOSS_RATIO_128_p * yp128[0][3])/cf.GAIN_RATIO_128_p /cf.LOSS_RATIO_128_p*marginRatioByMoney
        # elif y128[0] == 2:
        #     ka = ( cf.PROFIT_AND_LOSS_RATIO * yp128[0][2] - yp128[0][3] )/cf.PROFIT_AND_LOSS_RATIO
        elif y128[0] == 3:
            ka = ( cf.GAIN_RATIO_128_n * yp128[0][3] - cf.LOSS_RATIO_128_n * yp128[0][1])/cf.GAIN_RATIO_128_n /cf.LOSS_RATIO_128_n*marginRatioByMoney
            ka = ka * -1
        else:
            return 0
    if cf.DAY64_PREDICT and cf.DAY128_PREDICT:
        if y64[0] == 0 or y128[0] == 0:
            return 0
        elif y64[0] == 1 and y128[0] == 1:
            ka = ( (cf.GAIN_RATIO_128_p + cf.GAIN_RATIO_64_p)/2 * (yp64[0][1] + yp128[0][1])/2 - (cf.LOSS_RATIO_128_p + cf.LOSS_RATIO_64_p)/2 * (yp64[0][3] + yp128[0][3])/2)/(cf.GAIN_RATIO_128_p + cf.GAIN_RATIO_64_p) /(cf.LOSS_RATIO_128_p + cf.LOSS_RATIO_64_p)*4*marginRatioByMoney
        # elif y64[0] == 2 and y128[0] == 2:
        #     ka = ( cf.PROFIT_AND_LOSS_RATIO * yp64[0][2] * yp128[0][2] - yp64[0][3]*yp128[0][3] )/cf.PROFIT_AND_LOSS_RATIO
        elif y64[0] == 3 and y128[0] == 3:
            ka = ( (cf.GAIN_RATIO_128_n + cf.GAIN_RATIO_64_n)/2 * (yp64[0][3] + yp128[0][3])/2 - (cf.LOSS_RATIO_128_n + cf.LOSS_RATIO_64_n)/2 * (yp64[0][1] + yp128[0][1])/2)/(cf.GAIN_RATIO_128_n + cf.GAIN_RATIO_64_n) /(cf.LOSS_RATIO_128_n + cf.LOSS_RATIO_64_n)*4*marginRatioByMoney
            ka = ka * -1
        else:
            return 0


            # kal = ed.cal_kalley(y_aparray,marginRatioByMoney)
    # #凯利公式预测值
    # kallist = kal.tolist()

    #测试回撤用数据，内部生成
    my = []


    # ka = kallist[0]
    if(ka>1):
        compa = 1
    elif(ka<-1):
        compa = -1
    else:
        compa = ka
    # compa = ka
    use_money = money*np.abs(compa)
    hand = use_money//(price*volumeMultiple*marginRatioByMoney)
    use_money = (price*volumeMultiple*marginRatioByMoney)*hand
    if compa<0:
        want_hand = hand *  -1
    else:
        want_hand= hand
    want_hand_int = int(want_hand)
    return want_hand_int

if __name__ == '__main__':
    a = (cf.GAIN_RATIO_128_n + cf.GAIN_RATIO_64_n)/2 * cf.GAIN_PERCENT
    b = (cf.LOSS_RATIO_128_n + cf.LOSS_RATIO_64_n)/2 * cf.LOSS_PERCENT
    c = (cf.GAIN_RATIO_128_n + cf.GAIN_RATIO_64_n)*(cf.LOSS_RATIO_128_n + cf.LOSS_RATIO_64_n)/4
    print(a)
    print(b)
    print(c)
    print((cf.LOSS_RATIO_128_n + cf.LOSS_RATIO_64_n)/2)