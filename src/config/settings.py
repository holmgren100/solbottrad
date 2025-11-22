import os
from dotenv import load_dotenv
from typing import Optional

load_dotenv()

class TradingConfig:
    """Trading configuration"""
    PAPER_TRADING_MODE: bool = os.getenv('PAPER_TRADING_MODE', 'true').lower() == 'true'
    INITIAL_CAPITAL: float = float(os.getenv('INITIAL_CAPITAL', '1000'))
    MAX_POSITION_SIZE: float = float(os.getenv('MAX_POSITION_SIZE', '100'))
    MIN_CONFIDENCE_SCORE: float = float(os.getenv('MIN_CONFIDENCE_SCORE', '0.0'))
    STOP_LOSS_PERCENT: float = float(os.getenv('STOP_LOSS_PERCENT', '5'))
    TAKE_PROFIT_PERCENT: float = float(os.getenv('TAKE_PROFIT_PERCENT', '10'))
    SCAN_INTERVAL: int = int(os.getenv('SCAN_INTERVAL', '60'))

class RiskConfig:
    """Risk management configuration"""
    MAX_SLIPPAGE: float = float(os.getenv('MAX_SLIPPAGE', '2.0'))
    MAX_DRAWDOWN: float = float(os.getenv('MAX_DRAWDOWN', '20.0'))
    POSITION_SIZE_PERCENT: float = float(os.getenv('POSITION_SIZE_PERCENT', '10'))
    MIN_LIQUIDITY: float = float(os.getenv('MIN_LIQUIDITY', '1000'))
    MIN_VOLUME_24H: float = float(os.getenv('MIN_VOLUME_24H', '10000'))

class APIConfig:
    """API keys and configuration"""
    ALCHEMY_API_KEY: Optional[str] = os.getenv('ALCHEMY_API_KEY')
    SOLSNIFFER_API_KEY: Optional[str] = os.getenv('SOLSNIFFER_API_KEY')
    DEXSCREENER_API_KEY: Optional[str] = os.getenv('DEXSCREENER_API_KEY')

    TWITTER_BEARER_TOKEN: Optional[str] = os.getenv('TWITTER_BEARER_TOKEN')
    TWITTER_API_KEY: Optional[str] = os.getenv('TWITTER_API_KEY')
    TWITTER_API_SECRET: Optional[str] = os.getenv('TWITTER_API_SECRET')
    TWITTER_ACCESS_TOKEN: Optional[str] = os.getenv('TWITTER_ACCESS_TOKEN')
    TWITTER_ACCESS_SECRET: Optional[str] = os.getenv('TWITTER_ACCESS_SECRET')

    TELEGRAM_BOT_TOKEN: Optional[str] = os.getenv('TELEGRAM_BOT_TOKEN')
    TELEGRAM_CHAT_ID: Optional[str] = os.getenv('TELEGRAM_CHAT_ID')

    SENTIMENT_MODEL: str = os.getenv('SENTIMENT_MODEL', 'distilbert-base-uncased-finetuned-sst-2-english')
    PRICE_MODEL: str = os.getenv('PRICE_MODEL', 'lstm')

def validate_config() -> bool:
    """Validate critical configuration"""
    errors = []

    if not APIConfig.TELEGRAM_BOT_TOKEN:
        errors.append("TELEGRAM_BOT_TOKEN is required")

    if not APIConfig.TELEGRAM_CHAT_ID:
        errors.append("TELEGRAM_CHAT_ID is required")

    if TradingConfig.PAPER_TRADING_MODE:
        print("⚠️  Running in PAPER TRADING mode")
    else:
        print("🔴 Running in LIVE TRADING mode")
        if not APIConfig.ALCHEMY_API_KEY:
            errors.append("ALCHEMY_API_KEY required for live trading")

    if errors:
        print("❌ Configuration errors:")
        for error in errors:
            print(f"   - {error}")
        return False

    return True
