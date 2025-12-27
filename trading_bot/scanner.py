"""
Token Scanner - Discovers Trading Opportunities

Scans for new tokens using multiple sources and filters them
before passing to the risk assessor.
"""

import asyncio
import logging
from typing import List, Dict, Set, Optional
from datetime import datetime, timedelta

from trading_bot.api_clients import DexScreenerClient, JupiterClient

logger = logging.getLogger(__name__)


class TokenScanner:
    """
    Scans for new token opportunities.

    Uses DexScreener to discover tokens that meet basic criteria
    before passing to ML Bot 2 core for risk assessment.
    """

    def __init__(
        self,
        min_liquidity: float = 20000,
        min_volume_24h: float = 10000,
        dexscreener_api_key: Optional[str] = None,
        position_manager = None
    ):
        """
        Initialize token scanner.

        Args:
            min_liquidity: Minimum liquidity (USD) to consider
            min_volume_24h: Minimum 24h volume (USD) to consider
            dexscreener_api_key: Optional API key for DexScreener
            position_manager: Position manager to check for already-traded tokens
        """
        self.min_liquidity = min_liquidity
        self.min_volume_24h = min_volume_24h
        self.position_manager = position_manager

        # API clients
        self.dexscreener = DexScreenerClient(api_key=dexscreener_api_key)
        self.jupiter = JupiterClient()

        # Track scanned tokens to avoid duplicates within same session
        self.scanned_tokens: Set[str] = set()
        self.last_scan_time: Optional[datetime] = None

    async def __aenter__(self):
        """Async context manager entry."""
        await self.dexscreener.__aenter__()
        await self.jupiter.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.dexscreener.__aexit__(exc_type, exc_val, exc_tb)
        await self.jupiter.__aexit__(exc_type, exc_val, exc_tb)

    async def scan_new_tokens(self, limit: int = 20) -> List[Dict]:
        """
        Scan for new tokens using MULTI-SOURCE discovery.

        PHASE 1+2: Jupiter Discovery + DexScreener Categories

        Sources:
        - Jupiter: trending/traded/organic (cycling through 3 methods)
        - DexScreener: latest/trending (cycling through 2 categories)

        Args:
            limit: Max tokens to return after filtering

        Returns:
            List of token data dicts that pass initial filters
        """
        logger.info(f"=== MULTI-SOURCE TOKEN SCAN (limit: {limit}) ===")

        try:
            all_tokens = []

            # === SOURCE 1: JUPITER TRENDING (with cycling) ===
            try:
                jupiter_tokens = await self.jupiter.get_trending_tokens(limit=50)
                all_tokens.extend(jupiter_tokens)
                logger.info(f"  📊 Jupiter: {len(jupiter_tokens)} tokens")
            except Exception as e:
                logger.warning(f"  ⚠️  Jupiter scan failed: {e}")

            # === SOURCE 2: DEXSCREENER (with category cycling) ===
            try:
                dex_tokens = await self.dexscreener.get_latest_tokens(limit=50, use_cycling=True)
                all_tokens.extend(dex_tokens)
                logger.info(f"  📊 DexScreener: {len(dex_tokens)} tokens")
            except Exception as e:
                logger.warning(f"  ⚠️  DexScreener scan failed: {e}")

            if not all_tokens:
                logger.warning("❌ No tokens found from any source")
                return []

            logger.info(f"  📥 Total collected: {len(all_tokens)} tokens from {2} sources")

            # === DEDUPLICATION ===
            # Group by address to count sources and merge data
            token_map = {}
            for token in all_tokens:
                address = token.get('address')
                if not address:
                    continue

                if address not in token_map:
                    token_map[address] = token
                    token_map[address]['sources'] = [token.get('source', 'unknown')]
                    token_map[address]['source_count'] = 1
                else:
                    # Token seen in multiple sources - higher confidence!
                    source = token.get('source', 'unknown')
                    if source not in token_map[address]['sources']:
                        token_map[address]['sources'].append(source)
                        token_map[address]['source_count'] += 1

                    # Merge data (prefer non-zero values)
                    if token.get('liquidity', 0) > token_map[address].get('liquidity', 0):
                        token_map[address]['liquidity'] = token.get('liquidity')
                    if token.get('volume_24h', 0) > token_map[address].get('volume_24h', 0):
                        token_map[address]['volume_24h'] = token.get('volume_24h')

            unique_tokens = list(token_map.values())
            logger.info(f"  🔍 Deduplicated: {len(unique_tokens)} unique tokens")

            # Log multi-source tokens (higher confidence)
            multi_source = [t for t in unique_tokens if t.get('source_count', 1) > 1]
            if multi_source:
                logger.info(f"  ⭐ {len(multi_source)} tokens seen in multiple sources (high confidence)")

            # === FILTERING ===
            filtered_tokens = []

            for token in unique_tokens:
                address = token.get('address')

                # Skip if already scanned in this session
                if address in self.scanned_tokens:
                    continue

                # Skip if already have open position
                if self.position_manager:
                    has_open_position = any(
                        pos.token_address == address
                        for pos in self.position_manager.get_all_positions()
                    )
                    if has_open_position:
                        logger.debug(f"Skipped {address[:8]}... - Already have open position")
                        continue

                # Basic filters
                liquidity = token.get('liquidity_usd', 0) or token.get('liquidity', 0)
                volume_24h = token.get('volume_24h', 0)

                if liquidity < self.min_liquidity:
                    logger.debug(
                        f"Skipped {address[:8]}... - Low liquidity: ${liquidity:,.0f} "
                        f"(sources: {token.get('source_count', 1)})"
                    )
                    continue

                if volume_24h < self.min_volume_24h:
                    logger.debug(
                        f"Skipped {address[:8]}... - Low volume: ${volume_24h:,.0f} "
                        f"(sources: {token.get('source_count', 1)})"
                    )
                    continue

                # Add to filtered list
                filtered_tokens.append(token)
                self.scanned_tokens.add(address)

                if len(filtered_tokens) >= limit:
                    break

            logger.info(
                f"✅ {len(filtered_tokens)} tokens passed filters "
                f"(from {len(all_tokens)} total, {len(unique_tokens)} unique)"
            )

            self.last_scan_time = datetime.now()

            return filtered_tokens

        except Exception as e:
            logger.error(f"Error in multi-source scan: {e}", exc_info=True)
            return []

    async def get_token_details(self, token_address: str) -> Optional[Dict]:
        """
        Get comprehensive token details for risk assessment.

        Args:
            token_address: Token address

        Returns:
            Token details dict or None
        """
        try:
            # Get market data from DexScreener
            market_data = await self.dexscreener.get_token_profile(token_address)

            if not market_data:
                return None

            # Validate price with Jupiter
            jupiter_data = await self.jupiter.get_token_price_data(token_address)

            # If Jupiter has data, cross-validate
            if jupiter_data:
                dex_price = market_data.get('price_usd', 0)
                jup_price = jupiter_data.get('price_usd', 0)

                if dex_price > 0 and jup_price > 0:
                    price_diff = abs(dex_price - jup_price) / dex_price * 100

                    if price_diff > 20:
                        logger.warning(
                            f"Large price discrepancy for {token_address[:8]}... "
                            f"(DexScreener: ${dex_price:.8f}, Jupiter: ${jup_price:.8f})"
                        )

            return {
                'address': token_address,
                'market_data': market_data,
                'jupiter_data': jupiter_data,
                'scan_time': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error getting token details: {e}")
            return None

    def clear_scan_history(self, hours: int = 24):
        """
        Clear old entries from scan history.

        Args:
            hours: Clear entries older than this many hours
        """
        # For now, just clear all (could add timestamp tracking)
        old_count = len(self.scanned_tokens)
        self.scanned_tokens.clear()
        logger.info(f"Cleared {old_count} entries from scan history")

    def get_stats(self) -> Dict:
        """Get scanner statistics."""
        return {
            'scanned_tokens_count': len(self.scanned_tokens),
            'last_scan_time': self.last_scan_time.isoformat() if self.last_scan_time else None,
            'min_liquidity': self.min_liquidity,
            'min_volume_24h': self.min_volume_24h
        }
