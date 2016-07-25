from numpy import *

eps = 1e-5

def fillArrayToFixedLength(x,filler,fixedLen):
    if len(x)<fixedLen:
        return concatenate((x,array([filler]*(fixedLen-len(x)))))
    else: return x


def calcMidPrice(bid, ask, bidQty,askQty, mode):
    if mode == 1:
        return (bid[0] + ask[0])/2
    else:
        if mode==2:
            return (bid[0]*askQty[0]+ask[0]*bidQty[0])/(askQty[0]+bidQty[0])
        else:
            return NaN


def updateBookWithFixedSize(tick,len, roundDigits):
    bid = fillArrayToFixedLength(around(array(tick.bids)[:, 0], decimals=roundDigits), NaN, len)
    ask = fillArrayToFixedLength(around(array(tick.asks)[:, 0], decimals=roundDigits), NaN, len)
    bidQty = fillArrayToFixedLength(around(array(tick.bids)[:, 1]), 0, len)
    askQty = fillArrayToFixedLength(around(array(tick.asks)[:, 1]), 0, len)
    return [bid,ask,bidQty,askQty]



def roundDown(num,unit=1):
    temp=num/unit
    if temp > 0.0:
        temp= int(floor(temp))
    else:
        temp=-int(floor(-temp))
    return temp*unit


def getFlattener(minutes):
    if minutes<(60+35):
        return 0
    else:
        if minutes<(60+45):
            return (minutes - (60+35))*0.1
        else:
            if minutes<(6*60 + 45):
                return 1
            else:
                if minutes<(6*60 + 55):
                    return 1 - (minutes - (6*60+45))*0.1
                else: return 0



