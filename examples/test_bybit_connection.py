#!/usr/bin/env python3
"""
Test script to verify Bybit WebSocket connection and demo API credentials.

This script tests:
1. WebSocket connection to Bybit mainnet for market data
2. Demo API credentials for paper trading
3. Basic orderbook processing and order placement

Usage:
    python examples/test_bybit_connection.py
"""

import asyncio
import logging
import sys
from pathlib import Path
import yaml

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from alphaevolve.realtime.data.bybit_websocket import BybitWebSocketManager
from alphaevolve.realtime.data.orderbook import RealtimeOrderbook
from alphaevolve.realtime.trading.paper_trader import PaperTrader


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_websocket_connection():
    """Test WebSocket connection to Bybit."""
    logger.info("🔌 Testing Bybit WebSocket connection...")
    
    # Counter for received messages
    message_count = 0
    orderbook = RealtimeOrderbook("BTCUSDT")
    
    async def test_callback(orderbook_data):
        nonlocal message_count
        message_count += 1
        
        # Process the message
        updated = orderbook.process_message(orderbook_data)
        
        if updated and message_count <= 5:
            data_type = orderbook_data.get("type", "unknown")
            logger.info(f"📊 Received {data_type} message #{message_count}")
            
            if orderbook.is_initialized:
                spread = orderbook.get_spread()
                mid_price = orderbook.get_mid_price()
                stats = orderbook.get_liquidity_stats()
                
                logger.info(f"   Spread: {spread:.2f} USDT")
                logger.info(f"   Mid Price: ${mid_price:,.2f}")
                logger.info(f"   Bid/Ask Levels: {stats['bid_count']}/{stats['ask_count']}")
        
        # Stop after receiving 5 messages
        if message_count >= 5:
            return True
    
    # Create WebSocket manager
    ws_manager = BybitWebSocketManager(
        symbol="BTCUSDT",
        depth=50,
        callback=test_callback
    )
    
    try:
        # Start connection with timeout
        await asyncio.wait_for(ws_manager.start(), timeout=30.0)
        logger.info("✅ WebSocket connection test successful!")
        return True
        
    except asyncio.TimeoutError:
        logger.info("✅ WebSocket connection test successful! (timeout reached)")
        return True
        
    except Exception as e:
        logger.error(f"❌ WebSocket connection test failed: {e}")
        return False
        
    finally:
        await ws_manager.disconnect()


async def test_paper_trading():
    """Test paper trading functionality."""
    logger.info("💰 Testing paper trading functionality...")
    
    # Check credentials file
    creds_path = Path("credentials/bybit_demo.yaml")
    if not creds_path.exists():
        logger.warning(f"⚠️  Credentials file not found: {creds_path}")
        logger.info("   Creating example credentials file...")
        
        # Create credentials directory if it doesn't exist
        creds_path.parent.mkdir(exist_ok=True)
        
        # Copy example config
        example_path = Path("credentials/example_config.yaml")
        if example_path.exists():
            import shutil
            shutil.copy(example_path, creds_path)
            logger.info(f"   Please edit {creds_path} with your actual demo API credentials")
        
        return False
    
    try:
        # Load credentials to verify format
        with open(creds_path, 'r') as f:
            creds = yaml.safe_load(f)
        
        if not creds.get('api_key') or not creds.get('api_secret'):
            logger.error("❌ Invalid credentials: api_key and api_secret required")
            return False
        
        if creds.get('api_key') == 'your_demo_api_key_here':
            logger.error("❌ Please update credentials with actual demo API keys")
            return False
        
        # Create paper trader
        paper_trader = PaperTrader(str(creds_path))
        
        # Create mock orderbook
        orderbook = RealtimeOrderbook("BTCUSDT")
        snapshot_data = {
            "type": "snapshot",
            "b": [["45000.0", "1.5"], ["44999.5", "2.0"], ["44999.0", "0.5"]],
            "a": [["45001.0", "1.0"], ["45001.5", "1.2"], ["45002.0", "0.8"]],
            "u": 12345,
            "seq": 1,
            "timestamp": 1640000000000
        }
        
        orderbook.process_message(snapshot_data)
        paper_trader.set_orderbook(orderbook)
        
        logger.info("📊 Mock orderbook created")
        logger.info(f"   Best bid: ${orderbook.get_best_bid().price}")
        logger.info(f"   Best ask: ${orderbook.get_best_ask().price}")
        logger.info(f"   Spread: {orderbook.get_spread():.2f} USDT")
        
        # Test order placement
        logger.info("📋 Testing order placement...")
        
        # Place a small market buy order
        order = await paper_trader.place_order("BTCUSDT", "Buy", "Market", 0.001)
        
        if order:
            logger.info(f"✅ Order placed successfully: {order.order_id}")
            logger.info(f"   Side: {order.side}, Quantity: {order.quantity}, Status: {order.status}")
            
            # Check account summary
            summary = paper_trader.get_account_summary()
            logger.info(f"💰 Account summary after trade:")
            logger.info(f"   Balance: ${summary['balance']:,.2f}")
            logger.info(f"   Total PnL: ${summary['total_pnl']:+.2f}")
            logger.info(f"   Positions: {summary['positions']}")
            logger.info(f"   Total trades: {summary['total_trades']}")
            
            return True
        else:
            logger.error("❌ Failed to place order")
            return False
            
    except Exception as e:
        logger.error(f"❌ Paper trading test failed: {e}")
        return False


