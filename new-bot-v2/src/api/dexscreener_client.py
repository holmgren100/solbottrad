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

            # Extract data
            token_data = {
                "address": token_address,
                "price": float(main_pair.get("priceUsd", 0)),
                "volume_5m": float(main_pair.get("volume", {}).get("m5", 0)),
                "volume_1h": float(main_pair.get("volume", {}).get("h1", 0)),
                "volume_24h": float(main_pair.get("volume", {}).get("h24", 0)),
                "liquidity": float(main_pair.get("liquidity", {}).get("usd", 0)),
                "buys": int(main_pair.get("txns", {}).get("m5", {}).get("buys", 0)),
                "sells": int(main_pair.get("txns", {}).get("m5", {}).get("sells", 0)),
                "price_change_5m": float(main_pair.get("priceChange", {}).get("m5", 0)),
                "price_change_1h": float(main_pair.get("priceChange", {}).get("h1", 0)),
                "price_change_24h": float(main_pair.get("priceChange", {}).get("h24", 0)),
                "pair_address": main_pair.get("pairAddress", ""),
                "dex": main_pair.get("dexId", ""),
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
        timeframe: str = "1m",
        limit: int = 100
    ) -> Optional[List[Dict]]:
        """
        Get historical price candles.

        Note: DexScreener doesn't provide a direct candle endpoint in their free API.
        We simulate this by getting pair data and deriving approximate candles from
        price changes. For production, you'd want to:
        1. Use a paid API with candle data
        2. Build candles from transaction data
        3. Use a WebSocket for real-time candle updates

        Args:
            token_address: Token mint address
            timeframe: Candle timeframe ("1m", "5m", "15m", "1h")
            limit: Number of candles to return

        Returns:
            List of candles:
            [
                {
                    "timestamp": int,
                    "open": float,
                    "high": float,
                    "low": float,
                    "close": float,
                    "volume": float
                },
                ...
            ]
            or None on failure
        """
        try:
            # Get current token data
            token_data = self.get_token_data(token_address)

            if not token_data:
                return None

            # For now, create a single "candle" from current data
            # In production, you'd implement proper candle collection
            current_price = token_data["price"]
            current_volume = token_data.get("volume_5m", 0)

            # Estimate OHLC from price changes
            price_change_5m = token_data.get("price_change_5m", 0)
            price_5m_ago = current_price / (1 + price_change_5m / 100)

            candle = {
                "timestamp": int(time.time()),
                "open": price_5m_ago,
                "high": max(current_price, price_5m_ago),
                "low": min(current_price, price_5m_ago),
                "close": current_price,
                "volume": current_volume
            }

            logger.debug(f"Created approximate candle for {token_address}")

            # Return list with single candle (placeholder)
            # TODO: Implement proper candle collection with historical data
            return [candle]

        except Exception as e:
            logger.error(f"Error getting price history: {e}")
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
