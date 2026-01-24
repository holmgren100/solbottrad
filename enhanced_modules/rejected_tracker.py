"""
Rejected Trades Tracker - Learn from what you're missing!

Tracks all tokens that passed initial discovery but were rejected
during screening. This data helps identify:
- Patterns in rejected tokens that actually performed well
- Filter thresholds that might be too strict
- Opportunities being missed
- Which rejection reasons are most common

Usage:
    tracker = RejectedTracker()
    tracker.record_rejection(
        token_address="...",
        symbol="TOKEN",
        rejection_reason="top10_concentration_too_high",
        token_data={...}  # All the data we collected
    )
"""

import csv
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class RejectedToken:
    """Data structure for rejected token tracking."""

    # Timestamp
    timestamp: str = ''

    # Token identification
    token_address: str = ''
    symbol: str = ''
    name: str = ''

    # Rejection info
    rejection_reason: str = ''
    rejection_stage: str = ''  # 'screening' or 'safety_filter'

    # Price & Liquidity
    price_usd: float = 0.0
    liquidity_usd: float = 0.0
    volume_24h: float = 0.0
    volume_1h: float = 0.0

    # Market data
    market_cap: float = 0.0
    fdv: float = 0.0

    # Price changes
    price_change_5m: float = 0.0
    price_change_1h: float = 0.0
    price_change_24h: float = 0.0

    # Transaction activity
    txns_24h: int = 0
    txns_1h: int = 0
    buys_24h: int = 0
    sells_24h: int = 0
    buys_1h: int = 0
    sells_1h: int = 0

    # Sentiment
    buy_ratio_24h: float = 0.0
    buy_ratio_1h: float = 0.0

    # Holder analysis
    holder_count: int = 0
    top1_concentration: float = 0.0
    top10_concentration: float = 0.0

    # Token safety
    lp_locked: bool = False
    lp_burned: bool = False
    lp_lock_days: int = 0
    lp_burned_percent: float = 0.0

    # Token info
    token_age_hours: float = 0.0
    token_age_minutes: float = 0.0    # For 5-30m timing analysis

    # Volume/Liquidity momentum
    vol_liq_ratio: float = 0.0        # volume_24h / liquidity

    # Entry momentum
    entry_price_change_5m: float = 0.0
    entry_price_change_1h: float = 0.0

    # Multi-source data validation
    birdeye_security_score: float = 0.0
    birdeye_trending_rank: int = 0
    coingecko_trending_score: float = 0.0
    has_freeze_authority: bool = False
    has_mint_authority: bool = False
    volume_crosscheck_percent: float = 0.0
    liquidity_crosscheck_percent: float = 0.0
    jupiter_organic_score: float = 0.0

    dex_platform: str = ''
    data_provider: str = ''
    discovery_source: str = ''

    # DEX info
    pair_address: str = ''
    labels: str = ''  # Comma-separated labels from DexScreener


