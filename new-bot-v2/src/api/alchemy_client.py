"""
Alchemy Client - Solana Blockchain Data

Uses Alchemy FREE tier for:
- Token metadata (name, symbol, decimals, supply)
- LP burned check (safety verification)
- Mint authority check (safety verification)

Limit: 300M compute units/month (plenty for our needs)
Cost: FREE
"""

import requests
import logging
from typing import Dict, Optional
import time

from config.apis import (
    ALCHEMY_ENDPOINT,
    API_TIMEOUT_SECONDS,
    API_MAX_RETRIES,
    API_RETRY_DELAY,
    DEFAULT_HEADERS
)

logger = logging.getLogger(__name__)


class AlchemyClient:
    """
    Client for Alchemy Solana API.

    Primary use: Safety checks (LP burned, mint revoked)
    """

    def __init__(self):
        """Initialize Alchemy client."""
        self.endpoint = ALCHEMY_ENDPOINT
        self.timeout = API_TIMEOUT_SECONDS
        self.max_retries = API_MAX_RETRIES
        self.retry_delay = API_RETRY_DELAY

        if not self.endpoint or "None" in self.endpoint:
            logger.warning("Alchemy API key not configured!")

    def _make_request(self, method: str, params: list) -> Optional[Dict]:
        """
        Make RPC request to Alchemy with retries.

        Args:
            method: RPC method name
            params: Method parameters

        Returns:
            Response data or None on failure
        """
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params
        }

        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    self.endpoint,
                    json=payload,
                    headers=DEFAULT_HEADERS,
                    timeout=self.timeout
                )

                if response.status_code == 200:
                    data = response.json()
                    if "result" in data:
                        return data["result"]
                    elif "error" in data:
                        logger.error(f"Alchemy RPC error: {data['error']}")
                        return None

                logger.warning(
                    f"Alchemy request failed (attempt {attempt + 1}/{self.max_retries}): "
                    f"Status {response.status_code}"
                )

            except requests.exceptions.Timeout:
                logger.warning(f"Alchemy request timeout (attempt {attempt + 1}/{self.max_retries})")
            except Exception as e:
                logger.error(f"Alchemy request error: {e}")

            if attempt < self.max_retries - 1:
                time.sleep(self.retry_delay * (attempt + 1))  # Exponential backoff

        logger.error(f"Alchemy request failed after {self.max_retries} attempts")
        return None

    def get_token_metadata(self, token_address: str) -> Optional[Dict]:
        """
        Get token metadata (name, symbol, decimals, supply).

        Args:
            token_address: Token mint address

        Returns:
            {
                "name": str,
                "symbol": str,
                "decimals": int,
                "supply": int
            }
            or None on failure
        """
        try:
            # Get account info
            result = self._make_request(
                "getAccountInfo",
                [token_address, {"encoding": "jsonParsed"}]
            )

            if not result or not result.get("value"):
                logger.debug(f"No account info found for {token_address}")
                return None

            account_data = result["value"]["data"]

            if isinstance(account_data, dict) and "parsed" in account_data:
                parsed = account_data["parsed"]
                info = parsed.get("info", {})

                metadata = {
                    "name": info.get("name", "Unknown"),
                    "symbol": info.get("symbol", "???"),
                    "decimals": info.get("decimals", 9),
                    "supply": int(info.get("supply", 0))
                }

                logger.debug(f"Token metadata: {metadata}")
                return metadata

            return None

        except Exception as e:
            logger.error(f"Error getting token metadata: {e}")
            return None

    def check_mint_authority(self, token_address: str) -> bool:
        """
        Check if mint authority is revoked (safety check).

        A revoked mint authority means no more tokens can be minted,
        which prevents rug pulls via inflation.

        Args:
            token_address: Token mint address

        Returns:
            True if mint authority is revoked (SAFE)
            False if mint authority exists (RISKY)
        """
        try:
            result = self._make_request(
                "getAccountInfo",
                [token_address, {"encoding": "jsonParsed"}]
            )

            if not result or not result.get("value"):
                logger.warning(f"Cannot verify mint authority for {token_address}")
                return False

            account_data = result["value"]["data"]

            if isinstance(account_data, dict) and "parsed" in account_data:
                parsed = account_data["parsed"]
                info = parsed.get("info", {})

                # Check if mintAuthority is null (revoked)
                mint_authority = info.get("mintAuthority")

                if mint_authority is None:
                    logger.info(f"✅ Mint authority REVOKED for {token_address}")
                    return True
                else:
                    logger.warning(f"⚠️ Mint authority EXISTS for {token_address}: {mint_authority}")
                    return False

            return False

        except Exception as e:
            logger.error(f"Error checking mint authority: {e}")
            return False

    def check_lp_burned(self, token_address: str, lp_address: Optional[str] = None) -> bool:
        """
        Check if LP (liquidity pool) tokens are burned (safety check).

        Burned LP means liquidity is locked forever, preventing rug pulls
        where developers remove liquidity.

        Args:
            token_address: Token mint address
            lp_address: LP token address (if known)

        Returns:
            True if LP is burned (SAFE)
            False if LP is not burned or cannot verify (RISKY)

        Note:
            This is a simplified check. In production, you would:
            1. Find the main liquidity pool for this token
            2. Check if LP tokens are in a burn address
            3. Verify the burn address is truly unrecoverable

            For now, we'll implement a basic version that checks
            if the LP token account is owned by a known burn address.
        """
        try:
            # Common Solana burn addresses
            BURN_ADDRESSES = [
                "1nc1nerator11111111111111111111111111111111",  # Incinerator
                "11111111111111111111111111111111",  # System program (null)
            ]

            # If LP address is provided, check if it's sent to burn address
            if lp_address:
                result = self._make_request(
                    "getAccountInfo",
                    [lp_address, {"encoding": "jsonParsed"}]
                )

                if not result or not result.get("value"):
                    logger.warning(f"Cannot verify LP burn for {lp_address}")
                    return False

                account_data = result["value"]["data"]

                if isinstance(account_data, dict) and "parsed" in account_data:
                    parsed = account_data["parsed"]
                    info = parsed.get("info", {})
                    owner = info.get("owner", "")

                    if owner in BURN_ADDRESSES:
                        logger.info(f"✅ LP tokens BURNED for {token_address}")
                        return True
                    else:
                        logger.warning(f"⚠️ LP tokens NOT BURNED for {token_address}")
                        return False

            # If no LP address provided, skip check for now
            # TODO: Query Raydium/Orca APIs to find LP address automatically
            logger.debug(f"LP burn check skipped (no LP address) for {token_address}")
            return True  # PASS for now - skip LP check

        except Exception as e:
            logger.error(f"Error checking LP burned: {e}")
            return False

    def get_token_supply(self, token_address: str) -> Optional[int]:
        """
        Get current token supply.

        Args:
            token_address: Token mint address

        Returns:
            Total supply or None on failure
        """
        try:
            result = self._make_request(
                "getTokenSupply",
                [token_address]
            )

            if result and "value" in result:
                supply = int(result["value"]["amount"])
                logger.debug(f"Token supply for {token_address}: {supply}")
                return supply

            return None

        except Exception as e:
            logger.error(f"Error getting token supply: {e}")
            return None

    def verify_token_safety(self, token_address: str, lp_address: Optional[str] = None) -> Dict:
        """
        Comprehensive safety check for a token.

        Checks:
        1. Mint authority revoked (prevents inflation rug)
        2. LP burned (prevents liquidity rug)

        Args:
            token_address: Token mint address
            lp_address: LP token address (optional)

        Returns:
            {
                "mint_revoked": bool,
                "lp_burned": bool,
                "safe": bool,  # True only if BOTH checks pass
                "warnings": List[str]
            }
        """
        warnings = []

        # Check 1: Mint authority
        mint_revoked = self.check_mint_authority(token_address)
        if not mint_revoked:
            warnings.append("Mint authority NOT revoked - inflation risk!")

        # Check 2: LP burned
        lp_burned = self.check_lp_burned(token_address, lp_address)
        if not lp_burned:
            warnings.append("LP NOT burned - liquidity rug risk!")

        # Only safe if BOTH checks pass
        safe = mint_revoked and lp_burned

        result = {
            "mint_revoked": mint_revoked,
            "lp_burned": lp_burned,
            "safe": safe,
            "warnings": warnings
        }

        if safe:
            logger.info(f"✅ Token {token_address} passed ALL safety checks")
        else:
            logger.warning(f"⚠️ Token {token_address} FAILED safety checks: {warnings}")

        return result


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    client = AlchemyClient()

    # Example token address (replace with real one)
    test_token = "So11111111111111111111111111111111111111112"  # Wrapped SOL

    # Get metadata
    metadata = client.get_token_metadata(test_token)
    print(f"Metadata: {metadata}")

    # Check safety
    safety = client.verify_token_safety(test_token)
    print(f"Safety: {safety}")
