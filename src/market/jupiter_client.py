"""
Jupiter API client for token discovery.
"""

import aiohttp
from typing import Dict, List, Optional
from datetime import datetime
from ..monitoring.logger import get_logger

logger = get_logger(__name__)


class JupiterClient:
    """Client for Jupiter Token API v2 to discover new tokens."""

    # Cycling strategies for token discovery
    DISCOVERY_CYCLES = [
        'toporganicscore',  # Cycle 1: Organic activity (filters bots)
        'toptraded',        # Cycle 2: Highest traded volume
        'toptrending'       # Cycle 3: Trending tokens
    ]

    def __init__(self):
        """Initialize Jupiter client (no API key needed)."""
        self.base_url = "https://lite-api.jup.ag/tokens/v2"
        self.session: Optional[aiohttp.ClientSession] = None
        self.current_cycle = 0  # Track which discovery cycle we're on

    async def _ensure_session(self):
        """Ensure aiohttp session exists."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()

    async def close(self):
        """Close the client session."""
        if self.session and not self.session.closed:
            await self.session.close()

    async def get_recent_tokens(self, limit: int = 50) -> List[Dict]:
        """
        Get recently created tokens from Jupiter.

        This returns tokens that just had their first pool created.

        Args:
            limit: Maximum number of tokens to retrieve (default: 50)

        Returns:
            List of token dictionaries with mint addresses and metadata
        """
        await self._ensure_session()

        try:
            url = f"{self.base_url}/recent"
            params = {'limit': limit}

            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()

                    # DEBUG: Log first token to see structure
                    if data and len(data) > 0:
                        logger.info(f"Sample Jupiter token data: {data[0]}")

                    # Jupiter returns array of token objects
                    # NOTE: Jupiter uses 'id' for the mint address, not 'address'!
                    # Convert to our standard format
                    tokens = []
                    for token in data:
                        # Jupiter uses 'id' for the token mint address
                        token_address = token.get('id') or token.get('address')
                        if not token_address:
                            logger.warning(f"Token missing id/address: {token}")
                            continue

                        tokens.append({
                            'address': token_address,
                            'symbol': token.get('symbol'),
                            'name': token.get('name'),
                            'decimals': token.get('decimals'),
                            'logoURI': token.get('icon') or token.get('logoURI'),  # Jupiter uses 'icon'
                            'tags': token.get('tags') or [],  # Handle null/None from API
                            'liquidity': token.get('liquidity'),
                            'fdv': token.get('fdv'),
                            'mcap': token.get('mcap'),
                            'usdPrice': token.get('usdPrice'),
                            'holderCount': token.get('holderCount'),
                            'audit': token.get('audit') or {},  # Handle null/None from API
                            'launchpad': token.get('launchpad'),
                            'createdAt': token.get('createdAt')
                        })

                    logger.info(f"Retrieved {len(tokens)} recent tokens from Jupiter")
                    return tokens
                else:
                    logger.error(f"Jupiter API error: {response.status}")
                    return []

        except Exception as e:
            logger.error(f"Error fetching recent tokens from Jupiter: {e}")
            return []

    async def get_trending_tokens(
        self,
        category: str = None,  # If None, uses cycling
        interval: str = '1h',
        limit: int = 50
    ) -> List[Dict]:
        """
        Get trending/top tokens using CYCLING strategy.

        Rotates through 3 discovery methods:
        1. toporganicscore - Organic activity (filters bots)
        2. toptraded - Highest traded volume
        3. toptrending - Trending tokens

        Args:
            category: Category type (if None, uses automatic cycling)
            interval: Time interval (5m, 1h, 6h, 24h)
            limit: Maximum number of tokens to retrieve

        Returns:
            List of token dictionaries with full market data
        """
        await self._ensure_session()

        try:
            # Use cycling if category not specified
            if category is None:
                category = self.DISCOVERY_CYCLES[self.current_cycle]
                use_cycling = True
                logger.info(f"Jupiter Cycle {self.current_cycle + 1}/3: Using '{category}' discovery")
            else:
                use_cycling = False

            # Correct format: /tokens/v2/{category}/{interval}?limit={limit}
            url = f"{self.base_url}/{category}/{interval}"
            params = {'limit': limit}

            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()

                    tokens = []
                    for token in data:
                        # Jupiter v2 returns comprehensive data
                        token_address = token.get('id') or token.get('address')
                        if not token_address:
                            continue

                        tokens.append({
                            'address': token_address,
                            'symbol': token.get('symbol'),
                            'name': token.get('name'),
                            'decimals': token.get('decimals'),
                            'logoURI': token.get('icon') or token.get('logoURI'),
                            'tags': token.get('tags') or [],
                            'liquidity': token.get('liquidity', 0),  # IMPORTANT for filtering
                            'fdv': token.get('fdv'),
                            'mcap': token.get('mcap'),
                            'usdPrice': token.get('usdPrice'),
                            'holderCount': token.get('holderCount'),
                            'organicScore': token.get('organicScore'),  # Organic activity indicator
                            'audit': token.get('audit') or {},
                            'launchpad': token.get('launchpad'),
                            'createdAt': token.get('createdAt')
                        })

                    # FILTER: Remove tokens with $0 liquidity (garbage data)
                    filtered_tokens = [t for t in tokens if t.get('liquidity', 0) > 0]

                    # Advance cycle if using automatic cycling
                    if use_cycling:
                        self.current_cycle = (self.current_cycle + 1) % len(self.DISCOVERY_CYCLES)
                        logger.info(f"Retrieved {len(filtered_tokens)} tokens using '{category}' (Next cycle: {self.DISCOVERY_CYCLES[self.current_cycle]})")
                    else:
                        logger.info(f"Retrieved {len(filtered_tokens)} {category} tokens from Jupiter")

                    return filtered_tokens
                else:
                    logger.warning(f"Jupiter {category} API returned {response.status}")
                    return []

        except Exception as e:
            logger.error(f"Error fetching {category} tokens from Jupiter: {e}")
            return []

    async def search_token(self, query: str) -> List[Dict]:
        """
        Search for tokens by symbol, name, or mint address.

        Args:
            query: Search query string

        Returns:
            List of matching token dictionaries
        """
        await self._ensure_session()

        try:
            url = f"{self.base_url}/search"
            params = {'q': query}

            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.debug(f"Found {len(data)} tokens matching '{query}'")
                    return data
                else:
                    logger.warning(f"Jupiter search returned {response.status}")
                    return []

        except Exception as e:
            logger.error(f"Error searching tokens on Jupiter: {e}")
            return []

    async def get_token_price_data(self, token_address: str) -> Optional[Dict]:
        """
        Get price and liquidity data for a specific token.

        Args:
            token_address: Token mint address

        Returns:
            Dictionary with price and liquidity data, or None if not found
        """
        await self._ensure_session()

        try:
            # Jupiter API doesn't have a direct single-token endpoint
            # We can search for the token and extract price/liquidity
            url = f"{self.base_url}/search"
            params = {'q': token_address}

            async with self.session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    data = await response.json()

                    # Find exact match by address/id
                    for token in data:
                        token_id = token.get('id') or token.get('address')
                        if token_id and token_id.lower() == token_address.lower():
                            # Found the token, extract price and liquidity
                            price_usd = token.get('usdPrice', 0.0)
                            liquidity = token.get('liquidity', 0.0)

                            if price_usd and isinstance(price_usd, (int, float)):
                                return {
                                    'price_usd': float(price_usd),
                                    'liquidity_usd': float(liquidity) if liquidity else 0.0,
                                    'volume_24h': 0.0,  # Jupiter doesn't provide volume data
                                    'volume_1h': 0.0,   # Jupiter doesn't provide volume data
                                    'symbol': token.get('symbol', 'UNKNOWN'),
                                    'name': token.get('name', 'Unknown'),
                                    'source': 'jupiter',
                                    'dex_id': 'unknown'  # Jupiter doesn't provide DEX platform
                                }

                    # Token not found in search results
                    logger.debug(f"Token {token_address[:8]}... not found in Jupiter search")
                    return None
                else:
                    # 400/404/429 = token not found or rate limited (expected), use debug
                    # Other errors = real issues, use warning
                    if response.status in [400, 404]:
                        logger.debug(f"Jupiter search: token {token_address[:8]}... not found ({response.status})")
                    elif response.status == 429:
                        logger.debug(f"Jupiter search: rate limited (429) - skipping {token_address[:8]}...")
                    else:
                        logger.warning(f"Jupiter search API returned {response.status} for {token_address[:8]}...")
                    return None

        except Exception as e:
            logger.error(f"Error fetching token data from Jupiter for {token_address[:8]}...: {e}")
            return None

    async def health_check(self) -> bool:
        """
        Check if Jupiter API is accessible.

        Returns:
            True if healthy, False otherwise
        """
        await self._ensure_session()

        try:
            # Try to get a small number of recent tokens
            url = f"{self.base_url}/recent"
            params = {'limit': 1}

            async with self.session.get(
                url,
                params=params,
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                return response.status == 200
        except Exception as e:
            logger.error(f"Jupiter health check failed: {e}")
            return False