class RejectedTracker:
    """Tracks all rejected tokens for analysis."""

    def __init__(self, export_path: str = 'data/rejected_trades.csv'):
        """
        Initialize rejected trades tracker.

        Args:
            export_path: Path to CSV export file
        """
        self.export_path = export_path

        # Ensure data directory exists
        Path(self.export_path).parent.mkdir(parents=True, exist_ok=True)

        # Initialize CSV file with headers if it doesn't exist
        if not Path(self.export_path).exists():
            self._initialize_csv()
            logger.info(f"✅ Rejected tracker initialized: {self.export_path}")
        else:
            logger.info(f"📊 Rejected tracker loaded: {self.export_path}")

    def _initialize_csv(self):
        """Create CSV file with headers."""
        with open(self.export_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                # Timestamp
                'Timestamp',

                # Token identification
                'Token Address', 'Symbol', 'Name',

                # Rejection info
                'Rejection Reason', 'Rejection Stage',

                # Price & Liquidity
                'Price (USD)', 'Liquidity (USD)', 'Volume 24h', 'Volume 1h',

                # Market data
                'Market Cap', 'FDV',

                # Price changes
                'Price Change 5m (%)', 'Price Change 1h (%)', 'Price Change 24h (%)',

                # Transaction activity
                'Txns 24h', 'Txns 1h', 'Buys 24h', 'Sells 24h', 'Buys 1h', 'Sells 1h',

                # Sentiment
                'Buy Ratio 24h', 'Buy Ratio 1h',

                # Holder analysis
                'Holder Count', 'Top 1 Concentration (%)', 'Top 10 Concentration (%)',

                # Token safety
                'LP Locked', 'LP Burned', 'LP Lock Days', 'LP Burned (%)',

                # Token info
                'Token Age (hours)', 'Token Age (minutes)',

                # Timing & Momentum Analysis
                'Vol/Liq Ratio', 'Entry Price Change 5m (%)', 'Entry Price Change 1h (%)',

                # Multi-Source Data Validation
                'Birdeye Security Score', 'Birdeye Trending Rank', 'CoinGecko Trending Score',
                'Has Freeze Authority', 'Has Mint Authority',
                'Volume Crosscheck (%)', 'Liquidity Crosscheck (%)',
                'Jupiter Organic Score',

                'DEX Platform', 'Data Provider', 'Discovery Source',

                # DEX info
                'Pair Address', 'Labels'
            ])
        logger.info(f"Created new rejected trades CSV: {self.export_path}")

    def record_rejection(
        self,
        token_address: str,
        rejection_reason: str,
        token_data: Dict,
        symbol: str = '',
        rejection_stage: str = 'screening'
    ):
        """
        Record a rejected token.

        Args:
            token_address: Token contract address
            rejection_reason: Why the token was rejected
            token_data: All token data collected during screening
            symbol: Token symbol (if available)
            rejection_stage: 'screening' or 'safety_filter'
        """
        try:
            # Create rejected token record
            rejected = RejectedToken(
                timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                token_address=token_address,
                symbol=symbol or token_data.get('symbol', ''),
                name=token_data.get('name', ''),
                rejection_reason=rejection_reason,
                rejection_stage=rejection_stage,

                # Price & Liquidity
                price_usd=token_data.get('price_usd', 0.0),
                liquidity_usd=token_data.get('liquidity_usd', 0.0),
                volume_24h=token_data.get('volume_24h', 0.0),
                volume_1h=token_data.get('volume_1h', 0.0),

                # Market data
                market_cap=token_data.get('market_cap', 0.0),
                fdv=token_data.get('fdv', 0.0),

                # Price changes
                price_change_5m=token_data.get('price_change_5m', 0.0),
                price_change_1h=token_data.get('price_change_1h', 0.0),
                price_change_24h=token_data.get('price_change_24h', 0.0),

                # Transaction activity
                txns_24h=token_data.get('txns_24h', 0),
                txns_1h=token_data.get('txns_1h', 0),
                buys_24h=token_data.get('buys_24h', 0),
                sells_24h=token_data.get('sells_24h', 0),
                buys_1h=token_data.get('buys_1h', 0),
                sells_1h=token_data.get('sells_1h', 0),

                # Sentiment
                buy_ratio_24h=token_data.get('buy_ratio_24h', 0.0),
                buy_ratio_1h=token_data.get('buy_ratio_1h', 0.0),

                # Holder analysis
                holder_count=token_data.get('holder_count', 0),
                top1_concentration=token_data.get('top1_concentration', 0.0),
                top10_concentration=token_data.get('top10_concentration', 0.0),

                # Token safety
                lp_locked=token_data.get('lp_locked', False),
                lp_burned=token_data.get('lp_burned', False),
                lp_lock_days=token_data.get('lp_lock_days', 0),
                lp_burned_percent=token_data.get('lp_burned_percent', 0.0),

                # Token info
                token_age_hours=token_data.get('token_age_hours', 0.0),
                token_age_minutes=token_data.get('token_age_hours', 0.0) * 60,  # Convert to minutes

                # Volume/Liquidity momentum
                vol_liq_ratio=(token_data.get('volume_24h', 0.0) / token_data.get('liquidity_usd', 1.0)
                              if token_data.get('liquidity_usd', 0) > 0 else 0),

                # Entry momentum
                entry_price_change_5m=token_data.get('price_change_5m', 0.0),
                entry_price_change_1h=token_data.get('price_change_1h', 0.0),

                dex_platform=token_data.get('dex_id', ''),
                data_provider=token_data.get('source', ''),

                # DEX info
                pair_address=token_data.get('pair_address', ''),
                labels=','.join(token_data.get('labels', []))
            )

            # Append to CSV
            with open(self.export_path, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    rejected.timestamp,
                    rejected.token_address,
                    rejected.symbol,
                    rejected.name,
                    rejected.rejection_reason,
                    rejected.rejection_stage,
                    f"${rejected.price_usd:.8f}",
                    f"${rejected.liquidity_usd:,.0f}",
                    f"${rejected.volume_24h:,.0f}",
                    f"${rejected.volume_1h:,.0f}",
                    f"${rejected.market_cap:,.0f}",
                    f"${rejected.fdv:,.0f}",
                    f"{rejected.price_change_5m:.2f}%",
                    f"{rejected.price_change_1h:.2f}%",
                    f"{rejected.price_change_24h:.2f}%",
                    rejected.txns_24h,
                    rejected.txns_1h,
                    rejected.buys_24h,
                    rejected.sells_24h,
                    rejected.buys_1h,
                    rejected.sells_1h,
                    f"{rejected.buy_ratio_24h:.1%}",
                    f"{rejected.buy_ratio_1h:.1%}",
                    rejected.holder_count,
                    f"{rejected.top1_concentration:.1f}%",
                    f"{rejected.top10_concentration:.1f}%",
                    'Yes' if rejected.lp_locked else 'No',
                    'Yes' if rejected.lp_burned else 'No',
                    rejected.lp_lock_days,
                    f"{rejected.lp_burned_percent:.1f}%",
                    f"{rejected.token_age_hours:.1f}",
                    f"{rejected.token_age_minutes:.1f}",
                    f"{rejected.vol_liq_ratio:.2f}x",
                    f"{rejected.entry_price_change_5m:+.2f}%",
                    f"{rejected.entry_price_change_1h:+.2f}%",
                    f"{rejected.birdeye_security_score:.2f}",
                    rejected.birdeye_trending_rank,
                    f"{rejected.coingecko_trending_score:.2f}",
                    'Yes' if rejected.has_freeze_authority else 'No',
                    'Yes' if rejected.has_mint_authority else 'No',
                    f"{rejected.volume_crosscheck_percent:+.1f}%",
                    f"{rejected.liquidity_crosscheck_percent:+.1f}%",
                    f"{rejected.jupiter_organic_score:.2f}",
                    rejected.dex_platform,
                    rejected.data_provider,
                    rejected.discovery_source,
                    rejected.pair_address,
                    rejected.labels
                ])

            logger.debug(
                f"📝 Rejected: {rejected.symbol} ({token_address[:8]}...) - "
                f"Reason: {rejection_reason}"
            )

        except Exception as e:
            logger.error(f"Error recording rejected token: {e}")
