"""
🔒 PROTECTED ML BOT CORE
Based on ML Bot 2 (71.7% win rate, 9.02x profit factor, 276 trades)

DO NOT MODIFY - This is proven core logic!

This package contains the protected core components from ML Bot 2:
- RiskAssessor: Weighted risk scoring (35% liquidity, 35% security)
- PositionManager: Trailing stops (15% below peak), drawdown tracking
- PriceValidator: Dual-source validation (DexScreener + Jupiter)
- MLBot2Config: Exact settings that achieved 71.7% win rate

WHY IT WORKS:
- Simpler than ML Bot 1 but more effective (+8.4% win rate)
- Fewer filters = less over-optimization
- Trusts the core risk scoring
- Lets winners run with trailing stops
- Fast rug detection (5 min, $5k)

PERFORMANCE METRICS (ML Bot 2):
- Win Rate: 71.7% (vs 63.3% for ML Bot 1)
- Avg Profit: $30.09 per trade (vs $12.88 for ML Bot 1)
- Profit Factor: 9.02x (vs 3.58x for ML Bot 1)
- Stop Loss Rate: 8.3% (vs 22.2% for ML Bot 1)
- Trail Win Rate: 85-93%
- Low Liq Exit Win Rate: 73.7%

THE SECRET:
- LESS IS MORE! Fewer filters = better performance
- 70% weight on essentials (liquidity + security)
- Only 10% on volatility/age (they're opportunities!)
- Trailing stops let winners run to 100%+
- Fast rug detection exits before total loss
"""

__version__ = "2.0.0"
__protected__ = True
__base_bot__ = "ML Bot 2"
__performance__ = {
    "trades": 276,
    "win_rate": 71.7,
    "avg_profit": 30.09,
    "profit_factor": 9.02,
    "stop_loss_rate": 8.3,
    "trail_win_rate_min": 85.0,
    "trail_win_rate_max": 93.0,
    "low_liq_exit_win_rate": 73.7,
}

# Import protected components
from ml_bot_core.selection.risk_assessor import RiskAssessor
from ml_bot_core.exit.position_manager import PositionManager
from ml_bot_core.monitoring.price_validator import PriceValidator
from ml_bot_core.config.ml_bot_2_config import MLBot2Config, DEFAULT_CONFIG

__all__ = [
    'RiskAssessor',
    'PositionManager',
    'PriceValidator',
    'MLBot2Config',
    'DEFAULT_CONFIG',
    'validate_core',
    'get_performance_metrics',
]


def validate_core():
    """
    Validate that the protected core hasn't been modified.

    This is a placeholder for future file hash validation.
    For now, it just confirms the core is loaded.

    Returns:
        bool: True if core is valid
    """
    # TODO: Add file hash validation in production
    # Check that critical files match original hashes
    # Raise error if any modifications detected

    return True


def get_performance_metrics() -> dict:
    """
    Get ML Bot 2's proven performance metrics.

    Returns:
        dict: Performance metrics from ML Bot 2
    """
    return __performance__.copy()


def print_info():
    """Print protected core information."""
    print("=" * 70)
    print("🔒 PROTECTED ML BOT CORE")
    print("=" * 70)
    print(f"Version: {__version__}")
    print(f"Base Bot: {__base_bot__}")
    print(f"Protected: {__protected__}")
    print()
    print("📊 PROVEN PERFORMANCE:")
    print(f"  Trades: {__performance__['trades']}")
    print(f"  Win Rate: {__performance__['win_rate']}%")
    print(f"  Avg Profit: ${__performance__['avg_profit']:.2f}/trade")
    print(f"  Profit Factor: {__performance__['profit_factor']:.2f}x")
    print(f"  Stop Loss Rate: {__performance__['stop_loss_rate']}%")
    print(f"  Trail Win Rate: {__performance__['trail_win_rate_min']}-{__performance__['trail_win_rate_max']}%")
    print(f"  Low Liq Exit Win Rate: {__performance__['low_liq_exit_win_rate']}%")
    print()
    print("🎯 CORE COMPONENTS:")
    print("  ✅ RiskAssessor - Weighted risk scoring (THE SECRET!)")
    print("  ✅ PositionManager - Trailing stops (15% below peak)")
    print("  ✅ PriceValidator - Dual-source validation")
    print("  ✅ MLBot2Config - Exact proven settings")
    print()
    print("⚠️  DO NOT MODIFY - Import and use only!")
    print("=" * 70)


# Print info on import (optional - remove if too verbose)
# print_info()
