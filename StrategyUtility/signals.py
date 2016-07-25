from numpy import *
from StrategyUtility.utility import *

resetDuration = 4*60 #4hours reset state

class SignalState():
    def __init__(self,signalList,tickSize):
        self.lastBid = []
        self.lastAsk = []
        self.lastBidQty = []
        self.lastAskQty = []
        self.bid = []
        self.bidQty = []
        self.ask = []
        self.askQty = []
        self.cumAmount = 0.0
        self.lastCumAmount = 0.0
        self.cumSum = 0.0
        self.lastCumSum = 0.0
        self.ts = NaN
        self.tsString = ''
        self.lastTs = NaN
        self.signalsNo = len(signalList)
        self.signals = dict()
        self.signalBuffer = dict()
        self.bookLength = 5
        self.multiplier = 1

        self.signalSetting = signalList
        for key in signalList:
            self.signals[key]=0.0
            self.signalBuffer[key] = 0.0
        self.tickSize = tickSize
        self.roundDigits = int(round(-log10(self.tickSize)))
    def setBookLength(self,bookLength):
        self.bookLength = bookLength

    def setMultiplier(self, mult):
        self.multiplier = mult


    def reset(self):
        self.lastBid = []
        self.lastAsk = []
        self.lastBidQty = []
        self.lastAskQty = []
        self.bid = []
        self.bidQty = []
        self.ask = []
        self.askQty = []
        self.cumAmount = 0.0
        self.lastCumAmount = 0.0
        self.cumSum = 0.0
        self.lastCumSum = 0.0
        self.ts = NaN
        self.tsString = ''
        self.lastTs = NaN
        for key in self.signals:
            self.signals[key]=0.0

    def updateStates(self,tick):
        if ((len(tick.bids) > 0) & (len(tick.asks) > 0)):
            self.lastBid = self.bid
            self.lastAsk = self.ask
            self.lastBidQty = self.bidQty
            self.lastAskQty = self.askQty
            self.lastCumAmount = self.cumAmount
            self.lastCumSum = self.cumSum
            self.lastTs =self.ts
            self.ts = tick.utc_time
            [self.bid, self.ask, self.bidQty, self.askQty] = updateBookWithFixedSize(tick,self.bookLength,self.roundDigits)
            self.cumSum = tick.cum_volume
            self.cumAmount = tick.cum_amount
            self.tsString = tick.strtime
            if (self.lastTs>0) & (self.ts - self.lastTs> resetDuration*60):
                self.reset()
                print('reset here '+str(tick.strtime))
                return
            if (len(self.lastBid) > 0) & (len(self.lastAsk) > 0):
                for key in self.signalSetting:
                    self.signals[key] = self.processSignals(self.signalSetting[key]['name'],self.signalSetting[key],self.signals[key])

    def processSignals(self, signalName, signalParam, lastValue):
        volume = self.cumSum - self.lastCumSum
        lastMid = calcMidPrice(self.lastBid, self.lastAsk, self.lastBidQty, self.lastAskQty, 1)
        lastWMid = calcMidPrice(self.lastBid, self.lastAsk, self.lastBidQty, self.lastAskQty, 2)
        if volume>0: vwap = (self.cumAmount - self.lastCumAmount) / self.multiplier/volume
        else: vwap = 0.0
        timeLag = (self.ts - self.lastTs) #seconds
        currentValue = 0
        alpha = 1 - pow(1 - signalParam['alpha'], timeLag)
        if signalName == 'imbl':
            if timeLag > 14*60: #if lag is more than 15 min discard this point
                return lastValue * (1 - alpha) + currentValue * alpha
            if signalParam['filterThroughQ'] & (vwap<=self.lastAsk[0]) & (vwap>=self.lastBid[0]):
                return lastValue * (1 - alpha) + currentValue * alpha
            if signalParam['refWMidQ']: refPrice = lastWMid
            else: refPrice = lastMid
            if signalParam['timeNormQ']: normalizer = max(1,timeLag)
            else: normalizer = 1
            currentValue = volume * sign(vwap - refPrice)/normalizer
            return lastValue*(1-alpha) + currentValue * alpha
        if signalName == 'imblCnt':
            if (timeLag > 14 * 60) | (volume<=0.0):  # if lag is more than 30 min discard this point
                return lastValue * (1 - alpha) + currentValue * alpha
            if signalParam['filterThroughQ'] & (vwap<=self.lastAsk[0]) & (vwap>=self.lastBid[0]):
                return lastValue * (1 - alpha) + currentValue * alpha
            if signalParam['refWMidQ']: refPrice = lastWMid
            else: refPrice = lastMid
            if signalParam['timeNormQ']: normalizer = max(1,timeLag)
            else: normalizer = 1
            currentValue = 1 * sign(vwap - refPrice)/normalizer
            return lastValue*(1-alpha) + currentValue * alpha
        if signalName == 'relativeValue':
            #to do!!
            return NaN
        if signalName == 'imblCancel':
            if (timeLag > 14 * 60):  # if lag is more than 15 min discard this point
                return lastValue * (1 - alpha) + currentValue * alpha
            if (vwap > self.lastAsk[0]):
                volumeBuy = min(volume,self.lastAskQty[0])
                volumeSell = 0
            elif (vwap >= self.lastBid[0]):
                volumeBuy = (volume * vwap - volume * self.lastBid[0]) / (self.lastAsk[0] - self.lastBid[0])
                volumeSell = volume - volumeBuy
            elif (vwap < self.lastBid[0]):
                volumeBuy = 0
                volumeSell =  min(volume, self.lastBidQty[0])
            else: #vwap = NaN
                volumeBuy = volumeSell = 0
            if self.ask[0] == self.lastAsk[0]:
                currentValue = - self.askQty[0] + self.lastAskQty[0] - volumeBuy
            else:
                currentValue =  self.lastAskQty[0] - volumeBuy
            if self.bid[0] == self.lastBid[0]:
                currentValue += self.bidQty[0] - self.lastBidQty[0] + volumeSell
            else:
                currentValue += - self.lastBidQty[0] + volumeSell
            return lastValue * (1 - alpha) + currentValue * alpha
        if signalName=='midEma':
            currentValue = calcMidPrice(self.bid, self.ask, self.bidQty, self.askQty, 1)
            if abs(lastValue)<eps: return currentValue
            return lastValue * (1 - alpha) + currentValue * alpha
        if signalName == 'midEmaTwtd':
            duration = signalParam['duration']
            if (timeLag >= duration) | (abs(signalParam['initial']) < eps) :
                currentValue = lastMid
            else:
                currentValue = (signalParam['initial']*(duration - timeLag)+lastMid*timeLag)/duration
            signalParam['initial'] = currentValue

            if abs(lastValue) < eps: return currentValue
            return lastValue * (1 - alpha) + currentValue * alpha

def calcPosition(signals, signalCombo):
    val = 0.0
    for item in signalCombo:
        signal = 0.0
        wts = signalCombo[item]['weights']
        sigVal = array([signals[x] for x in  signalCombo[item]['components']])
        val+= tanh(wts.dot(sigVal))*signalCombo[item]['coef']
    return val




