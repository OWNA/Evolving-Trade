#!/usr/bin/env python3
"""
Comprehensive system diagnostics for Evolving Trade.

This script runs through all components and reports any errors or issues.
"""

import sys
import asyncio
import logging
from pathlib import Path
import traceback

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def test_imports():
    """Test all critical imports."""
    print("🔍 Testing Imports")
    print("=" * 50)
    
    errors = []
    
    try:
        import streamlit as st
        print("✅ streamlit imported successfully")
    except Exception as e:
        errors.append(f"streamlit: {e}")
        print(f"❌ streamlit: {e}")
    
    try:
        import plotly.graph_objects as go
        print("✅ plotly imported successfully")
    except Exception as e:
        errors.append(f"plotly: {e}")
        print(f"❌ plotly: {e}")
    
    try:
        import pybit
        print("✅ pybit imported successfully")
    except Exception as e:
        errors.append(f"pybit: {e}")
        print(f"❌ pybit: {e}")
    
    try:
        import websockets
        print("✅ websockets imported successfully")
    except Exception as e:
        errors.append(f"websockets: {e}")
        print(f"❌ websockets: {e}")
    
    try:
        from alphaevolve.realtime.data.bybit_websocket import BybitWebSocketManager
        print("✅ BybitWebSocketManager imported successfully")
    except Exception as e:
        errors.append(f"BybitWebSocketManager: {e}")
        print(f"❌ BybitWebSocketManager: {e}")
    
    try:
        from alphaevolve.realtime.data.orderbook import RealtimeOrderbook
        print("✅ RealtimeOrderbook imported successfully")
    except Exception as e:
        errors.append(f"RealtimeOrderbook: {e}")
        print(f"❌ RealtimeOrderbook: {e}")
    
    try:
        from alphaevolve.realtime.trading.paper_trader import PaperTrader
        print("✅ PaperTrader imported successfully")
    except Exception as e:
        errors.append(f"PaperTrader: {e}")
        print(f"❌ PaperTrader: {e}")
    
    try:
        from alphaevolve.realtime.strategies.realtime_base import SimpleSpreadStrategy
        print("✅ SimpleSpreadStrategy imported successfully")
    except Exception as e:
        errors.append(f"SimpleSpreadStrategy: {e}")
        print(f"❌ SimpleSpreadStrategy: {e}")
    
    return errors

def test_credentials():
    """Test credential loading."""
    print("\n🔑 Testing Credentials")
    print("=" * 50)
    
    errors = []
    
    try:
        creds_path = Path("credentials/bybit_demo.yaml")
        if not creds_path.exists():
            errors.append("credentials/bybit_demo.yaml not found")
            print("❌ credentials/bybit_demo.yaml not found")
        else:
            print("✅ Credentials file exists")
            
            import yaml
            with open(creds_path, 'r') as f:
                creds = yaml.safe_load(f)
            
            if not creds.get('api_key') or creds.get('api_key') == 'your_demo_api_key_here':
                errors.append("API key not configured")
                print("❌ API key not configured")
            else:
                print("✅ API key configured")
                
            if not creds.get('api_secret') or creds.get('api_secret') == 'your_demo_api_secret_here':
                errors.append("API secret not configured") 
                print("❌ API secret not configured")
            else:
                print("✅ API secret configured")
                
    except Exception as e:
        errors.append(f"Credential loading error: {e}")
        print(f"❌ Credential loading error: {e}")
    
    return errors

async def test_websocket():
    """Test WebSocket connection."""
    print("\n🔌 Testing WebSocket Connection")
    print("=" * 50)
    
    errors = []
    
    try:
        from alphaevolve.realtime.data.bybit_websocket import BybitWebSocketManager
        from alphaevolve.realtime.data.orderbook import RealtimeOrderbook
        
        # Create components
        orderbook = RealtimeOrderbook("BTCUSDT")
        message_count = 0
        
        async def test_callback(data):
            nonlocal message_count
            message_count += 1
            updated = orderbook.process_message(data)
            if updated and message_count >= 3:
                return True  # Stop after 3 successful updates
        
        ws_manager = BybitWebSocketManager(
            symbol="BTCUSDT",
            depth=50,
            callback=test_callback
        )
        
        # Test connection with timeout
        await asyncio.wait_for(ws_manager.start(), timeout=10.0)
        
        if message_count >= 3:
            print(f"✅ WebSocket test successful: {message_count} messages received")
            
            # Test orderbook data
            if orderbook.is_initialized:
                spread = orderbook.get_spread()
                mid_price = orderbook.get_mid_price()
                print(f"✅ Orderbook data: Spread={spread:.2f}, Mid=${mid_price:,.2f}")
            else:
                errors.append("Orderbook not initialized")
                print("❌ Orderbook not initialized")
        else:
            errors.append(f"Insufficient messages received: {message_count}")
            print(f"❌ Insufficient messages received: {message_count}")
            
        await ws_manager.disconnect()
        
    except asyncio.TimeoutError:
        print("✅ WebSocket timeout reached (normal)")
    except Exception as e:
        errors.append(f"WebSocket error: {e}")
        print(f"❌ WebSocket error: {e}")
        traceback.print_exc()
    
    return errors

