"""
Anti-FOMO Strategy

Prevents entering at the top when everyone else is buying (FOMO).

Blocks entry if:
- RSI > 80 (overbought)
- 4+ consecutive green candles (topping signal)
- Price pumped 15%+ in 1 minute without pullback

Smart money buys the dip. We wait for pullbacks!
"""

import logging
from typing import Dict, List

from config.parameters import (
    FOMO_RSI_OVERBOUGHT,
    FOMO_MAX_CONSECUTIVE_GREEN,
    FOMO_MAX_PUMP_PERCENT
)

logger = logging.getLogger(__name__)


class AntiFOMO:
    """
    Anti-FOMO strategy to prevent buying tops.

    Capital preservation through patience!
    """

    def __init__(self):
        """Initialize anti-FOMO strategy."""
        logger.debug(
            f"Anti-FOMO initialized: "
            f"RSI>{FOMO_RSI_OVERBOUGHT}, "
            f"{FOMO_MAX_CONSECUTIVE_GREEN}+ green candles, "
            f"{FOMO_MAX_PUMP_PERCENT}%+ pump"
        )

    def check_overbought_rsi(self, rsi: float) -> Dict:
        """
        Check if RSI is overbought (FOMO zone).

        Args:
            rsi: Current RSI value

        Returns:
            {
                "is_fomo": bool,
                "rsi": float,
                "threshold": int,
                "reason": str
            }
        """
        is_fomo = rsi > FOMO_RSI_OVERBOUGHT

        result = {
            "is_fomo": is_fomo,
            "rsi": rsi,
            "threshold": FOMO_RSI_OVERBOUGHT,
            "reason": f"RSI overbought ({rsi:.1f} > {FOMO_RSI_OVERBOUGHT})" if is_fomo else ""
        }

        if is_fomo:
            logger.warning(f"⚠️ FOMO ALERT: RSI overbought ({rsi:.1f})")

        return result

    def check_consecutive_green(self, candles: List[Dict]) -> Dict:
        """
        Check for too many consecutive green candles (topping signal).

        Args:
            candles: List of candle dicts

        Returns:
            {
                "is_fomo": bool,
                "consecutive_green": int,
                "max_allowed": int,
                "reason": str
            }
        """
        try:
            if len(candles) == 0:
                return {
                    "is_fomo": False,
                    "consecutive_green": 0,
                    "max_allowed": FOMO_MAX_CONSECUTIVE_GREEN,
                    "reason": ""
                }

            # Count consecutive green candles from the end
            consecutive = 0
            for i in range(len(candles) - 1, -1, -1):
                candle = candles[i]
                if candle["close"] > candle["open"]:
                    consecutive += 1
                else:
                    break

            is_fomo = consecutive >= FOMO_MAX_CONSECUTIVE_GREEN

            result = {
                "is_fomo": is_fomo,
                "consecutive_green": consecutive,
                "max_allowed": FOMO_MAX_CONSECUTIVE_GREEN,
                "reason": f"{consecutive} consecutive green candles (max {FOMO_MAX_CONSECUTIVE_GREEN})" if is_fomo else ""
            }

            if is_fomo:
                logger.warning(f"⚠️ FOMO ALERT: {consecutive} consecutive green candles (topping!)")

            return result

        except Exception as e:
            logger.error(f"Error checking consecutive green: {e}")
            return {
                "is_fomo": False,
                "consecutive_green": 0,
                "max_allowed": FOMO_MAX_CONSECUTIVE_GREEN,
                "reason": f"Error: {e}"
            }

    def check_rapid_pump(self, candles: List[Dict], lookback: int = 1) -> Dict:
        """
        Check for rapid price pump without pullback.

        Args:
            candles: List of candle dicts
            lookback: Number of candles to check (default: 1 minute)

        Returns:
            {
                "is_fomo": bool,
                "pump_percent": float,
                "max_allowed": int,
                "had_pullback": bool,
                "reason": str
            }
        """
        try:
            if len(candles) < lookback + 1:
                return {
                    "is_fomo": False,
                    "pump_percent": 0.0,
                    "max_allowed": FOMO_MAX_PUMP_PERCENT,
                    "had_pullback": False,
                    "reason": ""
                }

            # Get price from N candles ago and current
            start_candle = candles[-(lookback + 1)]
            end_candle = candles[-1]

            start_price = start_candle["close"]
            end_price = end_candle["close"]

            # Calculate pump percentage
            if start_price == 0:
                pump_percent = 0.0
            else:
                pump_percent = ((end_price - start_price) / start_price) * 100

            # Check if there was a pullback (any red candle)
            recent_candles = candles[-lookback:]
            had_pullback = any(c["close"] < c["open"] for c in recent_candles)

            # FOMO if pumped too fast WITHOUT pullback
            is_fomo = pump_percent > FOMO_MAX_PUMP_PERCENT and not had_pullback

            result = {
                "is_fomo": is_fomo,
                "pump_percent": pump_percent,
                "max_allowed": FOMO_MAX_PUMP_PERCENT,
                "had_pullback": had_pullback,
                "reason": f"Rapid pump {pump_percent:.1f}% without pullback" if is_fomo else ""
            }

            if is_fomo:
                logger.warning(f"⚠️ FOMO ALERT: Rapid {pump_percent:.1f}% pump without pullback!")

            return result

        except Exception as e:
            logger.error(f"Error checking rapid pump: {e}")
            return {
                "is_fomo": False,
                "pump_percent": 0.0,
                "max_allowed": FOMO_MAX_PUMP_PERCENT,
                "had_pullback": False,
                "reason": f"Error: {e}"
            }

    def should_wait(self, token_data: Dict) -> Dict:
        """
        Comprehensive FOMO check - should we wait before entering?

        Args:
            token_data: Dict containing:
                {
                    "rsi": float,
                    "candles": List[Dict],
                }

        Returns:
            {
                "wait": bool,  # True if should wait (FOMO detected)
                "reason": str,  # Primary reason to wait
                "wait_for": str,  # What to wait for
                "checks": Dict  # All check results
            }
        """
        try:
            rsi = token_data.get("rsi", 0)
            candles = token_data.get("candles", [])

            # Run all checks
            rsi_check = self.check_overbought_rsi(rsi)
            green_check = self.check_consecutive_green(candles)
            pump_check = self.check_rapid_pump(candles)

            # Collect all FOMO signals
            fomo_reasons = []
            if rsi_check["is_fomo"]:
                fomo_reasons.append(rsi_check["reason"])
            if green_check["is_fomo"]:
                fomo_reasons.append(green_check["reason"])
            if pump_check["is_fomo"]:
                fomo_reasons.append(pump_check["reason"])

            # Should wait if ANY check triggered
            should_wait = len(fomo_reasons) > 0

            # Primary reason (first one)
            primary_reason = fomo_reasons[0] if fomo_reasons else ""

            # What to wait for
            if should_wait:
                wait_for_items = []
                if rsi_check["is_fomo"]:
                    wait_for_items.append(f"RSI < {FOMO_RSI_OVERBOUGHT}")
                if green_check["is_fomo"]:
                    wait_for_items.append("pullback (red candle)")
                if pump_check["is_fomo"]:
                    wait_for_items.append("pullback to reset")

                wait_for = " OR ".join(wait_for_items)
            else:
                wait_for = ""

            result = {
                "wait": should_wait,
                "reason": primary_reason,
                "wait_for": wait_for,
                "checks": {
                    "rsi": rsi_check,
                    "consecutive_green": green_check,
                    "rapid_pump": pump_check
                }
            }

            if should_wait:
                logger.warning(f"🛑 FOMO DETECTED - WAIT!")
                logger.warning(f"   Reason: {primary_reason}")
                logger.warning(f"   Wait for: {wait_for}")
            else:
                logger.info(f"✅ No FOMO - safe to enter")

            return result

        except Exception as e:
            logger.error(f"Error in FOMO check: {e}")
            return {
                "wait": True,  # Be conservative on error
                "reason": f"Error: {e}",
                "wait_for": "Error resolution",
                "checks": {}
            }


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    strategy = AntiFOMO()

    # Test 1: Overbought RSI
    print("Test 1: Overbought RSI")
    token_data1 = {
        "rsi": 85,
        "candles": []
    }
    result1 = strategy.should_wait(token_data1)
    print(f"Wait: {result1['wait']}, Reason: {result1['reason']}\n")

    # Test 2: Too many green candles
    print("Test 2: Consecutive green candles")
    candles2 = [
        {"open": 100, "close": 102},
        {"open": 102, "close": 104},
        {"open": 104, "close": 106},
        {"open": 106, "close": 108},
        {"open": 108, "close": 110},  # 5 consecutive green
    ]
    token_data2 = {
        "rsi": 65,
        "candles": candles2
    }
    result2 = strategy.should_wait(token_data2)
    print(f"Wait: {result2['wait']}, Reason: {result2['reason']}\n")

    # Test 3: Rapid pump without pullback
    print("Test 3: Rapid pump")
    candles3 = [
        {"open": 100, "close": 105},
        {"open": 105, "close": 115},  # 15% pump in 1 candle
    ]
    token_data3 = {
        "rsi": 70,
        "candles": candles3
    }
    result3 = strategy.should_wait(token_data3)
    print(f"Wait: {result3['wait']}, Reason: {result3['reason']}\n")

    # Test 4: Healthy entry (no FOMO)
    print("Test 4: Healthy entry")
    candles4 = [
        {"open": 100, "close": 102},
        {"open": 102, "close": 101},  # Pullback
        {"open": 101, "close": 103},  # Green after pullback
    ]
    token_data4 = {
        "rsi": 60,
        "candles": candles4
    }
    result4 = strategy.should_wait(token_data4)
    print(f"Wait: {result4['wait']}, Reason: {result4['reason']}")
