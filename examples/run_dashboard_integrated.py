#!/usr/bin/env python3
"""
Integrated Streamlit dashboard with live data connections.

This creates a dashboard that actually connects to:
1. Real WebSocket data from Bybit
2. Live paper trading
3. Active strategy execution
"""

import asyncio
import logging
import sys
import threading
import time
from pathlib import Path
from typing import Optional
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from alphaevolve.realtime.data.bybit_websocket import BybitWebSocketManager
from alphaevolve.realtime.data.orderbook import RealtimeOrderbook
from alphaevolve.realtime.trading.paper_trader import PaperTrader
from alphaevolve.realtime.strategies.realtime_base import SimpleSpreadStrategy

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global state for sharing data between async processes and Streamlit
class GlobalState:
    def __init__(self):
        self.orderbook: Optional[RealtimeOrderbook] = None
        self.paper_trader: Optional[PaperTrader] = None
        self.strategy: Optional[SimpleSpreadStrategy] = None
        self.ws_manager: Optional[BybitWebSocketManager] = None
        self.is_running = False
        self.last_update = time.time()
        self.message_count = 0
        self.error_log = []
    
    def log_error(self, message: str):
        timestamp = time.strftime("%H:%M:%S")
        self.error_log.append(f"[{timestamp}] ERROR: {message}")
        if len(self.error_log) > 10:
            self.error_log = self.error_log[-10:]  # Keep last 10 errors

    def log_info(self, message: str):
        timestamp = time.strftime("%H:%M:%S")
        self.error_log.append(f"[{timestamp}] INFO: {message}")
        if len(self.error_log) > 10:
            self.error_log = self.error_log[-10:]  # Keep last 10 logs

# Global state instance
if 'state' not in st.session_state:
    st.session_state.state = GlobalState()

state = st.session_state.state

async def start_trading_system():
    """Start the integrated trading system."""
    try:
        state.log_info("Initializing trading system...")
        
        # Initialize components
        symbol = "BTCUSDT"
        depth = 50
        
        # Create orderbook
        state.orderbook = RealtimeOrderbook(symbol, max_depth=depth)
        state.log_info(f"Created orderbook for {symbol}")
        
        # Create paper trader
        state.paper_trader = PaperTrader("credentials/bybit_demo.yaml")
        state.paper_trader.balance = 100000.0
        state.log_info(f"Initialized paper trader with ${state.paper_trader.balance:,.2f}")
        
        # Create strategy
        state.strategy = SimpleSpreadStrategy(spread_threshold=5.0, position_size=0.001)
        state.strategy.set_paper_trader(state.paper_trader)
        state.strategy.set_orderbook(state.orderbook)
        state.log_info(f"Created strategy: {state.strategy.name}")
        
        # Enhanced callback
        async def enhanced_callback(orderbook_data):
            try:
                state.message_count += 1
                state.last_update = time.time()
                
                # Update orderbook
                updated = state.orderbook.process_message(orderbook_data)
                
                if updated and state.strategy and state.strategy.is_running:
                    # Call strategy
                    await state.strategy.on_orderbook_update(orderbook_data)
                    
                    # Log every 50th update
                    if state.message_count % 50 == 0:
                        stats = state.orderbook.get_liquidity_stats()
                        state.log_info(f"Update #{state.message_count}: Mid=${stats.get('mid_price', 0):,.2f}, Spread={stats.get('spread', 0):.2f}")
                        
            except Exception as e:
                state.log_error(f"Callback error: {e}")
        
        # Create WebSocket manager
        state.ws_manager = BybitWebSocketManager(
            symbol=symbol,
            depth=depth,
            callback=enhanced_callback
        )
        
        # Start strategy
        state.strategy.start()
        state.log_info("Strategy started")
        
        # Start WebSocket
        state.is_running = True
        state.log_info("Starting WebSocket connection...")
        
        # Run WebSocket
        await state.ws_manager.start()
        
    except Exception as e:
        state.log_error(f"System startup error: {e}")
        logger.error(f"System startup error: {e}")

