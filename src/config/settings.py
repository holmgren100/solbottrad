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
    max_liquidity_usd: float           # Maximum entry liquidity (avoid crowded tokens)
    min_volume_24h: float
    # === OPTION B: ENHANCED TIER 2 FILTERS ===
    min_volume_liquidity_ratio: float  # Minimum volume/liquidity ratio (0.1 = 10% turnover)
    max_entry_price: float             # Maximum token price for entry
    min_tokens_per_dollar: float       # Minimum tokens per $1 (avoid too expensive)
    max_tokens_per_dollar: float       # Maximum tokens per $1 (avoid worthless)
    # === BATCH 9 OPTIMIZATIONS (Expected +30% win rate!) ===
    min_total_transactions: int        # Minimum total transactions (buys+sells) in 1h
    min_buy_sell_ratio: float          # Minimum buy/sell ratio (blocks dumping tokens)
    golden_liq_min: float              # Golden liquidity range minimum ($30k)
    golden_liq_max: float              # Golden liquidity range maximum ($50k)
    # === POSITION SIZING MULTIPLIERS (455-trade research) ===
    prefer_golden_range: bool          # Prioritize golden liquidity range
    golden_range_multiplier: float     # Position size multiplier for golden range
    preferred_price_max: float         # Preferred price maximum
    preferred_price_multiplier: float  # Position size multiplier for preferred price
    # === MOMENTUM FILTERS (Reduce no-momentum trades 50% → 30%) ===
    enable_momentum_filters: bool
    min_price_change_1h: float         # Minimum 1h price change
    min_price_change_5min: float       # Minimum 5min price change
    min_price_change_1min: float       # Minimum 1min price change
    max_price_change_1h: float         # Maximum 1h price change (avoid exhausted)
    min_volume_spike_ratio: float      # Minimum 1h volume / avg ratio
    min_buy_pressure_recent: float     # Minimum recent buy pressure %
    require_acceleration: bool         # Require accelerating momentum
    # === LP LOCK & RUG PREVENTION (Save $120-150 per 100 trades) ===
    enable_lp_lock_check: bool
    min_lp_lock_days: int
    allow_lp_burned: bool
    skip_unlocked_lp: bool
    # === HOLDER CONCENTRATION ===
    enable_holder_check: bool
    max_top_10_concentration: float    # Max % owned by top 10
    max_top_1_concentration: float     # Max % owned by top 1
    max_dev_wallet: float              # Max % owned by dev
    # === CONTRACT SAFETY ===
    block_mint_authority: bool
    block_freeze_authority: bool
    require_renounced: bool
    # === EXISTING CONFIG ===
    max_slippage_percent: float
    min_confidence_score: float
    paper_trading_mode: bool
    priority_fee: float
    rugcheck_strict_mode: bool
    rugcheck_min_score: int
    enable_volume_breakout: bool
    enable_whale_tracking: bool
    enable_movement_detection: bool


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
    rugcheck_api_key: Optional[str]
    solscan_api_key: Optional[str]
    birdeye_api_key: Optional[str]
    telegram_bot_token: str
    telegram_chat_id: str
    gmgn_telegram_bot: str


