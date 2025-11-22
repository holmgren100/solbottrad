import logging
from typing import List, Dict, Optional
import aiohttp

class TwitterClient:
    """Client for Twitter API - Social sentiment data"""

    def __init__(self, bearer_token: Optional[str] = None):
        self.bearer_token = bearer_token
        self.base_url = "https://api.twitter.com/2"
        self.logger = logging.getLogger('trading_bot.twitter')
        self.enabled = bool(bearer_token)

    async def search_tweets(self, query: str, max_results: int = 10) -> List[Dict]:
        """Search for tweets matching query"""
        if not self.enabled:
            self.logger.debug("Twitter client disabled (no bearer token)")
            return []

        try:
            headers = {
                'Authorization': f'Bearer {self.bearer_token}'
            }

            params = {
                'query': query,
                'max_results': min(max_results, 100),
                'tweet.fields': 'created_at,public_metrics,lang'
            }

            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/tweets/search/recent"

                async with session.get(url, headers=headers, params=params, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get('data', [])
                    else:
                        error_text = await response.text()
                        self.logger.error(f"Twitter API error: {response.status} - {error_text}")
                        return []

        except Exception as e:
            self.logger.error(f"Error fetching tweets: {e}")
            return []

    async def get_token_mentions(self, token_symbol: str, token_address: str) -> List[Dict]:
        """Get recent mentions of a token"""
        # Search for both symbol and address
        queries = [
            f'${token_symbol} -is:retweet lang:en',
            f'{token_address[:8]} -is:retweet lang:en'
        ]

        all_tweets = []
        for query in queries:
            tweets = await self.search_tweets(query, max_results=10)
            all_tweets.extend(tweets)

        return all_tweets

    async def is_connected(self) -> bool:
        """Check if API is accessible"""
        if not self.enabled:
            return False

        try:
            headers = {
                'Authorization': f'Bearer {self.bearer_token}'
            }

            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/tweets/search/recent?query=bitcoin&max_results=10"

                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    return response.status == 200
        except:
            return False
