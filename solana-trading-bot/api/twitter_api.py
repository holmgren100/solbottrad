import asyncio
import time
from typing import List, Dict, Any, Optional
import tweepy
from utils.logger import setup_logger
from config.settings import settings
from exceptions.custom_exceptions import APIError

class TwitterAPI:
    """
    Twitter API client for fetching tweets and engagement analysis.
    Uses Twitter API v2 with Bearer Token authentication.
    """

    def __init__(self):
        self.logger = setup_logger(__name__)
        
        # Load API credentials from settings
        self.bearer_token = settings.TWITTER_BEARER_TOKEN
        
        # Initialize Twitter client with Bearer Token (API v2)
        try:
            self.client = tweepy.Client(bearer_token=self.bearer_token)
            self.logger.info("Twitter API client initialized successfully")
        except Exception as e:
            error_msg = f"Failed to initialize Twitter API client: {str(e)}"
            self.logger.error(error_msg)
            raise APIError(error_msg)

        # Optional: Initialize API v1.1 client if needed (requires all 4 tokens)
        self.api_v1 = None
        try:
            api_key = getattr(settings, 'TWITTER_API_KEY', None)
            api_secret = getattr(settings, 'TWITTER_API_SECRET', None)
            access_token = getattr(settings, 'TWITTER_ACCESS_TOKEN', None)
            access_token_secret = getattr(settings, 'TWITTER_ACCESS_TOKEN_SECRET', None)
            
            if all([api_key, api_secret, access_token, access_token_secret]):
                auth = tweepy.OAuthHandler(api_key, api_secret)
                auth.set_access_token(access_token, access_token_secret)
                self.api_v1 = tweepy.API(auth)
                self.logger.info("Twitter API v1.1 client initialized successfully")
            else:
                self.logger.info("Twitter API v1.1 credentials not provided, using v2 only")
        except Exception as e:
            self.logger.warning(f"Failed to initialize Twitter API v1.1: {str(e)}")

    def search_tweets(self, query: str, max_results: int = 100) -> List[Dict[str, Any]]:
        """
        Search for tweets about a specific token using Twitter API v2.
        
        Args:
            query: Search query (e.g., token name or hashtag)
            max_results: Maximum number of tweets to fetch (10-100)
            
        Returns:
            List of tweets with metadata
            
        Raises:
            APIError: If the request fails
        """
        try:
            self.logger.debug(f"Searching tweets for query: {query}")
            
            # Ensure max_results is within API limits
            max_results = min(max(max_results, 10), 100)
            
            tweets = self.client.search_recent_tweets(
                query=query,
                max_results=max_results,
                tweet_fields=["created_at", "public_metrics", "author_id"],
                expansions=["author_id"],
                user_fields=["username", "verified"]
            )

            results = []
            if tweets.data:
                # Create user lookup for author information - Fixed includes handling
                users = {}
                if hasattr(tweets, 'includes') and tweets.includes:
                    users = {user.id: user for user in getattr(tweets.includes, "users", [])}
                
                for tweet in tweets.data:
                    author = users.get(tweet.author_id)
                    
                    # Handle missing public_metrics
                    metrics = getattr(tweet, 'public_metrics', {}) or {}
                    
                    results.append({
                        "id": tweet.id,
                        "text": tweet.text,
                        "created_at": tweet.created_at.isoformat() if tweet.created_at else None,
                        "metrics": {
                            "like_count": metrics.get("like_count", 0),
                            "retweet_count": metrics.get("retweet_count", 0),
                            "reply_count": metrics.get("reply_count", 0),
                            "quote_count": metrics.get("quote_count", 0)
                        },
                        "author": {
                            "id": tweet.author_id,
                            "username": getattr(author, 'username', 'unknown') if author else 'unknown',
                            "verified": getattr(author, 'verified', False) if author else False
                        }
                    })
                    
                self.logger.info(f"Successfully fetched {len(results)} tweets for query: {query}")
            else:
                self.logger.warning(f"No tweets found for query: {query}")

            return results
            
        except tweepy.TooManyRequests:
            error_msg = f"Twitter API rate limit exceeded for query: {query}"
            self.logger.error(error_msg)
            raise APIError(error_msg)
        except Exception as e:
            error_msg = f"Twitter API error: {str(e)}"
            self.logger.error(error_msg)
            raise APIError(error_msg)

    def get_recent_tweets(self, token_symbol: str, count: int = 10) -> List[Dict[str, Any]]:
        """
        Fetch recent tweets for a specific token (method name expected by tests).
        
        Args:
            token_symbol: Token symbol (e.g., SOL, BTC)
            count: Number of tweets to fetch
            
        Returns:
            List of tweet data dictionaries
        """
        try:
            query = f"#{token_symbol} OR ${token_symbol} OR {token_symbol}"
            return self.search_tweets(query, max_results=count)
        except Exception as e:
            self.logger.error(f"Error fetching recent tweets for {token_symbol}: {e}")
            return []

    def get_tweets(self, query: str, count: int = 10) -> List[str]:
        """
        Fetch recent tweets based on a query (simplified version returning only text).
        
        Args:
            query: Search query (e.g., token name or hashtag)
            count: Number of tweets to fetch
            
        Returns:
            List of tweet texts
        """
        try:
            tweets_data = self.search_tweets(query, max_results=count)
            return [tweet["text"] for tweet in tweets_data]
        except Exception as e:
            self.logger.error(f"Error fetching tweets: {e}")
            return []

    def get_tweet_sentiment(self, tweet_text: str) -> Dict[str, Any]:
        """
        Analyze sentiment of a single tweet text (basic implementation).
        
        Args:
            tweet_text: The tweet text to analyze
            
        Returns:
            Dictionary containing basic sentiment analysis
        """
        try:
            # Basic sentiment analysis based on keywords
            positive_words = ['good', 'great', 'amazing', 'bullish', 'moon', 'pump', 'buy', 'hold']
            negative_words = ['bad', 'terrible', 'bearish', 'dump', 'sell', 'crash', 'scam']
            
            text_lower = tweet_text.lower()
            positive_count = sum(1 for word in positive_words if word in text_lower)
            negative_count = sum(1 for word in negative_words if word in text_lower)
            
            if positive_count > negative_count:
                sentiment = "positive"
                score = min(positive_count / (positive_count + negative_count + 1), 1.0)
            elif negative_count > positive_count:
                sentiment = "negative"
                score = -min(negative_count / (positive_count + negative_count + 1), 1.0)
            else:
                sentiment = "neutral"
                score = 0.0
            
            return {
                "sentiment": sentiment,
                "score": score,
                "confidence": abs(score),
                "positive_words": positive_count,
                "negative_words": negative_count
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing tweet sentiment: {e}")
            return {
                "sentiment": "neutral",
                "score": 0.0,
                "confidence": 0.0,
                "positive_words": 0,
                "negative_words": 0
            }

    def get_token_sentiment(self, token_symbol: str) -> Dict[str, Any]:
        """
        Get overall sentiment and engagement metrics for a token.
        
        Args:
            token_symbol: Token symbol (e.g., SOL, BTC)
            
        Returns:
            Dictionary containing sentiment metrics and tweets
            
        Raises:
            APIError: If the request fails
        """
        try:
            self.logger.debug(f"Getting sentiment for token: {token_symbol}")
            
            # Create search query for the token
            query = f"#{token_symbol} OR ${token_symbol} OR {token_symbol}"
            
            # Search for tweets containing the token symbol
            tweets = self.search_tweets(query, max_results=100)

            if not tweets:
                return {
                    "token_symbol": token_symbol,
                    "tweet_count": 0,
                    "total_likes": 0,
                    "total_retweets": 0,
                    "total_replies": 0,
                    "total_quotes": 0,
                    "engagement_score": 0,
                    "average_sentiment": 0.0,
                    "tweets": []
                }

            # Calculate engagement metrics
            total_likes = sum(tweet["metrics"]["like_count"] for tweet in tweets)
            total_retweets = sum(tweet["metrics"]["retweet_count"] for tweet in tweets)
            total_replies = sum(tweet["metrics"]["reply_count"] for tweet in tweets)
            total_quotes = sum(tweet["metrics"]["quote_count"] for tweet in tweets)
            
            # Calculate engagement score
            engagement_score = total_likes + (total_retweets * 2) + total_replies + total_quotes

            # Calculate average sentiment
            sentiment_scores = []
            for tweet in tweets:
                sentiment_data = self.get_tweet_sentiment(tweet["text"])
                sentiment_scores.append(sentiment_data["score"])
            
            average_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0.0

            sentiment_data = {
                "token_symbol": token_symbol,
                "tweet_count": len(tweets),
                "total_likes": total_likes,
                "total_retweets": total_retweets,
                "total_replies": total_replies,
                "total_quotes": total_quotes,
                "engagement_score": engagement_score,
                "average_engagement": engagement_score / len(tweets) if tweets else 0,
                "average_sentiment": average_sentiment,
                "tweets": tweets[:10]  # Return top 10 tweets
            }
            
            self.logger.info(
                f"Token sentiment for {token_symbol}: "
                f"{len(tweets)} tweets, engagement score: {engagement_score}, "
                f"avg sentiment: {average_sentiment:.2f}"
            )
            
            return sentiment_data
            
        except Exception as e:
            error_msg = f"Error getting token sentiment: {str(e)}"
            self.logger.error(error_msg)
            raise APIError(error_msg)

    def get_trending_tokens(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get trending cryptocurrency tokens from Twitter (synchronous method).
        
        Args:
            limit: Number of trending tokens to return
            
        Returns:
            List of trending token information
        """
        try:
            # Common crypto-related hashtags and terms
            crypto_terms = [
                "#crypto", "#cryptocurrency", "#altcoin", "#memecoin",
                "#solana", "#ethereum", "#bitcoin", "#defi"
            ]
            
            trending_data = []
            
            for term in crypto_terms[:limit]:
                try:
                    tweets = self.search_tweets(term, max_results=50)
                    if tweets:
                        total_engagement = sum(
                            tweet["metrics"]["like_count"] + 
                            tweet["metrics"]["retweet_count"] 
                            for tweet in tweets
                        )
                        
                        trending_data.append({
                            "term": term,
                            "tweet_count": len(tweets),
                            "total_engagement": total_engagement,
                            "recent_tweets": tweets[:3]  # Top 3 recent tweets
                        })
                    
                    # Add small delay to avoid rate limiting
                    time.sleep(0.25)
                    
                except Exception as e:
                    self.logger.warning(f"Error fetching data for term {term}: {e}")
                    continue
            
            # Sort by engagement
            trending_data.sort(key=lambda x: x["total_engagement"], reverse=True)
            
            self.logger.info(f"Successfully fetched trending data for {len(trending_data)} terms")
            return trending_data
            
        except Exception as e:
            error_msg = f"Error getting trending tokens: {str(e)}"
            self.logger.error(error_msg)
            raise APIError(error_msg)

# Test function
async def test_twitter_api():
    """Test function for Twitter API"""
    try:
        twitter_api = TwitterAPI()
        
        # Test basic tweet search
        print("Testing tweet search...")
        tweets = twitter_api.get_tweets("Solana", count=5)
        print(f"Found {len(tweets)} tweets about Solana")
        
        # Test recent tweets (method expected by tests)
        print("\nTesting recent tweets...")
        recent_tweets = twitter_api.get_recent_tweets("SOL", count=5)
        print(f"Found {len(recent_tweets)} recent tweets about SOL")
        
        # Test tweet sentiment
        print("\nTesting tweet sentiment...")
        if recent_tweets:
            sentiment = twitter_api.get_tweet_sentiment(recent_tweets[0]["text"])
            print(f"Tweet sentiment: {sentiment}")
        
        # Test token sentiment
        print("\nTesting token sentiment...")
        token_sentiment = twitter_api.get_token_sentiment("SOL")
        print(f"SOL sentiment: {token_sentiment['tweet_count']} tweets, "
              f"engagement score: {token_sentiment['engagement_score']}")
        
        # Test trending tokens
        print("\nTesting trending tokens...")
        trending = twitter_api.get_trending_tokens(limit=3)
        print(f"Found {len(trending)} trending terms")
        
        return tweets, token_sentiment, trending
        
    except Exception as e:
        print(f"Test failed: {e}")
        return None, None, None

# Example usage
if __name__ == "__main__":
    asyncio.run(test_twitter_api())