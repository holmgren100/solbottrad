"""
API Clients for Token Discovery and Price Data

Integrates with:
- DexScreener: Token profiles, price, volume, liquidity
- Jupiter: Price validation, swap quotes
"""

import asyncio
import aiohttp
import logging
from typing import Dict, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


class DexScreenerClient:
    """DexScreener API client for token discovery and market data."""

    # PHASE 2: Category Discovery - Cycling strategies
    DISCOVERY_CATEGORIES = [
        'latest',    # Cycle 1: Latest tokens (newly created)
        'trending'   # Cycle 2: Trending tokens (proven activity)
    ]

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize DexScreener client.

        Args:
            api_key: Optional API key for higher rate limits
        """
        self.api_key = api_key
        self.base_url = "https://api.dexscreener.com"
        self.session: Optional[aiohttp.ClientSession] = None
        self.current_category = 0  # Track which category we're on

    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()

    async def get_token_profile(self, token_address: str) -> Optional[Dict]:
        """
        Get token profile from DexScreener.

        Args:
            token_address: Solana token address

        Returns:
            Token data dict or None if not found
        """
        try:
            url = f"{self.base_url}/latest/dex/tokens/{token_address}"

            headers = {}
            if self.api_key:
                headers['X-Api-Key'] = self.api_key

            async with self.session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    data = await response.json()

                    # DexScreener returns pairs array
                    pairs = data.get('pairs')
                    if not pairs or not isinstance(pairs, list):
                        logger.debug(f"No pairs found for {token_address[:8]}...")
                        return None

                    # Get the main SOL pair (highest liquidity) - with safe checks
                    sol_pairs = []
                    for p in pairs:
                        if not p or not isinstance(p, dict):
                            continue
                        base_token = p.get('baseToken')
                        if not base_token or not isinstance(base_token, dict):
                            continue
                        if base_token.get('address') == token_address:
                            sol_pairs.append(p)

                    if not sol_pairs:
                        logger.debug(f"No SOL pairs found for {token_address[:8]}...")
                        return None

                    # Get pair with highest liquidity - safe version
                    def get_liquidity(p):
                        try:
                            liq = p.get('liquidity') or {}
                            if not isinstance(liq, dict):
                                return 0
                            return float(liq.get('usd', 0))
                        except:
                            return 0

                    pair = max(sol_pairs, key=get_liquidity)

                    # Extract relevant data with safe nested gets
                    base_token = pair.get('baseToken') or {}
                    liquidity = pair.get('liquidity') or {}
                    volume = pair.get('volume') or {}
                    price_change = pair.get('priceChange') or {}
                    txns = pair.get('txns') or {}
                    txns_h24 = txns.get('h24') or {}

                    return {
                        'address': token_address,
                        'symbol': base_token.get('symbol', ''),
                        'name': base_token.get('name', ''),
                        'price_usd': float(pair.get('priceUsd', 0)),
                        'liquidity_usd': float(liquidity.get('usd', 0)),
                        'volume_24h': float(volume.get('h24', 0)),
                        'price_change_5m': float(price_change.get('m5', 0)),
                        'price_change_1h': float(price_change.get('h1', 0)),
                        'price_change_24h': float(price_change.get('h24', 0)),
                        'txns_24h': txns_h24.get('buys', 0) + txns_h24.get('sells', 0),
                        'pair_address': pair.get('pairAddress', ''),
                        'dex_id': pair.get('dexId', ''),
                    }
                elif response.status == 404:
                    logger.debug(f"Token {token_address[:8]}... not found on DexScreener (may be too new)")
                    return None
                else:
                    logger.warning(f"DexScreener API error: {response.status}")
                    return None

        except Exception as e:
            logger.debug(f"Error fetching token profile from DexScreener: {e}")
            return None

    async def get_latest_tokens(self, limit: int = 50, use_cycling: bool = False) -> List[Dict]:
        """
        Get latest token profiles with optional category cycling.

        Args:
            limit: Max number of tokens to return
            use_cycling: If True, cycles between 'latest' and 'trending' categories

        Returns:
            List of token data dicts
        """
        try:
            # Use cycling if enabled
            if use_cycling:
                category = self.DISCOVERY_CATEGORIES[self.current_category]
                logger.info(f"DexScreener Cycle {self.current_category + 1}/2: Using '{category}' category")
            else:
                category = 'latest'

            url = f"{self.base_url}/token-profiles/{category}/v1"

            async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as response:
                if response.status == 200:
                    data = await response.json()

                    # Filter for Solana tokens with good data
                    tokens = []
                    for item in data[:limit]:
                        if item.get('chainId') == 'solana':
                            token_data = await self.get_token_profile(item.get('tokenAddress'))
                            if token_data:
                                # Add source tracking
                                token_data['source'] = f'dexscreener_{category}'
                                tokens.append(token_data)

                    # Advance to next category for next scan
                    if use_cycling:
                        self.current_category = (self.current_category + 1) % len(self.DISCOVERY_CATEGORIES)
                        logger.info(
                            f"Retrieved {len(tokens)} tokens from DexScreener '{category}' "
                            f"(Next cycle: {self.DISCOVERY_CATEGORIES[self.current_category]})"
                        )
                    else:
                        logger.info(f"Retrieved {len(tokens)} tokens from DexScreener 'latest'")

                    return tokens
                else:
                    logger.warning(f"DexScreener {category} tokens error: {response.status}")
                    return []

        except Exception as e:
            logger.error(f"Error fetching {category if use_cycling else 'latest'} tokens: {e}")
            return []

    async def get_trending_tokens(self, limit: int = 50) -> List[Dict]:
        """
        Get trending token profiles.

        Args:
            limit: Max number of tokens to return

        Returns:
            List of token data dicts
        """
        try:
            url = f"{self.base_url}/token-profiles/trending/v1"

            async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as response:
                if response.status == 200:
                    data = await response.json()

                    # Filter for Solana tokens
                    tokens = []
                    for item in data[:limit]:
                        if item.get('chainId') == 'solana':
                            token_data = await self.get_token_profile(item.get('tokenAddress'))
                            if token_data:
                                token_data['source'] = 'dexscreener_trending'
                                tokens.append(token_data)

                    logger.info(f"Retrieved {len(tokens)} trending tokens from DexScreener")
                    return tokens
                else:
                    logger.warning(f"DexScreener trending tokens error: {response.status}")
                    return []

        except Exception as e:
            logger.error(f"Error fetching trending tokens: {e}")
            return []


class JupiterClient:
    """Jupiter API client for price validation and token discovery."""

    # PHASE 1: Token Discovery - Cycling strategies
    DISCOVERY_CYCLES = [
        'toporganicscore',  # Cycle 1: Organic activity (filters bots)
        'toptraded',        # Cycle 2: Highest traded volume
        'toptrending'       # Cycle 3: Trending tokens
    ]

    def __init__(self):
        """Initialize Jupiter client."""
        self.base_url = "https://quote-api.jup.ag/v6"
        self.tokens_base_url = "https://lite-api.jup.ag/tokens/v2"
        self.session: Optional[aiohttp.ClientSession] = None
        self.current_cycle = 0  # Track which discovery cycle we're on

    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
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
        try:
            # Ensure session is initialized
            if self.session is None:
                self.session = aiohttp.ClientSession()

            url = f"{self.tokens_base_url}/recent"
            params = {'limit': limit}

            async with self.session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=15)) as response:
                if response.status == 200:
                    data = await response.json()

                    # Convert to standard format
                    tokens = []
                    for token in data:
                        token_address = token.get('id') or token.get('address')
                        if not token_address:
                            continue

                        tokens.append({
                            'address': token_address,
                            'symbol': token.get('symbol'),
                            'name': token.get('name'),
                            'decimals': token.get('decimals'),
                            'liquidity': token.get('liquidity', 0),
                            'fdv': token.get('fdv', 0),
                            'mcap': token.get('mcap', 0),
                            'price_usd': token.get('usdPrice', 0),
                            'holder_count': token.get('holderCount', 0),
                            'source': 'jupiter_recent'
                        })

                    logger.info(f"Retrieved {len(tokens)} recent tokens from Jupiter")
                    return tokens
                else:
                    logger.warning(f"Jupiter recent tokens error: {response.status}")
                    return []

        except Exception as e:
            logger.error(f"Error fetching recent tokens from Jupiter: {e}")
            return []

    async def get_trending_tokens(
        self,
        category: str = None,
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
        try:
            # Ensure session is initialized
            if self.session is None:
                self.session = aiohttp.ClientSession()

            # Use cycling if category not specified
            if category is None:
                category = self.DISCOVERY_CYCLES[self.current_cycle]
                logger.info(f"Jupiter Cycle {self.current_cycle + 1}/3: Using '{category}' discovery")

            # Endpoint: /tokens/v2/{category}/{interval}?limit={limit}
            url = f"{self.tokens_base_url}/{category}/{interval}"
            params = {'limit': limit}

            async with self.session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=15)) as response:
                if response.status == 200:
                    data = await response.json()

                    tokens = []
                    for token in data:
                        token_address = token.get('id') or token.get('address')
                        if not token_address:
                            continue

                        tokens.append({
                            'address': token_address,
                            'symbol': token.get('symbol'),
                            'name': token.get('name'),
                            'decimals': token.get('decimals'),
                            'liquidity': token.get('liquidity', 0),
                            'fdv': token.get('fdv', 0),
                            'mcap': token.get('mcap', 0),
                            'price_usd': token.get('usdPrice', 0),
                            'holder_count': token.get('holderCount', 0),
                            'volume_24h': token.get('volume24h', 0),
                            'source': f'jupiter_{category}'
                        })

                    # Advance to next cycle for next scan
                    if category is None or category in self.DISCOVERY_CYCLES:
                        self.current_cycle = (self.current_cycle + 1) % len(self.DISCOVERY_CYCLES)

                    logger.info(
                        f"Retrieved {len(tokens)} tokens using Jupiter '{category}' "
                        f"(Next cycle: {self.DISCOVERY_CYCLES[self.current_cycle]})"
                    )
                    return tokens
                else:
                    logger.warning(f"Jupiter trending tokens error {response.status}")
                    return []

        except Exception as e:
            logger.error(f"Error fetching trending tokens from Jupiter: {e}")
            return []

    async def get_token_price(self, token_address: str) -> Optional[float]:
        """
        Get token price from Jupiter in USD.

        Uses Jupiter Price API v2 which directly returns USD prices.

        Args:
            token_address: Token address

        Returns:
            Price in USD or None
        """
        try:
            # Ensure session is initialized
            if self.session is None:
                self.session = aiohttp.ClientSession()

            # Use Jupiter Price API v2 - much simpler and more reliable
            url = f"https://api.jup.ag/price/v2"
            params = {'ids': token_address}

            async with self.session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    data = await response.json()

                    # Safe null check for response
                    if not data or not isinstance(data, dict):
                        logger.warning(f"⚠️  Invalid Jupiter response format for {token_address[:8]}...")
                        return None

                    # Response format: {"data": {"<address>": {"id": "...", "price": "..."}}}
                    data_dict = data.get('data')
                    if not data_dict or not isinstance(data_dict, dict):
                        logger.warning(f"⚠️  No Jupiter price data for {token_address[:8]}... (too new or no liquidity)")
                        return None

                    token_data = data_dict.get(token_address)
                    if token_data and isinstance(token_data, dict) and 'price' in token_data:
                        price = float(token_data['price'])
                        logger.info(f"✅ Jupiter price for {token_address[:8]}...: ${price:.8f}")
                        return price
                    else:
                        logger.warning(f"⚠️  No Jupiter price data for {token_address[:8]}... (too new or no liquidity)")
                        return None
                else:
                    logger.warning(f"⚠️  Jupiter Price API error {response.status} for {token_address[:8]}...")
                    return None

        except Exception as e:
            logger.warning(f"⚠️  Error getting Jupiter price for {token_address[:8]}...: {e}")
            return None

    async def get_token_price_data(self, token_address: str) -> Optional[Dict]:
        """
        Get comprehensive price data from Jupiter.

        Args:
            token_address: Token address

        Returns:
            Price data dict or None
        """
        price = await self.get_token_price(token_address)

        if price:
            return {
                'price_usd': price,
                'source': 'jupiter',
                'timestamp': datetime.now().isoformat()
            }

        return None


class SolscanClient:
    """Solscan API client for holder analysis."""

    def __init__(self, api_key: str):
        """
        Initialize Solscan client.

        Args:
            api_key: Solscan API key
        """
        self.api_key = api_key
        self.base_url = "https://pro-api.solscan.io/v1.0"
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        """Async context manager entry."""
        headers = {'token': self.api_key}
        self.session = aiohttp.ClientSession(headers=headers)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()

    async def get_holder_analysis(self, token_address: str) -> Optional[Dict]:
        """
        Get holder concentration analysis.

        Args:
            token_address: Token address

        Returns:
            Holder data dict or None
        """
        try:
            url = f"{self.base_url}/token/holders"
            params = {'tokenAddress': token_address, 'limit': 10}

            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()

                    holders = data.get('data', [])
                    if not holders:
                        return None

                    # Calculate concentrations
                    total_supply = sum(h.get('amount', 0) for h in holders)

                    top1_pct = (holders[0].get('amount', 0) / total_supply * 100) if total_supply > 0 else 100
                    top10_pct = sum(h.get('amount', 0) for h in holders[:10]) / total_supply * 100 if total_supply > 0 else 100

                    return {
                        'top1_concentration': top1_pct,
                        'top10_concentration': top10_pct,
                        'total_holders': data.get('total', 0)
                    }

                return None

        except Exception as e:
            logger.error(f"Error getting holder analysis: {e}")
            return None
