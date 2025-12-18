"""
Safety Filters Module

Optional pre-filters that check for common rug pull indicators:
- LP lock status (locked, burned, duration)
- Holder concentration (top 10, top 1)
- Contract safety (mint authority, freeze authority, ownership)

These filters run BEFORE the core RiskAssessor.
They are OPTIONAL and can be toggled on/off to test impact on performance.

WHY OPTIONAL:
- ML Bot 2 doesn't use these and achieves 71.7% win rate
- They may block good opportunities (needs A/B testing)
- Should be tested to see if they IMPROVE or HURT performance

Usage:
    filters = SafetyFilters(enabled=True, config={...})

    passed, reason = filters.check_all(token_data)

    if not passed:
        logger.info(f"Blocked by safety filter: {reason}")
"""

import logging
from typing import Dict, Tuple, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SafetyConfig:
    """Configuration for safety filters."""

    # LP Lock checking
    enable_lp_lock_check: bool = True
    lp_lock_min_days: int = 30
    lp_lock_accept_burned: bool = True  # Accept burned LP as safe

    # Holder concentration checking
    enable_holder_check: bool = True
    holder_top10_max_percent: float = 50.0  # Top 10 holders < 50%
    holder_top1_max_percent: float = 20.0   # Top 1 holder < 20%

    # Contract safety checking
    enable_contract_safety: bool = True
    reject_mint_authority: bool = True      # Reject if can mint new tokens
    reject_freeze_authority: bool = True     # Reject if can freeze accounts
    require_ownership_renounced: bool = True  # Require ownership renounced


