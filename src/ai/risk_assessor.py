import logging
from typing import Dict, Optional
from dataclasses import dataclass

@dataclass
class RiskAssessment:
    risk_score: float  # 0.0 (low risk) to 1.0 (high risk)
    recommended_position_size: float  # In USD
    warnings: list
    approved: bool

class RiskAssessor:
    """Assess risk and recommend position sizing"""

    def __init__(self, max_position_size: float = 100.0):
        self.max_position_size = max_position_size
        self.logger = logging.getLogger('trading_bot.risk_assessor')

    def assess(
        self,
        token_data: Dict,
        prediction_confidence: float,
        sentiment_score: float,
        current_portfolio_value: float
    ) -> RiskAssessment:
        """Assess risk for a trading opportunity"""
        try:
            warnings = []
            risk_score = 0.5  # Start at medium risk

            # Extract token metrics
            liquidity = float(token_data.get('liquidity', {}).get('usd', 0))
            volume_24h = float(token_data.get('volume', {}).get('h24', 0))
            price_change_24h = float(token_data.get('priceChange', {}).get('h24', 0))

            # Risk factors

            # 1. Liquidity risk
            if liquidity < 5000:
                risk_score += 0.3
                warnings.append("Very low liquidity")
            elif liquidity < 10000:
                risk_score += 0.15
                warnings.append("Low liquidity")

            # 2. Volume risk
            if volume_24h < 1000:
                risk_score += 0.2
                warnings.append("Very low volume")
            elif volume_24h < 5000:
                risk_score += 0.1
                warnings.append("Low volume")

            # 3. Volatility risk
            if abs(price_change_24h) > 50:
                risk_score += 0.25
                warnings.append("Extreme volatility")
            elif abs(price_change_24h) > 20:
                risk_score += 0.1
                warnings.append("High volatility")

            # 4. Prediction confidence (FIXED: Set minimum to 0.4)
            confidence_factor = max(prediction_confidence, 0.4)
            if confidence_factor < 0.5:
                warnings.append("Low prediction confidence")

            # Clamp risk score
            risk_score = min(max(risk_score, 0.0), 1.0)

            # Calculate position size
            recommended_position = self._calculate_position_size(
                risk_score,
                confidence_factor,
                sentiment_score,
                liquidity,
                current_portfolio_value
            )

            # Approve trade if position size is reasonable (FIXED: Lowered threshold to 0.05)
            if recommended_position < 0.05:
                warnings.append("Position size too small")
                approved = False
            else:
                approved = True

            return RiskAssessment(
                risk_score=risk_score,
                recommended_position_size=recommended_position,
                warnings=warnings,
                approved=approved
            )

        except Exception as e:
            self.logger.error(f"Error in risk assessment: {e}")
            return RiskAssessment(
                risk_score=1.0,
                recommended_position_size=0.0,
                warnings=["Error in risk assessment"],
                approved=False
            )

    def _calculate_position_size(
        self,
        risk_score: float,
        prediction_confidence: float,
        sentiment_score: float,
        liquidity: float,
        portfolio_value: float
    ) -> float:
        """Calculate recommended position size based on risk factors"""

        # Start with max position size
        position = self.max_position_size

        # Adjust for risk (lower risk = larger position)
        risk_factor = 1.0 - (risk_score * 0.5)  # Risk reduces position by up to 50%
        position *= risk_factor

        # Adjust for confidence
        position *= prediction_confidence

        # Adjust for sentiment (-1 to 1, we want positive sentiment)
        sentiment_factor = (sentiment_score + 1) / 2  # Normalize to 0-1
        sentiment_factor = max(sentiment_factor, 0.5)  # Don't reduce below 50%
        position *= sentiment_factor

        # Adjust for liquidity (FIXED: For high liquidity tokens, use full position)
        if liquidity > 10000:
            liquidity_factor = 1.0
        else:
            liquidity_factor = min(self.max_position_size / max(liquidity * 0.05, 1), 1.0)
        position *= liquidity_factor

        # Don't exceed max position size or portfolio percentage
        max_portfolio_percent = 0.1  # Max 10% of portfolio
        position = min(position, portfolio_value * max_portfolio_percent, self.max_position_size)

        return round(position, 2)
