"""
Extended HFT strategy base class for real-time trading with evolution integration.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timezone
import pandas as pd
import numpy as np

from ...strategies.hft_base import HFTStrategy
from ..data.orderbook import RealtimeOrderbook, OrderbookLevel
from ..trading.paper_trader import PaperTrader, Order


logger = logging.getLogger(__name__)


class RealtimeHFTStrategy(HFTStrategy):
    """
    Extended HFT strategy base class for real-time execution.
    
    Integrates with evolution system and provides real-time trading capabilities.
    """
    
    def __init__(self, name: str = "RealtimeHFTStrategy"):
        """
        Initialize real-time HFT strategy.
        
        Args:
            name: Strategy name for identification
        """
        self.name = name
        self.paper_trader: Optional[PaperTrader] = None
        self.orderbook: Optional[RealtimeOrderbook] = None
        
        # Strategy state
        self.is_running = False
        self.last_signal_time = None
        self.position_size = 0.0
        self.max_position_size = 1.0  # Maximum position in BTC
        self.min_spread_threshold = 0.5  # Minimum spread to trade (USDT)
        
        # Performance tracking
        self.signals_generated = 0
        self.orders_placed = 0
        self.trades_executed = 0
        self.start_time = None
        
        # Risk management
        self.max_drawdown_pct = 0.05  # 5% max drawdown
        self.daily_loss_limit = 1000.0  # Max daily loss in USDT
        self.max_orders_per_minute = 60
        
        # Order tracking
        self.recent_orders: List[datetime] = []
        self.active_orders: Dict[str, Order] = {}
    
    def set_paper_trader(self, trader: PaperTrader):
        """Set the paper trader instance."""
        self.paper_trader = trader
        logger.info(f"Paper trader connected to strategy: {self.name}")
    
    def set_orderbook(self, orderbook: RealtimeOrderbook):
        """Set the orderbook instance."""
        self.orderbook = orderbook
        if self.paper_trader:
            self.paper_trader.set_orderbook(orderbook)
    
    async def on_orderbook_update(self, orderbook_data: Dict[str, Any]):
        """
        Handle real-time orderbook updates.
        
        This is the main entry point for real-time strategy execution.
        Called by the WebSocket manager for each orderbook update.
        
        Args:
            orderbook_data: Raw orderbook data from Bybit WebSocket
        """
        try:
            if not self.is_running:
                return
            
            # Update orderbook
            if self.orderbook:
                updated = self.orderbook.process_message(orderbook_data)
                if not updated:
                    return
                
                # Update paper trader orderbook
                if self.paper_trader:
                    self.paper_trader.set_orderbook(self.orderbook)
                
                # Generate trading signal
                await self._process_tick()
                
        except Exception as e:
            logger.error(f"Error processing orderbook update: {e}")
    
    async def _process_tick(self):
        """Process a single tick and generate trading signals."""
        if not self.orderbook or not self.paper_trader:
            return
        
        # Check risk limits
        if not self._check_risk_limits():
            return
        
        # Check rate limits
        if not self._check_rate_limits():
            return
        
        try:
            # Create tick data compatible with existing HFT framework
            tick = self._create_tick_data()
            if tick is not None:
                # Call the strategy's on_tick method
                await self.on_tick_async(tick, self.paper_trader)
                self.signals_generated += 1
                self.last_signal_time = datetime.now(timezone.utc)
                
        except Exception as e:
            logger.error(f"Error in strategy on_tick: {e}")
    
    def _create_tick_data(self) -> Optional[pd.Series]:
        """
        Create tick data compatible with existing HFT backtester format.
        
        Returns:
            pandas Series with orderbook data in expected format
        """
        if not self.orderbook:
            return None
        
        best_bid = self.orderbook.get_best_bid()
        best_ask = self.orderbook.get_best_ask()
        
        if not best_bid or not best_ask:
            return None
        
        # Get multiple levels for comprehensive data
        bid_levels = self.orderbook.get_sorted_levels('bid', 10)
        ask_levels = self.orderbook.get_sorted_levels('ask', 10)
        
        # Create tick data in format expected by HFT strategies
        tick_data = {}
        
        # Best bid/ask (level 0)
        tick_data['bids[0].price'] = best_bid.price
        tick_data['bids[0].size'] = best_bid.size
        tick_data['asks[0].price'] = best_ask.price
        tick_data['asks[0].size'] = best_ask.size
        
        # Additional levels
        for i, bid_level in enumerate(bid_levels[:10]):
            tick_data[f'bids[{i}].price'] = bid_level.price
            tick_data[f'bids[{i}].size'] = bid_level.size
        
        for i, ask_level in enumerate(ask_levels[:10]):
            tick_data[f'asks[{i}].price'] = ask_level.price
            tick_data[f'asks[{i}].size'] = ask_level.size
        
        # Additional market data
        tick_data['mid_price'] = self.orderbook.get_mid_price()
        tick_data['spread'] = self.orderbook.get_spread()
        tick_data['timestamp'] = self.orderbook.last_update_time
        
        # Liquidity metrics
        stats = self.orderbook.get_liquidity_stats()
        tick_data['total_bid_volume'] = stats.get('total_bid_volume', 0)
        tick_data['total_ask_volume'] = stats.get('total_ask_volume', 0)
        tick_data['bid_count'] = stats.get('bid_count', 0)
        tick_data['ask_count'] = stats.get('ask_count', 0)
        
        return pd.Series(tick_data)
    
    async def on_tick_async(self, tick: pd.Series, trader: PaperTrader):
        """
        Async wrapper for the on_tick method.
        
        Override this method in evolved strategies for async trading logic.
        Falls back to sync on_tick if not overridden.
        
        Args:
            tick: Market tick data
            trader: Paper trader instance for order execution
        """
        # Try async version first, fall back to sync
        try:
            await self.on_tick_realtime(tick, trader)
        except NotImplementedError:
            # Fall back to sync version for compatibility
            self.on_tick(tick, trader)
    
    async def on_tick_realtime(self, tick: pd.Series, trader: PaperTrader):
        """
        Real-time tick processing method.
        
        Override this method in evolved strategies for async trading logic.
        
        Args:
            tick: Market tick data with L2 orderbook information
            trader: Paper trader for order execution
        """
        raise NotImplementedError("Strategy must implement on_tick_realtime method")
    
    def on_tick(self, tick: pd.Series, backtester):
        """
        Sync tick processing (compatibility with existing framework).
        
        Args:
            tick: Market tick data
            backtester: Backtester or paper trader instance
        """
        # Default implementation - override in evolved strategies
        pass
    
    def _check_risk_limits(self) -> bool:
        """Check if strategy is within risk limits."""
        if not self.paper_trader:
            return True
        
        # Check drawdown limit
        account_summary = self.paper_trader.get_account_summary()
        if account_summary['total_pnl'] < -self.daily_loss_limit:
            logger.warning(f"Daily loss limit reached: {account_summary['total_pnl']}")
            return False
        
        # Check position size
        position = self.paper_trader.get_position(self.orderbook.symbol if self.orderbook else "BTCUSDT")
        if position and abs(position.size) >= self.max_position_size:
            return False
        
        return True
    
    def _check_rate_limits(self) -> bool:
        """Check if strategy is within rate limits."""
        now = datetime.now(timezone.utc)
        
        # Clean old orders (older than 1 minute)
        self.recent_orders = [
            order_time for order_time in self.recent_orders 
            if (now - order_time).total_seconds() < 60
        ]
        
        # Check rate limit
        if len(self.recent_orders) >= self.max_orders_per_minute:
            return False
        
        return True
    
    async def buy(self, size: float, price: Optional[float] = None, 
                 order_type: str = "Market") -> Optional[Order]:
        """
        Execute a buy order.
        
        Args:
            size: Order size in BTC
            price: Limit price (optional for market orders)
            order_type: 'Market' or 'Limit'
            
        Returns:
            Order object if successful
        """
        if not self.paper_trader or not self.orderbook:
            logger.error("Paper trader or orderbook not available")
            return None
        
        # Check minimum spread
        spread = self.orderbook.get_spread()
        if spread and spread < self.min_spread_threshold:
            return None
        
        try:
            order = await self.paper_trader.place_order(
                symbol=self.orderbook.symbol,
                side="Buy",
                order_type=order_type,
                quantity=size,
                price=price
            )
            
            if order:
                self.orders_placed += 1
                self.recent_orders.append(datetime.now(timezone.utc))
                self.active_orders[order.order_id] = order
                logger.info(f"Buy order placed: {order}")
            
            return order
            
        except Exception as e:
            logger.error(f"Failed to place buy order: {e}")
            return None
    
    async def sell(self, size: float, price: Optional[float] = None, 
                  order_type: str = "Market") -> Optional[Order]:
        """
        Execute a sell order.
        
        Args:
            size: Order size in BTC
            price: Limit price (optional for market orders)
            order_type: 'Market' or 'Limit'
            
        Returns:
            Order object if successful
        """
        if not self.paper_trader or not self.orderbook:
            logger.error("Paper trader or orderbook not available")
            return None
        
        # Check minimum spread
        spread = self.orderbook.get_spread()
        if spread and spread < self.min_spread_threshold:
            return None
        
        try:
            order = await self.paper_trader.place_order(
                symbol=self.orderbook.symbol,
                side="Sell",
                order_type=order_type,
                quantity=size,
                price=price
            )
            
            if order:
                self.orders_placed += 1
                self.recent_orders.append(datetime.now(timezone.utc))
                self.active_orders[order.order_id] = order
                logger.info(f"Sell order placed: {order}")
            
            return order
            
        except Exception as e:
            logger.error(f"Failed to place sell order: {e}")
            return None
    
    def start(self):
        """Start the strategy."""
        self.is_running = True
        self.start_time = datetime.now(timezone.utc)
        logger.info(f"Strategy started: {self.name}")
    
    def stop(self):
        """Stop the strategy."""
        self.is_running = False
        logger.info(f"Strategy stopped: {self.name}")
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get strategy performance statistics."""
        runtime = (datetime.now(timezone.utc) - self.start_time).total_seconds() if self.start_time else 0
        
        account_summary = self.paper_trader.get_account_summary() if self.paper_trader else {}
        
        return {
            'name': self.name,
            'runtime_seconds': runtime,
            'is_running': self.is_running,
            'signals_generated': self.signals_generated,
            'orders_placed': self.orders_placed,
            'trades_executed': account_summary.get('total_trades', 0),
            'total_pnl': account_summary.get('total_pnl', 0),
            'win_rate': 0,  # TODO: Calculate from trade history
            'sharpe_ratio': 0,  # TODO: Calculate from returns
        }
    
    def __repr__(self):
        stats = self.get_performance_stats()
        return (f"{self.name}(running={stats['is_running']}, "
                f"signals={stats['signals_generated']}, "
                f"orders={stats['orders_placed']}, "
                f"pnl={stats['total_pnl']:.2f})")


