"""
Token Performance Tracker - Learn from historical token performance.

Tracks which tokens have been traded before and their win/loss records.
Can be used for:
- Blacklisting tokens with poor historical performance
- Whitelisting tokens with good historical performance
- Avoiding repeat trades on known losers

IMPORTANT: This is INFRASTRUCTURE ONLY - disabled by default.
Enable via .env when ready to use the data.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import json
import os
from ..monitoring.logger import get_logger

logger = get_logger(__name__)


@dataclass
class TokenPerformance:
    """Performance statistics for a single token."""
    token_address: str
    symbol: str = ''

    # Trade statistics
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0

    # Financial statistics
    total_pnl: float = 0.0
    total_pnl_percent: float = 0.0
    avg_pnl: float = 0.0
    avg_pnl_percent: float = 0.0
    best_pnl_percent: float = 0.0
    worst_pnl_percent: float = 0.0

    # Timestamps
    first_trade_time: datetime = None
    last_trade_time: datetime = None

    # Computed metrics
    @property
    def win_rate(self) -> float:
        """Calculate win rate percentage."""
        if self.total_trades == 0:
            return 0.0
        return (self.winning_trades / self.total_trades) * 100

    @property
    def is_consistent_loser(self) -> bool:
        """Check if token is consistently losing (3+ trades, 0% win rate)."""
        return self.total_trades >= 3 and self.win_rate == 0.0

    @property
    def is_repeat_winner(self) -> bool:
        """Check if token has good track record (3+ trades, 60%+ win rate)."""
        return self.total_trades >= 3 and self.win_rate >= 60.0


class TokenPerformanceTracker:
    """
    Track token performance history for learning and filtering.

    Usage:
        # After each trade closes, update tracker
        tracker.record_trade(token_address, pnl, pnl_percent, symbol)

        # Check if token should be avoided
        if tracker.should_avoid_token(token_address):
            skip_token()

        # Check if token is a good repeat
        if tracker.is_repeat_winner(token_address):
            prioritize_token()
    """

    def __init__(self, data_file: str = 'data/token_performance.json'):
        """
        Initialize token performance tracker.

        Args:
            data_file: Path to JSON file for persistent storage
        """
        self.data_file = data_file
        self.tokens: Dict[str, TokenPerformance] = {}

        # Load existing data
        self.load_data()

        logger.info(f"📊 Token Performance Tracker initialized with {len(self.tokens)} tracked tokens")

    def record_trade(
        self,
        token_address: str,
        pnl: float,
        pnl_percent: float,
        symbol: str = '',
        timestamp: datetime = None
    ):
        """
        Record a completed trade for a token.

        Args:
            token_address: Token contract address
            pnl: Profit/loss in USD
            pnl_percent: Profit/loss percentage
            symbol: Token symbol (optional)
            timestamp: Trade timestamp (defaults to now)
        """
        if timestamp is None:
            timestamp = datetime.now()

        # Get or create token performance record
        if token_address not in self.tokens:
            self.tokens[token_address] = TokenPerformance(
                token_address=token_address,
                symbol=symbol,
                first_trade_time=timestamp
            )

        perf = self.tokens[token_address]

        # Update symbol if provided
        if symbol and not perf.symbol:
            perf.symbol = symbol

        # Update trade count
        perf.total_trades += 1
        if pnl > 0:
            perf.winning_trades += 1
        else:
            perf.losing_trades += 1

        # Update PnL statistics
        perf.total_pnl += pnl
        perf.total_pnl_percent += pnl_percent
        perf.avg_pnl = perf.total_pnl / perf.total_trades
        perf.avg_pnl_percent = perf.total_pnl_percent / perf.total_trades

        # Update best/worst
        if pnl_percent > perf.best_pnl_percent:
            perf.best_pnl_percent = pnl_percent
        if pnl_percent < perf.worst_pnl_percent:
            perf.worst_pnl_percent = pnl_percent

        # Update timestamps
        perf.last_trade_time = timestamp

        # Log significant patterns
        if perf.is_consistent_loser:
            logger.warning(
                f"⚠️  CONSISTENT LOSER DETECTED: {token_address[:8]}... ({perf.symbol}) - "
                f"{perf.total_trades} trades, {perf.win_rate:.0f}% win rate, "
                f"avg {perf.avg_pnl_percent:+.1f}% PnL"
            )
        elif perf.is_repeat_winner:
            logger.info(
                f"✅ REPEAT WINNER: {token_address[:8]}... ({perf.symbol}) - "
                f"{perf.total_trades} trades, {perf.win_rate:.0f}% win rate, "
                f"avg {perf.avg_pnl_percent:+.1f}% PnL"
            )

        # Save to disk
        self.save_data()

    def get_performance(self, token_address: str) -> Optional[TokenPerformance]:
        """
        Get performance statistics for a token.

        Args:
            token_address: Token contract address

        Returns:
            TokenPerformance object or None if never traded
        """
        return self.tokens.get(token_address)

    def should_avoid_token(
        self,
        token_address: str,
        min_trades: int = 3,
        max_win_rate: float = 0.0
    ) -> bool:
        """
        Check if token should be avoided based on historical performance.

        Args:
            token_address: Token contract address
            min_trades: Minimum trades required for decision (default 3)
            max_win_rate: Maximum win rate % to avoid (default 0 = only avoid 100% losers)

        Returns:
            True if token should be avoided
        """
        perf = self.get_performance(token_address)
        if not perf:
            return False  # No history, don't avoid

        # Need minimum trades to make a decision
        if perf.total_trades < min_trades:
            return False

        # Avoid if win rate is at or below threshold
        return perf.win_rate <= max_win_rate

    def is_repeat_winner(
        self,
        token_address: str,
        min_trades: int = 3,
        min_win_rate: float = 60.0
    ) -> bool:
        """
        Check if token is a repeat winner.

        Args:
            token_address: Token contract address
            min_trades: Minimum trades required for decision (default 3)
            min_win_rate: Minimum win rate % to qualify (default 60%)

        Returns:
            True if token is a repeat winner
        """
        perf = self.get_performance(token_address)
        if not perf:
            return False  # No history

        # Need minimum trades
        if perf.total_trades < min_trades:
            return False

        # Check if win rate meets threshold
        return perf.win_rate >= min_win_rate

    def get_worst_performers(self, limit: int = 10) -> List[TokenPerformance]:
        """
        Get worst performing tokens (by win rate, then avg PnL %).

        Args:
            limit: Number of tokens to return

        Returns:
            List of TokenPerformance objects
        """
        # Filter to tokens with at least 2 trades
        qualified = [p for p in self.tokens.values() if p.total_trades >= 2]

        # Sort by win rate (ascending), then avg PnL % (ascending)
        sorted_tokens = sorted(
            qualified,
            key=lambda p: (p.win_rate, p.avg_pnl_percent)
        )

        return sorted_tokens[:limit]

    def get_best_performers(self, limit: int = 10) -> List[TokenPerformance]:
        """
        Get best performing tokens (by win rate, then avg PnL %).

        Args:
            limit: Number of tokens to return

        Returns:
            List of TokenPerformance objects
        """
        # Filter to tokens with at least 2 trades
        qualified = [p for p in self.tokens.values() if p.total_trades >= 2]

        # Sort by win rate (descending), then avg PnL % (descending)
        sorted_tokens = sorted(
            qualified,
            key=lambda p: (-p.win_rate, -p.avg_pnl_percent)
        )

        return sorted_tokens[:limit]

    def get_statistics(self) -> Dict:
        """
        Get overall tracker statistics.

        Returns:
            Dictionary with summary statistics
        """
        total_tokens = len(self.tokens)
        tokens_with_multiple_trades = len([p for p in self.tokens.values() if p.total_trades >= 2])
        consistent_losers = len([p for p in self.tokens.values() if p.is_consistent_loser])
        repeat_winners = len([p for p in self.tokens.values() if p.is_repeat_winner])

        return {
            'total_tracked_tokens': total_tokens,
            'tokens_with_multiple_trades': tokens_with_multiple_trades,
            'consistent_losers': consistent_losers,
            'repeat_winners': repeat_winners
        }

    def save_data(self):
        """Save token performance data to JSON file."""
        try:
            # Create data directory if needed
            os.makedirs(os.path.dirname(self.data_file), exist_ok=True)

            # Convert to serializable format
            data = {}
            for token_addr, perf in self.tokens.items():
                data[token_addr] = {
                    'token_address': perf.token_address,
                    'symbol': perf.symbol,
                    'total_trades': perf.total_trades,
                    'winning_trades': perf.winning_trades,
                    'losing_trades': perf.losing_trades,
                    'total_pnl': perf.total_pnl,
                    'total_pnl_percent': perf.total_pnl_percent,
                    'avg_pnl': perf.avg_pnl,
                    'avg_pnl_percent': perf.avg_pnl_percent,
                    'best_pnl_percent': perf.best_pnl_percent,
                    'worst_pnl_percent': perf.worst_pnl_percent,
                    'first_trade_time': perf.first_trade_time.isoformat() if perf.first_trade_time else None,
                    'last_trade_time': perf.last_trade_time.isoformat() if perf.last_trade_time else None
                }

            # Write to file
            with open(self.data_file, 'w') as f:
                json.dump(data, f, indent=2)

            logger.debug(f"💾 Token performance data saved: {len(data)} tokens → {self.data_file}")

        except Exception as e:
            logger.error(f"❌ Error saving token performance data: {e}", exc_info=True)

    def load_data(self):
        """Load token performance data from JSON file."""
        try:
            if not os.path.exists(self.data_file):
                logger.info(f"📝 No existing token performance data at {self.data_file}")
                return

            with open(self.data_file, 'r') as f:
                data = json.load(f)

            # Convert from JSON format
            for token_addr, perf_data in data.items():
                self.tokens[token_addr] = TokenPerformance(
                    token_address=perf_data['token_address'],
                    symbol=perf_data.get('symbol', ''),
                    total_trades=perf_data['total_trades'],
                    winning_trades=perf_data['winning_trades'],
                    losing_trades=perf_data['losing_trades'],
                    total_pnl=perf_data['total_pnl'],
                    total_pnl_percent=perf_data['total_pnl_percent'],
                    avg_pnl=perf_data['avg_pnl'],
                    avg_pnl_percent=perf_data['avg_pnl_percent'],
                    best_pnl_percent=perf_data['best_pnl_percent'],
                    worst_pnl_percent=perf_data['worst_pnl_percent'],
                    first_trade_time=datetime.fromisoformat(perf_data['first_trade_time']) if perf_data.get('first_trade_time') else None,
                    last_trade_time=datetime.fromisoformat(perf_data['last_trade_time']) if perf_data.get('last_trade_time') else None
                )

            logger.info(f"✅ Loaded token performance data: {len(self.tokens)} tokens from {self.data_file}")

        except Exception as e:
            logger.error(f"❌ Error loading token performance data: {e}", exc_info=True)
            logger.warning("⚠️  Starting with empty token tracker")
