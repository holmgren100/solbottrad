"""
Weakness Detector - Detect When Momentum is Fading

Scores weakness on 0-100 scale:
- MACD shrinking: 30 points
- Volume declining: 25 points
- RSI divergence: 25 points
- Sell pressure: 20 points

70+ points = EXIT signal (momentum is dead)

This prevents us from holding losers!
"""

import logging
from typing import Dict, List

from src.indicators.macd import MACDCalculator
from src.indicators.rsi import RSICalculator
from src.indicators.volume import VolumeAnalyzer
from src.api.dexscreener_client import DexScreenerClient
from config.parameters import (
    WEAKNESS_SCORE_THRESHOLD,
    WEAKNESS_MACD_SHRINKING_CANDLES,
    WEAKNESS_VOLUME_DECLINE_PERCENT,
    WEAKNESS_VOLUME_DECLINE_CANDLES,
    WEAKNESS_SELL_MULTIPLIER
)

logger = logging.getLogger(__name__)


class WeaknessDetector:
    """
    Detects when position momentum is weakening.

    Scores weakness 0-100:
    - 0-40: Still strong
    - 40-70: Weakening
    - 70+: WEAK - exit signal
    """

    def __init__(self):
        """Initialize weakness detector."""
        self.macd_calculator = MACDCalculator()
        self.rsi_calculator = RSICalculator()
        self.volume_analyzer = VolumeAnalyzer()
        self.dexscreener_client = DexScreenerClient()

        logger.info(f"Weakness Detector initialized - threshold: {WEAKNESS_SCORE_THRESHOLD} points")

    def _check_macd_shrinking(self, prices: List[float]) -> Dict:
        """
        Check if MACD histogram is shrinking (momentum fading).

        Scoring:
        - If histogram declining for 2+ candles: +30 points

        Args:
            prices: List of recent prices (need at least 30 for MACD)

        Returns:
            {"score": int, "shrinking": bool, "signal": str}
        """
        try:
            if len(prices) < 30:
                return {"score": 0, "shrinking": False, "signal": ""}

            # Calculate MACD for last several candles to detect trend
            # We need to check if histogram is declining over last 2+ candles
            macd_result = self.macd_calculator.calculate(prices)
            if not macd_result:
                return {"score": 0, "shrinking": False, "signal": ""}

            # Check if histogram is declining (inverse of growing)
            is_shrinking = not macd_result["is_growing"]

            score = 30 if is_shrinking else 0
            signal = "macd_shrinking" if is_shrinking else ""

            logger.debug(f"MACD shrinking check: shrinking={is_shrinking}, score={score}")

            return {
                "score": score,
                "shrinking": is_shrinking,
                "signal": signal
            }

        except Exception as e:
            logger.error(f"Error checking MACD shrinking: {e}")
            return {"score": 0, "shrinking": False, "signal": ""}

    def _check_volume_declining(self, candles: List[Dict]) -> Dict:
        """
        Check if volume is declining (interest dying).

        Scoring:
        - If volume declined >= 30% over last 3 candles: +25 points

        Args:
            candles: List of candle dicts with 'volume' key

        Returns:
            {"score": int, "declining": bool, "decline_pct": float, "signal": str}
        """
        try:
            if len(candles) < WEAKNESS_VOLUME_DECLINE_CANDLES:
                return {"score": 0, "declining": False, "decline_pct": 0, "signal": ""}

            # Get last 3 candles' volumes
            volumes = [c.get("volume", 0) for c in candles[-WEAKNESS_VOLUME_DECLINE_CANDLES:]]

            if volumes[0] == 0:  # Avoid division by zero
                return {"score": 0, "declining": False, "decline_pct": 0, "signal": ""}

            # Calculate decline from first to last
            decline_pct = ((volumes[0] - volumes[-1]) / volumes[0]) * 100

            is_declining = decline_pct >= WEAKNESS_VOLUME_DECLINE_PERCENT

            score = 25 if is_declining else 0
            signal = f"volume_declining_{int(decline_pct)}+" if is_declining else ""

            logger.debug(
                f"Volume declining check: decline={decline_pct:.1f}%, declining={is_declining}, score={score}"
            )

            return {
                "score": score,
                "declining": is_declining,
                "decline_pct": decline_pct,
                "signal": signal
            }

        except Exception as e:
            logger.error(f"Error checking volume declining: {e}")
            return {"score": 0, "declining": False, "decline_pct": 0, "signal": ""}

    def _check_rsi_divergence(self, prices: List[float]) -> Dict:
        """
        Check for bearish RSI divergence (price makes new high but RSI doesn't).

        Scoring:
        - If price makes new high in last 5 candles but RSI doesn't: +25 points

        Args:
            prices: List of recent prices

        Returns:
            {"score": int, "divergence": bool, "signal": str}
        """
        try:
            if len(prices) < 14:  # Need at least 14 for RSI
                return {"score": 0, "divergence": False, "signal": ""}

            # Check if price made new high in last 5 candles
            lookback = min(5, len(prices) - 1)
            recent_prices = prices[-lookback:]
            price_new_high = prices[-1] >= max(recent_prices)

            if not price_new_high:
                return {"score": 0, "divergence": False, "signal": ""}

            # Calculate RSI for last 2 points to check if RSI is confirming
            rsi_result = self.rsi_calculator.calculate(prices)
            if not rsi_result:
                return {"score": 0, "divergence": False, "signal": ""}

            # If price making new high but RSI is NOT rising = bearish divergence
            rsi_not_confirming = not rsi_result.get("rising", True)

            divergence = price_new_high and rsi_not_confirming

            score = 25 if divergence else 0
            signal = "rsi_divergence" if divergence else ""

            logger.debug(
                f"RSI divergence: price_new_high={price_new_high}, "
                f"rsi_not_confirming={rsi_not_confirming}, divergence={divergence}, score={score}"
            )

            return {
                "score": score,
                "divergence": divergence,
                "signal": signal
            }

        except Exception as e:
            logger.error(f"Error checking RSI divergence: {e}")
            return {"score": 0, "divergence": False, "signal": ""}

    def _check_sell_pressure(self, token_address: str) -> Dict:
        """
        Check for massive sell pressure (sells >> buys).

        Scoring:
        - If sells > buys * 3: +20 points

        Args:
            token_address: Token address to check

        Returns:
            {"score": int, "massive_selling": bool, "signal": str}
        """
        try:
            # Get buy/sell pressure from DexScreener
            pressure_data = self.dexscreener_client.get_buy_sell_pressure(token_address)

            if not pressure_data:
                return {"score": 0, "massive_selling": False, "signal": ""}

            buys = pressure_data.get("buys", 0)
            sells = pressure_data.get("sells", 0)

            if buys == 0:  # Avoid division by zero
                # If no buys but sells exist = very bad
                massive_selling = sells > 0
            else:
                massive_selling = sells > (buys * WEAKNESS_SELL_MULTIPLIER)

            score = 20 if massive_selling else 0
            signal = "massive_sell_pressure" if massive_selling else ""

            logger.debug(
                f"Sell pressure: buys={buys}, sells={sells}, "
                f"massive_selling={massive_selling}, score={score}"
            )

            return {
                "score": score,
                "massive_selling": massive_selling,
                "buys": buys,
                "sells": sells,
                "signal": signal
            }

        except Exception as e:
            logger.error(f"Error checking sell pressure: {e}")
            return {"score": 0, "massive_selling": False, "signal": ""}

    def calculate_score(self, token_data: Dict) -> Dict:
        """
        Calculate overall weakness score.

        Args:
            token_data: Dict with:
                - 'prices': List of recent prices
                - 'candles': List of candle dicts
                - 'token_address': Token address

        Returns:
            {
                "score": int (0-100),
                "should_exit": bool (>= 70),
                "reason": str,
                "signals": List[str],
                "details": {
                    "macd": Dict,
                    "volume": Dict,
                    "rsi": Dict,
                    "sell_pressure": Dict
                }
            }
        """
        try:
            prices = token_data.get("prices", [])
            candles = token_data.get("candles", [])
            token_address = token_data.get("token_address", "")

            # Run all weakness checks
            macd_check = self._check_macd_shrinking(prices)
            volume_check = self._check_volume_declining(candles)
            rsi_check = self._check_rsi_divergence(prices)
            sell_check = self._check_sell_pressure(token_address)

            # Calculate total score
            total_score = (
                macd_check["score"] +
                volume_check["score"] +
                rsi_check["score"] +
                sell_check["score"]
            )

            # Exit if score >= threshold (70)
            should_exit = total_score >= WEAKNESS_SCORE_THRESHOLD

            # Collect active signals
            signals = []
            if macd_check["signal"]:
                signals.append(macd_check["signal"])
            if volume_check["signal"]:
                signals.append(volume_check["signal"])
            if rsi_check["signal"]:
                signals.append(rsi_check["signal"])
            if sell_check["signal"]:
                signals.append(sell_check["signal"])

            # Build reason string
            if signals:
                reason = f"Weakness detected: {', '.join(signals)}"
            else:
                reason = "No weakness detected"

            if should_exit:
                logger.warning(f"⚠️ WEAKNESS EXIT SIGNAL: score {total_score}/100")
                logger.warning(f"   Signals: {', '.join(signals)}")

            result = {
                "score": total_score,
                "should_exit": should_exit,
                "reason": reason,
                "signals": signals,
                "details": {
                    "macd": macd_check,
                    "volume": volume_check,
                    "rsi": rsi_check,
                    "sell_pressure": sell_check
                }
            }

            logger.debug(f"Weakness score: {total_score}/100 - {reason}")

            return result

        except Exception as e:
            logger.error(f"Error calculating weakness score: {e}")
            return {
                "score": 0,
                "should_exit": False,
                "reason": f"Error: {e}",
                "signals": [],
                "details": {}
            }


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    detector = WeaknessDetector()

    # Test data with weakness signals
    test_data = {
        "prices": [100 + i for i in range(20)] + [120 - i for i in range(10)],  # Peak then decline
        "candles": [
            {"volume": 100000},
            {"volume": 80000},
            {"volume": 50000},  # 50% decline
        ],
        "token_address": "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263"  # BONK
    }

    # Calculate weakness score
    result = detector.calculate_score(test_data)

    print(f"\nWeakness Score: {result['score']}/100")
    print(f"Should Exit: {result['should_exit']}")
    print(f"Reason: {result['reason']}")
    print(f"Signals: {result['signals']}")
    print(f"\nDetails:")
    print(f"  MACD: {result['details']['macd']['score']} points")
    print(f"  Volume: {result['details']['volume']['score']} points")
    print(f"  RSI: {result['details']['rsi']['score']} points")
    print(f"  Sell Pressure: {result['details']['sell_pressure']['score']} points")
