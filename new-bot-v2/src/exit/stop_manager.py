"""
Stop Loss Manager - Protect Capital with Hard and Trailing Stops

Manages stop losses:
1. Hard Stop: -25% from entry (set at position open)
2. Trailing Stop: Activates at +100%, trails 30% from highest price
3. Breakeven Stop: Handled by BreakevenHandler at +50%

This ensures we cut losers fast and protect big winners!
"""

import logging
from typing import Dict

from config.parameters import (
    HARD_STOP_LOSS_PERCENT,
    TRAILING_STOP_ACTIVATION,
    TRAILING_STOP_PERCENT
)

logger = logging.getLogger(__name__)


class StopManager:
    """
    Manages stop losses for positions.

    Types:
    - Hard stop: -25% from entry (always active)
    - Trailing stop: Activates at +100%, trails 30% from high
    - Breakeven stop: Managed by BreakevenHandler
    """

    def __init__(self):
        """Initialize stop manager."""
        logger.info(
            f"Stop Manager initialized: "
            f"hard={HARD_STOP_LOSS_PERCENT}%, "
            f"trailing activates at +{TRAILING_STOP_ACTIVATION}% "
            f"(trails {TRAILING_STOP_PERCENT}%)"
        )

    def check_stops(self, position) -> Dict:
        """
        Check if any stop loss is hit.

        Args:
            position: Position object

        Returns:
            {
                "hit": bool,
                "stop_type": str,  # "hard" or "trailing"
                "stop_price": float,
                "current_price": float,
                "reason": str
            }
        """
        try:
            current_price = position.current_price
            stop_loss = position.stop_loss

            # Check hard stop
            hard_stop_hit = current_price <= stop_loss

            if hard_stop_hit:
                loss_pct = ((current_price - position.entry_price) / position.entry_price) * 100

                logger.warning(
                    f"🛑 HARD STOP HIT: {position.symbol} "
                    f"@ {current_price:.6f} (stop: {stop_loss:.6f})"
                )
                logger.warning(f"   Loss: {loss_pct:.1f}%")

                return {
                    "hit": True,
                    "stop_type": "hard",
                    "stop_price": stop_loss,
                    "current_price": current_price,
                    "reason": f"Hard stop @ {stop_loss:.6f} ({loss_pct:.1f}%)"
                }

            # Check trailing stop (only if in profit)
            if position.pnl_percent >= TRAILING_STOP_ACTIVATION:
                trailing_stop = self._calculate_trailing_stop(position)

                # Update position stop if trailing is tighter
                if trailing_stop > position.stop_loss:
                    old_stop = position.stop_loss
                    position.update_stop_loss(trailing_stop)

                    logger.info(
                        f"📈 Trailing stop updated: {position.symbol} "
                        f"{old_stop:.6f} → {trailing_stop:.6f}"
                    )

                # Check if trailing stop hit
                trailing_stop_hit = current_price <= trailing_stop

                if trailing_stop_hit:
                    profit_pct = position.pnl_percent

                    logger.info(
                        f"🎯 TRAILING STOP HIT: {position.symbol} "
                        f"@ {current_price:.6f} (stop: {trailing_stop:.6f})"
                    )
                    logger.info(f"   Profit locked: +{profit_pct:.1f}%")

                    return {
                        "hit": True,
                        "stop_type": "trailing",
                        "stop_price": trailing_stop,
                        "current_price": current_price,
                        "reason": f"Trailing stop @ {trailing_stop:.6f} (+{profit_pct:.1f}%)"
                    }

            # No stop hit
            return {
                "hit": False,
                "stop_type": "",
                "stop_price": stop_loss,
                "current_price": current_price,
                "reason": f"Price {current_price:.6f} > stop {stop_loss:.6f}"
            }

        except Exception as e:
            logger.error(f"Error checking stops: {e}")
            return {
                "hit": False,
                "stop_type": "",
                "stop_price": 0,
                "current_price": 0,
                "reason": f"Error: {e}"
            }

    def _calculate_trailing_stop(self, position) -> float:
        """
        Calculate trailing stop price.

        Trail TRAILING_STOP_PERCENT below highest price.

        Args:
            position: Position object

        Returns:
            Trailing stop price
        """
        try:
            # Trail 30% below highest price
            trailing_stop = position.highest_price * (1 - TRAILING_STOP_PERCENT / 100)

            logger.debug(
                f"Trailing stop: {trailing_stop:.6f} "
                f"({TRAILING_STOP_PERCENT}% below high {position.highest_price:.6f})"
            )

            return trailing_stop

        except Exception as e:
            logger.error(f"Error calculating trailing stop: {e}")
            return position.stop_loss  # Fallback to current stop

    def should_activate_trailing(self, position) -> bool:
        """
        Check if trailing stop should activate.

        Args:
            position: Position object

        Returns:
            True if profit >= activation threshold
        """
        return position.pnl_percent >= TRAILING_STOP_ACTIVATION

    def get_stop_info(self, position) -> Dict:
        """
        Get current stop information.

        Args:
            position: Position object

        Returns:
            {
                "current_stop": float,
                "stop_type": str,
                "stop_pct_from_entry": float,
                "trailing_active": bool,
                "trailing_stop": float (if active)
            }
        """
        try:
            trailing_active = self.should_activate_trailing(position)

            # Calculate stop percentage from entry
            if position.entry_price > 0:
                stop_pct = ((position.stop_loss - position.entry_price) / position.entry_price) * 100
            else:
                stop_pct = 0

            info = {
                "current_stop": position.stop_loss,
                "stop_type": "hard",
                "stop_pct_from_entry": stop_pct,
                "trailing_active": trailing_active,
            }

            # Add trailing stop if active
            if trailing_active:
                trailing_stop = self._calculate_trailing_stop(position)
                info["stop_type"] = "trailing"
                info["trailing_stop"] = trailing_stop

            return info

        except Exception as e:
            logger.error(f"Error getting stop info: {e}")
            return {
                "current_stop": 0,
                "stop_type": "unknown",
                "stop_pct_from_entry": 0,
                "trailing_active": False
            }

    def update_trailing_stop(self, position) -> Dict:
        """
        Update trailing stop if needed (called after price update).

        Args:
            position: Position object

        Returns:
            {
                "updated": bool,
                "old_stop": float,
                "new_stop": float,
                "reason": str
            }
        """
        try:
            # Only update if trailing is active
            if not self.should_activate_trailing(position):
                return {
                    "updated": False,
                    "old_stop": position.stop_loss,
                    "new_stop": position.stop_loss,
                    "reason": f"Trailing not active (profit {position.pnl_percent:.1f}% < {TRAILING_STOP_ACTIVATION}%)"
                }

            # Calculate trailing stop
            trailing_stop = self._calculate_trailing_stop(position)

            # Only update if trailing stop is higher (tighter)
            if trailing_stop > position.stop_loss:
                old_stop = position.stop_loss
                position.update_stop_loss(trailing_stop)

                return {
                    "updated": True,
                    "old_stop": old_stop,
                    "new_stop": trailing_stop,
                    "reason": f"Trailing stop raised ({TRAILING_STOP_PERCENT}% below high {position.highest_price:.6f})"
                }
            else:
                return {
                    "updated": False,
                    "old_stop": position.stop_loss,
                    "new_stop": position.stop_loss,
                    "reason": "Trailing stop not tighter than current stop"
                }

        except Exception as e:
            logger.error(f"Error updating trailing stop: {e}")
            return {
                "updated": False,
                "old_stop": 0,
                "new_stop": 0,
                "reason": f"Error: {e}"
            }


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    from src.position.position_manager import Position

    manager = StopManager()

    # Test 1: Hard stop scenario
    print("\n=== Test 1: Hard Stop ===")
    position1 = Position(
        token_address="TEST1",
        symbol="HARD",
        entry_price=0.001,
        size_sol=0.1
    )

    print(f"Entry: {position1.entry_price:.6f}")
    print(f"Hard stop: {position1.stop_loss:.6f}")

    # Price drops to -25%
    position1.update_price(0.00075)
    result1 = manager.check_stops(position1)
    print(f"\nAt -25%: Hit={result1['hit']}, Type={result1['stop_type']}")
    print(f"Reason: {result1['reason']}")

    # Test 2: Trailing stop scenario
    print("\n\n=== Test 2: Trailing Stop ===")
    position2 = Position(
        token_address="TEST2",
        symbol="TRAIL",
        entry_price=0.001,
        size_sol=0.1
    )

    # Price rises to +200%
    position2.update_price(0.003)
    print(f"\nAt +200%:")
    print(f"  Profit: {position2.pnl_percent:.1f}%")
    print(f"  Highest: {position2.highest_price:.6f}")

    # Check trailing stop activation
    update_result = manager.update_trailing_stop(position2)
    print(f"  Trailing updated: {update_result['updated']}")
    if update_result['updated']:
        print(f"  New stop: {update_result['new_stop']:.6f}")

    # Price drops to trigger trailing stop
    position2.update_price(0.0021)  # -30% from high
    result2 = manager.check_stops(position2)
    print(f"\nAt +110% (dropped from +200%):")
    print(f"  Hit={result2['hit']}, Type={result2['stop_type']}")
    print(f"  Reason: {result2['reason']}")

    # Test 3: Stop info
    print("\n\n=== Test 3: Stop Info ===")
    position3 = Position(
        token_address="TEST3",
        symbol="INFO",
        entry_price=0.001,
        size_sol=0.1
    )

    position3.update_price(0.0015)  # +50%
    info = manager.get_stop_info(position3)
    print(f"At +50%:")
    print(f"  Current stop: {info['current_stop']:.6f}")
    print(f"  Stop type: {info['stop_type']}")
    print(f"  Stop % from entry: {info['stop_pct_from_entry']:.1f}%")
    print(f"  Trailing active: {info['trailing_active']}")
