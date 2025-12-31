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
                    txns_h1 = txns.get('h1') or {}  # 1h txns for recent activity

                    # Calculate buy/sell ratio and activity
                    buys_24h = txns_h24.get('buys', 0)
                    sells_24h = txns_h24.get('sells', 0)
                    buys_1h = txns_h1.get('buys', 0)
                    sells_1h = txns_h1.get('sells', 0)

                    total_txns_24h = buys_24h + sells_24h
                    total_txns_1h = buys_1h + sells_1h

                    # Calculate buy ratio (0-1, where >0.5 = more buyers)
                    buy_ratio_24h = buys_24h / total_txns_24h if total_txns_24h > 0 else 0
                    buy_ratio_1h = buys_1h / total_txns_1h if total_txns_1h > 0 else 0

                    return {
                        'address': token_address,
                        'symbol': base_token.get('symbol', ''),
                        'name': base_token.get('name', ''),
                        'price_usd': float(pair.get('priceUsd', 0)),
                        'liquidity_usd': float(liquidity.get('usd', 0)),
                        'volume_24h': float(volume.get('h24', 0)),
                        'volume_1h': float(volume.get('h1', 0)),  # ⚡ 1h volume for spike detection
                        'price_change_5m': float(price_change.get('m5', 0)),
                        'price_change_1h': float(price_change.get('h1', 0)),
                        'price_change_24h': float(price_change.get('h24', 0)),
                        'txns_24h': total_txns_24h,
                        'txns_1h': total_txns_1h,
                        'buys_24h': buys_24h,
                        'sells_24h': sells_24h,
                        'buys_1h': buys_1h,
                        'sells_1h': sells_1h,
                        'buy_ratio_24h': buy_ratio_24h,
                        'buy_ratio_1h': buy_ratio_1h,
                        'pair_address': pair.get('pairAddress', ''),
                        'dex_id': pair.get('dexId', ''),
                        # ⚡ CRITICAL ANALYSIS FIELDS
                        'pair_created_at': pair.get('pairCreatedAt', 0),  # Timestamp for token age
                        'fdv': float(pair.get('fdv', 0)),  # Fully diluted valuation
                        'market_cap': float(pair.get('marketCap', 0)),  # Market cap
                        'info': pair.get('info', {}),  # Social links, websites
                        'labels': pair.get('labels', []),  # Community flags (v2, v3, scam, etc)
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

            headers = {}
            if self.api_key:
                headers['X-Api-Key'] = self.api_key

            async with self.session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as response:
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

            headers = {}
            if self.api_key:
                headers['X-Api-Key'] = self.api_key

            async with self.session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as response:
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
        await self._ensure_session()

        try:
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
        await self._ensure_session()

        try:
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

                    # PHASE 1: Data Enrichment (controlled by env var)
                    # Problem: Discovery API returns liquidity=0, volume=0 for many tokens
                    # Solution: Query each token individually to get real data
                    import os
                    enrich_data = os.getenv('ENABLE_JUPITER_ENRICHMENT', 'false').lower() == 'true'

                    if enrich_data and tokens:
                        logger.info(f"🔍 Enriching {len(tokens)} Jupiter tokens with liquidity/volume data...")
                        enriched_tokens = []
                        success_count = 0

                        for token in tokens[:20]:  # Limit to 20 to avoid rate limits
                            try:
                                # Get detailed data including liquidity/volume
                                detailed_data = await self.get_token_price_data(token['address'])

                                if detailed_data and detailed_data.get('liquidity_usd', 0) > 0:
                                    # Merge basic info with detailed data
                                    enriched_token = {**token, **detailed_data}
                                    enriched_tokens.append(enriched_token)
                                    success_count += 1
                                else:
                                    # Keep original if no detailed data
                                    enriched_tokens.append(token)
                            except Exception as e:
                                logger.debug(f"Failed to enrich {token['address'][:8]}...: {e}")
                                enriched_tokens.append(token)

                        logger.info(f"✅ Enriched {success_count}/{len(enriched_tokens)} tokens with real data")
                        return enriched_tokens

                    return tokens
                else:
                    logger.warning(f"Jupiter trending tokens error {response.status}")
                    return []

        except Exception as e:
            logger.error(f"Error fetching trending tokens from Jupiter: {e}")
            return []

    async def _ensure_session(self):
        """Ensure aiohttp session exists (WORKING ML BOT METHOD)."""
        if self.session is None or (hasattr(self.session, 'closed') and self.session.closed):
            self.session = aiohttp.ClientSession()

    async def get_token_price_data(self, token_address: str) -> Optional[Dict]:
        """
        Get price and liquidity data for a specific token (COMPLETE WORKING VERSION).

        Args:
            token_address: Token mint address

        Returns:
            Dictionary with price and liquidity data, or None if not found
        """
        await self._ensure_session()

        try:
            # Jupiter API search endpoint - PROVEN WORKING METHOD
            url = f"{self.tokens_base_url}/search"
            params = {'query': token_address}  # Fixed: 'query' not 'q' per API docs

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
                                    'dex_id': 'unknown',  # Jupiter doesn't provide DEX platform
                                    # Transaction data (Jupiter doesn't provide, set to 0)
                                    'txns_h1_buys': 0,
                                    'txns_h1_sells': 0,
                                    'txns_m5_buys': 0,
                                    'txns_m5_sells': 0
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
            logger.debug(f"Error fetching token data from Jupiter for {token_address[:8]}...: {e}")
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
