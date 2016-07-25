#!/usr/bin/env python
# encoding: utf-8


import time

from numpy import *
from collections import deque
from gmsdk import *
from StrategyUtility.signals import *
import logging
import logging.config
import pandas as pd



# 算法用到的一些常量，阀值，主要用于信号过滤

threshold = 0 #minumum position discrepancy for execution, to avoid flickering

signalList = {'imbl3': {'name': 'imbl', 'alpha': 1.0 / (1.0 + 15.0 * 60), 'refWMidQ': True, 'timeNormQ': False,
                        'filterThroughQ': False},  # \alpha =  1 / (1 + c)
              'imbl': {'name': 'imbl', 'alpha': 1.0 / (1.0 + 15.0 * 60), 'refWMidQ': True, 'timeNormQ': True,
                       'filterThroughQ': False},
              'imblThrough': {'name': 'imbl', 'alpha': 1.0 / (1.0 + 15.0 * 60), 'refWMidQ': True, 'timeNormQ': True,
                              'filterThroughQ': True},
              'midEma5': {'name': 'midEma', 'alpha': 1.0 / (1.0 + 5.0 * 60)},
              'midEma10': {'name': 'midEma', 'alpha': 1.0 / (1.0 + 10.0 * 60)},
              'midEma20': {'name': 'midEma', 'alpha': 1.0 / (1.0 + 20.0 * 60)},
              }


signalCombo = {'imbl':{'components': array(['imbl']),'weights':array([1.0/19.7]),'coef':1.0/4.0},
               'imblSpread':{'components':array(['imbl','imblThrough']),'weights':array([1.0,-1.0])/8.38,'coef':1.0/4.0},
               'midMomentum':{'components':array(['midEma5','midEma10']),'weights':array([1.0,-1.0])/0.109,'coef':2.0/4.0}
               }

