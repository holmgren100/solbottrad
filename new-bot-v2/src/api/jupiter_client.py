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

    def _make_request(self, url: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """
        Make HTTP request to Jupiter with retries.

        Args:
            url: API endpoint URL
            params: Query parameters

        Returns:
            Response data or None on failure
        """
        for attempt in range(self.max_retries):
            try:
                response = requests.get(
                    url,
                    params=params,
                    headers=DEFAULT_HEADERS,
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

    def get_all_tokens(self, strict_only: bool = False) -> Optional[List[Dict]]:
        """
        Get list of all tokens available on Jupiter.

        Args:
            strict_only: If True, only return verified tokens

        Returns:
            List of token info dicts or None on failure
        """
        try:
            url = self.endpoints["strict_tokens"] if strict_only else self.endpoints["tokens"]
            result = self._make_request(url)

            if result and isinstance(result, list):
                logger.info(f"Loaded {len(result)} tokens from Jupiter")
                return result

            logger.warning("Failed to load token list")
            return None

        except Exception as e:
            logger.error(f"Error getting token list: {e}")
            return None

    def find_token_by_symbol(self, symbol: str) -> Optional[Dict]:
        """
        Find token by symbol.

        Args:
            symbol: Token symbol (e.g., "BONK")

        Returns:
            Token info dict or None if not found
        """
        try:
            tokens = self.get_all_tokens(strict_only=True)

            if not tokens:
                return None

            # Search for matching symbol (case-insensitive)
            symbol_upper = symbol.upper()
            for token in tokens:
                if token.get("symbol", "").upper() == symbol_upper:
                    logger.debug(f"Found token: {token}")
                    return token

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
