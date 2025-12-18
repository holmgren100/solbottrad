"""
Twitter API client for social media monitoring.
"""

import aiohttp
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from ..monitoring.logger import get_logger

logger = get_logger(__name__)


class TwitterClient:
    """Client for Twitter API v2 to monitor cryptocurrency discussions."""

    def __init__(self, bearer_token: Optional[str] = None):
        """
        Initialize Twitter client.

        Args:
            bearer_token: Twitter API Bearer token
        """
        self.bearer_token = bearer_token
        self.base_url = "https://api.twitter.com/2"
        self.session: Optional[aiohttp.ClientSession] = None
        self._enabled = bearer_token is not None

    async def _ensure_session(self):
        """Ensure aiohttp session exists."""
        if not self._enabled:
            return

        if self.session is None or self.session.closed:
            headers = {
                'Authorization': f'Bearer {self.bearer_token}',
                'Content-Type': 'application/json'
            }
            self.session = aiohttp.ClientSession(headers=headers)

    async def close(self):
        """Close the client session."""
        if self.session and not self.session.closed:
            await self.session.close()

    async def search_recent_tweets(
        self,
        query: str,
        max_results: int = 10,
        hours_back: int = 24
    ) -> List[Dict]:
        """
        Search recent tweets matching a query.

        Args:
            query: Search query
            max_results: Maximum number of tweets to return
            hours_back: Hours to look back

        Returns:
            List of tweet dictionaries
        """
        if not self._enabled:
            logger.warning("Twitter client not enabled (no bearer token)")
            return []

        await self._ensure_session()

        try:
            # Calculate start time
            start_time = datetime.utcnow() - timedelta(hours=hours_back)
            start_time_str = start_time.strftime('%Y-%m-%dT%H:%M:%SZ')

            url = f"{self.base_url}/tweets/search/recent"
            params = {
                'query': query,
                'max_results': min(max_results, 100),
                'start_time': start_time_str,
                'tweet.fields': 'created_at,public_metrics,author_id,text',
                'expansions': 'author_id',
                'user.fields': 'username,verified,public_metrics'
            }

            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    tweets = data.get('data', [])
                    users = {u['id']: u for u in data.get('includes', {}).get('users', [])}

                    # Enrich tweets with user data
                    for tweet in tweets:
                        author_id = tweet.get('author_id')
                        if author_id in users:
                            tweet['author'] = users[author_id]

                    logger.debug(f"Retrieved {len(tweets)} tweets for query: {query}")
                    return tweets
                elif response.status == 429:
                    # Rate limit is expected and handled gracefully - use debug
                    logger.debug("Twitter API rate limit reached (using defaults)")
                    return []
                else:
                    logger.error(f"Twitter API error: {response.status}")
                    return []

        except Exception as e:
            logger.error(f"Error searching tweets: {e}")
            return []

    async def get_user_tweets(
        self,
        user_id: str,
        max_results: int = 10
    ) -> List[Dict]:
        """
        Get recent tweets from a specific user.

        Args:
            user_id: Twitter user ID
            max_results: Maximum number of tweets to return

        Returns:
            List of tweet dictionaries
        """
        if not self._enabled:
            logger.warning("Twitter client not enabled (no bearer token)")
            return []

        await self._ensure_session()

        try:
            url = f"{self.base_url}/users/{user_id}/tweets"
            params = {
                'max_results': min(max_results, 100),
                'tweet.fields': 'created_at,public_metrics,text'
            }

            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    tweets = data.get('data', [])
                    logger.debug(f"Retrieved {len(tweets)} tweets for user {user_id}")
                    return tweets
                else:
                    logger.error(f"Twitter API error: {response.status}")
                    return []

        except Exception as e:
            logger.error(f"Error getting user tweets: {e}")
            return []

    async def search_token_mentions(
        self,
        token_symbol: str,
        token_address: str,
        max_results: int = 50
    ) -> List[Dict]:
        """
        Search for tweets mentioning a specific token.

        Args:
            token_symbol: Token symbol (e.g., 'BONK')
            token_address: Token contract address
            max_results: Maximum number of tweets to return

        Returns:
            List of tweet dictionaries
        """
        # Build query with symbol and partial address
        short_address = token_address[:8]
        query = f'({token_symbol} OR ${token_symbol} OR {short_address}) (solana OR sol) -is:retweet lang:en'

        return await self.search_recent_tweets(query, max_results=max_results, hours_back=24)

    def calculate_engagement_score(self, tweet: Dict) -> float:
        """
        Calculate engagement score for a tweet.

        Args:
            tweet: Tweet dictionary

        Returns:
            Engagement score (0-1)
        """
        metrics = tweet.get('public_metrics', {})

        likes = metrics.get('like_count', 0)
        retweets = metrics.get('retweet_count', 0)
        replies = metrics.get('reply_count', 0)

        # Weighted engagement score
        engagement = (likes * 1) + (retweets * 3) + (replies * 2)

        # Normalize to 0-1 scale (logarithmic)
        if engagement <= 0:
            return 0.0

        import math
        # Score ranges: 0-10 = 0-0.3, 10-100 = 0.3-0.6, 100-1000 = 0.6-0.9, 1000+ = 0.9-1.0
        if engagement < 10:
            return engagement / 10 * 0.3
        elif engagement < 100:
            return 0.3 + (math.log10(engagement) - 1) * 0.3
        elif engagement < 1000:
            return 0.6 + (math.log10(engagement) - 2) * 0.3
        else:
            return min(0.9 + (math.log10(engagement) - 3) * 0.1, 1.0)

    def is_influential_user(self, user: Dict) -> bool:
        """
        Determine if a user is influential.

        Args:
            user: User dictionary

        Returns:
            True if user is influential
        """
        if not user:
            return False

        metrics = user.get('public_metrics', {})
        followers = metrics.get('followers_count', 0)
        verified = user.get('verified', False)

        # Consider verified users or users with >10k followers as influential
        return verified or followers > 10000

    async def analyze_token_buzz(
        self,
        token_symbol: str,
        token_address: str
    ) -> Dict:
        """
        Analyze social buzz for a token.

        Args:
            token_symbol: Token symbol
            token_address: Token contract address

        Returns:
            Dictionary with buzz analysis
        """
        tweets = await self.search_token_mentions(token_symbol, token_address)

        if not tweets:
            return {
                'token_symbol': token_symbol,
                'token_address': token_address,
                'tweet_count': 0,
                'total_engagement': 0,
                'avg_engagement_score': 0.0,
                'influential_mentions': 0,
                'buzz_score': 0.0,
                'timestamp': datetime.now().isoformat()
            }

        total_engagement = 0
        engagement_scores = []
        influential_mentions = 0

        for tweet in tweets:
            engagement_score = self.calculate_engagement_score(tweet)
            engagement_scores.append(engagement_score)
            total_engagement += sum(tweet.get('public_metrics', {}).values())

            author = tweet.get('author', {})
            if self.is_influential_user(author):
                influential_mentions += 1

        avg_engagement_score = sum(engagement_scores) / len(engagement_scores) if engagement_scores else 0.0

        # Calculate overall buzz score
        buzz_score = self._calculate_buzz_score(
            len(tweets),
            avg_engagement_score,
            influential_mentions
        )

        return {
            'token_symbol': token_symbol,
            'token_address': token_address,
            'tweet_count': len(tweets),
            'total_engagement': total_engagement,
            'avg_engagement_score': avg_engagement_score,
            'influential_mentions': influential_mentions,
            'buzz_score': buzz_score,
            'timestamp': datetime.now().isoformat()
        }

    def _calculate_buzz_score(
        self,
        tweet_count: int,
        avg_engagement: float,
        influential_mentions: int
    ) -> float:
        """
        Calculate overall buzz score.

        Args:
            tweet_count: Number of tweets
            avg_engagement: Average engagement score
            influential_mentions: Number of influential user mentions

        Returns:
            Buzz score (0-1)
        """
        # Weight factors
        volume_score = min(tweet_count / 100, 1.0) * 0.4
        engagement_score = avg_engagement * 0.4
        influence_score = min(influential_mentions / 10, 1.0) * 0.2

        return volume_score + engagement_score + influence_score

    async def health_check(self) -> bool:
        """
        Check if Twitter API is accessible.

        Returns:
            True if healthy, False otherwise
        """
        if not self._enabled:
            return True  # Consider it healthy if not configured

        await self._ensure_session()

        try:
            # Simple query to test API access
            url = f"{self.base_url}/tweets/search/recent"
            params = {'query': 'crypto', 'max_results': 10}

            async with self.session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=5)) as response:
                return response.status in [200, 429]  # 429 means rate limited but API is working

        except Exception as e:
            logger.error(f"Twitter health check failed: {e}")
            return False
