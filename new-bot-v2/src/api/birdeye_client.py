"""
Birdeye Client - Token Discovery & Market Data

Uses Birdeye FREE API for:
- Token discovery (trending tokens)
- Real-time prices
- Security checks
- OHLCV data

Limit: 100 requests/min (FREE!)
Cost: FREE
"""

import requests
import logging
from typing import Dict, List, Optional
import time

from config.apis import (
    BIRDEYE_ENDPOINTS,
    BIRDEYE_API_KEY,
    API_TIMEOUT_SECONDS,
    API_MAX_RETRIES,
    API_RETRY_DELAY
)

logger = logging.getLogger(__name__)


class BirdeyeClient:
    """
    Client for Birdeye API.

    Primary use: Token discovery (trending), prices, security checks
    """

    def __init__(self):
        """Initialize Birdeye client."""
        self.endpoints = BIRDEYE_ENDPOINTS
        self.timeout = API_TIMEOUT_SECONDS
        self.max_retries = API_MAX_RETRIES
        self.retry_delay = API_RETRY_DELAY
        self.api_key = BIRDEYE_API_KEY

        if not self.api_key:
            logger.warning("Birdeye API key not configured - token discovery will be limited")

    def _make_request(self, url: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """
        Make HTTP request to Birdeye with retries.

        Args:
            url: API endpoint URL
            params: Query parameters

        Returns:
            Response data or None on failure
        """
        if not self.api_key:
            logger.debug("Birdeye API key not configured - skipping")
            return None

        for attempt in range(self.max_retries):
            try:
                headers = {
                    "X-API-KEY": self.api_key,
                    "x-chain": "solana",  # Required: specify blockchain network
                    "Content-Type": "application/json"
                }

                response = requests.get(
                    url,
                    params=params,
                    headers=headers,
                    timeout=self.timeout
                )

                if response.status_code == 200:
                    return response.json()

                logger.warning(
                    f"Birdeye request failed (attempt {attempt + 1}/{self.max_retries}): "
                    f"Status {response.status_code}"
                )

            except requests.exceptions.Timeout:
                logger.warning(f"Birdeye request timeout (attempt {attempt + 1}/{self.max_retries})")
            except Exception as e:
                logger.error(f"Birdeye request error: {e}")

            if attempt < self.max_retries - 1:
                time.sleep(self.retry_delay * (attempt + 1))

        logger.error(f"Birdeye request failed after {self.max_retries} attempts")
        return None

    async def get_trending_tokens(self, limit: int = 50) -> List[str]:
        """
        Get trending Solana tokens from Birdeye.

        Args:
            limit: Maximum tokens to return

        Returns:
            List of token addresses
        """
        if not self.api_key:
            logger.debug("Birdeye API key not configured - skipping")
            return []

        try:
            params = {
                "chain": "solana",
                "sort_by": "rank",
                "sort_type": "asc",
                "offset": 0,
                "limit": limit
            }

            logger.debug("Fetching trending tokens from Birdeye...")

            result = self._make_request(self.endpoints["trending"], params=params)

            if not result or "data" not in result:
                logger.warning("No trending data from Birdeye")
                return []

            # Extract token addresses
            token_addresses = []
            tokens_data = result.get("data", {}).get("items", [])

            for token in tokens_data:
                address = token.get("address")
                if address:
                    token_addresses.append(address)

            logger.info(f"✅ Birdeye (trending): {len(token_addresses)} tokens")
            return token_addresses

        except Exception as e:
            logger.error(f"Error getting trending tokens from Birdeye: {e}")
            return []

    def get_token_price(self, token_address: str) -> Optional[float]:
        """
        Get current price for a token.

        Args:
            token_address: Token mint address

        Returns:
            Price in USD or None on failure
        """
        if not self.api_key:
            return None

        try:
            params = {
                "address": token_address,
                "chain": "solana"
            }

            result = self._make_request(self.endpoints["price"], params=params)

            if result and "data" in result:
                price = result["data"].get("value")
                if price:
                    logger.debug(f"Birdeye price for {token_address}: ${price}")
                    return float(price)

            logger.warning(f"No price data from Birdeye for {token_address}")
            return None

        except Exception as e:
            logger.error(f"Error getting token price from Birdeye: {e}")
            return None

    def get_token_security(self, token_address: str) -> Optional[Dict]:
        """
        Get security info for a token.

        Args:
            token_address: Token mint address

        Returns:
            Security data dict or None on failure
        """
        if not self.api_key:
            return None

        try:
            params = {
                "address": token_address
            }

            result = self._make_request(self.endpoints["token_security"], params=params)

            if result and "data" in result:
                logger.debug(f"Got security data for {token_address}")
                return result["data"]

            logger.warning(f"No security data from Birdeye for {token_address}")
            return None

        except Exception as e:
            logger.error(f"Error getting security data from Birdeye: {e}")
            return None


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    client = BirdeyeClient()

    # Test: Get trending tokens
    import asyncio
    trending = asyncio.run(client.get_trending_tokens(10))
    print(f"Trending tokens: {trending}")
