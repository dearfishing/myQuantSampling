from gmsdk import *
from numpy import *

class Sampling(StrategyBase):

    ''' strategy example1: MA decision price cross long MA, then place a order, temporary reverse trends place more orders '''

    def __init__(self, *args, **kwargs):
        #import pdb; pdb.set_trace()
        super(Sampling, self).__init__(*args, **kwargs)
        # 策略初始化工作在这里写，从外部读取静态数据，读取策略配置参数等工作，只在策略启动初始化时执行一次。
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
        self.tickSize = 0.01
        self.ts = NaN
        self.lastTs = NaN
        self.imbalance = 0.0
        self.imbalance1 = 0.0
        self.outputFile = open('saveData.csv', 'w')

    # 响应bar数据到达事件
    def on_bar(self, bar):
        print('bar: %s,%s,%s,%s,%s\n' % (bar.strtime, bar.open, bar.close, bar.volume, bar.amount))
        print('last snapshot: %s,%5.2f,%5.2f,%d,%d\n' % (self.ts, self.bid[0], self.ask[0], self.cumAmount, self.cumSum))
        self.outputFile.write([bar.strtime, self.tsString] + self.bid + self.ask + self.bidQty + self.askQty + [self.cumAmount, self.imbalance])
        self.imbalance = 0.0
        self.imbalance1 = 0.0

    def on_tick(self,tick):
        if (tick.utc_time>self.lastTs) & (tick.cum_amount>=self.lastCumAmount):
            self.lastBid = self.bid
            self.lastAsk = self.ask
            self.lastBidQty = self.bidQty
            self.lastAskQty = self.askQty
            self.lastCumAmount = self.cumAmount
            self.lastCumSum = self.cumSum
            self.lastTs = self.ts
            lastMid = (self.lastBid[0] + self.lastAsk[0])/2

            self.ts = tick.utc_time
            self.bid = list(tick.bids)[:,0]
            self.ask= list(tick.asks)[:,0]
            self.bidQty = list(tick.bids)[:,1]
            self.askQty = list(tick.asks)[:,1]
            self.cumSum = tick.cum_Sum
            self.cumAmount = tick.cum_amount
            self.tsString = tick.strtime
            volume = self.cumAmount - self.lastCumAmount
            if (volume>0):
                vwap = (self.cumSum -self.lastCumSum)/volume
                self.imbalance += volume*(vwap - lastMid)/self.tickSize
                self.imbalance1 += volume * sign(vwap - lastMid)


if __name__ == '__main__':
    mystrategy = Sampling(
        username='lafayette_yu@yahoo.com',
        password='fishman',
        strategy_id='strategy_1',
        subscribe_symbols='SZSE.300017.tick,SZSE.300017.bar.60',
        mode=4,
        td_addr='localhost:8001'
    )
    ret = mystrategy.backtest_config(
        start_time='2016-05-27 09:30:00',
        end_time='2016-05-27 10:00:00',
        initial_cash=1000000,
        transaction_ratio=1,
        commission_ratio=0,
        slippage_ratio=0,
        price_type=1,
        bench_symbol='SHSE.000300')#基准=沪深300
    print('config status: ', ret)
    ret = mystrategy.run()
    print('exit code: ', ret, get_strerror(ret))
