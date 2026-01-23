"""
Time-Based Exit - Cut Stagnant Positions

Exits positions that aren't moving:
- Open 3+ minutes with <5% movement = EXIT (stagnant)
- Open 10+ minutes and still red = EXIT (failed trade)

This keeps capital active and cuts losers fast!
"""

import logging
from typing import Dict

from config.parameters import (
    TIME_EXIT_MIN_MINUTES,
    TIME_EXIT_MIN_MOVEMENT
)

logger = logging.getLogger(__name__)


class TimeExit:
    """
    Handles time-based exit logic.

    Cuts positions that aren't performing:
    - Stagnant positions (3+ min, <5% movement)
    - Failed positions (10+ min, still red)
    """

    def __init__(self):
        """Initialize time exit handler."""
        logger.info(
            f"Time Exit initialized: "
            f"{TIME_EXIT_MIN_MINUTES}m min, "
            f"{TIME_EXIT_MIN_MOVEMENT}% min movement"
        )

    def should_exit(self, position) -> Dict:
        """
        Check if position should exit based on time.

        Args:
            position: Position object

        Returns:
            {
                "should_exit": bool,
                "reason": str,
                "hold_time": int,
                "movement_pct": float,
                "exit_type": str  # "stagnant" or "failed" or ""
            }
        """
        try:
            hold_time = position.hold_time_minutes
            movement_pct = abs(position.pnl_percent)  # Absolute movement
            is_profitable = position.pnl_percent > 0

            # Check 1: Stagnant position (3+ min, <5% movement)
            if hold_time >= TIME_EXIT_MIN_MINUTES:
                if movement_pct < TIME_EXIT_MIN_MOVEMENT:
                    logger.warning(
                        f"⏱️ TIME EXIT (STAGNANT): {position.symbol} "
                        f"held {hold_time}m, only {movement_pct:.1f}% movement"
                    )

                    return {
                        "should_exit": True,
                        "reason": f"Stagnant: {hold_time}m hold, {movement_pct:.1f}% movement",
                        "hold_time": hold_time,
                        "movement_pct": movement_pct,
                        "exit_type": "stagnant"
                    }

            # Check 2: Failed position (10+ min, still red)
            if hold_time >= 10:
                if not is_profitable:
                    logger.warning(
                        f"⏱️ TIME EXIT (FAILED): {position.symbol} "
                        f"held {hold_time}m, still {position.pnl_percent:.1f}%"
                    )

                    return {
                        "should_exit": True,
                        "reason": f"Failed: {hold_time}m hold, still {position.pnl_percent:.1f}%",
                        "hold_time": hold_time,
                        "movement_pct": movement_pct,
                        "exit_type": "failed"
                    }

            # No time exit needed
            return {
                "should_exit": False,
                "reason": f"OK: {hold_time}m, {position.pnl_percent:+.1f}%",
                "hold_time": hold_time,
                "movement_pct": movement_pct,
                "exit_type": ""
            }

        except Exception as e:
            logger.error(f"Error in time exit check: {e}")
            return {
                "should_exit": False,
                "reason": f"Error: {e}",
                "hold_time": 0,
                "movement_pct": 0,
                "exit_type": ""
            }

    def get_time_stats(self, position) -> Dict:
        """
        Get time-related statistics for position.

        Args:
            position: Position object

        Returns:
            {
                "hold_time_minutes": int,
                "hold_time_seconds": int,
                "pnl_percent": float,
                "movement_pct": float,
                "is_stagnant": bool,
                "is_failed": bool
            }
        """
        try:
            hold_time = position.hold_time_minutes
            movement_pct = abs(position.pnl_percent)
            is_profitable = position.pnl_percent > 0

            # Check stagnant
            is_stagnant = (
                hold_time >= TIME_EXIT_MIN_MINUTES and
                movement_pct < TIME_EXIT_MIN_MOVEMENT
            )

            # Check failed
            is_failed = (
                hold_time >= 10 and
                not is_profitable
            )

            return {
                "hold_time_minutes": hold_time,
                "hold_time_seconds": hold_time * 60,
                "pnl_percent": position.pnl_percent,
                "movement_pct": movement_pct,
                "is_stagnant": is_stagnant,
                "is_failed": is_failed
            }

        except Exception as e:
            logger.error(f"Error getting time stats: {e}")
            return {
                "hold_time_minutes": 0,
                "hold_time_seconds": 0,
                "pnl_percent": 0,
                "movement_pct": 0,
                "is_stagnant": False,
                "is_failed": False
            }

    def format_hold_time(self, minutes: int) -> str:
        """
        Format hold time in human-readable format.

        Args:
            minutes: Hold time in minutes

        Returns:
            Formatted string (e.g., "3m", "1h 15m")
        """
        if minutes < 60:
            return f"{minutes}m"
        else:
            hours = minutes // 60
            mins = minutes % 60
            return f"{hours}h {mins}m" if mins > 0 else f"{hours}h"


