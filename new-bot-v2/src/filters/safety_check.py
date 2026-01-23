"""
Safety Check Filter - Binary Pass/Fail

CRITICAL: These checks MUST pass before any trade.

Checks (BINARY - both must pass):
1. LP_BURNED = True (prevents liquidity rug)
2. MINT_REVOKED = True (prevents inflation rug)

If EITHER fails → REJECT immediately!
"""

import logging
from typing import Dict, Optional

from src.api.alchemy_client import AlchemyClient
from config.parameters import (
    LP_BURNED_REQUIRED,
    MINT_REVOKED_REQUIRED
)

logger = logging.getLogger(__name__)


class SafetyCheck:
    """
    Binary safety filter for token verification.

    These are THE most important filters - they prevent rug pulls!
    """

    def __init__(self):
        """Initialize safety check filter."""
        self.alchemy_client = AlchemyClient()

        logger.info(
            f"Safety Check initialized: "
            f"LP_BURNED={LP_BURNED_REQUIRED}, "
            f"MINT_REVOKED={MINT_REVOKED_REQUIRED}"
        )

    def check_token(
        self,
        token_address: str,
        lp_address: Optional[str] = None
    ) -> Dict:
        """
        Run complete safety check on a token.

        Args:
            token_address: Token mint address
            lp_address: LP token address (optional, for LP burned check)

        Returns:
            {
                "safe": bool,  # True only if ALL checks pass
                "mint_revoked": bool,
                "lp_burned": bool,
                "passed_checks": List[str],
                "failed_checks": List[str],
                "rejection_reason": str  # If rejected
            }
        """
        try:
            passed_checks = []
            failed_checks = []

            logger.info(f"Running safety checks for {token_address}")

            # Check 1: Mint authority revoked
            mint_revoked = self.alchemy_client.check_mint_authority(token_address)

            if mint_revoked:
                passed_checks.append("Mint authority REVOKED")
            else:
                failed_checks.append("Mint authority NOT revoked (inflation risk!)")

            # Check 2: LP burned
            lp_burned = self.alchemy_client.check_lp_burned(token_address, lp_address)

            if lp_burned:
                passed_checks.append("LP tokens BURNED")
            else:
                failed_checks.append("LP tokens NOT burned (liquidity rug risk!)")

            # Token is safe only if BOTH checks pass
            safe = mint_revoked and lp_burned

            # Build rejection reason if not safe
            if not safe:
                rejection_reason = "SAFETY CHECK FAILED: " + "; ".join(failed_checks)
            else:
                rejection_reason = ""

            result = {
                "safe": safe,
                "mint_revoked": mint_revoked,
                "lp_burned": lp_burned,
                "passed_checks": passed_checks,
                "failed_checks": failed_checks,
                "rejection_reason": rejection_reason
            }

            if safe:
                logger.info(f"✅ SAFETY CHECK PASSED for {token_address}")
                for check in passed_checks:
                    logger.info(f"   ✓ {check}")
            else:
                logger.error(f"❌ SAFETY CHECK FAILED for {token_address}")
                for check in failed_checks:
                    logger.error(f"   ✗ {check}")

            return result

        except Exception as e:
            logger.error(f"Error in safety check: {e}")
            return {
                "safe": False,
                "mint_revoked": False,
                "lp_burned": False,
                "passed_checks": [],
                "failed_checks": [f"Error: {e}"],
                "rejection_reason": f"Safety check error: {e}"
            }

    def is_safe(self, token_address: str, lp_address: Optional[str] = None) -> bool:
        """
        Quick safety check - returns True/False only.

        Args:
            token_address: Token mint address
            lp_address: LP token address (optional)

        Returns:
            True if safe, False otherwise
        """
        result = self.check_token(token_address, lp_address)
        return result["safe"]


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    safety_check = SafetyCheck()

    # Test with a token address (replace with real one)
    test_token = "So11111111111111111111111111111111111111112"  # Wrapped SOL

    result = safety_check.check_token(test_token)

    print(f"\nSafety Check Result:")
    print(f"Safe: {result['safe']}")
    print(f"Mint Revoked: {result['mint_revoked']}")
    print(f"LP Burned: {result['lp_burned']}")
    print(f"\nPassed Checks:")
    for check in result['passed_checks']:
        print(f"  ✓ {check}")
    print(f"\nFailed Checks:")
    for check in result['failed_checks']:
        print(f"  ✗ {check}")

    if not result['safe']:
        print(f"\nRejection Reason: {result['rejection_reason']}")
