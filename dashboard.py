"""
Streamlit dashboard for the Solana Trading Bot.
Provides real-time monitoring, controls, and performance analytics.

Run with: streamlit run dashboard.py
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import json
import os
import sys

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.config import settings
from src.trading.paper_trading import PaperTradingEngine
from src.trading.position_manager import PositionManager

# Page configuration
st.set_page_config(
    page_title="Solana Trading Bot Dashboard",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
    }
    .positive {
        color: #00ff00;
    }
    .negative {
        color: #ff0000;
    }
</style>
""", unsafe_allow_html=True)

# Title
st.title("🤖 Solana Trading Bot Dashboard")

# Sidebar
with st.sidebar:
    st.header("⚙️ Controls")

    # Refresh button
    if st.button("🔄 Refresh Data"):
        st.rerun()

    st.divider()

    st.header("📊 Settings")

    # Current settings
    st.subheader("Current Configuration")
    st.write(f"**Mode:** {'📄 Paper Trading' if settings.is_paper_trading() else '💰 Live Trading'}")
    st.write(f"**Stop Loss:** {settings.risk.stop_loss_percent}%")
    st.write(f"**Take Profit:** {settings.risk.take_profit_percent}%")
    st.write(f"**Max Position:** ${settings.trading.max_position_size}")
    st.write(f"**Max Open Positions:** {settings.risk.max_open_positions}")

    st.divider()

    st.info("💡 Use Telegram commands to modify settings:\n- /stop_loss <pct>\n- /take_profit <pct>\n- /pause\n- /resume")


def load_portfolio_data():
    """Load current portfolio data."""
    # For now, we'll create a mock instance
    # In a real implementation, this would connect to the running bot
    engine = PaperTradingEngine(initial_capital=1000.0)

    # Try to load positions from log file
    try:
        # This is a simplified version - in production, you'd use a database or shared state
        # For now, show example data
        return {
            'portfolio_value': 1000.00,
            'cash': 1000.00,
            'invested': 0.00,
            'total_pnl': 0.00,
            'total_return_percent': 0.00,
            'positions': []
        }
    except Exception as e:
        st.error(f"Error loading portfolio data: {e}")
        return None


def load_log_data():
    """Load recent activity from log file."""
    try:
        log_file = 'trading_bot.log'
        if not os.path.exists(log_file):
            return []

        with open(log_file, 'r') as f:
            lines = f.readlines()
            # Get last 50 lines
            recent_logs = lines[-50:]

        # Parse log entries
        log_entries = []
        for line in recent_logs:
            if '[PAPER] BUY' in line or '[PAPER] SELL' in line:
                log_entries.append(line.strip())

        return log_entries
    except Exception as e:
        st.error(f"Error loading logs: {e}")
        return []


# Main content
tab1, tab2, tab3, tab4 = st.tabs(["📊 Portfolio", "📈 Positions", "📜 Activity Log", "📉 Performance"])

with tab1:
    st.header("Portfolio Overview")

    # Load portfolio data
    portfolio = load_portfolio_data()

    if portfolio:
        # Metrics row
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                label="💰 Portfolio Value",
                value=f"${portfolio['portfolio_value']:.2f}",
                delta=f"{portfolio['total_return_percent']:+.2f}%"
            )

        with col2:
            st.metric(
                label="💵 Cash Available",
                value=f"${portfolio['cash']:.2f}"
            )

        with col3:
            st.metric(
                label="📊 Invested",
                value=f"${portfolio['invested']:.2f}"
            )

        with col4:
            pnl_color = "normal" if portfolio['total_pnl'] >= 0 else "inverse"
            st.metric(
                label="📈 Total P&L",
                value=f"${portfolio['total_pnl']:.2f}",
                delta=f"{portfolio['total_return_percent']:+.2f}%",
                delta_color=pnl_color
            )

        st.divider()

        # Portfolio composition pie chart
        if portfolio['invested'] > 0:
            st.subheader("Portfolio Composition")

            fig = go.Figure(data=[go.Pie(
                labels=['Cash', 'Invested'],
                values=[portfolio['cash'], portfolio['invested']],
                hole=.3
            )])

            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("💡 No active positions. Bot will open positions when opportunities are found.")

