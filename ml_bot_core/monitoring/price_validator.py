"""
🔒 PROTECTED - ML Bot 2 Price Validation
Based on ML Bot 2 (71.7% win rate, 9.02x profit factor)

DO NOT MODIFY - This is proven core logic!

This module provides dual-source price validation that prevents:
- Bad API data causing fake losses
- Suspicious price drops (>80%)
- Invalid price data (None, NaN, Infinity, zero)

Extracted from: ml2/src/main.py lines 609-760
"""

import logging
import math
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class PriceValidator:
    """
    🔒 PROTECTED - Dual-source price validation from ML Bot 2

    Validates prices from multiple sources (DexScreener + Jupiter) and rejects
    suspicious data that could cause fake losses.

    WHY IT WORKS:
    - Prevents bad data from causing fake 100% losses
    - Cross-validates prices from 2 sources
    - Rejects suspicious drops >80%
    - Saved countless trades from bad API responses
    """

    def __init__(self, dexscreener_client=None, jupiter_client=None):
        """
        Initialize price validator with data sources.

        Args:
            dexscreener_client: DexScreener API client
            jupiter_client: Jupiter API client
        """
        self.dexscreener = dexscreener_client
        self.jupiter = jupiter_client

    async def get_validated_price(
        self,
        token_address: str,
        entry_price: Optional[float] = None
    ) -> Tuple[Optional[float], Optional[float], Optional[str]]:
        """
        Get validated price from dual sources.

        Args:
            token_address: Token address to get price for
            entry_price: Entry price for suspicious drop detection (optional)

        Returns:
            Tuple of (validated_price, liquidity, data_source) or (None, None, None)
        """
        try:
            # DUAL-SOURCE VALIDATION: Query both DexScreener and Jupiter
            dex_profile = await self.dexscreener.get_token_profile(token_address)
            jupiter_data = await self.jupiter.get_token_price_data(token_address)

            # Extract data from both sources
            dex_price = dex_profile['price_usd'] if dex_profile else None
            dex_liquidity = dex_profile.get('liquidity_usd', 0.0) if dex_profile else 0.0

            jupiter_price = jupiter_data['price_usd'] if jupiter_data else None
            jupiter_liquidity = jupiter_data.get('liquidity_usd', 0.0) if jupiter_data else 0.0

            # Cross-validate and choose best data
            current_price = None
            liquidity = 0.0
            data_source = None

            if dex_price and jupiter_price:
                # Both sources available - cross-validate
                price_diff_pct = abs((dex_price - jupiter_price) / dex_price) * 100

                if price_diff_pct < 10:
                    # Prices agree (within 10%) - use average
                    current_price = (dex_price + jupiter_price) / 2
                    liquidity = max(dex_liquidity, jupiter_liquidity)  # Use higher liquidity
                    data_source = "DexScreener + Jupiter"
                    logger.debug(
                        f"Price agreement for {token_address[:8]}: "
                        f"Dex ${dex_price:.8f} vs Jup ${jupiter_price:.8f} (diff: {price_diff_pct:.1f}%)"
                    )
                else:
                    # Large divergence - flag as suspicious
                    logger.warning(
                        f"PRICE DIVERGENCE: {token_address[:8]}... "
                        f"DexScreener ${dex_price:.8f} vs Jupiter ${jupiter_price:.8f} ({price_diff_pct:.1f}% diff!)"
                    )
                    # Use DexScreener as primary (more reliable for liquidity)
                    current_price = dex_price
                    liquidity = dex_liquidity
                    data_source = "DexScreener (divergence)"

            elif dex_price:
                # Only DexScreener available
                current_price = dex_price
                liquidity = dex_liquidity
                data_source = "DexScreener"

            elif jupiter_price:
                # Only Jupiter available - use as fallback
                current_price = jupiter_price
                liquidity = jupiter_liquidity
                data_source = "Jupiter (fallback)"
                logger.info(f"Using Jupiter fallback for {token_address[:8]}...")

            else:
                # No data from either source
                logger.error(f"No price data from either source for {token_address[:8]}...")
                return None, None, None

            # Validate the chosen price
            validated_price = self._validate_price(current_price, entry_price, token_address)

            if validated_price is None:
                return None, None, None

            return validated_price, liquidity, data_source

        except Exception as e:
            logger.error(f"Error getting validated price for {token_address}: {e}")
            return None, None, None

    def _validate_price(
        self,
        price: float,
        entry_price: Optional[float],
        token_address: str
    ) -> Optional[float]:
        """
        🛡️ ENHANCED PRICE VALIDATION - Reject bad data that would cause 100% loss

        Args:
            price: Price to validate
            entry_price: Entry price for suspicious drop detection
            token_address: Token address for logging

        Returns:
            Validated price or None if invalid
        """
        # Check 1: None or not a number
        if price is None:
            logger.warning(f"Price is None for {token_address[:8]}")
            return None

        # Check 2: NaN (not a number)
        try:
            if not isinstance(price, (int, float)) or (isinstance(price, float) and (price != price)):
                logger.warning(f"Price is NaN for {token_address[:8]}")
                return None
        except (TypeError, ValueError):
            logger.warning(f"Invalid price type for {token_address[:8]}: {type(price)}")
            return None

        # Check 3: Infinity
        try:
            if math.isinf(price):
                logger.warning(f"Price is Infinity for {token_address[:8]}")
                return None
        except:
            pass

        # Check 4: Zero or negative
        if price <= 0:
            logger.warning(f"Invalid price ${price} for {token_address[:8]}")
            return None

        # Check 5: Extremely small (effectively zero, < $0.000000001)
        if price < 1e-9:
            logger.warning(f"Price too small ${price} for {token_address[:8]}")
            return None

        # Check 6: Suspicious price drops (>80% loss in one update)
        if entry_price is not None:
            try:
                price_change_pct = ((price - entry_price) / entry_price) * 100

                if price_change_pct < -80:
                    logger.error(
                        f"Rejected suspicious price for {token_address[:8]}: "
                        f"${entry_price:.8f} → ${price:.8f} ({price_change_pct:.1f}%)"
                    )
                    return None
            except (ZeroDivisionError, TypeError):
                logger.error(f"Error calculating price change for {token_address[:8]}")
                return None

        # Price validated - safe to use
        return price

    @staticmethod
    def is_price_divergence_suspicious(
        price1: float,
        price2: float,
        threshold_percent: float = 10.0
    ) -> bool:
        """
        Check if price divergence between two sources is suspicious.

        Args:
            price1: First price
            price2: Second price
            threshold_percent: Divergence threshold (default 10%)

        Returns:
            True if divergence is suspicious (>threshold)
        """
        try:
            if price1 <= 0 or price2 <= 0:
                return True

            diff_pct = abs((price1 - price2) / price1) * 100
            return diff_pct >= threshold_percent

        except (ZeroDivisionError, TypeError):
            return True