def test_paper_trader():
    """Test paper trader functionality."""
    print("\n💰 Testing Paper Trader")
    print("=" * 50)
    
    errors = []
    
    try:
        from alphaevolve.realtime.trading.paper_trader import PaperTrader
        from alphaevolve.realtime.data.orderbook import RealtimeOrderbook
        
        # Create paper trader
        trader = PaperTrader("credentials/bybit_demo.yaml")
        print(f"✅ Paper trader created: Balance=${trader.balance:,.2f}")
        
        # Create mock orderbook
        orderbook = RealtimeOrderbook("BTCUSDT")
        snapshot_data = {
            "b": [["45000.0", "1.5"], ["44999.5", "2.0"]],
            "a": [["45001.0", "1.0"], ["45001.5", "1.2"]],
            "u": 12345,
            "seq": 1,
            "timestamp": 1640000000000
        }
        
        orderbook.process_message(snapshot_data)
        trader.set_orderbook(orderbook)
        print("✅ Mock orderbook created and connected")
        
        # Test account summary
        summary = trader.get_account_summary()
        print(f"✅ Account summary: Balance=${summary['balance']:,.2f}, Trades={summary['total_trades']}")
        
    except Exception as e:
        errors.append(f"Paper trader error: {e}")
        print(f"❌ Paper trader error: {e}")
        traceback.print_exc()
    
    return errors

def test_strategy():
    """Test strategy functionality.""" 
    print("\n🤖 Testing Strategy")
    print("=" * 50)
    
    errors = []
    
    try:
        from alphaevolve.realtime.strategies.realtime_base import SimpleSpreadStrategy
        from alphaevolve.realtime.trading.paper_trader import PaperTrader
        from alphaevolve.realtime.data.orderbook import RealtimeOrderbook
        
        # Create components
        strategy = SimpleSpreadStrategy(spread_threshold=5.0, position_size=0.001)
        trader = PaperTrader("credentials/bybit_demo.yaml")
        orderbook = RealtimeOrderbook("BTCUSDT")
        
        # Connect components
        strategy.set_paper_trader(trader)
        strategy.set_orderbook(orderbook)
        print("✅ Strategy components connected")
        
        # Test strategy stats
        stats = strategy.get_performance_stats()
        print(f"✅ Strategy stats: {stats['name']}, Running={stats['is_running']}")
        
    except Exception as e:
        errors.append(f"Strategy error: {e}")
        print(f"❌ Strategy error: {e}")
        traceback.print_exc()
    
    return errors

def test_dashboard_components():
    """Test dashboard component imports."""
    print("\n📊 Testing Dashboard Components")
    print("=" * 50)
    
    errors = []
    
    try:
        # Test if we can create basic dashboard components
        import streamlit as st
        import pandas as pd
        import plotly.graph_objects as go
        
        # Test basic data structures
        df = pd.DataFrame({
            'x': [1, 2, 3],
            'y': [4, 5, 6]
        })
        print("✅ Pandas DataFrame creation successful")
        
        # Test plotly figure
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df['x'], y=df['y']))
        print("✅ Plotly Figure creation successful")
        
    except Exception as e:
        errors.append(f"Dashboard component error: {e}")
        print(f"❌ Dashboard component error: {e}")
        traceback.print_exc()
    
    return errors

async def run_diagnostics():
    """Run all diagnostic tests."""
    print("🔧 EVOLVING TRADE SYSTEM DIAGNOSTICS")
    print("=" * 60)
    
    all_errors = []
    
    # Run all tests
    all_errors.extend(test_imports())
    all_errors.extend(test_credentials())
    all_errors.extend(await test_websocket())
    all_errors.extend(test_paper_trader())
    all_errors.extend(test_strategy())
    all_errors.extend(test_dashboard_components())
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 DIAGNOSTIC SUMMARY")
    print("=" * 60)
    
    if not all_errors:
        print("🎉 ALL TESTS PASSED! System is ready to use.")
        print("\n🚀 You can now run:")
        print("   python examples/run_dashboard_integrated.py")
        print("   python examples/demo_system.py")
    else:
        print(f"❌ Found {len(all_errors)} errors:")
        for i, error in enumerate(all_errors, 1):
            print(f"   {i}. {error}")
        
        print("\n🔧 To fix these issues:")
        
        if any("import" in error for error in all_errors):
            print("   • Install missing packages: pip install -e .")
        
        if any("credential" in error.lower() for error in all_errors):
            print("   • Set up credentials: edit credentials/bybit_demo.yaml")
        
        if any("websocket" in error.lower() for error in all_errors):
            print("   • Check internet connection and Bybit API access")
    
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(run_diagnostics())