"""
Pyramid Manager - Add to Winning Positions

Pyramiding = Adding to winning positions when momentum continues.

Stage 1 (+150% profit):
- Add 30% of initial position size
- Condition: Momentum still strong (MACD histogram growing)
- Only trigger ONCE

Stage 2 (+300% profit):
- Add 20% of initial position size
- Condition: Momentum accelerating (MACD + Volume both up)
- Only trigger ONCE

This is how we maximize big winners!
"""

import logging
from typing import Dict

from src.indicators.macd import MACDCalculator
from src.indicators.volume import VolumeAnalyzer
from config.parameters import (
    PYRAMID_1_TRIGGER,
    PYRAMID_1_SIZE,
    PYRAMID_2_TRIGGER,
    PYRAMID_2_SIZE
)

logger = logging.getLogger(__name__)


class PyramidManager:
    """
    Manages pyramiding logic for winning positions.

    Adds to positions when momentum continues strong.
    """

    def __init__(self):
        """Initialize pyramid manager."""
        self.macd_calculator = MACDCalculator()
        self.volume_analyzer = VolumeAnalyzer()

        logger.info(
            f"Pyramid Manager initialized: "
            f"Stage 1: +{PYRAMID_1_TRIGGER}% ({PYRAMID_1_SIZE}%), "
            f"Stage 2: +{PYRAMID_2_TRIGGER}% ({PYRAMID_2_SIZE}%)"
        )

    def _momentum_still_strong(self, token_data: Dict) -> bool:
        """
        Check if momentum is still strong for pyramid stage 1.

        Conditions:
        - MACD histogram > 0
        - MACD histogram growing

        Args:
            token_data: Dict with 'prices'

        Returns:
            True if momentum is strong
        """
        try:
            prices = token_data.get("prices", [])
            if len(prices) < 30:  # Need enough data for MACD
                logger.debug("Not enough data for MACD check")
                return False

            macd_result = self.macd_calculator.calculate(prices)
            if not macd_result:
                return False

            is_positive = macd_result["is_positive"]
            is_growing = macd_result["is_growing"]

            strong = is_positive and is_growing

            logger.debug(
                f"Momentum check: positive={is_positive}, growing={is_growing}, strong={strong}"
            )

            return strong

        except Exception as e:
            logger.error(f"Error checking momentum: {e}")
            return False

    def _momentum_accelerating(self, token_data: Dict) -> bool:
        """
        Check if momentum is accelerating for pyramid stage 2.

        Conditions:
        - MACD histogram increasing
        - Volume velocity still >= 2.0x

        Args:
            token_data: Dict with 'prices', 'vol_1m', 'vol_5m'

        Returns:
            True if momentum is accelerating
        """
        try:
            prices = token_data.get("prices", [])
            vol_1m = token_data.get("vol_1m", 0)
            vol_5m = token_data.get("vol_5m", 0)

            if len(prices) < 30:
                return False

            # Check MACD histogram increasing
            macd_result = self.macd_calculator.calculate(prices)
            if not macd_result:
                return False

            macd_increasing = macd_result["is_growing"]

            # Check volume still strong
            velocity = self.volume_analyzer.calculate_velocity(vol_1m, vol_5m)
            volume_strong = velocity >= 2.0  # At least 2x average

            accelerating = macd_increasing and volume_strong

            logger.debug(
                f"Acceleration check: macd_increasing={macd_increasing}, "
                f"volume_strong={volume_strong} ({velocity:.1f}x), "
                f"accelerating={accelerating}"
            )

            return accelerating

        except Exception as e:
            logger.error(f"Error checking acceleration: {e}")
            return False

    def check_pyramid(self, position, token_data: Dict) -> Dict:
        """
        Check if position should pyramid.

        Args:
            position: Position object
            token_data: Token data with prices and volume

        Returns:
            {
                "should_add": bool,
                "stage": int,  # 1 or 2
                "size_sol": float,
                "size_percent": float,
                "reason": str
            }
        """
        try:
            # Check Stage 1: +150%
            if (not position.pyramid_1_triggered and
                position.pnl_percent >= PYRAMID_1_TRIGGER):

                # Check momentum
                if self._momentum_still_strong(token_data):
                    add_size = position.initial_size_sol * (PYRAMID_1_SIZE / 100)

                    logger.info(
                        f"🔺 PYRAMID STAGE 1: {position.symbol} at +{position.pnl_percent:.1f}%"
                    )
                    logger.info(
                        f"   Add {PYRAMID_1_SIZE}% ({add_size:.4f} SOL) - momentum still strong!"
                    )

                    return {
                        "should_add": True,
                        "stage": 1,
                        "size_sol": add_size,
                        "size_percent": PYRAMID_1_SIZE,
                        "reason": f"Stage 1: +{position.pnl_percent:.1f}%, momentum strong"
                    }
                else:
                    logger.debug(
                        f"Pyramid 1 trigger reached but momentum not strong"
                    )
                    return {
                        "should_add": False,
                        "stage": 1,
                        "size_sol": 0,
                        "size_percent": 0,
                        "reason": "Momentum not strong enough"
                    }

            # Check Stage 2: +300%
            if (not position.pyramid_2_triggered and
                position.pnl_percent >= PYRAMID_2_TRIGGER):

                # Check momentum accelerating
                if self._momentum_accelerating(token_data):
                    add_size = position.initial_size_sol * (PYRAMID_2_SIZE / 100)

                    logger.info(
                        f"🔺🔺 PYRAMID STAGE 2: {position.symbol} at +{position.pnl_percent:.1f}%"
                    )
                    logger.info(
                        f"   Add {PYRAMID_2_SIZE}% ({add_size:.4f} SOL) - momentum accelerating!"
                    )

                    return {
                        "should_add": True,
                        "stage": 2,
                        "size_sol": add_size,
                        "size_percent": PYRAMID_2_SIZE,
                        "reason": f"Stage 2: +{position.pnl_percent:.1f}%, momentum accelerating"
                    }
                else:
                    logger.debug(
                        f"Pyramid 2 trigger reached but momentum not accelerating"
                    )
                    return {
                        "should_add": False,
                        "stage": 2,
                        "size_sol": 0,
                        "size_percent": 0,
                        "reason": "Momentum not accelerating"
                    }

            # No pyramid trigger
            return {
                "should_add": False,
                "stage": 0,
                "size_sol": 0,
                "size_percent": 0,
                "reason": f"Profit {position.pnl_percent:.1f}% below pyramid triggers"
            }

        except Exception as e:
            logger.error(f"Error in pyramid check: {e}")
            return {
                "should_add": False,
                "stage": 0,
                "size_sol": 0,
                "size_percent": 0,
                "reason": f"Error: {e}"
            }


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    from src.position.position_manager import Position

    manager = PyramidManager()

    # Create test position
    position = Position(
        token_address="TEST123",
        symbol="TEST",
        entry_price=0.001,
        size_sol=0.1
    )

    # Test data with strong momentum
    test_data = {
        "prices": [100 + i for i in range(50)],  # Uptrend
        "vol_1m": 50000,
        "vol_5m": 50000,
    }

    # Test 1: Below pyramid 1 trigger
    position.update_price(0.0012)  # +20%
    result1 = manager.check_pyramid(position, test_data)
    print(f"\nAt +20%: Should add={result1['should_add']}, Reason={result1['reason']}")

    # Test 2: Pyramid 1 trigger
    position.update_price(0.0025)  # +150%
    result2 = manager.check_pyramid(position, test_data)
    print(f"\nAt +150%: Should add={result2['should_add']}, Stage={result2['stage']}")
    if result2['should_add']:
        print(f"Add size: {result2['size_sol']:.4f} SOL ({result2['size_percent']}%)")

    # Mark as triggered
    position.pyramid_1_triggered = True

    # Test 3: Pyramid 2 trigger
    position.update_price(0.004)  # +300%
    result3 = manager.check_pyramid(position, test_data)
    print(f"\nAt +300%: Should add={result3['should_add']}, Stage={result3['stage']}")
    if result3['should_add']:
        print(f"Add size: {result3['size_sol']:.4f} SOL ({result3['size_percent']}%)")
