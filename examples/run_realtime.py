#!/usr/bin/env python3
"""
Main execution script for real-time Bybit trading with evolution strategies.

This script orchestrates:
1. Real-time market data streaming from Bybit mainnet WebSocket
2. Paper trading execution via Bybit demo API  
3. Strategy execution with evolution framework integration
4. Live monitoring dashboard

Usage:
    python examples/run_realtime.py --config examples/realtime_config.yaml
    python examples/run_realtime.py --dashboard-only  # Dashboard only mode
"""

import argparse
import asyncio
import logging
import sys
import signal
from pathlib import Path
from typing import Optional, Dict, Any
import yaml

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from alphaevolve.realtime.data.bybit_websocket import BybitWebSocketManager
from alphaevolve.realtime.data.orderbook import RealtimeOrderbook
from alphaevolve.realtime.trading.paper_trader import PaperTrader
from alphaevolve.realtime.strategies.realtime_base import RealtimeHFTStrategy, SimpleSpreadStrategy
from alphaevolve.realtime.dashboard.realtime_dashboard import RealtimeDashboard


# Global components for clean shutdown
ws_manager: Optional[BybitWebSocketManager] = None
paper_trader: Optional[PaperTrader] = None
strategy: Optional[RealtimeHFTStrategy] = None
running = False


def setup_logging(config: Dict[str, Any]):
    """Setup logging configuration."""
    log_config = config.get('logging', {})
    
    # Create logs directory
    if log_config.get('log_to_file'):
        log_file = Path(log_config.get('log_file', 'logs/realtime_trading.log'))
        log_file.parent.mkdir(exist_ok=True)
    
    # Configure logging
    level = getattr(logging, log_config.get('level', 'INFO').upper())
    
    handlers = [logging.StreamHandler(sys.stdout)]
    if log_config.get('log_to_file'):
        from logging.handlers import RotatingFileHandler
        
        max_bytes = 100 * 1024 * 1024  # 100MB default
        if 'max_file_size' in log_config:
            size_str = log_config['max_file_size']
            if size_str.endswith('MB'):
                max_bytes = int(size_str[:-2]) * 1024 * 1024
        
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=log_config.get('backup_count', 5)
        )
        handlers.append(file_handler)
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers
    )
    
    # Configure specific loggers
    logger_configs = log_config.get('loggers', {})
    for logger_name, logger_level in logger_configs.items():
        logger = logging.getLogger(logger_name)
        logger.setLevel(getattr(logging, logger_level.upper()))


def load_config(config_path: str) -> Dict[str, Any]:
    """Load configuration from YAML file."""
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        logging.info(f"Configuration loaded from: {config_path}")
        return config
        
    except Exception as e:
        logging.error(f"Failed to load config: {e}")
        sys.exit(1)


def create_strategy(config: Dict[str, Any]) -> RealtimeHFTStrategy:
    """Create strategy instance based on configuration."""
    strategy_config = config.get('strategy', {})
    strategy_name = strategy_config.get('name', 'SimpleSpreadStrategy')
    parameters = strategy_config.get('parameters', {})
    
    if strategy_name == 'SimpleSpreadStrategy':
        strategy = SimpleSpreadStrategy(
            spread_threshold=parameters.get('spread_threshold', 10.0),
            position_size=parameters.get('position_size', 0.001)
        )
    else:
        # Default to simple spread strategy
        logging.warning(f"Unknown strategy: {strategy_name}, using SimpleSpreadStrategy")
        strategy = SimpleSpreadStrategy()
    
    # Apply risk limits
    risk_limits = strategy_config.get('risk_limits', {})
    if hasattr(strategy, 'max_position_size'):
        strategy.max_position_size = risk_limits.get('max_position_size', 1.0)
    if hasattr(strategy, 'min_spread_threshold'):
        strategy.min_spread_threshold = risk_limits.get('min_spread_threshold', 0.5)
    if hasattr(strategy, 'max_orders_per_minute'):
        strategy.max_orders_per_minute = risk_limits.get('max_orders_per_minute', 60)
    
    logging.info(f"Strategy created: {strategy}")
    return strategy


async def websocket_callback(orderbook_data: Dict[str, Any]):
    """Callback function for WebSocket orderbook updates."""
    global strategy
    
    if strategy and strategy.is_running:
        await strategy.on_orderbook_update(orderbook_data)


