"""
Price prediction model for market movement forecasting.
Uses technical indicators and historical patterns.
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
import statistics
from ..monitoring.logger import get_logger

logger = get_logger(__name__)


@dataclass
class PricePrediction:
    """Represents a price prediction."""
    token_address: str
    current_price: float
    predicted_direction: str  # 'up', 'down', 'sideways'
    confidence: float  # 0-1
    predicted_change_percent: float
    timeframe_hours: int
    factors: List[str]
    timestamp: datetime


class PricePredictor:
    """Predicts price movements using technical analysis."""

    def __init__(self):
        """Initialize the price predictor."""
        self.price_history: Dict[str, List[Dict]] = {}

    def record_price(
        self,
        token_address: str,
        price: float,
        volume: float,
        liquidity: float
    ):
        """
        Record a price data point.

        Args:
            token_address: Token address
            price: Current price
            volume: Trading volume
            liquidity: Current liquidity
        """
        if token_address not in self.price_history:
            self.price_history[token_address] = []

        self.price_history[token_address].append({
            'price': price,
            'volume': volume,
            'liquidity': liquidity,
            'timestamp': datetime.now()
        })

        # Keep only last 200 data points
        if len(self.price_history[token_address]) > 200:
            self.price_history[token_address] = self.price_history[token_address][-200:]

    def predict(
        self,
        token_address: str,
        current_price: float,
        market_signal: Dict,
        sentiment_score: Dict,
        timeframe_hours: int = 24
    ) -> PricePrediction:
        """
        Predict price movement.

        Args:
            token_address: Token address
            current_price: Current token price
            market_signal: Market signal data
            sentiment_score: Sentiment analysis score
            timeframe_hours: Prediction timeframe in hours

        Returns:
            PricePrediction with forecast
        """
        factors = []
        direction_score = 0.0

        # 1. Market Signal Analysis
        signal_type = market_signal.get('signal_type', 'hold')
        signal_strength = market_signal.get('strength', 0.0)
        signal_confidence = market_signal.get('confidence', 0.0)

        if signal_type == 'buy':
            direction_score += signal_strength * 0.3
            factors.append(f"Market signal: {signal_type} (strength: {signal_strength:.2f})")
        elif signal_type == 'sell':
            direction_score -= signal_strength * 0.3
            factors.append(f"Market signal: {signal_type} (strength: {signal_strength:.2f})")

        # 2. Sentiment Analysis
        sentiment_overall = sentiment_score.get('overall_score', 0.5)
        sentiment_confidence = sentiment_score.get('confidence', 0.5)

        # Convert sentiment (0-1) to direction (-0.3 to +0.3)
        sentiment_direction = (sentiment_overall - 0.5) * 0.6
        direction_score += sentiment_direction * sentiment_confidence
        factors.append(f"Sentiment score: {sentiment_overall:.2f}")

        # 3. Historical Price Pattern
        if token_address in self.price_history and len(self.price_history[token_address]) >= 5:
            pattern_score = self._analyze_price_pattern(token_address)
            direction_score += pattern_score * 0.2
            if pattern_score > 0.1:
                factors.append(f"Positive price pattern detected")
            elif pattern_score < -0.1:
                factors.append(f"Negative price pattern detected")

        # 4. Volume Trend
        if token_address in self.price_history and len(self.price_history[token_address]) >= 3:
            volume_trend = self._analyze_volume_trend(token_address)
            direction_score += volume_trend * 0.15
            if volume_trend > 0.1:
                factors.append("Increasing volume trend")
            elif volume_trend < -0.1:
                factors.append("Decreasing volume trend")

        # 5. Liquidity Stability
        liquidity = market_signal.get('liquidity', 0)
        if liquidity > 100000:
            factors.append("Strong liquidity support")
            direction_score += 0.05
        elif liquidity < 20000:
            factors.append("Weak liquidity - high risk")
            direction_score -= 0.1

        # Determine Direction and Predicted Change
        if direction_score > 0.2:
            predicted_direction = 'up'
            predicted_change = self._estimate_price_change(direction_score, 'up')
        elif direction_score < -0.2:
            predicted_direction = 'down'
            predicted_change = self._estimate_price_change(direction_score, 'down')
        else:
            predicted_direction = 'sideways'
            predicted_change = 0.0

        # Calculate Confidence
        confidence = self._calculate_prediction_confidence(
            signal_confidence,
            sentiment_confidence,
            len(self.price_history.get(token_address, []))
        )

        prediction = PricePrediction(
            token_address=token_address,
            current_price=current_price,
            predicted_direction=predicted_direction,
            confidence=confidence,
            predicted_change_percent=predicted_change,
            timeframe_hours=timeframe_hours,
            factors=factors,
            timestamp=datetime.now()
        )

        logger.debug(
            f"Price prediction for {token_address[:8]}...: "
            f"{predicted_direction} ({predicted_change:+.1f}%) "
            f"confidence: {confidence:.2f}"
        )

        return prediction

    def _analyze_price_pattern(self, token_address: str) -> float:
        """
        Analyze historical price pattern.

        Args:
            token_address: Token address

        Returns:
            Pattern score (-1 to 1)
        """
        history = self.price_history[token_address][-20:]
        if len(history) < 5:
            return 0.0

        prices = [h['price'] for h in history]

        # Calculate simple moving average trend
        recent_prices = prices[-5:]
        older_prices = prices[-10:-5] if len(prices) >= 10 else prices[:5]

        recent_avg = sum(recent_prices) / len(recent_prices)
        older_avg = sum(older_prices) / len(older_prices)

        if older_avg == 0:
            return 0.0

        trend = (recent_avg - older_avg) / older_avg

        # Normalize to -1 to 1 range
        return max(min(trend * 5, 1.0), -1.0)

    def _analyze_volume_trend(self, token_address: str) -> float:
        """
        Analyze volume trend.

        Args:
            token_address: Token address

        Returns:
            Volume trend score (-1 to 1)
        """
        history = self.price_history[token_address][-10:]
        if len(history) < 3:
            return 0.0

        volumes = [h['volume'] for h in history]

        recent_vol = sum(volumes[-3:]) / 3
        older_vol = sum(volumes[:3]) / 3

        if older_vol == 0:
            return 0.0

        trend = (recent_vol - older_vol) / older_vol

        # Normalize to -1 to 1 range
        return max(min(trend, 1.0), -1.0)

    def _estimate_price_change(self, direction_score: float, direction: str) -> float:
        """
        Estimate predicted price change percentage.

        Args:
            direction_score: Direction score
            direction: 'up' or 'down'

        Returns:
            Predicted change percentage
        """
        # Map direction score to realistic price change
        # Crypto can be volatile, so allow for larger swings
        magnitude = abs(direction_score)

        if direction == 'up':
            # Positive prediction: 5% to 50%
            return 5 + (magnitude * 45)
        else:
            # Negative prediction: -5% to -40%
            return -(5 + (magnitude * 35))

    def _calculate_prediction_confidence(
        self,
        market_confidence: float,
        sentiment_confidence: float,
        data_points: int
    ) -> float:
        """
        Calculate overall prediction confidence.

        Args:
            market_confidence: Market signal confidence
            sentiment_confidence: Sentiment analysis confidence
            data_points: Number of historical data points

        Returns:
            Confidence score (0-1)
        """
        # Base confidence from inputs
        base_confidence = (market_confidence + sentiment_confidence) / 2

        # Adjust based on available historical data
        data_factor = min(data_points / 20, 1.0)

        # Combined confidence
        confidence = base_confidence * 0.7 + data_factor * 0.3

        return confidence

    def get_prediction_accuracy(self, token_address: str) -> Optional[Dict]:
        """
        Calculate historical prediction accuracy (placeholder).

        Args:
            token_address: Token address

        Returns:
            Accuracy metrics or None
        """
        # This would track historical predictions vs actual outcomes
        # For now, return None as it requires persistent storage
        return None
