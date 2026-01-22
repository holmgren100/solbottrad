"""
Solana Trading Bot v2.0 - Main Entry Point

Simple binary decision logic:
- TIER 1 Safety Checks → TIER 2 Performance Checks → TRADE or REJECT
- NO age-based logic
- NO complex scoring systems
- Clean, readable, well-logged

Based on strategy achieving 71.4% win rate (November 2024 version)
"""

import logging
import sys
import yaml
from pathlib import Path
from typing import Dict, List
from datetime import datetime

from src.decision_engine import DecisionEngine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(f'logs/bot_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    ]
)

logger = logging.getLogger(__name__)


class SolanaTradinBot:
    """
    Solana Trading Bot v2.0

    Strategy:
    - TIER 1: Safety filters (price, liquidity, security, verification)
    - TIER 2: Performance filters (V/L ratio, tokens/$, top holder %)
    - Binary decision: ALL pass → TRADE, ANY fail → REJECT
    """

    def __init__(self, config_path: str = "config/settings.yaml"):
        """
        Initialize the trading bot with configuration.

        Args:
            config_path: Path to YAML configuration file
        """
        logger.info("="*80)
        logger.info("Initializing Solana Trading Bot v2.0")
        logger.info("="*80)

        # Load configuration
        self.config = self._load_config(config_path)

        # Initialize decision engine
        self.decision_engine = DecisionEngine(self.config)

        # Statistics
        self.stats = {
            'tokens_evaluated': 0,
            'trades_approved': 0,
            'trades_rejected': 0,
            'tier1_rejections': 0,
            'tier2_rejections': 0,
        }

        logger.info("Bot initialized successfully")
        logger.info(f"Configuration: {self.decision_engine.get_summary_stats()}\n")

    def _load_config(self, config_path: str) -> Dict:
        """
        Load configuration from YAML file.

        Args:
            config_path: Path to configuration file

        Returns:
            Configuration dictionary
        """
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            logger.info(f"Loaded configuration from {config_path}")
            return config
        except FileNotFoundError:
            logger.warning(f"Config file not found: {config_path}, using defaults")
            return self._get_default_config()
        except Exception as e:
            logger.error(f"Error loading config: {e}, using defaults")
            return self._get_default_config()

    def _get_default_config(self) -> Dict:
        """
        Get default configuration matching the strategy document.

        Returns:
            Default configuration dictionary
        """
        return {
            'tier1': {
                'min_price': 0.10,
                'max_price': 1.0,
                'min_liquidity': 50000,
                'min_security_score': 80,
            },
            'tier2': {
                'min_volume_liquidity_ratio': 0.3,
                'max_volume_liquidity_ratio': 0.8,
                'max_tokens_per_dollar': 10000,
                'max_top_holder_percent': 20,
            },
            'position': {
                'entry_size': 0.1,
                'take_profit_percent': 15,
                'stop_loss_percent': 8,
                'max_hold_hours': 4,
            },
        }

    def evaluate_token(self, token_data: Dict) -> bool:
        """
        Evaluate a single token and make trade decision.

        Args:
            token_data: Dictionary containing token information

        Returns:
            True if approved for trading, False if rejected
        """
        self.stats['tokens_evaluated'] += 1

        should_trade, decision_details = self.decision_engine.evaluate_token(token_data)

        if should_trade:
            self.stats['trades_approved'] += 1
            self._log_trade_approval(decision_details)
        else:
            self.stats['trades_rejected'] += 1
            if not decision_details['tier1_passed']:
                self.stats['tier1_rejections'] += 1
            else:
                self.stats['tier2_rejections'] += 1
            self._log_trade_rejection(decision_details)

        return should_trade

    def _log_trade_approval(self, decision_details: Dict):
        """Log details of approved trade."""
        symbol = decision_details['symbol']
        params = decision_details['position_params']

        logger.info(f"✅ TRADE APPROVED: {symbol}")
        logger.info(f"   Position: {params['entry_size_sol']} SOL @ {params['entry_price']:.6f}")
        logger.info(f"   TP/SL: +{params['take_profit_percent']}% / -{params['stop_loss_percent']}%")

    def _log_trade_rejection(self, decision_details: Dict):
        """Log details of rejected trade."""
        symbol = decision_details['symbol']
        reason = decision_details['rejection_reason']

        logger.info(f"❌ TRADE REJECTED: {symbol}")
        logger.info(f"   Reason: {reason}")

    def get_statistics(self) -> Dict:
        """
        Get bot statistics.

        Returns:
            Dictionary containing statistics
        """
        if self.stats['tokens_evaluated'] > 0:
            approval_rate = (self.stats['trades_approved'] / self.stats['tokens_evaluated']) * 100
        else:
            approval_rate = 0

        return {
            **self.stats,
            'approval_rate': f"{approval_rate:.1f}%",
        }

    def print_statistics(self):
        """Print bot statistics to console."""
        stats = self.get_statistics()

        logger.info("\n" + "="*80)
        logger.info("BOT STATISTICS")
        logger.info("="*80)
        logger.info(f"Tokens Evaluated:    {stats['tokens_evaluated']}")
        logger.info(f"Trades Approved:     {stats['trades_approved']}")
        logger.info(f"Trades Rejected:     {stats['trades_rejected']}")
        logger.info(f"  - TIER 1 Failures: {stats['tier1_rejections']}")
        logger.info(f"  - TIER 2 Failures: {stats['tier2_rejections']}")
        logger.info(f"Approval Rate:       {stats['approval_rate']}")
        logger.info("="*80 + "\n")


def main():
    """Main entry point for the bot."""
    # Create logs directory if it doesn't exist
    Path("logs").mkdir(exist_ok=True)

    # Initialize bot
    bot = SolanaTradinBot()

    # Example: Evaluate sample tokens
    # In production, this would connect to Solana blockchain/API
    sample_tokens = [
        {
            'symbol': 'TEST1',
            'address': '0x123...',
            'price': 0.15,
            'liquidity': 75000,
            'security_score': 85,
            'contract_verified': True,
            'volume_24h': 40000,
            'sol_price_usd': 100,
            'top_holder_percent': 15,
        },
        {
            'symbol': 'TEST2',
            'address': '0x456...',
            'price': 0.05,  # Too low
            'liquidity': 60000,
            'security_score': 90,
            'contract_verified': True,
            'volume_24h': 30000,
            'sol_price_usd': 100,
            'top_holder_percent': 18,
        },
        {
            'symbol': 'TEST3',
            'address': '0x789...',
            'price': 0.25,
            'liquidity': 100000,
            'security_score': 82,
            'contract_verified': True,
            'volume_24h': 20000,  # V/L ratio too low (0.2)
            'sol_price_usd': 100,
            'top_holder_percent': 12,
        },
    ]

    logger.info("Starting token evaluation...")
    for token in sample_tokens:
        bot.evaluate_token(token)

    # Print final statistics
    bot.print_statistics()


if __name__ == "__main__":
    main()
