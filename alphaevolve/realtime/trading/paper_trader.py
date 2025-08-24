"""
Paper trading engine using Bybit demo API with real orderbook data.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from pathlib import Path
import yaml
from pybit.unified_trading import HTTP

from ..data.orderbook import RealtimeOrderbook, OrderbookLevel


logger = logging.getLogger(__name__)


class Order:
    """Represents a trading order."""
    
    def __init__(self, order_id: str, symbol: str, side: str, order_type: str, 
                 quantity: float, price: Optional[float] = None):
        self.order_id = order_id
        self.symbol = symbol
        self.side = side  # 'Buy' or 'Sell'
        self.order_type = order_type  # 'Market' or 'Limit'
        self.quantity = quantity
        self.price = price
        self.status = 'New'
        self.filled_quantity = 0.0
        self.remaining_quantity = quantity
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = self.created_at
        
    def __repr__(self):
        return (f"Order(id={self.order_id}, {self.side} {self.quantity} "
                f"{self.symbol} @ {self.price or 'Market'}, status={self.status})")


class Position:
    """Represents a trading position."""
    
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.size = 0.0  # Positive for long, negative for short
        self.entry_price = 0.0
        self.unrealized_pnl = 0.0
        self.realized_pnl = 0.0
        self.total_cost = 0.0
        
    def update_position(self, fill_size: float, fill_price: float):
        """Update position with a new fill."""
        if self.size == 0:
            # Opening new position
            self.size = fill_size
            self.entry_price = fill_price
            self.total_cost = abs(fill_size * fill_price)
        else:
            # Adding to or reducing position
            if (self.size > 0 and fill_size > 0) or (self.size < 0 and fill_size < 0):
                # Adding to position
                new_total_cost = self.total_cost + abs(fill_size * fill_price)
                new_size = self.size + fill_size
                self.entry_price = new_total_cost / abs(new_size) if new_size != 0 else 0
                self.size = new_size
                self.total_cost = new_total_cost
            else:
                # Reducing position or reversing
                if abs(fill_size) >= abs(self.size):
                    # Position reversal or full close
                    pnl = self.size * (fill_price - self.entry_price)
                    self.realized_pnl += pnl
                    
                    remaining_size = fill_size + self.size  # Remaining after closing
                    if remaining_size != 0:
                        # Position reversal
                        self.size = remaining_size
                        self.entry_price = fill_price
                        self.total_cost = abs(remaining_size * fill_price)
                    else:
                        # Full close
                        self.size = 0
                        self.entry_price = 0
                        self.total_cost = 0
                else:
                    # Partial close
                    close_size = -fill_size  # Amount being closed
                    pnl = close_size * (fill_price - self.entry_price)
                    self.realized_pnl += pnl
                    self.size += fill_size
    
    def update_unrealized_pnl(self, current_price: float):
        """Update unrealized PnL based on current price."""
        if self.size != 0:
            self.unrealized_pnl = self.size * (current_price - self.entry_price)
        else:
            self.unrealized_pnl = 0.0
    
    def get_total_pnl(self) -> float:
        """Get total PnL (realized + unrealized)."""
        return self.realized_pnl + self.unrealized_pnl
    
    def __repr__(self):
        return (f"Position({self.symbol}, size={self.size:.4f}, "
                f"entry={self.entry_price:.2f}, PnL={self.get_total_pnl():.2f})")


class PaperTrader:
    """
    Paper trading engine using Bybit demo API.
    
    Combines real market data with simulated order execution.
    """
    
    def __init__(self, credentials_path: Optional[str] = None):
        """
        Initialize paper trader.
        
        Args:
            credentials_path: Path to credentials YAML file
        """
        self.credentials_path = credentials_path or "credentials/bybit_demo.yaml"
        self.session = None
        
        # Trading state
        self.positions: Dict[str, Position] = {}
        self.orders: Dict[str, Order] = {}
        self.balance = 100000.0  # Default demo balance in USDT
        self.order_counter = 0
        
        # Real-time data
        self.current_orderbook: Optional[RealtimeOrderbook] = None
        
        # Trading statistics
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_fees = 0.0
        
        self._load_credentials()
    
    def _load_credentials(self):
        """Load API credentials from YAML file."""
        try:
            creds_path = Path(self.credentials_path)
            if creds_path.exists():
                with open(creds_path, 'r') as f:
                    creds = yaml.safe_load(f)
                
                # Initialize Bybit demo session
                self.session = HTTP(
                    testnet=False,  # Use mainnet endpoint but demo account
                    api_key=creds.get('api_key'),
                    api_secret=creds.get('api_secret'),
                    demo=True  # Use demo trading endpoint
                )
                
                logger.info("Successfully loaded demo trading credentials")
            else:
                logger.warning(f"Credentials file not found: {creds_path}")
                logger.info("Paper trader will run in simulation-only mode")
                
        except Exception as e:
            logger.error(f"Failed to load credentials: {e}")
            logger.info("Paper trader will run in simulation-only mode")
    
    def set_orderbook(self, orderbook: RealtimeOrderbook):
        """Set the current orderbook for trade simulation."""
        self.current_orderbook = orderbook
        self._update_unrealized_pnl()
    
    def _update_unrealized_pnl(self):
        """Update unrealized PnL for all positions."""
        if not self.current_orderbook:
            return
            
        mid_price = self.current_orderbook.get_mid_price()
        if mid_price:
            for position in self.positions.values():
                position.update_unrealized_pnl(mid_price)
    
    def _generate_order_id(self) -> str:
        """Generate unique order ID."""
        self.order_counter += 1
        return f"paper_order_{self.order_counter}_{int(datetime.now().timestamp())}"
    
    async def place_order(self, symbol: str, side: str, order_type: str, 
                         quantity: float, price: Optional[float] = None) -> Optional[Order]:
        """
        Place a trading order.
        
        Args:
            symbol: Trading symbol (e.g., BTCUSDT)
            side: 'Buy' or 'Sell'
            order_type: 'Market' or 'Limit'
            quantity: Order quantity
            price: Order price (required for limit orders)
            
        Returns:
            Order object if successful, None otherwise
        """
        try:
            order_id = self._generate_order_id()
            order = Order(order_id, symbol, side, order_type, quantity, price)
            
            # Validate order
            if order_type == 'Limit' and price is None:
                logger.error("Price required for limit orders")
                return None
            
            if quantity <= 0:
                logger.error("Quantity must be positive")
                return None
            
            # Store order
            self.orders[order_id] = order
            
            # Try to execute immediately for market orders or marketable limit orders
            if order_type == 'Market':
                await self._execute_market_order(order)
            elif order_type == 'Limit':
                # Check if limit order is immediately marketable
                if await self._check_marketable_limit(order):
                    await self._execute_limit_order(order)
                else:
                    order.status = 'Open'
                    logger.info(f"Limit order placed: {order}")
            
            return order
            
        except Exception as e:
            logger.error(f"Failed to place order: {e}")
            return None
    
    async def _execute_market_order(self, order: Order):
        """Execute a market order using current orderbook."""
        if not self.current_orderbook:
            logger.error("No orderbook available for market order execution")
            order.status = 'Rejected'
            return
        
        try:
            if order.side == 'Buy':
                best_ask = self.current_orderbook.get_best_ask()
                if best_ask:
                    fill_price = best_ask.price
                else:
                    logger.error("No asks available for buy market order")
                    order.status = 'Rejected'
                    return
            else:
                best_bid = self.current_orderbook.get_best_bid()
                if best_bid:
                    fill_price = best_bid.price
                else:
                    logger.error("No bids available for sell market order")
                    order.status = 'Rejected'
                    return
            
            # Execute the fill
            await self._fill_order(order, order.quantity, fill_price)
            logger.info(f"Market order executed: {order}")
            
        except Exception as e:
            logger.error(f"Failed to execute market order: {e}")
            order.status = 'Rejected'
    
    async def _check_marketable_limit(self, order: Order) -> bool:
        """Check if a limit order is immediately marketable."""
        if not self.current_orderbook:
            return False
        
        if order.side == 'Buy':
            best_ask = self.current_orderbook.get_best_ask()
            return best_ask and order.price >= best_ask.price
        else:
            best_bid = self.current_orderbook.get_best_bid()
            return best_bid and order.price <= best_bid.price
    
    async def _execute_limit_order(self, order: Order):
        """Execute a marketable limit order."""
        if order.side == 'Buy':
            best_ask = self.current_orderbook.get_best_ask()
            fill_price = min(order.price, best_ask.price)
        else:
            best_bid = self.current_orderbook.get_best_bid()
            fill_price = max(order.price, best_bid.price)
        
        await self._fill_order(order, order.quantity, fill_price)
        logger.info(f"Limit order executed: {order}")
    
    async def _fill_order(self, order: Order, fill_quantity: float, fill_price: float):
        """Fill an order and update positions."""
        try:
            # Update order
            order.filled_quantity += fill_quantity
            order.remaining_quantity -= fill_quantity
            order.status = 'Filled' if order.remaining_quantity == 0 else 'PartiallyFilled'
            order.updated_at = datetime.now(timezone.utc)
            
            # Update position
            symbol = order.symbol
            if symbol not in self.positions:
                self.positions[symbol] = Position(symbol)
            
            # Determine fill size (positive for buy, negative for sell)
            fill_size = fill_quantity if order.side == 'Buy' else -fill_quantity
            
            self.positions[symbol].update_position(fill_size, fill_price)
            
            # Update balance (subtract fees)
            fee_rate = 0.0006  # Bybit taker fee (~0.06%)
            fee = fill_quantity * fill_price * fee_rate
            self.balance -= fee
            self.total_fees += fee
            
            # Update statistics
            self.total_trades += 1
            
            # Log the fill
            logger.info(f"Order filled: {fill_quantity} {symbol} at {fill_price}")
            logger.info(f"Updated position: {self.positions[symbol]}")
            
        except Exception as e:
            logger.error(f"Failed to fill order: {e}")
    
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an open order."""
        try:
            if order_id not in self.orders:
                logger.error(f"Order not found: {order_id}")
                return False
            
            order = self.orders[order_id]
            if order.status not in ['Open', 'PartiallyFilled']:
                logger.error(f"Cannot cancel order in status: {order.status}")
                return False
            
            order.status = 'Cancelled'
            order.updated_at = datetime.now(timezone.utc)
            
            logger.info(f"Order cancelled: {order}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cancel order: {e}")
            return False
    
    def get_position(self, symbol: str) -> Optional[Position]:
        """Get current position for a symbol."""
        return self.positions.get(symbol)
    
    def get_open_orders(self, symbol: Optional[str] = None) -> List[Order]:
        """Get all open orders, optionally filtered by symbol."""
        open_orders = []
        for order in self.orders.values():
            if order.status in ['Open', 'PartiallyFilled']:
                if symbol is None or order.symbol == symbol:
                    open_orders.append(order)
        return open_orders
    
    def get_account_summary(self) -> Dict[str, Any]:
        """Get account summary with balance and positions."""
        total_unrealized_pnl = sum(pos.unrealized_pnl for pos in self.positions.values())
        total_realized_pnl = sum(pos.realized_pnl for pos in self.positions.values())
        
        return {
            'balance': self.balance,
            'total_unrealized_pnl': total_unrealized_pnl,
            'total_realized_pnl': total_realized_pnl,
            'total_pnl': total_realized_pnl + total_unrealized_pnl,
            'equity': self.balance + total_unrealized_pnl,
            'positions': len([p for p in self.positions.values() if p.size != 0]),
            'open_orders': len(self.get_open_orders()),
            'total_trades': self.total_trades,
            'total_fees': self.total_fees,
        }
    
    def __repr__(self):
        summary = self.get_account_summary()
        return (f"PaperTrader(balance={summary['balance']:.2f}, "
                f"equity={summary['equity']:.2f}, "
                f"positions={summary['positions']}, "
                f"trades={summary['total_trades']})")


if __name__ == "__main__":
    # Example usage
    import asyncio
    from ..data.orderbook import RealtimeOrderbook
    
    async def main():
        trader = PaperTrader()
        
        # Create mock orderbook
        orderbook = RealtimeOrderbook("BTCUSDT")
        snapshot_data = {
            "type": "snapshot",
            "b": [["45000.0", "1.5"], ["44999.5", "2.0"]],
            "a": [["45001.0", "1.0"], ["45001.5", "1.2"]],
            "u": 12345,
            "seq": 1,
            "timestamp": 1640000000000
        }
        orderbook.process_message(snapshot_data)
        trader.set_orderbook(orderbook)
        
        # Place some orders
        print("Placing market buy order...")
        order1 = await trader.place_order("BTCUSDT", "Buy", "Market", 0.001)
        
        print("Placing limit sell order...")
        order2 = await trader.place_order("BTCUSDT", "Sell", "Limit", 0.0005, 45500.0)
        
        print("\nAccount Summary:")
        print(trader.get_account_summary())
        
        print("\nPositions:")
        for symbol, position in trader.positions.items():
            if position.size != 0:
                print(position)
    
    asyncio.run(main())