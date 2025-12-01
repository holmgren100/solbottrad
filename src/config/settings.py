"""
Configuration management for the trading bot.
Loads settings from environment variables and provides validation.
"""

import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@dataclass
class TradingConfig:
    """Trading-specific configuration."""
    max_position_size: float
    min_liquidity_usd: float
    min_volume_24h: float
    max_slippage_percent: float
    min_confidence_score: float
    paper_trading_mode: bool
    priority_fee: float


@dataclass
class RiskConfig:
    """Risk management configuration."""
    max_portfolio_risk_percent: float
    stop_loss_percent: float
    take_profit_percent: float
    max_daily_trades: int
    max_open_positions: int


@dataclass
class APIConfig:
    """API credentials configuration."""
    alchemy_api_key: str
    solsniffer_api_key: Optional[str]
    dexscreener_api_key: Optional[str]
    twitter_bearer_token: Optional[str]
    telegram_bot_token: str
    telegram_chat_id: str
    gmgn_telegram_bot: str


class Settings:
    """Central configuration class for the trading bot."""

    def __init__(self):
        """Initialize settings from environment variables."""
        self.trading = TradingConfig(
            max_position_size=float(os.getenv('MAX_POSITION_SIZE', '100')),
            min_liquidity_usd=float(os.getenv('MIN_ENTRY_LIQUIDITY', '40000')),
            min_volume_24h=float(os.getenv('MIN_24H_VOLUME', '20000')),
            max_slippage_percent=float(os.getenv('MAX_SLIPPAGE_PERCENT', '5')),
            min_confidence_score=float(os.getenv('MIN_CONFIDENCE_SCORE', '0.7')),
            paper_trading_mode=os.getenv('PAPER_TRADING_MODE', 'true').lower() == 'true',
            priority_fee=float(os.getenv('PRIORITY_FEE', '0.001'))
        )

        self.risk = RiskConfig(
            max_portfolio_risk_percent=float(os.getenv('MAX_PORTFOLIO_RISK_PERCENT', '10')),
            stop_loss_percent=float(os.getenv('STOP_LOSS_PERCENT', '20')),
            take_profit_percent=float(os.getenv('TAKE_PROFIT_PERCENT', '50')),
            max_daily_trades=int(os.getenv('MAX_DAILY_TRADES', '10')),
            max_open_positions=int(os.getenv('MAX_OPEN_POSITIONS', '5'))
        )

        self.api = APIConfig(
            alchemy_api_key=os.getenv('ALCHEMY_API_KEY', ''),
            solsniffer_api_key=os.getenv('SOLSNIFFER_API_KEY'),
            dexscreener_api_key=os.getenv('DEXSCREENER_API_KEY'),
            twitter_bearer_token=os.getenv('TWITTER_BEARER_TOKEN'),
            telegram_bot_token=os.getenv('TELEGRAM_BOT_TOKEN', ''),
            telegram_chat_id=os.getenv('TELEGRAM_CHAT_ID', ''),
            gmgn_telegram_bot=os.getenv('GMGN_TELEGRAM_BOT', '@gmgnsolbot')
        )

        # Monitoring settings
        self.log_level = os.getenv('LOG_LEVEL', 'INFO')
        self.log_file = os.getenv('LOG_FILE', 'trading_bot.log')

        # Validate critical settings
        self._validate()

    def _validate(self):
        """Validate that critical settings are properly configured."""
        errors = []

        if not self.api.alchemy_api_key:
            errors.append("ALCHEMY_API_KEY is required")

        if not self.api.telegram_bot_token:
            errors.append("TELEGRAM_BOT_TOKEN is required")

        if not self.api.telegram_chat_id:
            errors.append("TELEGRAM_CHAT_ID is required")

        if self.trading.max_position_size <= 0:
            errors.append("MAX_POSITION_SIZE must be positive")

        if self.trading.min_confidence_score < 0 or self.trading.min_confidence_score > 1:
            errors.append("MIN_CONFIDENCE_SCORE must be between 0 and 1")

        if errors:
            raise ValueError(f"Configuration errors:\n" + "\n".join(f"  - {e}" for e in errors))

    def is_paper_trading(self) -> bool:
        """Check if paper trading mode is enabled."""
        return self.trading.paper_trading_mode


# Global settings instance
settings = Settings()
