"""
Real-time L2 orderbook processor for Bybit data.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
from collections import defaultdict
import logging
from datetime import datetime, timezone


logger = logging.getLogger(__name__)


class OrderbookLevel:
    """Represents a single level in the orderbook."""
    
    def __init__(self, price: float, size: float):
        self.price = price
        self.size = size
        self.timestamp = datetime.now(timezone.utc)
    
    def __repr__(self):
        return f"Level(price={self.price}, size={self.size})"


class RealtimeOrderbook:
    """
    Maintains a real-time L2 orderbook with snapshot/delta processing.
    
    Handles Bybit's orderbook message format:
    - Initial "snapshot" message provides full orderbook state
    - Subsequent "delta" messages update specific levels
    - Zero-size entries indicate level deletion
    """
    
    def __init__(self, symbol: str, max_depth: int = 50):
        """
        Initialize orderbook processor.
        
        Args:
            symbol: Trading symbol (e.g., BTCUSDT)
            max_depth: Maximum depth to maintain (levels per side)
        """
        self.symbol = symbol
        self.max_depth = max_depth
        
        # Orderbook state: price -> OrderbookLevel
        self.bids: Dict[float, OrderbookLevel] = {}
        self.asks: Dict[float, OrderbookLevel] = {}
        
        # Metadata
        self.last_update_id = None
        self.sequence_number = None
        self.last_update_time = None
        self.is_initialized = False
        
        # Statistics
        self.update_count = 0
        self.snapshot_count = 0
        self.delta_count = 0
    
    def process_message(self, data: Dict[str, Any]) -> bool:
        """
        Process orderbook message from Bybit WebSocket.
        
        Args:
            data: Orderbook data from WebSocket message
            
        Returns:
            True if orderbook was updated, False otherwise
        """
        try:
            # Bybit uses different message structure - check for 'type' or infer from data
            data_type = data.get("type")
            
            # If no explicit type, infer from content
            if not data_type:
                if "b" in data and "a" in data:
                    # Has bids and asks, this is orderbook data
                    # If we haven't been initialized, treat as snapshot
                    data_type = "snapshot" if not self.is_initialized else "delta"
                else:
                    # Not orderbook data, skip
                    return False
            
            if data_type == "snapshot":
                return self._process_snapshot(data)
            elif data_type == "delta":
                return self._process_delta(data)
            else:
                logger.debug(f"Skipping message type: {data_type}")
                return False
                
        except Exception as e:
            logger.error(f"Error processing orderbook message: {e}")
            return False
    
    def _process_snapshot(self, data: Dict[str, Any]) -> bool:
        """Process snapshot message (full orderbook state)."""
        try:
            # Clear existing orderbook
            self.bids.clear()
            self.asks.clear()
            
            # Process bids (buy orders)
            bids_data = data.get("b", [])
            for bid in bids_data:
                if len(bid) >= 2:
                    price, size = float(bid[0]), float(bid[1])
                    if size > 0:  # Only add non-zero sizes
                        self.bids[price] = OrderbookLevel(price, size)
            
            # Process asks (sell orders)  
            asks_data = data.get("a", [])
            for ask in asks_data:
                if len(ask) >= 2:
                    price, size = float(ask[0]), float(ask[1])
                    if size > 0:  # Only add non-zero sizes
                        self.asks[price] = OrderbookLevel(price, size)
            
            # Update metadata
            self.last_update_id = data.get("u")
            self.sequence_number = data.get("seq")
            self.last_update_time = data.get("timestamp", 0)
            self.is_initialized = True
            
            self.snapshot_count += 1
            self.update_count += 1
            
            logger.info(f"Processed snapshot: {len(self.bids)} bids, {len(self.asks)} asks")
            return True
            
        except Exception as e:
            logger.error(f"Error processing snapshot: {e}")
            return False
    
    def _process_delta(self, data: Dict[str, Any]) -> bool:
        """Process delta message (incremental updates)."""
        if not self.is_initialized:
            logger.warning("Received delta before snapshot, ignoring")
            return False
        
        try:
            # Process bid updates
            bids_data = data.get("b", [])
            for bid in bids_data:
                if len(bid) >= 2:
                    price, size = float(bid[0]), float(bid[1])
                    
                    if size == 0:
                        # Size of 0 means delete this level
                        self.bids.pop(price, None)
                    else:
                        # Update or add level
                        self.bids[price] = OrderbookLevel(price, size)
            
            # Process ask updates
            asks_data = data.get("a", [])
            for ask in asks_data:
                if len(ask) >= 2:
                    price, size = float(ask[0]), float(ask[1])
                    
                    if size == 0:
                        # Size of 0 means delete this level
                        self.asks.pop(price, None)
                    else:
                        # Update or add level
                        self.asks[price] = OrderbookLevel(price, size)
            
            # Update metadata
            self.last_update_id = data.get("u")
            self.sequence_number = data.get("seq")
            self.last_update_time = data.get("timestamp", 0)
            
            self.delta_count += 1
            self.update_count += 1
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing delta: {e}")
            return False
    
    def get_best_bid(self) -> Optional[OrderbookLevel]:
        """Get the best (highest) bid."""
        if not self.bids:
            return None
        best_price = max(self.bids.keys())
        return self.bids[best_price]
    
    def get_best_ask(self) -> Optional[OrderbookLevel]:
        """Get the best (lowest) ask."""
        if not self.asks:
            return None
        best_price = min(self.asks.keys())
        return self.asks[best_price]
    
    def get_spread(self) -> Optional[float]:
        """Get the bid-ask spread."""
        best_bid = self.get_best_bid()
        best_ask = self.get_best_ask()
        
        if best_bid and best_ask:
            return best_ask.price - best_bid.price
        return None
    
    def get_mid_price(self) -> Optional[float]:
        """Get the mid price (average of best bid and ask)."""
        best_bid = self.get_best_bid()
        best_ask = self.get_best_ask()
        
        if best_bid and best_ask:
            return (best_bid.price + best_ask.price) / 2
        return None
    
    def get_sorted_levels(self, side: str, max_levels: Optional[int] = None) -> List[OrderbookLevel]:
        """
        Get sorted orderbook levels.
        
        Args:
            side: 'bid' or 'ask'
            max_levels: Maximum number of levels to return
            
        Returns:
            List of OrderbookLevel objects, sorted appropriately
        """
        if side.lower() == 'bid':
            # Bids sorted by price descending (highest first)
            sorted_prices = sorted(self.bids.keys(), reverse=True)
            levels = [self.bids[price] for price in sorted_prices]
        elif side.lower() == 'ask':
            # Asks sorted by price ascending (lowest first)
            sorted_prices = sorted(self.asks.keys())
            levels = [self.asks[price] for price in sorted_prices]
        else:
            raise ValueError("side must be 'bid' or 'ask'")
        
        if max_levels:
            levels = levels[:max_levels]
        
        return levels
    
    def to_dataframe(self, max_levels: int = 10) -> pd.DataFrame:
        """
        Convert orderbook to pandas DataFrame for analysis.
        
        Args:
            max_levels: Maximum levels per side to include
            
        Returns:
            DataFrame with bid/ask prices and sizes
        """
        bid_levels = self.get_sorted_levels('bid', max_levels)
        ask_levels = self.get_sorted_levels('ask', max_levels)
        
        # Create structured data
        data = []
        max_len = max(len(bid_levels), len(ask_levels))
        
        for i in range(max_len):
            row = {
                'level': i,
                'bid_price': bid_levels[i].price if i < len(bid_levels) else np.nan,
                'bid_size': bid_levels[i].size if i < len(bid_levels) else np.nan,
                'ask_price': ask_levels[i].price if i < len(ask_levels) else np.nan,
                'ask_size': ask_levels[i].size if i < len(ask_levels) else np.nan,
            }
            data.append(row)
        
        df = pd.DataFrame(data)
        df['spread'] = df['ask_price'] - df['bid_price']
        df['mid_price'] = (df['bid_price'] + df['ask_price']) / 2
        
        return df
    
    def get_liquidity_stats(self) -> Dict[str, float]:
        """Get liquidity statistics from current orderbook."""
        bid_levels = self.get_sorted_levels('bid')
        ask_levels = self.get_sorted_levels('ask')
        
        stats = {
            'bid_count': len(bid_levels),
            'ask_count': len(ask_levels),
            'total_bid_volume': sum(level.size for level in bid_levels),
            'total_ask_volume': sum(level.size for level in ask_levels),
            'spread': self.get_spread(),
            'mid_price': self.get_mid_price(),
            'update_count': self.update_count,
            'snapshot_count': self.snapshot_count,
            'delta_count': self.delta_count,
        }
        
        if bid_levels:
            stats['best_bid'] = bid_levels[0].price
            stats['best_bid_size'] = bid_levels[0].size
        
        if ask_levels:
            stats['best_ask'] = ask_levels[0].price  
            stats['best_ask_size'] = ask_levels[0].size
        
        return stats
    
    def __repr__(self):
        best_bid = self.get_best_bid()
        best_ask = self.get_best_ask()
        spread = self.get_spread()
        
        return (f"Orderbook({self.symbol}, "
                f"bid={best_bid.price if best_bid else 'N/A'}, "
                f"ask={best_ask.price if best_ask else 'N/A'}, "
                f"spread={spread:.2f if spread else 'N/A'}, "
                f"levels={len(self.bids)}/{len(self.asks)})")


if __name__ == "__main__":
    # Example usage
    orderbook = RealtimeOrderbook("BTCUSDT", max_depth=10)
    
    # Simulate snapshot message
    snapshot_data = {
        "type": "snapshot",
        "b": [["45000.0", "1.5"], ["44999.5", "2.0"], ["44999.0", "0.5"]],
        "a": [["45001.0", "1.0"], ["45001.5", "1.2"], ["45002.0", "0.8"]],
        "u": 12345,
        "seq": 1,
        "timestamp": 1640000000000
    }
    
    orderbook.process_message(snapshot_data)
    print("After snapshot:", orderbook)
    print("\nLiquidity stats:", orderbook.get_liquidity_stats())
    
    # Simulate delta message
    delta_data = {
        "type": "delta",
        "b": [["45000.5", "2.5"]],  # New bid level
        "a": [["45001.0", "0"]],    # Remove ask level
        "u": 12346,
        "seq": 2,
        "timestamp": 1640000001000
    }
    
    orderbook.process_message(delta_data)
    print("\nAfter delta:", orderbook)
    print("\nDataFrame representation:")
    print(orderbook.to_dataframe(5))