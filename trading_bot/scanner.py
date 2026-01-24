"""
Token Scanner - Discovers Trading Opportunities

Scans for new tokens using multiple sources and filters them
before passing to the risk assessor.
"""

import asyncio
import logging
from typing import List, Dict, Set, Optional
from datetime import datetime, timedelta

from trading_bot.api_clients import DexScreenerClient, JupiterClient, BirdeyeClient, CoinGeckoClient
import os

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

        # Multi-source API clients (optional)
        birdeye_key = os.getenv('BIRDEYE_API_KEY')
        coingecko_key = os.getenv('COINGECKO_API_KEY')
        self.birdeye = BirdeyeClient(birdeye_key) if birdeye_key and os.getenv('ENABLE_BIRDEYE', 'false').lower() == 'true' else None
        self.coingecko = CoinGeckoClient(coingecko_key) if coingecko_key and os.getenv('ENABLE_COINGECKO', 'false').lower() == 'true' else None

        # Track scanned tokens with timestamps (allow re-entry after cooldown)
        self.scanned_tokens: Dict[str, datetime] = {}  # address -> last_scan_time
        self.scan_cooldown_minutes = 5  # Allow re-entry after 5 min (memecoin momentum changes fast!)
        self.last_scan_time: Optional[datetime] = None

    async def __aenter__(self):
        """Async context manager entry."""
        await self.dexscreener.__aenter__()
        await self.jupiter.__aenter__()
        if self.birdeye:
            await self.birdeye.__aenter__()
        if self.coingecko:
            await self.coingecko.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.dexscreener.__aexit__(exc_type, exc_val, exc_tb)
        await self.jupiter.__aexit__(exc_type, exc_val, exc_tb)
        if self.birdeye:
            await self.birdeye.__aexit__(exc_type, exc_val, exc_tb)
        if self.coingecko:
            await self.coingecko.__aexit__(exc_type, exc_val, exc_tb)

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
                logger.info("  🔍 Querying Jupiter API...")
                jupiter_tokens = await self.jupiter.get_trending_tokens(limit=50)
                all_tokens.extend(jupiter_tokens)
                logger.info(f"  📊 Jupiter: {len(jupiter_tokens)} tokens")
            except Exception as e:
                logger.error(f"  ❌ Jupiter scan failed: {e}", exc_info=True)

            # === SOURCE 2: DEXSCREENER (with category cycling) ===
            try:
                dex_tokens = await self.dexscreener.get_latest_tokens(limit=50, use_cycling=True)
                all_tokens.extend(dex_tokens)
                logger.info(f"  📊 DexScreener: {len(dex_tokens)} tokens")
            except Exception as e:
                logger.warning(f"  ⚠️  DexScreener scan failed: {e}")

            # === SOURCE 3: BIRDEYE (Solana-native trending + security) ===
            if self.birdeye:
                try:
                    logger.info("  🔍 Querying Birdeye API...")
                    birdeye_tokens = await self.birdeye.get_trending_tokens(limit=30)
                    all_tokens.extend(birdeye_tokens)
                    logger.info(f"  📊 Birdeye: {len(birdeye_tokens)} tokens")
                except Exception as e:
                    logger.warning(f"  ⚠️  Birdeye scan failed: {e}")

            # === SOURCE 4: COINGECKO (Cross-chain gainers) ===
            if self.coingecko:
                try:
                    logger.info("  🔍 Querying CoinGecko API...")
                    coingecko_tokens = await self.coingecko.get_top_gainers(limit=30)
                    # Note: CoinGecko returns cross-chain data, will need address mapping for Solana
                    all_tokens.extend(coingecko_tokens)
                    logger.info(f"  📊 CoinGecko: {len(coingecko_tokens)} gainers")
                except Exception as e:
                    logger.warning(f"  ⚠️  CoinGecko scan failed: {e}")

            if not all_tokens:
                logger.warning("❌ No tokens found from any source")
                return []

            source_count = 2 + (1 if self.birdeye else 0) + (1 if self.coingecko else 0)
            logger.info(f"  📥 Total collected: {len(all_tokens)} tokens from {source_count} sources")

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

            # === ENRICH WITH DEXSCREENER DATA (GET TXNS/BUYS/SELLS) ===
            # Critical: Jupiter tokens don't have txns data, need DexScreener for that!
            logger.info(f"  📡 Enriching tokens with DexScreener data (txns/buys/sells)...")
            enriched_tokens = []
            for token in unique_tokens[:30]:  # Limit to avoid rate limits
                try:
                    address = token.get('address')
                    # Get full data from DexScreener
                    dex_data = await self.dexscreener.get_token_profile(address)

                    if dex_data:
                        # Merge DexScreener data (has txns) with existing token data
                        enriched_token = {**token, **dex_data}
                        enriched_tokens.append(enriched_token)
                    else:
                        # Keep original if DexScreener doesn't have it
                        enriched_tokens.append(token)
                except Exception as e:
                    logger.debug(f"Failed to enrich {address[:8]}...: {e}")
                    enriched_tokens.append(token)

            logger.info(f"  ✅ Enriched {len(enriched_tokens)} tokens with DexScreener data")

            # Use enriched tokens for filtering
            unique_tokens = enriched_tokens

            # === FILTERING ===
            filtered_tokens = []

            # CRITICAL: Filter out stablecoins and bluechips!
            EXCLUDED_TOKENS = {
                # Native tokens
                'So11111111111111111111111111111111111111112',  # SOL
                # Stablecoins
                'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v',  # USDC
                'Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB',  # USDT
                'USD1ttGYauSYU7wmwKPEvQGTRdq9icial4EmuB',      # USD1
                # Wrapped BTC
                'cbbtcf3aGTPqhU2kAFWbEDN747ZMwCgethernet4iMij',  # cbBTC (Coinbase BTC)
                '3NZ9JMVBmGAqocybic2c7LQCJScmgsAZ6vQqTDzcqmJh',  # WBTC (Wrapped BTC)
                # Liquid staking tokens
                'mSoLzYCxHdYgdzU16g5QSh3i5K3z3KZK7ytfqcJm7So',   # mSOL
                '7dHbWXmci3dT8UFYWYZweBLXgycu7Y3iL6trKn1Y7ARj',  # stSOL
                # Wrapped ETH
                '7vfCXTUXx5WJV5JADk17DUJ4ksgau7utNKj4b963voxs',  # ETH (wrapped)
            }

            # Stablecoin patterns (name/symbol based)
            STABLECOIN_PATTERNS = ['USDC', 'USDT', 'USD1', 'DAI', 'BUSD', 'TUSD', 'USDP', 'FRAX']
            BLUECHIP_PATTERNS = ['BTC', 'WBTC', 'cbBTC', 'ETH', 'WETH', 'SOL', 'stSOL', 'mSOL']

            for token in unique_tokens:
                address = token.get('address')
                symbol = (token.get('symbol') or '').upper()
                name = (token.get('name') or '').upper()

                # FILTER 1: Skip known stablecoins/bluechips by address
                if address in EXCLUDED_TOKENS:
                    logger.debug(f"Skipped {address[:8]}... - Known stablecoin/bluechip")
                    continue

                # FILTER 2: Skip by symbol/name patterns
                if any(pattern in symbol or pattern in name for pattern in STABLECOIN_PATTERNS + BLUECHIP_PATTERNS):
                    logger.debug(f"Skipped {address[:8]}... ({symbol}) - Stablecoin/bluechip pattern")
                    continue

                # FILTER 3: Skip if scanned recently (allow re-entry after cooldown)
                if address in self.scanned_tokens:
                    last_scan = self.scanned_tokens[address]
                    time_since_scan = (datetime.now() - last_scan).total_seconds() / 60  # minutes

                    if time_since_scan < self.scan_cooldown_minutes:
                        # Too soon - skip to avoid duplicate entries
                        logger.debug(f"Skipped {address[:8]}... - Scanned {time_since_scan:.0f}min ago (cooldown: {self.scan_cooldown_minutes}min)")
                        continue
                    else:
                        # Cooldown expired - allow re-entry!
                        logger.debug(f"Re-entry allowed: {address[:8]}... - {time_since_scan:.0f}min since last scan")

                # FILTER 4: Skip if already have open position
                if self.position_manager:
                    has_open_position = any(
                        pos.token_address == address
                        for pos in self.position_manager.get_all_positions()
                    )
                    if has_open_position:
                        logger.debug(f"Skipped {address[:8]}... - Already have open position")
                        continue

                # FILTERS REMOVED - Let risk assessor handle filtering like old working bot
                # Old bot gathered ALL tokens, then risk assessor decided
                # Scanner filters were blocking everything because Jupiter tokens have liquidity=0

                # Add to filtered list (no filters)
                filtered_tokens.append(token)
                self.scanned_tokens[address] = datetime.now()  # Track scan time for cooldown

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
        cutoff_time = datetime.now() - timedelta(hours=hours)
        old_count = len(self.scanned_tokens)

        # Remove entries older than cutoff
        self.scanned_tokens = {
            addr: scan_time
            for addr, scan_time in self.scanned_tokens.items()
            if scan_time > cutoff_time
        }

        cleared = old_count - len(self.scanned_tokens)
        if cleared > 0:
            logger.info(f"Cleared {cleared} old entries from scan history (kept {len(self.scanned_tokens)} recent)")

    def get_stats(self) -> Dict:
        """Get scanner statistics."""
        return {
            'scanned_tokens_count': len(self.scanned_tokens),
            'last_scan_time': self.last_scan_time.isoformat() if self.last_scan_time else None,
            'min_liquidity': self.min_liquidity,
            'min_volume_24h': self.min_volume_24h
        }
