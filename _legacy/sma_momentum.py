from collections import deque
import backtrader as bt

from alphaevolve.strategies.base import BaseLoggingStrategy


class SMAMomentum(BaseLoggingStrategy):
    params = dict(leverage=0.9, sma_period=210)

    def __init__(self):
        super().__init__()
        self.sma = {
            d._name: bt.indicators.SMA(d.close, period=self.p.sma_period)
            for d in self.datas
        }
        self.last_month = -1

    # === EVOLVE-BLOCK: decision_logic =================================
    def next(self):
        super().next()

        today = self.datas[0].datetime.date(0)
        if today.month == self.last_month:
            return
        self.last_month = today.month

        tradable = [
            d for d in self.datas if len(self.sma[d._name]) >= self.p.sma_period
        ]
        longs = [d for d in tradable if d.close[0] > self.sma[d._name][0]]

        weight = self.p.leverage / len(longs) if longs else 0.0
        for d in self.datas:
            self.order_target_percent(d, target=weight if d in longs else 0.0)
    # === END EVOLVE-BLOCK =============================================


STRATEGY_CLASS = SMAMomentum
