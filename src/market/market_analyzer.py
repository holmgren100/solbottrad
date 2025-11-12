"""
Market analysis and volatility assessment.
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
import statistics
from ..monitoring.logger import get_logger

logger = get_logger(__name__)


@dataclass
class MarketSignal:
    """Represents a market signal for trading."""
    token_address: str
    signal_type: str  # 'buy', 'sell', 'hold'
    strength: float  # 0-1
    confidence: float  # 0-1
    reasons: List[str]
    timestamp: datetime
    price: float
    volume_24h: float
    liquidity: float


class MarketAnalyzer:
    """Analyzes market data to generate trading signals."""

    def __init__(self, min_liquidity_usd: float = 10000):
        """
        Initialize market analyzer.

        Args:
            min_liquidity_usd: Minimum liquidity threshold in USD
        """
        self.min_liquidity_usd = min_liquidity_usd
        self.price_history: Dict[str, List[Dict]] = {}

    def record_price(self, token_address: str, price: float, volume: float):
        """
        Record a price data point.

        Args:
            token_address: Token address
            price: Token price
            volume: Trading volume
        """
        if token_address not in self.price_history:
            self.price_history[token_address] = []

        self.price_history[token_address].append({
            'price': price,
            'volume': volume,
            'timestamp': datetime.now()
        })

        # Keep only last 100 data points per token
        if len(self.price_history[token_address]) > 100:
            self.price_history[token_address] = self.price_history[token_address][-100:]

    def analyze_token(self, profile: Dict) -> MarketSignal:
        """
        Analyze a token and generate a market signal.

        Args:
            profile: Token profile from DexScreener

        Returns:
            MarketSignal with analysis results
        """
        token_address = profile['address']
        price = profile['price_usd']
        volume_24h = profile['volume_24h']
        liquidity = profile['liquidity_usd']
        price_change_24h = profile['price_change_24h']

        reasons = []
        score = 0.5  # Neutral starting point

        # Liquidity check
        if liquidity < self.min_liquidity_usd:
            reasons.append(f"Low liquidity (${liquidity:,.0f})")
            signal_type = 'hold'
            confidence = 0.3
            return MarketSignal(
                token_address=token_address,
                signal_type=signal_type,
                strength=0.0,
                confidence=confidence,
                reasons=reasons,
                timestamp=datetime.now(),
                price=price,
                volume_24h=volume_24h,
                liquidity=liquidity
            )

        # Volume analysis
        volume_to_liquidity_ratio = volume_24h / liquidity if liquidity > 0 else 0
        if volume_to_liquidity_ratio > 0.5:
            reasons.append(f"Strong volume/liquidity ratio ({volume_to_liquidity_ratio:.2f})")
            score += 0.15
        elif volume_to_liquidity_ratio < 0.1:
            reasons.append(f"Low volume/liquidity ratio ({volume_to_liquidity_ratio:.2f})")
            score -= 0.1

        # Price change analysis
        if price_change_24h > 20:
            reasons.append(f"Strong upward momentum (+{price_change_24h:.1f}%)")
            score += 0.2
        elif price_change_24h > 5:
            reasons.append(f"Positive price action (+{price_change_24h:.1f}%)")
            score += 0.1
        elif price_change_24h < -20:
            reasons.append(f"Sharp decline ({price_change_24h:.1f}%)")
            score -= 0.2
        elif price_change_24h < -5:
            reasons.append(f"Negative price action ({price_change_24h:.1f}%)")
            score -= 0.1

        # Liquidity assessment
        if liquidity > 100000:
            reasons.append(f"Excellent liquidity (${liquidity:,.0f})")
            score += 0.1
        elif liquidity > 50000:
            reasons.append(f"Good liquidity (${liquidity:,.0f})")
            score += 0.05

        # Market cap analysis
        market_cap = profile.get('market_cap', 0)
        if 0 < market_cap < 1000000:  # Small cap
            reasons.append("Small cap with growth potential")
            score += 0.05

        # Determine signal type and strength
        if score >= 0.65:
            signal_type = 'buy'
            strength = min((score - 0.65) / 0.35, 1.0)
            confidence = 0.6 + (strength * 0.3)
        elif score <= 0.35:
            signal_type = 'sell'
            strength = min((0.35 - score) / 0.35, 1.0)
            confidence = 0.6 + (strength * 0.3)
        else:
            signal_type = 'hold'
            strength = 0.0
            confidence = 0.5

        return MarketSignal(
            token_address=token_address,
            signal_type=signal_type,
            strength=strength,
            confidence=confidence,
            reasons=reasons,
            timestamp=datetime.now(),
            price=price,
            volume_24h=volume_24h,
            liquidity=liquidity
        )

    def calculate_volatility(self, token_address: str) -> float:
        """
        Calculate price volatility for a token.

        Args:
            token_address: Token address

        Returns:
            Volatility score (standard deviation of returns)
        """
        if token_address not in self.price_history:
            return 0.0

        history = self.price_history[token_address]
        if len(history) < 2:
            return 0.0

        # Calculate returns
        returns = []
        for i in range(1, len(history)):
            prev_price = history[i-1]['price']
            curr_price = history[i]['price']
            if prev_price > 0:
                return_pct = (curr_price - prev_price) / prev_price
                returns.append(return_pct)

        if not returns:
            return 0.0

        # Return standard deviation of returns
        return statistics.stdev(returns) if len(returns) > 1 else 0.0

    def get_price_trend(self, token_address: str, periods: int = 10) -> str:
        """
        Determine price trend direction.

        Args:
            token_address: Token address
            periods: Number of periods to analyze

        Returns:
            'uptrend', 'downtrend', or 'sideways'
        """
        if token_address not in self.price_history:
            return 'unknown'

        history = self.price_history[token_address][-periods:]
        if len(history) < 2:
            return 'unknown'

        prices = [h['price'] for h in history]
        first_price = prices[0]
        last_price = prices[-1]

        change_pct = ((last_price - first_price) / first_price * 100) if first_price > 0 else 0

        if change_pct > 5:
            return 'uptrend'
        elif change_pct < -5:
            return 'downtrend'
        else:
            return 'sideways'

    def calculate_risk_score(self, profile: Dict) -> float:
        """
        Calculate risk score for a token (0=low risk, 1=high risk).

        Args:
            profile: Token profile

        Returns:
            Risk score between 0 and 1
        """
        risk_score = 0.0

        # Liquidity risk
        liquidity = profile['liquidity_usd']
        if liquidity < 10000:
            risk_score += 0.4
        elif liquidity < 50000:
            risk_score += 0.2
        elif liquidity < 100000:
            risk_score += 0.1

        # Volatility risk
        token_address = profile['address']
        volatility = self.calculate_volatility(token_address)
        if volatility > 0.1:  # >10% volatility
            risk_score += 0.3
        elif volatility > 0.05:  # >5% volatility
            risk_score += 0.15

        # Age risk (newer pairs are riskier)
        pair_created_at = profile.get('pair_created_at')
        if pair_created_at:
            try:
                created_date = datetime.fromtimestamp(pair_created_at / 1000)
                age_hours = (datetime.now() - created_date).total_seconds() / 3600
                if age_hours < 24:
                    risk_score += 0.3
                elif age_hours < 72:
                    risk_score += 0.15
            except Exception:
                risk_score += 0.2

        return min(risk_score, 1.0)

    def should_trade(self, signal: MarketSignal, min_confidence: float = 0.7) -> bool:
        """
        Determine if a signal warrants trading action.

        Args:
            signal: Market signal to evaluate
            min_confidence: Minimum confidence threshold

        Returns:
            True if should trade, False otherwise
        """
        if signal.signal_type == 'hold':
            return False

        if signal.confidence < min_confidence:
            return False

        if signal.liquidity < self.min_liquidity_usd:
            return False

        return True
