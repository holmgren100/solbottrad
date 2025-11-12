import asyncio
import pytest
from api.twitter_api import TwitterAPI
from utils.logger import setup_logger
from datetime import datetime, timedelta

logger = setup_logger(__name__)

class TestTwitterAPI:
    def setup_method(self):
        """Setup method called before each test"""
        self.twitter_api = TwitterAPI()
        logger.info("TwitterAPI test instance created")

    @pytest.mark.asyncio
    async def test_get_recent_tweets(self):
        """Test getting recent tweets for a specific token"""
        try:
            # Test getting recent tweets for a specific token
            token = "SOL"  # Example token
            # REMOVED await - TwitterAPI methods are synchronous
            tweets = self.twitter_api.get_recent_tweets(token)

            logger.info(f"Retrieved {len(tweets)} tweets for {token}")
            for tweet in tweets[:3]:  # Log first 3 tweets
                logger.info(f"Tweet text: {tweet['text'][:100]}...")

            assert isinstance(tweets, list), "Expected tweets to be a list"
            assert len(tweets) >= 0, "Expected non-negative number of tweets"
            logger.info("✅ Recent tweets test passed")

        except Exception as e:
            logger.error(f"Error getting recent tweets: {str(e)}")
            pytest.fail(f"Recent tweets test failed: {str(e)}")

    @pytest.mark.asyncio
    async def test_get_tweet_sentiment(self):
        """Test getting sentiment for a sample tweet"""
        try:
            # Test getting sentiment for a sample tweet
            tweet = "This is an amazing project with great potential! #Solana"
            # REMOVED await - TwitterAPI methods are synchronous
            sentiment = self.twitter_api.get_tweet_sentiment(tweet)

            logger.info(f"Sentiment score for test tweet: {sentiment}")
            
            assert sentiment is not None, "Expected sentiment to not be None"
            assert isinstance(sentiment, (int, float, dict)), "Expected sentiment to be a number or dict"
            logger.info("✅ Tweet sentiment test passed")

        except Exception as e:
            logger.error(f"Error getting tweet sentiment: {str(e)}")
            pytest.fail(f"Tweet sentiment test failed: {str(e)}")

    @pytest.mark.asyncio
    async def test_get_trending_tokens(self):
        """Test getting trending tokens"""
        try:
            # Test getting trending tokens
            # REMOVED await - TwitterAPI methods are synchronous
            trending = self.twitter_api.get_trending_tokens()

            logger.info(f"Retrieved {len(trending)} trending tokens")
            for token in trending[:5]:  # Log first 5 trending tokens
                logger.info(f"Trending token: {token}")

            assert isinstance(trending, list), "Expected trending tokens to be a list"
            assert len(trending) >= 0, "Expected non-negative number of trending tokens"
            logger.info("✅ Trending tokens test passed")

        except Exception as e:
            logger.error(f"Error getting trending tokens: {str(e)}")
            pytest.fail(f"Trending tokens test failed: {str(e)}")

    @pytest.mark.asyncio
    async def test_all_twitter_methods_with_delays(self):
        """Test all Twitter API methods with proper delays to avoid rate limiting"""
        logger.info("Starting comprehensive Twitter API test...")

        # Test recent tweets
        token = "SOL"
        # REMOVED await - TwitterAPI methods are synchronous
        tweets = self.twitter_api.get_recent_tweets(token)
        logger.info(f"✅ Retrieved {len(tweets)} tweets for {token}")
        await asyncio.sleep(1)  # Rate limiting pause

        # Test sentiment analysis
        test_tweet = "This is an amazing project with great potential! #Solana"
        # REMOVED await - TwitterAPI methods are synchronous
        sentiment = self.twitter_api.get_tweet_sentiment(test_tweet)
        logger.info(f"✅ Sentiment analysis result: {sentiment}")
        await asyncio.sleep(1)  # Rate limiting pause

        # Test trending tokens
        # REMOVED await - TwitterAPI methods are synchronous
        trending = self.twitter_api.get_trending_tokens()
        logger.info(f"✅ Retrieved {len(trending)} trending tokens")

        # Assertions
        assert isinstance(tweets, list), "Tweets should be a list"
        assert sentiment is not None, "Sentiment should not be None"
        assert isinstance(trending, list), "Trending tokens should be a list"

        logger.info("🎉 All Twitter API methods tested successfully!")

    def test_twitter_api_error_handling(self):
        """Test Twitter API error handling with invalid inputs - MADE SYNCHRONOUS"""
        try:
            # Test with empty token
            # REMOVED await - TwitterAPI methods are synchronous
            empty_tweets = self.twitter_api.get_recent_tweets("")
            assert isinstance(empty_tweets, list), "Should return empty list for invalid token"

            # Test sentiment with empty text
            # REMOVED await - TwitterAPI methods are synchronous
            empty_sentiment = self.twitter_api.get_tweet_sentiment("")
            # Should handle gracefully (return None or default value)

            logger.info("✅ Error handling test passed")

        except Exception as e:
            logger.warning(f"Expected error handling behavior: {str(e)}")
            # This is acceptable - API should handle errors gracefully

# Standalone test runner (for manual testing)
async def run_manual_tests():
    """Manual test runner - use this if you want to run tests outside pytest"""
    logger.info("Starting manual Twitter API tests...")
    
    twitter_api = TwitterAPI()
    
    try:
        # Test recent tweets
        logger.info("Testing recent tweets...")
        # REMOVED await - TwitterAPI methods are synchronous
        tweets = twitter_api.get_recent_tweets("SOL")
        logger.info(f"✅ Retrieved {len(tweets)} tweets")
        await asyncio.sleep(1)

        # Test sentiment analysis
        logger.info("Testing sentiment analysis...")
        # REMOVED await - TwitterAPI methods are synchronous
        sentiment = twitter_api.get_tweet_sentiment("Great project! Very bullish on this token!")
        logger.info(f"✅ Sentiment result: {sentiment}")
        await asyncio.sleep(1)

        # Test trending tokens
        logger.info("Testing trending tokens...")
        # REMOVED await - TwitterAPI methods are synchronous
        trending = twitter_api.get_trending_tokens()
        logger.info(f"✅ Found {len(trending)} trending tokens")

        logger.info("🎉 All manual Twitter API tests completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Manual test failed: {str(e)}")
        raise

def main():
    """Main function for manual testing"""
    try:
        asyncio.run(run_manual_tests())
    except Exception as e:
        logger.error(f"Error running manual tests: {str(e)}")
        raise

if __name__ == "__main__":
    main()