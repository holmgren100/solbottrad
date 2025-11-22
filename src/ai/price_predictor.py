import logging
from typing import Dict, List
from dataclasses import dataclass
import numpy as np

@dataclass
class PricePrediction:
    predicted_price: float
    confidence: float
    direction: str  # 'up', 'down', 'sideways'
    time_horizon: str  # '1h', '24h', etc.

class PricePredictor:
    """AI model for price prediction"""

    def __init__(self, model_type: str = 'lstm'):
        self.model_type = model_type
        self.logger = logging.getLogger('trading_bot.price_predictor')
        self.logger.info(f"Price predictor initialized (trend-based)")

    def predict(self, current_price: float, price_change_24h: float, volume_24h: float, liquidity: float) -> PricePrediction:
        """Predict future price based on current data"""
        try:
            # Trend-based prediction
            confidence = 0.5

            # Calculate momentum indicator
            momentum_score = 0.0

            # Price change momentum
            if price_change_24h > 10:
                momentum_score += 0.4
                confidence += 0.1
            elif price_change_24h > 5:
                momentum_score += 0.2
                confidence += 0.05
            elif price_change_24h < -10:
                momentum_score -= 0.4
                confidence += 0.1
            elif price_change_24h < -5:
                momentum_score -= 0.2
                confidence += 0.05

            # Volume relative to liquidity
            if liquidity > 0:
                volume_ratio = volume_24h / liquidity
                if volume_ratio > 2:  # High volume
                    momentum_score += 0.2
                    confidence += 0.1
                elif volume_ratio > 1:
                    momentum_score += 0.1
                    confidence += 0.05

            # Predict price direction
            if momentum_score > 0.3:
                direction = 'up'
                # Predict 5-15% increase based on momentum
                predicted_price = current_price * (1 + (momentum_score * 0.15))
            elif momentum_score < -0.3:
                direction = 'down'
                # Predict 5-15% decrease
                predicted_price = current_price * (1 + (momentum_score * 0.15))
            else:
                direction = 'sideways'
                # Predict small change
                predicted_price = current_price * (1 + (momentum_score * 0.05))

            # Ensure confidence is reasonable
            confidence = min(max(confidence, 0.3), 0.9)

            return PricePrediction(
                predicted_price=predicted_price,
                confidence=confidence,
                direction=direction,
                time_horizon='24h'
            )

        except Exception as e:
            self.logger.error(f"Error in price prediction: {e}")
            return PricePrediction(
                predicted_price=current_price,
                confidence=0.0,
                direction='sideways',
                time_horizon='24h'
            )

    def calculate_trend_strength(self, price_changes: List[float]) -> float:
        """Calculate trend strength from historical price changes"""
        if not price_changes:
            return 0.0

        # Simple trend calculation
        positive = sum(1 for x in price_changes if x > 0)
        negative = sum(1 for x in price_changes if x < 0)
        total = len(price_changes)

        if total == 0:
            return 0.0

        return (positive - negative) / total
