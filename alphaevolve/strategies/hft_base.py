"""
Base class for high-frequency trading strategies.
"""

class HFTStrategy:
    """
    Base class for strategies that operate on tick-level order book data.

    The LLM will generate subclasses of this class, implementing the on_tick
    method to define the trading logic.
    """
    def on_tick(self, tick, backtester):
        """
        This method is called for each tick of data from the backtester.

        Args:
            tick (pd.Series): A row from the data DataFrame, representing the
                              current order book snapshot.
            backtester (HFTBacktester): The backtester instance, which can be
                                        used to execute trades (e.g.,
                                        backtester.buy(1.0)).
        """
        raise NotImplementedError("Strategy must implement on_tick method")
