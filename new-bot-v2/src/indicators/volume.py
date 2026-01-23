"""
Volume Analyzer - Volume Spike Detection

Volume spikes indicate strong buying interest and potential momentum.

Key Metrics:
- Volume Velocity: vol_1m / (vol_5m / 5)
- 400% spike (velocity >= 4.0) = strong momentum

Scoring (30 points max):
- Velocity >= 4.0 (400% spike): +30 points
"""

import logging
from typing import List, Dict, Optional

from config.parameters import (
    VOLUME_VELOCITY_THRESHOLD,
    VOLUME_SPIKE_POINTS
)

logger = logging.getLogger(__name__)


class VolumeAnalyzer:
    """
    Volume analyzer for detecting momentum through volume spikes.

    Volume velocity measures how current volume compares to recent average.
    High velocity = strong buying pressure = momentum!
    """

    def __init__(self):
        """Initialize volume analyzer."""
        logger.debug("Volume Analyzer initialized")

    def calculate_velocity(
        self,
        vol_1m: float,
        vol_5m: float
    ) -> float:
        """
        Calculate volume velocity (current vs average).

        Formula: vol_1m / (vol_5m / 5)
        - Dividing vol_5m by 5 gives average volume per minute
        - Dividing current by average gives velocity multiplier

        Args:
            vol_1m: Volume in last 1 minute
            vol_5m: Volume in last 5 minutes

        Returns:
            Velocity multiplier (e.g., 4.0 = 400% of average)
        """
        try:
            if vol_5m == 0:
                logger.warning("Cannot calculate velocity: vol_5m is zero")
                return 0.0

            avg_volume_per_minute = vol_5m / 5
            velocity = vol_1m / avg_volume_per_minute if avg_volume_per_minute > 0 else 0.0

            logger.debug(
                f"Volume velocity: {vol_1m:,.0f} / ({vol_5m:,.0f} / 5) = {velocity:.2f}x"
            )

            return velocity

        except Exception as e:
            logger.error(f"Error calculating velocity: {e}")
            return 0.0

    def check_spike(
        self,
        current: float,
        average: float,
        min_multiplier: float = VOLUME_VELOCITY_THRESHOLD
    ) -> bool:
        """
        Check if current volume is spiking vs average.

        Args:
            current: Current volume
            average: Average volume
            min_multiplier: Minimum multiplier for spike (default: 4.0)

        Returns:
            True if current >= average * min_multiplier
        """
        try:
            if average == 0:
                return False

            multiplier = current / average
            is_spike = multiplier >= min_multiplier

            if is_spike:
                logger.info(f"🚀 VOLUME SPIKE: {multiplier:.1f}x average!")

            return is_spike

        except Exception as e:
            logger.error(f"Error checking spike: {e}")
            return False

    def analyze_trend(
        self,
        volumes: List[float],
        lookback: int = 5
    ) -> Dict:
        """
        Analyze volume trend over recent candles.

        Args:
            volumes: List of volume values
            lookback: Number of candles to analyze

        Returns:
            {
                "trend": str,  # "INCREASING", "DECREASING", "FLAT"
                "change_pct": float,  # Percent change from first to last
                "is_healthy": bool,  # Is volume increasing with price?
                "average": float,  # Average volume
            }
        """
        try:
            if len(volumes) < lookback:
                lookback = len(volumes)

            if lookback < 2:
                return {
                    "trend": "UNKNOWN",
                    "change_pct": 0.0,
                    "is_healthy": False,
                    "average": 0.0
                }

            recent = volumes[-lookback:]
            average = sum(recent) / len(recent)

            # Compare first and last volume
            first_vol = recent[0]
            last_vol = recent[-1]

            if first_vol == 0:
                change_pct = 0.0
            else:
                change_pct = ((last_vol - first_vol) / first_vol) * 100

            # Determine trend
            if change_pct > 10:
                trend = "INCREASING"
                is_healthy = True
            elif change_pct < -10:
                trend = "DECREASING"
                is_healthy = False
            else:
                trend = "FLAT"
                is_healthy = True  # Flat is ok

            result = {
                "trend": trend,
                "change_pct": change_pct,
                "is_healthy": is_healthy,
                "average": average
            }

            logger.debug(
                f"Volume trend: {trend} ({change_pct:+.1f}%), "
                f"avg: {average:,.0f}, "
                f"healthy: {is_healthy}"
            )

            return result

        except Exception as e:
            logger.error(f"Error analyzing trend: {e}")
            return {
                "trend": "ERROR",
                "change_pct": 0.0,
                "is_healthy": False,
                "average": 0.0
            }

    def calculate_score(
        self,
        vol_1m: float,
        vol_5m: float
    ) -> Dict:
        """
        Calculate volume momentum score (0-30 points).

        Scoring:
        - Velocity >= 4.0 (400% spike): +30 points

        Args:
            vol_1m: Volume in last 1 minute
            vol_5m: Volume in last 5 minutes

        Returns:
            {
                "score": int,  # 0-30 points
                "signals": List[str],  # Positive signals
                "velocity": float,  # Volume velocity
                "is_spike": bool  # Is this a spike?
            }
        """
        score = 0
        signals = []

        # Calculate velocity
        velocity = self.calculate_velocity(vol_1m, vol_5m)

        # Check if spike
        is_spike = velocity >= VOLUME_VELOCITY_THRESHOLD

        if is_spike:
            score += VOLUME_SPIKE_POINTS
            signals.append(
                f"Volume SPIKE {velocity:.1f}x ({int(velocity * 100)}%) (+{VOLUME_SPIKE_POINTS} pts)"
            )
        else:
            signals.append(f"Volume normal {velocity:.1f}x (need {VOLUME_VELOCITY_THRESHOLD}x for spike)")

        result = {
            "score": score,
            "signals": signals,
            "velocity": velocity,
            "is_spike": is_spike
        }

        logger.info(
            f"Volume Score: {score}/30 points - {', '.join(signals)}"
        )

        return result

    def get_volume_profile(
        self,
        vol_1m: float,
        vol_5m: float,
        vol_1h: float,
        vol_24h: float
    ) -> Dict:
        """
        Get comprehensive volume profile.

        Args:
            vol_1m: Volume last 1 minute
            vol_5m: Volume last 5 minutes
            vol_1h: Volume last 1 hour
            vol_24h: Volume last 24 hours

        Returns:
            {
                "velocity_1m": float,
                "velocity_5m": float,
                "velocity_1h": float,
                "is_accelerating": bool,
                "momentum_strength": str  # "WEAK", "MODERATE", "STRONG"
            }
        """
        try:
            # Calculate velocities
            velocity_1m = self.calculate_velocity(vol_1m, vol_5m)

            # Calculate 5m velocity vs 1h
            avg_vol_per_5m_from_1h = (vol_1h / 60) * 5
            velocity_5m = vol_5m / avg_vol_per_5m_from_1h if avg_vol_per_5m_from_1h > 0 else 0.0

            # Calculate 1h velocity vs 24h
            avg_vol_per_1h_from_24h = vol_24h / 24
            velocity_1h = vol_1h / avg_vol_per_1h_from_24h if avg_vol_per_1h_from_24h > 0 else 0.0

            # Check if accelerating (each timeframe faster than next)
            is_accelerating = velocity_1m > velocity_5m > velocity_1h

            # Determine momentum strength
            if velocity_1m >= 4.0:
                momentum_strength = "STRONG"
            elif velocity_1m >= 2.0:
                momentum_strength = "MODERATE"
            else:
                momentum_strength = "WEAK"

            result = {
                "velocity_1m": velocity_1m,
                "velocity_5m": velocity_5m,
                "velocity_1h": velocity_1h,
                "is_accelerating": is_accelerating,
                "momentum_strength": momentum_strength
            }

            logger.debug(
                f"Volume profile: 1m={velocity_1m:.2f}x, 5m={velocity_5m:.2f}x, "
                f"1h={velocity_1h:.2f}x, accelerating={is_accelerating}, "
                f"strength={momentum_strength}"
            )

            return result

        except Exception as e:
            logger.error(f"Error getting volume profile: {e}")
            return {
                "velocity_1m": 0.0,
                "velocity_5m": 0.0,
                "velocity_1h": 0.0,
                "is_accelerating": False,
                "momentum_strength": "WEAK"
            }


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    analyzer = VolumeAnalyzer()

    # Test 1: Normal volume (no spike)
    vol_1m = 10000
    vol_5m = 50000  # Average = 10000 per minute
    score1 = analyzer.calculate_score(vol_1m, vol_5m)
    print(f"Normal Volume Score: {score1}")

    # Test 2: Volume spike (400%+)
    vol_1m_spike = 50000
    vol_5m_normal = 50000  # Average = 10000 per minute
    score2 = analyzer.calculate_score(vol_1m_spike, vol_5m_normal)
    print(f"\nVolume Spike Score: {score2}")

    # Test 3: Volume trend analysis
    volumes = [1000, 1500, 2000, 3000, 5000, 8000]
    trend = analyzer.analyze_trend(volumes)
    print(f"\nVolume Trend: {trend}")

    # Test 4: Volume profile
    profile = analyzer.get_volume_profile(
        vol_1m=50000,
        vol_5m=150000,
        vol_1h=500000,
        vol_24h=5000000
    )
    print(f"\nVolume Profile: {profile}")