# Example usage
if __name__ == "__main__":
    import time
    from datetime import datetime, timedelta
    logging.basicConfig(level=logging.DEBUG)

    from src.position.position_manager import Position

    handler = TimeExit()

    # Test 1: Stagnant position (3+ min, <5% movement)
    print("\n=== Test 1: Stagnant Position ===")
    position1 = Position(
        token_address="TEST1",
        symbol="STAGNANT",
        entry_price=0.001,
        size_sol=0.1,
        timestamp=datetime.now() - timedelta(minutes=4)  # 4 minutes ago
    )

    position1.update_price(0.00103)  # Only +3% movement
    result1 = handler.should_exit(position1)
    print(f"Hold time: {result1['hold_time']}m")
    print(f"Movement: {result1['movement_pct']:.1f}%")
    print(f"Should exit: {result1['should_exit']}")
    print(f"Reason: {result1['reason']}")

    # Test 2: Failed position (10+ min, still red)
    print("\n\n=== Test 2: Failed Position ===")
    position2 = Position(
        token_address="TEST2",
        symbol="FAILED",
        entry_price=0.001,
        size_sol=0.1,
        timestamp=datetime.now() - timedelta(minutes=12)  # 12 minutes ago
    )

    position2.update_price(0.00095)  # -5%
    result2 = handler.should_exit(position2)
    print(f"Hold time: {result2['hold_time']}m")
    print(f"PnL: {position2.pnl_percent:.1f}%")
    print(f"Should exit: {result2['should_exit']}")
    print(f"Reason: {result2['reason']}")

    # Test 3: Good position (moving well)
    print("\n\n=== Test 3: Good Position ===")
    position3 = Position(
        token_address="TEST3",
        symbol="GOOD",
        entry_price=0.001,
        size_sol=0.1,
        timestamp=datetime.now() - timedelta(minutes=2)
    )

    position3.update_price(0.0012)  # +20%
    result3 = handler.should_exit(position3)
    print(f"Hold time: {result3['hold_time']}m")
    print(f"PnL: {position3.pnl_percent:.1f}%")
    print(f"Should exit: {result3['should_exit']}")
    print(f"Reason: {result3['reason']}")

    # Test 4: Time stats
    print("\n\n=== Test 4: Time Stats ===")
    stats = handler.get_time_stats(position1)
    print(f"Hold time: {stats['hold_time_minutes']}m ({stats['hold_time_seconds']}s)")
    print(f"PnL: {stats['pnl_percent']:.1f}%")
    print(f"Movement: {stats['movement_pct']:.1f}%")
    print(f"Is stagnant: {stats['is_stagnant']}")
    print(f"Is failed: {stats['is_failed']}")

    # Test 5: Format hold time
    print("\n\n=== Test 5: Format Hold Time ===")
    print(f"45 minutes: {handler.format_hold_time(45)}")
    print(f"75 minutes: {handler.format_hold_time(75)}")
    print(f"120 minutes: {handler.format_hold_time(120)}")
