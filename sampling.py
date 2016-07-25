from gmsdk.api import md
from numpy import *
import csv
from StrategyUtility.utility import *


symbol = 'SHSE.510050' ##50 ETF 0.001
#symbol = 'SZSE.300017' ##网宿
#symbol = 'SHSE.600519' ##茅台
#symbol = 'SZSE.002466' ##天齐锂业
#tickSize = 0.01
tickSize = 0.001

lastBid = []
lastAsk = []
lastBidQty = []
lastAskQty = []
bid = []
bidQty = []
ask = []
askQty = []
cumAmount = 0.0
lastCumAmount = 0.0
cumSum = 0.0
lastCumSum = 0.0
ts = NaN
tsString = ''
lastTs = 0
imbalance = 0.0
imbalance1 = 0.0
imbalance2 = 0.0
vwap = NaN
thisSum = 0.0
thisAmount = 0.0
#outputFile = open('saveData.csv', 'w')

csvFile = open('saveData.csv','w',newline='')
outputFile = csv.writer(csvFile, delimiter=',',
                        quotechar='|', quoting=csv.QUOTE_MINIMAL)

    # 响应bar数据到达事件
header= ['barTime','tickTime','tickUTC','bid1','bid2','bid3','bid4','bid5',
         'ask1','ask2','ask3','ask4','ask5',
         'bidQ1','bidQ2','bidQ3','bidQ4','bidQ5',
         'askQ1','askQ2','askQ3','askQ4','askQ5',
         'cumVolume','imbl','imbl1','imbl2',
         'imblAsk','imblBid','cancelBid','cancelAsk',
         'volume','vwap']

outputFile.writerow(header)


def on_bar(bar):
    global ts,bid,ask,bidQty,askQty,cumAmount,cumSum,tsString,imbalance,imbalance1, imbalance2,imbalanceAsk,imbalanceBid,cancelBid,cancelAsk, outputFile, vwap, thisSum,thisAmount
    print('bar: %s,%s,%s,%s,%s\n' % (bar.strtime, bar.open, bar.close, bar.volume, bar.amount))
    if len(bid)>0:
#        print('snapshot: %s,%s,%s,%s,%s\n' % (tsString, bid[0], ask[0], cumSum, imbalance))
        if cumSum>thisSum:
            vwap = (cumAmount - thisAmount)/(cumSum - thisSum)
        outputFile.writerow([bar.strtime, tsString,ts] + bid.tolist() + ask.tolist() + bidQty.tolist() + askQty.tolist() + [cumSum, imbalance,imbalance1, imbalance2,imbalanceAsk,imbalanceBid,cancelBid,cancelAsk, cumSum-thisSum, vwap])
    imbalance = 0.0
    imbalance1 = 0.0
    imbalance2 = 0.0
    imbalanceAsk =imbalanceBid = cancelBid = cancelAsk = 0.0
    thisSum = cumSum
    thisAmount = cumAmount


def on_tick(tick):
    global ts, bid, ask, cumAmount, cumSum, tsString, imbalance, imbalance1, imbalance2, imbalanceAsk,imbalanceBid,cancelBid,cancelAsk
    global lastTs,lastCumSum,bidQty,askQty,lastCumAmount, tickSize

    roundDigits = int(round(-log10(tickSize)))
    if ( (len(tick.bids)>0) & (len(tick.asks)>0)):
        lastBid = bid
        lastAsk = ask
        lastBidQty = bidQty
        lastAskQty = askQty
        lastCumAmount = cumAmount
        lastCumSum = cumSum
        lastTs = ts
        ts = tick.utc_time
        [bid,ask,bidQty,askQty]=updateBookWithFixedSize(tick,5, roundDigits)
        cumSum = tick.cum_volume
        cumAmount = tick.cum_amount
        tsString = tick.strtime
        volume = cumSum - lastCumSum
        if (volume>0) & (len(lastBid)>0) & (len(lastAsk)>0):
            lastMid = calcMidPrice(lastBid, lastAsk, lastBidQty, lastAskQty,1)
            lastWMid = calcMidPrice(lastBid, lastAsk, lastBidQty, lastAskQty,2)
            vwap = (cumAmount -lastCumAmount)/volume
            imbalance += volume* (vwap - lastMid)/tickSize
            imbalance1 += volume * sign(vwap - lastMid)
            #imbalance2 += volume * (vwap - lastWMid) / tickSize
            imbalance2 += volume * sign(vwap - lastWMid)
            if vwap>lastAsk[0]:
                if volume>lastAskQty[0]:
                    imbalanceAsk += volume - lastAskQty[0]
                else:
                    cancelAsk += lastAskQty[0]-volume
            if vwap<lastBid[0]:
                if volume > lastBidQty[0]:
                    imbalanceBid += volume - lastBidQty[0]
                else:
                    cancelBid += lastBidQty[0] - volume
            print('tick: %s,%s,%s,%s\n' % (tick.strtime,volume,lastMid,vwap))

md.ev_tick += on_tick
md.ev_bar += on_bar

ret = md.init(username='lafayette_yu@yahoo.com',
              password='fishman',
              mode=4,
              subscribe_symbols=symbol+'.tick,'+symbol+'.bar.60',
              start_time='2016-03-01 09:30:00',
              end_time='2016-03-03 14:59:00')


print('init result: ', ret)
md.run()

csvFile.close()