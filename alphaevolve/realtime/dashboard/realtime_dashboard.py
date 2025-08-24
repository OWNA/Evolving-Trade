"""
Streamlit dashboard components for real-time trading monitoring.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import Dict, Any, Optional, List
import asyncio
from datetime import datetime, timezone, timedelta
import time

import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from alphaevolve.realtime.data.orderbook import RealtimeOrderbook
from alphaevolve.realtime.trading.paper_trader import PaperTrader, Position
from alphaevolve.realtime.strategies.realtime_base import RealtimeHFTStrategy


class RealtimeDashboard:
    """
    Streamlit dashboard for real-time trading monitoring.
    
    Provides live visualization of:
    - Orderbook depth and spread
    - Strategy performance metrics
    - Position and P&L tracking
    - Trade execution logs
    """
    
    def __init__(self):
        """Initialize the dashboard."""
        self.setup_page_config()
        
    def setup_page_config(self):
        """Configure Streamlit page settings."""
        st.set_page_config(
            page_title="Realtime Bybit Trading Dashboard",
            page_icon="📈",
            layout="wide",
            initial_sidebar_state="expanded"
        )
        
    def render_main_dashboard(self, 
                            orderbook: Optional[RealtimeOrderbook] = None,
                            paper_trader: Optional[PaperTrader] = None,
                            strategy: Optional[RealtimeHFTStrategy] = None):
        """
        Render the main dashboard.
        
        Args:
            orderbook: Real-time orderbook data
            paper_trader: Paper trader instance
            strategy: Active trading strategy
        """
        # Header
        st.title("🚀 Realtime Bybit Trading Dashboard")
        st.markdown("---")
        
        # Status indicators
        self.render_status_indicators(orderbook, paper_trader, strategy)
        
        # Main content in columns
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Orderbook visualization
            self.render_orderbook_chart(orderbook)
            
            # Trade history
            self.render_trade_history(paper_trader)
            
        with col2:
            # Account summary
            self.render_account_summary(paper_trader)
            
            # Strategy controls
            self.render_strategy_controls(strategy)
            
            # Performance metrics
            self.render_performance_metrics(strategy, paper_trader)
        
        # Bottom section
        st.markdown("---")
        
        # Real-time logs
        self.render_live_logs()
    
    def render_status_indicators(self, 
                               orderbook: Optional[RealtimeOrderbook] = None,
                               paper_trader: Optional[PaperTrader] = None,
                               strategy: Optional[RealtimeHFTStrategy] = None):
        """Render connection and system status indicators."""
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            # WebSocket connection status
            if orderbook and orderbook.is_initialized:
                st.success("🟢 WebSocket Connected")
                st.caption(f"Last update: {orderbook.last_update_time}")
            else:
                st.error("🔴 WebSocket Disconnected")
        
        with col2:
            # Paper trader status
            if paper_trader:
                st.success("🟢 Paper Trader Active")
                summary = paper_trader.get_account_summary()
                st.caption(f"Balance: ${summary['balance']:,.2f}")
            else:
                st.warning("🟡 Paper Trader Inactive")
        
        with col3:
            # Strategy status
            if strategy and strategy.is_running:
                st.success(f"🟢 Strategy: {strategy.name}")
                st.caption("Running")
            elif strategy:
                st.warning(f"🟡 Strategy: {strategy.name}")
                st.caption("Stopped")
            else:
                st.error("🔴 No Strategy Loaded")
        
        with col4:
            # Market status
            if orderbook and orderbook.is_initialized:
                spread = orderbook.get_spread()
                st.info(f"📊 Spread: {spread:.2f}" if spread else "📊 Market Data")
                mid_price = orderbook.get_mid_price()
                st.caption(f"Mid: ${mid_price:,.2f}" if mid_price else "No price data")
            else:
                st.error("🔴 No Market Data")
    
    def render_orderbook_chart(self, orderbook: Optional[RealtimeOrderbook]):
        """Render real-time orderbook depth chart."""
        st.subheader("📊 Order Book Depth")
        
        if not orderbook or not orderbook.is_initialized:
            st.warning("No orderbook data available")
            return
        
        try:
            # Get orderbook data
            df = orderbook.to_dataframe(max_levels=20)
            
            if df.empty:
                st.warning("Empty orderbook data")
                return
            
            # Create depth chart
            fig = make_subplots(
                rows=2, cols=1,
                subplot_titles=('Order Book Depth', 'Spread Over Time'),
                vertical_spacing=0.1
            )
            
            # Orderbook depth visualization
            # Bids (buy orders) - green
            valid_bids = df[df['bid_price'].notna()]
            if not valid_bids.empty:
                fig.add_trace(
                    go.Bar(
                        x=valid_bids['bid_price'],
                        y=valid_bids['bid_size'],
                        name='Bids',
                        marker_color='green',
                        opacity=0.7
                    ),
                    row=1, col=1
                )
            
            # Asks (sell orders) - red
            valid_asks = df[df['ask_price'].notna()]
            if not valid_asks.empty:
                fig.add_trace(
                    go.Bar(
                        x=valid_asks['ask_price'],
                        y=valid_asks['ask_size'],
                        name='Asks',
                        marker_color='red',
                        opacity=0.7
                    ),
                    row=1, col=1
                )
            
            # Update layout
            fig.update_layout(
                height=600,
                title_text=f"BTC/USDT Order Book - {datetime.now().strftime('%H:%M:%S')}",
                showlegend=True
            )
            
            # Add current spread as annotation
            spread = orderbook.get_spread()
            best_bid = orderbook.get_best_bid()
            best_ask = orderbook.get_best_ask()
            
            if spread and best_bid and best_ask:
                fig.add_annotation(
                    x=(best_bid.price + best_ask.price) / 2,
                    y=max(df['bid_size'].max(), df['ask_size'].max()) / 2,
                    text=f"Spread: {spread:.2f}",
                    showarrow=True,
                    arrowhead=2,
                    row=1, col=1
                )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Show orderbook statistics
            stats = orderbook.get_liquidity_stats()
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Best Bid", f"${stats.get('best_bid', 0):,.2f}", 
                         help="Highest buy order price")
            with col2:
                st.metric("Best Ask", f"${stats.get('best_ask', 0):,.2f}",
                         help="Lowest sell order price")
            with col3:
                st.metric("Spread", f"{stats.get('spread', 0):.2f}",
                         help="Difference between best ask and bid")
            with col4:
                st.metric("Mid Price", f"${stats.get('mid_price', 0):,.2f}",
                         help="Average of best bid and ask")
                
        except Exception as e:
            st.error(f"Error rendering orderbook chart: {e}")
    
    def render_account_summary(self, paper_trader: Optional[PaperTrader]):
        """Render account balance and position summary."""
        st.subheader("💰 Account Summary")
        
        if not paper_trader:
            st.warning("No paper trader connected")
            return
        
        try:
            summary = paper_trader.get_account_summary()
            
            # Account metrics
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric(
                    "Balance",
                    f"${summary['balance']:,.2f}",
                    help="Available trading balance"
                )
                st.metric(
                    "Total PnL",
                    f"${summary['total_pnl']:,.2f}",
                    delta=f"{summary['total_pnl']:+.2f}",
                    help="Total realized + unrealized PnL"
                )
                
            with col2:
                st.metric(
                    "Equity",
                    f"${summary['equity']:,.2f}",
                    help="Balance + unrealized PnL"
                )
                st.metric(
                    "Total Trades",
                    summary['total_trades'],
                    help="Total executed trades"
                )
            
            # Positions
            positions = [pos for pos in paper_trader.positions.values() if pos.size != 0]
            
            if positions:
                st.subheader("📍 Active Positions")
                
                for position in positions:
                    with st.container():
                        col1, col2, col3 = st.columns([1, 1, 1])
                        
                        with col1:
                            direction = "LONG" if position.size > 0 else "SHORT"
                            color = "green" if position.size > 0 else "red"
                            st.markdown(f"**{position.symbol}** :{color}[{direction}]")
                            
                        with col2:
                            st.write(f"Size: {abs(position.size):.6f} BTC")
                            st.write(f"Entry: ${position.entry_price:,.2f}")
                            
                        with col3:
                            pnl_color = "green" if position.get_total_pnl() >= 0 else "red"
                            st.markdown(f"PnL: :{pnl_color}[${position.get_total_pnl():+.2f}]")
                            st.write(f"Unrealized: ${position.unrealized_pnl:+.2f}")
            else:
                st.info("No active positions")
                
            # Open orders
            open_orders = paper_trader.get_open_orders()
            if open_orders:
                st.subheader("📋 Open Orders")
                
                orders_data = []
                for order in open_orders:
                    orders_data.append({
                        'ID': order.order_id[-8:],  # Last 8 chars
                        'Side': order.side,
                        'Type': order.order_type,
                        'Quantity': f"{order.quantity:.6f}",
                        'Price': f"${order.price:.2f}" if order.price else "Market",
                        'Status': order.status,
                    })
                
                st.dataframe(pd.DataFrame(orders_data), use_container_width=True)
            
        except Exception as e:
            st.error(f"Error rendering account summary: {e}")
    
    def render_strategy_controls(self, strategy: Optional[RealtimeHFTStrategy]):
        """Render strategy control panel."""
        st.subheader("⚙️ Strategy Controls")
        
        if not strategy:
            st.warning("No strategy loaded")
            return
        
        try:
            # Strategy info
            st.write(f"**Strategy:** {strategy.name}")
            
            # Start/Stop controls
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("▶️ Start Strategy", key="start_btn"):
                    strategy.start()
                    st.success("Strategy started!")
                    
            with col2:
                if st.button("⏹️ Stop Strategy", key="stop_btn"):
                    strategy.stop()
                    st.success("Strategy stopped!")
            
            # Strategy parameters (if editable)
            st.subheader("Parameters")
            
            # Generic parameter display
            if hasattr(strategy, 'max_position_size'):
                new_max_pos = st.number_input(
                    "Max Position Size (BTC)",
                    value=strategy.max_position_size,
                    min_value=0.001,
                    max_value=10.0,
                    step=0.001,
                    key="max_pos"
                )
                strategy.max_position_size = new_max_pos
            
            if hasattr(strategy, 'min_spread_threshold'):
                new_spread_thresh = st.number_input(
                    "Min Spread Threshold (USDT)",
                    value=strategy.min_spread_threshold,
                    min_value=0.1,
                    max_value=100.0,
                    step=0.1,
                    key="spread_thresh"
                )
                strategy.min_spread_threshold = new_spread_thresh
            
            # Risk limits
            st.subheader("Risk Limits")
            
            if hasattr(strategy, 'daily_loss_limit'):
                new_loss_limit = st.number_input(
                    "Daily Loss Limit (USDT)",
                    value=strategy.daily_loss_limit,
                    min_value=100.0,
                    max_value=10000.0,
                    step=100.0,
                    key="loss_limit"
                )
                strategy.daily_loss_limit = new_loss_limit
            
        except Exception as e:
            st.error(f"Error rendering strategy controls: {e}")
    
    def render_performance_metrics(self, 
                                 strategy: Optional[RealtimeHFTStrategy],
                                 paper_trader: Optional[PaperTrader]):
        """Render strategy performance metrics."""
        st.subheader("📈 Performance Metrics")
        
        if not strategy:
            st.warning("No strategy available")
            return
        
        try:
            stats = strategy.get_performance_stats()
            
            # Key metrics
            st.metric("Signals Generated", stats['signals_generated'])
            st.metric("Orders Placed", stats['orders_placed'])
            
            runtime_minutes = stats['runtime_seconds'] / 60
            st.metric("Runtime", f"{runtime_minutes:.1f} min")
            
            if stats['orders_placed'] > 0:
                signal_to_order_ratio = stats['signals_generated'] / stats['orders_placed']
                st.metric("Signal/Order Ratio", f"{signal_to_order_ratio:.2f}")
            
            # Trading performance
            if paper_trader:
                account_summary = paper_trader.get_account_summary()
                
                if account_summary['total_trades'] > 0:
                    avg_trade_size = account_summary['total_pnl'] / account_summary['total_trades']
                    st.metric("Avg Trade PnL", f"${avg_trade_size:.2f}")
                
                st.metric("Total Fees", f"${account_summary.get('total_fees', 0):.2f}")
                
                # Return percentage
                if account_summary['balance'] > 0:
                    return_pct = (account_summary['total_pnl'] / account_summary['balance']) * 100
                    st.metric("Return %", f"{return_pct:+.2f}%")
            
        except Exception as e:
            st.error(f"Error rendering performance metrics: {e}")
    
    def render_trade_history(self, paper_trader: Optional[PaperTrader]):
        """Render recent trade history."""
        st.subheader("📋 Recent Trades")
        
        if not paper_trader:
            st.warning("No paper trader available")
            return
        
        try:
            # Get completed orders (trades)
            completed_orders = [
                order for order in paper_trader.orders.values()
                if order.status == 'Filled'
            ]
            
            if not completed_orders:
                st.info("No trades executed yet")
                return
            
            # Sort by creation time (most recent first)
            completed_orders.sort(key=lambda x: x.created_at, reverse=True)
            
            # Display recent trades (last 10)
            recent_trades = completed_orders[:10]
            
            trades_data = []
            for order in recent_trades:
                trades_data.append({
                    'Time': order.updated_at.strftime('%H:%M:%S'),
                    'Side': order.side,
                    'Quantity': f"{order.filled_quantity:.6f}",
                    'Price': f"${order.price:.2f}" if order.price else "Market",
                    'Status': order.status,
                })
            
            df_trades = pd.DataFrame(trades_data)
            
            # Color code by side
            def color_side(val):
                if val == 'Buy':
                    return 'background-color: #d4edda'
                elif val == 'Sell':
                    return 'background-color: #f8d7da'
                return ''
            
            styled_df = df_trades.style.applymap(color_side, subset=['Side'])
            st.dataframe(styled_df, use_container_width=True)
            
            # Trade statistics
            if len(completed_orders) > 1:
                st.subheader("Trade Statistics")
                
                buy_orders = [o for o in completed_orders if o.side == 'Buy']
                sell_orders = [o for o in completed_orders if o.side == 'Sell']
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Total Trades", len(completed_orders))
                
                with col2:
                    st.metric("Buy Orders", len(buy_orders))
                    
                with col3:
                    st.metric("Sell Orders", len(sell_orders))
                    
        except Exception as e:
            st.error(f"Error rendering trade history: {e}")
    
    def render_live_logs(self):
        """Render live system logs."""
        st.subheader("📝 Live System Logs")
        
        # This would be connected to actual logging system
        # For now, show placeholder
        log_container = st.container()
        
        with log_container:
            # Simulate some log entries
            sample_logs = [
                f"[{datetime.now().strftime('%H:%M:%S')}] INFO: WebSocket connection active",
                f"[{datetime.now().strftime('%H:%M:%S')}] INFO: Orderbook updated - spread: 5.2 USDT",
                f"[{datetime.now().strftime('%H:%M:%S')}] INFO: Strategy signal generated",
            ]
            
            for log_entry in sample_logs[-5:]:  # Show last 5 logs
                st.text(log_entry)
        
        # Auto-refresh toggle
        if st.checkbox("Auto-refresh logs", value=False):
            time.sleep(1)
            st.rerun()
    
    def render_sidebar_config(self):
        """Render sidebar configuration options."""
        st.sidebar.header("🔧 Configuration")
        
        # Connection settings
        st.sidebar.subheader("Connection")
        symbol = st.sidebar.selectbox("Symbol", ["BTCUSDT", "ETHUSDT", "SOLUSDT"])
        depth = st.sidebar.selectbox("Orderbook Depth", [10, 25, 50])
        
        # Strategy selection
        st.sidebar.subheader("Strategy")
        strategy_name = st.sidebar.selectbox(
            "Select Strategy",
            ["SimpleSpreadStrategy", "Custom Strategy"]
        )
        
        # Refresh settings
        st.sidebar.subheader("Display")
        auto_refresh = st.sidebar.checkbox("Auto-refresh", value=True)
        refresh_interval = st.sidebar.slider("Refresh Interval (s)", 1, 10, 2)
        
        return {
            'symbol': symbol,
            'depth': depth,
            'strategy_name': strategy_name,
            'auto_refresh': auto_refresh,
            'refresh_interval': refresh_interval
        }


def create_dashboard_app():
    """Create the main Streamlit dashboard app."""
    dashboard = RealtimeDashboard()
    
    # Render sidebar config
    config = dashboard.render_sidebar_config()
    
    # Main dashboard content
    # Note: In a real implementation, you would connect these to actual instances
    dashboard.render_main_dashboard(
        orderbook=None,  # Connect to real orderbook
        paper_trader=None,  # Connect to real paper trader
        strategy=None  # Connect to real strategy
    )
    
    # Auto-refresh
    if config['auto_refresh']:
        time.sleep(config['refresh_interval'])
        st.rerun()


if __name__ == "__main__":
    create_dashboard_app()