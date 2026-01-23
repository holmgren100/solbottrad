"""
Partial Profits - Lock in Gains at Milestones

Takes profits at key levels while letting winners run:

+50%: Sell 40% (with breakeven - recover initial investment)
+500%: Sell 30% (lock in solid gains)
+1000%: Sell 30% (lock in massive gains)
Remaining: 40% moon bag rides to 1700%+

This ensures we ALWAYS profit on big winners!
"""

import logging
from typing import Dict, List

from config.parameters import (
    PARTIAL_PROFIT_1_TRIGGER,
    PARTIAL_PROFIT_1_SELL,
    PARTIAL_PROFIT_2_TRIGGER,
    PARTIAL_PROFIT_2_SELL,
    MOON_BAG_PERCENT
)

logger = logging.getLogger(__name__)


class PartialProfits:
    """
    Manages partial profit taking at milestones.

    Ensures we lock in gains while letting winners run.
    """

    def __init__(self):
        """Initialize partial profits manager."""
        logger.info(
            f"Partial Profits initialized: "
            f"+{PARTIAL_PROFIT_1_TRIGGER}% ({PARTIAL_PROFIT_1_SELL}%), "
            f"+{PARTIAL_PROFIT_2_TRIGGER}% ({PARTIAL_PROFIT_2_SELL}%), "
            f"moon bag: {MOON_BAG_PERCENT}%"
        )

    def _has_taken_partial(self, position, partial_name: str) -> bool:
        """
        Check if a partial has already been taken.

        Args:
            position: Position object
            partial_name: Partial stage name (e.g., "PARTIAL_50")

        Returns:
            True if partial was already taken
        """
        for stage in position.position_stages:
            if stage["type"] == partial_name:
                return True
        return False

    def check_partials(self, position) -> Dict:
        """
        Check if position should take partial profits.

        Args:
            position: Position object

        Returns:
            {
                "should_sell": bool,
                "sell_pct": float,
                "trigger_pct": int,
                "partial_name": str,
                "reason": str
            }
        """
        try:
            # Check +1000% partial first (highest trigger)
            if position.pnl_percent >= PARTIAL_PROFIT_2_TRIGGER:
                partial_name = "PARTIAL_1000"

                if not self._has_taken_partial(position, partial_name):
                    logger.info(
                        f"💰💰💰 PARTIAL PROFIT: {position.symbol} at +{position.pnl_percent:.1f}%"
                    )
                    logger.info(
                        f"   Sell {PARTIAL_PROFIT_2_SELL}% - lock in massive gains!"
                    )

                    return {
                        "should_sell": True,
                        "sell_pct": PARTIAL_PROFIT_2_SELL,
                        "trigger_pct": PARTIAL_PROFIT_2_TRIGGER,
                        "partial_name": partial_name,
                        "reason": f"+{PARTIAL_PROFIT_2_TRIGGER}% milestone"
                    }

            # Check +500% partial
            if position.pnl_percent >= PARTIAL_PROFIT_1_TRIGGER:
                partial_name = "PARTIAL_500"

                if not self._has_taken_partial(position, partial_name):
                    logger.info(
                        f"💰💰 PARTIAL PROFIT: {position.symbol} at +{position.pnl_percent:.1f}%"
                    )
                    logger.info(
                        f"   Sell {PARTIAL_PROFIT_1_SELL}% - lock in solid gains!"
                    )

                    return {
                        "should_sell": True,
                        "sell_pct": PARTIAL_PROFIT_1_SELL,
                        "trigger_pct": PARTIAL_PROFIT_1_TRIGGER,
                        "partial_name": partial_name,
                        "reason": f"+{PARTIAL_PROFIT_1_TRIGGER}% milestone"
                    }

            # Check +50% partial (breakeven - handled separately but check here too)
            # This is usually triggered by BreakevenHandler, but we track it here
            if position.pnl_percent >= 50:
                partial_name = "BREAKEVEN_50"

                if not self._has_taken_partial(position, partial_name):
                    # Note: This should normally be triggered by BreakevenHandler
                    # We return the data but BreakevenHandler will handle the action
                    logger.debug(f"Breakeven partial ready for {position.symbol}")

                    return {
                        "should_sell": True,
                        "sell_pct": 40,  # From BREAKEVEN_SELL_PERCENT
                        "trigger_pct": 50,
                        "partial_name": partial_name,
                        "reason": "Breakeven +50%"
                    }

            # No partials to take
            return {
                "should_sell": False,
                "sell_pct": 0,
                "trigger_pct": 0,
                "partial_name": "",
                "reason": f"Profit {position.pnl_percent:.1f}% below partial triggers"
            }

        except Exception as e:
            logger.error(f"Error checking partials: {e}")
            return {
                "should_sell": False,
                "sell_pct": 0,
                "trigger_pct": 0,
                "partial_name": "",
                "reason": f"Error: {e}"
            }

    def get_remaining_target(self, position) -> Dict:
        """
        Get moon bag info and target.

        Args:
            position: Position object

        Returns:
            {
                "moon_bag_pct": float,
                "partials_taken": int,
                "remaining_pct": float,
                "target_gain": int
            }
        """
        try:
            # Count partials taken
            partials_taken = 0
            total_sold = 0

            for stage in position.position_stages:
                if stage["type"].startswith("PARTIAL") or stage["type"].startswith("BREAKEVEN"):
                    partials_taken += 1
                    # Note: size_sol is negative for sells
                    if stage.get("size_sol", 0) < 0:
                        sold_pct = abs(stage["size_sol"]) / position.initial_size_sol * 100
                        total_sold += sold_pct

            remaining_pct = 100 - total_sold

            return {
                "moon_bag_pct": MOON_BAG_PERCENT,
                "partials_taken": partials_taken,
                "remaining_pct": remaining_pct,
                "target_gain": 1700  # Target for moon bag
            }

        except Exception as e:
            logger.error(f"Error getting remaining target: {e}")
            return {
                "moon_bag_pct": MOON_BAG_PERCENT,
                "partials_taken": 0,
                "remaining_pct": 100,
                "target_gain": 1700
            }


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    from src.position.position_manager import Position

    partial_manager = PartialProfits()

    # Create test position
    position = Position(
        token_address="TEST123",
        symbol="TEST",
        entry_price=0.001,
        size_sol=0.1
    )

    # Test 1: Below triggers
    position.update_price(0.0012)  # +20%
    result1 = partial_manager.check_partials(position)
    print(f"\nAt +20%: Should sell={result1['should_sell']}, Reason={result1['reason']}")

    # Test 2: +50% (breakeven)
    position.update_price(0.0015)  # +50%
    result2 = partial_manager.check_partials(position)
    print(f"\nAt +50%: Should sell={result2['should_sell']}, Sell {result2['sell_pct']}%")

    # Mark as taken
    position.take_partial(result2["sell_pct"], 0.0015, result2["partial_name"])

    # Test 3: +500%
    position.update_price(0.006)  # +500%
    result3 = partial_manager.check_partials(position)
    print(f"\nAt +500%: Should sell={result3['should_sell']}, Sell {result3['sell_pct']}%")

    # Mark as taken
    position.take_partial(result3["sell_pct"], 0.006, result3["partial_name"])

    # Test 4: +1000%
    position.update_price(0.011)  # +1000%
    result4 = partial_manager.check_partials(position)
    print(f"\nAt +1000%: Should sell={result4['should_sell']}, Sell {result4['sell_pct']}%")

    # Mark as taken
    position.take_partial(result4["sell_pct"], 0.011, result4["partial_name"])

    # Get moon bag info
    moon_info = partial_manager.get_remaining_target(position)
    print(f"\nMoon bag: {moon_info['remaining_pct']:.1f}% remaining")
    print(f"Partials taken: {moon_info['partials_taken']}")
    print(f"Target: +{moon_info['target_gain']}%")
