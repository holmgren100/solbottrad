"""
Birdeye API client for Solana DEX data.
Birdeye is Solana-native and provides trending, new listings, and token data.
"""

import aiohttp
from typing import Dict, List, Optional
from datetime import datetime
from ..monitoring.logger import get_logger

logger = get_logger(__name__)


class BirdeyeClient:
    """Client for Birdeye API - Solana-native DEX aggregator."""

    # Cycling strategies for token discovery
    DISCOVERY_CYCLES = [
        'rank',             # Cycle 1: Trending rank
        'liquidity',        # Cycle 2: Liquidity amount
        'volume24hUSD',     # Cycle 3: 24h volume
        'priceChange24h',   # Cycle 4: 24h price change (gainers)
        'priceChange1h'     # Cycle 5: 1h price change (gainers)
    ]

    def __init__(self, api_key: str):
        """
        Initialize Birdeye client.

        Args:
            api_key: Birdeye API key
        """
        self.api_key = api_key
        self.base_url = "https://public-api.birdeye.so"
        self.session: Optional[aiohttp.ClientSession] = None
        self.chain = "solana"
        self.current_cycle = 0  # Track which discovery cycle we're on

    async def _ensure_session(self):
        """Ensure aiohttp session exists."""
        if self.session is None or self.session.closed:
            headers = {
                "X-API-KEY": self.api_key,
                "accept": "application/json"
            }
            self.session = aiohttp.ClientSession(headers=headers)

    async def close(self):
        """Close the aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()

    async def health_check(self) -> bool:
        """Check if Birdeye API is accessible."""
        try:
            await self._ensure_session()
            url = f"{self.base_url}/public/tokenlist"
            params = {"chain": self.chain, "limit": 1}

            async with self.session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as response:
                return response.status == 200
        except Exception as e:
            logger.error(f"Birdeye health check failed: {e}")
            return False

    async def get_trending_tokens(self, limit: int = 30) -> List[Dict]:
        """
        Get trending tokens using CYCLING strategy.

        Rotates through 5 discovery methods:
        1. rank - Trending rank
        2. liquidity - Liquidity amount
        3. volume24hUSD - 24h volume
        4. priceChange24h - 24h price change (gainers)
        5. priceChange1h - 1h price change (gainers)

        Args:
            limit: Maximum number of tokens to return

        Returns:
            List of trending token dictionaries
        """
        await self._ensure_session()

        try:
            # Get current cycle
            sort_by = self.DISCOVERY_CYCLES[self.current_cycle]
            logger.info(f"Birdeye Cycle {self.current_cycle + 1}/5: Using '{sort_by}' discovery")

            # Birdeye trending tokens endpoint
            url = f"{self.base_url}/defi/token_trending"
            params = {
                "sort_by": sort_by,
                "sort_type": "desc",
                "offset": 0,
                "limit": min(limit, 50)
            }
            headers = {
                "X-API-KEY": self.api_key,
                "x-chain": "solana",
                "accept": "application/json"
            }

            async with self.session.get(url, params=params, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as response:
                if response.status == 200:
                    data = await response.json()

                    # Check if request was successful
                    if not data.get('success', False):
                        logger.warning("Birdeye API returned success=false")
                        return []

                    tokens = data.get('data', {}).get('tokens', [])

                    # Extract token data
                    token_list = []
                    for token in tokens:
                        token_list.append({
                            'address': token.get('address'),
                            'symbol': token.get('symbol'),
                            'name': token.get('name'),
                            'liquidity': token.get('liquidity', 0),
                            'volume_24h': token.get('volume24hUSD', 0),
                            'rank': token.get('rank', 999),
                        })

                    # Advance to next cycle for next scan
                    self.current_cycle = (self.current_cycle + 1) % len(self.DISCOVERY_CYCLES)

                    logger.info(f"Retrieved {len(token_list)} tokens using '{sort_by}' (Next cycle: {self.DISCOVERY_CYCLES[self.current_cycle]})")
                    return token_list
                elif response.status == 401:
                    error_text = await response.text()
                    logger.error(f"Birdeye 401 Unauthorized - Check API key! Response: {error_text[:200]}")
                    logger.error(f"Headers sent: x-api-key={self.api_key[:8]}..., x-chain=solana")
                    logger.error(f"URL: {url}")
                    return []
                elif response.status == 429:
                    logger.warning("Birdeye API rate limit reached")
                    return []
                else:
                    error_text = await response.text()
                    logger.warning(f"Birdeye trending tokens error {response.status}: {error_text[:200]}")
                    return []

        except Exception as e:
            logger.error(f"Error fetching trending tokens from Birdeye: {e}")
            return []

    async def get_new_listings(self, limit: int = 30) -> List[Dict]:
        """
        Get newly listed tokens - using token_creation_time filter.

        Args:
            limit: Maximum number of tokens to return

        Returns:
            List of new token dictionaries
        """
        await self._ensure_session()

        try:
            # Birdeye trending tokens endpoint (sorted by rank for newer tokens)
            url = f"{self.base_url}/defi/token_trending"
            params = {
                "sort_by": "rank",
                "sort_type": "asc",
                "offset": 0,
                "limit": min(limit, 50)
            }
            headers = {
                "X-API-KEY": self.api_key,
                "x-chain": "solana",
                "accept": "application/json"
            }

            async with self.session.get(url, params=params, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as response:
                if response.status == 200:
                    data = await response.json()

                    # Check if request was successful
                    if not data.get('success', False):
                        logger.warning("Birdeye API returned success=false")
                        return []

                    tokens = data.get('data', {}).get('tokens', [])

                    # Extract token data
                    token_list = []
                    for token in tokens:
                        token_list.append({
                            'address': token.get('address'),
                            'symbol': token.get('symbol'),
                            'name': token.get('name'),
                            'liquidity': token.get('liquidity', 0),
                            'volume_24h': token.get('volume24hUSD', 0),
                            'rank': token.get('rank', 999),
                        })

                    logger.info(f"Retrieved {len(token_list)} new listings from Birdeye")
                    return token_list
                elif response.status == 401:
                    error_text = await response.text()
                    logger.error(f"Birdeye 401 Unauthorized - Check API key! Response: {error_text[:200]}")
                    logger.error(f"Headers sent: x-api-key={self.api_key[:8]}..., x-chain=solana")
                    logger.error(f"URL: {url}")
                    return []
                elif response.status == 429:
                    logger.warning("Birdeye API rate limit reached")
                    return []
                else:
                    error_text = await response.text()
                    logger.warning(f"Birdeye new listings error {response.status}: {error_text[:200]}")
                    return []

        except Exception as e:
            logger.error(f"Error fetching new listings from Birdeye: {e}")
            return []

    async def get_token_overview(self, token_address: str) -> Optional[Dict]:
        """
        Get comprehensive token overview data.

        Args:
            token_address: Token mint address

        Returns:
            Token overview dictionary or None
        """
        await self._ensure_session()

        try:
            url = f"{self.base_url}/defi/token_overview"
            params = {"address": token_address}

            async with self.session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    data = await response.json()
                    token_data = data.get('data', {})

                    return {
                        'address': token_address,
                        'symbol': token_data.get('symbol'),
                        'name': token_data.get('name'),
                        'price': token_data.get('price', 0),
                        'liquidity': token_data.get('liquidity', 0),
                        'volume_24h': token_data.get('v24hUSD', 0),
                        'market_cap': token_data.get('mc', 0),
                        'price_change_24h': token_data.get('priceChange24hPercent', 0),
                        'unique_wallets_24h': token_data.get('uniqueWallet24h', 0),
                        'trade_24h': token_data.get('trade24h', 0),
                    }
                elif response.status == 404:
                    logger.debug(f"Token {token_address[:8]}... not found in Birdeye")
                    return None
                else:
                    logger.warning(f"Birdeye token overview error: {response.status}")
                    return None

        except Exception as e:
            logger.error(f"Error fetching token overview from Birdeye: {e}")
            return None

    async def get_token_security(self, token_address: str) -> Optional[Dict]:
        """
        Get token security information.

        Args:
            token_address: Token mint address

        Returns:
            Security information dictionary or None
        """
        await self._ensure_session()

        try:
            url = f"{self.base_url}/defi/token_security"
            params = {"address": token_address}

            async with self.session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    data = await response.json()
                    security_data = data.get('data', {})

                    return {
                        'address': token_address,
                        'is_true_token': security_data.get('isTrueToken'),
                        'creator_address': security_data.get('creatorAddress'),
                        'creation_tx': security_data.get('creationTx'),
                        'creation_time': security_data.get('creationTime'),
                        'mint_authority': security_data.get('mintAuthority'),
                        'freeze_authority': security_data.get('freezeAuthority'),
                        'top_10_holder_percent': security_data.get('top10HolderPercent', 0),
                        'total_supply': security_data.get('totalSupply', 0),
                    }
                elif response.status == 404:
                    logger.debug(f"Security info not found for {token_address[:8]}...")
                    return None
                else:
                    logger.warning(f"Birdeye security check error: {response.status}")
                    return None

        except Exception as e:
            logger.error(f"Error fetching token security from Birdeye: {e}")
            return None
