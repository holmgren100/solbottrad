"""
MACD (Moving Average Convergence Divergence) Calculator

MOST IMPORTANT INDICATOR (40 points in momentum scoring!)

MACD Components:
- Fast EMA (default: 12 periods)
- Slow EMA (default: 26 periods)
- Signal line (default: 9-period EMA of MACD)
- Histogram (MACD - Signal)

Scoring (40 points max):
- Histogram > 0: +20 points
- Histogram growing for 3+ candles: +20 points
"""

import logging
from typing import List, Dict, Optional
import numpy as np

from config.parameters import (
    MACD_FAST_PERIOD,
    MACD_SLOW_PERIOD,
    MACD_SIGNAL_PERIOD,
    MACD_HISTOGRAM_POSITIVE_POINTS,
    MACD_HISTOGRAM_GROWING_POINTS,
    MACD_GROWING_STREAK_MIN
)

logger = logging.getLogger(__name__)


class MACDCalculator:
    """
    MACD indicator calculator for momentum detection.

    The histogram is key:
    - Positive histogram = bullish momentum
    - Growing histogram = accelerating momentum
    """

    def __init__(
        self,
        fast_period: int = MACD_FAST_PERIOD,
        slow_period: int = MACD_SLOW_PERIOD,
        signal_period: int = MACD_SIGNAL_PERIOD
    ):
        """
        Initialize MACD calculator.

        Args:
            fast_period: Fast EMA period (default: 12)
            slow_period: Slow EMA period (default: 26)
            signal_period: Signal line EMA period (default: 9)
        """
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period

        logger.debug(
            f"MACD initialized: fast={fast_period}, slow={slow_period}, signal={signal_period}"
        )

    def calculate_ema(self, prices: List[float], period: int) -> List[float]:
        """
        Calculate Exponential Moving Average.

        Args:
            prices: List of prices
            period: EMA period

        Returns:
            List of EMA values
        """
        if len(prices) < period:
            logger.warning(f"Not enough data for EMA: {len(prices)} < {period}")
            return []

        ema = []
        multiplier = 2 / (period + 1)

        # First EMA is SMA
        sma = sum(prices[:period]) / period
        ema.append(sma)

        # Calculate remaining EMAs
        for i in range(period, len(prices)):
            ema_value = (prices[i] - ema[-1]) * multiplier + ema[-1]
            ema.append(ema_value)

        return ema

    def calculate(self, prices: List[float]) -> Optional[Dict]:
        """
        Calculate MACD, signal line, and histogram.

        Args:
            prices: List of closing prices (most recent last)

        Returns:
            {
                "macd": float,  # Current MACD value
                "signal": float,  # Current signal line
                "histogram": float,  # Current histogram
                "is_positive": bool,  # Is histogram positive?
                "is_growing": bool,  # Is histogram growing?
                "macd_line": List[float],  # Full MACD line
                "signal_line": List[float],  # Full signal line
                "histogram_line": List[float],  # Full histogram
            }
            or None if insufficient data
        """
        try:
            # Need enough data for slow EMA
            min_data = self.slow_period + self.signal_period
            if len(prices) < min_data:
                logger.warning(
                    f"Insufficient data for MACD: {len(prices)} < {min_data}"
                )
                return None

            # Calculate fast and slow EMAs
            fast_ema = self.calculate_ema(prices, self.fast_period)
            slow_ema = self.calculate_ema(prices, self.slow_period)

            # MACD line = fast EMA - slow EMA
            # Align arrays (slow EMA starts later)
            offset = self.slow_period - self.fast_period
            macd_line = []

            for i in range(len(slow_ema)):
                fast_idx = i + offset
                macd_value = fast_ema[fast_idx] - slow_ema[i]
                macd_line.append(macd_value)

            # Signal line = EMA of MACD line
            signal_line = self.calculate_ema(macd_line, self.signal_period)

            # Histogram = MACD - Signal
            # Align arrays again
            histogram_line = []
            offset2 = len(macd_line) - len(signal_line)

            for i in range(len(signal_line)):
                macd_idx = i + offset2
                hist_value = macd_line[macd_idx] - signal_line[i]
                histogram_line.append(hist_value)

            # Get current values (most recent)
            current_macd = macd_line[-1]
            current_signal = signal_line[-1]
            current_histogram = histogram_line[-1]

            # Check if histogram is positive
            is_positive = current_histogram > 0

            # Check if histogram is growing (last 3+ candles)
            is_growing = self.check_growing_streak(
                histogram_line,
                min_candles=MACD_GROWING_STREAK_MIN
            )

            result = {
                "macd": current_macd,
                "signal": current_signal,
                "histogram": current_histogram,
                "is_positive": is_positive,
                "is_growing": is_growing,
                "macd_line": macd_line,
                "signal_line": signal_line,
                "histogram_line": histogram_line,
            }

            logger.debug(
                f"MACD: {current_macd:.6f}, "
                f"Signal: {current_signal:.6f}, "
                f"Histogram: {current_histogram:.6f} "
                f"({'POSITIVE' if is_positive else 'NEGATIVE'}, "
                f"{'GROWING' if is_growing else 'NOT GROWING'})"
            )

            return result

        except Exception as e:
            logger.error(f"Error calculating MACD: {e}")
            return None

    def check_growing_streak(
        self,
        histograms: List[float],
        min_candles: int = MACD_GROWING_STREAK_MIN
    ) -> bool:
        """
        Check if histogram has been growing for minimum candles.

        Args:
            histograms: List of histogram values
            min_candles: Minimum candles for growing streak

        Returns:
            True if histogram growing for min_candles
        """
        try:
            if len(histograms) < min_candles:
                return False

            # Check last N candles
            recent = histograms[-min_candles:]

            # Each candle should be higher than previous
            for i in range(1, len(recent)):
                if recent[i] <= recent[i - 1]:
                    return False

            logger.debug(f"Histogram growing for {min_candles} candles!")
            return True

        except Exception as e:
            logger.error(f"Error checking growing streak: {e}")
            return False

    def calculate_score(self, prices: List[float]) -> Dict:
        """
        Calculate MACD momentum score (0-40 points).

        Scoring:
        - Histogram > 0: +20 points
        - Histogram growing 3+ candles: +20 points

        Args:
            prices: List of closing prices

        Returns:
            {
                "score": int,  # 0-40 points
                "signals": List[str],  # Positive signals
                "macd_data": Dict  # Full MACD calculation
            }
        """
        score = 0
        signals = []

        # Calculate MACD
        macd_data = self.calculate(prices)

        if not macd_data:
            return {
                "score": 0,
                "signals": ["INSUFFICIENT DATA"],
                "macd_data": None
            }

        # Check histogram positive
        if macd_data["is_positive"]:
            score += MACD_HISTOGRAM_POSITIVE_POINTS
            signals.append(f"Histogram POSITIVE (+{MACD_HISTOGRAM_POSITIVE_POINTS} pts)")

        # Check histogram growing
        if macd_data["is_growing"]:
            score += MACD_HISTOGRAM_GROWING_POINTS
            signals.append(f"Histogram GROWING (+{MACD_HISTOGRAM_GROWING_POINTS} pts)")

        result = {
            "score": score,
            "signals": signals,
            "macd_data": macd_data
        }

        logger.info(f"MACD Score: {score}/40 points - {', '.join(signals) if signals else 'No signals'}")

        return result


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    calculator = MACDCalculator()

    # Test with sample price data (simulating uptrend)
    prices = [
        100, 102, 101, 103, 105, 104, 106, 108, 107, 109,  # 10
        111, 110, 112, 114, 113, 115, 117, 116, 118, 120,  # 20
        119, 121, 123, 122, 124, 126, 125, 127, 129, 128,  # 30
        130, 132, 131, 133, 135, 134, 136, 138, 137, 139,  # 40
        141, 140, 142, 144, 143, 145, 147, 146, 148, 150   # 50
    ]

    # Calculate MACD
    result = calculator.calculate(prices)
    print(f"MACD Result: {result}")

    # Calculate score
    score_result = calculator.calculate_score(prices)
    print(f"\nScore Result: {score_result}")
    print(f"MACD Score: {score_result['score']}/40 points")
    print(f"Signals: {score_result['signals']}")
