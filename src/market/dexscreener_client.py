import aiohttp
import logging
from typing import Optional, Dict, List

class DexScreenerClient:
    """Client for DexScreener API - Market data"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.base_url = "https://api.dexscreener.com/latest"
        self.logger = logging.getLogger('trading_bot.dexscreener')

    async def get_token_data(self, token_address: str) -> Optional[Dict]:
        """Get token market data from DexScreener"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/dex/tokens/{token_address}"

                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        data = await response.json()

                        if data.get('pairs') and len(data['pairs']) > 0:
                            # Get the most liquid pair
                            pairs = sorted(data['pairs'], key=lambda x: float(x.get('liquidity', {}).get('usd', 0)), reverse=True)
                            return pairs[0]  # Return most liquid pair

                        self.logger.warning(f"No pairs found for token {token_address}")
                        return None
                    else:
                        self.logger.warning(f"DexScreener API returned status {response.status} for {token_address}")
                        return None
        except Exception as e:
            self.logger.error(f"Error fetching token data from DexScreener: {e}")
            return None

    async def get_pair_data(self, pair_address: str) -> Optional[Dict]:
        """Get specific pair data"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/dex/pairs/solana/{pair_address}"

                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('pair'):
                            return data['pair']
                    return None
        except Exception as e:
            self.logger.error(f"Error fetching pair data: {e}")
            return None

    async def search_tokens(self, query: str) -> List[Dict]:
        """Search for tokens"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/dex/search?q={query}"

                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get('pairs', [])
                    return []
        except Exception as e:
            self.logger.error(f"Error searching tokens: {e}")
            return []

    async def is_connected(self) -> bool:
        """Check if API is accessible"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/dex/tokens/So11111111111111111111111111111111111111112"  # SOL address
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    return response.status == 200
        except:
            return False
