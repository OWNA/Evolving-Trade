from collections import deque
import backtrader as bt

from alphaevolve.strategies.base import BaseLoggingStrategy


class VolAdjMomentum(BaseLoggingStrategy):
    params = dict(leverage=0.95, lookback=63)

    def __init__(self):
        super().__init__()
        self.roc = {
            d._name: bt.indicators.RateOfChange(d.close, period=self.p.lookback)
            for d in self.datas
        }
        self.std = {
            d._name: bt.indicators.StandardDeviation(d.close, period=self.p.lookback)
            for d in self.datas
        }

    # === EVOLVE-BLOCK: decision_logic =================================
    def next(self):
        super().next()
        scores = {}
        for d in self.datas:
            if len(self.roc[d._name]) < self.p.lookback:
                continue
            momentum = self.roc[d._name][0]
            vol = self.std[d._name][0] or 1e-9
            scores[d] = momentum / vol

        top = [d for d, s in scores.items() if s > 0]
        n = len(top)
        w = self.p.leverage / n if n else 0
        for d in self.datas:
            self.order_target_percent(d, target=w if d in top else 0)
    # === END EVOLVE-BLOCK =============================================


STRATEGY_CLASS = VolAdjMomentum
