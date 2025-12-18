"""
ML Bot 2 Foundation - Trading Bot

Main integration layer that combines:
- 🔒 Protected core (ml_bot_core) - ML Bot 2's proven 71.7% win logic
- ✅ Optional enhancements (enhanced_modules) - CSV tracking, safety filters

Architecture:
    Protected Core (NEVER modified)
    ↓
    Enhancement Modules (wrap around core)
    ↓
    Trading Bot (main integration)

Usage:
    from trading_bot import MLBot2Foundation
    from trading_bot.config import load_config

    config = load_config()
    bot = MLBot2Foundation(config)
    await bot.start()
"""

from trading_bot.main import MLBot2Foundation
from trading_bot.config import load_config, BotConfig

__all__ = [
    'MLBot2Foundation',
    'load_config',
    'BotConfig',
]

__version__ = "1.0.0"
