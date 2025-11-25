"""
ML Data Collection System
Captures comprehensive trade data for future machine learning training.
"""

from typing import Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass, asdict, field
import json
import csv
import os
from ..monitoring.logger import get_logger

logger = get_logger(__name__)


@dataclass
class MLTradeRecord:
    """
    Comprehensive trade record for ML training.
    Captures everything needed to learn from trades.
    """
    # === IDENTIFIERS ===
    trade_id: str  # Unique trade ID
    token_address: str
    token_symbol: str

    # === TRADE BASICS ===
    action: str  # 'buy' or 'sell'
    entry_time: datetime
    exit_time: Optional[datetime] = None
    hold_duration_minutes: float = 0.0

    # === PRICES ===
    entry_price: float = 0.0
    exit_price: float = 0.0
    highest_price_reached: float = 0.0  # Peak during hold
    lowest_price_reached: float = 0.0   # Bottom during hold

    # === POSITION SIZE ===
    amount_usd: float = 0.0
    quantity: float = 0.0
    position_size_percent_of_portfolio: float = 0.0

    # === OUTCOME ===
    pnl_usd: float = 0.0
    pnl_percent: float = 0.0
    win: bool = False  # True if profitable
    exit_reason: str = ''  # 'trailing_stop', 'stop_loss', 'manual', 'rugged', 'partial_profit'

    # === MARKET CONDITIONS AT ENTRY ===
    entry_liquidity_usd: float = 0.0
    entry_volume_24h: float = 0.0
    entry_price_change_24h: float = 0.0
    entry_holder_count: int = 0
    entry_market_cap: float = 0.0

    # === MARKET CONDITIONS AT EXIT ===
    exit_liquidity_usd: float = 0.0
    exit_volume_24h: float = 0.0
    exit_price_change_24h: float = 0.0

    # === TOKEN CHARACTERISTICS ===
    token_age_hours: float = 0.0
    is_mintable: bool = False
    has_freeze_authority: bool = False
    is_verified: bool = False
    ownership_renounced: bool = False

    # === RISK SCORES (0-1) ===
    overall_risk_score: float = 0.0
    liquidity_risk: float = 0.0
    security_risk: float = 0.0
    volatility_risk: float = 0.0
    sentiment_risk: float = 0.0
    age_risk: float = 0.0

    # === SIGNALS & PREDICTIONS ===
    sentiment_score: float = 0.5  # 0-1
    sentiment_confidence: float = 0.0
    coordination_risk: float = 0.0
    price_prediction_direction: str = ''  # 'up', 'down', 'sideways'
    price_prediction_confidence: float = 0.0
    predicted_change_percent: float = 0.0

    # === TECHNICAL INDICATORS ===
    volume_trend: str = ''  # 'increasing', 'decreasing', 'stable'
    price_pattern: str = ''  # 'uptrend', 'downtrend', 'sideways'

    # === PORTFOLIO CONTEXT ===
    portfolio_value_at_entry: float = 0.0
    open_positions_count: int = 0
    daily_trades_before_this: int = 0

    # === EXECUTION DETAILS ===
    slippage_percent: float = 0.0
    total_fees_usd: float = 0.0
    execution_method: str = 'jupiter'  # 'jupiter', 'gmgn', 'manual'

    # === TRAILING STOP DATA ===
    used_trailing_stop: bool = True
    trailing_stop_percent: float = 15.0
    max_drawdown_from_peak_percent: float = 0.0  # How far it dropped from peak before exit

    # === PARTIAL PROFIT DATA ===
    is_partial_sell: bool = False
    milestones_hit: List[int] = field(default_factory=list)  # [100, 200, 300, ...]
    partial_sell_count: int = 0

    # === METADATA ===
    bot_version: str = '1.0'
    paper_trading: bool = True
    notes: str = ''


