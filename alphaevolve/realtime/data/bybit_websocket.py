"""
Bybit WebSocket connection manager for real-time market data.
"""

import asyncio
import json
import logging
from typing import Callable, Optional, Dict, Any
import websockets
import yaml
from pathlib import Path


logger = logging.getLogger(__name__)


class BybitWebSocketManager:
    """
    Manages WebSocket connections to Bybit for real-time market data.
    
    Uses mainnet for authentic market data while keeping trading separate.
    """
    
    def __init__(self, 
                 symbol: str = "BTCUSDT",
                 depth: int = 50,
                 callback: Optional[Callable] = None):
        """
        Initialize WebSocket manager.
        
        Args:
            symbol: Trading symbol (e.g., BTCUSDT)
            depth: Orderbook depth (1-1000, recommend 50 for HFT)
            callback: Function to call with each orderbook update
        """
        self.symbol = symbol
        self.depth = depth
        self.callback = callback
        
        # Mainnet WebSocket endpoint for real market data
        self.ws_url = "wss://stream.bybit.com/v5/public/linear"
        self.ws = None
        self.running = False
        
        # Connection management
        self.reconnect_delay = 5  # seconds
        self.max_reconnect_attempts = 10
        
    async def connect(self):
        """Establish WebSocket connection to Bybit."""
        try:
            logger.info(f"Connecting to Bybit WebSocket: {self.ws_url}")
            self.ws = await websockets.connect(self.ws_url)
            
            # Subscribe to orderbook updates
            subscription = {
                "req_id": "orderbook_subscription",
                "op": "subscribe", 
                "args": [f"orderbook.{self.depth}.{self.symbol}"]
            }
            
            await self.ws.send(json.dumps(subscription))
            logger.info(f"Subscribed to {self.symbol} orderbook (depth: {self.depth})")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Bybit WebSocket: {e}")
            return False
    
    async def disconnect(self):
        """Close WebSocket connection."""
        self.running = False
        if self.ws and hasattr(self.ws, 'close'):
            await self.ws.close()
            logger.info("Disconnected from Bybit WebSocket")
    
    async def listen(self):
        """
        Listen for WebSocket messages and process orderbook updates.
        
        Handles both snapshot and delta messages according to Bybit documentation.
        """
        reconnect_attempts = 0
        
        while reconnect_attempts < self.max_reconnect_attempts:
            try:
                if not self.ws or getattr(self.ws, 'closed', True):
                    success = await self.connect()
                    if not success:
                        reconnect_attempts += 1
                        await asyncio.sleep(self.reconnect_delay)
                        continue
                
                self.running = True
                reconnect_attempts = 0  # Reset on successful connection
                
                async for message in self.ws:
                    try:
                        data = json.loads(message)
                        await self._process_message(data)
                        
                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to parse WebSocket message: {e}")
                    except Exception as e:
                        logger.error(f"Error processing message: {e}")
                        
            except websockets.exceptions.ConnectionClosed:
                logger.warning("WebSocket connection closed, attempting reconnect...")
                reconnect_attempts += 1
                await asyncio.sleep(self.reconnect_delay)
                
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                reconnect_attempts += 1
                await asyncio.sleep(self.reconnect_delay)
        
        logger.error(f"Max reconnection attempts ({self.max_reconnect_attempts}) reached")
    
    async def _process_message(self, data: Dict[str, Any]):
        """
        Process incoming WebSocket messages.
        
        Args:
            data: Parsed JSON message from Bybit
        """
        # Handle subscription confirmation
        if data.get("op") == "subscribe":
            if data.get("success"):
                logger.info(f"Successfully subscribed: {data.get('ret_msg')}")
            else:
                logger.error(f"Subscription failed: {data.get('ret_msg')}")
            return
        
        # Handle orderbook data
        if "topic" in data and "orderbook" in data["topic"]:
            topic = data["topic"]
            if self.symbol in topic:
                orderbook_data = data.get("data", {})
                
                # Add metadata
                orderbook_data["symbol"] = self.symbol
                orderbook_data["topic"] = topic
                orderbook_data["timestamp"] = data.get("ts", 0)
                
                # Call the callback function if provided
                if self.callback:
                    try:
                        await self.callback(orderbook_data)
                    except Exception as e:
                        logger.error(f"Callback error: {e}")
    
    async def start(self):
        """Start the WebSocket listener."""
        logger.info(f"Starting Bybit WebSocket for {self.symbol}")
        await self.listen()
    
    def start_sync(self):
        """Start the WebSocket listener synchronously."""
        asyncio.run(self.start())


async def example_callback(orderbook_data: Dict[str, Any]):
    """Example callback function for processing orderbook updates."""
    data_type = orderbook_data.get("type", "unknown")
    symbol = orderbook_data.get("symbol", "unknown")
    timestamp = orderbook_data.get("timestamp", 0)
    
    bids = orderbook_data.get("b", [])
    asks = orderbook_data.get("a", [])
    
    if bids and asks:
        best_bid = float(bids[0][0]) if bids else 0
        best_ask = float(asks[0][0]) if asks else 0
        spread = best_ask - best_bid
        
        print(f"[{data_type}] {symbol} | Bid: {best_bid} | Ask: {best_ask} | Spread: {spread:.2f}")


if __name__ == "__main__":
    # Example usage
    import asyncio
    
    async def main():
        ws_manager = BybitWebSocketManager(
            symbol="BTCUSDT",
            depth=50,
            callback=example_callback
        )
        
        try:
            await ws_manager.start()
        except KeyboardInterrupt:
            print("\nShutting down...")
            await ws_manager.disconnect()
    
    asyncio.run(main())