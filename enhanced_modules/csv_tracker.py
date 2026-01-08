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
    pnl_percent: float = 0.0                    # DEPRECATED: Use token_price_change_percent instead
    token_price_change_percent: float = 0.0     # How much the token price changed (entry -> exit)
    position_pnl_percent: float = 0.0           # Actual position P&L % (includes partial profits)
    exit_reason: str = ''

    # Rug detection tracking
    is_rug: bool = False                        # True if exit was due to rug detection
    rug_type: str = ''                          # stale_price, frozen_price, liquidity_dead, or empty

    # Partial profit tracking
    partial_profit_usd: float = 0.0         # Total profit from partial sells
    partial_profit_count: int = 0           # Number of partial profit milestones hit
    milestones_hit: str = ''                # Comma-separated list of milestones (e.g., "50,100,200")
    remaining_quantity_percent: float = 100.0  # % of position remaining at final exit
    total_realized_pnl_usd: float = 0.0     # Partial profits + final exit profit

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
    exit_volume_24h: float = 0.0           # Volume at exit (for spike analysis)
    exit_volume_1h: float = 0.0            # 1h volume at exit
    volume_change_24h_percent: float = 0.0 # Entry vs exit volume change
    volume_change_1h_percent: float = 0.0  # 1h volume change

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
    buy_sell_ratio: float = 0.0            # Buys/Sells ratio
    entry_buy_ratio: float = 0.0           # Buys/(Buys+Sells) at entry (0-1)
    exit_buy_ratio: float = 0.0            # Buys/(Buys+Sells) at exit (0-1)
    exit_txns_h1_buys: int = 0             # Buy transactions at exit
    exit_txns_h1_sells: int = 0            # Sell transactions at exit

    # Position sizing (455-trade optimization)
    position_multiplier: float = 1.0
    golden_range_bonus: bool = False
    preferred_price_bonus: bool = False
    original_position_size: float = 0.0

    # LP lock & rug prevention
    lp_locked: bool = False
    lp_burned: bool = False
    lp_lock_days: int = 0
    lp_burned_percent: float = 0.0         # % of LP burned (0-100)

    # Holder concentration
    holder_count: int = 0                  # Total number of holders
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

    # ⚡ CRITICAL ANALYSIS FIELDS (from 401-trade analysis)
    # Drawdown tracking (ML Bot primary signal!)
    current_drawdown_percent: float = 0.0  # Current DD from peak
    max_drawdown_percent: float = 0.0      # Maximum DD reached

    # Token age (bluechip filter)
    token_age_hours: float = 0.0           # Hours since token creation
    token_age_minutes: float = 0.0         # Minutes (for 5-30m timing analysis)

    # Volume/Liquidity momentum
    vol_liq_ratio: float = 0.0             # volume_24h / liquidity (momentum indicator)

    # Entry momentum (timing analysis)
    entry_price_change_5m: float = 0.0     # Price change 5m at entry
    entry_price_change_1h: float = 0.0     # Price change 1h at entry

    # Multi-source data validation (cross-check APIs)
    birdeye_security_score: float = 0.0    # Birdeye security rating
    birdeye_trending_rank: int = 0         # Birdeye trending position
    coingecko_trending_score: float = 0.0  # CoinGecko trending score
    has_freeze_authority: bool = False     # Can token be frozen?
    has_mint_authority: bool = False       # Can supply be minted?
    volume_crosscheck_percent: float = 0.0 # DexScreener vs Birdeye volume difference %
    liquidity_crosscheck_percent: float = 0.0  # DexScreener vs Birdeye liq difference %
    jupiter_organic_score: float = 0.0     # Jupiter organic activity score

    # Data provider tracking (which source works best?)
    data_provider: str = 'unknown'         # DexScreener, Jupiter, etc.
    discovery_source: str = 'unknown'      # Where token was discovered

    # Rug detection indicators
    price_frozen: bool = False             # Price hasn't moved >0.1% in 15+ min
    consecutive_failed_updates: int = 0    # Failed price updates count


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

        # Calculate PnL for final exit (remaining position only)
        final_exit_pnl_usd = (exit_price - position.entry_price) * position.quantity

        # Get partial profit data
        partial_profit_usd = getattr(position, 'total_partial_profit_usd', 0.0)
        milestones_hit_set = getattr(position, 'milestones_hit', set())
        initial_quantity = getattr(position, 'initial_quantity', position.quantity)

        # 🚨 BUG FIX: Validate partial profits make sense!
        # If exit_reason is stop_loss/rug, there should be NO partial profits!
        if exit_reason in ['stop_loss', 'fast_rug_exit_2min', 'zombie_exit_45min'] or exit_reason.startswith('rug_'):
            if partial_profit_usd > 0:
                logger.warning(
                    f"⚠️ DATA BUG DETECTED: {getattr(position, 'symbol', 'Unknown')} has "
                    f"partial profits ${partial_profit_usd:.2f} but exited at {exit_reason}! "
                    f"This is impossible (price must have been losing). Resetting to $0."
                )
                partial_profit_usd = 0.0
                milestones_hit_set = set()

        # Calculate total realized P&L (partial profits + final exit)
        total_realized_pnl_usd = partial_profit_usd + final_exit_pnl_usd

        # Calculate initial investment (original position size)
        initial_investment_usd = position.entry_price * initial_quantity

        # Calculate P&L percentages
        token_price_change_percent = ((exit_price - position.entry_price) / position.entry_price) * 100 if position.entry_price > 0 else 0
        position_pnl_percent = (total_realized_pnl_usd / initial_investment_usd) * 100 if initial_investment_usd > 0 else 0
        pnl_percent = token_price_change_percent  # Keep for backward compatibility

        # 🚨 SANITY CHECK: Detect extreme PnL vs price change mismatch (CoinMaxing bug!)
        # If token price changed <10% but position PnL is >1000%, data is corrupted!
        if abs(token_price_change_percent) < 10 and abs(position_pnl_percent) > 1000:
            logger.error(
                f"🚨 DATA CORRUPTION DETECTED: {getattr(position, 'symbol', 'Unknown')} "
                f"price changed {token_price_change_percent:.1f}% but position PnL is {position_pnl_percent:.1f}%! "
                f"Using token price change as PnL (more reliable)."
            )
            # Use token price change since it's based on actual prices (more reliable)
            position_pnl_percent = token_price_change_percent
            total_realized_pnl_usd = final_exit_pnl_usd  # Ignore partial profits (corrupted!)

        # Calculate remaining quantity percentage
        remaining_quantity_percent = (position.quantity / initial_quantity * 100) if initial_quantity > 0 else 100.0

        # Format milestones as comma-separated string
        milestones_hit_str = ','.join(str(m) for m in sorted(milestones_hit_set)) if milestones_hit_set else ''

        # Use total realized PnL as the main pnl_usd field
        pnl_usd = total_realized_pnl_usd

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

        # Calculate entry and exit buy ratios (buys / (buys + sells))
        entry_buy_ratio = 0.0
        exit_buy_ratio = 0.0
        entry_buys = getattr(position, 'txns_h1_buys', 0)
        entry_sells = getattr(position, 'txns_h1_sells', 0)
        exit_buys = getattr(position, 'exit_txns_h1_buys', entry_buys)  # Fallback to entry if not tracked
        exit_sells = getattr(position, 'exit_txns_h1_sells', entry_sells)

        if (entry_buys + entry_sells) > 0:
            entry_buy_ratio = entry_buys / (entry_buys + entry_sells)
        if (exit_buys + exit_sells) > 0:
            exit_buy_ratio = exit_buys / (exit_buys + exit_sells)

        # Calculate exit volumes and volume changes
        exit_volume_24h = getattr(position, 'exit_volume_24h', 0.0)
        exit_volume_1h = getattr(position, 'exit_volume_1h', 0.0)
        entry_volume_24h = getattr(position, 'volume_24h', 0.0)
        entry_volume_1h = getattr(position, 'volume_1h', 0.0)

        volume_change_24h_percent = 0.0
        volume_change_1h_percent = 0.0
        if entry_volume_24h > 0:
            volume_change_24h_percent = ((exit_volume_24h - entry_volume_24h) / entry_volume_24h) * 100
        if entry_volume_1h > 0:
            volume_change_1h_percent = ((exit_volume_1h - entry_volume_1h) / entry_volume_1h) * 100

        # Detect if this is a rug exit
        is_rug = exit_reason.startswith('rug_')
        rug_type = ''
        if is_rug:
            # Extract rug type from exit_reason (e.g., 'rug_stale_price' -> 'stale_price')
            rug_type = exit_reason.replace('rug_', '')

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
            token_price_change_percent=token_price_change_percent,
            position_pnl_percent=position_pnl_percent,
            exit_reason=exit_reason,

            # Rug detection tracking
            is_rug=is_rug,
            rug_type=rug_type,

            # Partial profit tracking
            partial_profit_usd=partial_profit_usd,
            partial_profit_count=len(milestones_hit_set),
            milestones_hit=milestones_hit_str,
            remaining_quantity_percent=remaining_quantity_percent,
            total_realized_pnl_usd=total_realized_pnl_usd,

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
            volume_24h=entry_volume_24h,
            volume_1h=entry_volume_1h,
            exit_volume_24h=exit_volume_24h,
            exit_volume_1h=exit_volume_1h,
            volume_change_24h_percent=volume_change_24h_percent,
            volume_change_1h_percent=volume_change_1h_percent,

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
            txns_h1_buys=entry_buys,
            txns_h1_sells=entry_sells,
            buy_sell_ratio=buy_sell_ratio,
            entry_buy_ratio=entry_buy_ratio,
            exit_buy_ratio=exit_buy_ratio,
            exit_txns_h1_buys=exit_buys,
            exit_txns_h1_sells=exit_sells,

            # Position sizing
            position_multiplier=getattr(position, 'position_multiplier_applied', 1.0),
            golden_range_bonus=getattr(position, 'golden_range_bonus', False),
            preferred_price_bonus=getattr(position, 'preferred_price_bonus', False),
            original_position_size=getattr(position, 'original_position_size', position.amount_usd),

            # LP lock
            lp_locked=getattr(position, 'lp_locked', False),
            lp_burned=getattr(position, 'lp_burned', False),
            lp_lock_days=getattr(position, 'lp_lock_days', 0),
            lp_burned_percent=getattr(position, 'lp_burned_percent', 0.0),

            # Holder concentration
            holder_count=getattr(position, 'holder_count', 0),
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
            'PnL ($)', 'PnL (%)', 'Token Price Change (%)', 'Position PnL (%)', 'Win/Loss', 'Exit Reason',
            'Duration (min)',
            # Liquidity
            'Entry Liquidity', 'Exit Liquidity', 'Liquidity Change (%)',
            # Volume
            'Volume 24h', 'Volume 1h',
            'Exit Volume 24h', 'Exit Volume 1h',
            'Volume Change 24h (%)', 'Volume Change 1h (%)',
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
            'Entry Buy Ratio', 'Exit Buy Ratio',
            'Exit Txns H1 Buys', 'Exit Txns H1 Sells',
            # Position sizing
            'Position Multiplier', 'Golden Range Bonus', 'Preferred Price Bonus', 'Original Position Size',
            # LP lock
            'LP Locked', 'LP Burned', 'LP Lock Days', 'LP Burned (%)',
            # Holder concentration
            'Holder Count', 'Top 10 Concentration (%)', 'Top 1 Concentration (%)',
            # Contract safety
            'Mint Authority', 'Freeze Authority', 'Ownership Renounced',
            # Momentum
            'Price Change 1h (%)', 'Price Change 5min (%)', 'Price Change 1min (%)',
            'Volume Spike Ratio', 'Buy Pressure', 'Momentum Accelerating',
            # ⚡ Critical Analysis Fields (401-trade analysis)
            'Current Drawdown (%)', 'Max Drawdown (%)',
            'Token Age (hours)', 'Token Age (minutes)',
            # ⚡ Timing & Momentum Analysis
            'Vol/Liq Ratio', 'Entry Price Change 5m (%)', 'Entry Price Change 1h (%)',
            # ⚡ Multi-Source Data Validation
            'Birdeye Security Score', 'Birdeye Trending Rank', 'CoinGecko Trending Score',
            'Has Freeze Authority', 'Has Mint Authority',
            'Volume Crosscheck (%)', 'Liquidity Crosscheck (%)',
            'Jupiter Organic Score',
            'Data Provider', 'Discovery Source',
            'Price Frozen', 'Failed Updates Count',
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
                    'Token Price Change (%)': f"{trade.token_price_change_percent:+.2f}%",
                    'Position PnL (%)': f"{trade.position_pnl_percent:+.2f}%",
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
                    'Exit Volume 24h': f"${trade.exit_volume_24h:,.0f}",
                    'Exit Volume 1h': f"${trade.exit_volume_1h:,.0f}",
                    'Volume Change 24h (%)': f"{trade.volume_change_24h_percent:+.1f}%",
                    'Volume Change 1h (%)': f"{trade.volume_change_1h_percent:+.1f}%",
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
                    'Entry Buy Ratio': f"{trade.entry_buy_ratio:.3f}",
                    'Exit Buy Ratio': f"{trade.exit_buy_ratio:.3f}",
                    'Exit Txns H1 Buys': trade.exit_txns_h1_buys,
                    'Exit Txns H1 Sells': trade.exit_txns_h1_sells,
                    # Position sizing
                    'Position Multiplier': f"{trade.position_multiplier:.2f}x",
                    'Golden Range Bonus': 'Yes' if trade.golden_range_bonus else 'No',
                    'Preferred Price Bonus': 'Yes' if trade.preferred_price_bonus else 'No',
                    'Original Position Size': f"${trade.original_position_size:.2f}",
                    # LP lock
                    'LP Locked': 'Yes' if trade.lp_locked else 'No',
                    'LP Burned': 'Yes' if trade.lp_burned else 'No',
                    'LP Lock Days': trade.lp_lock_days,
                    'LP Burned (%)': f"{trade.lp_burned_percent:.1f}%",
                    # Holder concentration
                    'Holder Count': trade.holder_count,
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
                    # ⚡ Critical Analysis Fields
                    'Current Drawdown (%)': f"{trade.current_drawdown_percent:.2f}%",
                    'Max Drawdown (%)': f"{trade.max_drawdown_percent:.2f}%",
                    'Token Age (hours)': f"{trade.token_age_hours:.1f}",
                    'Token Age (minutes)': f"{trade.token_age_minutes:.1f}",
                    # ⚡ Timing & Momentum Analysis
                    'Vol/Liq Ratio': f"{trade.vol_liq_ratio:.2f}x",
                    'Entry Price Change 5m (%)': f"{trade.entry_price_change_5m:+.2f}%",
                    'Entry Price Change 1h (%)': f"{trade.entry_price_change_1h:+.2f}%",
                    # ⚡ Multi-Source Data Validation
                    'Birdeye Security Score': f"{trade.birdeye_security_score:.2f}",
                    'Birdeye Trending Rank': trade.birdeye_trending_rank,
                    'CoinGecko Trending Score': f"{trade.coingecko_trending_score:.2f}",
                    'Has Freeze Authority': 'Yes' if trade.has_freeze_authority else 'No',
                    'Has Mint Authority': 'Yes' if trade.has_mint_authority else 'No',
                    'Volume Crosscheck (%)': f"{trade.volume_crosscheck_percent:+.1f}%",
                    'Liquidity Crosscheck (%)': f"{trade.liquidity_crosscheck_percent:+.1f}%",
                    'Jupiter Organic Score': f"{trade.jupiter_organic_score:.2f}",
                    'Data Provider': trade.data_provider,
                    'Discovery Source': trade.discovery_source,
                    'Price Frozen': 'Yes' if trade.price_frozen else 'No',
                    'Failed Updates Count': trade.consecutive_failed_updates,
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
