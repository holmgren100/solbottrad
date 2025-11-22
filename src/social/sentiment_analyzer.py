import logging
from typing import List, Dict
from dataclasses import dataclass

@dataclass
class SentimentScore:
    sentiment: str  # 'positive', 'negative', 'neutral'
    score: float  # -1.0 to 1.0
    confidence: float  # 0.0 to 1.0
    tweet_count: int

class SentimentAnalyzer:
    """Analyze social sentiment from tweets and other sources"""

    def __init__(self):
        self.logger = logging.getLogger('trading_bot.sentiment')
        # Positive and negative keywords for basic sentiment
        self.positive_keywords = ['bullish', 'moon', 'buy', 'pump', 'gem', 'lfg', 'hodl', 'lambo', 'rocket', '🚀', '📈', '💎']
        self.negative_keywords = ['bearish', 'dump', 'sell', 'rug', 'scam', 'avoid', 'rekt', 'crash', '📉', '💩']

    async def analyze_tweets(self, tweets: List[Dict]) -> SentimentScore:
        """Analyze sentiment from tweets"""
        if not tweets:
            self.logger.debug("No tweets to analyze")
            return SentimentScore(
                sentiment='neutral',
                score=0.0,
                confidence=0.0,
                tweet_count=0
            )

        try:
            sentiments = []

            for tweet in tweets:
                text = tweet.get('text', '').lower()

                # Count positive and negative keywords
                positive_count = sum(1 for keyword in self.positive_keywords if keyword in text)
                negative_count = sum(1 for keyword in self.negative_keywords if keyword in text)

                # Calculate tweet sentiment
                if positive_count > negative_count:
                    sentiments.append(0.5 + (positive_count * 0.1))
                elif negative_count > positive_count:
                    sentiments.append(-0.5 - (negative_count * 0.1))
                else:
                    sentiments.append(0.0)

            # Aggregate sentiment
            if sentiments:
                avg_sentiment = sum(sentiments) / len(sentiments)
                avg_sentiment = max(min(avg_sentiment, 1.0), -1.0)  # Clamp to [-1, 1]

                # Determine overall sentiment
                if avg_sentiment > 0.2:
                    sentiment_label = 'positive'
                elif avg_sentiment < -0.2:
                    sentiment_label = 'negative'
                else:
                    sentiment_label = 'neutral'

                # Confidence based on tweet count
                confidence = min(len(tweets) / 20, 1.0)  # Max confidence at 20+ tweets

                return SentimentScore(
                    sentiment=sentiment_label,
                    score=avg_sentiment,
                    confidence=confidence,
                    tweet_count=len(tweets)
                )

        except Exception as e:
            self.logger.error(f"Error analyzing sentiment: {e}")

        return SentimentScore(
            sentiment='neutral',
            score=0.0,
            confidence=0.0,
            tweet_count=0
        )

    def analyze_text(self, text: str) -> float:
        """Analyze sentiment of a single text (-1.0 to 1.0)"""
        text_lower = text.lower()

        positive_count = sum(1 for keyword in self.positive_keywords if keyword in text_lower)
        negative_count = sum(1 for keyword in self.negative_keywords if keyword in text_lower)

        if positive_count > negative_count:
            return 0.5 + (positive_count * 0.1)
        elif negative_count > positive_count:
            return -0.5 - (negative_count * 0.1)
        else:
            return 0.0
