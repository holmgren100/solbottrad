"""
Decision Engine - Simple Binary Pass/Fail Logic

NO AGE-BASED LOGIC
NO SCORING SYSTEMS (0-100 points)
NO COMPLEX DECISION LAYERS

Simple rule: if Safety_Checks_Pass AND Performance_Checks_Pass → TRADE
"""

import logging
from typing import Dict, Tuple
from src.filters.tier1_safety import Tier1SafetyFilters
from src.filters.tier2_performance import Tier2PerformanceFilters

logger = logging.getLogger(__name__)


class DecisionEngine:
    """
    Simple binary decision engine for trading decisions.

    Decision Logic:
        if TIER1_PASS and TIER2_PASS:
            TRADE
        else:
            REJECT (with logged reason)
    """

    def __init__(self, config: Dict):
        """
        Initialize decision engine with filter configurations.

        Args:
            config: Configuration dictionary containing:
                - tier1: TIER 1 safety filter settings
                - tier2: TIER 2 performance filter settings
                - position: Position management settings
        """
        self.tier1_filters = Tier1SafetyFilters(config.get('tier1', {}))
        self.tier2_filters = Tier2PerformanceFilters(config.get('tier2', {}))

        # Position management settings
        position_config = config.get('position', {})
        self.entry_size = position_config.get('entry_size', 0.1)  # SOL
        self.take_profit_percent = position_config.get('take_profit_percent', 15)  # %
        self.stop_loss_percent = position_config.get('stop_loss_percent', 8)  # %
        self.max_hold_hours = position_config.get('max_hold_hours', 4)  # hours

        logger.info(
            f"Initialized Decision Engine - "
            f"Entry: {self.entry_size} SOL, "
            f"TP: +{self.take_profit_percent}%, "
            f"SL: -{self.stop_loss_percent}%, "
            f"Max hold: {self.max_hold_hours}h"
        )

    def evaluate_token(self, token_data: Dict) -> Tuple[bool, Dict]:
        """
        Evaluate a token using simple binary logic.

        Process:
        1. Run TIER 1 safety checks (must all pass)
        2. If TIER 1 passes, run TIER 2 performance checks (must all pass)
        3. If both pass → TRADE, else → REJECT

        Args:
            token_data: Dictionary containing all token information

        Returns:
            Tuple of (should_trade: bool, decision_details: Dict)
            decision_details contains:
                - decision: 'TRADE' or 'REJECT'
                - tier1_passed: bool
                - tier1_results: Dict
                - tier2_passed: bool (None if TIER 1 failed)
                - tier2_results: Dict (None if TIER 1 failed)
                - rejection_reason: str (if rejected)
                - position_params: Dict (if trade approved)
        """
        token_symbol = token_data.get('symbol', 'UNKNOWN')
        token_address = token_data.get('address', 'UNKNOWN')

        logger.info(f"\n{'#'*60}")
        logger.info(f"EVALUATING TOKEN: {token_symbol} ({token_address})")
        logger.info(f"{'#'*60}")

        decision_details = {
            'symbol': token_symbol,
            'address': token_address,
            'tier1_passed': False,
            'tier1_results': {},
            'tier2_passed': None,
            'tier2_results': None,
            'rejection_reason': None,
            'position_params': None,
        }

        # TIER 1: Safety Checks
        tier1_passed, tier1_results = self.tier1_filters.run_all_checks(token_data)
        decision_details['tier1_passed'] = tier1_passed
        decision_details['tier1_results'] = tier1_results

        if not tier1_passed:
            # Collect failed check reasons
            failed_reasons = [
                reason for check, (passed, reason) in tier1_results.items()
                if not passed
            ]
            rejection_reason = "TIER 1 FAILED: " + "; ".join(failed_reasons)
            decision_details['decision'] = 'REJECT'
            decision_details['rejection_reason'] = rejection_reason

            logger.warning(f"🚫 DECISION: REJECT {token_symbol}")
            logger.warning(f"   Reason: {rejection_reason}\n")
            return False, decision_details

        # TIER 2: Performance Checks
        logger.info(f"✅ TIER 1 passed, proceeding to TIER 2...")
        tier2_passed, tier2_results = self.tier2_filters.run_all_checks(token_data)
        decision_details['tier2_passed'] = tier2_passed
        decision_details['tier2_results'] = tier2_results

        if not tier2_passed:
            # Collect failed check reasons
            failed_reasons = [
                reason for check, (passed, reason) in tier2_results.items()
                if not passed
            ]
            rejection_reason = "TIER 2 FAILED: " + "; ".join(failed_reasons)
            decision_details['decision'] = 'REJECT'
            decision_details['rejection_reason'] = rejection_reason

            logger.warning(f"🚫 DECISION: REJECT {token_symbol}")
            logger.warning(f"   Reason: {rejection_reason}\n")
            return False, decision_details

        # ALL CHECKS PASSED → TRADE
        position_params = {
            'entry_size_sol': self.entry_size,
            'take_profit_percent': self.take_profit_percent,
            'stop_loss_percent': self.stop_loss_percent,
            'max_hold_hours': self.max_hold_hours,
            'entry_price': token_data.get('price', 0),
        }

        decision_details['decision'] = 'TRADE'
        decision_details['position_params'] = position_params

        logger.info(f"\n{'='*60}")
        logger.info(f"✅ DECISION: TRADE {token_symbol}")
        logger.info(f"   Entry Size: {self.entry_size} SOL")
        logger.info(f"   Entry Price: {token_data.get('price', 0):.6f} SOL")
        logger.info(f"   Take Profit: +{self.take_profit_percent}%")
        logger.info(f"   Stop Loss: -{self.stop_loss_percent}%")
        logger.info(f"   Max Hold: {self.max_hold_hours} hours")
        logger.info(f"{'='*60}\n")

        return True, decision_details

    def get_summary_stats(self) -> Dict:
        """
        Get summary statistics of the decision engine configuration.

        Returns:
            Dictionary containing configuration summary
        """
        return {
            'tier1_config': {
                'min_price': self.tier1_filters.min_price,
                'max_price': self.tier1_filters.max_price,
                'min_liquidity': self.tier1_filters.min_liquidity,
                'min_security_score': self.tier1_filters.min_security_score,
            },
            'tier2_config': {
                'min_volume_liquidity_ratio': self.tier2_filters.min_volume_liquidity_ratio,
                'max_volume_liquidity_ratio': self.tier2_filters.max_volume_liquidity_ratio,
                'max_tokens_per_dollar': self.tier2_filters.max_tokens_per_dollar,
                'max_top_holder_percent': self.tier2_filters.max_top_holder_percent,
            },
            'position_config': {
                'entry_size': self.entry_size,
                'take_profit_percent': self.take_profit_percent,
                'stop_loss_percent': self.stop_loss_percent,
                'max_hold_hours': self.max_hold_hours,
            },
        }
