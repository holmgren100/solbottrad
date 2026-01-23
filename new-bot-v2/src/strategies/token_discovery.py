"""
Token Discovery - Multi-Source Token Discovery Strategy

Discovers tokens from multiple sources with fallbacks:
1. Jupiter (verified and all tokens)
2. DexScreener (trending and latest)
3. Birdeye (future - Solana-specific)

Strategy:
- Try all sources in parallel
- Combine and deduplicate results
- Filter by minimum criteria
- Return prioritized list

This ensures we always find tokens even if one source fails!
"""

import logging
from typing import List, Set
import asyncio

from src.api.jupiter_client import JupiterClient
from src.api.dexscreener_client import DexScreenerClient

logger = logging.getLogger(__name__)


class TokenDiscovery:
    """
    Multi-source token discovery with intelligent fallbacks.

    Combines multiple data sources to ensure reliable token discovery.
    """

    def __init__(self):
        """Initialize token discovery with all sources."""
        self.jupiter = JupiterClient()
        self.dexscreener = DexScreenerClient()

        logger.info("Token Discovery initialized - multi-source strategy active")

    async def get_tokens(self, limit: int = 50) -> List[str]:
        """
        Get tokens from multiple sources.

        Strategy:
        1. Get tokens from Jupiter (verified list)
        2. Get trending from DexScreener
        3. Get latest from DexScreener
        4. Combine and deduplicate
        5. Return up to limit

        Args:
            limit: Maximum tokens to return

        Returns:
            List of unique token addresses
        """
        try:
            logger.info(f"\n{'='*60}")
            logger.info(f"🔍 TOKEN DISCOVERY - Target: {limit} tokens")
            logger.info(f"{'='*60}")

            all_tokens: Set[str] = set()

            # Source 1: Jupiter token list
            try:
                logger.debug("Fetching from Jupiter...")
                jupiter_tokens = await self.jupiter.get_trending_tokens(limit)

                if jupiter_tokens:
                    all_tokens.update(jupiter_tokens)
                    logger.info(f"✅ Jupiter: {len(jupiter_tokens)} tokens")
                else:
                    logger.warning("⚠️ Jupiter: No tokens returned")

            except Exception as e:
                logger.warning(f"⚠️ Jupiter failed: {e}")

            # Source 2: DexScreener trending
            try:
                logger.debug("Fetching trending from DexScreener...")
                dex_trending = await self.dexscreener.get_trending_tokens_async(limit)

                if dex_trending:
                    all_tokens.update(dex_trending)
                    logger.info(f"✅ DexScreener (trending): {len(dex_trending)} tokens")
                else:
                    logger.warning("⚠️ DexScreener trending: No tokens")

            except Exception as e:
                logger.warning(f"⚠️ DexScreener trending failed: {e}")

            # Source 3: DexScreener latest
            try:
                logger.debug("Fetching latest from DexScreener...")
                dex_latest = self.dexscreener.get_latest_tokens(limit // 2)  # Get fewer latest

                if dex_latest:
                    all_tokens.update(dex_latest)
                    logger.info(f"✅ DexScreener (latest): {len(dex_latest)} tokens")
                else:
                    logger.warning("⚠️ DexScreener latest: No tokens")

            except Exception as e:
                logger.warning(f"⚠️ DexScreener latest failed: {e}")

            # Convert to list and limit
            token_list = list(all_tokens)[:limit]

            logger.info(f"{'='*60}")
            logger.info(f"📊 DISCOVERY COMPLETE: {len(token_list)} unique tokens")
            logger.info(f"{'='*60}\n")

            if not token_list:
                logger.error("❌ NO TOKENS FROM ANY SOURCE!")
                return []

            return token_list

        except Exception as e:
            logger.error(f"Error in token discovery: {e}", exc_info=True)
            return []

    async def get_tokens_by_source(self, source: str, limit: int = 50) -> List[str]:
        """
        Get tokens from a specific source.

        Args:
            source: 'jupiter', 'dexscreener-trending', or 'dexscreener-latest'
            limit: Maximum tokens

        Returns:
            List of token addresses
        """
        try:
            if source == "jupiter":
                return await self.jupiter.get_trending_tokens(limit)

            elif source == "dexscreener-trending":
                return await self.dexscreener.get_trending_tokens_async(limit)

            elif source == "dexscreener-latest":
                return self.dexscreener.get_latest_tokens(limit)

            else:
                logger.warning(f"Unknown source: {source}")
                return []

        except Exception as e:
            logger.error(f"Error getting tokens from {source}: {e}")
            return []

    def filter_tokens(
        self,
        tokens: List[str],
        min_liquidity: float = 0,
        min_volume: float = 0
    ) -> List[str]:
        """
        Filter tokens by criteria (future enhancement).

        For now, just returns the list as-is.
        Can be enhanced to fetch liquidity/volume and filter.

        Args:
            tokens: List of token addresses
            min_liquidity: Minimum liquidity (USD)
            min_volume: Minimum 24h volume (USD)

        Returns:
            Filtered list of tokens
        """
        # TODO: Implement filtering by liquidity/volume
        # For now, return all
        return tokens


# Example usage
if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.INFO)

    async def test_discovery():
        discovery = TokenDiscovery()

        print("\n" + "="*60)
        print("TEST: Multi-Source Token Discovery")
        print("="*60)

        # Test 1: Get tokens from all sources
        tokens = await discovery.get_tokens(limit=50)
        print(f"\n✅ Found {len(tokens)} unique tokens")

        if tokens:
            print("\nFirst 10 tokens:")
            for i, token in enumerate(tokens[:10], 1):
                print(f"  {i}. {token}")

        # Test 2: Get from specific source
        print("\n" + "="*60)
        print("TEST: Jupiter Only")
        print("="*60)

        jupiter_tokens = await discovery.get_tokens_by_source("jupiter", 20)
        print(f"\n✅ Jupiter: {len(jupiter_tokens)} tokens")

        # Test 3: DexScreener trending
        print("\n" + "="*60)
        print("TEST: DexScreener Trending")
        print("="*60)

        dex_tokens = await discovery.get_tokens_by_source("dexscreener-trending", 20)
        print(f"\n✅ DexScreener: {len(dex_tokens)} tokens")

    asyncio.run(test_discovery())
