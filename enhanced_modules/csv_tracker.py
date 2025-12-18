"""
Enhanced CSV Tracking Module

Tracks extensive data for every trade to enable:
- Performance analysis
- Pattern discovery
- Strategy optimization
- A/B testing results

This module is OPTIONAL and can be toggled on/off.
It does NOT modify core trading logic - only tracks data.

Based on the 455-trade optimization tracking system from src/
"""

import csv
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class EnhancedTradeData:
    """
    Extended trade data for comprehensive analysis.

    Tracks 50+ fields across multiple categories:
    - Core trade data (price, PnL, duration)
    - Liquidity tracking (entry vs exit)
    - Volume data (24h, 1h)
    - Selection scoring
    - Source tracking (API, DEX)
    - Peak tracking (max gain, drawdown)
    - Configuration used
    - Transaction activity
    - Position sizing data
    - LP lock & rug prevention
    - Holder concentration
    - Contract safety
    - Momentum indicators
    """

    # Core trade data
    timestamp: datetime
    token_address: str
    symbol: str = ''
    entry_price: float = 0.0
    exit_price: float = 0.0
    position_size_usd: float = 0.0
    quantity: float = 0.0
    pnl_usd: float = 0.0
    pnl_percent: float = 0.0
    exit_reason: str = ''

    # Timing data
    entry_time: datetime = None
    exit_time: datetime = None
    duration_minutes: float = 0.0
    day_of_week: str = ''
    hour_of_day: int = 0

    # Liquidity tracking
    entry_liquidity: float = 0.0
    exit_liquidity: float = 0.0
    liquidity_change_percent: float = 0.0

    # Volume data
    volume_24h: float = 0.0
    volume_1h: float = 0.0

    # Selection scoring
    opportunity_score: float = 0.0
    risk_score: float = 0.0

    # Source tracking
    token_source: str = 'unknown'
    dex_platform: str = 'unknown'

    # Peak tracking
    max_gain_percent: float = 0.0
    peak_to_exit_drop_percent: float = 0.0
    entry_to_peak_minutes: float = 0.0
    peak_to_exit_minutes: float = 0.0
    highest_price: float = 0.0

    # Configuration
    config_stop_loss_percent: float = 0.0
    config_trailing_activation_percent: float = 0.0
    config_trailing_distance_percent: float = 0.0

    # Transaction activity
    txns_h1_buys: int = 0
    txns_h1_sells: int = 0
    buy_sell_ratio: float = 0.0

    # Position sizing (455-trade optimization)
    position_multiplier: float = 1.0
    golden_range_bonus: bool = False
    preferred_price_bonus: bool = False
    original_position_size: float = 0.0

    # LP lock & rug prevention
    lp_locked: bool = False
    lp_burned: bool = False
    lp_lock_days: int = 0

    # Holder concentration
    top10_concentration: float = 0.0
    top1_concentration: float = 0.0

    # Contract safety
    mint_authority_active: bool = False
    freeze_authority_active: bool = False
    ownership_renounced: bool = True

    # Momentum indicators
    price_change_1h: float = 0.0
    price_change_5min: float = 0.0
    price_change_1min: float = 0.0
    volume_spike_ratio: float = 0.0
    buy_pressure_recent: float = 0.0
    momentum_accelerating: bool = False


