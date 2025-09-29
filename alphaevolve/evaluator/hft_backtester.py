"""
A simple, event-driven backtester for high-frequency, tick-level data.
"""

import pandas as pd
import numpy as np

class HFTBacktester:
    """
    A simple backtester for high-frequency, single-asset strategies.

    Processes a DataFrame of tick data, executes trades based on strategy
    signals, and tracks portfolio performance.
    """
    def __init__(self, data: pd.DataFrame, strategy, initial_cash: float = 100_000):
        self.data = data
        self.strategy = strategy
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.position = 0.0
        self.equity_curve = []
        self.trades = []
        self._current_tick = 0

    def run(self):
        """Runs the backtest simulation."""
        for i, (timestamp, tick) in enumerate(self.data.iterrows()):
            self._current_tick = i
            self.strategy.on_tick(tick, self)
            
            # Update equity
            current_price = (tick['asks[0].price'] + tick['bids[0].price']) / 2
            equity = self.cash + self.position * current_price
            self.equity_curve.append({'timestamp': timestamp, 'equity': equity})

        return pd.DataFrame(self.equity_curve).set_index('timestamp')

    def buy(self, size: float):
        """Executes a market buy order."""
        if size <= 0:
            return
        
        # For simplicity, we assume we can always get the best ask price
        price = self.data.iloc[self._current_tick]['asks[0].price']
        cost = price * size
        
        if self.cash >= cost:
            self.cash -= cost
            self.position += size
            self.trades.append({
                'type': 'buy', 'price': price, 'size': size, 
                'timestamp': self.data.index[self._current_tick]
            })

    def sell(self, size: float):
        """Executes a market sell order."""
        if size <= 0:
            return
            
        # For simplicity, we assume we can always get the best bid price
        price = self.data.iloc[self._current_tick]['bids[0].price']
        
        if self.position >= size:
            self.cash += price * size
            self.position -= size
            self.trades.append({
                'type': 'sell', 'price': price, 'size': size,
                'timestamp': self.data.index[self._current_tick]
            })
