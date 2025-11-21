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

                    # Jupiter returns array of token objects
                    # Convert to our standard format
                    tokens = []
                    for token in data:
                        tokens.append({
                            'address': token.get('address'),
                            'symbol': token.get('symbol'),
                            'name': token.get('name'),
                            'decimals': token.get('decimals'),
                            'logoURI': token.get('logoURI'),
                            'tags': token.get('tags', []),
                            'daily_volume': token.get('daily_volume'),
                            'freeze_authority': token.get('freeze_authority'),
                            'mint_authority': token.get('mint_authority'),
                            'permanent_delegate': token.get('permanent_delegate'),
                            'minted_at': token.get('minted_at'),
                            'extensions': token.get('extensions', {})
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