class SimpleSpreadStrategy(RealtimeHFTStrategy):
    """
    Example real-time strategy: Simple spread trading.
    
    This is a basic example that demonstrates the real-time strategy framework.
    """
    
    def __init__(self, spread_threshold: float = 10.0, position_size: float = 0.001):
        """
        Initialize spread strategy.
        
        Args:
            spread_threshold: Minimum spread to trigger trades (USDT)
            position_size: Order size per trade (BTC)
        """
        super().__init__("SimpleSpreadStrategy")
        self.spread_threshold = spread_threshold
        self.position_size = position_size
        self.last_trade_time = None
        self.min_trade_interval = 5.0  # Minimum seconds between trades
    
    async def on_tick_realtime(self, tick: pd.Series, trader: PaperTrader):
        """
        Simple spread-based trading logic.
        
        Buys when spread is wide and we don't have a long position.
        Sells when spread is narrow and we have a long position.
        """
        try:
            spread = tick.get('spread', 0)
            mid_price = tick.get('mid_price', 0)
            
            if spread <= 0 or mid_price <= 0:
                return
            
            # Check time since last trade
            now = datetime.now(timezone.utc)
            if (self.last_trade_time and 
                (now - self.last_trade_time).total_seconds() < self.min_trade_interval):
                return
            
            # Get current position
            position = trader.get_position("BTCUSDT")
            current_size = position.size if position else 0
            
            # Trading logic
            if spread > self.spread_threshold and current_size <= 0:
                # Wide spread, consider buying
                order = await self.buy(self.position_size, order_type="Market")
                if order:
                    self.last_trade_time = now
                    
            elif spread < self.spread_threshold / 2 and current_size > 0:
                # Narrow spread, consider selling if long
                sell_size = min(self.position_size, current_size)
                order = await self.sell(sell_size, order_type="Market")
                if order:
                    self.last_trade_time = now
                    
        except Exception as e:
            logger.error(f"Error in spread strategy: {e}")


if __name__ == "__main__":
    # Example usage
    import asyncio
    from ..data.orderbook import RealtimeOrderbook
    from ..trading.paper_trader import PaperTrader
    
    async def main():
        # Create components
        strategy = SimpleSpreadStrategy(spread_threshold=5.0)
        trader = PaperTrader()
        orderbook = RealtimeOrderbook("BTCUSDT")
        
        # Connect components
        strategy.set_paper_trader(trader)
        strategy.set_orderbook(orderbook)
        
        # Simulate orderbook update
        snapshot_data = {
            "type": "snapshot",
            "b": [["45000.0", "1.5"], ["44995.0", "2.0"]],
            "a": [["45010.0", "1.0"], ["45015.0", "1.2"]],  # Wide spread
            "u": 12345,
            "seq": 1,
            "timestamp": 1640000000000
        }
        
        strategy.start()
        await strategy.on_orderbook_update(snapshot_data)
        
        print("Strategy performance:", strategy.get_performance_stats())
        print("Account summary:", trader.get_account_summary())
    
    asyncio.run(main())