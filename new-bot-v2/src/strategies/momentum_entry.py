"""
Momentum Entry Strategy - 80-Point Scorer

Combines all indicators to detect 500-1700% momentum runners.

Scoring System (need 80/100 points):
- MACD (40 points max):
  * Histogram > 0: +20 pts
  * Histogram growing 3+ candles: +20 pts

- Volume (30 points max):
  * Velocity >= 4.0 (400% spike): +30 pts

- RSI (20 points max):
  * RSI in sweet spot (40-70): +10 pts
  * RSI rising: +10 pts

- Pullback (10 points max):
  * 1-2 red candles before green: +10 pts

TOTAL >= 80 → Pattern matches! Enter trade!
"""

import logging
from typing import Dict, List, Optional

from src.indicators.macd import MACDCalculator
from src.indicators.rsi import RSICalculator
from src.indicators.volume import VolumeAnalyzer
from config.parameters import (
    MOMENTUM_SCORE_THRESHOLD,
    PULLBACK_RED_CANDLES_MIN,
    PULLBACK_RED_CANDLES_MAX,
    PULLBACK_POINTS
)

logger = logging.getLogger(__name__)


class MomentumEntry:
    """
    Momentum entry strategy using technical indicators.

    This is the heart of the bot - the pattern detector!
    """

    def __init__(self):
        """Initialize momentum entry strategy."""
        self.macd_calculator = MACDCalculator()
        self.rsi_calculator = RSICalculator()
        self.volume_analyzer = VolumeAnalyzer()

        logger.info(
            f"Momentum Entry initialized - need {MOMENTUM_SCORE_THRESHOLD}/100 points to enter"
        )

    def check_pullback(self, candles: List[Dict]) -> Dict:
        """
        Check for pullback pattern (1-2 red candles before current green).

        A pullback confirms "buying the dip" - smart money entering.

        Args:
            candles: List of candle dicts with {open, close, ...}

        Returns:
            {
                "has_pullback": bool,
                "red_candles": int,
                "points": int,
                "signal": str
            }
        """
        try:
            if len(candles) < 3:
                return {
                    "has_pullback": False,
                    "red_candles": 0,
                    "points": 0,
                    "signal": "Not enough candles"
                }

            # Check if current candle is green
            current = candles[-1]
            current_green = current["close"] > current["open"]

            if not current_green:
                return {
                    "has_pullback": False,
                    "red_candles": 0,
                    "points": 0,
                    "signal": "Current candle not green"
                }

            # Count recent red candles before current
            red_count = 0
            for i in range(len(candles) - 2, max(len(candles) - 4, -1), -1):
                candle = candles[i]
                is_red = candle["close"] < candle["open"]

                if is_red:
                    red_count += 1
                else:
                    break  # Stop at first green candle

            # Valid pullback = 1-2 red candles
            has_pullback = PULLBACK_RED_CANDLES_MIN <= red_count <= PULLBACK_RED_CANDLES_MAX

            result = {
                "has_pullback": has_pullback,
                "red_candles": red_count,
                "points": PULLBACK_POINTS if has_pullback else 0,
                "signal": f"Pullback {red_count} red candles" if has_pullback else f"{red_count} red candles (need {PULLBACK_RED_CANDLES_MIN}-{PULLBACK_RED_CANDLES_MAX})"
            }

            if has_pullback:
                logger.debug(f"✅ Pullback detected: {red_count} red candles (+{PULLBACK_POINTS} pts)")

            return result

        except Exception as e:
            logger.error(f"Error checking pullback: {e}")
            return {
                "has_pullback": False,
                "red_candles": 0,
                "points": 0,
                "signal": f"Error: {e}"
            }

    def check_pattern(self, token_data: Dict) -> Dict:
        """
        Check if token matches momentum pattern.

        This is the main entry decision function!

        Args:
            token_data: Dict containing:
                {
                    "prices": List[float],  # Closing prices
                    "candles": List[Dict],  # Full candle data
                    "vol_1m": float,
                    "vol_5m": float,
                }

        Returns:
            {
                "match": bool,  # True if score >= threshold
                "score": int,  # Total score (0-100)
                "threshold": int,  # Threshold needed
                "signals": List[str],  # All positive signals
                "reasons": List[str],  # Why entered/rejected
                "breakdown": {  # Score breakdown
                    "macd": int,
                    "volume": int,
                    "rsi": int,
                    "pullback": int
                }
            }
        """
        try:
            prices = token_data.get("prices", [])
            candles = token_data.get("candles", [])
            vol_1m = token_data.get("vol_1m", 0)
            vol_5m = token_data.get("vol_5m", 0)

            total_score = 0
            all_signals = []
            breakdown = {
                "macd": 0,
                "volume": 0,
                "rsi": 0,
                "pullback": 0
            }

            # A) MACD Score (40 points max)
            macd_result = self.macd_calculator.calculate_score(prices)
            breakdown["macd"] = macd_result["score"]
            total_score += macd_result["score"]
            all_signals.extend(macd_result["signals"])

            # B) Volume Score (30 points max)
            volume_result = self.volume_analyzer.calculate_score(vol_1m, vol_5m)
            breakdown["volume"] = volume_result["score"]
            total_score += volume_result["score"]
            all_signals.extend(volume_result["signals"])

            # C) RSI Score (20 points max)
            rsi_result = self.rsi_calculator.calculate_score(prices)
            breakdown["rsi"] = rsi_result["score"]
            total_score += rsi_result["score"]
            all_signals.extend(rsi_result["signals"])

            # D) Pullback Score (10 points max)
            pullback_result = self.check_pullback(candles)
            breakdown["pullback"] = pullback_result["points"]
            total_score += pullback_result["points"]
            all_signals.append(pullback_result["signal"])

            # Check if pattern matches
            pattern_match = total_score >= MOMENTUM_SCORE_THRESHOLD

            # Build reasons
            reasons = []
            if pattern_match:
                reasons.append(f"✅ MOMENTUM PATTERN DETECTED! Score: {total_score}/{MOMENTUM_SCORE_THRESHOLD}")
                reasons.append(f"Breakdown: MACD={breakdown['macd']}, Volume={breakdown['volume']}, RSI={breakdown['rsi']}, Pullback={breakdown['pullback']}")
            else:
                reasons.append(f"❌ Score too low: {total_score}/{MOMENTUM_SCORE_THRESHOLD}")
                missing = MOMENTUM_SCORE_THRESHOLD - total_score
                reasons.append(f"Need {missing} more points")

            result = {
                "match": pattern_match,
                "score": total_score,
                "threshold": MOMENTUM_SCORE_THRESHOLD,
                "signals": all_signals,
                "reasons": reasons,
                "breakdown": breakdown
            }

            # Log result
            if pattern_match:
                logger.info(f"🚀 MOMENTUM PATTERN MATCH! Score: {total_score}/100")
                logger.info(f"   MACD: {breakdown['macd']}, Volume: {breakdown['volume']}, RSI: {breakdown['rsi']}, Pullback: {breakdown['pullback']}")
            else:
                logger.info(f"📊 Pattern check: {total_score}/100 (need {MOMENTUM_SCORE_THRESHOLD})")

            return result

        except Exception as e:
            logger.error(f"Error checking pattern: {e}")
            return {
                "match": False,
                "score": 0,
                "threshold": MOMENTUM_SCORE_THRESHOLD,
                "signals": [f"Error: {e}"],
                "reasons": [f"Error checking pattern: {e}"],
                "breakdown": {
                    "macd": 0,
                    "volume": 0,
                    "rsi": 0,
                    "pullback": 0
                }
            }


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    strategy = MomentumEntry()

    # Test with sample data
    # Simulating strong uptrend with momentum
    prices = [
        100, 102, 101, 103, 105, 104, 106, 108, 107, 109,  # 10
        111, 110, 112, 114, 113, 115, 117, 116, 118, 120,  # 20
        119, 121, 123, 122, 124, 126, 125, 127, 129, 128,  # 30
        130, 132, 131, 133, 135, 134, 136, 138, 137, 139,  # 40
        141, 140, 142, 144, 143, 145, 147, 146, 148, 150   # 50
    ]

    # Create candles with pullback
    candles = []
    for i in range(len(prices) - 1):
        candles.append({
            "open": prices[i],
            "close": prices[i + 1],
            "high": max(prices[i], prices[i + 1]),
            "low": min(prices[i], prices[i + 1])
        })

    token_data = {
        "prices": prices,
        "candles": candles,
        "vol_1m": 50000,  # Volume spike
        "vol_5m": 50000,  # Average volume
    }

    result = strategy.check_pattern(token_data)

    print(f"\nMomentum Pattern Check:")
    print(f"Match: {result['match']}")
    print(f"Score: {result['score']}/{result['threshold']}")
    print(f"Breakdown: {result['breakdown']}")
    print(f"\nSignals:")
    for signal in result['signals']:
        print(f"  - {signal}")
    print(f"\nReasons:")
    for reason in result['reasons']:
        print(f"  - {reason}")
