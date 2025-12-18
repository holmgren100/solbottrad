"""
Configuration loader for ML Bot 2 Trading Bot.

Loads settings from .env file and creates configuration objects for:
- Protected core (MLBot2Config)
- Enhancement modules (CSV, Safety Filters)
- API credentials

Usage:
    from trading_bot.config import load_config

    config = load_config()
    print(f"Trading mode: {'PAPER' if config.paper_trading else 'LIVE'}")
"""

import os
import sys
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv
import logging

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ml_bot_core import MLBot2Config
from enhanced_modules import SafetyConfig

logger = logging.getLogger(__name__)


@dataclass
class BotConfig:
    """
    Complete bot configuration combining core + enhancements.

    This wraps the protected MLBot2Config and adds enhancement settings.
    """

    # Mode
    paper_trading: bool = True
    paper_sol_balance: float = 1000.0

    # Protected core config
    core_config: MLBot2Config = None

    # Enhancement modules
    enable_csv_tracking: bool = True
    csv_auto_export: bool = True
    csv_export_path: str = 'data/ml_trades.csv'

    enable_safety_filters: bool = False
    safety_config: SafetyConfig = None

    # API Credentials
    solana_rpc_url: str = ''
    solana_private_key: str = ''
    dexscreener_api_key: str = ''
    jupiter_api_url: str = ''
    solsniffer_api_key: str = ''
    solscan_api_key: str = ''
    telegram_bot_token: str = ''
    telegram_chat_id: str = ''

    # Logging
    log_level: str = 'INFO'
    log_file: str = 'trading_bot.log'

    def __post_init__(self):
        """Initialize nested configs if not provided."""
        if self.core_config is None:
            self.core_config = MLBot2Config()
        if self.safety_config is None:
            self.safety_config = SafetyConfig()

    def validate(self) -> tuple[bool, list[str]]:
        """
        Validate configuration.

        Returns:
            Tuple of (is_valid, errors)
        """
        errors = []

        # Check API keys if not paper trading
        if not self.paper_trading:
            if not self.solana_private_key:
                errors.append("SOLANA_PRIVATE_KEY required for live trading")
            if not self.solana_rpc_url:
                errors.append("SOLANA_RPC_URL required")

        # Warn about safety filters
        if self.enable_safety_filters:
            logger.warning(
                "⚠️  Safety filters enabled! ML Bot 2 achieved 71.7% win WITHOUT these. "
                "A/B test to verify they IMPROVE performance!"
            )

        # Recommend CSV tracking
        if not self.enable_csv_tracking:
            logger.warning("CSV tracking disabled - you won't have data for optimization!")

        return len(errors) == 0, errors


