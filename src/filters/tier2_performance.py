"""
TIER 2 Performance Filters - Binary Pass/Fail Checks

These filters check token performance metrics to identify good trading opportunities.
Tokens must pass TIER 1 safety checks before reaching these filters.
Based on analysis of 774 trades showing 71.4% win rate with these parameters.
"""

import logging
from typing import Dict, Tuple

logger = logging.getLogger(__name__)


class Tier2PerformanceFilters:
    """Performance filters based on historical data analysis."""

    def __init__(self, config: Dict):
        """
        Initialize TIER 2 performance filters with configuration.

        Args:
            config: Dictionary containing filter thresholds:
                - min_volume_liquidity_ratio: Minimum V/L ratio (default: 0.3)
                - max_volume_liquidity_ratio: Maximum V/L ratio (default: 0.8)
                - max_tokens_per_dollar: Max tokens/$1 (default: 10000)
                - max_top_holder_percent: Max top holder % (default: 20)
        """
        self.min_volume_liquidity_ratio = config.get('min_volume_liquidity_ratio', 0.3)
        self.max_volume_liquidity_ratio = config.get('max_volume_liquidity_ratio', 0.8)
        self.max_tokens_per_dollar = config.get('max_tokens_per_dollar', 10000)
        self.max_top_holder_percent = config.get('max_top_holder_percent', 20)

        logger.info(
            f"Initialized TIER 2 Performance Filters: "
            f"V/L ratio={self.min_volume_liquidity_ratio}-{self.max_volume_liquidity_ratio}, "
            f"max_tokens_per_dollar={self.max_tokens_per_dollar:,}, "
            f"max_top_holder={self.max_top_holder_percent}%"
        )

    def check_volume_liquidity_ratio(self, token_data: Dict) -> Tuple[bool, str]:
        """
        Check if Volume/Liquidity ratio is in optimal range.

        Optimal range: 0.3 to 0.8 (from historical data analysis)
        - Too low (<0.3): Not enough trading activity
        - Too high (>0.8): Potential pump & dump

        Args:
            token_data: Dictionary containing 'volume_24h' and 'liquidity'

        Returns:
            Tuple of (pass: bool, reason: str)
        """
        volume = token_data.get('volume_24h', 0)
        liquidity = token_data.get('liquidity', 1)  # Avoid division by zero

        if liquidity == 0:
            reason = "Cannot calculate V/L ratio: liquidity is zero"
            logger.info(f"❌ REJECTED - {reason}")
            return False, reason

        ratio = volume / liquidity

        if ratio < self.min_volume_liquidity_ratio:
            reason = (
                f"V/L ratio too low: {ratio:.3f} < {self.min_volume_liquidity_ratio} "
                f"(volume=${volume:,.0f}, liquidity=${liquidity:,.0f})"
            )
            logger.info(f"❌ REJECTED - {reason}")
            return False, reason

        if ratio > self.max_volume_liquidity_ratio:
            reason = (
                f"V/L ratio too high: {ratio:.3f} > {self.max_volume_liquidity_ratio} "
                f"(volume=${volume:,.0f}, liquidity=${liquidity:,.0f})"
            )
            logger.info(f"❌ REJECTED - {reason}")
            return False, reason

        logger.debug(f"✅ V/L ratio check passed: {ratio:.3f}")
        return True, f"V/L ratio OK: {ratio:.3f}"

    def check_tokens_per_dollar(self, token_data: Dict) -> Tuple[bool, str]:
        """
        Check tokens per dollar is below maximum threshold.

        Maximum: 10,000 tokens per $1 (filters extremely cheap tokens)
        Based on November 2024 version with 71.4% win rate.

        Args:
            token_data: Dictionary containing 'price' in SOL and 'sol_price_usd'

        Returns:
            Tuple of (pass: bool, reason: str)
        """
        price_sol = token_data.get('price', 0)
        sol_price_usd = token_data.get('sol_price_usd', 100)  # Default SOL price

        if price_sol == 0:
            reason = "Cannot calculate tokens per dollar: price is zero"
            logger.info(f"❌ REJECTED - {reason}")
            return False, reason

        # Calculate token price in USD
        price_usd = price_sol * sol_price_usd
        tokens_per_dollar = 1.0 / price_usd if price_usd > 0 else float('inf')

        if tokens_per_dollar > self.max_tokens_per_dollar:
            reason = (
                f"Too many tokens per dollar: {tokens_per_dollar:,.0f} > "
                f"{self.max_tokens_per_dollar:,} "
                f"(price=${price_usd:.6f})"
            )
            logger.info(f"❌ REJECTED - {reason}")
            return False, reason

        logger.debug(f"✅ Tokens per dollar check passed: {tokens_per_dollar:,.0f}")
        return True, f"Tokens per dollar OK: {tokens_per_dollar:,.0f}"

    def check_top_holder_concentration(self, token_data: Dict) -> Tuple[bool, str]:
        """
        Check top holder concentration is below maximum threshold.

        Maximum: 20% (prevents whale manipulation risk)

        Args:
            token_data: Dictionary containing 'top_holder_percent'

        Returns:
            Tuple of (pass: bool, reason: str)
        """
        top_holder_percent = token_data.get('top_holder_percent', 0)

        if top_holder_percent > self.max_top_holder_percent:
            reason = (
                f"Top holder concentration too high: {top_holder_percent:.1f}% > "
                f"{self.max_top_holder_percent}%"
            )
            logger.info(f"❌ REJECTED - {reason}")
            return False, reason

        logger.debug(f"✅ Top holder check passed: {top_holder_percent:.1f}%")
        return True, f"Top holder OK: {top_holder_percent:.1f}%"

    def run_all_checks(self, token_data: Dict) -> Tuple[bool, Dict[str, Tuple[bool, str]]]:
        """
        Run all TIER 2 performance checks on a token.

        Args:
            token_data: Dictionary containing all token information

        Returns:
            Tuple of (all_passed: bool, results: Dict)
            results format: {
                'check_name': (passed: bool, reason: str),
                ...
            }
        """
        token_symbol = token_data.get('symbol', 'UNKNOWN')
        logger.info(f"\n{'='*60}")
        logger.info(f"Running TIER 2 Performance Checks for {token_symbol}")
        logger.info(f"{'='*60}")

        results = {
            'volume_liquidity_ratio': self.check_volume_liquidity_ratio(token_data),
            'tokens_per_dollar': self.check_tokens_per_dollar(token_data),
            'top_holder_concentration': self.check_top_holder_concentration(token_data),
        }

        # All checks must pass
        all_passed = all(passed for passed, _ in results.values())

        if all_passed:
            logger.info(f"✅ {token_symbol} PASSED all TIER 2 performance checks")
        else:
            failed_checks = [name for name, (passed, _) in results.items() if not passed]
            logger.info(f"❌ {token_symbol} FAILED TIER 2 checks: {', '.join(failed_checks)}")

        return all_passed, results
