"""
TIER 1 Safety Filters - Binary Pass/Fail Checks

These filters ensure basic safety requirements before considering a trade.
All filters must pass for a token to proceed to TIER 2 performance checks.
"""

import logging
from typing import Dict, Tuple

logger = logging.getLogger(__name__)


class Tier1SafetyFilters:
    """Safety filters that must all pass before trading a token."""

    def __init__(self, config: Dict):
        """
        Initialize TIER 1 safety filters with configuration.

        Args:
            config: Dictionary containing filter thresholds:
                - min_price: Minimum token price in SOL (default: 0.10)
                - max_price: Maximum token price in SOL (default: 1.0)
                - min_liquidity: Minimum liquidity in USD (default: 50000)
                - min_security_score: Minimum security score 0-100 (default: 80)
        """
        self.min_price = config.get('min_price', 0.10)
        self.max_price = config.get('max_price', 1.0)
        self.min_liquidity = config.get('min_liquidity', 50000)
        self.min_security_score = config.get('min_security_score', 80)

        logger.info(
            f"Initialized TIER 1 Safety Filters: "
            f"price={self.min_price}-{self.max_price} SOL, "
            f"min_liquidity=${self.min_liquidity:,}, "
            f"min_security={self.min_security_score}"
        )

    def check_price_range(self, token_data: Dict) -> Tuple[bool, str]:
        """
        Check if token price is within acceptable range.

        Range: 0.10 to 1.0 SOL (sweet spot from historical data)

        Args:
            token_data: Dictionary containing 'price' in SOL

        Returns:
            Tuple of (pass: bool, reason: str)
        """
        price = token_data.get('price', 0)

        if price < self.min_price:
            reason = f"Price too low: {price:.4f} SOL < {self.min_price} SOL"
            logger.info(f"❌ REJECTED - {reason}")
            return False, reason

        if price > self.max_price:
            reason = f"Price too high: {price:.4f} SOL > {self.max_price} SOL"
            logger.info(f"❌ REJECTED - {reason}")
            return False, reason

        logger.debug(f"✅ Price check passed: {price:.4f} SOL")
        return True, f"Price OK: {price:.4f} SOL"

    def check_liquidity(self, token_data: Dict) -> Tuple[bool, str]:
        """
        Check if token has sufficient liquidity.

        Minimum: $50,000 (prevents low-liquidity traps)

        Args:
            token_data: Dictionary containing 'liquidity' in USD

        Returns:
            Tuple of (pass: bool, reason: str)
        """
        liquidity = token_data.get('liquidity', 0)

        if liquidity < self.min_liquidity:
            reason = f"Insufficient liquidity: ${liquidity:,.0f} < ${self.min_liquidity:,}"
            logger.info(f"❌ REJECTED - {reason}")
            return False, reason

        logger.debug(f"✅ Liquidity check passed: ${liquidity:,.0f}")
        return True, f"Liquidity OK: ${liquidity:,.0f}"

    def check_security_score(self, token_data: Dict) -> Tuple[bool, str]:
        """
        Check if token meets minimum security score.

        Minimum: 80/100 (filters out risky contracts)

        Args:
            token_data: Dictionary containing 'security_score' (0-100)

        Returns:
            Tuple of (pass: bool, reason: str)
        """
        security_score = token_data.get('security_score', 0)

        if security_score < self.min_security_score:
            reason = f"Low security score: {security_score}/100 < {self.min_security_score}/100"
            logger.info(f"❌ REJECTED - {reason}")
            return False, reason

        logger.debug(f"✅ Security check passed: {security_score}/100")
        return True, f"Security OK: {security_score}/100"

    def check_contract_verified(self, token_data: Dict) -> Tuple[bool, str]:
        """
        Check if smart contract is verified.

        Required: YES (unverified contracts are too risky)

        Args:
            token_data: Dictionary containing 'contract_verified' (bool)

        Returns:
            Tuple of (pass: bool, reason: str)
        """
        verified = token_data.get('contract_verified', False)

        if not verified:
            reason = "Contract not verified"
            logger.info(f"❌ REJECTED - {reason}")
            return False, reason

        logger.debug("✅ Contract verification passed")
        return True, "Contract verified"

    def run_all_checks(self, token_data: Dict) -> Tuple[bool, Dict[str, Tuple[bool, str]]]:
        """
        Run all TIER 1 safety checks on a token.

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
        logger.info(f"Running TIER 1 Safety Checks for {token_symbol}")
        logger.info(f"{'='*60}")

        results = {
            'price_range': self.check_price_range(token_data),
            'liquidity': self.check_liquidity(token_data),
            'security_score': self.check_security_score(token_data),
            'contract_verified': self.check_contract_verified(token_data),
        }

        # All checks must pass
        all_passed = all(passed for passed, _ in results.values())

        if all_passed:
            logger.info(f"✅ {token_symbol} PASSED all TIER 1 safety checks")
        else:
            failed_checks = [name for name, (passed, _) in results.items() if not passed]
            logger.info(f"❌ {token_symbol} FAILED TIER 1 checks: {', '.join(failed_checks)}")

        return all_passed, results