class myStrat(StrategyBase):

    ''' strategy example1: MA decision price cross long MA, then place a order, temporary reverse trends place more orders '''

    def __init__(self, *args, **kwargs):
        #import pdb; pdb.set_trace()

        self.logger = logging.getLogger(__name__)
        super(myStrat, self).__init__(*args, **kwargs)
        # 策略初始化工作在这里写，从外部读取静态数据，读取策略配置参数等工作，只在策略启动初始化时执行一次。

        # 从配置文件中读取配置参数
        self.exchange = self.config.get('para', 'trade_exchange')
        self.sec_id = self.config.get('para', 'trade_symbol')
        self.symbol = ".".join([self.exchange, self.sec_id])
        self.tickSize = float(self.config.get('para','tick_size'))

        self.start_time = self.config.get('backtest','start_time')
        self.end_time = self.config.get('backtest','end_time')
        #self.subscribe(self.config.get('strategy','subscribe_symbols'))
        self.mode = self.config.get('strategy','mode')

        self.signalState = SignalState(signalList,self.tickSize)
        self.signalCombo = signalCombo
        self.targetPosition = 0
        self.maxPosition = 500
        self.longPosition = 2000
        self.shortPosition = 0
        self.initialPosition = 2000
        self.netSell = 0
        self.position = self.longPosition - self.shortPosition - self.initialPosition #actual strategy position
        self.flattener = 0

        self.last_price = 0.0
        self.trade_unit = 100
        self.maxTradeSize = 500 #max lots per order
        self.trade_count = 0
        self.trade_limit = 5
        self.window_size = self.config.getint('para', 'window_size') or 60
        self.timeperiod = self.config.getint('para', 'timeperiod') or 60
        self.bar_type = self.config.getint('para', 'bar_type') or 15
        self.close_buffer = deque(maxlen=self.window_size)
        self.orderQueue = deque()
        self.hasBuyOrder = False
        self.hasSellOrder = False
        self.bid =  NaN
        self.ask = NaN
        self.ts = ""

        ##order placing parameters
        self.aggressTick = 2
        self.cancelTick = 4

        # prepare historical bars for MA calculating
        # 从数据服务中准备一段历史数据，使得收到第一个bar后就可以按需要计算ma
        last_closes = [bar.close for bar in self.get_last_n_bars(self.symbol, self.bar_type, self.window_size)]
        last_closes.reverse()     #因为查询出来的时间是倒序排列，需要倒一下顺序
        self.close_buffer.extend(last_closes)

    # 响应bar数据到达事件
    def on_bar(self, bar):
        # 确认下bar数据是订阅的分时
        if bar.bar_type == self.bar_type:
            # 把数据加入缓存
            self.close_buffer.append(bar.close)
            # 调用策略计算
            self.algo_action()
        bartime = pd.to_datetime(bar.strtime)
        self.flattener = getFlattener(60 * bartime.hour + bartime.minute)
        self.checkRestingOrder()

    def checkRestingOrder(self):
        #cancel order if too far in the book
        if self.hasBuyOrder & (len(self.orderQueue)>0):
            order = self.get_order(self.orderQueue[0])
            print("has resting buy order")
            if (order is not None):
                if (self.bid - order.price > self.cancelTick * self.tickSize): self.cancel_order(self.orderQueue[0])
            return
        if self.hasSellOrder & (len(self.orderQueue)>0):
            order = self.get_order(self.orderQueue[0])
            print("has resting sell order")
            if (order is not None):
                if (order.price - self.ask > self.cancelTick * self.tickSize): self.cancel_order(self.orderQueue[0])
            return

   # 响应tick数据到达事件
    def on_tick(self, tick):
        # 更新市场最新成交价
        self.last_price = tick.last_price
        self.signalState.updateStates(tick)
        self.bid = self.signalState.bid[0]
        self.ask = self.signalState.ask[0]
        self.ts =  self.signalState.tsString
        self.targetPosition = roundDown(calcPosition(self.signalState.signals, self.signalCombo)*self.maxPosition*self.flattener)
        self.algo_action()

    def on_execrpt(self, execrpt):
        print(
            self.ts + "order receipt: order CL_ID: %s, order_ID: %s,  type: %s, order side：%s, order effect: %s, order volume: %s" % (
            execrpt.cl_ord_id, execrpt.order_id, execrpt.exec_type, execrpt.side, execrpt.position_effect, execrpt.volume))


    def addOrderToQueue(self, order):
        if (order.cl_ord_id in self.orderQueue):
            print(self.ts + ": order already in queue: ", order.cl_ord_id)
        else:
            self.orderQueue.append(order.cl_ord_id)
            if self.isBuyOrder(order):
                self.hasBuyOrder = True
            else:
                self.hasSellOrder = True
            print(self.ts+"order CL_ID: %s, order_ID: %s, order status: %s, price: %s, order side：%s, order effect: %s, order volume: %s"%(order.cl_ord_id, order.order_id, order.status,order.price, order.side, order.position_effect, order.volume))

    def isBuyOrder(self,order):
        if ((order.side == OrderSide_Bid)&(order.position_effect == PositionEffect_Open)) | ((order.side == OrderSide_Ask)&(order.position_effect != PositionEffect_Open)):
            return True
        else: return False

    def removeOrderFromQueue(self,order):
        if not (order.cl_ord_id in self.orderQueue):
            print(self.ts + ":remove order not in queue: ", order.cl_ord_id," ",order.order_id)
        else:
            self.orderQueue.remove(order.cl_ord_id)
            if self.isBuyOrder(order):
                self.hasBuyOrder = False
            else:
                self.hasSellOrder = False

    def updatePositionFromOrder(self,order):
        vol = order.filled_volume
        if order.position_effect == PositionEffect_Open:
            if order.side == OrderSide_Bid:
                self.longPosition += vol
            else:
                self.shortPosition += vol
                self.netSell += vol
        else:
            if order.side == OrderSide_Bid: #counterintuitive directions
                self.longPosition -= vol
                self.netSell += vol
            else: self.shortPosition -= vol
        self.position = self.longPosition-self.shortPosition-self.initialPosition
        print('pos long: %s, pos short: %s, total: %s'%(self.longPosition, self.shortPosition,self.position))


    def on_execution(self, execution):
        #打印订单成交回报信息
        a_p = self.get_position(self.exchange, self.sec_id, OrderSide_Ask)    #查询策略所持有的空仓
        b_p = self.get_position(self.exchange, self.sec_id, OrderSide_Bid)    #查询策略所持有的多仓
        # 打印持仓信息
        print("%s: received execution: %s " % (self.ts, execution.exec_type))
        self.logger.info('pos long: {0} vwap: {1}, pos short: {2}, vwap: {3}'.format(b_p.volume if b_p else 0.0,
                round(b_p.vwap,2) if b_p else 0.0,
                a_p.volume if a_p else 0.0,
                round(a_p.vwap,2) if a_p else 0.0))
        self.longPosition =b_p.volume if b_p else 0.0
        self.shortPosition = a_p.volume if a_p else 0.0
        self.position = self.longPosition - self.shortPosition - self.initialPosition

    def on_order_new(self, order):
        self.addOrderToQueue(order)

    def on_order_filled(self,order):
        print(self.ts+": order filled")
        self.updatePositionFromOrder(order)
        self.removeOrderFromQueue(order)

    def on_order_partially_filled(self, order):
        print(self.ts+": order partially filled")
        self.updatePositionFromOrder(order)

    def on_order_cancelled(self,order):
        print(self.ts + ": order cancelled")
        self.removeOrderFromQueue(order)

    def on_order_rejected(self,order):
        print(self.ts + ":order rejected reason:" + str(order.ord_rej_reason) +
              " " + str(order.ord_rej_reason_detail))
        self.removeOrderFromQueue(order)

    def on_order_stop_executed(self, order):
        print(self.ts + ": order stopped")
        self.removeOrderFromQueue(order)

    def algo_action(self):
        delta = roundDown(self.targetPosition - self.position, self.trade_unit)
        if (abs(delta)>threshold):
            self.logger.info('position to execute: %s, target: %s, has buy %s has sell %s'%(delta, self.targetPosition,self.hasBuyOrder, self.hasSellOrder))
            print('%s: position to execute: %s, target: %s, has buy %s has sell %s, flattener: %s' % (self.ts, delta, self.targetPosition, self.hasBuyOrder, self.hasSellOrder, self.flattener))
        if ((delta > threshold) & (not self.hasBuyOrder)):
            if self.hasSellOrder: self.cancel_order(self.orderQueue[0])
            vol = min(delta, self.maxTradeSize)
            price = self.ask - self.aggressTick * self.tickSize
            if (self.shortPosition < eps):
                if (max(0,self.longPosition - self.initialPosition)+delta+self.netSell > self.initialPosition):
                    print('trade blocked to avoid sell limits:long:%s, initial:%s, total sell:%s'%(self.longPosition,self.initialPosition,self.netSell))
                    return
                order = self.open_long(self.exchange, self.sec_id, price, round(vol))
                self.addOrderToQueue(order)
                print("open long")
            else:
                #  如果有空仓，且达到本次信号的交易次数上限
                if self.shortPosition > eps:
                    order = self.close_short(self.exchange, self.sec_id, price, round(min(self.shortPosition,vol)))
                    self.addOrderToQueue(order)# 平掉所有空仓
                    print("close short")

        elif ((delta < - threshold) & (not self.hasSellOrder) & (self.netSell < self.initialPosition)):
            if self.hasBuyOrder: self.cancel_order(self.orderQueue[0])
            # 没有多仓时，开空
            vol = min(-delta, self.maxTradeSize)
            price = self.bid + self.aggressTick * self.tickSize
            if (self.longPosition < eps):
                order = self.open_short_sync(self.exchange, self.sec_id, price, round(vol))
                self.addOrderToQueue(order)
            else:
                if self.longPosition > eps:
                    order = self.close_long(self.exchange, self.sec_id, price, round(min(self.longPosition,vol)))
                    print("close long here "+str(round(min(self.longPosition,vol))))
                    self.addOrderToQueue(order)
        else:       ##  其他情况，忽略不处理
            ## get positions and close if any
            #self.trade_count = 0   ## reset trade count
            pass

    def checkPosition(self):
        # 打印订单成交回报信息
        a_p = self.get_position(self.exchange, self.sec_id, OrderSide_Ask)  # 查询策略所持有的空仓
        b_p = self.get_position(self.exchange, self.sec_id, OrderSide_Bid)  # 查询策略所持有的多仓
        # 打印持仓信息
        print('pos long: {0} vwap: {1}, pos short: {2}, vwap: {3}'.format(b_p.volume if b_p else 0.0,
                                                                          round(b_p.vwap,
                                                                                2) if b_p else 0.0,
                                                                          a_p.volume if a_p else 0.0,
                                                                          round(a_p.vwap,
                                                                                2) if a_p else 0.0))
        self.longPosition = b_p.volume if b_p else 0.0
        self.shortPosition = a_p.volume if a_p else 0.0
        self.position = self.longPosition - self.shortPosition - self.initialPosition

# 策略启动入口
if __name__ == '__main__':
    #  初始化策略
    ma = myStrat(config_file='testStrategy.ini')
    #logging.config.fileConfig('testStrategy.ini')
    ma.logger.info("Strategy turtle ready, waiting for data ...")

    #import pdb; pdb.set_trace()   # python调试开关
    print('strategy ready, waiting for market data ......')
    # 策略进入运行，等待数据事件
    print('start time '+ma.start_time + ', end time'+ma.end_time)
    ret = ma.run()
    # 打印策略退出状态
    print("MA :", ma.get_strerror(ret))