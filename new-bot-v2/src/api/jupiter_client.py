"""
Jupiter Client - Token Discovery, Prices, and Swaps

Uses Jupiter FREE API for:
- Token discovery (trending tokens)
- Real-time prices
- Swap quotes
- Swap execution

Limit: Unlimited (FREE!)
Cost: FREE
"""

import requests
import logging
from typing import Dict, List, Optional
import time

from config.apis import (
    JUPITER_ENDPOINTS,
    JUPITER_API_KEY,
    API_TIMEOUT_SECONDS,
    API_MAX_RETRIES,
    API_RETRY_DELAY,
    DEFAULT_HEADERS
)

logger = logging.getLogger(__name__)


class JupiterClient:
    """
    Client for Jupiter API.

    Primary use: Token discovery, price data, swap execution
    """

    def __init__(self):
        """Initialize Jupiter client."""
        self.endpoints = JUPITER_ENDPOINTS
        self.timeout = API_TIMEOUT_SECONDS
        self.max_retries = API_MAX_RETRIES
        self.retry_delay = API_RETRY_DELAY
        self.api_key = JUPITER_API_KEY

        # Check if API key is configured
        self.has_api_key = bool(self.api_key)
        if not self.has_api_key:
            logger.warning(
                "Jupiter API key not configured. Token discovery will be disabled. "
                "Get free API key at https://jup.ag and set JUPITER_API_KEY in .env"
            )

    def _make_request(self, url: str, params: Optional[Dict] = None, use_api_key: bool = False) -> Optional[Dict]:
        """
        Make HTTP request to Jupiter with retries.

        Args:
            url: API endpoint URL
            params: Query parameters
            use_api_key: Whether to include API key header (for Token API V2)

        Returns:
            Response data or None on failure
        """
        for attempt in range(self.max_retries):
            try:
                headers = DEFAULT_HEADERS.copy()

                # Add API key if needed (Token API V2)
                if use_api_key and self.has_api_key:
                    headers['x-api-key'] = self.api_key

                response = requests.get(
                    url,
                    params=params,
                    headers=headers,
                    timeout=self.timeout
                )

                if response.status_code == 200:
                    return response.json()

                logger.warning(
                    f"Jupiter request failed (attempt {attempt + 1}/{self.max_retries}): "
                    f"Status {response.status_code}"
                )

            except requests.exceptions.Timeout:
                logger.warning(f"Jupiter request timeout (attempt {attempt + 1}/{self.max_retries})")
            except Exception as e:
                logger.error(f"Jupiter request error: {e}")

            if attempt < self.max_retries - 1:
                time.sleep(self.retry_delay * (attempt + 1))

        logger.error(f"Jupiter request failed after {self.max_retries} attempts")
        return None

    def _make_post_request(self, url: str, data: Dict) -> Optional[Dict]:
        """
        Make HTTP POST request to Jupiter with retries.

        Args:
            url: API endpoint URL
            data: Request body data

        Returns:
            Response data or None on failure
        """
        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    url,
                    json=data,
                    headers=DEFAULT_HEADERS,
                    timeout=self.timeout
                )

                if response.status_code == 200:
                    return response.json()

                logger.warning(
                    f"Jupiter POST request failed (attempt {attempt + 1}/{self.max_retries}): "
                    f"Status {response.status_code}"
                )

            except requests.exceptions.Timeout:
                logger.warning(f"Jupiter POST timeout (attempt {attempt + 1}/{self.max_retries})")
            except Exception as e:
                logger.error(f"Jupiter POST error: {e}")

            if attempt < self.max_retries - 1:
                time.sleep(self.retry_delay * (attempt + 1))

        logger.error(f"Jupiter POST request failed after {self.max_retries} attempts")
        return None

    def get_token_price(self, token_address: str) -> Optional[Dict]:
        """
        Get current price for a token.

        Args:
            token_address: Token mint address

        Returns:
            {
                "id": str,  # Token address
                "price": float,  # Price in USD
                "timestamp": int
            }
            or None on failure
        """
        try:
            params = {"ids": token_address}
            result = self._make_request(self.endpoints["price"], params)

            if result and "data" in result:
                token_data = result["data"].get(token_address)
                if token_data:
                    price_data = {
                        "id": token_address,
                        "price": float(token_data.get("price", 0)),
                        "timestamp": int(time.time())
                    }
                    logger.debug(f"Price for {token_address}: ${price_data['price']}")
                    return price_data

            logger.warning(f"No price data for {token_address}")
            return None

        except Exception as e:
            logger.error(f"Error getting token price: {e}")
            return None

    def get_multiple_prices(self, token_addresses: List[str]) -> Dict[str, float]:
        """
        Get prices for multiple tokens in one request.

        Args:
            token_addresses: List of token mint addresses

        Returns:
            Dict mapping token_address -> price (USD)
        """
        try:
            # Jupiter price API supports comma-separated IDs
            ids = ",".join(token_addresses)
            params = {"ids": ids}
            result = self._make_request(self.endpoints["price"], params)

            prices = {}
            if result and "data" in result:
                for address in token_addresses:
                    token_data = result["data"].get(address)
                    if token_data:
                        prices[address] = float(token_data.get("price", 0))

            logger.debug(f"Got prices for {len(prices)}/{len(token_addresses)} tokens")
            return prices

        except Exception as e:
            logger.error(f"Error getting multiple prices: {e}")
            return {}

    def get_quote(
        self,
        input_mint: str,
        output_mint: str,
        amount: int,
        slippage_bps: int = 50
    ) -> Optional[Dict]:
        """
        Get swap quote from Jupiter.

        Args:
            input_mint: Input token address
            output_mint: Output token address
            amount: Amount in smallest unit (e.g., lamports)
            slippage_bps: Slippage in basis points (50 = 0.5%)

        Returns:
            {
                "inputMint": str,
                "outputMint": str,
                "inAmount": int,
                "outAmount": int,
                "priceImpactPct": float,
                "routePlan": List[...],
                ...
            }
            or None on failure
        """
        try:
            params = {
                "inputMint": input_mint,
                "outputMint": output_mint,
                "amount": str(amount),
                "slippageBps": slippage_bps,
                "onlyDirectRoutes": False  # Allow multi-hop routes
            }

            result = self._make_request(self.endpoints["quote"], params)

            if result and "data" in result and len(result["data"]) > 0:
                # Get best quote (first in list)
                quote = result["data"][0]
                logger.debug(
                    f"Quote: {amount} {input_mint[:8]}... -> "
                    f"{quote.get('outAmount')} {output_mint[:8]}..."
                )
                return quote

            logger.warning(f"No quote available for {input_mint} -> {output_mint}")
            return None

        except Exception as e:
            logger.error(f"Error getting quote: {e}")
            return None

    def get_swap_transaction(
        self,
        quote: Dict,
        user_public_key: str,
        wrap_unwrap_sol: bool = True
    ) -> Optional[Dict]:
        """
        Get serialized transaction for a swap.

        Args:
            quote: Quote from get_quote()
            user_public_key: User's wallet public key
            wrap_unwrap_sol: Auto wrap/unwrap SOL

        Returns:
            {
                "swapTransaction": str,  # Base64 encoded transaction
                "lastValidBlockHeight": int,
                ...
            }
            or None on failure
        """
        try:
            data = {
                "quoteResponse": quote,
                "userPublicKey": user_public_key,
                "wrapAndUnwrapSol": wrap_unwrap_sol,
                "computeUnitPriceMicroLamports": "auto"  # Auto set priority fee
            }

            result = self._make_post_request(self.endpoints["swap"], data)

            if result and "swapTransaction" in result:
                logger.debug("Got swap transaction")
                return result

            logger.warning("Failed to get swap transaction")
            return None

        except Exception as e:
            logger.error(f"Error getting swap transaction: {e}")
            return None


    def find_token_by_symbol(self, symbol: str) -> Optional[str]:
        """
        Find token address by symbol using search endpoint.

        REQUIRES API KEY! Set JUPITER_API_KEY in .env (free at https://jup.ag)

        Args:
            symbol: Token symbol (e.g., "BONK")

        Returns:
            Token mint address or None if not found
        """
        if not self.has_api_key:
            logger.debug("Jupiter API key not configured - cannot search by symbol")
            return None

        try:
            # Use Token API V2 search endpoint
            url = self.endpoints["search"]
            params = {"query": symbol}

            result = self._make_request(url, params=params, use_api_key=True)

            if not result:
                logger.warning(f"Token not found: {symbol}")
                return None

            # Extract first matching token
            tokens_data = result.get("data", result)

            if isinstance(tokens_data, list) and len(tokens_data) > 0:
                token = tokens_data[0]
                mint = token.get("mint") or token.get("address")
                if mint:
                    logger.debug(f"Found token {symbol}: {mint}")
                    return mint

            logger.warning(f"Token not found: {symbol}")
            return None

        except Exception as e:
            logger.error(f"Error finding token by symbol: {e}")
            return None

    def get_token_info_batch(self, addresses: List[str]) -> Dict[str, Dict]:
        """
        Get information for multiple tokens.

        Args:
            addresses: List of token addresses

        Returns:
            Dict mapping address -> {price, volume, liquidity, ...}
        """
        try:
            # Get prices
            prices = self.get_multiple_prices(addresses)

            # Build result
            token_info = {}
            for address in addresses:
                price = prices.get(address, 0)
                token_info[address] = {
                    "address": address,
                    "price": price,
                    "timestamp": int(time.time())
                }

            return token_info

        except Exception as e:
            logger.error(f"Error getting token info batch: {e}")
            return {}

    def get_all_tokens(self, limit: int = 100) -> List[str]:
        """
        Get verified tokens from Jupiter Token API V2.

        REQUIRES API KEY! Set JUPITER_API_KEY in .env (free at https://jup.ag)

        Args:
            limit: Maximum tokens to return

        Returns:
            List of token addresses (empty if no API key)
        """
        if not self.has_api_key:
            logger.debug("Jupiter API key not configured - skipping")
            return []

        try:
            # Use Token API V2: /tag?query=verified
            url = self.endpoints["verified"]
            logger.debug("Fetching verified tokens from Jupiter API V2...")

            result = self._make_request(url, use_api_key=True)

            if not result:
                logger.warning("No response from Jupiter Token API V2")
                return []

            # Extract mint addresses from response
            token_addresses = []

            # Response format: { "data": [{"mint": "..."}, ...] }
            tokens_data = result.get("data", result)  # Handle different response formats

            if isinstance(tokens_data, list):
                for token in tokens_data[:limit]:
                    if isinstance(token, dict):
                        # Try different field names
                        mint = token.get("mint") or token.get("address")
                        if mint:
                            token_addresses.append(mint)

            logger.info(f"✅ Jupiter (verified): {len(token_addresses)} tokens")
            return token_addresses

        except Exception as e:
            logger.error(f"Error getting Jupiter token list: {e}")
            return []

    async def get_trending_tokens(self, limit: int = 50) -> List[str]:
        """
        Get trending tokens from Jupiter Token API V2.

        Uses toptrending endpoint with 5-minute interval.
        REQUIRES API KEY! Set JUPITER_API_KEY in .env (free at https://jup.ag)

        Args:
            limit: Maximum tokens to return

        Returns:
            List of token addresses (empty if no API key)
        """
        if not self.has_api_key:
            logger.debug("Jupiter API key not configured - skipping")
            return []

        try:
            # Use Token API V2: /toptrending/5m
            url = self.endpoints["trending"]
            params = {"limit": limit} if limit != 50 else None  # 50 is default

            logger.debug("Fetching trending tokens from Jupiter API V2...")

            result = self._make_request(url, params=params, use_api_key=True)

            if not result:
                logger.warning("No response from Jupiter trending API")
                return []

            # Extract mint addresses
            token_addresses = []

            # Response format may vary - handle both list and dict
            tokens_data = result.get("data", result)

            if isinstance(tokens_data, list):
                for token in tokens_data[:limit]:
                    if isinstance(token, dict):
                        mint = token.get("mint") or token.get("address")
                        if mint:
                            token_addresses.append(mint)

            logger.info(f"✅ Jupiter (trending): {len(token_addresses)} tokens")
            return token_addresses

        except Exception as e:
            logger.error(f"Error getting trending tokens: {e}")
            return []


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    client = JupiterClient()

    # Test 1: Get token price
    SOL_MINT = "So11111111111111111111111111111111111111112"
    price = client.get_token_price(SOL_MINT)
    print(f"SOL Price: {price}")

    # Test 2: Get multiple prices
    USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
    prices = client.get_multiple_prices([SOL_MINT, USDC_MINT])
    print(f"Multiple prices: {prices}")

    # Test 3: Find token by symbol
    bonk = client.find_token_by_symbol("BONK")
    print(f"BONK token: {bonk}")

    # Test 4: Get quote (1 SOL -> USDC)
    quote = client.get_quote(
        input_mint=SOL_MINT,
        output_mint=USDC_MINT,
        amount=1_000_000_000,  # 1 SOL in lamports
        slippage_bps=50
    )
    print(f"Swap quote: {quote}")
