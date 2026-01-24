"""
Simple Momentum Entry - NO FAKE DATA, ONLY REAL DEXSCREENER DATA!

Scoring based on REAL data from DexScreener:
- Price momentum (5m, 1h, 24h changes)
- Volume spike (5m vs 1h comparison)
- Buy pressure (buys vs sells ratio)
- Liquidity strength

NO MACD, NO RSI, NO FAKE CANDLES - just real market data!
"""

import logging
from typing import Dict

logger = logging.getLogger(__name__)


class SimpleMomentumEntry:
    """
    Simple momentum entry using ONLY real DexScreener data.

    Score: 100 points max, need 60+ to enter
    """

    def __init__(self):
        """Initialize simple momentum strategy."""
        logger.info("Simple Momentum Entry initialized - using REAL data only!")

    def check_pattern(self, token_data: Dict) -> Dict:
        """
        Check momentum pattern using REAL DexScreener data.

        Args:
            token_data: Dict with DexScreener data:
                - price_change_5m: % price change last 5 minutes
                - price_change_1h: % price change last hour
                - price_change_24h: % price change last 24h
                - volume_5m: Volume last 5 minutes
                - volume_1h: Volume last hour
                - volume_24h: Volume last 24h
                - buys_5m: Buy transactions last 5 min
                - sells_5m: Sell transactions last 5 min
                - liquidity: USD liquidity

        Returns:
            {
                "match": bool,
                "score": int (0-100),
                "signals": List[str],
                "breakdown": dict
            }
        """
        try:
            score = 0
            signals = []
            breakdown = {}

            # 1. PRICE MOMENTUM (40 points max)
            price_5m = token_data.get("price_change_5m", 0)
            price_1h = token_data.get("price_change_1h", 0)
            price_24h = token_data.get("price_change_24h", 0)

            momentum_score = 0

            # Strong 5m momentum: +5% or more
            if price_5m >= 10:
                momentum_score += 20
                signals.append(f"Strong 5m pump: +{price_5m:.1f}%")
            elif price_5m >= 5:
                momentum_score += 10
                signals.append(f"Moderate 5m gain: +{price_5m:.1f}%")

            # Strong 1h momentum: +10% or more
            if price_1h >= 20:
                momentum_score += 20
                signals.append(f"Strong 1h trend: +{price_1h:.1f}%")
            elif price_1h >= 10:
                momentum_score += 10
                signals.append(f"Moderate 1h trend: +{price_1h:.1f}%")

            score += momentum_score
            breakdown["price_momentum"] = momentum_score

            # 2. VOLUME SPIKE (30 points max)
            vol_5m = token_data.get("volume_5m", 0)
            vol_1h = token_data.get("volume_1h", 0)

            volume_score = 0

            if vol_1h > 0:
                # Expected 5m volume = 1h volume / 12
                expected_5m = vol_1h / 12
                if expected_5m > 0:
                    spike_ratio = vol_5m / expected_5m

                    if spike_ratio >= 6.0:  # 6x spike!
                        volume_score = 30
                        signals.append(f"MASSIVE volume spike: {spike_ratio:.1f}x")
                    elif spike_ratio >= 4.0:  # 4x spike
                        volume_score = 20
                        signals.append(f"Strong volume spike: {spike_ratio:.1f}x")
                    elif spike_ratio >= 2.0:  # 2x spike
                        volume_score = 10
                        signals.append(f"Volume increasing: {spike_ratio:.1f}x")

            score += volume_score
            breakdown["volume_spike"] = volume_score

            # 3. BUY PRESSURE (20 points max)
            buys = token_data.get("buys_5m", 0)
            sells = token_data.get("sells_5m", 0)

            pressure_score = 0

            if sells > 0:
                buy_ratio = buys / sells

                if buy_ratio >= 3.0:  # 3:1 buy pressure!
                    pressure_score = 20
                    signals.append(f"HEAVY buy pressure: {buy_ratio:.1f}:1")
                elif buy_ratio >= 2.0:  # 2:1 buy pressure
                    pressure_score = 15
                    signals.append(f"Strong buy pressure: {buy_ratio:.1f}:1")
                elif buy_ratio >= 1.5:  # 1.5:1 buy pressure
                    pressure_score = 10
                    signals.append(f"Buy pressure: {buy_ratio:.1f}:1")
            elif buys > 0:
                # All buys, no sells!
                pressure_score = 20
                signals.append("ALL BUYS, NO SELLS!")

            score += pressure_score
            breakdown["buy_pressure"] = pressure_score

            # 4. POSITIVE TREND (10 points)
            trend_score = 0

            if price_24h > 0:
                trend_score = 10
                signals.append(f"24h uptrend: +{price_24h:.1f}%")

            score += trend_score
            breakdown["trend"] = trend_score

            # Pattern matches if score >= 60
            pattern_match = score >= 60

            result = {
                "match": pattern_match,
                "score": score,
                "threshold": 60,
                "signals": signals,
                "breakdown": breakdown,
                "macd_score": 0,  # For compatibility
                "volume_score": volume_score,
                "rsi_score": 0,  # For compatibility
                "pullback_score": 0  # For compatibility
            }

            if pattern_match:
                logger.info(f"🚀 MOMENTUM MATCH! Score: {score}/100")
                logger.info(f"   Breakdown: {breakdown}")
            else:
                logger.debug(f"Score: {score}/100 (need 60+)")

            return result

        except Exception as e:
            logger.error(f"Error checking pattern: {e}")
            return {
                "match": False,
                "score": 0,
                "threshold": 60,
                "signals": [f"Error: {e}"],
                "breakdown": {},
                "macd_score": 0,
                "volume_score": 0,
                "rsi_score": 0,
                "pullback_score": 0
            }


# Test
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    strategy = SimpleMomentumEntry()

    # Test with strong momentum token
    test_data = {
        "price_change_5m": 12.5,  # Strong 5m pump
        "price_change_1h": 25.0,  # Strong 1h trend
        "price_change_24h": 50.0,  # Uptrend
        "volume_5m": 100000,
        "volume_1h": 200000,  # 5m vol = 6x expected
        "volume_24h": 500000,
        "buys_5m": 150,
        "sells_5m": 50,  # 3:1 buy pressure
        "liquidity": 100000
    }

    result = strategy.check_pattern(test_data)

    print(f"\nPattern Match: {result['match']}")
    print(f"Score: {result['score']}/100")
    print(f"Breakdown: {result['breakdown']}")
    print(f"\nSignals:")
    for signal in result['signals']:
        print(f"  - {signal}")
