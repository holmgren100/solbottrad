"""
Wallet tracking system for monitoring "smart money" movements.
"""

import asyncio
from typing import Dict, List, Set, Callable, Awaitable, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from ..monitoring.logger import get_logger

logger = get_logger(__name__)


@dataclass
class WalletActivity:
    """Represents a wallet's trading activity."""
    address: str
    total_trades: int
    profitable_trades: int
    win_rate: float
    avg_profit_percent: float
    last_activity: datetime


@dataclass
class WalletTransaction:
    """Represents a wallet transaction."""
    wallet_address: str
    token_address: str
    action: str  # 'buy' or 'sell'
    amount: float
    price: float
    timestamp: datetime


class WalletTracker:
    """Tracks and analyzes wallet activities to identify smart money."""

    def __init__(self):
        """Initialize the wallet tracker."""
        self.tracked_wallets: Set[str] = set()
        self.wallet_activities: Dict[str, WalletActivity] = {}
        self.recent_transactions: List[WalletTransaction] = []
        self.callbacks: List[Callable[[WalletTransaction], Awaitable[None]]] = []
        self._running = False

    def add_wallet(self, wallet_address: str):
        """
        Add a wallet to track.

        Args:
            wallet_address: Wallet address to track
        """
        self.tracked_wallets.add(wallet_address)
        logger.info(f"Now tracking wallet: {wallet_address}")

    def remove_wallet(self, wallet_address: str):
        """
        Remove a wallet from tracking.

        Args:
            wallet_address: Wallet address to stop tracking
        """
        self.tracked_wallets.discard(wallet_address)
        logger.info(f"Stopped tracking wallet: {wallet_address}")

    def register_callback(
        self,
        callback: Callable[[WalletTransaction], Awaitable[None]]
    ):
        """
        Register a callback for wallet transactions.

        Args:
            callback: Async function to call when transaction detected
        """
        self.callbacks.append(callback)

    async def record_transaction(
        self,
        wallet_address: str,
        token_address: str,
        action: str,
        amount: float,
        price: float
    ):
        """
        Record a wallet transaction.

        Args:
            wallet_address: Wallet address
            token_address: Token address
            action: 'buy' or 'sell'
            amount: Transaction amount
            price: Transaction price
        """
        transaction = WalletTransaction(
            wallet_address=wallet_address,
            token_address=token_address,
            action=action,
            amount=amount,
            price=price,
            timestamp=datetime.now()
        )

        self.recent_transactions.append(transaction)

        # Keep only last 1000 transactions
        if len(self.recent_transactions) > 1000:
            self.recent_transactions = self.recent_transactions[-1000:]

        logger.debug(
            f"Recorded {action} transaction: {wallet_address[:8]}... "
            f"for token {token_address[:8]}..."
        )

        # Notify callbacks
        for callback in self.callbacks:
            try:
                await callback(transaction)
            except Exception as e:
                logger.error(f"Error in wallet tracker callback: {e}")

    def get_wallet_activity(self, wallet_address: str) -> Optional[WalletActivity]:
        """
        Get activity summary for a wallet.

        Args:
            wallet_address: Wallet address

        Returns:
            WalletActivity or None if not tracked
        """
        return self.wallet_activities.get(wallet_address)

    def get_top_performers(self, limit: int = 10) -> List[WalletActivity]:
        """
        Get top performing wallets by win rate.

        Args:
            limit: Maximum number of wallets to return

        Returns:
            List of top performing wallet activities
        """
        activities = sorted(
            self.wallet_activities.values(),
            key=lambda x: (x.win_rate, x.total_trades),
            reverse=True
        )
        return activities[:limit]

    def get_recent_wallet_transactions(
        self,
        wallet_address: str,
        hours: int = 24
    ) -> List[WalletTransaction]:
        """
        Get recent transactions for a specific wallet.

        Args:
            wallet_address: Wallet address
            hours: Number of hours to look back

        Returns:
            List of recent transactions
        """
        cutoff = datetime.now() - timedelta(hours=hours)
        return [
            tx for tx in self.recent_transactions
            if tx.wallet_address == wallet_address and tx.timestamp > cutoff
        ]

    def get_token_transactions(
        self,
        token_address: str,
        hours: int = 24
    ) -> List[WalletTransaction]:
        """
        Get recent transactions for a specific token.

        Args:
            token_address: Token address
            hours: Number of hours to look back

        Returns:
            List of recent transactions
        """
        cutoff = datetime.now() - timedelta(hours=hours)
        return [
            tx for tx in self.recent_transactions
            if tx.token_address == token_address and tx.timestamp > cutoff
        ]

    def analyze_token_sentiment(self, token_address: str) -> Dict:
        """
        Analyze smart money sentiment for a token.

        Args:
            token_address: Token address

        Returns:
            Dictionary with buy/sell counts and sentiment score
        """
        transactions = self.get_token_transactions(token_address, hours=24)

        buy_count = sum(1 for tx in transactions if tx.action == 'buy')
        sell_count = sum(1 for tx in transactions if tx.action == 'sell')

        total = buy_count + sell_count
        if total == 0:
            sentiment_score = 0.5
        else:
            sentiment_score = buy_count / total

        return {
            'token_address': token_address,
            'buy_count': buy_count,
            'sell_count': sell_count,
            'sentiment_score': sentiment_score,
            'signal': self._get_sentiment_signal(sentiment_score)
        }

    def _get_sentiment_signal(self, score: float) -> str:
        """
        Convert sentiment score to signal.

        Args:
            score: Sentiment score (0-1)

        Returns:
            'bullish', 'bearish', or 'neutral'
        """
        if score >= 0.7:
            return 'bullish'
        elif score <= 0.3:
            return 'bearish'
        else:
            return 'neutral'

    def get_statistics(self) -> Dict:
        """
        Get tracker statistics.

        Returns:
            Dictionary with tracker statistics
        """
        return {
            'tracked_wallets': len(self.tracked_wallets),
            'total_transactions': len(self.recent_transactions),
            'active_wallets': len(self.wallet_activities),
            'top_performers': len([
                a for a in self.wallet_activities.values()
                if a.win_rate > 0.6
            ])
        }

    async def health_check(self) -> bool:
        """
        Health check for wallet tracker.

        Returns:
            True if healthy
        """
        return True  # Wallet tracker is always healthy if initialized