class Settings:
    """Central configuration class for the trading bot."""

    def __init__(self):
        """Initialize settings from environment variables."""
        self.trading = TradingConfig(
            max_position_size=float(os.getenv('MAX_POSITION_SIZE', '100')),
            # === TIER 2 FILTERS (OPTION B) ===
            min_liquidity_usd=float(os.getenv('MIN_ENTRY_LIQUIDITY', '30000')),
            max_liquidity_usd=float(os.getenv('MAX_ENTRY_LIQUIDITY', '100000')),
            min_volume_24h=float(os.getenv('MIN_24H_VOLUME', '20000')),
            min_volume_liquidity_ratio=float(os.getenv('MIN_VOLUME_LIQUIDITY_RATIO', '0.1')),
            max_entry_price=float(os.getenv('MAX_ENTRY_PRICE', '0.001')),
            min_tokens_per_dollar=float(os.getenv('MIN_TOKENS_PER_DOLLAR', '0.1')),
            max_tokens_per_dollar=float(os.getenv('MAX_TOKENS_PER_DOLLAR', '10000')),
            # === BATCH 9 OPTIMIZATIONS (Expected +30% win rate!) ===
            min_total_transactions=int(os.getenv('MIN_TOTAL_TRANSACTIONS', '1000')),
            min_buy_sell_ratio=float(os.getenv('MIN_BUY_SELL_RATIO', '0.8')),
            golden_liq_min=float(os.getenv('GOLDEN_LIQUIDITY_MIN', '30000')),
            golden_liq_max=float(os.getenv('GOLDEN_LIQUIDITY_MAX', '75000')),
            # === POSITION SIZING MULTIPLIERS (455-trade research) ===
            prefer_golden_range=os.getenv('PREFER_GOLDEN_RANGE', 'true').lower() == 'true',
            golden_range_multiplier=float(os.getenv('GOLDEN_RANGE_MULTIPLIER', '1.2')),
            preferred_price_max=float(os.getenv('PREFERRED_PRICE_MAX', '0.0005')),
            preferred_price_multiplier=float(os.getenv('PREFERRED_PRICE_MULTIPLIER', '1.3')),
            # === MOMENTUM FILTERS (Reduce no-momentum trades 50% → 30%) ===
            enable_momentum_filters=os.getenv('ENABLE_MOMENTUM_FILTERS', 'true').lower() == 'true',
            min_price_change_1h=float(os.getenv('MIN_PRICE_CHANGE_1H', '10')),
            min_price_change_5min=float(os.getenv('MIN_PRICE_CHANGE_5MIN', '3')),
            min_price_change_1min=float(os.getenv('MIN_PRICE_CHANGE_1MIN', '1')),
            max_price_change_1h=float(os.getenv('MAX_PRICE_CHANGE_1H', '50')),
            min_volume_spike_ratio=float(os.getenv('MIN_VOLUME_SPIKE_RATIO', '3.0')),
            min_buy_pressure_recent=float(os.getenv('MIN_BUY_PRESSURE_RECENT', '60')),
            require_acceleration=os.getenv('REQUIRE_ACCELERATION', 'true').lower() == 'true',
            # === LP LOCK & RUG PREVENTION (Save $120-150 per 100 trades) ===
            enable_lp_lock_check=os.getenv('ENABLE_LP_LOCK_CHECK', 'true').lower() == 'true',
            min_lp_lock_days=int(os.getenv('MIN_LP_LOCK_DAYS', '30')),
            allow_lp_burned=os.getenv('ALLOW_LP_BURNED', 'true').lower() == 'true',
            skip_unlocked_lp=os.getenv('SKIP_UNLOCKED_LP', 'true').lower() == 'true',
            # === HOLDER CONCENTRATION ===
            enable_holder_check=os.getenv('ENABLE_HOLDER_CHECK', 'true').lower() == 'true',
            max_top_10_concentration=float(os.getenv('MAX_TOP_10_CONCENTRATION', '50')),
            max_top_1_concentration=float(os.getenv('MAX_TOP_1_CONCENTRATION', '20')),
            max_dev_wallet=float(os.getenv('MAX_DEV_WALLET', '10')),
            # === CONTRACT SAFETY ===
            block_mint_authority=os.getenv('BLOCK_MINT_AUTHORITY', 'true').lower() == 'true',
            block_freeze_authority=os.getenv('BLOCK_FREEZE_AUTHORITY', 'true').lower() == 'true',
            require_renounced=os.getenv('REQUIRE_RENOUNCED', 'false').lower() == 'true',
            # === OTHER SETTINGS ===
            max_slippage_percent=float(os.getenv('MAX_SLIPPAGE_PERCENT', '5')),
            min_confidence_score=float(os.getenv('MIN_CONFIDENCE_SCORE', '0.4')),
            paper_trading_mode=os.getenv('PAPER_TRADING_MODE', 'true').lower() == 'true',
            priority_fee=float(os.getenv('PRIORITY_FEE', '0.001')),
            rugcheck_strict_mode=os.getenv('RUGCHECK_STRICT_MODE', 'true').lower() == 'true',
            rugcheck_min_score=int(os.getenv('RUGCHECK_MIN_SCORE', '50')),
            enable_volume_breakout=os.getenv('ENABLE_VOLUME_BREAKOUT', 'true').lower() == 'true',
            enable_whale_tracking=os.getenv('ENABLE_WHALE_TRACKING', 'true').lower() == 'true',
            enable_movement_detection=os.getenv('ENABLE_MOVEMENT_DETECTION', 'true').lower() == 'true'
        )

        self.risk = RiskConfig(
            max_portfolio_risk_percent=float(os.getenv('MAX_PORTFOLIO_RISK_PERCENT', '10')),
            stop_loss_percent=float(os.getenv('STOP_LOSS_PERCENT', '15')),  # BATCH 9: Widen from 10% to 15%
            take_profit_percent=float(os.getenv('TAKE_PROFIT_PERCENT', '50')),
            max_daily_trades=int(os.getenv('MAX_DAILY_TRADES', '10')),
            max_open_positions=int(os.getenv('MAX_OPEN_POSITIONS', '5'))
        )

        self.api = APIConfig(
            alchemy_api_key=os.getenv('ALCHEMY_API_KEY', ''),
            solsniffer_api_key=os.getenv('SOLSNIFFER_API_KEY'),
            dexscreener_api_key=os.getenv('DEXSCREENER_API_KEY'),
            twitter_bearer_token=os.getenv('TWITTER_BEARER_TOKEN'),
            rugcheck_api_key=os.getenv('RUGCHECK_API_KEY'),
            solscan_api_key=os.getenv('SOLSCAN_API_KEY'),
            birdeye_api_key=os.getenv('BIRDEYE_API_KEY'),
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