class CSVTracker:
    """
    Enhanced CSV tracking for comprehensive trade analysis.

    Usage:
        tracker = CSVTracker(enabled=True)

        # Log trade on exit
        tracker.log_trade(position, exit_reason)

        # Export to CSV
        tracker.export_csv('data/trades.csv')
    """

    def __init__(self, enabled: bool = True, auto_export: bool = True):
        """
        Initialize CSV tracker.

        Args:
            enabled: Whether tracking is enabled
            auto_export: Auto-export after each trade
        """
        self.enabled = enabled
        self.auto_export = auto_export
        self.trades: List[EnhancedTradeData] = []
        self.export_path = 'data/ml_trades.csv'

    def log_trade(
        self,
        position,
        exit_reason: str,
        exit_price: float,
        exit_time: datetime = None
    ) -> Optional[EnhancedTradeData]:
        """
        Log a completed trade with all tracking data.

        Args:
            position: Position object with all tracking fields
            exit_reason: Reason for exit (trailing_stop, stop_loss, etc.)
            exit_price: Exit price
            exit_time: Exit timestamp (defaults to now)

        Returns:
            EnhancedTradeData object or None if tracking disabled
        """
        if not self.enabled:
            return None

        if exit_time is None:
            exit_time = datetime.now()

        # Calculate duration
        duration_minutes = (exit_time - position.entry_time).total_seconds() / 60

        # Calculate PnL
        pnl_usd = (exit_price - position.entry_price) * position.quantity
        pnl_percent = ((exit_price - position.entry_price) / position.entry_price) * 100 if position.entry_price > 0 else 0

        # Calculate liquidity change
        liquidity_change_percent = 0.0
        if hasattr(position, 'entry_liquidity') and position.entry_liquidity > 0:
            exit_liq = getattr(position, 'current_liquidity', 0.0)
            liquidity_change_percent = ((exit_liq - position.entry_liquidity) / position.entry_liquidity) * 100

        # Calculate peak metrics
        max_gain_percent = 0.0
        peak_to_exit_drop_percent = 0.0
        entry_to_peak_minutes = 0.0
        peak_to_exit_minutes = 0.0

        if hasattr(position, 'highest_price') and position.highest_price > position.entry_price:
            max_gain_percent = ((position.highest_price - position.entry_price) / position.entry_price) * 100
            peak_to_exit_drop_percent = ((position.highest_price - exit_price) / position.highest_price) * 100

            if hasattr(position, 'peak_time') and position.peak_time:
                entry_to_peak_minutes = (position.peak_time - position.entry_time).total_seconds() / 60
                peak_to_exit_minutes = (exit_time - position.peak_time).total_seconds() / 60

        # Calculate buy/sell ratio
        buy_sell_ratio = 0.0
        if hasattr(position, 'txns_h1_buys') and hasattr(position, 'txns_h1_sells'):
            if position.txns_h1_sells > 0:
                buy_sell_ratio = position.txns_h1_buys / position.txns_h1_sells

        # Create enhanced trade data
        trade_data = EnhancedTradeData(
            # Core
            timestamp=exit_time,
            token_address=position.token_address,
            symbol=getattr(position, 'symbol', position.token_address[:8]),
            entry_price=position.entry_price,
            exit_price=exit_price,
            position_size_usd=position.amount_usd,
            quantity=position.quantity,
            pnl_usd=pnl_usd,
            pnl_percent=pnl_percent,
            exit_reason=exit_reason,

            # Timing
            entry_time=position.entry_time,
            exit_time=exit_time,
            duration_minutes=duration_minutes,
            day_of_week=exit_time.strftime('%A'),
            hour_of_day=exit_time.hour,

            # Liquidity
            entry_liquidity=getattr(position, 'entry_liquidity', 0.0),
            exit_liquidity=getattr(position, 'current_liquidity', 0.0),
            liquidity_change_percent=liquidity_change_percent,

            # Volume
            volume_24h=getattr(position, 'volume_24h', 0.0),
            volume_1h=getattr(position, 'volume_1h', 0.0),

            # Scoring
            opportunity_score=getattr(position, 'opportunity_score', 0.0),
            risk_score=0.0,  # Would come from RiskAssessor

            # Source
            token_source=getattr(position, 'token_source', 'unknown'),
            dex_platform=getattr(position, 'dex_platform', 'unknown'),

            # Peak tracking
            max_gain_percent=max_gain_percent,
            peak_to_exit_drop_percent=peak_to_exit_drop_percent,
            entry_to_peak_minutes=entry_to_peak_minutes,
            peak_to_exit_minutes=peak_to_exit_minutes,
            highest_price=getattr(position, 'highest_price', exit_price),

            # Configuration
            config_stop_loss_percent=getattr(position, 'config_stop_loss_percent', 0.0),
            config_trailing_activation_percent=getattr(position, 'config_trailing_activation_percent', 0.0),
            config_trailing_distance_percent=getattr(position, 'config_trailing_distance_percent', 15.0),

            # Transaction activity
            txns_h1_buys=getattr(position, 'txns_h1_buys', 0),
            txns_h1_sells=getattr(position, 'txns_h1_sells', 0),
            buy_sell_ratio=buy_sell_ratio,

            # Position sizing
            position_multiplier=getattr(position, 'position_multiplier_applied', 1.0),
            golden_range_bonus=getattr(position, 'golden_range_bonus', False),
            preferred_price_bonus=getattr(position, 'preferred_price_bonus', False),
            original_position_size=getattr(position, 'original_position_size', position.amount_usd),

            # LP lock
            lp_locked=getattr(position, 'lp_locked', False),
            lp_burned=getattr(position, 'lp_burned', False),
            lp_lock_days=getattr(position, 'lp_lock_days', 0),

            # Holder concentration
            top10_concentration=getattr(position, 'top10_concentration', 0.0),
            top1_concentration=getattr(position, 'top1_concentration', 0.0),

            # Contract safety
            mint_authority_active=getattr(position, 'mint_authority_active', False),
            freeze_authority_active=getattr(position, 'freeze_authority_active', False),
            ownership_renounced=getattr(position, 'ownership_renounced', True),

            # Momentum
            price_change_1h=getattr(position, 'price_change_1h', 0.0),
            price_change_5min=getattr(position, 'price_change_5min', 0.0),
            price_change_1min=getattr(position, 'price_change_1min', 0.0),
            volume_spike_ratio=getattr(position, 'volume_spike_ratio', 0.0),
            buy_pressure_recent=getattr(position, 'buy_pressure_recent', 0.0),
            momentum_accelerating=getattr(position, 'momentum_accelerating', False),
        )

        self.trades.append(trade_data)

        if self.auto_export:
            self.export_csv()

        logger.info(f"Logged trade: {trade_data.symbol} {pnl_percent:+.1f}% ({exit_reason})")

        return trade_data

    def export_csv(self, filepath: str = None) -> int:
        """
        Export all trades to CSV.

        Args:
            filepath: Path to save CSV (defaults to self.export_path)

        Returns:
            Number of trades exported
        """
        if not self.enabled or not self.trades:
            return 0

        if filepath is None:
            filepath = self.export_path

        # Create directory
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        # Define fieldnames (all 50+ fields)
        fieldnames = [
            'Date', 'Time', 'Day of Week', 'Hour',
            'Token', 'Symbol',
            'Entry Price', 'Exit Price', 'Price Change ($)', 'Price Change (%)',
            'Position Size ($)', 'Quantity', 'Tokens per Dollar',
            'PnL ($)', 'PnL (%)', 'Win/Loss', 'Exit Reason',
            'Duration (min)',
            # Liquidity
            'Entry Liquidity', 'Exit Liquidity', 'Liquidity Change (%)',
            # Volume
            'Volume 24h', 'Volume 1h',
            # Scoring
            'Opportunity Score', 'Risk Score',
            # Source
            'Token Source', 'DEX Platform',
            # Peak tracking
            'Max Gain (%)', 'Peak to Exit Drop (%)',
            'Entry to Peak (min)', 'Peak to Exit (min)', 'Highest Price',
            # Configuration
            'Config Stop Loss (%)', 'Config Trailing Activation (%)', 'Config Trailing Distance (%)',
            # Transaction activity
            'Txns H1 Buys', 'Txns H1 Sells', 'Buy/Sell Ratio',
            # Position sizing
            'Position Multiplier', 'Golden Range Bonus', 'Preferred Price Bonus', 'Original Position Size',
            # LP lock
            'LP Locked', 'LP Burned', 'LP Lock Days',
            # Holder concentration
            'Top 10 Concentration (%)', 'Top 1 Concentration (%)',
            # Contract safety
            'Mint Authority', 'Freeze Authority', 'Ownership Renounced',
            # Momentum
            'Price Change 1h (%)', 'Price Change 5min (%)', 'Price Change 1min (%)',
            'Volume Spike Ratio', 'Buy Pressure', 'Momentum Accelerating',
        ]

        # Write CSV
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for trade in self.trades:
                # Calculate derived fields
                price_change_usd = trade.exit_price - trade.entry_price
                tokens_per_dollar = 1.0 / trade.entry_price if trade.entry_price > 0 else 0
                win_loss = 'WIN' if trade.pnl_usd > 0 else 'LOSS' if trade.pnl_usd < 0 else 'BREAK-EVEN'

                writer.writerow({
                    'Date': trade.timestamp.strftime('%Y-%m-%d'),
                    'Time': trade.timestamp.strftime('%H:%M:%S'),
                    'Day of Week': trade.day_of_week,
                    'Hour': trade.hour_of_day,
                    'Token': trade.token_address[:16] + '...',
                    'Symbol': trade.symbol,
                    'Entry Price': f"${trade.entry_price:.8f}",
                    'Exit Price': f"${trade.exit_price:.8f}",
                    'Price Change ($)': f"${price_change_usd:.8f}",
                    'Price Change (%)': f"{trade.pnl_percent:.2f}%",
                    'Position Size ($)': f"${trade.position_size_usd:.2f}",
                    'Quantity': f"{trade.quantity:.2f}",
                    'Tokens per Dollar': f"{tokens_per_dollar:.0f}",
                    'PnL ($)': f"${trade.pnl_usd:.2f}",
                    'PnL (%)': f"{trade.pnl_percent:+.2f}%",
                    'Win/Loss': win_loss,
                    'Exit Reason': trade.exit_reason,
                    'Duration (min)': f"{trade.duration_minutes:.1f}",
                    # Liquidity
                    'Entry Liquidity': f"${trade.entry_liquidity:,.0f}",
                    'Exit Liquidity': f"${trade.exit_liquidity:,.0f}",
                    'Liquidity Change (%)': f"{trade.liquidity_change_percent:+.1f}%",
                    # Volume
                    'Volume 24h': f"${trade.volume_24h:,.0f}",
                    'Volume 1h': f"${trade.volume_1h:,.0f}",
                    # Scoring
                    'Opportunity Score': f"{trade.opportunity_score:.1f}",
                    'Risk Score': f"{trade.risk_score:.2f}",
                    # Source
                    'Token Source': trade.token_source,
                    'DEX Platform': trade.dex_platform,
                    # Peak tracking
                    'Max Gain (%)': f"{trade.max_gain_percent:.2f}%",
                    'Peak to Exit Drop (%)': f"{trade.peak_to_exit_drop_percent:.2f}%",
                    'Entry to Peak (min)': f"{trade.entry_to_peak_minutes:.1f}",
                    'Peak to Exit (min)': f"{trade.peak_to_exit_minutes:.1f}",
                    'Highest Price': f"${trade.highest_price:.8f}",
                    # Configuration
                    'Config Stop Loss (%)': f"{trade.config_stop_loss_percent:.1f}%",
                    'Config Trailing Activation (%)': f"{trade.config_trailing_activation_percent:.1f}%",
                    'Config Trailing Distance (%)': f"{trade.config_trailing_distance_percent:.1f}%",
                    # Transaction activity
                    'Txns H1 Buys': trade.txns_h1_buys,
                    'Txns H1 Sells': trade.txns_h1_sells,
                    'Buy/Sell Ratio': f"{trade.buy_sell_ratio:.2f}",
                    # Position sizing
                    'Position Multiplier': f"{trade.position_multiplier:.2f}x",
                    'Golden Range Bonus': 'Yes' if trade.golden_range_bonus else 'No',
                    'Preferred Price Bonus': 'Yes' if trade.preferred_price_bonus else 'No',
                    'Original Position Size': f"${trade.original_position_size:.2f}",
                    # LP lock
                    'LP Locked': 'Yes' if trade.lp_locked else 'No',
                    'LP Burned': 'Yes' if trade.lp_burned else 'No',
                    'LP Lock Days': trade.lp_lock_days,
                    # Holder concentration
                    'Top 10 Concentration (%)': f"{trade.top10_concentration:.1f}%",
                    'Top 1 Concentration (%)': f"{trade.top1_concentration:.1f}%",
                    # Contract safety
                    'Mint Authority': 'Yes' if trade.mint_authority_active else 'No',
                    'Freeze Authority': 'Yes' if trade.freeze_authority_active else 'No',
                    'Ownership Renounced': 'Yes' if trade.ownership_renounced else 'No',
                    # Momentum
                    'Price Change 1h (%)': f"{trade.price_change_1h:+.2f}%",
                    'Price Change 5min (%)': f"{trade.price_change_5min:+.2f}%",
                    'Price Change 1min (%)': f"{trade.price_change_1min:+.2f}%",
                    'Volume Spike Ratio': f"{trade.volume_spike_ratio:.2f}x",
                    'Buy Pressure': f"{trade.buy_pressure_recent:.2f}",
                    'Momentum Accelerating': 'Yes' if trade.momentum_accelerating else 'No',
                })

        logger.info(f"Exported {len(self.trades)} trades to {filepath}")
        return len(self.trades)

    def get_statistics(self) -> Dict:
        """Get trading statistics from logged trades."""
        if not self.trades:
            return {}

        wins = [t for t in self.trades if t.pnl_usd > 0]
        losses = [t for t in self.trades if t.pnl_usd < 0]

        return {
            'total_trades': len(self.trades),
            'wins': len(wins),
            'losses': len(losses),
            'win_rate': len(wins) / len(self.trades) * 100 if self.trades else 0,
            'avg_pnl': sum(t.pnl_usd for t in self.trades) / len(self.trades) if self.trades else 0,
            'avg_win': sum(t.pnl_usd for t in wins) / len(wins) if wins else 0,
            'avg_loss': sum(t.pnl_usd for t in losses) / len(losses) if losses else 0,
            'total_pnl': sum(t.pnl_usd for t in self.trades),
        }
