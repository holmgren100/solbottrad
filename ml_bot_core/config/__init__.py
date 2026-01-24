"""
🔒 PROTECTED - ML Bot 2 Configuration Module

Contains the exact settings that achieved:
- 71.7% win rate (276 trades)
- $30.09 average profit per trade
- 9.02x profit factor
- 8.3% stop loss rate

DO NOT MODIFY without extensive testing and data proof!

WHAT ML BOT 2 HAS (KEEP THIS!):
✅ Weighted risk scoring
✅ Trailing stops at 15%
✅ Fast rug detection (5 min, $5k)
✅ Dual-source price validation

WHAT ML BOT 2 DOESN'T HAVE (And wins without!):
❌ Fee/slippage simulation
❌ Tier 2 filters (they block winners!)
❌ Volume fallback (adds risk)
❌ Stuck position cleanup
"""

from ml_bot_core.config.ml_bot_2_config import MLBot2Config, DEFAULT_CONFIG

__all__ = ['MLBot2Config', 'DEFAULT_CONFIG']
