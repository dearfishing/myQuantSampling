from gmsdk.api import md
from numpy import *
import csv
from StrategyUtility.utility import *
from StrategyUtility.signals import *


bookLen = 5
st = '2016-05-03 09:00:00'
# et='2016-05-03 10:00:00'
et = '2016-07-01 15:30:00'
#et='2016-06-17 15:00:00'
printTickQ=False
useFuture=False
outputPath = 'Data\\'
outputPath = 'Data2\\'

    # 响应bar数据到达事件
symbolList = ['SZSE.002241',  # gegf 0.03
              'SHSE.601166']  #
tickSize = 0.01

# symbolList =[ 'SHSE.510050', 'SHSE.510300']
# tickSize = 0.001


multiplier = 1

#for stock
signalList = {'imbl3':{'name':'imbl','alpha': 1.0/(1.0+15.0*60),'refWMidQ':True,'timeNormQ':False,'filterThroughQ':False},#\alpha =  1 / (1 + c)
              'imbl3_30':{'name':'imbl','alpha': 1.0/(1.0+30.0*60),'refWMidQ':True,'timeNormQ':False,'filterThroughQ':False},
              'imbl': {'name':'imbl','alpha': 1.0/(1.0+15.0*60),'refWMidQ':True,'timeNormQ':True,'filterThroughQ':False},
              'imblThrough':{'name':'imbl','alpha': 1.0/(1.0+15.0*60),'refWMidQ':True,'timeNormQ':True,'filterThroughQ':True},
              'midEma5':{'name':'midEma','alpha': 1.0/(1.0+ 5.0*60)},
              'midEma10':{'name':'midEma','alpha': 1.0/(1.0+ 10.0*60)},
              'midEma20':{'name':'midEma','alpha':1.0/(1.0+ 20.0*60)},
              'imblCnt3': {'name': 'imblCnt', 'alpha': 1.0 / (1.0 + 15.0 * 60), 'refWMidQ': True, 'timeNormQ': False,
                           'filterThroughQ': False},  # \alpha =  1 / (1 + c)
              'imblCnt3_30': {'name': 'imblCnt', 'alpha': 1.0 / (1.0 + 30.0 * 60), 'refWMidQ': True, 'timeNormQ': False,
                           'filterThroughQ': False},  # \alpha =  1 / (1 + c)
              'imblCnt': {'name': 'imblCnt', 'alpha': 1.0 / (1.0 + 15.0 * 60), 'refWMidQ': True, 'timeNormQ': True,
                          'filterThroughQ': False},
              'imblCntThrough': {'name': 'imblCnt', 'alpha': 1.0 / (1.0 + 15.0 * 60), 'refWMidQ': True,
                                  'timeNormQ': True,
                                  'filterThroughQ': True},
              'imblCncl': {'name': 'imblCancel', 'alpha': 1.0 / (1.0 + 15.0 * 60)},
              'imblCncl_30': {'name': 'imblCancel', 'alpha': 1.0 / (1.0 + 30.0 * 60)}
              }

if useFuture:
    signalList = {'imbl3':{'name':'imbl','alpha': 1.0/(1.0+15.0*60),'refWMidQ':True,'timeNormQ':False,'filterThroughQ':False},  #\alpha =  1 / (1 + c)
                  'imbl': {'name':'imbl','alpha': 1.0/(1.0+15.0*60),'refWMidQ':True,'timeNormQ':True,'filterThroughQ':False},
                  'imblThrough3':{'name':'imbl','alpha': 1.0/(1.0+15.0*60),'refWMidQ':True,'timeNormQ':False,'filterThroughQ':True},
                  'imblCncl': {'name': 'imblCancel', 'alpha': 1.0 / (1.0 + 15.0 * 60)},
                  'imblCnt3': {'name': 'imblCnt', 'alpha': 1.0 / (1.0 + 15.0 * 60), 'refWMidQ': True, 'timeNormQ': False,
                               'filterThroughQ': False},  # \alpha =  1 / (1 + c)
                  'imblCnt': {'name': 'imblCnt', 'alpha': 1.0 / (1.0 + 15.0 * 60), 'refWMidQ': True, 'timeNormQ': True,
                              'filterThroughQ': False},
                  'imblCntThrough3': {'name': 'imblCnt', 'alpha': 1.0 / (1.0 + 15.0 * 60), 'refWMidQ': True, 'timeNormQ': False,
                                      'filterThroughQ': True},
                  'wMidEma5':{'name':'midEmaTwtd','alpha': 1.0/(1.0+ 5.0*60), 'duration':60, 'initial':0},
                  'wMidEma10':{'name':'midEmaTwtd','alpha': 1.0/(1.0+ 10.0*60), 'duration':60, 'initial':0},
                  'wMidEma20': {'name': 'midEmaTwtd', 'alpha': 1.0 / (1.0 + 20.0 * 60), 'duration': 60, 'initial': 0}
                  }
    bookLen = 1





signalState = SignalState(signalList, tickSize)
signalState.setBookLength(bookLen)
signalState.setMultiplier(multiplier)

header = ['barTime','mid']+ list(signalState.signals.keys())

def on_bar(bar):
    global signalState
    print('bar: %s,%s,%s,%s,%s\n' % (bar.strtime, bar.open, bar.close, bar.volume, bar.amount))
    print(signalState.signals)
    if (len(signalState.bid)>0) & (len(signalState.ask)>0):
        mid = (signalState.bid[0]+signalState.ask[0])/2
    else: mid = NaN
    outputFile.writerow([bar.strtime, mid] + list(signalState.signals.values()))

def on_tick(tick):
    global signalState
    roundDigits = int(round(-log10(tickSize)))
    signalState.updateStates(tick)
    if (signalState.cumSum - signalState.lastCumSum)>0:
        vwap = round((signalState.cumAmount - signalState.lastCumAmount)/multiplier/(signalState.cumSum - signalState.lastCumSum),2)
    else:
        vwap = NaN
    if printTickQ:
        print('tick: %s, last:%s, vwap:%s, high:%s, low:%s, bid:%s, ask:%s, book:%s,%s, cumvol:%s' % (tick.strtime,tick.last_price,vwap,tick.high,tick.low,tick.bids[0][0],tick.asks[0][0],tick.bids[0][1],tick.asks[0][1],tick.cum_volume))

def on_event(evt):
    global signalState
    print('reset here\n')
    signalState.reset()

md.ev_tick += on_tick
md.ev_bar += on_bar
md.ev_event += on_event


#outputFile = open('saveData.csv', 'w')
for symbol in symbolList:
    print(symbol)
    print('printTick:',printTickQ)
    if printTickQ:
        csvFile = open(outputPath+'temp.csv','w',newline='')
    else:csvFile = open(outputPath+symbol.split(".")[1]+'.csv','w',newline='')
    outputFile = csv.writer(csvFile, delimiter=',',
                            quotechar='|', quoting=csv.QUOTE_MINIMAL)
    outputFile.writerow(header)

    ret = md.init(username='lafayette_yu@yahoo.com',
                  password='fishman',
                  mode=4,
                  subscribe_symbols=symbol+'.tick,'+symbol+'.bar.60',
                  start_time=st,
                  end_time=et
                  )


    print('init result: ', ret)
    md.run()
    md.close()
    signalState.reset()

    csvFile.close()