async def run_realtime_trading(config: Dict[str, Any]):
    """Main real-time trading loop."""
    global ws_manager, paper_trader, strategy, running
    
    try:
        # Initialize components
        market_config = config.get('market_data', {})
        trading_config = config.get('paper_trading', {})
        
        # Create orderbook processor
        symbol = market_config.get('symbol', 'BTCUSDT')
        depth = market_config.get('depth', 50)
        orderbook = RealtimeOrderbook(symbol, max_depth=depth)
        
        # Create paper trader
        credentials_path = f"credentials/{trading_config.get('credentials_file', 'bybit_demo.yaml')}"
        paper_trader = PaperTrader(credentials_path)
        paper_trader.balance = trading_config.get('initial_balance', 100000.0)
        
        # Create strategy
        strategy = create_strategy(config)
        strategy.set_paper_trader(paper_trader)
        strategy.set_orderbook(orderbook)
        
        # Create enhanced callback that updates orderbook and calls strategy
        async def enhanced_callback(orderbook_data: Dict[str, Any]):
            # Update orderbook
            orderbook.process_message(orderbook_data)
            # Call strategy
            if strategy and strategy.is_running:
                await strategy.on_orderbook_update(orderbook_data)
        
        # Create WebSocket manager
        ws_manager = BybitWebSocketManager(
            symbol=symbol,
            depth=depth,
            callback=enhanced_callback
        )
        
        # Start components
        logging.info("Starting real-time trading system...")
        
        # Start strategy
        strategy.start()
        
        # Start WebSocket in background
        running = True
        ws_task = asyncio.create_task(ws_manager.start())
        
        logging.info("✅ Real-time trading system started successfully!")
        logging.info(f"📊 Monitoring {symbol} with {depth}-level orderbook depth")
        logging.info(f"🤖 Strategy: {strategy.name}")
        logging.info(f"💰 Paper trading with ${paper_trader.balance:,.2f} balance")
        logging.info("Press Ctrl+C to stop...")
        
        # Main monitoring loop
        while running:
            await asyncio.sleep(10)  # Check every 10 seconds
            
            # Log status
            if strategy.is_running:
                stats = strategy.get_performance_stats()
                account_summary = paper_trader.get_account_summary()
                
                logging.info(
                    f"Strategy: {stats['signals_generated']} signals, "
                    f"{stats['orders_placed']} orders, "
                    f"PnL: ${account_summary['total_pnl']:+.2f}, "
                    f"Balance: ${account_summary['balance']:,.2f}"
                )
                
                # Check orderbook health
                if orderbook.is_initialized:
                    liquidity_stats = orderbook.get_liquidity_stats()
                    logging.info(
                        f"Market: spread={liquidity_stats.get('spread', 0):.2f}, "
                        f"mid=${liquidity_stats.get('mid_price', 0):,.2f}, "
                        f"updates={orderbook.update_count}"
                    )
        
        # Wait for WebSocket task to complete
        await ws_task
        
    except Exception as e:
        logging.error(f"Error in real-time trading: {e}")
        raise
    finally:
        # Cleanup
        if strategy:
            strategy.stop()
        if ws_manager:
            await ws_manager.disconnect()
        
        logging.info("Real-time trading system stopped")


async def run_dashboard_only():
    """Run dashboard in standalone mode for monitoring."""
    import subprocess
    import os
    
    logging.info("Starting Streamlit dashboard...")
    
    # Get the path to the dashboard module
    dashboard_path = Path(__file__).parent.parent / "alphaevolve" / "realtime" / "dashboard" / "realtime_dashboard.py"
    
    # Run Streamlit
    cmd = [
        sys.executable, "-m", "streamlit", "run", 
        str(dashboard_path),
        "--server.port", "8501",
        "--server.headless", "true"
    ]
    
    try:
        process = subprocess.Popen(cmd, cwd=os.getcwd())
        logging.info("Dashboard started at: http://localhost:8501")
        process.wait()
    except KeyboardInterrupt:
        logging.info("Stopping dashboard...")
        process.terminate()
        process.wait()


def signal_handler(signum, frame):
    """Handle shutdown signals."""
    global running
    logging.info("Received shutdown signal, stopping...")
    running = False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Real-time Bybit trading with evolution strategies",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Full trading system
    python examples/run_realtime.py --config examples/realtime_config.yaml
    
    # Dashboard only
    python examples/run_realtime.py --dashboard-only
    
    # Debug mode
    python examples/run_realtime.py --config examples/realtime_config.yaml --debug
        """
    )
    
    parser.add_argument(
        '--config', '-c',
        default='examples/realtime_config.yaml',
        help='Configuration file path (default: examples/realtime_config.yaml)'
    )
    
    parser.add_argument(
        '--dashboard-only',
        action='store_true',
        help='Run dashboard only (no trading)'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )
    
    args = parser.parse_args()
    
    # Load configuration
    if not args.dashboard_only:
        if not Path(args.config).exists():
            print(f"Error: Configuration file not found: {args.config}")
            sys.exit(1)
        
        config = load_config(args.config)
        
        # Override debug setting if specified
        if args.debug:
            config.setdefault('logging', {})['level'] = 'DEBUG'
        
        # Setup logging
        setup_logging(config)
    else:
        # Basic logging for dashboard mode
        logging.basicConfig(level=logging.INFO)
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        if args.dashboard_only:
            # Run dashboard only
            asyncio.run(run_dashboard_only())
        else:
            # Run full trading system
            asyncio.run(run_realtime_trading(config))
            
    except KeyboardInterrupt:
        logging.info("Stopped by user")
    except Exception as e:
        logging.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()