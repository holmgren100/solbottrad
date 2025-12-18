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

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize DexScreener client.

        Args:
            api_key: Optional API key for higher rate limits
        """
        self.api_key = api_key
        self.base_url = "https://api.dexscreener.com"
        self.session: Optional[aiohttp.ClientSession] = None

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

            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()

                    # DexScreener returns pairs array
                    pairs = data.get('pairs', [])
                    if not pairs:
                        return None

                    # Get the main SOL pair (highest liquidity)
                    sol_pairs = [p for p in pairs if p.get('baseToken', {}).get('address') == token_address]
                    if not sol_pairs:
                        return None

                    pair = max(sol_pairs, key=lambda p: float(p.get('liquidity', {}).get('usd', 0)))

                    # Extract relevant data
                    return {
                        'address': token_address,
                        'symbol': pair.get('baseToken', {}).get('symbol', ''),
                        'name': pair.get('baseToken', {}).get('name', ''),
                        'price_usd': float(pair.get('priceUsd', 0)),
                        'liquidity_usd': float(pair.get('liquidity', {}).get('usd', 0)),
                        'volume_24h': float(pair.get('volume', {}).get('h24', 0)),
                        'price_change_5m': float(pair.get('priceChange', {}).get('m5', 0)),
                        'price_change_1h': float(pair.get('priceChange', {}).get('h1', 0)),
                        'price_change_24h': float(pair.get('priceChange', {}).get('h24', 0)),
                        'txns_24h': pair.get('txns', {}).get('h24', {}).get('buys', 0) +
                                   pair.get('txns', {}).get('h24', {}).get('sells', 0),
                        'pair_address': pair.get('pairAddress', ''),
                        'dex_id': pair.get('dexId', ''),
                    }
                else:
                    logger.warning(f"DexScreener API error: {response.status}")
                    return None

        except Exception as e:
            logger.error(f"Error fetching token profile from DexScreener: {e}")
            return None

    async def get_latest_tokens(self, limit: int = 50) -> List[Dict]:
        """
        Get latest token profiles.

        Args:
            limit: Max number of tokens to return

        Returns:
            List of token data dicts
        """
        try:
            url = f"{self.base_url}/token-profiles/latest/v1"

            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()

                    # Filter for Solana tokens with good data
                    tokens = []
                    for item in data[:limit]:
                        if item.get('chainId') == 'solana':
                            token_data = await self.get_token_profile(item.get('tokenAddress'))
                            if token_data and token_data.get('liquidity_usd', 0) > 5000:
                                tokens.append(token_data)

                    return tokens
                else:
                    logger.warning(f"DexScreener latest tokens error: {response.status}")
                    return []

        except Exception as e:
            logger.error(f"Error fetching latest tokens: {e}")
            return []


class JupiterClient:
    """Jupiter API client for price validation and swaps."""

    def __init__(self):
        """Initialize Jupiter client."""
        self.base_url = "https://quote-api.jup.ag/v6"
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()

    async def get_token_price(self, token_address: str) -> Optional[float]:
        """
        Get token price from Jupiter.

        Args:
            token_address: Token address

        Returns:
            Price in USD or None
        """
        try:
            # Get quote for 1 SOL worth of token
            sol_mint = "So11111111111111111111111111111111111111112"
            amount = 1_000_000_000  # 1 SOL in lamports

            url = f"{self.base_url}/quote"
            params = {
                'inputMint': sol_mint,
                'outputMint': token_address,
                'amount': amount,
                'slippageBps': 50
            }

            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()

                    # Calculate price from quote
                    out_amount = int(data.get('outAmount', 0))
                    if out_amount > 0:
                        # Price of token in SOL
                        price_sol = amount / out_amount

                        # Convert to USD (would need SOL/USD price)
                        # For now, return SOL price
                        return price_sol

                    return None
                else:
                    return None

        except Exception as e:
            logger.debug(f"Error getting Jupiter price: {e}")
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
