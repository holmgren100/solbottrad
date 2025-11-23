import aiohttp
import logging
from typing import Optional, Dict, List

class DexScreenerClient:
    """Client for DexScreener API - Market data"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.base_url = "https://api.dexscreener.com/latest"
        self.logger = logging.getLogger('trading_bot.dexscreener')
        self.price_cache = {}  # Cache last known good prices

    def _validate_price(self, price: float, token_address: str) -> bool:
        """Validate that price is reasonable and not corrupted data"""
        MIN_PRICE = 1e-12  # Minimum realistic price
        MAX_PRICE = 1e10   # Maximum realistic price

        # Check if price is in reasonable range
        if price <= MIN_PRICE or price >= MAX_PRICE:
            self.logger.warning(f"Price ${price:.2e} outside valid range for {token_address[:12]}...")
            return False

        # Check against cached price if available (reject >90% changes)
        if token_address in self.price_cache:
            last_price = self.price_cache[token_address]
            change_pct = abs((price - last_price) / last_price) * 100

            if change_pct > 90:
                self.logger.warning(f"Suspicious price change {change_pct:.1f}% for {token_address[:12]}... (${last_price:.8f} → ${price:.8f})")
                return False

        return True

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
                            pair_data = pairs[0]

                            # Validate price before returning
                            price = float(pair_data.get('priceUsd', 0))
                            if not self._validate_price(price, token_address):
                                # Return cached data if validation fails
                                self.logger.warning(f"Using last known price for {token_address[:12]}...")
                                if token_address in self.price_cache:
                                    pair_data['priceUsd'] = str(self.price_cache[token_address])
                                else:
                                    return None

                            # Cache valid price
                            else:
                                self.price_cache[token_address] = price

                            return pair_data

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
