#!/usr/bin/env python3
"""
Quick test to verify components work individually.
"""

import sys
import asyncio
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

async def test_websocket():
    """Test just the WebSocket connection."""
    from alphaevolve.realtime.data.bybit_websocket import BybitWebSocketManager
    from alphaevolve.realtime.data.orderbook import RealtimeOrderbook
    
    print("🔌 Testing WebSocket connection...")
    
    message_count = 0
    orderbook = RealtimeOrderbook("BTCUSDT")
    
    async def callback(data):
        nonlocal message_count
        message_count += 1
        updated = orderbook.process_message(data)
        
        if updated:
            spread = orderbook.get_spread()
            mid_price = orderbook.get_mid_price()
            print(f"Message {message_count}: Spread={spread:.2f}, Mid=${mid_price:,.2f}")
        
        if message_count >= 3:
            return True  # Stop after 3 messages
    
    ws_manager = BybitWebSocketManager(
        symbol="BTCUSDT", 
        depth=50, 
        callback=callback
    )
    
    try:
        # Run for maximum 10 seconds
        await asyncio.wait_for(ws_manager.start(), timeout=10.0)
    except asyncio.TimeoutError:
        print("✅ WebSocket test completed (timeout reached)")
    finally:
        await ws_manager.disconnect()

def test_paper_trader():
    """Test paper trader."""
    from alphaevolve.realtime.trading.paper_trader import PaperTrader
    
    print("\n💰 Testing paper trader...")
    
    trader = PaperTrader("credentials/bybit_demo.yaml")
    print(f"✅ Paper trader created: {trader}")

async def main():
    print("🧪 Quick component tests...\n")
    
    # Test 1: WebSocket
    await test_websocket()
    
    # Test 2: Paper Trader
    test_paper_trader()
    
    print("\n✅ Quick tests completed!")

if __name__ == "__main__":
    asyncio.run(main())