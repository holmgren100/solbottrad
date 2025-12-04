"""
DexScreener API client for market data and liquidity monitoring.
Supports cycling through different discovery methods.
"""

import aiohttp
from typing import Dict, List, Optional
from datetime import datetime
from ..monitoring.logger import get_logger

logger = get_logger(__name__)


class DexScreenerClient:
    """Client for DexScreener API to get market data."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize DexScreener client.

        Args:
            api_key: DexScreener API key (optional)
        """
        self.api_key = api_key
        self.base_url = "https://api.dexscreener.com/latest"
        self.session: Optional[aiohttp.ClientSession] = None
        self.price_cache: Dict[str, float] = {}  # Cache last known good prices

    def _validate_price(self, price: float, token_address: str) -> bool:
        """
        Validate that price is reasonable and not corrupted data.

        Args:
            price: Price to validate
            token_address: Token address for logging

        Returns:
            True if price is valid
        """
        MIN_PRICE = 1e-12  # Minimum realistic price
        MAX_PRICE = 1e10   # Maximum realistic price

        # Check if price is in reasonable range
        if price <= MIN_PRICE or price >= MAX_PRICE:
            logger.warning(f"Price ${price:.2e} outside valid range for {token_address[:12]}...")
            return False

        # Check against cached price if available (reject >90% changes)
        if token_address in self.price_cache:
            last_price = self.price_cache[token_address]
            change_pct = abs((price - last_price) / last_price) * 100

            if change_pct > 90:
                logger.warning(
                    f"Suspicious price change {change_pct:.1f}% for {token_address[:12]}... "
                    f"(${last_price:.8f} → ${price:.8f})"
                )
                return False

        return True

    async def _ensure_session(self):
        """Ensure aiohttp session exists."""
        if self.session is None or self.session.closed:
            headers = {}
            if self.api_key:
                headers['Authorization'] = f'Bearer {self.api_key}'
            self.session = aiohttp.ClientSession(headers=headers)

    async def close(self):
        """Close the client session."""
        if self.session and not self.session.closed:
            await self.session.close()

    async def get_token_pairs(self, token_address: str) -> List[Dict]:
        """
        Get all trading pairs for a token.

        Args:
            token_address: Token contract address

        Returns:
            List of trading pair dictionaries
        """
        await self._ensure_session()

        try:
            url = f"{self.base_url}/dex/tokens/{token_address}"

            async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    data = await response.json()
                    pairs = data.get('pairs') or []  # Handle null/None from API
                    logger.debug(f"Retrieved {len(pairs)} pairs for {token_address}")
                    return pairs
                else:
                    logger.error(f"DexScreener API error: {response.status}")
                    return []

        except Exception as e:
            logger.error(f"Error fetching token pairs: {e}")
            return []

    async def get_pair_info(self, pair_address: str, chain: str = 'solana') -> Optional[Dict]:
        """
        Get detailed information for a specific pair.

        Args:
            pair_address: Trading pair address
            chain: Blockchain name (default: solana)

        Returns:
            Pair information dictionary or None
        """
        await self._ensure_session()

        try:
            url = f"{self.base_url}/dex/pairs/{chain}/{pair_address}"

            async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    data = await response.json()
                    pair = data.get('pair')
                    if pair:
                        logger.debug(f"Retrieved pair info for {pair_address}")
                        return pair
                    return None
                else:
                    logger.warning(f"Pair info not available for {pair_address}")
                    return None

        except Exception as e:
            logger.error(f"Error fetching pair info: {e}")
            return None

    async def search_pairs(self, query: str) -> List[Dict]:
        """
        Search for trading pairs.

        Args:
            query: Search query (token name, symbol, or address)

        Returns:
            List of matching pair dictionaries
        """
        await self._ensure_session()

        try:
            url = f"{self.base_url}/dex/search"
            params = {'q': query}

            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    pairs = data.get('pairs') or []  # Handle null/None from API
                    logger.debug(f"Found {len(pairs)} pairs for query: {query}")
                    return pairs
                else:
                    logger.error(f"DexScreener search error: {response.status}")
                    return []

        except Exception as e:
            logger.error(f"Error searching pairs: {e}")
            return []

    async def get_token_profile(self, token_address: str) -> Optional[Dict]:
        """
        Get comprehensive token profile with market data.

        Args:
            token_address: Token contract address

        Returns:
            Token profile dictionary or None
        """
        pairs = await self.get_token_pairs(token_address)

        if not pairs:
            return None

        # Find the pair with highest liquidity
        main_pair = max(pairs, key=lambda p: float(p.get('liquidity', {}).get('usd', 0)))

        # Validate price before using it
        price_usd = float(main_pair.get('priceUsd', 0))
        if not self._validate_price(price_usd, token_address):
            # Use cached price if validation fails
            if token_address in self.price_cache:
                logger.warning(f"Using cached price for {token_address[:12]}...")
                price_usd = self.price_cache[token_address]
            else:
                logger.error(f"No valid price for {token_address[:12]}...")
                return None
        else:
            # Cache valid price
            self.price_cache[token_address] = price_usd

        profile = {
            'address': token_address,
            'symbol': main_pair.get('baseToken', {}).get('symbol', 'UNKNOWN'),
            'name': main_pair.get('baseToken', {}).get('name', 'Unknown'),
            'price_usd': price_usd,
            'price_change_24h': float(main_pair.get('priceChange', {}).get('h24', 0)),
            'volume_24h': float(main_pair.get('volume', {}).get('h24', 0)),
            'liquidity_usd': float(main_pair.get('liquidity', {}).get('usd', 0)),
            'market_cap': float(main_pair.get('marketCap', 0)),
            'fdv': float(main_pair.get('fdv', 0)),
            'pair_address': main_pair.get('pairAddress'),
            'dex_id': main_pair.get('dexId'),
            'pair_created_at': main_pair.get('pairCreatedAt'),
            'all_pairs': pairs,
            'timestamp': datetime.now().isoformat()
        }

        return profile

    async def get_trending_tokens(self, chain: str = 'solana', limit: int = 20) -> List[Dict]:
        """
        Get trending tokens on a specific chain.

        Note: This may require premium API access.

        Args:
            chain: Blockchain name
            limit: Maximum number of tokens to return

        Returns:
            List of trending token dictionaries
        """
        await self._ensure_session()

        try:
            # Note: This endpoint might not be available in free tier
            url = f"{self.base_url}/dex/trending/{chain}"

            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    tokens = (data.get('tokens') or [])[:limit]  # Handle null/None from API
                    logger.debug(f"Retrieved {len(tokens)} trending tokens")
                    return tokens
                elif response.status == 403:
                    logger.warning("Trending tokens endpoint requires premium access")
                    return []
                else:
                    logger.error(f"DexScreener trending error: {response.status}")
                    return []

        except Exception as e:
            logger.error(f"Error fetching trending tokens: {e}")
            return []

    async def get_organic_tokens(self, limit: int = 30) -> List[Dict]:
        """
        Get organic (NON-BOOSTED) token profiles from latest listings.

        WARNING: This method fetches latest profiles and FILTERS OUT boosted tokens.
        Boosted = PAID PROMOTIONS = High scam risk!

        NOTE: DexScreener API only supports fetching LATEST profiles, not sorted by
        price change or volume. Cycling strategies are not available for this API.

        Args:
            limit: Maximum number of ORGANIC tokens to return (will fetch more to filter)

        Returns:
            List of organic token dictionaries
        """
        await self._ensure_session()

        try:
            # Get latest token profiles (need to fetch more to filter out boosted)
            url = "https://api.dexscreener.com/token-profiles/latest/v1"

            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()

                    # Extract Solana tokens and filter OUT boosted
                    organic_tokens = []
                    for item in data:
                        token_address = item.get('tokenAddress')
                        chain_id = item.get('chainId', '').lower()

                        # Only Solana tokens
                        if chain_id != 'solana' or not token_address:
                            continue

                        # CRITICAL: Skip boosted (promoted) tokens
                        # These are paid promotions and usually scams!
                        boosts = item.get('boosts', {})
                        active_boosts = boosts.get('active', 0) if boosts else 0

                        if active_boosts > 0:
                            logger.debug(f"Skipping boosted token {token_address[:8]} (boosts: {active_boosts})")
                            continue

                        organic_tokens.append({
                            'address': token_address,
                            'chainId': chain_id,
                            'url': item.get('url'),
                            'links': item.get('links', []),
                            'icon': item.get('icon'),
                            'description': item.get('description'),
                            'boosts_active': 0,  # Explicitly mark as organic
                            # Will be enriched with price/liquidity later
                        })

                        if len(organic_tokens) >= limit:
                            break

                    logger.info(f"Retrieved {len(organic_tokens)} ORGANIC (non-boosted) Solana tokens from DexScreener")
                    return organic_tokens
                else:
                    logger.warning(f"DexScreener organic tokens error: {response.status}")
                    return []

        except Exception as e:
            logger.error(f"Error fetching organic tokens: {e}")
            return []

    async def get_latest_token_profiles(self, limit: int = 30) -> List[Dict]:
        """
        Get latest token profiles (FREE endpoint - no premium required).
        These are newly created/updated tokens with profiles.

        Args:
            limit: Maximum number of tokens to return

        Returns:
            List of token dictionaries
        """
        await self._ensure_session()

        try:
            # FREE endpoint: https://api.dexscreener.com/token-profiles/latest/v1
            url = "https://api.dexscreener.com/token-profiles/latest/v1"

            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()

                    # Extract Solana tokens only
                    tokens = []
                    for item in data[:limit]:
                        token_address = item.get('tokenAddress')
                        chain_id = item.get('chainId', '').lower()

                        # Only Solana tokens
                        if chain_id == 'solana' and token_address:
                            tokens.append({
                                'address': token_address,
                                'chainId': chain_id,
                                'url': item.get('url'),
                                'links': item.get('links', []),
                                'icon': item.get('icon'),
                                'description': item.get('description'),
                                # Will be enriched with price/liquidity later
                            })

                    logger.info(f"Retrieved {len(tokens)} latest Solana token profiles from DexScreener")
                    return tokens
                else:
                    logger.warning(f"DexScreener latest profiles error: {response.status}")
                    return []

        except Exception as e:
            logger.error(f"Error fetching latest token profiles: {e}")
            return []

    def calculate_liquidity_score(self, liquidity_usd: float) -> float:
        """
        Calculate a normalized liquidity score (0-1).

        Args:
            liquidity_usd: Liquidity in USD

        Returns:
            Liquidity score between 0 and 1
        """
        # Logarithmic scale for liquidity scoring
        if liquidity_usd <= 0:
            return 0.0

        # Target liquidity ranges
        min_liquidity = 1000  # $1K
        good_liquidity = 100000  # $100K
        excellent_liquidity = 1000000  # $1M

        if liquidity_usd < min_liquidity:
            return liquidity_usd / min_liquidity * 0.3
        elif liquidity_usd < good_liquidity:
            return 0.3 + (liquidity_usd - min_liquidity) / (good_liquidity - min_liquidity) * 0.4
        elif liquidity_usd < excellent_liquidity:
            return 0.7 + (liquidity_usd - good_liquidity) / (excellent_liquidity - good_liquidity) * 0.3
        else:
            return 1.0

    async def health_check(self) -> bool:
        """
        Check if DexScreener API is accessible.

        Returns:
            True if healthy, False otherwise
        """
        await self._ensure_session()

        try:
            # Try to search for a well-known token (e.g., SOL)
            url = f"{self.base_url}/dex/search"
            params = {'q': 'SOL'}

            async with self.session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=5)) as response:
                return response.status == 200

        except Exception as e:
            logger.error(f"DexScreener health check failed: {e}")
            return False
