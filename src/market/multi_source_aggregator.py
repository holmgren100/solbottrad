"""
Multi-source data aggregator with cross-validation.
Combines Jupiter, DexScreener, and Birdeye data with smart rate limiting.
"""

import asyncio
import time
import statistics
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from ..monitoring.logger import get_logger

logger = get_logger(__name__)


class RateLimiter:
    """Smart rate limiter to prevent API bans."""

    def __init__(self, calls_per_minute: int):
        """
        Initialize rate limiter.

        Args:
            calls_per_minute: Maximum API calls per minute
        """
        self.calls_per_minute = calls_per_minute
        self.calls_per_second = calls_per_minute / 60
        self.min_interval = 1.0 / self.calls_per_second
        self.last_call = 0
        self.call_count = 0
        self.window_start = time.time()

    async def acquire(self):
        """Wait if necessary to respect rate limit."""
        current_time = time.time()

        # Reset window if 60 seconds passed
        if current_time - self.window_start >= 60:
            self.call_count = 0
            self.window_start = current_time

        # Check if at limit for this minute
        if self.call_count >= self.calls_per_minute:
            sleep_time = 60 - (current_time - self.window_start)
            if sleep_time > 0:
                logger.debug(f"Rate limit reached, sleeping {sleep_time:.1f}s")
                await asyncio.sleep(sleep_time)
                self.call_count = 0
                self.window_start = time.time()

        # Enforce minimum interval between calls
        time_since_last = current_time - self.last_call
        if time_since_last < self.min_interval:
            await asyncio.sleep(self.min_interval - time_since_last)

        self.last_call = time.time()
        self.call_count += 1


