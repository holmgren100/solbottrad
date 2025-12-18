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

    def __init__(self):
        """Initialize Jupiter client (no API key needed)."""
        self.base_url = "https://lite-api.jup.ag/tokens/v2"
        self.session: Optional[aiohttp.ClientSession] = None

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

    async def get_trending_tokens(self, category: str = 'toptraded', limit: int = 50) -> List[Dict]:
        """
        Get trending/top tokens by category.

        Args:
            category: Category type ('toptraded', 'toptrending', 'toporganicscore')
            limit: Maximum number of tokens to retrieve

        Returns:
            List of token dictionaries
        """
        await self._ensure_session()

        try:
            url = f"{self.base_url}/categories/{category}"
            params = {'limit': limit}

            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"Retrieved {len(data)} {category} tokens from Jupiter")

                    tokens = []
                    for token in data:
                        tokens.append({
                            'address': token.get('address'),
                            'symbol': token.get('symbol'),
                            'name': token.get('name')
                        })
                    return tokens
                else:
                    logger.warning(f"Jupiter categories API returned {response.status}")
                    return []

        except Exception as e:
            logger.error(f"Error fetching trending tokens from Jupiter: {e}")
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
                                    'symbol': token.get('symbol', 'UNKNOWN'),
                                    'name': token.get('name', 'Unknown'),
                                    'source': 'jupiter'
                                }

                    # Token not found in search results
                    logger.debug(f"Token {token_address[:8]}... not found in Jupiter search")
                    return None
                else:
                    # 400/404 = token not found (normal for new tokens), use debug
                    # Other errors = real issues, use warning
                    log_level = logger.debug if response.status in [400, 404] else logger.warning
                    log_level(f"Jupiter search API returned {response.status} for {token_address[:8]}...")
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
