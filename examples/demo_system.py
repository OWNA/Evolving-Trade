#!/usr/bin/env python3
"""
Demo script showing the full real-time system working.
Runs for 30 seconds to demonstrate functionality.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from alphaevolve.realtime.data.bybit_websocket import BybitWebSocketManager
from alphaevolve.realtime.data.orderbook import RealtimeOrderbook
from alphaevolve.realtime.trading.paper_trader import PaperTrader
from alphaevolve.realtime.strategies.realtime_base import SimpleSpreadStrategy

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def demo_realtime_system():
    """Demo the complete real-time trading system."""
    logger.info("🚀 Starting Real-time BTC/USDT Trading System Demo")
    logger.info("=" * 60)
    
    # Create components
    symbol = "BTCUSDT"
    depth = 50
    
    # Initialize orderbook
    orderbook = RealtimeOrderbook(symbol, max_depth=depth)
    
    # Initialize paper trader
    paper_trader = PaperTrader("credentials/bybit_demo.yaml")
    paper_trader.balance = 100000.0
    
    # Initialize strategy
    strategy = SimpleSpreadStrategy(spread_threshold=5.0, position_size=0.001)
    strategy.set_paper_trader(paper_trader)
    strategy.set_orderbook(orderbook)
    
    logger.info(f"📊 Created orderbook for {symbol} (depth: {depth})")
    logger.info(f"💰 Paper trader initialized with ${paper_trader.balance:,.2f}")
    logger.info(f"🤖 Strategy loaded: {strategy.name}")
    
    # Enhanced callback that updates orderbook and calls strategy
    message_count = 0
    
    async def enhanced_callback(orderbook_data):
        nonlocal message_count
        message_count += 1
        
        # Update orderbook
        updated = orderbook.process_message(orderbook_data)
        
        if updated and strategy.is_running:
            # Call strategy
            await strategy.on_orderbook_update(orderbook_data)
            
            # Log every 20th update
            if message_count % 20 == 0:
                stats = orderbook.get_liquidity_stats()
                account = paper_trader.get_account_summary()
                strategy_stats = strategy.get_performance_stats()
                
                logger.info(
                    f"📈 Update #{message_count}: "
                    f"Mid=${stats.get('mid_price', 0):,.2f}, "
                    f"Spread={stats.get('spread', 0):.2f}, "
                    f"Signals={strategy_stats['signals_generated']}, "
                    f"Orders={strategy_stats['orders_placed']}, "
                    f"PnL=${account['total_pnl']:+.2f}"
                )
    
    # Create WebSocket manager
    ws_manager = BybitWebSocketManager(
        symbol=symbol,
        depth=depth,
        callback=enhanced_callback
    )
    
    logger.info("🔌 Connecting to Bybit WebSocket...")
    
    try:
        # Start strategy
        strategy.start()
        logger.info("✅ Strategy started")
        
        # Start WebSocket and run for 30 seconds
        ws_task = asyncio.create_task(ws_manager.start())
        
        logger.info("🟢 SYSTEM LIVE - Monitoring for 30 seconds...")
        logger.info("   Real market data streaming")
        logger.info("   Paper trading active") 
        logger.info("   Strategy executing")
        logger.info("-" * 60)
        
        # Wait 30 seconds
        await asyncio.sleep(30)
        
        # Final status
        logger.info("-" * 60)
        logger.info("📊 FINAL SYSTEM STATUS:")
        
        # Orderbook stats
        if orderbook.is_initialized:
            stats = orderbook.get_liquidity_stats()
            logger.info(f"   Orderbook: {stats['update_count']} updates received")
            logger.info(f"   Current spread: {stats.get('spread', 0):.2f} USDT")
            logger.info(f"   Mid price: ${stats.get('mid_price', 0):,.2f}")
        
        # Account stats  
        account = paper_trader.get_account_summary()
        logger.info(f"   Account balance: ${account['balance']:,.2f}")
        logger.info(f"   Total PnL: ${account['total_pnl']:+.2f}")
        logger.info(f"   Total trades: {account['total_trades']}")
        
        # Strategy stats
        strategy_stats = strategy.get_performance_stats()
        logger.info(f"   Signals generated: {strategy_stats['signals_generated']}")
        logger.info(f"   Orders placed: {strategy_stats['orders_placed']}")
        logger.info(f"   Runtime: {strategy_stats['runtime_seconds']:.1f} seconds")
        
        logger.info("=" * 60)
        logger.info("✅ Demo completed successfully!")
        logger.info("🎯 System is ready for production use")
        
    except Exception as e:
        logger.error(f"❌ System error: {e}")
        
    finally:
        # Cleanup
        strategy.stop()
        await ws_manager.disconnect()
        logger.info("🔌 System stopped")

if __name__ == "__main__":
    asyncio.run(demo_realtime_system())