"""
Token Data Gatherer - REAL DATA ONLY!

Gathers data from DexScreener - NO FAKE CANDLES!
Returns unified data dict with REAL market data.
"""

import logging
from typing import Dict, Optional

from src.api.alchemy_client import AlchemyClient
from src.api.dexscreener_client import DexScreenerClient

logger = logging.getLogger(__name__)


class TokenDataGatherer:
    """
    Gathers token data from DexScreener - REAL DATA ONLY!
    NO FAKE CANDLES, NO APPROXIMATIONS!
    """

    def __init__(self):
        """Initialize data gatherer."""
        self.alchemy_client = AlchemyClient()
        self.dexscreener_client = DexScreenerClient()

        logger.info("Token Data Gatherer initialized - REAL DATA ONLY!")

    def gather_complete_data(self, token_address: str) -> Optional[Dict]:
        """
        Gather complete token data from DexScreener.

        Args:
            token_address: Token mint address

        Returns:
            Complete token data dict or None if critical data missing
        """
        try:
            logger.debug(f"Gathering data for {token_address[:8]}...")

            # Get token data from DexScreener
            dex_data = self.dexscreener_client.get_token_data(token_address)

            if not dex_data:
                logger.warning(f"No DexScreener data for {token_address[:8]}")
                return None

            # Extract all REAL data (no fabrication!)
            data = {
                "address": token_address,
                "symbol": dex_data.get("symbol", "UNKNOWN"),
                "name": dex_data.get("name", "UNKNOWN"),
                "price": dex_data.get("price", 0),
                "liquidity": dex_data.get("liquidity", 0),
                "volume_5m": dex_data.get("volume_5m", 0),
                "volume_1h": dex_data.get("volume_1h", 0),
                "volume_24h": dex_data.get("volume_24h", 0),
                "price_change_5m": dex_data.get("price_change_5m", 0),
                "price_change_1h": dex_data.get("price_change_1h", 0),
                "price_change_24h": dex_data.get("price_change_24h", 0),
                "buys_5m": dex_data.get("buys", 0),
                "sells_5m": dex_data.get("sells", 0),
                "buys_1h": dex_data.get("buys_1h", 0),
                "sells_1h": dex_data.get("sells_1h", 0),
                "market_cap_usd": dex_data.get("market_cap_usd", 0),
                "lp_burned": False,  # Will check below
                "mint_revoked": False,  # Will check below
            }

            # Get safety checks from Alchemy
            try:
                lp_burned = self.alchemy_client.check_lp_burned(token_address)
                mint_revoked = self.alchemy_client.check_mint_authority(token_address)

                data["lp_burned"] = lp_burned
                data["mint_revoked"] = mint_revoked

                logger.debug(f"Safety: LP={lp_burned}, Mint={mint_revoked}")

            except Exception as e:
                logger.warning(f"Alchemy safety check failed: {e}")

            logger.info(
                f"✅ Gathered data for {data['symbol']}: "
                f"${data['price']:.8f}, Liq=${data['liquidity']:.0f}, "
                f"Vol5m=${data['volume_5m']:.0f}"
            )

            return data

        except Exception as e:
            logger.error(f"Error gathering token data: {e}")
            return None

    def gather_price_update(self, token_address: str) -> Optional[Dict]:
        """
        Quick price update for existing position.

        Args:
            token_address: Token mint address

        Returns:
            Price update dict or None
        """
        try:
            dex_data = self.dexscreener_client.get_token_data(token_address)

            if not dex_data:
                return None

            return {
                "address": token_address,
                "price": dex_data.get("price", 0),
                "volume_5m": dex_data.get("volume_5m", 0),
                "volume_1h": dex_data.get("volume_1h", 0),
            }

        except Exception as e:
            logger.error(f"Error getting price update: {e}")
            return None

    def verify_safety(self, token_address: str) -> Dict:
        """
        Quick safety verification (LP + Mint).

        Args:
            token_address: Token mint address

        Returns:
            {"passed": bool, "lp_burned": bool, "mint_revoked": bool}
        """
        try:
            lp_burned = self.alchemy_client.check_lp_burned(token_address)
            mint_revoked = self.alchemy_client.check_mint_authority(token_address)

            passed = lp_burned and mint_revoked

            logger.debug(f"Safety check: LP={lp_burned}, Mint={mint_revoked}, Pass={passed}")

            return {
                "passed": passed,
                "lp_burned": lp_burned,
                "mint_revoked": mint_revoked
            }

        except Exception as e:
            logger.error(f"Safety verification failed: {e}")
            return {
                "passed": False,
                "lp_burned": False,
                "mint_revoked": False
            }