class MultiSourceAggregator:
    """
    Aggregates data from multiple sources with cross-validation.
    Manages rate limits intelligently to get maximum data without bans.
    """

    def __init__(self, jupiter_client, dexscreener_client, birdeye_client):
        """Initialize aggregator with all API clients."""
        self.jupiter = jupiter_client
        self.dexscreener = dexscreener_client
        self.birdeye = birdeye_client

        # Rate limiters for each API
        self.dex_limiter = RateLimiter(calls_per_minute=280)  # Safe margin under 300
        self.jupiter_limiter = RateLimiter(calls_per_minute=500)  # Conservative estimate
        self.birdeye_limiter = RateLimiter(calls_per_minute=40)  # Free tier: 1 RPS = 60/min, but compute units limit is stricter - use 40 for safety

        # Cache for recent data (avoid redundant calls)
        self.cache = {}
        self.cache_ttl = 5  # 5 seconds cache for position monitoring

    def _get_cache_key(self, token_address: str, data_type: str) -> str:
        """Generate cache key."""
        return f"{token_address}:{data_type}"

    def _is_cache_valid(self, cache_entry: Dict) -> bool:
        """Check if cache entry is still valid."""
        if not cache_entry:
            return False
        age = time.time() - cache_entry['timestamp']
        return age < self.cache_ttl

    async def get_token_data_all_sources(self, token_address: str) -> Dict:
        """
        Get comprehensive token data from ALL sources with cross-validation.

        This is the MAIN method for position monitoring - gets everything.

        Args:
            token_address: Token mint address

        Returns:
            Dictionary with validated data from all sources
        """
        # Check cache first
        cache_key = self._get_cache_key(token_address, 'comprehensive')
        if cache_key in self.cache and self._is_cache_valid(self.cache[cache_key]):
            logger.debug(f"Cache hit for {token_address[:8]}...")
            return self.cache[cache_key]['data']

        # Fetch from all sources concurrently
        results = await asyncio.gather(
            self._get_dexscreener_data(token_address),
            self._get_jupiter_data(token_address),
            self._get_birdeye_data(token_address),
            return_exceptions=True
        )

        dex_data, jupiter_data, birdeye_data = results

        # Handle exceptions
        dex_data = None if isinstance(dex_data, Exception) else dex_data
        jupiter_data = None if isinstance(jupiter_data, Exception) else jupiter_data
        birdeye_data = None if isinstance(birdeye_data, Exception) else birdeye_data

        # Cross-validate and combine
        combined = self._cross_validate_data(
            token_address,
            dex_data,
            jupiter_data,
            birdeye_data
        )

        # Cache result
        self.cache[cache_key] = {
            'data': combined,
            'timestamp': time.time()
        }

        return combined

    async def _get_dexscreener_data(self, token_address: str) -> Optional[Dict]:
        """Get data from DexScreener with rate limiting."""
        await self.dex_limiter.acquire()

        try:
            pairs = await self.dexscreener.get_token_pairs(token_address)
            if not pairs:
                return None

            # Get best pair (highest liquidity)
            best_pair = max(pairs, key=lambda p: float(p.get('liquidity', {}).get('usd', 0) or 0))

            return {
                'source': 'dexscreener',
                'price': float(best_pair.get('priceUsd', 0)),
                'liquidity': float(best_pair.get('liquidity', {}).get('usd', 0) or 0),
                'volume_24h': float(best_pair.get('volume', {}).get('h24', 0) or 0),
                'volume_6h': float(best_pair.get('volume', {}).get('h6', 0) or 0),
                'volume_1h': float(best_pair.get('volume', {}).get('h1', 0) or 0),
                'price_change_24h': float(best_pair.get('priceChange', {}).get('h24', 0) or 0),
                'txns_24h_buys': best_pair.get('txns', {}).get('h24', {}).get('buys', 0),
                'txns_24h_sells': best_pair.get('txns', {}).get('h24', {}).get('sells', 0),
                'pair_created_at': best_pair.get('pairCreatedAt', 0),
                'dex_id': best_pair.get('dexId', ''),
                'timestamp': time.time()
            }
        except Exception as e:
            logger.error(f"DexScreener error for {token_address[:8]}: {e}")
            return None

    async def _get_jupiter_data(self, token_address: str) -> Optional[Dict]:
        """Get data from Jupiter with rate limiting."""
        await self.jupiter_limiter.acquire()

        try:
            # Jupiter doesn't have direct token info endpoint
            # We'll use it for price verification via quote API
            # For now, return None - implement quote check if needed
            return None
        except Exception as e:
            logger.error(f"Jupiter error for {token_address[:8]}: {e}")
            return None

    async def _get_birdeye_data(self, token_address: str) -> Optional[Dict]:
        """Get data from Birdeye with rate limiting."""
        await self.birdeye_limiter.acquire()

        try:
            # Get token overview from Birdeye
            token_data = await self.birdeye.get_token_overview(token_address)
            if not token_data:
                return None

            return {
                'source': 'birdeye',
                'price': float(token_data.get('price', 0)),
                'liquidity': float(token_data.get('liquidity', 0)),
                'volume_24h': float(token_data.get('v24hUSD', 0)),
                'market_cap': float(token_data.get('mc', 0)),
                'holder_count': token_data.get('holder', 0),
                'timestamp': time.time()
            }
        except Exception as e:
            logger.error(f"Birdeye error for {token_address[:8]}: {e}")
            return None

    def _cross_validate_data(
        self,
        token_address: str,
        dex_data: Optional[Dict],
        jupiter_data: Optional[Dict],
        birdeye_data: Optional[Dict]
    ) -> Dict:
        """
        Cross-validate data from multiple sources.

        Uses median for numerical values when sources disagree.
        Flags confidence level based on source agreement.
        """
        sources = []
        if dex_data:
            sources.append(dex_data)
        if jupiter_data:
            sources.append(jupiter_data)
        if birdeye_data:
            sources.append(birdeye_data)

        if not sources:
            return {
                'token_address': token_address,
                'confidence': 'none',
                'sources_count': 0,
                'price': 0,
                'liquidity': 0,
                'volume_24h': 0,
                'error': 'No data from any source'
            }

        # Extract prices for validation
        prices = [s['price'] for s in sources if s.get('price', 0) > 0]
        liquidities = [s['liquidity'] for s in sources if s.get('liquidity', 0) > 0]
        volumes = [s['volume_24h'] for s in sources if s.get('volume_24h', 0) > 0]

        # Calculate median values
        price = statistics.median(prices) if prices else 0
        liquidity = statistics.median(liquidities) if liquidities else 0
        volume_24h = statistics.median(volumes) if volumes else 0

        # Check price agreement (sources within 10% = high confidence)
        price_confidence = 'low'
        if len(prices) >= 2:
            price_variance = max(abs(p - price) / price * 100 for p in prices) if price > 0 else 100
            if price_variance < 10:
                price_confidence = 'high'
            elif price_variance < 20:
                price_confidence = 'medium'

        # Determine overall confidence
        if len(sources) >= 2 and price_confidence in ['high', 'medium']:
            confidence = 'high'
        elif len(sources) >= 2:
            confidence = 'medium'
        else:
            confidence = 'low'

        # Build comprehensive result
        result = {
            'token_address': token_address,
            'confidence': confidence,
            'sources_count': len(sources),
            'sources_used': [s['source'] for s in sources],

            # Core data (median values)
            'price': price,
            'liquidity': liquidity,
            'volume_24h': volume_24h,

            # Additional data from best source (DexScreener preferred)
            'volume_6h': dex_data.get('volume_6h', 0) if dex_data else 0,
            'volume_1h': dex_data.get('volume_1h', 0) if dex_data else 0,
            'price_change_24h': dex_data.get('price_change_24h', 0) if dex_data else 0,
            'txns_24h_buys': dex_data.get('txns_24h_buys', 0) if dex_data else 0,
            'txns_24h_sells': dex_data.get('txns_24h_sells', 0) if dex_data else 0,
            'pair_created_at': dex_data.get('pair_created_at', 0) if dex_data else 0,
            'dex_id': dex_data.get('dex_id', '') if dex_data else '',

            # Birdeye exclusive data
            'market_cap': birdeye_data.get('market_cap', 0) if birdeye_data else 0,
            'holder_count': birdeye_data.get('holder_count', 0) if birdeye_data else 0,

            # Metadata
            'timestamp': time.time(),
            'price_confidence': price_confidence
        }

        # Log if sources disagree significantly
        if confidence == 'low' and len(sources) > 1:
            logger.warning(
                f"⚠️ Low confidence data for {token_address[:8]}... "
                f"Sources: {result['sources_used']}, "
                f"Prices: {prices}"
            )

        return result

    async def get_liquidity_fast(self, token_address: str) -> Tuple[float, str]:
        """
        Fast liquidity check - uses cached data or single fastest source.

        For high-frequency monitoring (every 5 seconds).

        Returns:
            Tuple of (liquidity_usd, confidence)
        """
        # Check cache first
        cache_key = self._get_cache_key(token_address, 'liquidity')
        if cache_key in self.cache and self._is_cache_valid(self.cache[cache_key]):
            cached = self.cache[cache_key]
            return cached['data']['liquidity'], cached['data']['confidence']

        # Get from DexScreener (fastest and most reliable for liquidity)
        await self.dex_limiter.acquire()

        try:
            pairs = await self.dexscreener.get_token_pairs(token_address)
            if not pairs:
                return 0, 'none'

            best_pair = max(pairs, key=lambda p: float(p.get('liquidity', {}).get('usd', 0) or 0))
            liquidity = float(best_pair.get('liquidity', {}).get('usd', 0) or 0)

            # Cache it
            self.cache[cache_key] = {
                'data': {'liquidity': liquidity, 'confidence': 'medium'},
                'timestamp': time.time()
            }

            return liquidity, 'medium'

        except Exception as e:
            logger.error(f"Fast liquidity check failed for {token_address[:8]}: {e}")
            return 0, 'none'

    async def monitor_position_continuous(
        self,
        token_address: str,
        entry_liquidity: float,
        callback_on_drop,
        check_interval: int = 5
    ):
        """
        Continuously monitor a position for liquidity/price drops.

        This runs in background for each open position.

        Args:
            token_address: Token to monitor
            entry_liquidity: Liquidity at entry (for comparison)
            callback_on_drop: Async function to call if critical drop detected
            check_interval: Seconds between checks (default 5)
        """
        logger.info(f"🔍 Starting continuous monitoring for {token_address[:8]}... every {check_interval}s")

        warning_threshold = 0.30  # 30% drop = warning
        critical_threshold = 0.50  # 50% drop = exit
        absolute_minimum = 30000  # $30k = critical

        last_warning_time = 0

        while True:
            try:
                # Get comprehensive data
                data = await self.get_token_data_all_sources(token_address)

                if not data or data['confidence'] == 'none':
                    logger.warning(f"⚠️ No data available for {token_address[:8]}...")
                    await asyncio.sleep(check_interval)
                    continue

                current_liquidity = data['liquidity']
                current_price = data['price']

                # Calculate drop percentage
                drop_pct = (entry_liquidity - current_liquidity) / entry_liquidity if entry_liquidity > 0 else 0

                # CRITICAL: Absolute minimum check
                if current_liquidity < absolute_minimum:
                    logger.error(
                        f"🚨 CRITICAL: {token_address[:8]}... liquidity ${current_liquidity:,.0f} "
                        f"below ${absolute_minimum:,.0f} - TRIGGERING FORCE EXIT"
                    )
                    await callback_on_drop(
                        'critical_low_liquidity',
                        {
                            'current_liquidity': current_liquidity,
                            'entry_liquidity': entry_liquidity,
                            'drop_pct': drop_pct * 100,
                            'reason': f'Below ${absolute_minimum:,.0f}'
                        }
                    )
                    break

                # CRITICAL: Drop percentage check
                if drop_pct > critical_threshold:
                    logger.error(
                        f"🚨 CRITICAL: {token_address[:8]}... liquidity dropped {drop_pct*100:.0f}% "
                        f"(${entry_liquidity:,.0f} → ${current_liquidity:,.0f}) - TRIGGERING FORCE EXIT"
                    )
                    await callback_on_drop(
                        'liquidity_drop_critical',
                        {
                            'current_liquidity': current_liquidity,
                            'entry_liquidity': entry_liquidity,
                            'drop_pct': drop_pct * 100,
                            'reason': f'Dropped {drop_pct*100:.0f}%'
                        }
                    )
                    break

                # WARNING: Significant drop but not critical yet
                elif drop_pct > warning_threshold:
                    # Only warn once per minute to avoid spam
                    if time.time() - last_warning_time > 60:
                        logger.warning(
                            f"⚠️ WARNING: {token_address[:8]}... liquidity dropped {drop_pct*100:.0f}% "
                            f"(${entry_liquidity:,.0f} → ${current_liquidity:,.0f})"
                        )
                        last_warning_time = time.time()

                # All good - log debug info
                else:
                    logger.debug(
                        f"✅ {token_address[:8]}... OK: "
                        f"Liq ${current_liquidity:,.0f} ({drop_pct*100:+.1f}%), "
                        f"Price ${current_price:.8f}, "
                        f"Confidence: {data['confidence']}"
                    )

            except Exception as e:
                logger.error(f"Error monitoring {token_address[:8]}: {e}")

            # Wait before next check
            await asyncio.sleep(check_interval)
