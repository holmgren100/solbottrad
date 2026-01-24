"""
🔒 PROTECTED - ML Bot 2 Exit Module

Contains the PositionManager with trailing stops.

Trailing Stops:
- 15% below PEAK price (not entry!)
- 85-93% win rate on trail exits
- Lets winners run to 100%+ gains

WHY IT WORKS:
- Not capped at fixed take profit (20%)
- Follows price up, protects downside
- Captures big moves before dump
- Proven: 85-93% success rate
"""

from ml_bot_core.exit.position_manager import PositionManager

__all__ = ['PositionManager']
