"""
Weakness Detector - Detect When Momentum is Fading

Scores weakness on 0-100 scale:
- MACD declining: 40 points
- Volume dropping: 30 points
- RSI divergence: 20 points
- Rapid drawdown: 10 points

60+ points = EXIT signal (momentum is dead)

This prevents us from holding losers!
"""

import logging
from typing import Dict, List

from src.indicators.macd import MACDCalculator
from src.indicators.rsi import RSICalculator
from src.indicators.volume import VolumeAnalyzer

logger = logging.getLogger(__name__)


class WeaknessDetector:
    """
    Detects when position momentum is weakening.

    Scores weakness 0-100:
    - 0-30: Still strong
    - 30-60: Weakening
    - 60+: WEAK - exit signal
    """

    def __init__(self):
        """Initialize weakness detector."""
        self.macd_calculator = MACDCalculator()
        self.rsi_calculator = RSICalculator()
        self.volume_analyzer = VolumeAnalyzer()

        logger.info("Weakness Detector initialized - threshold: 60 points")

    def _check_macd_declining(self, prices: List[float]) -> Dict:
        """
        Check if MACD histogram is declining (momentum fading).

        Scoring:
        - Histogram negative: +20 points
        - Histogram declining 2+ candles: +20 points

        Args:
            prices: List of recent prices

        Returns:
            {"score": int, "negative": bool, "declining": bool}
        """
        try:
            if len(prices) < 30:
                return {"score": 0, "negative": False, "declining": False}

            macd_result = self.macd_calculator.calculate(prices)
            if not macd_result:
                return {"score": 0, "negative": False, "declining": False}

            is_negative = not macd_result["is_positive"]
            is_declining = not macd_result["is_growing"]

            score = 0
            if is_negative:
                score += 20
            if is_declining:
                score += 20

            logger.debug(
                f"MACD weakness: negative={is_negative}, declining={is_declining}, score={score}"
            )

            return {
                "score": score,
                "negative": is_negative,
                "declining": is_declining
            }

        except Exception as e:
            logger.error(f"Error checking MACD declining: {e}")
            return {"score": 0, "negative": False, "declining": False}

    def _check_volume_dropping(self, vol_1m: float, vol_5m: float) -> Dict:
        """
        Check if volume is dropping (interest dying).

        Scoring:
        - Volume velocity < 2.0x: +15 points
        - Volume velocity < 1.0x: +15 points (total 30)

        Args:
            vol_1m: 1-minute volume
            vol_5m: 5-minute volume

        Returns:
            {"score": int, "velocity": float}
        """
        try:
            velocity = self.volume_analyzer.calculate_velocity(vol_1m, vol_5m)

            score = 0
            if velocity < 2.0:
                score += 15
            if velocity < 1.0:
                score += 15

            logger.debug(f"Volume weakness: velocity={velocity:.1f}x, score={score}")

            return {
                "score": score,
                "velocity": velocity
            }

        except Exception as e:
            logger.error(f"Error checking volume dropping: {e}")
            return {"score": 0, "velocity": 0}

    def _check_rsi_divergence(self, prices: List[float]) -> Dict:
        """
        Check for RSI divergence (price up but RSI down = weakness).

        Scoring:
        - RSI declining while price rising: +20 points

        Args:
            prices: List of recent prices

        Returns:
            {"score": int, "divergence": bool}
        """
        try:
            if len(prices) < 14:
                return {"score": 0, "divergence": False}

            rsi_result = self.rsi_calculator.calculate(prices)
            if not rsi_result:
                return {"score": 0, "divergence": False}

            # Check if price rising but RSI falling
            price_rising = prices[-1] > prices[-5] if len(prices) >= 5 else False
            rsi_falling = not rsi_result.get("rising", True)

            divergence = price_rising and rsi_falling

            score = 20 if divergence else 0

            logger.debug(
                f"RSI divergence: price_rising={price_rising}, "
                f"rsi_falling={rsi_falling}, divergence={divergence}, score={score}"
            )

            return {
                "score": score,
                "divergence": divergence
            }

        except Exception as e:
            logger.error(f"Error checking RSI divergence: {e}")
            return {"score": 0, "divergence": False}

    def _check_rapid_drawdown(self, position) -> Dict:
        """
        Check for rapid drawdown from highest price.

        Scoring:
        - Drawdown > 10% from highest: +10 points

        Args:
            position: Position object with highest_price, current_price

        Returns:
            {"score": int, "drawdown_pct": float}
        """
        try:
            if position.highest_price == 0:
                return {"score": 0, "drawdown_pct": 0}

            drawdown_pct = (
                (position.highest_price - position.current_price) / position.highest_price
            ) * 100

            score = 10 if drawdown_pct > 10 else 0

            logger.debug(f"Drawdown: {drawdown_pct:.1f}% from high, score={score}")

            return {
                "score": score,
                "drawdown_pct": drawdown_pct
            }

        except Exception as e:
            logger.error(f"Error checking rapid drawdown: {e}")
            return {"score": 0, "drawdown_pct": 0}

    def detect_weakness(self, position, token_data: Dict) -> Dict:
        """
        Detect overall weakness in position.

        Args:
            position: Position object
            token_data: Dict with 'prices', 'vol_1m', 'vol_5m'

        Returns:
            {
                "is_weak": bool,
                "weakness_score": int (0-100),
                "should_exit": bool,
                "reason": str,
                "details": {
                    "macd": Dict,
                    "volume": Dict,
                    "rsi": Dict,
                    "drawdown": Dict
                }
            }
        """
        try:
            prices = token_data.get("prices", [])
            vol_1m = token_data.get("vol_1m", 0)
            vol_5m = token_data.get("vol_5m", 0)

            # Run all weakness checks
            macd_weakness = self._check_macd_declining(prices)
            volume_weakness = self._check_volume_dropping(vol_1m, vol_5m)
            rsi_weakness = self._check_rsi_divergence(prices)
            drawdown_weakness = self._check_rapid_drawdown(position)

            # Calculate total weakness score
            weakness_score = (
                macd_weakness["score"] +
                volume_weakness["score"] +
                rsi_weakness["score"] +
                drawdown_weakness["score"]
            )

            # Exit threshold: 60+ points
            should_exit = weakness_score >= 60
            is_weak = weakness_score >= 30

            # Build reason
            reasons = []
            if macd_weakness["negative"]:
                reasons.append("MACD negative")
            if macd_weakness["declining"]:
                reasons.append("MACD declining")
            if volume_weakness["velocity"] < 1.0:
                reasons.append("volume dying")
            if rsi_weakness["divergence"]:
                reasons.append("RSI divergence")
            if drawdown_weakness["drawdown_pct"] > 10:
                reasons.append(f"{drawdown_weakness['drawdown_pct']:.1f}% drawdown")

            reason = ", ".join(reasons) if reasons else "No weakness detected"

            if should_exit:
                logger.warning(
                    f"⚠️ WEAKNESS DETECTED: {position.symbol} - {weakness_score} points"
                )
                logger.warning(f"   Reason: {reason}")

            result = {
                "is_weak": is_weak,
                "weakness_score": weakness_score,
                "should_exit": should_exit,
                "reason": reason,
                "details": {
                    "macd": macd_weakness,
                    "volume": volume_weakness,
                    "rsi": rsi_weakness,
                    "drawdown": drawdown_weakness
                }
            }

            logger.debug(
                f"{position.symbol} weakness: {weakness_score}/100 - {reason}"
            )

            return result

        except Exception as e:
            logger.error(f"Error detecting weakness: {e}")
            return {
                "is_weak": False,
                "weakness_score": 0,
                "should_exit": False,
                "reason": f"Error: {e}",
                "details": {}
            }


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    from src.position.position_manager import Position

    detector = WeaknessDetector()

    # Create test position with drawdown
    position = Position(
        token_address="TEST123",
        symbol="TEST",
        entry_price=0.001,
        size_sol=0.1
    )

    # Simulate price movement
    position.update_price(0.002)  # +100% high
    position.update_price(0.0015)  # Dropped 25% from high

    # Test data with declining momentum
    test_data = {
        "prices": [100 + i for i in range(20)] + [120 - i for i in range(10)],  # Peak then decline
        "vol_1m": 10000,
        "vol_5m": 50000,  # Low velocity
    }

    # Check weakness
    result = detector.detect_weakness(position, test_data)

    print(f"\nWeakness Score: {result['weakness_score']}/100")
    print(f"Is Weak: {result['is_weak']}")
    print(f"Should Exit: {result['should_exit']}")
    print(f"Reason: {result['reason']}")
    print(f"\nDetails:")
    print(f"  MACD: {result['details']['macd']['score']} points")
    print(f"  Volume: {result['details']['volume']['score']} points")
    print(f"  RSI: {result['details']['rsi']['score']} points")
    print(f"  Drawdown: {result['details']['drawdown']['score']} points")
