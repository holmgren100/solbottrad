"""
Enhanced Modules - Optional Trading Bot Enhancements

These modules are OPTIONAL and wrap around the protected ML Bot 2 core.
They do NOT modify core logic - only add functionality for:
- Comprehensive data tracking (CSV)
- Additional safety filters (LP lock, holders, contract)
- (Future) Telegram bot control
- (Future) Multi-source API aggregation

WHY OPTIONAL:
- ML Bot 2 achieves 71.7% win rate WITHOUT these
- They need to be A/B tested to prove they IMPROVE performance
- Can be toggled on/off via .env configuration

Usage:
    from enhanced_modules import CSVTracker, SafetyFilters

    # CSV tracking (always recommended - essential for analysis)
    csv_tracker = CSVTracker(enabled=True)

    # Safety filters (test if they help or hurt)
    safety_filters = SafetyFilters(enabled=True, config={...})
"""

from enhanced_modules.csv_tracker import CSVTracker, EnhancedTradeData
from enhanced_modules.safety_filters import SafetyFilters, SafetyConfig
from enhanced_modules.rejected_tracker import RejectedTracker

__all__ = [
    'CSVTracker',
    'EnhancedTradeData',
    'SafetyFilters',
    'SafetyConfig',
    'RejectedTracker',
]

__version__ = "1.0.0"
