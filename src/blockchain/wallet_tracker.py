import logging
from typing import List, Dict, Set
from datetime import datetime, timedelta

class WalletTracker:
    """Track smart money wallets and their activities"""

    def __init__(self):
        self.logger = logging.getLogger('trading_bot.wallet_tracker')
        self.tracked_wallets: Set[str] = set()
        self.wallet_activities: Dict[str, List[Dict]] = {}
        self.smart_money_threshold = 0.7  # 70% win rate

    def add_wallet(self, wallet_address: str):
        """Add wallet to tracking list"""
        self.tracked_wallets.add(wallet_address)
        if wallet_address not in self.wallet_activities:
            self.wallet_activities[wallet_address] = []
        self.logger.info(f"Now tracking wallet: {wallet_address[:8]}...")

    def record_activity(self, wallet_address: str, activity: Dict):
        """Record wallet activity"""
        if wallet_address not in self.wallet_activities:
            self.wallet_activities[wallet_address] = []

        activity['timestamp'] = datetime.now()
        self.wallet_activities[wallet_address].append(activity)

    def is_smart_money(self, wallet_address: str) -> bool:
        """Determine if wallet is smart money based on history"""
        if wallet_address not in self.wallet_activities:
            return False

        activities = self.wallet_activities[wallet_address]
        if len(activities) < 5:  # Need at least 5 trades to evaluate
            return False

        profitable = sum(1 for a in activities if a.get('profit', 0) > 0)
        win_rate = profitable / len(activities)

        return win_rate >= self.smart_money_threshold

    def get_wallet_stats(self, wallet_address: str) -> Dict:
        """Get statistics for a wallet"""
        if wallet_address not in self.wallet_activities:
            return {}

        activities = self.wallet_activities[wallet_address]
        total_trades = len(activities)
        profitable_trades = sum(1 for a in activities if a.get('profit', 0) > 0)

        return {
            'total_trades': total_trades,
            'profitable_trades': profitable_trades,
            'win_rate': profitable_trades / total_trades if total_trades > 0 else 0,
            'is_smart_money': self.is_smart_money(wallet_address)
        }
