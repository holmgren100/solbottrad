# config/settings.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from pydantic import Field, ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


def _default_base_dir() -> str:
    try:
        return str(Path(__file__).resolve().parent.parent)
    except NameError:
        return str(Path.cwd())


def _default_subdir(name: str) -> str:
    return str(Path(_default_base_dir()) / name)


class Settings(BaseSettings):
    # Project paths
    BASE_DIR: str = Field(default_factory=_default_base_dir)
    LOGS_DIR: str = Field(default_factory=lambda: _default_subdir("logs"))
    DATA_DIR: str = Field(default_factory=lambda: _default_subdir("data"))
    MODELS_DIR: str = Field(default_factory=lambda: _default_subdir("models"))

    # Trading parameters
    MIN_VOLUME: float = Field(1000.0)
    MIN_LIQUIDITY: float = Field(5000.0)
    MIN_SENTIMENT_SCORE: float = Field(0.5)
    PRICE_CHANGE_THRESHOLD: float = Field(0.05)
    DEFAULT_POSITION_SIZE: float = Field(100.0)
    MIN_SOCIAL_SCORE: float = Field(0.6)
    DEFAULT_SLIPPAGE: float = Field(5.0)
    STOP_LOSS_PERCENTAGE: float = Field(0.10)
    TAKE_PROFIT_PERCENTAGE: float = Field(0.20)

    # Trading settings
    DEFAULT_BUY_AMOUNT: float = Field(0.01)
    DEFAULT_PRIORITY_FEE: float = Field(0.0001)
    MAX_TRADE_RETRIES: int = Field(3)
    TRADE_TIMEOUT: int = Field(30)

    # Dry run / paper trading
    DRY_RUN: bool = Field(True)
    PAPER_SOL_BALANCE: float = Field(5.0)
    TRADE_JOURNAL_PATH: str = Field(default_factory=lambda: str(Path(_default_subdir("data")) / "trade_journal.csv"))

    # Endpoints
    SOLANA_HTTP: Optional[str] = Field(default=None)
    SOLANA_WSS: Optional[str] = Field(default=None)
    ALCHEMY_WSS: Optional[str] = Field(default=None)

    # API keys
    OPENAI_API_KEY: str = Field(...)
    SOLSNIFFER_API_KEY: str = Field(...)
    METEORA_API_KEY: Optional[str] = Field(default=None)
    TWITTER_BEARER_TOKEN: str = Field(...)
    RUGCHECK_API_KEY: Optional[str] = Field(default=None)
    DEXSCREENER_API_URL: str = Field("https://api.dexscreener.com/token-profiles/latest/v1")
    SANTIMENT_API_KEY: str = Field(...)
    COINMARKETCAP_API_KEY: str = Field(...)
    CRYPTORANK_API_KEY: str = Field(...)
    BITQUERY_API_KEY: str = Field(...)

    # Telegram
    TELEGRAM_BOT_TOKEN: str = Field(...)
    TELEGRAM_CHAT_ID: str = Field(...)
    TELEGRAM_API_HASH: str = Field(...)
    TELEGRAM_API_ID: int = Field(...)
    TELEGRAM_SESSION_NEW: Optional[str] = Field(default=None)
    GMGN_BOT_USERNAME: str = Field(...)

    # Monitoring
    HEALTH_CHECK_INTERVAL: int = Field(300)
    RATE_LIMIT_CALLS: int = Field(30)
    RATE_LIMIT_PERIOD: int = Field(60)
    MONITORING_INTERVAL: int = Field(60)
    MAX_RETRIES: int = Field(3)
    RETRY_DELAY: int = Field(5)

    # Wallets - FIXED: Use field_validator to handle both CSV and JSON formats
    TRACKED_WALLETS: List[str] = Field(default_factory=list)

    # Logging preferences
    LOG_LEVEL: str = Field("INFO")
    LOG_FORMAT: str = Field("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    LOG_ROTATION: str = Field("midnight")
    LOG_BACKUP_COUNT: int = Field(7)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
        populate_by_name=True,
    )

    @field_validator("LOG_LEVEL", mode="after")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        up = v.upper()
        if up not in valid:
            raise ValueError(f"Invalid log level. Must be one of: {', '.join(valid)}")
        return up

    # FIXED: This validator handles both CSV and JSON formats for TRACKED_WALLETS
    @field_validator("TRACKED_WALLETS", mode="before")
    @classmethod
    def parse_tracked_wallets(cls, v):
        if v is None:
            return []
        if isinstance(v, list):
            return [str(x).strip() for x in v if str(x).strip()]
        if isinstance(v, str):
            s = v.strip()
            if not s:
                return []
            if s.startswith("[") and s.endswith("]"):
                try:
                    parsed = json.loads(s)
                    if isinstance(parsed, list):
                        return [str(x).strip() for x in parsed if str(x).strip()]
                except Exception:
                    pass
            return [w.strip() for w in s.split(",") if w.strip()]
        return []

    def validate_config(self) -> None:
        for d in [self.LOGS_DIR, self.DATA_DIR, self.MODELS_DIR, str(Path(self.TRADE_JOURNAL_PATH).parent)]:
            Path(d).mkdir(parents=True, exist_ok=True)
        self._validate_api_keys()
        self._validate_numbers()
        self._validate_telegram()

    def _validate_api_keys(self) -> None:
        if not (self.SOLANA_WSS or self.ALCHEMY_WSS):
            raise ValueError("Missing WebSocket endpoint: set SOLANA_WSS or ALCHEMY_WSS")
        required = [
            "OPENAI_API_KEY",
            "SOLSNIFFER_API_KEY",
            "TWITTER_BEARER_TOKEN",
            "SANTIMENT_API_KEY",
            "COINMARKETCAP_API_KEY",
            "CRYPTORANK_API_KEY",
            "BITQUERY_API_KEY",
            "TELEGRAM_BOT_TOKEN",
        ]
        missing = [k for k in required if not getattr(self, k, None)]
        if missing:
            raise ValueError(f"Missing required API keys: {', '.join(missing)}")

    def _validate_numbers(self) -> None:
        if self.MIN_VOLUME <= 0:
            raise ValueError("MIN_VOLUME must be > 0")
        if self.MIN_LIQUIDITY <= 0:
            raise ValueError("MIN_LIQUIDITY must be > 0")
        if not 0 <= self.MIN_SENTIMENT_SCORE <= 1:
            raise ValueError("MIN_SENTIMENT_SCORE must be between 0 and 1")
        if not 0 <= self.MIN_SOCIAL_SCORE <= 1:
            raise ValueError("MIN_SOCIAL_SCORE must be between 0 and 1")
        if not 0 <= self.DEFAULT_SLIPPAGE <= 100:
            raise ValueError("DEFAULT_SLIPPAGE must be a percentage (0-100)")
        if not 0 <= self.STOP_LOSS_PERCENTAGE <= 1:
            raise ValueError("STOP_LOSS_PERCENTAGE must be between 0 and 1")
        if not 0 <= self.TAKE_PROFIT_PERCENTAGE <= 1:
            raise ValueError("TAKE_PROFIT_PERCENTAGE must be between 0 and 1")
        if self.PAPER_SOL_BALANCE < 0:
            raise ValueError("PAPER_SOL_BALANCE must be >= 0")

    def _validate_telegram(self) -> None:
        required = ["TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "TELEGRAM_API_HASH", "TELEGRAM_API_ID"]
        miss = [k for k in required if not getattr(self, k, None)]
        if miss:
            raise ValueError(f"Missing required Telegram settings: {', '.join(miss)}")

    def get_api_config(self) -> Dict[str, Any]:
        return {
            "dexscreener_url": self.DEXSCREENER_API_URL,
            "rate_limit_calls": self.RATE_LIMIT_CALLS,
            "rate_limit_period": self.RATE_LIMIT_PERIOD,
            "max_retries": self.MAX_RETRIES,
            "retry_delay": self.RETRY_DELAY,
        }

    def get_trading_config(self) -> Dict[str, Any]:
        return {
            "position_size": self.DEFAULT_POSITION_SIZE,
            "slippage": self.DEFAULT_SLIPPAGE,
            "stop_loss": self.STOP_LOSS_PERCENTAGE,
            "take_profit": self.TAKE_PROFIT_PERCENTAGE,
            "max_retries": self.MAX_TRADE_RETRIES,
            "timeout": self.TRADE_TIMEOUT,
        }


try:
    settings = Settings()
except (ValidationError, ValueError) as e:
    print(f"Settings validation error: {e}")
    raise
except Exception as e:
    print(f"Unexpected error during settings initialization: {e}")
    raise

__all__ = ["Settings", "settings"]