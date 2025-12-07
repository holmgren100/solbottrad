"""
CoinGecko API client for crypto market data.
Provides top gainers/losers, trending tokens, and market data across all chains.
"""

import aiohttp
from typing import Dict, List, Optional
from datetime import datetime
from ..monitoring.logger import get_logger

logger = get_logger(__name__)


class CoinGeckoClient:
    """Client for CoinGecko API - Multi-chain crypto data aggregator."""

    # Cycling strategies for token discovery
    DISCOVERY_CYCLES = [
        'top_gainers',      # Cycle 1: Top gainers (biggest price increases)
        'trending',         # Cycle 2: Trending searches
        'top_losers',       # Cycle 3: Top losers (for reversal opportunities)
    ]

    def __init__(self, api_key: str):
        """
        Initialize CoinGecko client.

        Args:
            api_key: CoinGecko API key (Demo/Pro/Enterprise)
        """
        self.api_key = api_key
        self.base_url = "https://api.coingecko.com/api/v3"
        self.session: Optional[aiohttp.ClientSession] = None
        self.current_cycle = 0  # Track which discovery cycle we're on

    async def _ensure_session(self):
        """Ensure aiohttp session exists."""
        if self.session is None or self.session.closed:
            headers = {
                "x-cg-demo-api-key": self.api_key,
                "accept": "application/json"
            }
            self.session = aiohttp.ClientSession(headers=headers)

    async def close(self):
        """Close the aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()

    async def health_check(self) -> bool:
        """Check if CoinGecko API is accessible."""
        try:
            await self._ensure_session()
            url = f"{self.base_url}/ping"

            async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                return response.status == 200
        except Exception as e:
            logger.error(f"CoinGecko health check failed: {e}")
            return False

    async def get_top_gainers_losers(self, vs_currency: str = "usd", duration: str = "24h",
                                      top_coins: str = "1000") -> Dict[str, List[Dict]]:
        """
        Get top gainers and losers by price change.

        Args:
            vs_currency: Currency for price comparison (default: usd)
            duration: Time period (1h, 24h)
            top_coins: Top N coins by market cap to consider (default: 1000)

        Returns:
            Dictionary with 'top_gainers' and 'top_losers' lists
        """
        await self._ensure_session()

        try:
            url = f"{self.base_url}/coins/top_gainers_losers"
            params = {
                "vs_currency": vs_currency,
                "duration": duration,
                "top_coins": top_coins
            }

            async with self.session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=15)) as response:
                if response.status == 200:
                    data = await response.json()

                    gainers = data.get('top_gainers', [])
                    losers = data.get('top_losers', [])

                    # Filter for Solana tokens only (check platforms)
                    solana_gainers = []
                    for token in gainers:
                        platforms = token.get('platforms', {})
                        if 'solana' in platforms or token.get('symbol', '').upper() == 'SOL':
                            solana_gainers.append({
                                'address': platforms.get('solana', token.get('id')),
                                'symbol': token.get('symbol'),
                                'name': token.get('name'),
                                'price_change_24h': token.get('usd_24h_change', 0),
                                'market_cap_rank': token.get('market_cap_rank', 999),
                                'coingecko_id': token.get('id'),
                            })

                    logger.info(f"Retrieved {len(solana_gainers)} Solana GAINERS from CoinGecko (total: {len(gainers)})")
                    return {
                        'top_gainers': solana_gainers,
                        'top_losers': []  # Not using losers for now
                    }

                elif response.status == 401:
                    logger.error(f"CoinGecko 401 Unauthorized - Check API key!")
                    return {'top_gainers': [], 'top_losers': []}
                elif response.status == 429:
                    logger.warning("CoinGecko API rate limit reached (30 calls/min)")
                    return {'top_gainers': [], 'top_losers': []}
                else:
                    error_text = await response.text()
                    logger.warning(f"CoinGecko top gainers/losers error {response.status}: {error_text[:200]}")
                    return {'top_gainers': [], 'top_losers': []}

        except Exception as e:
            logger.error(f"Error fetching top gainers/losers from CoinGecko: {e}")
            return {'top_gainers': [], 'top_losers': []}

    async def get_trending(self) -> List[Dict]:
        """
        Get trending search tokens (most searched in last 24h).

        Returns:
            List of trending token dictionaries
        """
        await self._ensure_session()

        try:
            url = f"{self.base_url}/search/trending"

            async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as response:
                if response.status == 200:
                    data = await response.json()

                    coins = data.get('coins', [])

                    # Filter for Solana tokens
                    solana_trending = []
                    for item in coins:
                        coin = item.get('item', {})
                        platforms = coin.get('data', {}).get('platforms', {})

                        if 'solana' in platforms or coin.get('symbol', '').upper() == 'SOL':
                            solana_trending.append({
                                'address': platforms.get('solana', coin.get('id')),
                                'symbol': coin.get('symbol'),
                                'name': coin.get('name'),
                                'market_cap_rank': coin.get('market_cap_rank', 999),
                                'coingecko_id': coin.get('id'),
                            })

                    logger.info(f"Retrieved {len(solana_trending)} Solana TRENDING tokens from CoinGecko (total: {len(coins)})")
                    return solana_trending

                elif response.status == 401:
                    logger.error(f"CoinGecko 401 Unauthorized - Check API key!")
                    return []
                elif response.status == 429:
                    logger.warning("CoinGecko API rate limit reached (30 calls/min)")
                    return []
                else:
                    error_text = await response.text()
                    logger.warning(f"CoinGecko trending error {response.status}: {error_text[:200]}")
                    return []

        except Exception as e:
            logger.error(f"Error fetching trending tokens from CoinGecko: {e}")
            return []

    async def get_tokens_by_cycle(self, limit: int = 30) -> List[Dict]:
        """
        Get tokens using CYCLING strategy (rotates between gainers/trending).

        Rotates through 3 discovery methods:
        1. top_gainers - Biggest price increases
        2. trending - Most searched tokens
        3. top_losers - Reversal opportunities

        Args:
            limit: Maximum number of tokens to return

        Returns:
            List of token dictionaries
        """
        # Get current cycle
        cycle_type = self.DISCOVERY_CYCLES[self.current_cycle]
        logger.info(f"CoinGecko Cycle {self.current_cycle + 1}/3: Using '{cycle_type}' discovery")

        tokens = []
        if cycle_type == 'top_gainers':
            data = await self.get_top_gainers_losers(duration="24h")
            tokens = data.get('top_gainers', [])[:limit]
        elif cycle_type == 'trending':
            tokens = await self.get_trending()
            tokens = tokens[:limit]
        elif cycle_type == 'top_losers':
            data = await self.get_top_gainers_losers(duration="24h")
            tokens = data.get('top_losers', [])[:limit]

        # Advance to next cycle for next scan
        self.current_cycle = (self.current_cycle + 1) % len(self.DISCOVERY_CYCLES)

        logger.info(f"Retrieved {len(tokens)} tokens using '{cycle_type}' (Next cycle: {self.DISCOVERY_CYCLES[self.current_cycle]})")
        return tokens

    async def get_token_market_data(self, coingecko_id: str) -> Optional[Dict]:
        """
        Get detailed market data for a specific token.

        Args:
            coingecko_id: CoinGecko token ID

        Returns:
            Token market data dictionary or None
        """
        await self._ensure_session()

        try:
            url = f"{self.base_url}/coins/{coingecko_id}"
            params = {
                "localization": "false",
                "tickers": "false",
                "market_data": "true",
                "community_data": "false",
                "developer_data": "false"
            }

            async with self.session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    data = await response.json()
                    market_data = data.get('market_data', {})

                    return {
                        'coingecko_id': coingecko_id,
                        'symbol': data.get('symbol'),
                        'name': data.get('name'),
                        'price': market_data.get('current_price', {}).get('usd', 0),
                        'market_cap': market_data.get('market_cap', {}).get('usd', 0),
                        'volume_24h': market_data.get('total_volume', {}).get('usd', 0),
                        'price_change_24h': market_data.get('price_change_percentage_24h', 0),
                        'price_change_7d': market_data.get('price_change_percentage_7d', 0),
                        'liquidity': market_data.get('total_volume', {}).get('usd', 0),  # Approximate
                    }
                elif response.status == 404:
                    logger.debug(f"Token {coingecko_id} not found in CoinGecko")
                    return None
                else:
                    logger.warning(f"CoinGecko market data error: {response.status}")
                    return None

        except Exception as e:
            logger.error(f"Error fetching token market data from CoinGecko: {e}")
            return None
