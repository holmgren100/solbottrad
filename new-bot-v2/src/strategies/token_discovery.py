"""
Token Discovery - Multi-Source Token Discovery Strategy

Discovers tokens from multiple sources with fallbacks:
1. Birdeye (PRIMARY - trending tokens, requires API key)
2. DexScreener (PRIMARY - trending and latest, no API key needed)
3. Fallback list (hardcoded popular tokens)

Strategy:
- Birdeye provides trending tokens (you have API key!)
- DexScreener provides trending/latest pairs (always works, no API key)
- Combine and deduplicate results
- Return prioritized list
- Use fallback list if all sources fail

This ensures we always find tokens even if APIs fail!
"""

import logging
from typing import List, Set
import asyncio

from src.api.birdeye_client import BirdeyeClient
from src.api.dexscreener_client import DexScreenerClient
from src.strategies.token_fallback import get_fallback_tokens

logger = logging.getLogger(__name__)


class TokenDiscovery:
    """
    Multi-source token discovery with intelligent fallbacks.

    Combines multiple data sources to ensure reliable token discovery.
    """

    def __init__(self):
        """Initialize token discovery with all sources."""
        self.birdeye = BirdeyeClient()
        self.dexscreener = DexScreenerClient()

        logger.info("Token Discovery initialized - multi-source strategy active")

    async def get_tokens(self, limit: int = 50) -> List[str]:
        """
        Get tokens from multiple sources with smart deduplication.

        Priority order:
        1. DexScreener trending/latest (PRIMARY - always works, no API key!)
        2. Birdeye trending (SECONDARY - if API key works)
        3. Fallback list (if both fail)

        Smart deduplication:
        - Combines tokens from multiple sources
        - Prevents scanning same token repeatedly
        - Ensures diversity

        Args:
            limit: Maximum tokens to return

        Returns:
            List of unique token addresses (deduplicated)
        """
        try:
            logger.info(f"\n{'='*60}")
            logger.info(f"🔍 TOKEN DISCOVERY - Target: {limit} tokens")
            logger.info(f"{'='*60}")

            all_tokens: Set[str] = set()

            # Source 1: DexScreener trending/latest (PRIMARY - reliable!)
            try:
                logger.debug("Fetching trending from DexScreener (PRIMARY)...")
                dex_tokens = self.dexscreener.get_trending_tokens(limit * 2)  # Get more for filtering

                if dex_tokens:
                    all_tokens.update(dex_tokens)
                    logger.info(f"✅ DexScreener (latest pairs): {len(dex_tokens)} tokens")
                else:
                    logger.warning("⚠️ DexScreener: No tokens")

            except Exception as e:
                logger.warning(f"⚠️ DexScreener failed: {e}")

            # Source 2: Birdeye trending (SECONDARY - if API works)
            try:
                logger.debug("Fetching trending from Birdeye (SECONDARY)...")
                birdeye_tokens = await self.birdeye.get_trending_tokens(limit)

                if birdeye_tokens:
                    # Filter out duplicates from DexScreener
                    new_tokens = [t for t in birdeye_tokens if t not in all_tokens]
                    all_tokens.update(new_tokens)
                    logger.info(f"✅ Birdeye (trending): {len(birdeye_tokens)} tokens ({len(new_tokens)} unique)")
                else:
                    logger.debug("ℹ️  Birdeye: No tokens (API key may not be working)")

            except Exception as e:
                logger.debug(f"ℹ️  Birdeye failed (expected if no API key): {e}")

            # Convert to list and limit
            token_list = list(all_tokens)[:limit]

            # If no tokens from ANY source, use fallback list
            if not token_list:
                logger.warning("❌ NO TOKENS FROM ANY SOURCE - USING FALLBACK LIST!")
                fallback_tokens = get_fallback_tokens(limit)
                token_list = fallback_tokens
                logger.info(f"✅ Fallback: {len(fallback_tokens)} hardcoded tokens")

            logger.info(f"{'='*60}")
            logger.info(f"📊 DISCOVERY COMPLETE: {len(token_list)} unique tokens")
            logger.info(f"{'='*60}\n")

            return token_list

        except Exception as e:
            logger.error(f"Error in token discovery: {e}", exc_info=True)
            # Return fallback on error
            return get_fallback_tokens(limit)

    async def get_tokens_by_source(self, source: str, limit: int = 50) -> List[str]:
        """
        Get tokens from a specific source.

        Args:
            source: 'birdeye', 'dexscreener-trending', or 'dexscreener-latest'
            limit: Maximum tokens

        Returns:
            List of token addresses
        """
        try:
            if source == "birdeye":
                return await self.birdeye.get_trending_tokens(limit)

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
        print("TEST: Birdeye Only")
        print("="*60)

        birdeye_tokens = await discovery.get_tokens_by_source("birdeye", 20)
        print(f"\n✅ Birdeye: {len(birdeye_tokens)} tokens")

        # Test 3: DexScreener trending
        print("\n" + "="*60)
        print("TEST: DexScreener Trending")
        print("="*60)

        dex_tokens = await discovery.get_tokens_by_source("dexscreener-trending", 20)
        print(f"\n✅ DexScreener: {len(dex_tokens)} tokens")

    asyncio.run(test_discovery())
