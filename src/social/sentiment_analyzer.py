"""
Sentiment analysis for social media content.
Uses basic NLP techniques and keyword matching.
"""

import re
from typing import Dict, List
from datetime import datetime
from ..monitoring.logger import get_logger

logger = get_logger(__name__)


class SentimentAnalyzer:
    """Analyzes sentiment from social media text."""

    def __init__(self):
        """Initialize sentiment analyzer with keyword lists."""
        # Positive sentiment keywords
        self.positive_keywords = {
            'moon', 'mooning', 'bullish', 'pump', 'pumping', 'gem', 'rocket',
            'buy', 'buying', 'long', 'calls', 'up', 'gain', 'gains', 'profit',
            'profits', 'winner', 'winning', 'breakout', 'rally', 'surge',
            'explosion', 'launched', 'launching', 'ath', 'undervalued',
            'opportunity', 'potential', 'great', 'amazing', 'excellent',
            'huge', 'massive', 'love', 'hodl', 'diamond', 'hands'
        }

        # Negative sentiment keywords
        self.negative_keywords = {
            'dump', 'dumping', 'bearish', 'sell', 'selling', 'short', 'crash',
            'crashing', 'scam', 'rug', 'rugpull', 'dead', 'dying', 'loss',
            'losses', 'losing', 'loser', 'warning', 'avoid', 'danger',
            'dangerous', 'risky', 'careful', 'exit', 'exiting', 'panic',
            'fear', 'fud', 'awful', 'terrible', 'bad', 'worst', 'fail',
            'failed', 'failing', 'worthless', 'overvalued', 'bubble'
        }

        # Strong sentiment modifiers
        self.intensifiers = {
            'very', 'extremely', 'super', 'mega', 'ultra', 'absolutely',
            'definitely', 'certainly', 'really', 'truly', 'highly'
        }

        # Negation words
        self.negations = {
            'not', 'no', 'never', 'neither', 'nobody', 'nothing', 'nowhere',
            'don\'t', 'doesn\'t', 'didn\'t', 'won\'t', 'wouldn\'t', 'can\'t',
            'couldn\'t', 'shouldn\'t', 'isn\'t', 'aren\'t', 'wasn\'t', 'weren\'t'
        }

    def analyze_text(self, text: str) -> Dict:
        """
        Analyze sentiment of a text.

        Args:
            text: Text to analyze

        Returns:
            Dictionary with sentiment analysis results
        """
        # Normalize text
        text_lower = text.lower()
        words = re.findall(r'\b\w+\b', text_lower)

        # Count sentiment keywords
        positive_count = 0
        negative_count = 0
        intensifier_multiplier = 1.0
        negation_active = False

        for i, word in enumerate(words):
            # Check for intensifiers
            if word in self.intensifiers:
                intensifier_multiplier = 1.5
                continue

            # Check for negations
            if word in self.negations:
                negation_active = True
                continue

            # Count sentiment
            multiplier = intensifier_multiplier
            if word in self.positive_keywords:
                if negation_active:
                    negative_count += multiplier
                else:
                    positive_count += multiplier
            elif word in self.negative_keywords:
                if negation_active:
                    positive_count += multiplier
                else:
                    negative_count += multiplier

            # Reset modifiers after sentiment word
            if word in self.positive_keywords or word in self.negative_keywords:
                intensifier_multiplier = 1.0
                negation_active = False

        # Calculate sentiment score (-1 to 1)
        total = positive_count + negative_count
        if total == 0:
            sentiment_score = 0.0
            sentiment_label = 'neutral'
        else:
            sentiment_score = (positive_count - negative_count) / total

            if sentiment_score > 0.3:
                sentiment_label = 'positive'
            elif sentiment_score < -0.3:
                sentiment_label = 'negative'
            else:
                sentiment_label = 'neutral'

        # Normalize score to 0-1 range for consistency
        normalized_score = (sentiment_score + 1) / 2

        return {
            'text': text[:100] + '...' if len(text) > 100 else text,
            'sentiment_score': sentiment_score,
            'normalized_score': normalized_score,
            'sentiment_label': sentiment_label,
            'positive_count': positive_count,
            'negative_count': negative_count,
            'confidence': self._calculate_confidence(positive_count, negative_count)
        }

    def _calculate_confidence(self, positive_count: float, negative_count: float) -> float:
        """
        Calculate confidence in sentiment analysis.

        Args:
            positive_count: Count of positive sentiment
            negative_count: Count of negative sentiment

        Returns:
            Confidence score (0-1)
        """
        total = positive_count + negative_count

        if total == 0:
            return 0.0

        # Higher total and higher difference = higher confidence
        difference = abs(positive_count - negative_count)
        confidence = min((difference / max(total, 1)) * (min(total / 5, 1)), 1.0)

        return confidence

    def analyze_tweets(self, tweets: List[Dict]) -> Dict:
        """
        Analyze sentiment across multiple tweets.

        Args:
            tweets: List of tweet dictionaries

        Returns:
            Aggregated sentiment analysis
        """
        if not tweets:
            return {
                'tweet_count': 0,
                'overall_sentiment': 'neutral',
                'sentiment_score': 0.0,
                'confidence': 0.0,
                'positive_ratio': 0.0,
                'negative_ratio': 0.0,
                'neutral_ratio': 0.0
            }

        sentiments = []
        positive_count = 0
        negative_count = 0
        neutral_count = 0

        for tweet in tweets:
            text = tweet.get('text', '')
            analysis = self.analyze_text(text)
            sentiments.append(analysis)

            label = analysis['sentiment_label']
            if label == 'positive':
                positive_count += 1
            elif label == 'negative':
                negative_count += 1
            else:
                neutral_count += 1

        total = len(tweets)
        positive_ratio = positive_count / total
        negative_ratio = negative_count / total
        neutral_ratio = neutral_count / total

        # Calculate overall sentiment score (weighted average)
        avg_score = sum(s['sentiment_score'] for s in sentiments) / len(sentiments)
        avg_confidence = sum(s['confidence'] for s in sentiments) / len(sentiments)

        # Determine overall sentiment
        if avg_score > 0.2:
            overall_sentiment = 'positive'
        elif avg_score < -0.2:
            overall_sentiment = 'negative'
        else:
            overall_sentiment = 'neutral'

        return {
            'tweet_count': total,
            'overall_sentiment': overall_sentiment,
            'sentiment_score': avg_score,
            'normalized_score': (avg_score + 1) / 2,
            'confidence': avg_confidence,
            'positive_ratio': positive_ratio,
            'negative_ratio': negative_ratio,
            'neutral_ratio': neutral_ratio,
            'timestamp': datetime.now().isoformat()
        }

    def detect_pump_signals(self, text: str) -> bool:
        """
        Detect potential pump and dump signals.

        Args:
            text: Text to analyze

        Returns:
            True if pump signals detected
        """
        text_lower = text.lower()

        # Pump indicators
        pump_indicators = [
            'pump', 'pumping', 'moon', 'mooning', '🚀', '🌙',
            'buy now', 'going to', 'about to', 'get ready',
            'don\'t miss', 'last chance', 'loading up'
        ]

        # Count indicators
        count = sum(1 for indicator in pump_indicators if indicator in text_lower)

        # Detect urgency and hype
        urgency_words = ['now', 'quick', 'fast', 'hurry', 'soon', 'today']
        urgency_count = sum(1 for word in urgency_words if word in text_lower)

        # Multiple indicators + urgency suggests pump signal
        return count >= 2 or (count >= 1 and urgency_count >= 2)

    def detect_coordinated_activity(self, tweets: List[Dict]) -> Dict:
        """
        Detect signs of coordinated promotion activity.

        Args:
            tweets: List of tweet dictionaries

        Returns:
            Dictionary with coordination analysis
        """
        if not tweets:
            return {
                'is_coordinated': False,
                'coordination_score': 0.0,
                'reasons': []
            }

        reasons = []
        coordination_score = 0.0

        # Check for similar content
        texts = [tweet.get('text', '') for tweet in tweets]
        if len(tweets) > 5:
            # Count tweets with pump signals
            pump_tweets = sum(1 for text in texts if self.detect_pump_signals(text))
            pump_ratio = pump_tweets / len(tweets)

            if pump_ratio > 0.5:
                coordination_score += 0.3
                reasons.append(f"High ratio of pump signals ({pump_ratio:.1%})")

        # Check for unusual posting patterns
        if len(tweets) > 20:
            coordination_score += 0.2
            reasons.append(f"High volume of tweets ({len(tweets)})")

        # Check for similar language
        unique_words_per_tweet = []
        for text in texts[:10]:  # Sample first 10
            words = set(re.findall(r'\b\w+\b', text.lower()))
            unique_words_per_tweet.append(words)

        if len(unique_words_per_tweet) > 1:
            # Calculate word overlap
            all_words = set()
            for words in unique_words_per_tweet:
                all_words.update(words)

            common_words = set.intersection(*unique_words_per_tweet) if unique_words_per_tweet else set()
            if len(all_words) > 0:
                overlap_ratio = len(common_words) / len(all_words)
                if overlap_ratio > 0.3:
                    coordination_score += 0.2
                    reasons.append(f"High word overlap ({overlap_ratio:.1%})")

        is_coordinated = coordination_score > 0.4

        return {
            'is_coordinated': is_coordinated,
            'coordination_score': coordination_score,
            'reasons': reasons
        }