def load_config(env_file: str = '.env') -> BotConfig:
    """
    Load configuration from .env file.

    Args:
        env_file: Path to .env file (defaults to .env)

    Returns:
        BotConfig object with all settings

    Raises:
        FileNotFoundError: If .env file doesn't exist
        ValueError: If configuration is invalid
    """
    # Load .env file
    if not os.path.exists(env_file):
        raise FileNotFoundError(
            f"{env_file} not found. Copy .env.ml_bot_2 to .env first:\n"
            f"  cp .env.ml_bot_2 .env"
        )

    load_dotenv(env_file)
    logger.info(f"Loading configuration from {env_file}")

    # === CORE CONFIGURATION ===
    # Create MLBot2Config with settings from .env (or use defaults)
    core_config = MLBot2Config()

    # Override core config from .env if provided
    core_config.use_trailing_stop = _get_bool('USE_TRAILING_STOP', True)
    core_config.trailing_stop_percent = _get_float('TRAILING_STOP_PERCENT', 15.0)
    core_config.stop_loss_percent = _get_float('STOP_LOSS_PERCENT', 20.0)
    core_config.take_profit_percent = _get_float('TAKE_PROFIT_PERCENT', 50.0)
    core_config.max_open_positions = _get_int('MAX_OPEN_POSITIONS', 7)
    core_config.rug_detection_enabled = _get_bool('RUG_DETECTION_ENABLED', True)
    core_config.stale_price_minutes = _get_int('STALE_PRICE_MINUTES', 5)
    core_config.min_position_liquidity = _get_float('MIN_POSITION_LIQUIDITY', 5000.0)
    core_config.scan_interval = _get_int('SCAN_INTERVAL', 120)
    core_config.monitor_interval = _get_int('MONITOR_INTERVAL', 60)

    # === SAFETY FILTERS CONFIGURATION ===
    safety_config = SafetyConfig(
        enable_lp_lock_check=_get_bool('ENABLE_LP_LOCK_CHECK', True),
        lp_lock_min_days=_get_int('LP_LOCK_MIN_DAYS', 30),
        lp_lock_accept_burned=_get_bool('LP_LOCK_ACCEPT_BURNED', True),
        enable_holder_check=_get_bool('ENABLE_HOLDER_CHECK', True),
        holder_top10_max_percent=_get_float('HOLDER_TOP10_MAX', 50.0),
        holder_top1_max_percent=_get_float('HOLDER_TOP1_MAX', 20.0),
        enable_contract_safety=_get_bool('ENABLE_CONTRACT_SAFETY', True),
        reject_mint_authority=_get_bool('REJECT_MINT_AUTHORITY', True),
        reject_freeze_authority=_get_bool('REJECT_FREEZE_AUTHORITY', True),
        require_ownership_renounced=_get_bool('REQUIRE_OWNERSHIP_RENOUNCED', True),
    )

    # === BOT CONFIGURATION ===
    config = BotConfig(
        # Mode
        paper_trading=_get_bool('PAPER_TRADING_MODE', True),
        paper_sol_balance=_get_float('PAPER_SOL_BALANCE', 1000.0),

        # Core
        core_config=core_config,

        # CSV Tracking
        enable_csv_tracking=_get_bool('ENABLE_CSV_TRACKING', True),
        csv_auto_export=_get_bool('CSV_AUTO_EXPORT', True),
        csv_export_path=os.getenv('CSV_EXPORT_PATH', 'data/ml_trades.csv'),

        # Safety Filters
        enable_safety_filters=_get_bool('ENABLE_SAFETY_FILTERS', False),
        safety_config=safety_config,

        # API Credentials
        solana_rpc_url=os.getenv('SOLANA_RPC_URL', 'https://api.mainnet-beta.solana.com'),
        solana_private_key=os.getenv('SOLANA_PRIVATE_KEY', ''),
        dexscreener_api_key=os.getenv('DEXSCREENER_API_KEY', ''),
        jupiter_api_url=os.getenv('JUPITER_API_URL', 'https://quote-api.jup.ag/v6'),
        solsniffer_api_key=os.getenv('SOLSNIFFER_API_KEY', ''),
        solscan_api_key=os.getenv('SOLSCAN_API_KEY', ''),
        telegram_bot_token=os.getenv('TELEGRAM_BOT_TOKEN', ''),
        telegram_chat_id=os.getenv('TELEGRAM_CHAT_ID', ''),

        # Logging
        log_level=os.getenv('LOG_LEVEL', 'INFO'),
        log_file=os.getenv('LOG_FILE', 'trading_bot.log'),
    )

    # Validate configuration
    is_valid, errors = config.validate()
    if not is_valid:
        error_msg = "Configuration errors:\n" + "\n".join(f"  - {e}" for e in errors)
        raise ValueError(error_msg)

    # Log configuration summary
    logger.info("=" * 60)
    logger.info("ML BOT 2 CONFIGURATION LOADED")
    logger.info("=" * 60)
    logger.info(f"Mode: {'PAPER TRADING' if config.paper_trading else 'LIVE TRADING ⚠️'}")
    logger.info(f"Paper Balance: ${config.paper_sol_balance:.2f} SOL")
    logger.info(f"Max Positions: {config.core_config.max_open_positions}")
    logger.info(f"Trailing Stop: {config.core_config.trailing_stop_percent}% below peak")
    logger.info(f"Rug Detection: {config.core_config.stale_price_minutes}min, ${config.core_config.min_position_liquidity:,.0f}")
    logger.info(f"CSV Tracking: {'ENABLED ✅' if config.enable_csv_tracking else 'DISABLED ⚠️'}")
    logger.info(f"Safety Filters: {'ENABLED (test impact!)' if config.enable_safety_filters else 'DISABLED'}")
    logger.info("=" * 60)

    return config


def _get_bool(key: str, default: bool) -> bool:
    """Get boolean from environment variable."""
    value = os.getenv(key, str(default))
    return value.lower() in ('true', '1', 'yes', 'on')


def _get_int(key: str, default: int) -> int:
    """Get integer from environment variable."""
    try:
        return int(os.getenv(key, str(default)))
    except ValueError:
        logger.warning(f"Invalid int for {key}, using default: {default}")
        return default


def _get_float(key: str, default: float) -> float:
    """Get float from environment variable."""
    try:
        return float(os.getenv(key, str(default)))
    except ValueError:
        logger.warning(f"Invalid float for {key}, using default: {default}")
        return default


if __name__ == '__main__':
    """Test configuration loading."""
    import sys

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='[%(levelname)s] %(message)s'
    )

    try:
        config = load_config()
        print("\n✅ Configuration loaded successfully!")
        print(f"\nCore Config:\n{config.core_config}")

        if config.enable_safety_filters:
            print(f"\nSafety Config:\n{config.safety_config}")

    except FileNotFoundError as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
    except ValueError as e:
        print(f"\n❌ {e}")
        sys.exit(1)
