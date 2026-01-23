"""
Breakeven Handler - Make Position Risk-Free at +50%

At +50% profit:
1. Move stop loss to entry +2% (position now RISK-FREE!)
2. Mark for 40% partial sell (recover initial investment)
3. Only trigger ONCE per position

This is capital preservation - we NEVER lose after +50%!
"""

import logging
from typing import Dict, Set

from config.parameters import (
    BREAKEVEN_TRIGGER_PERCENT,
    BREAKEVEN_SELL_PERCENT,
    BREAKEVEN_STOP_OFFSET
)

logger = logging.getLogger(__name__)


class BreakevenHandler:
    """
    Handles breakeven logic for positions.

    Ensures positions become risk-free after hitting +50% profit.
    """

    def __init__(self):
        """Initialize breakeven handler."""
        self.triggered_positions: Set[str] = set()  # Track which positions hit breakeven

        logger.info(
            f"Breakeven Handler initialized: "
            f"trigger={BREAKEVEN_TRIGGER_PERCENT}%, "
            f"sell={BREAKEVEN_SELL_PERCENT}%, "
            f"offset=+{BREAKEVEN_STOP_OFFSET}%"
        )

    def trigger_breakeven(self, position) -> Dict:
        """
        Check and trigger breakeven for a position.

        Args:
            position: Position object

        Returns:
            {
                "triggered": bool,
                "new_stop": float,
                "sell_percent": float,
                "reason": str
            }
        """
        try:
            # Check if already triggered
            if position.token_address in self.triggered_positions:
                return {
                    "triggered": False,
                    "new_stop": position.stop_loss,
                    "sell_percent": 0,
                    "reason": "Breakeven already triggered"
                }

            # Check if profit >= trigger threshold
            if position.pnl_percent < BREAKEVEN_TRIGGER_PERCENT:
                return {
                    "triggered": False,
                    "new_stop": position.stop_loss,
                    "sell_percent": 0,
                    "reason": f"Profit {position.pnl_percent:.1f}% < {BREAKEVEN_TRIGGER_PERCENT}%"
                }

            # TRIGGER BREAKEVEN!
            # Calculate new stop (entry + offset)
            new_stop = position.entry_price * (1 + BREAKEVEN_STOP_OFFSET / 100)

            # Update position stop loss
            position.update_stop_loss(new_stop)

            # Mark position as triggered
            self.triggered_positions.add(position.token_address)

            result = {
                "triggered": True,
                "new_stop": new_stop,
                "sell_percent": BREAKEVEN_SELL_PERCENT,
                "reason": f"RISK-FREE! +{position.pnl_percent:.1f}%, stop moved to +{BREAKEVEN_STOP_OFFSET}%"
            }

            logger.info(
                f"🛡️ BREAKEVEN TRIGGERED: {position.symbol} "
                f"at +{position.pnl_percent:.1f}%"
            )
            logger.info(
                f"   Stop moved: {position.entry_price:.6f} → {new_stop:.6f} (+{BREAKEVEN_STOP_OFFSET}%)"
            )
            logger.info(
                f"   Sell {BREAKEVEN_SELL_PERCENT}% to recover initial investment"
            )

            return result

        except Exception as e:
            logger.error(f"Error in breakeven trigger: {e}")
            return {
                "triggered": False,
                "new_stop": position.stop_loss,
                "sell_percent": 0,
                "reason": f"Error: {e}"
            }

    def is_triggered(self, token_address: str) -> bool:
        """
        Check if breakeven already triggered for a token.

        Args:
            token_address: Token address

        Returns:
            True if breakeven was triggered
        """
        return token_address in self.triggered_positions

    def reset(self, token_address: str):
        """
        Reset breakeven status for a token (e.g., after closing position).

        Args:
            token_address: Token address
        """
        if token_address in self.triggered_positions:
            self.triggered_positions.remove(token_address)
            logger.debug(f"Reset breakeven status for {token_address}")

    def get_stats(self) -> Dict:
        """Get breakeven statistics."""
        return {
            "total_triggered": len(self.triggered_positions),
            "triggered_tokens": list(self.triggered_positions)
        }


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    from src.position.position_manager import Position

    handler = BreakevenHandler()

    # Create test position
    position = Position(
        token_address="TEST123",
        symbol="TEST",
        entry_price=0.001,
        size_sol=0.1
    )

    # Test 1: Not enough profit
    position.update_price(0.0012)  # +20%
    result1 = handler.trigger_breakeven(position)
    print(f"\nAt +20%: Triggered={result1['triggered']}, Reason={result1['reason']}")

    # Test 2: Breakeven trigger
    position.update_price(0.0015)  # +50%
    result2 = handler.trigger_breakeven(position)
    print(f"\nAt +50%: Triggered={result2['triggered']}, Reason={result2['reason']}")
    print(f"New stop: {result2['new_stop']:.6f}")
    print(f"Sell: {result2['sell_percent']}%")

    # Test 3: Already triggered
    position.update_price(0.002)  # +100%
    result3 = handler.trigger_breakeven(position)
    print(f"\nAt +100%: Triggered={result3['triggered']}, Reason={result3['reason']}")

    # Stats
    print(f"\nStats: {handler.get_stats()}")
