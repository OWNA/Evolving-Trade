"""
Shared helpers / mixins for evolvable strategies.
"""

import backtrader as bt
from collections import deque
from typing import Dict, Any


class BaseLoggingStrategy(bt.Strategy):
    """Lightweight logger that stores equity curve for later KPIs."""

    params = (("log_equity", True),)

    def __init__(self):
        self._equity_log: deque[Dict[str, Any]] = deque()

    def next(self):
        if self.p.log_equity:
            self._equity_log.append(
                {
                    "date": self.datas[0].datetime.date(0),
                    "value": self.broker.getvalue(),
                }
            )

    # helpers for evaluator
    @property
    def equity_curve(self):
        return list(self._equity_log)
