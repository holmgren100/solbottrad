"""
Risk assessment system for evaluating trading opportunities.
"""

from typing import Dict, List
from datetime import datetime
from dataclasses import dataclass
from ..monitoring.logger import get_logger

logger = get_logger(__name__)


@dataclass
class RiskAssessment:
    """Represents a comprehensive risk assessment."""
    token_address: str
    overall_risk: str  # 'low', 'medium', 'high', 'extreme'
    risk_score: float  # 0-1 (0=low risk, 1=extreme risk)
    confidence: float  # 0-1
    risk_factors: Dict[str, float]
    warnings: List[str]
    recommended_position_size: float  # 0-1 (percentage of max position)
    should_trade: bool
    timestamp: datetime


class RiskAssessor:
    """Assesses risk for trading decisions."""

    def __init__(self, max_position_size: float = 100.0):
        """
        Initialize risk assessor.

        Args:
            max_position_size: Maximum position size in USD
        """
        self.max_position_size = max_position_size

    def assess_risk(
        self,
        token_address: str,
        market_data: Dict,
        security_data: Dict,
        sentiment_score: Dict,
        price_prediction: Dict
    ) -> RiskAssessment:
        """
        Perform comprehensive risk assessment.

        Args:
            token_address: Token address
            market_data: Market data including liquidity, volume
            security_data: Security analysis from SolSniffer
            sentiment_score: Sentiment analysis results
            price_prediction: Price prediction results

        Returns:
            RiskAssessment with comprehensive analysis
        """
        risk_factors = {}
        warnings = []

        # 1. Liquidity Risk
        liquidity = market_data.get('liquidity_usd', 0)
        liquidity_risk = self._assess_liquidity_risk(liquidity)
        risk_factors['liquidity'] = liquidity_risk

        if liquidity_risk > 0.6:
            warnings.append(f"Low liquidity: ${liquidity:,.0f}")
        elif liquidity_risk > 0.4:
            warnings.append(f"Moderate liquidity: ${liquidity:,.0f}")

        # 2. Security Risk
        security_risk = self._assess_security_risk(security_data)
        risk_factors['security'] = security_risk

        if security_risk > 0.7:
            warnings.append("High security risk - potential rug pull indicators")
        elif security_risk > 0.5:
            warnings.append("Moderate security concerns detected")

        # 3. Volatility Risk
        volatility = market_data.get('price_change_24h', 0)
        volatility_risk = self._assess_volatility_risk(volatility)
        risk_factors['volatility'] = volatility_risk

        if abs(volatility) > 50:
            warnings.append(f"Extreme volatility: {volatility:+.1f}% in 24h")
        elif abs(volatility) > 25:
            warnings.append(f"High volatility: {volatility:+.1f}% in 24h")

        # 4. Sentiment Risk
        coordination_risk = sentiment_score.get('coordination_risk', 0.0)
        sentiment_confidence = sentiment_score.get('confidence', 0.5)
        sentiment_risk = self._assess_sentiment_risk(coordination_risk, sentiment_confidence)
        risk_factors['sentiment'] = sentiment_risk

        if coordination_risk > 0.6:
            warnings.append("Possible coordinated pump detected")

        # 5. Prediction Uncertainty
        prediction_confidence = price_prediction.get('confidence', 0.5)
        prediction_risk = 1.0 - prediction_confidence
        risk_factors['prediction_uncertainty'] = prediction_risk

        if prediction_confidence < 0.4:
            warnings.append("Low prediction confidence")

        # 6. Age Risk (new tokens are riskier)
        pair_age = market_data.get('pair_created_at')
        age_risk = self._assess_age_risk(pair_age)
        risk_factors['age'] = age_risk

        if age_risk > 0.6:
            warnings.append("Very new token - high risk")

        # Calculate Overall Risk Score
        weights = {
            'liquidity': 0.25,
            'security': 0.30,
            'volatility': 0.15,
            'sentiment': 0.15,
            'prediction_uncertainty': 0.10,
            'age': 0.05
        }

        overall_risk_score = sum(
            risk_factors[factor] * weights[factor]
            for factor in risk_factors
        )

        # Determine Risk Level
        if overall_risk_score < 0.3:
            overall_risk = 'low'
        elif overall_risk_score < 0.5:
            overall_risk = 'medium'
        elif overall_risk_score < 0.7:
            overall_risk = 'high'
        else:
            overall_risk = 'extreme'

        # Calculate Recommended Position Size
        recommended_position = self._calculate_position_size(
            overall_risk_score,
            liquidity,
            prediction_confidence
        )

        # Determine if Should Trade
        should_trade = self._should_trade_decision(
            overall_risk_score,
            warnings,
            recommended_position
        )

        # Calculate Assessment Confidence
        # Higher confidence if we have all data points
        data_completeness = sum([
            1 if liquidity > 0 else 0,
            1 if security_data else 0,
            1 if sentiment_score else 0,
            1 if prediction_confidence > 0 else 0
        ]) / 4
        confidence = data_completeness * 0.7 + (1.0 - overall_risk_score) * 0.3

        assessment = RiskAssessment(
            token_address=token_address,
            overall_risk=overall_risk,
            risk_score=overall_risk_score,
            confidence=confidence,
            risk_factors=risk_factors,
            warnings=warnings,
            recommended_position_size=recommended_position,
            should_trade=should_trade,
            timestamp=datetime.now()
        )

        logger.debug(
            f"Risk assessment for {token_address[:8]}...: "
            f"{overall_risk} (score: {overall_risk_score:.2f}), "
            f"should_trade: {should_trade}"
        )

        return assessment

    def _assess_liquidity_risk(self, liquidity: float) -> float:
        """
        Assess liquidity risk.

        Args:
            liquidity: Liquidity in USD

        Returns:
            Risk score (0-1)
        """
        if liquidity >= 500000:
            return 0.1
        elif liquidity >= 100000:
            return 0.2
        elif liquidity >= 50000:
            return 0.4
        elif liquidity >= 20000:
            return 0.6
        elif liquidity >= 10000:
            return 0.8
        else:
            return 1.0

    def _assess_security_risk(self, security_data: Dict) -> float:
        """
        Assess security risk from token analysis.

        Args:
            security_data: Security analysis data

        Returns:
            Risk score (0-1)
        """
        if not security_data:
            return 0.5  # Medium risk if no data

        risk_score = 0.0

        # Check for common red flags
        if security_data.get('is_mintable'):
            risk_score += 0.25
        if security_data.get('has_freeze_authority'):
            risk_score += 0.25
        if not security_data.get('is_verified'):
            risk_score += 0.20
        if security_data.get('ownership_renounced') is False:
            risk_score += 0.20
        if security_data.get('has_blacklist'):
            risk_score += 0.10

        return min(risk_score, 1.0)

    def _assess_volatility_risk(self, price_change_24h: float) -> float:
        """
        Assess volatility risk.

        Args:
            price_change_24h: 24h price change percentage

        Returns:
            Risk score (0-1)
        """
        abs_change = abs(price_change_24h)

        if abs_change >= 100:
            return 1.0
        elif abs_change >= 50:
            return 0.8
        elif abs_change >= 25:
            return 0.6
        elif abs_change >= 10:
            return 0.4
        else:
            return 0.2

    def _assess_sentiment_risk(
        self,
        coordination_risk: float,
        sentiment_confidence: float
    ) -> float:
        """
        Assess sentiment-related risk.

        Args:
            coordination_risk: Risk of coordinated activity
            sentiment_confidence: Confidence in sentiment analysis

        Returns:
            Risk score (0-1)
        """
        # High coordination is risky
        base_risk = coordination_risk * 0.7

        # Low confidence adds risk
        confidence_risk = (1.0 - sentiment_confidence) * 0.3

        return base_risk + confidence_risk

    def _assess_age_risk(self, pair_created_at: Optional[int]) -> float:
        """
        Assess risk based on token age.

        Args:
            pair_created_at: Timestamp when pair was created

        Returns:
            Risk score (0-1)
        """
        if not pair_created_at:
            return 0.5  # Medium risk if unknown

        try:
            created_date = datetime.fromtimestamp(pair_created_at / 1000)
            age_hours = (datetime.now() - created_date).total_seconds() / 3600

            if age_hours < 6:
                return 0.9
            elif age_hours < 24:
                return 0.7
            elif age_hours < 72:
                return 0.5
            elif age_hours < 168:  # 1 week
                return 0.3
            else:
                return 0.1

        except Exception:
            return 0.5

    def _calculate_position_size(
        self,
        risk_score: float,
        liquidity: float,
        prediction_confidence: float
    ) -> float:
        """
        Calculate recommended position size.

        Args:
            risk_score: Overall risk score
            liquidity: Token liquidity
            prediction_confidence: Confidence in price prediction

        Returns:
            Recommended position size as percentage of max (0-1)
        """
        # Base position size inversely proportional to risk
        base_size = 1.0 - risk_score

        # Adjust for prediction confidence
        confidence_factor = prediction_confidence

        # Adjust for liquidity (don't risk too much of the liquidity)
        liquidity_factor = min(self.max_position_size / max(liquidity * 0.05, 1), 1.0)

        # Combine factors
        position_size = base_size * confidence_factor * liquidity_factor

        # Ensure reasonable bounds
        return max(min(position_size, 1.0), 0.0)

    def _should_trade_decision(
        self,
        risk_score: float,
        warnings: List[str],
        recommended_position: float
    ) -> bool:
        """
        Decide if trading should proceed.

        Args:
            risk_score: Overall risk score
            warnings: List of risk warnings
            recommended_position: Recommended position size

        Returns:
            True if should trade, False otherwise
        """
        # Don't trade if risk is extreme
        if risk_score > 0.75:
            return False

        # Don't trade if position size is too small
        if recommended_position < 0.1:
            return False

        # Don't trade if there are critical warnings
        critical_keywords = ['rug pull', 'coordinated pump', 'extreme']
        for warning in warnings:
            if any(keyword in warning.lower() for keyword in critical_keywords):
                return False

        return True

    def calculate_stop_loss(
        self,
        entry_price: float,
        risk_tolerance_percent: float = 20.0
    ) -> float:
        """
        Calculate stop loss price.

        Args:
            entry_price: Entry price
            risk_tolerance_percent: Maximum acceptable loss percentage

        Returns:
            Stop loss price
        """
        return entry_price * (1 - risk_tolerance_percent / 100)

    def calculate_take_profit(
        self,
        entry_price: float,
        profit_target_percent: float = 50.0
    ) -> float:
        """
        Calculate take profit price.

        Args:
            entry_price: Entry price
            profit_target_percent: Target profit percentage

        Returns:
            Take profit price
        """
        return entry_price * (1 + profit_target_percent / 100)
