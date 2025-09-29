"""
A simple, proof-of-concept high-frequency strategy based on order book imbalance.
"""

from alphaevolve.strategies.hft_base import HFTStrategy

class ImbalanceStrategy(HFTStrategy):
    """
    A simple strategy that buys when the bid side has significantly more
    volume than the ask side, and sells when the opposite is true.
    """
    def __init__(self, imbalance_ratio: float = 2.0, position_size: float = 0.1):
        self.imbalance_ratio = imbalance_ratio
        self.position_size = position_size

    def on_tick(self, tick, backtester):
        """Calculates imbalance and executes trades."""
        
        # Calculate the total volume on the top 10 levels of the bid and ask sides
        bid_volume = sum(tick[f'bids[{i}].amount'] for i in range(10))
        ask_volume = sum(tick[f'asks[{i}].amount'] for i in range(10))

        if ask_volume > 0 and bid_volume / ask_volume > self.imbalance_ratio:
            # If we're not already long, go long
            if backtester.position <= 0:
                backtester.buy(self.position_size)
        elif bid_volume > 0 and ask_volume / bid_volume > self.imbalance_ratio:
            # If we're not already short, go short (or exit long)
            if backtester.position >= 0:
                backtester.sell(self.position_size)