with tab2:
    st.header("Open Positions")

    portfolio = load_portfolio_data()

    if portfolio and portfolio['positions']:
        # Create positions dataframe
        positions_data = []
        for pos in portfolio['positions']:
            positions_data.append({
                'Token': pos.token_address[:12] + '...',
                'Entry Price': f"${pos.entry_price:.8f}",
                'Current Price': f"${pos.current_price:.8f}",
                'Size': f"${pos.amount_usd:.2f}",
                'P&L %': f"{pos.unrealized_pnl_percent:+.2f}%",
                'P&L $': f"${pos.unrealized_pnl:+.2f}",
                'Stop Loss': f"${pos.stop_loss:.8f}",
                'Take Profit': f"${pos.take_profit:.8f}"
            })

        df = pd.DataFrame(positions_data)

        # Color code P&L
        def color_pnl(val):
            if '+' in val:
                return 'background-color: #90EE90'
            elif '-' in val:
                return 'background-color: #FFB6C1'
            return ''

        styled_df = df.style.applymap(color_pnl, subset=['P&L %', 'P&L $'])
        st.dataframe(styled_df, use_container_width=True)

        # Position details
        st.subheader("Position Details")
        for pos in portfolio['positions']:
            with st.expander(f"{pos.token_address[:12]}... - {pos.unrealized_pnl_percent:+.2f}%"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Entry Price:** ${pos.entry_price:.8f}")
                    st.write(f"**Current Price:** ${pos.current_price:.8f}")
                    st.write(f"**Quantity:** {pos.quantity:.4f}")
                with col2:
                    st.write(f"**Stop Loss:** ${pos.stop_loss:.8f}")
                    st.write(f"**Take Profit:** ${pos.take_profit:.8f}")
                    st.write(f"**Entry Time:** {pos.entry_time.strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        st.info("📭 No open positions currently.")
        st.write("The bot is monitoring markets and will open positions when opportunities arise.")

with tab3:
    st.header("Recent Activity")

    # Load recent logs
    log_entries = load_log_data()

    if log_entries:
        st.subheader(f"Last {len(log_entries)} Trades")

        for entry in reversed(log_entries):  # Most recent first
            # Parse the log entry
            if 'BUY' in entry:
                st.success(f"🟢 {entry}")
            elif 'SELL' in entry:
                if 'stop_loss' in entry.lower():
                    st.error(f"🔴 {entry}")
                elif 'take_profit' in entry.lower():
                    st.success(f"🟢 {entry}")
                else:
                    st.warning(f"🟡 {entry}")
    else:
        st.info("No trading activity yet. Logs will appear here once the bot starts trading.")

    st.divider()

    # Full log viewer
    with st.expander("📄 View Full Log File"):
        try:
            with open('trading_bot.log', 'r') as f:
                full_log = f.read()
            st.code(full_log, language='log')
        except FileNotFoundError:
            st.warning("Log file not found. Make sure the bot is running.")

with tab4:
    st.header("Performance Analytics")

    portfolio = load_portfolio_data()

    if portfolio:
        # Performance metrics
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Total Trades", 0)
        with col2:
            st.metric("Win Rate", "0.0%")
        with col3:
            st.metric("Avg Win/Loss", "$0.00 / $0.00")

        st.divider()

        # Placeholder for performance chart
        st.subheader("Portfolio Value Over Time")
        st.info("📊 Chart will show historical portfolio value once trading data is available.")

        # Example empty chart
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=[datetime.now() - timedelta(hours=i) for i in range(24, 0, -1)],
            y=[1000] * 24,
            mode='lines',
            name='Portfolio Value'
        ))

        fig.update_layout(
            xaxis_title="Time",
            yaxis_title="Portfolio Value ($)",
            height=400
        )

        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    st.subheader("Trade Distribution")
    st.info("📊 Trade statistics will appear here after completing some trades.")

# Footer
st.divider()
st.caption(f"🤖 Solana Trading Bot Dashboard | Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
st.caption("💡 This dashboard shows data from the log file. For real-time controls, use Telegram commands.")

# Auto-refresh every 30 seconds
st.empty()
