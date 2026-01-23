"""
Trend Confirmation Strategy

Validates that price is in an uptrend before entering.
Prevents entries during downtrends or sideways movement.

Checks:
- Price above 1-min trendline
- Making higher highs and higher lows
- At least 2 green candles in recent history
- Volume increasing with price
"""

import logging
from typing import Dict, List
import numpy as np

from config.parameters import (
    TREND_MIN_GREEN_CANDLES,
    TREND_HIGHER_HIGHS_REQUIRED,
    TREND_HIGHER_LOWS_REQUIRED,
    TREND_VOLUME_INCREASING
)

logger = logging.getLogger(__name__)


class TrendConfirmation:
    """
    Trend confirmation strategy.

    Ensures we're trading WITH the trend, not against it.
    """

    def __init__(self):
        """Initialize trend confirmation strategy."""
        logger.debug("Trend Confirmation initialized")

    def calculate_trendline(self, prices: List[float], lookback: int = 10) -> Dict:
        """
        Calculate simple linear trendline.

        Args:
            prices: List of prices
            lookback: Number of candles for trendline

        Returns:
            {
                "slope": float,  # Trendline slope (positive = uptrend)
                "intercept": float,
                "current_trend_price": float,  # Expected price from trendline
                "above_trend": bool  # Is current price above trendline?
            }
        """
        try:
            if len(prices) < lookback:
                lookback = len(prices)

            if lookback < 2:
                return {
                    "slope": 0,
                    "intercept": 0,
                    "current_trend_price": 0,
                    "above_trend": False
                }

            recent_prices = prices[-lookback:]
            x = np.arange(len(recent_prices))

            # Linear regression: y = mx + b
            slope, intercept = np.polyfit(x, recent_prices, 1)

            # Calculate expected price at current position
            current_x = len(recent_prices) - 1
            current_trend_price = slope * current_x + intercept

            # Check if current price is above trendline
            current_price = recent_prices[-1]
            above_trend = current_price > current_trend_price

            result = {
                "slope": float(slope),
                "intercept": float(intercept),
                "current_trend_price": float(current_trend_price),
                "above_trend": above_trend
            }

            logger.debug(
                f"Trendline: slope={slope:.4f}, "
                f"price={current_price:.4f}, "
                f"trend={current_trend_price:.4f}, "
                f"above={above_trend}"
            )

            return result

        except Exception as e:
            logger.error(f"Error calculating trendline: {e}")
            return {
                "slope": 0,
                "intercept": 0,
                "current_trend_price": 0,
                "above_trend": False
            }

    def check_higher_highs_lows(self, candles: List[Dict], lookback: int = 5) -> Dict:
        """
        Check if price is making higher highs and higher lows.

        Args:
            candles: List of candle dicts
            lookback: Number of candles to check

        Returns:
            {
                "higher_highs": bool,
                "higher_lows": bool,
                "recent_highs": List[float],
                "recent_lows": List[float]
            }
        """
        try:
            if len(candles) < lookback:
                lookback = len(candles)

            if lookback < 2:
                return {
                    "higher_highs": False,
                    "higher_lows": False,
                    "recent_highs": [],
                    "recent_lows": []
                }

            recent = candles[-lookback:]

            highs = [c["high"] for c in recent]
            lows = [c["low"] for c in recent]

            # Check if highs are generally increasing
            higher_highs = highs[-1] > highs[0]

            # Check if lows are generally increasing
            higher_lows = lows[-1] > lows[0]

            result = {
                "higher_highs": higher_highs,
                "higher_lows": higher_lows,
                "recent_highs": highs,
                "recent_lows": lows
            }

            logger.debug(
                f"HH/HL check: higher_highs={higher_highs}, higher_lows={higher_lows}"
            )

            return result

        except Exception as e:
            logger.error(f"Error checking higher highs/lows: {e}")
            return {
                "higher_highs": False,
                "higher_lows": False,
                "recent_highs": [],
                "recent_lows": []
            }

    def count_green_candles(self, candles: List[Dict], lookback: int = 5) -> Dict:
        """
        Count green candles in recent history.

        Args:
            candles: List of candle dicts
            lookback: Number of candles to check

        Returns:
            {
                "green_count": int,
                "red_count": int,
                "green_pct": float,
                "enough_green": bool
            }
        """
        try:
            if len(candles) < lookback:
                lookback = len(candles)

            if lookback == 0:
                return {
                    "green_count": 0,
                    "red_count": 0,
                    "green_pct": 0.0,
                    "enough_green": False
                }

            recent = candles[-lookback:]

            green_count = sum(1 for c in recent if c["close"] > c["open"])
            red_count = len(recent) - green_count
            green_pct = (green_count / len(recent)) * 100

            enough_green = green_count >= TREND_MIN_GREEN_CANDLES

            result = {
                "green_count": green_count,
                "red_count": red_count,
                "green_pct": green_pct,
                "enough_green": enough_green
            }

            logger.debug(
                f"Green candles: {green_count}/{len(recent)} ({green_pct:.1f}%)"
            )

            return result

        except Exception as e:
            logger.error(f"Error counting green candles: {e}")
            return {
                "green_count": 0,
                "red_count": 0,
                "green_pct": 0.0,
                "enough_green": False
            }

    def check_trend(self, token_data: Dict) -> Dict:
        """
        Comprehensive trend confirmation check.

        Args:
            token_data: Dict containing:
                {
                    "prices": List[float],
                    "candles": List[Dict],
                    "volumes": List[float]  # Optional
                }

        Returns:
            {
                "confirmed": bool,  # True if trend confirmed
                "direction": str,  # "UP", "DOWN", "SIDEWAYS"
                "strength": str,  # "STRONG", "MODERATE", "WEAK"
                "signals": List[str],  # Positive signals
                "warnings": List[str]  # Warning signals
            }
        """
        try:
            prices = token_data.get("prices", [])
            candles = token_data.get("candles", [])
            volumes = token_data.get("volumes", [])

            signals = []
            warnings = []
            strength_score = 0  # 0-4 points

            # 1. Check trendline
            trendline = self.calculate_trendline(prices)
            if trendline["above_trend"]:
                signals.append("Price above trendline")
                strength_score += 1
            else:
                warnings.append("Price below trendline")

            # Determine direction from slope
            if trendline["slope"] > 0:
                direction = "UP"
                signals.append("Uptrend detected")
                strength_score += 1
            elif trendline["slope"] < 0:
                direction = "DOWN"
                warnings.append("Downtrend detected")
            else:
                direction = "SIDEWAYS"
                warnings.append("Sideways movement")

            # 2. Check higher highs/lows
            if TREND_HIGHER_HIGHS_REQUIRED or TREND_HIGHER_LOWS_REQUIRED:
                hh_hl = self.check_higher_highs_lows(candles)

                if TREND_HIGHER_HIGHS_REQUIRED and hh_hl["higher_highs"]:
                    signals.append("Making higher highs")
                    strength_score += 1
                elif TREND_HIGHER_HIGHS_REQUIRED:
                    warnings.append("Not making higher highs")

                if TREND_HIGHER_LOWS_REQUIRED and hh_hl["higher_lows"]:
                    signals.append("Making higher lows")
                    strength_score += 1
                elif TREND_HIGHER_LOWS_REQUIRED:
                    warnings.append("Not making higher lows")

            # 3. Check green candles
            green_check = self.count_green_candles(candles)
            if green_check["enough_green"]:
                signals.append(f"{green_check['green_count']} green candles")
            else:
                warnings.append(f"Only {green_check['green_count']} green candles (need {TREND_MIN_GREEN_CANDLES})")

            # 4. Check volume trend (if available)
            if TREND_VOLUME_INCREASING and len(volumes) >= 2:
                volume_increasing = volumes[-1] > volumes[0]
                if volume_increasing:
                    signals.append("Volume increasing")
                else:
                    warnings.append("Volume not increasing")

            # Determine strength
            if strength_score >= 3:
                strength = "STRONG"
            elif strength_score >= 2:
                strength = "MODERATE"
            else:
                strength = "WEAK"

            # Confirm trend if:
            # - Direction is UP
            # - Above trendline
            # - Enough green candles
            # - At least MODERATE strength
            confirmed = (
                direction == "UP" and
                trendline["above_trend"] and
                green_check["enough_green"] and
                strength in ["STRONG", "MODERATE"]
            )

            result = {
                "confirmed": confirmed,
                "direction": direction,
                "strength": strength,
                "signals": signals,
                "warnings": warnings
            }

            if confirmed:
                logger.info(f"✅ Trend CONFIRMED: {direction} ({strength})")
                logger.info(f"   Signals: {', '.join(signals)}")
            else:
                logger.warning(f"⚠️ Trend NOT confirmed: {direction} ({strength})")
                logger.warning(f"   Warnings: {', '.join(warnings)}")

            return result

        except Exception as e:
            logger.error(f"Error checking trend: {e}")
            return {
                "confirmed": False,
                "direction": "UNKNOWN",
                "strength": "WEAK",
                "signals": [],
                "warnings": [f"Error: {e}"]
            }


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    strategy = TrendConfirmation()

    # Test with uptrend data
    prices = [100, 102, 105, 107, 110, 112, 115, 118, 120, 123]

    candles = []
    for i in range(len(prices) - 1):
        candles.append({
            "open": prices[i],
            "close": prices[i + 1],
            "high": max(prices[i], prices[i + 1]) + 1,
            "low": min(prices[i], prices[i + 1]) - 1
        })

    volumes = [1000, 1200, 1500, 1800, 2000, 2200, 2500, 2800, 3000, 3200]

    token_data = {
        "prices": prices,
        "candles": candles,
        "volumes": volumes
    }

    result = strategy.check_trend(token_data)

    print(f"\nTrend Confirmation:")
    print(f"Confirmed: {result['confirmed']}")
    print(f"Direction: {result['direction']}")
    print(f"Strength: {result['strength']}")
    print(f"\nSignals:")
    for signal in result['signals']:
        print(f"  ✅ {signal}")
    print(f"\nWarnings:")
    for warning in result['warnings']:
        print(f"  ⚠️ {warning}")