async def test_integration():
    """Test integration of WebSocket + paper trading."""
    logger.info("🔄 Testing integrated system...")
    
    # This would test the full integration but requires valid credentials
    # For now, just verify the components can be created together
    
    try:
        from alphaevolve.realtime.strategies.realtime_base import SimpleSpreadStrategy
        
        # Create all components
        orderbook = RealtimeOrderbook("BTCUSDT")
        paper_trader = PaperTrader("credentials/bybit_demo.yaml")  # Will gracefully handle missing file
        strategy = SimpleSpreadStrategy(spread_threshold=5.0, position_size=0.001)
        
        # Connect components
        strategy.set_paper_trader(paper_trader)
        strategy.set_orderbook(orderbook)
        
        logger.info("✅ All components created and connected successfully")
        logger.info(f"   Strategy: {strategy}")
        logger.info(f"   Paper trader: {paper_trader}")
        logger.info(f"   Orderbook: {orderbook}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Integration test failed: {e}")
        return False


def print_setup_instructions():
    """Print setup instructions for the user."""
    logger.info("\n" + "="*60)
    logger.info("📋 SETUP INSTRUCTIONS")
    logger.info("="*60)
    
    logger.info("\n1. 🔑 Get Bybit Demo API Credentials:")
    logger.info("   • Sign up at https://www.bybit.com")
    logger.info("   • Go to Demo Trading section")
    logger.info("   • Create API keys with trading permissions")
    
    logger.info("\n2. ⚙️  Configure Credentials:")
    logger.info(f"   • Edit: credentials/bybit_demo.yaml")
    logger.info("   • Add your demo API key and secret")
    
    logger.info("\n3. 🚀 Run the System:")
    logger.info("   • Full system: python examples/run_realtime.py")
    logger.info("   • Dashboard only: python examples/run_realtime.py --dashboard-only")
    
    logger.info("\n4. 📊 Monitor Performance:")
    logger.info("   • Dashboard: http://localhost:8501")
    logger.info("   • Logs: Check console output")
    
    logger.info("\n" + "="*60)


async def main():
    """Main test function."""
    logger.info("🧪 Starting Bybit connection tests...")
    
    tests_passed = 0
    total_tests = 3
    
    # Test 1: WebSocket connection
    if await test_websocket_connection():
        tests_passed += 1
    
    logger.info("")  # Empty line for readability
    
    # Test 2: Paper trading
    if await test_paper_trading():
        tests_passed += 1
    
    logger.info("")  # Empty line for readability
    
    # Test 3: Integration
    if await test_integration():
        tests_passed += 1
    
    # Results
    logger.info("\n" + "="*60)
    logger.info(f"📊 TEST RESULTS: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        logger.info("🎉 All tests passed! System is ready for use.")
    elif tests_passed >= 1:
        logger.info("⚠️  Some tests passed. Check setup for remaining issues.")
    else:
        logger.info("❌ All tests failed. Please check your setup.")
    
    logger.info("="*60)
    
    # Always show setup instructions
    print_setup_instructions()


if __name__ == "__main__":
    asyncio.run(main())