class MLDataCollector:
    """Collects and stores comprehensive trade data for ML training."""

    def __init__(self, data_dir: str = 'data/ml_training'):
        """
        Initialize ML data collector.

        Args:
            data_dir: Directory to store ML training data
        """
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)

        self.trades_file = os.path.join(data_dir, 'ml_trades.jsonl')
        self.csv_file = os.path.join(data_dir, 'ml_trades.csv')

        logger.info(f"📊 ML Data Collector initialized: {data_dir}")

    def record_trade(self, trade: MLTradeRecord):
        """
        Record a trade for ML training.

        Args:
            trade: MLTradeRecord with comprehensive trade data
        """
        try:
            # Save as JSON Lines (one JSON object per line - easy for ML frameworks)
            with open(self.trades_file, 'a') as f:
                trade_dict = asdict(trade)
                # Convert datetime objects to ISO format
                for key, value in trade_dict.items():
                    if isinstance(value, datetime):
                        trade_dict[key] = value.isoformat() if value else None
                f.write(json.dumps(trade_dict) + '\n')

            # Also save to CSV for easy Excel analysis
            self._append_to_csv(trade)

            logger.debug(f"📊 ML trade recorded: {trade.token_symbol} {trade.pnl_percent:+.2f}%")

        except Exception as e:
            logger.error(f"❌ Error recording ML trade: {e}", exc_info=True)

    def _append_to_csv(self, trade: MLTradeRecord):
        """Append trade to CSV file."""
        trade_dict = asdict(trade)

        # Convert datetime to string
        for key, value in trade_dict.items():
            if isinstance(value, datetime):
                trade_dict[key] = value.isoformat() if value else ''
            elif isinstance(value, list):
                trade_dict[key] = ','.join(map(str, value))

        file_exists = os.path.exists(self.csv_file)

        with open(self.csv_file, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=trade_dict.keys())
            if not file_exists:
                writer.writeheader()
            writer.writerow(trade_dict)

    def load_all_trades(self) -> List[MLTradeRecord]:
        """
        Load all recorded trades for analysis.

        Returns:
            List of MLTradeRecord objects
        """
        trades = []

        if not os.path.exists(self.trades_file):
            return trades

        try:
            with open(self.trades_file, 'r') as f:
                for line in f:
                    trade_dict = json.loads(line)
                    # Convert ISO strings back to datetime
                    for key, value in trade_dict.items():
                        if key.endswith('_time') and value:
                            trade_dict[key] = datetime.fromisoformat(value)
                    trades.append(MLTradeRecord(**trade_dict))

            logger.info(f"📊 Loaded {len(trades)} ML training records")
            return trades

        except Exception as e:
            logger.error(f"❌ Error loading ML trades: {e}", exc_info=True)
            return []

    def get_statistics(self) -> Dict:
        """
        Get statistics about collected data.

        Returns:
            Statistics dictionary
        """
        trades = self.load_all_trades()

        if not trades:
            return {
                'total_trades': 0,
                'ready_for_ml': False,
                'message': 'No trades recorded yet'
            }

        winning_trades = [t for t in trades if t.win]
        losing_trades = [t for t in trades if not t.win]

        stats = {
            'total_trades': len(trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': len(winning_trades) / len(trades) if trades else 0,
            'avg_hold_duration_hours': sum(t.hold_duration_minutes for t in trades) / len(trades) / 60 if trades else 0,
            'total_data_points': len(trades),
            'ready_for_ml': len(trades) >= 100,
            'recommended_min_trades': 100,
            'data_quality_score': self._assess_data_quality(trades)
        }

        if len(trades) < 100:
            stats['message'] = f"Need {100 - len(trades)} more trades for ML training (current: {len(trades)})"
        else:
            stats['message'] = f"✅ Ready for ML training! ({len(trades)} trades collected)"

        return stats

    def _assess_data_quality(self, trades: List[MLTradeRecord]) -> float:
        """
        Assess quality of collected data (0-1 score).

        Args:
            trades: List of trade records

        Returns:
            Quality score 0-1
        """
        if not trades:
            return 0.0

        # Check completeness of key fields
        quality_checks = []

        for trade in trades[:100]:  # Sample first 100
            fields_filled = 0
            critical_fields = [
                trade.entry_liquidity_usd > 0,
                trade.sentiment_score > 0,
                trade.overall_risk_score > 0,
                trade.token_age_hours > 0,
                bool(trade.exit_reason),
                trade.highest_price_reached > 0
            ]
            fields_filled = sum(critical_fields)
            quality_checks.append(fields_filled / len(critical_fields))

        return sum(quality_checks) / len(quality_checks) if quality_checks else 0.0

    def export_for_ml_framework(self, output_file: str = None):
        """
        Export data in format ready for ML frameworks (Python/scikit-learn/TensorFlow).

        Args:
            output_file: Output file path (default: data/ml_training/ml_ready.json)
        """
        if not output_file:
            output_file = os.path.join(self.data_dir, 'ml_ready.json')

        trades = self.load_all_trades()

        if len(trades) < 50:
            logger.warning(f"⚠️ Only {len(trades)} trades - need 100+ for good ML training")

        # Structure data for ML
        ml_data = {
            'metadata': {
                'total_trades': len(trades),
                'date_exported': datetime.now().isoformat(),
                'data_quality': self._assess_data_quality(trades),
                'win_rate': sum(1 for t in trades if t.win) / len(trades) if trades else 0
            },
            'features': [
                # List of feature names for ML
                'entry_liquidity_usd', 'entry_volume_24h', 'token_age_hours',
                'overall_risk_score', 'liquidity_risk', 'security_risk', 'volatility_risk',
                'sentiment_score', 'sentiment_confidence', 'coordination_risk',
                'price_prediction_confidence', 'predicted_change_percent',
                'position_size_percent_of_portfolio', 'open_positions_count'
            ],
            'target': 'win',  # What we're trying to predict
            'trades': [asdict(t) for t in trades]
        }

        with open(output_file, 'w') as f:
            json.dump(ml_data, f, indent=2, default=str)

        logger.info(f"✅ ML data exported: {output_file} ({len(trades)} trades)")
        return output_file
