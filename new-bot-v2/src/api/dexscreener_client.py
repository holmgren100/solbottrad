"""
DexScreener Client - Market Data and Price Candles

Uses DexScreener FREE API for:
- Market data (price, volume, liquidity)
- Price history / candles
- Buy/Sell pressure
- Token pair information

Limit: Rate limited (respect limits)
Cost: FREE
"""

import requests
import logging
from typing import Dict, List, Optional
import time

from config.apis import (
    DEXSCREENER_ENDPOINTS,
    DEXSCREENER_RATE_LIMIT_DELAY,
    API_TIMEOUT_SECONDS,
    API_MAX_RETRIES,
    API_RETRY_DELAY,
    DEFAULT_HEADERS
)

logger = logging.getLogger(__name__)


class DexScreenerClient:
    """
    Client for DexScreener API.

    Primary use: Market data, price candles, volume analysis
    """

    def __init__(self):
        """Initialize DexScreener client."""
        self.endpoints = DEXSCREENER_ENDPOINTS
        self.timeout = API_TIMEOUT_SECONDS
        self.max_retries = API_MAX_RETRIES
        self.retry_delay = API_RETRY_DELAY
        self.rate_limit_delay = DEXSCREENER_RATE_LIMIT_DELAY
        self.last_request_time = 0

    def _rate_limit(self):
        """Implement rate limiting to respect API limits."""
        now = time.time()
        time_since_last = now - self.last_request_time

        if time_since_last < self.rate_limit_delay:
            sleep_time = self.rate_limit_delay - time_since_last
            logger.debug(f"Rate limiting: sleeping {sleep_time:.2f}s")
            time.sleep(sleep_time)

        self.last_request_time = time.time()

    def _make_request(self, url: str) -> Optional[Dict]:
        """
        Make HTTP request to DexScreener with retries and rate limiting.

        Args:
            url: Full API endpoint URL

        Returns:
            Response data or None on failure
        """
        self._rate_limit()

        for attempt in range(self.max_retries):
            try:
                response = requests.get(
                    url,
                    headers=DEFAULT_HEADERS,
                    timeout=self.timeout
                )

                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 429:  # Rate limited
                    logger.warning("DexScreener rate limit hit, waiting...")
                    time.sleep(self.rate_limit_delay * 2)
                else:
                    logger.warning(
                        f"DexScreener request failed (attempt {attempt + 1}/{self.max_retries}): "
                        f"Status {response.status_code}"
                    )

            except requests.exceptions.Timeout:
                logger.warning(f"DexScreener timeout (attempt {attempt + 1}/{self.max_retries})")
            except Exception as e:
                logger.error(f"DexScreener request error: {e}")

            if attempt < self.max_retries - 1:
                time.sleep(self.retry_delay * (attempt + 1))

        logger.error(f"DexScreener request failed after {self.max_retries} attempts")
        return None

    def get_token_data(self, token_address: str) -> Optional[Dict]:
        """
        Get comprehensive market data for a token.

        Args:
            token_address: Token mint address

        Returns:
            {
                "price": float,
                "volume_5m": float,
                "volume_1h": float,
                "volume_24h": float,
                "liquidity": float,
                "buys": int,
                "sells": int,
                "price_change_5m": float,
                "price_change_1h": float,
                "price_change_24h": float,
                "pairs": List[Dict]  # All trading pairs
            }
            or None on failure
        """
        try:
            url = f"{self.endpoints['token_profiles']}/{token_address}"
            result = self._make_request(url)

            if not result or "pairs" not in result or len(result["pairs"]) == 0:
                logger.debug(f"No market data for {token_address}")
                return None

            # Get the main/most liquid pair (usually first one)
            main_pair = result["pairs"][0]

            # Extract base token info (the token we're querying)
            base_token = main_pair.get("baseToken", {})
            quote_token = main_pair.get("quoteToken", {})

            # Determine which token is ours (not SOL/USDC)
            if base_token.get("address", "").lower() == token_address.lower():
                our_token = base_token
            else:
                our_token = quote_token

            # Extract data
            token_data = {
                "address": token_address,
                "symbol": our_token.get("symbol", "UNKNOWN"),
                "name": our_token.get("name", "UNKNOWN"),
                "price": float(main_pair.get("priceUsd", 0)),
                "volume_5m": float(main_pair.get("volume", {}).get("m5", 0)),
                "volume_1h": float(main_pair.get("volume", {}).get("h1", 0)),
                "volume_24h": float(main_pair.get("volume", {}).get("h24", 0)),
                "liquidity": float(main_pair.get("liquidity", {}).get("usd", 0)),
                "buys": int(main_pair.get("txns", {}).get("m5", {}).get("buys", 0)),
                "sells": int(main_pair.get("txns", {}).get("m5", {}).get("sells", 0)),
                "buys_1h": int(main_pair.get("txns", {}).get("h1", {}).get("buys", 0)),
                "sells_1h": int(main_pair.get("txns", {}).get("h1", {}).get("sells", 0)),
                "price_change_5m": float(main_pair.get("priceChange", {}).get("m5", 0)),
                "price_change_1h": float(main_pair.get("priceChange", {}).get("h1", 0)),
                "price_change_24h": float(main_pair.get("priceChange", {}).get("h24", 0)),
                "pair_address": main_pair.get("pairAddress", ""),
                "dex": main_pair.get("dexId", ""),
                "market_cap_usd": float(main_pair.get("fdv", 0)),  # FDV = Fully Diluted Valuation
                "pairs": result["pairs"]  # All pairs for reference
            }

            logger.debug(
                f"Token {token_address}: "
                f"${token_data['price']:.6f}, "
                f"Vol5m: ${token_data['volume_5m']:.0f}, "
                f"Liq: ${token_data['liquidity']:.0f}"
            )

            return token_data

        except Exception as e:
            logger.error(f"Error getting token data: {e}")
            return None

    def get_price_history(
        self,
        token_address: str,
        timeframe: str = "15m",
        limit: int = 50
    ) -> Optional[List[Dict]]:
        """
        Generate approximate candles from DexScreener price change data.

        DexScreener gives price changes over 5m, 1h, 24h. We use this to build
        approximate candles that are good enough for MACD/RSI calculations.

        Args:
            token_address: Token mint address
            timeframe: Candle timeframe ("15m" recommended)
            limit: Number of candles to return (default 50 for MACD)

        Returns:
            List of approximate candles
        """
        try:
            # Get current token data
            token_data = self.get_token_data(token_address)

            if not token_data:
                return None

            current_price = token_data["price"]
            current_time = int(time.time())

            # Price changes
            price_change_5m = token_data.get("price_change_5m", 0)
            price_change_1h = token_data.get("price_change_1h", 0)
            price_change_24h = token_data.get("price_change_24h", 0)

            # Calculate historical prices
            if price_change_5m != -100:
                price_5m_ago = current_price / (1 + price_change_5m / 100)
            else:
                price_5m_ago = current_price

            if price_change_1h != -100:
                price_1h_ago = current_price / (1 + price_change_1h / 100)
            else:
                price_1h_ago = current_price

            if price_change_24h != -100:
                price_24h_ago = current_price / (1 + price_change_24h / 100)
            else:
                price_24h_ago = current_price

            # Volume data
            volume_5m = token_data.get("volume_5m", 0)
            volume_1h = token_data.get("volume_1h", 0)
            volume_24h = token_data.get("volume_24h", 0)

            # Timeframe in seconds (15m = 900s)
            timeframe_seconds = 900

            # Generate approximate candles working backwards from current price
            candles = []

            for i in range(limit):
                candle_time = current_time - (i * timeframe_seconds)
                seconds_ago = i * timeframe_seconds

                # Linear interpolation between known price points
                if seconds_ago <= 300:  # 0-5 minutes
                    progress = seconds_ago / 300
                    base_price = current_price - (current_price - price_5m_ago) * progress
                elif seconds_ago <= 3600:  # 5 min - 1 hour
                    progress = (seconds_ago - 300) / 3300
                    base_price = price_5m_ago - (price_5m_ago - price_1h_ago) * progress
                else:  # Beyond 1 hour
                    hours_ago = seconds_ago / 3600
                    if hours_ago <= 24:
                        progress = (hours_ago - 1) / 23
                        base_price = price_1h_ago - (price_1h_ago - price_24h_ago) * progress
                    else:
                        base_price = price_24h_ago * 0.98  # Assume slight decline

                # Simulate OHLC with small variations (±1%)
                import random
                variation = base_price * 0.01 if base_price > 0 else 0.0001

                open_price = base_price + random.uniform(-variation, variation)
                close_price = base_price + random.uniform(-variation, variation)
                high_price = max(open_price, close_price) + random.uniform(0, variation)
                low_price = min(open_price, close_price) - random.uniform(0, variation)

                # Estimate volume per candle
                if seconds_ago <= 300:
                    candle_volume = volume_5m / (300 / timeframe_seconds) if volume_5m > 0 else 0
                elif seconds_ago <= 3600:
                    hourly_vol = max(0, volume_1h - volume_5m)
                    candle_volume = hourly_vol / ((3600 - 300) / timeframe_seconds) if hourly_vol > 0 else 0
                else:
                    daily_vol = max(0, volume_24h - volume_1h)
                    candle_volume = daily_vol / ((86400 - 3600) / timeframe_seconds) if daily_vol > 0 else 0

                candle = {
                    "timestamp": candle_time,
                    "open": max(0, open_price),
                    "high": max(0, high_price),
                    "low": max(0, low_price),
                    "close": max(0, close_price),
                    "volume": max(0, candle_volume)
                }

                candles.append(candle)

            # Reverse to chronological order (oldest first)
            candles.reverse()

            logger.debug(f"Generated {len(candles)} approximate 15m candles from DexScreener")

            return candles

        except Exception as e:
            logger.error(f"Error generating price history: {e}")
            return None

    def get_multiple_tokens(self, token_addresses: List[str]) -> Dict[str, Dict]:
        """
        Get data for multiple tokens.

        Note: DexScreener has a limit on batch requests, so we process
        tokens one at a time to respect rate limits.

        Args:
            token_addresses: List of token addresses

        Returns:
            Dict mapping token_address -> token_data
        """
        results = {}

        for address in token_addresses:
            try:
                data = self.get_token_data(address)
                if data:
                    results[address] = data
            except Exception as e:
                logger.error(f"Error getting data for {address}: {e}")

        logger.info(f"Got data for {len(results)}/{len(token_addresses)} tokens")
        return results

    def search_pairs(self, query: str) -> Optional[List[Dict]]:
        """
        Search for trading pairs by token name or symbol.

        Args:
            query: Search query (token name or symbol)

        Returns:
            List of matching pairs or None on failure
        """
        try:
            url = f"{self.endpoints['search']}?q={query}"
            result = self._make_request(url)

            if result and "pairs" in result:
                pairs = result["pairs"]
                logger.debug(f"Found {len(pairs)} pairs for query: {query}")
                return pairs

            return None

        except Exception as e:
            logger.error(f"Error searching pairs: {e}")
            return None

    def get_buy_sell_pressure(self, token_address: str) -> Optional[Dict]:
        """
        Get buy/sell pressure for a token.

        Args:
            token_address: Token mint address

        Returns:
            {
                "buys_5m": int,
                "sells_5m": int,
                "buy_sell_ratio": float,  # > 1 means buy pressure
                "net_pressure": str  # "BULLISH" or "BEARISH"
            }
            or None on failure
        """
        try:
            token_data = self.get_token_data(token_address)

            if not token_data:
                return None

            buys = token_data.get("buys", 0)
            sells = token_data.get("sells", 0)

            # Calculate ratio (avoid division by zero)
            if sells > 0:
                ratio = buys / sells
            elif buys > 0:
                ratio = float('inf')  # All buys, no sells
            else:
                ratio = 1.0  # No activity

            pressure = {
                "buys_5m": buys,
                "sells_5m": sells,
                "buy_sell_ratio": ratio,
                "net_pressure": "BULLISH" if ratio > 1 else "BEARISH" if ratio < 1 else "NEUTRAL"
            }

            logger.debug(
                f"Pressure for {token_address}: "
                f"{buys} buys / {sells} sells = {ratio:.2f} ({pressure['net_pressure']})"
            )

            return pressure

        except Exception as e:
            logger.error(f"Error getting buy/sell pressure: {e}")
            return None

    def get_trending_tokens(self, limit: int = 50) -> List[str]:
        """
        Get trending Solana tokens from DexScreener.

        Returns latest boosted/trending tokens on Solana.

        Args:
            limit: Maximum tokens to return

        Returns:
            List of token addresses
        """
        try:
            # DexScreener latest pairs endpoint
            url = self.endpoints.get("latest_pairs")
            if not url:
                # Fallback to building URL
                url = f"{self.endpoints.get('base', 'https://api.dexscreener.com/latest')}/dex/pairs/solana"

            logger.debug("Fetching trending tokens from DexScreener...")

            result = self._make_request(url)

            if not result or "pairs" not in result:
                logger.warning("No trending data from DexScreener")
                return []

            pairs = result["pairs"]

            if not pairs:
                logger.warning("No pairs in DexScreener response")
                return []

            # Extract token addresses from pairs
            token_addresses = []

            for pair in pairs[:limit]:
                # Get base token (usually the new/traded token)
                base_token = pair.get("baseToken", {})
                token_address = base_token.get("address")

                if token_address:
                    # Skip SOL pairs (we want the other token)
                    if token_address != "So11111111111111111111111111111111111111112":
                        token_addresses.append(token_address)

            # Remove duplicates
            token_addresses = list(set(token_addresses))

            logger.info(f"✅ DexScreener: {len(token_addresses)} trending tokens")

            return token_addresses[:limit]

        except Exception as e:
            logger.error(f"Error getting trending tokens: {e}")
            return []

    def get_latest_tokens(self, limit: int = 50) -> List[str]:
        """
        Get newest Solana tokens from DexScreener.

        Returns newly created pairs on Solana.

        Args:
            limit: Maximum tokens to return

        Returns:
            List of token addresses
        """
        try:
            # Get latest pairs endpoint
            url = self.endpoints.get("latest_pairs")
            if not url:
                # Fallback to building URL
                url = f"{self.endpoints.get('base', 'https://api.dexscreener.com/latest')}/dex/pairs/solana"

            logger.debug("Fetching latest tokens from DexScreener...")

            result = self._make_request(url)

            if not result or "pairs" not in result:
                logger.warning("No latest data from DexScreener")
                return []

            pairs = result["pairs"]

            # Extract and sort by creation time
            token_pairs = []

            for pair in pairs:
                base_token = pair.get("baseToken", {})
                token_address = base_token.get("address")

                # Get pair creation time
                pair_created_at = pair.get("pairCreatedAt", 0)

                if token_address and token_address != "So11111111111111111111111111111111111111112":
                    token_pairs.append({
                        "address": token_address,
                        "created_at": pair_created_at
                    })

            # Sort by creation time (newest first)
            token_pairs.sort(key=lambda x: x["created_at"], reverse=True)

            # Extract addresses
            token_addresses = [t["address"] for t in token_pairs[:limit]]

            # Remove duplicates while preserving order
            seen = set()
            unique_addresses = []
            for addr in token_addresses:
                if addr not in seen:
                    seen.add(addr)
                    unique_addresses.append(addr)

            logger.info(f"✅ DexScreener (latest): {len(unique_addresses)} new tokens")

            return unique_addresses

        except Exception as e:
            logger.error(f"Error getting latest tokens: {e}")
            return []

    async def get_trending_tokens_async(self, limit: int = 50) -> List[str]:
        """
        Async wrapper for get_trending_tokens.

        For compatibility with main bot loop.
        """
        return self.get_trending_tokens(limit)


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    client = DexScreenerClient()

    # Example token (BONK)
    BONK_ADDRESS = "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263"

    # Test 1: Get token data
    data = client.get_token_data(BONK_ADDRESS)
    print(f"Token data: {data}")

    # Test 2: Get buy/sell pressure
    pressure = client.get_buy_sell_pressure(BONK_ADDRESS)
    print(f"Buy/Sell pressure: {pressure}")

    # Test 3: Search pairs
    pairs = client.search_pairs("BONK")
    print(f"Search results: {len(pairs) if pairs else 0} pairs")

    # Test 4: Get price history
    candles = client.get_price_history(BONK_ADDRESS)
    print(f"Price history: {candles}")
