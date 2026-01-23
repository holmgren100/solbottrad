"""
RSI (Relative Strength Index) Calculator

RSI measures momentum on a scale of 0-100.

Sweet Spot: 40-70
- Below 40: Oversold (wait)
- 40-70: Ideal entry zone
- Above 70: Approaching overbought
- Above 80: Overbought (FOMO blocker)

Scoring (20 points max):
- RSI in sweet spot (40-70): +10 points
- RSI is rising: +10 points
"""

import logging
from typing import List, Dict, Optional

from config.parameters import (
    RSI_PERIOD,
    RSI_MIN_SWEET_SPOT,
    RSI_MAX_SWEET_SPOT,
    RSI_SWEET_SPOT_POINTS,
    RSI_RISING_POINTS,
    FOMO_RSI_OVERBOUGHT
)

logger = logging.getLogger(__name__)


class RSICalculator:
    """
    RSI indicator calculator for momentum confirmation.

    RSI helps identify:
    - Entry zone (40-70)
    - Overbought conditions (>80 = FOMO)
    - Momentum direction (rising/falling)
    """

    def __init__(self, period: int = RSI_PERIOD):
        """
        Initialize RSI calculator.

        Args:
            period: RSI period (default: 14)
        """
        self.period = period

        logger.debug(f"RSI initialized: period={period}")

    def calculate(self, prices: List[float]) -> Optional[Dict]:
        """
        Calculate RSI.

        Args:
            prices: List of closing prices (most recent last)

        Returns:
            {
                "rsi": float,  # Current RSI value (0-100)
                "is_oversold": bool,  # RSI < 30
                "is_overbought": bool,  # RSI > 70
                "in_sweet_spot": bool,  # 40 <= RSI <= 70
                "is_rising": bool,  # RSI rising from previous
                "rsi_line": List[float],  # Full RSI line
            }
            or None if insufficient data
        """
        try:
            # Need at least period + 1 prices
            if len(prices) < self.period + 1:
                logger.warning(
                    f"Insufficient data for RSI: {len(prices)} < {self.period + 1}"
                )
                return None

            # Calculate price changes
            changes = []
            for i in range(1, len(prices)):
                change = prices[i] - prices[i - 1]
                changes.append(change)

            # Separate gains and losses
            gains = [max(change, 0) for change in changes]
            losses = [abs(min(change, 0)) for change in changes]

            # Calculate RSI line
            rsi_line = []

            # First RSI uses simple average
            avg_gain = sum(gains[:self.period]) / self.period
            avg_loss = sum(losses[:self.period]) / self.period

            # Avoid division by zero
            if avg_loss == 0:
                rsi = 100
            else:
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))

            rsi_line.append(rsi)

            # Subsequent RSI uses smoothed average
            for i in range(self.period, len(changes)):
                avg_gain = (avg_gain * (self.period - 1) + gains[i]) / self.period
                avg_loss = (avg_loss * (self.period - 1) + losses[i]) / self.period

                if avg_loss == 0:
                    rsi = 100
                else:
                    rs = avg_gain / avg_loss
                    rsi = 100 - (100 / (1 + rs))

                rsi_line.append(rsi)

            # Get current RSI
            current_rsi = rsi_line[-1]

            # Check conditions
            is_oversold = current_rsi < 30
            is_overbought = current_rsi > 70
            in_sweet_spot = RSI_MIN_SWEET_SPOT <= current_rsi <= RSI_MAX_SWEET_SPOT

            # Check if rising (compare to previous RSI)
            is_rising = len(rsi_line) >= 2 and rsi_line[-1] > rsi_line[-2]

            result = {
                "rsi": current_rsi,
                "is_oversold": is_oversold,
                "is_overbought": is_overbought,
                "in_sweet_spot": in_sweet_spot,
                "is_rising": is_rising,
                "rsi_line": rsi_line,
            }

            logger.debug(
                f"RSI: {current_rsi:.2f} "
                f"({'OVERSOLD' if is_oversold else 'OVERBOUGHT' if is_overbought else 'SWEET SPOT' if in_sweet_spot else 'NORMAL'}, "
                f"{'RISING' if is_rising else 'FALLING'})"
            )

            return result

        except Exception as e:
            logger.error(f"Error calculating RSI: {e}")
            return None

    def check_divergence(
        self,
        prices: List[float],
        rsi_values: List[float],
        lookback: int = 5
    ) -> bool:
        """
        Check for bearish RSI divergence.

        Bearish divergence = price making higher highs but RSI making lower highs
        This signals weakening momentum.

        Args:
            prices: List of prices
            rsi_values: List of RSI values
            lookback: Candles to look back

        Returns:
            True if bearish divergence detected
        """
        try:
            if len(prices) < lookback or len(rsi_values) < lookback:
                return False

            recent_prices = prices[-lookback:]
            recent_rsi = rsi_values[-lookback:]

            # Find peaks in prices
            price_peaks = []
            for i in range(1, len(recent_prices) - 1):
                if recent_prices[i] > recent_prices[i-1] and recent_prices[i] > recent_prices[i+1]:
                    price_peaks.append((i, recent_prices[i]))

            # Find peaks in RSI
            rsi_peaks = []
            for i in range(1, len(recent_rsi) - 1):
                if recent_rsi[i] > recent_rsi[i-1] and recent_rsi[i] > recent_rsi[i+1]:
                    rsi_peaks.append((i, recent_rsi[i]))

            # Need at least 2 peaks to compare
            if len(price_peaks) < 2 or len(rsi_peaks) < 2:
                return False

            # Check if price peaks are rising but RSI peaks are falling
            price_trend = price_peaks[-1][1] > price_peaks[-2][1]  # Higher high
            rsi_trend = rsi_peaks[-1][1] < rsi_peaks[-2][1]  # Lower high

            divergence = price_trend and rsi_trend

            if divergence:
                logger.warning("⚠️ Bearish RSI divergence detected!")

            return divergence

        except Exception as e:
            logger.error(f"Error checking divergence: {e}")
            return False

    def calculate_score(self, prices: List[float]) -> Dict:
        """
        Calculate RSI momentum score (0-20 points).

        Scoring:
        - RSI in sweet spot (40-70): +10 points
        - RSI is rising: +10 points

        Args:
            prices: List of closing prices

        Returns:
            {
                "score": int,  # 0-20 points
                "signals": List[str],  # Positive signals
                "rsi_data": Dict  # Full RSI calculation
            }
        """
        score = 0
        signals = []

        # Calculate RSI
        rsi_data = self.calculate(prices)

        if not rsi_data:
            return {
                "score": 0,
                "signals": ["INSUFFICIENT DATA"],
                "rsi_data": None
            }

        # Check sweet spot
        if rsi_data["in_sweet_spot"]:
            score += RSI_SWEET_SPOT_POINTS
            signals.append(
                f"RSI in sweet spot ({rsi_data['rsi']:.1f}) (+{RSI_SWEET_SPOT_POINTS} pts)"
            )

        # Check rising
        if rsi_data["is_rising"]:
            score += RSI_RISING_POINTS
            signals.append(f"RSI rising (+{RSI_RISING_POINTS} pts)")

        # Warnings
        if rsi_data["is_oversold"]:
            signals.append(f"⚠️ RSI oversold ({rsi_data['rsi']:.1f})")
        elif rsi_data["rsi"] > FOMO_RSI_OVERBOUGHT:
            signals.append(f"⚠️ RSI overbought ({rsi_data['rsi']:.1f}) - FOMO RISK!")

        result = {
            "score": score,
            "signals": signals,
            "rsi_data": rsi_data
        }

        logger.info(
            f"RSI Score: {score}/20 points - {', '.join(signals) if signals else 'No signals'}"
        )

        return result


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    calculator = RSICalculator()

    # Test with sample price data (simulating uptrend with momentum)
    prices = [
        100, 102, 101, 103, 105, 104, 106, 108, 107, 109,  # 10
        111, 110, 112, 114, 113, 115, 117, 116, 118, 120,  # 20
        119, 121, 123, 122, 124, 126, 125, 127, 129, 128,  # 30
        130, 132, 131, 133, 135, 134, 136, 138, 137, 139,  # 40
        141, 140, 142, 144, 143, 145, 147, 146, 148, 150   # 50
    ]

    # Calculate RSI
    result = calculator.calculate(prices)
    print(f"RSI Result: {result}")

    # Calculate score
    score_result = calculator.calculate_score(prices)
    print(f"\nScore Result: {score_result}")
    print(f"RSI Score: {score_result['score']}/20 points")
    print(f"Signals: {score_result['signals']}")

    # Test divergence
    if result and result["rsi_line"]:
        divergence = calculator.check_divergence(prices, result["rsi_line"])
        print(f"\nBearish Divergence: {divergence}")