class SafetyFilters:
    """
    Optional safety pre-filters for rug detection.

    These check for common rug pull indicators BEFORE the core RiskAssessor.
    All checks are configurable and can be disabled for A/B testing.

    IMPORTANT: ML Bot 2 achieves 71.7% win without these filters!
    Test if they IMPROVE or HURT performance before keeping them.
    """

    def __init__(
        self,
        enabled: bool = True,
        config: Optional[SafetyConfig] = None
    ):
        """
        Initialize safety filters.

        Args:
            enabled: Whether filters are enabled globally
            config: Filter configuration (uses defaults if None)
        """
        self.enabled = enabled
        self.config = config or SafetyConfig()

        if self.enabled:
            logger.info("Safety filters enabled")
        else:
            logger.info("Safety filters disabled")

    def check_all(self, token_data: Dict) -> Tuple[bool, str]:
        """
        Run all enabled safety checks.

        Args:
            token_data: Token data dictionary with security/holder info

        Returns:
            Tuple of (passed: bool, reason: str)
            - (True, "passed") if all checks pass
            - (False, "reason") if any check fails
        """
        if not self.enabled:
            return True, "safety_filters_disabled"

        # LP Lock Check
        if self.config.enable_lp_lock_check:
            passed, reason = self.check_lp_lock(token_data)
            if not passed:
                return False, reason

        # Holder Concentration Check
        if self.config.enable_holder_check:
            passed, reason = self.check_holder_concentration(token_data)
            if not passed:
                return False, reason

        # Contract Safety Check
        if self.config.enable_contract_safety:
            passed, reason = self.check_contract_safety(token_data)
            if not passed:
                return False, reason

        return True, "passed_all_safety_checks"

    def check_lp_lock(self, token_data: Dict) -> Tuple[bool, str]:
        """
        Check if LP (liquidity provider) is locked or burned.

        Locked/burned LP prevents rug pulls where developers drain liquidity.

        Args:
            token_data: Token data with LP lock info

        Returns:
            (passed, reason) tuple
        """
        # Extract LP lock data
        lp_locked = token_data.get('lp_locked', False)
        lp_burned = token_data.get('lp_burned', False)
        lp_lock_days = token_data.get('lp_lock_days', 0)

        # Check if LP is burned (permanently locked)
        if self.config.lp_lock_accept_burned and lp_burned:
            logger.debug("LP lock check passed: LP burned (permanent)")
            return True, "lp_burned"

        # Check if LP is locked for sufficient duration
        if lp_locked and lp_lock_days >= self.config.lp_lock_min_days:
            logger.debug(f"LP lock check passed: Locked for {lp_lock_days} days")
            return True, f"lp_locked_{lp_lock_days}d"

        # Failed - LP not adequately locked
        if lp_locked:
            reason = f"lp_lock_insufficient ({lp_lock_days}/{self.config.lp_lock_min_days} days)"
        else:
            reason = "lp_not_locked"

        logger.debug(f"LP lock check failed: {reason}")
        return False, reason

    def check_holder_concentration(self, token_data: Dict) -> Tuple[bool, str]:
        """
        Check holder concentration to detect potential manipulation.

        High holder concentration = few wallets own most tokens = rug risk.

        Args:
            token_data: Token data with holder info

        Returns:
            (passed, reason) tuple
        """
        # Extract holder data
        top10_percent = token_data.get('top10_concentration', 0.0)
        top1_percent = token_data.get('top1_concentration', 0.0)

        # Check top 10 holders concentration
        if top10_percent > self.config.holder_top10_max_percent:
            reason = f"top10_concentration_too_high ({top10_percent:.1f}% > {self.config.holder_top10_max_percent}%)"
            logger.debug(f"Holder check failed: {reason}")
            return False, reason

        # Check top 1 holder concentration
        if top1_percent > self.config.holder_top1_max_percent:
            reason = f"top1_concentration_too_high ({top1_percent:.1f}% > {self.config.holder_top1_max_percent}%)"
            logger.debug(f"Holder check failed: {reason}")
            return False, reason

        logger.debug(f"Holder check passed: Top10={top10_percent:.1f}%, Top1={top1_percent:.1f}%")
        return True, f"holders_ok_top10_{top10_percent:.0f}_top1_{top1_percent:.0f}"

    def check_contract_safety(self, token_data: Dict) -> Tuple[bool, str]:
        """
        Check contract safety features.

        Dangerous features:
        - Mint authority: Can create new tokens (dilutes holders)
        - Freeze authority: Can freeze accounts (prevents selling)
        - Ownership not renounced: Developer still controls contract

        Args:
            token_data: Token data with contract info

        Returns:
            (passed, reason) tuple
        """
        # Extract contract safety data
        mint_authority = token_data.get('mint_authority_active', False)
        freeze_authority = token_data.get('freeze_authority_active', False)
        ownership_renounced = token_data.get('ownership_renounced', False)

        # Check mint authority (dangerous - can mint unlimited tokens)
        if self.config.reject_mint_authority and mint_authority:
            reason = "mint_authority_active"
            logger.debug(f"Contract safety check failed: {reason}")
            return False, reason

        # Check freeze authority (dangerous - can freeze accounts)
        if self.config.reject_freeze_authority and freeze_authority:
            reason = "freeze_authority_active"
            logger.debug(f"Contract safety check failed: {reason}")
            return False, reason

        # Check ownership renounced (safe - developer can't modify contract)
        if self.config.require_ownership_renounced and not ownership_renounced:
            reason = "ownership_not_renounced"
            logger.debug(f"Contract safety check failed: {reason}")
            return False, reason

        logger.debug("Contract safety check passed")
        return True, "contract_safe"

    def get_safety_score(self, token_data: Dict) -> float:
        """
        Calculate overall safety score (0-100).

        Higher = safer. Can be used for position sizing or filtering.

        Args:
            token_data: Token data

        Returns:
            Safety score 0-100
        """
        score = 0.0
        max_score = 100.0

        # LP lock score (0-40 points)
        lp_locked = token_data.get('lp_locked', False)
        lp_burned = token_data.get('lp_burned', False)
        lp_lock_days = token_data.get('lp_lock_days', 0)

        if lp_burned:
            score += 40.0  # Full points for burned LP
        elif lp_locked:
            # Partial points based on lock duration
            score += min(40.0, (lp_lock_days / 90) * 40.0)  # 90 days = full points

        # Holder concentration score (0-30 points)
        top10_percent = token_data.get('top10_concentration', 100.0)
        top1_percent = token_data.get('top1_concentration', 100.0)

        # Lower concentration = higher score
        top10_score = max(0, (100 - top10_percent) / 100 * 20)  # 20 points max
        top1_score = max(0, (100 - top1_percent) / 100 * 10)   # 10 points max
        score += top10_score + top1_score

        # Contract safety score (0-30 points)
        mint_authority = token_data.get('mint_authority_active', True)
        freeze_authority = token_data.get('freeze_authority_active', True)
        ownership_renounced = token_data.get('ownership_renounced', False)

        if not mint_authority:
            score += 10.0  # No mint = safe
        if not freeze_authority:
            score += 10.0  # No freeze = safe
        if ownership_renounced:
            score += 10.0  # Renounced = safe

        return min(score, max_score)

    def get_risk_factors(self, token_data: Dict) -> Dict[str, bool]:
        """
        Get individual risk factors as boolean flags.

        Args:
            token_data: Token data

        Returns:
            Dictionary of risk factors
        """
        return {
            'lp_not_locked': not token_data.get('lp_locked', False) and not token_data.get('lp_burned', False),
            'lp_lock_insufficient': token_data.get('lp_locked', False) and token_data.get('lp_lock_days', 0) < self.config.lp_lock_min_days,
            'top10_too_concentrated': token_data.get('top10_concentration', 0.0) > self.config.holder_top10_max_percent,
            'top1_too_concentrated': token_data.get('top1_concentration', 0.0) > self.config.holder_top1_max_percent,
            'mint_authority_active': token_data.get('mint_authority_active', False),
            'freeze_authority_active': token_data.get('freeze_authority_active', False),
            'ownership_not_renounced': not token_data.get('ownership_renounced', False),
        }

    def __repr__(self) -> str:
        """String representation."""
        status = "enabled" if self.enabled else "disabled"
        checks = []

        if self.config.enable_lp_lock_check:
            checks.append(f"LP lock ({self.config.lp_lock_min_days}d min)")
        if self.config.enable_holder_check:
            checks.append(f"Holder conc (top10<{self.config.holder_top10_max_percent}%, top1<{self.config.holder_top1_max_percent}%)")
        if self.config.enable_contract_safety:
            checks.append("Contract safety")

        checks_str = ", ".join(checks) if checks else "none"

        return f"SafetyFilters({status}, checks: {checks_str})"