def run_async_system():
    """Run the async system in a separate thread."""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(start_trading_system())
    except Exception as e:
        state.log_error(f"Async system error: {e}")

def render_dashboard():
    """Render the main Streamlit dashboard."""
    
    # Page config
    st.set_page_config(
        page_title="Realtime Bybit Trading Dashboard",
        page_icon="📈",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Title
    st.title("🚀 Realtime Bybit Trading Dashboard")
    st.markdown("---")
    
    # Control buttons
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🟢 Start System", key="start_btn"):
            if not state.is_running:
                # Start system in background thread
                system_thread = threading.Thread(target=run_async_system, daemon=True)
                system_thread.start()
                st.success("System starting...")
                time.sleep(2)  # Give it time to start
                st.rerun()
    
    with col2:
        if st.button("🔄 Refresh Data", key="refresh_btn"):
            state.last_update = time.time()
            st.rerun()
            
    with col3:
        if st.button("🛑 Stop System", key="stop_btn"):
            if state.ws_manager:
                state.is_running = False
                st.warning("System stopping...")
    
    # Status indicators
    st.subheader("System Status")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if state.orderbook and state.orderbook.is_initialized:
            st.success("🟢 WebSocket Connected")
            st.caption(f"Messages: {state.message_count}")
        else:
            st.error("🔴 WebSocket Disconnected")
    
    with col2:
        if state.paper_trader:
            st.success("🟢 Paper Trader Active")
            summary = state.paper_trader.get_account_summary()
            st.caption(f"Balance: ${summary['balance']:,.2f}")
        else:
            st.warning("🟡 Paper Trader Inactive")
    
    with col3:
        if state.strategy and state.strategy.is_running:
            st.success(f"🟢 Strategy: {state.strategy.name}")
            st.caption("Running")
        elif state.strategy:
            st.warning(f"🟡 Strategy: {state.strategy.name}")
            st.caption("Stopped")
        else:
            st.error("🔴 No Strategy Loaded")
    
    with col4:
        if state.orderbook and state.orderbook.is_initialized:
            spread = state.orderbook.get_spread()
            st.info(f"📊 Spread: {spread:.2f}" if spread else "📊 Market Data")
            mid_price = state.orderbook.get_mid_price()
            st.caption(f"Mid: ${mid_price:,.2f}" if mid_price else "No price data")
        else:
            st.error("🔴 No Market Data")
    
    # Main content
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Orderbook chart
        st.subheader("📊 Order Book Depth")
        
        if state.orderbook and state.orderbook.is_initialized:
            try:
                df = state.orderbook.to_dataframe(max_levels=20)
                
                if not df.empty:
                    # Create orderbook depth chart
                    fig = go.Figure()
                    
                    # Add bids (green)
                    valid_bids = df[df['bid_price'].notna()]
                    if not valid_bids.empty:
                        fig.add_trace(go.Bar(
                            x=valid_bids['bid_price'],
                            y=valid_bids['bid_size'],
                            name='Bids',
                            marker_color='green',
                            opacity=0.7
                        ))
                    
                    # Add asks (red)
                    valid_asks = df[df['ask_price'].notna()]
                    if not valid_asks.empty:
                        fig.add_trace(go.Bar(
                            x=valid_asks['ask_price'],
                            y=valid_asks['ask_size'],
                            name='Asks',
                            marker_color='red',
                            opacity=0.7
                        ))
                    
                    fig.update_layout(
                        title=f"BTC/USDT Order Book - {time.strftime('%H:%M:%S')}",
                        xaxis_title="Price (USDT)",
                        yaxis_title="Size (BTC)",
                        height=400
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Stats
                    stats = state.orderbook.get_liquidity_stats()
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric("Best Bid", f"${stats.get('best_bid', 0):,.2f}")
                    with col2:
                        st.metric("Best Ask", f"${stats.get('best_ask', 0):,.2f}")
                    with col3:
                        st.metric("Spread", f"{stats.get('spread', 0):.2f}")
                    with col4:
                        st.metric("Mid Price", f"${stats.get('mid_price', 0):,.2f}")
                else:
                    st.warning("Empty orderbook data")
                    
            except Exception as e:
                st.error(f"Error rendering orderbook: {e}")
                state.log_error(f"Orderbook rendering error: {e}")
        else:
            st.warning("No orderbook data available")
        
        # Trade history
        st.subheader("📋 Recent Trades")
        
        if state.paper_trader:
            try:
                completed_orders = [
                    order for order in state.paper_trader.orders.values()
                    if order.status == 'Filled'
                ]
                
                if completed_orders:
                    trades_data = []
                    for order in completed_orders[-10:]:  # Last 10 trades
                        trades_data.append({
                            'Time': order.updated_at.strftime('%H:%M:%S'),
                            'Side': order.side,
                            'Quantity': f"{order.filled_quantity:.6f}",
                            'Price': f"${order.price:.2f}" if order.price else "Market",
                            'Status': order.status,
                        })
                    
                    st.dataframe(pd.DataFrame(trades_data), use_container_width=True)
                else:
                    st.info("No trades executed yet")
            except Exception as e:
                st.error(f"Error loading trades: {e}")
                state.log_error(f"Trade history error: {e}")
        else:
            st.warning("No paper trader available")
    
    with col2:
        # Account summary
        st.subheader("💰 Account Summary")
        
        if state.paper_trader:
            try:
                summary = state.paper_trader.get_account_summary()
                
                st.metric("Balance", f"${summary['balance']:,.2f}")
                st.metric("Total PnL", f"${summary['total_pnl']:,.2f}", 
                         delta=f"{summary['total_pnl']:+.2f}")
                st.metric("Equity", f"${summary['equity']:,.2f}")
                st.metric("Total Trades", summary['total_trades'])
                
                # Positions
                positions = [pos for pos in state.paper_trader.positions.values() if pos.size != 0]
                if positions:
                    st.subheader("📍 Active Positions")
                    for position in positions:
                        direction = "LONG" if position.size > 0 else "SHORT"
                        color = "green" if position.size > 0 else "red"
                        st.markdown(f"**{position.symbol}** :{color}[{direction}]")
                        st.write(f"Size: {abs(position.size):.6f} BTC")
                        st.write(f"Entry: ${position.entry_price:,.2f}")
                        pnl_color = "green" if position.get_total_pnl() >= 0 else "red"
                        st.markdown(f"PnL: :{pnl_color}[${position.get_total_pnl():+.2f}]")
                else:
                    st.info("No active positions")
                    
            except Exception as e:
                st.error(f"Error loading account: {e}")
                state.log_error(f"Account summary error: {e}")
        else:
            st.warning("No paper trader connected")
        
        # Performance metrics
        st.subheader("📈 Performance Metrics")
        
        if state.strategy:
            try:
                stats = state.strategy.get_performance_stats()
                
                st.metric("Signals Generated", stats['signals_generated'])
                st.metric("Orders Placed", stats['orders_placed'])
                
                runtime_minutes = stats['runtime_seconds'] / 60
                st.metric("Runtime", f"{runtime_minutes:.1f} min")
                
            except Exception as e:
                st.error(f"Error loading performance: {e}")
                state.log_error(f"Performance metrics error: {e}")
        else:
            st.warning("No strategy available")
    
    # System logs
    st.markdown("---")
    st.subheader("📝 System Logs")
    
    if state.error_log:
        for log_entry in state.error_log[-10:]:  # Last 10 logs
            if "ERROR" in log_entry:
                st.error(log_entry)
            elif "INFO" in log_entry:
                st.info(log_entry)
            else:
                st.text(log_entry)
    else:
        st.info("No system logs yet")
    
    # Auto-refresh
    if st.checkbox("Auto-refresh (5 seconds)", value=True):
        time.sleep(5)
        st.rerun()

if __name__ == "__main__":
    render_dashboard()