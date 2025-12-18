"""
AI model for scoring social sentiment signals.
"""

from typing import Dict, List
from datetime import datetime
from dataclasses import dataclass
from ..monitoring.logger import get_logger

logger = get_logger(__name__)


@dataclass
class SentimentScore:
    """Represents a comprehensive sentiment score."""
    overall_score: float  # 0-1
    confidence: float  # 0-1
    social_buzz: float  # 0-1
    sentiment_polarity: float  # 0-1
    coordination_risk: float  # 0-1
    influential_support: float  # 0-1
    recommendation: str  # 'strong_buy', 'buy', 'hold', 'avoid'
    reasoning: List[str]
    timestamp: datetime


class SentimentModel:
    """AI model for comprehensive sentiment analysis and scoring."""

    def __init__(self):
        """Initialize the sentiment model."""
        self.history: Dict[str, List[SentimentScore]] = {}

    def score_sentiment(
        self,
        social_data: Dict,
        sentiment_analysis: Dict,
        coordination_analysis: Dict
    ) -> SentimentScore:
        """
        Generate a comprehensive sentiment score.

        Args:
            social_data: Social buzz data from Twitter
            sentiment_analysis: Sentiment analysis results
            coordination_analysis: Coordination detection results

        Returns:
            SentimentScore with comprehensive analysis
        """
        reasoning = []

        # 1. Social Buzz Score (0-1)
        buzz_score = social_data.get('buzz_score', 0.0)
        if buzz_score > 0.7:
            reasoning.append(f"Strong social buzz ({buzz_score:.2f})")
        elif buzz_score > 0.4:
            reasoning.append(f"Moderate social buzz ({buzz_score:.2f})")
        else:
            reasoning.append(f"Low social buzz ({buzz_score:.2f})")

        # 2. Sentiment Polarity (0-1)
        sentiment_polarity = sentiment_analysis.get('normalized_score', 0.5)
        if sentiment_polarity > 0.7:
            reasoning.append(f"Very positive sentiment ({sentiment_polarity:.2f})")
        elif sentiment_polarity > 0.55:
            reasoning.append(f"Positive sentiment ({sentiment_polarity:.2f})")
        elif sentiment_polarity < 0.3:
            reasoning.append(f"Negative sentiment ({sentiment_polarity:.2f})")

        # 3. Coordination Risk (0-1)
        coordination_risk = coordination_analysis.get('coordination_score', 0.0)
        if coordination_risk > 0.6:
            reasoning.append(f"⚠️ High coordination risk ({coordination_risk:.2f})")
        elif coordination_risk > 0.4:
            reasoning.append(f"Moderate coordination detected ({coordination_risk:.2f})")

        # 4. Influential Support (0-1)
        influential_mentions = social_data.get('influential_mentions', 0)
        total_tweets = social_data.get('tweet_count', 1)
        influential_ratio = influential_mentions / max(total_tweets, 1)
        influential_support = min(influential_ratio * 2, 1.0)  # Scale up

        if influential_support > 0.3:
            reasoning.append(f"Strong influential support ({influential_mentions} mentions)")
        elif influential_support > 0.1:
            reasoning.append(f"Some influential support ({influential_mentions} mentions)")

        # Calculate Overall Score
        # Weighted average with penalties for coordination
        weights = {
            'buzz': 0.25,
            'sentiment': 0.30,
            'influential': 0.25,
            'coordination_penalty': 0.20
        }

        coordination_penalty = 1.0 - coordination_risk

        overall_score = (
            buzz_score * weights['buzz'] +
            sentiment_polarity * weights['sentiment'] +
            influential_support * weights['influential'] +
            coordination_penalty * weights['coordination_penalty']
        )

        # Calculate Confidence
        # Higher confidence with more data and clear signals
        tweet_volume_factor = min(total_tweets / 50, 1.0)
        sentiment_clarity = abs(sentiment_polarity - 0.5) * 2  # 0-1
        confidence = (
            sentiment_analysis.get('confidence', 0.5) * 0.4 +
            tweet_volume_factor * 0.3 +
            sentiment_clarity * 0.3
        )

        # Reduce confidence if high coordination detected
        if coordination_risk > 0.5:
            confidence *= 0.7

        # Generate Recommendation
        recommendation = self._generate_recommendation(
            overall_score,
            confidence,
            coordination_risk
        )

        score = SentimentScore(
            overall_score=overall_score,
            confidence=confidence,
            social_buzz=buzz_score,
            sentiment_polarity=sentiment_polarity,
            coordination_risk=coordination_risk,
            influential_support=influential_support,
            recommendation=recommendation,
            reasoning=reasoning,
            timestamp=datetime.now()
        )

        return score

    def _generate_recommendation(
        self,
        overall_score: float,
        confidence: float,
        coordination_risk: float
    ) -> str:
        """
        Generate trading recommendation.

        Args:
            overall_score: Overall sentiment score
            confidence: Confidence in the analysis
            coordination_risk: Risk of coordinated manipulation

        Returns:
            Recommendation string
        """
        # Avoid if high coordination risk
        if coordination_risk > 0.6:
            return 'avoid'

        # Recommendations based on score and confidence
        # Lowered thresholds - Twitter often unavailable, don't block all trades!
        if overall_score >= 0.75 and confidence >= 0.6:
            return 'strong_buy'
        elif overall_score >= 0.6 and confidence >= 0.5:
            return 'buy'
        elif overall_score >= 0.25:  # Was 0.4 - too high when Twitter unavailable
            return 'hold'
        else:
            return 'avoid'  # Only avoid truly negative sentiment < 0.25

    def record_score(self, token_address: str, score: SentimentScore):
        """
        Record a sentiment score for historical tracking.

        Args:
            token_address: Token address
            score: Sentiment score to record
        """
        if token_address not in self.history:
            self.history[token_address] = []

        self.history[token_address].append(score)

        # Keep only last 100 scores per token
        if len(self.history[token_address]) > 100:
            self.history[token_address] = self.history[token_address][-100:]

    def get_sentiment_trend(self, token_address: str) -> str:
        """
        Analyze sentiment trend for a token.

        Args:
            token_address: Token address

        Returns:
            Trend: 'improving', 'declining', or 'stable'
        """
        if token_address not in self.history or len(self.history[token_address]) < 3:
            return 'unknown'

        recent_scores = self.history[token_address][-5:]
        scores = [s.overall_score for s in recent_scores]

        first_avg = sum(scores[:2]) / 2
        last_avg = sum(scores[-2:]) / 2

        change = last_avg - first_avg

        if change > 0.1:
            return 'improving'
        elif change < -0.1:
            return 'declining'
        else:
            return 'stable'

    def compare_with_history(self, token_address: str, current_score: SentimentScore) -> Dict:
        """
        Compare current score with historical data.

        Args:
            token_address: Token address
            current_score: Current sentiment score

        Returns:
            Comparison analysis
        """
        if token_address not in self.history or not self.history[token_address]:
            return {
                'has_history': False,
                'comparison': 'no_data'
            }

        historical_scores = [s.overall_score for s in self.history[token_address]]
        avg_historical = sum(historical_scores) / len(historical_scores)

        difference = current_score.overall_score - avg_historical

        if difference > 0.2:
            comparison = 'significantly_higher'
        elif difference > 0.1:
            comparison = 'higher'
        elif difference < -0.2:
            comparison = 'significantly_lower'
        elif difference < -0.1:
            comparison = 'lower'
        else:
            comparison = 'similar'

        return {
            'has_history': True,
            'comparison': comparison,
            'historical_avg': avg_historical,
            'current_score': current_score.overall_score,
            'difference': difference
        }
