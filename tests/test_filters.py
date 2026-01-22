"""
Comprehensive tests for TIER 1 and TIER 2 filters

Tests each filter function independently and the complete decision engine.
"""

import pytest
from src.filters.tier1_safety import Tier1SafetyFilters
from src.filters.tier2_performance import Tier2PerformanceFilters
from src.decision_engine import DecisionEngine


class TestTier1SafetyFilters:
    """Test TIER 1 safety filters."""

    @pytest.fixture
    def tier1_filters(self):
        """Create TIER 1 filters with default config."""
        config = {
            'min_price': 0.10,
            'max_price': 1.0,
            'min_liquidity': 50000,
            'min_security_score': 80,
        }
        return Tier1SafetyFilters(config)

    def test_price_range_pass(self, tier1_filters):
        """Test price check passes for valid price."""
        token_data = {'price': 0.15}
        passed, reason = tier1_filters.check_price_range(token_data)
        assert passed is True
        assert "OK" in reason

    def test_price_too_low(self, tier1_filters):
        """Test price check fails for price below minimum."""
        token_data = {'price': 0.05}
        passed, reason = tier1_filters.check_price_range(token_data)
        assert passed is False
        assert "too low" in reason.lower()

    def test_price_too_high(self, tier1_filters):
        """Test price check fails for price above maximum."""
        token_data = {'price': 1.5}
        passed, reason = tier1_filters.check_price_range(token_data)
        assert passed is False
        assert "too high" in reason.lower()

    def test_price_at_boundaries(self, tier1_filters):
        """Test price check at exact boundaries."""
        # At minimum boundary
        token_data = {'price': 0.10}
        passed, _ = tier1_filters.check_price_range(token_data)
        assert passed is True

        # At maximum boundary
        token_data = {'price': 1.0}
        passed, _ = tier1_filters.check_price_range(token_data)
        assert passed is True

    def test_liquidity_pass(self, tier1_filters):
        """Test liquidity check passes for sufficient liquidity."""
        token_data = {'liquidity': 75000}
        passed, reason = tier1_filters.check_liquidity(token_data)
        assert passed is True
        assert "OK" in reason

    def test_liquidity_insufficient(self, tier1_filters):
        """Test liquidity check fails for insufficient liquidity."""
        token_data = {'liquidity': 30000}
        passed, reason = tier1_filters.check_liquidity(token_data)
        assert passed is False
        assert "insufficient" in reason.lower()

    def test_liquidity_at_boundary(self, tier1_filters):
        """Test liquidity check at exact boundary."""
        token_data = {'liquidity': 50000}
        passed, _ = tier1_filters.check_liquidity(token_data)
        assert passed is True

    def test_security_score_pass(self, tier1_filters):
        """Test security score check passes for high score."""
        token_data = {'security_score': 85}
        passed, reason = tier1_filters.check_security_score(token_data)
        assert passed is True
        assert "OK" in reason

    def test_security_score_too_low(self, tier1_filters):
        """Test security score check fails for low score."""
        token_data = {'security_score': 70}
        passed, reason = tier1_filters.check_security_score(token_data)
        assert passed is False
        assert "low security" in reason.lower()

    def test_security_score_at_boundary(self, tier1_filters):
        """Test security score check at exact boundary."""
        token_data = {'security_score': 80}
        passed, _ = tier1_filters.check_security_score(token_data)
        assert passed is True

    def test_contract_verified_pass(self, tier1_filters):
        """Test contract verification check passes when verified."""
        token_data = {'contract_verified': True}
        passed, reason = tier1_filters.check_contract_verified(token_data)
        assert passed is True
        assert "verified" in reason.lower()

    def test_contract_not_verified(self, tier1_filters):
        """Test contract verification check fails when not verified."""
        token_data = {'contract_verified': False}
        passed, reason = tier1_filters.check_contract_verified(token_data)
        assert passed is False
        assert "not verified" in reason.lower()

    def test_run_all_checks_pass(self, tier1_filters):
        """Test all TIER 1 checks pass for valid token."""
        token_data = {
            'symbol': 'TEST',
            'price': 0.15,
            'liquidity': 75000,
            'security_score': 85,
            'contract_verified': True,
        }
        all_passed, results = tier1_filters.run_all_checks(token_data)
        assert all_passed is True
        assert len(results) == 4
        assert all(passed for passed, _ in results.values())

    def test_run_all_checks_fail(self, tier1_filters):
        """Test TIER 1 checks fail when one check fails."""
        token_data = {
            'symbol': 'TEST',
            'price': 0.05,  # Too low
            'liquidity': 75000,
            'security_score': 85,
            'contract_verified': True,
        }
        all_passed, results = tier1_filters.run_all_checks(token_data)
        assert all_passed is False


class TestTier2PerformanceFilters:
    """Test TIER 2 performance filters."""

    @pytest.fixture
    def tier2_filters(self):
        """Create TIER 2 filters with default config."""
        config = {
            'min_volume_liquidity_ratio': 0.3,
            'max_volume_liquidity_ratio': 0.8,
            'max_tokens_per_dollar': 10000,
            'max_top_holder_percent': 20,
        }
        return Tier2PerformanceFilters(config)

    def test_volume_liquidity_ratio_pass(self, tier2_filters):
        """Test V/L ratio check passes for optimal ratio."""
        token_data = {
            'volume_24h': 50000,
            'liquidity': 100000,
        }
        passed, reason = tier2_filters.check_volume_liquidity_ratio(token_data)
        assert passed is True
        assert "OK" in reason

    def test_volume_liquidity_ratio_too_low(self, tier2_filters):
        """Test V/L ratio check fails for low ratio."""
        token_data = {
            'volume_24h': 20000,
            'liquidity': 100000,
        }
        passed, reason = tier2_filters.check_volume_liquidity_ratio(token_data)
        assert passed is False
        assert "too low" in reason.lower()

    def test_volume_liquidity_ratio_too_high(self, tier2_filters):
        """Test V/L ratio check fails for high ratio."""
        token_data = {
            'volume_24h': 90000,
            'liquidity': 100000,
        }
        passed, reason = tier2_filters.check_volume_liquidity_ratio(token_data)
        assert passed is False
        assert "too high" in reason.lower()

    def test_volume_liquidity_ratio_at_boundaries(self, tier2_filters):
        """Test V/L ratio check at exact boundaries."""
        # At minimum boundary
        token_data = {
            'volume_24h': 30000,
            'liquidity': 100000,
        }
        passed, _ = tier2_filters.check_volume_liquidity_ratio(token_data)
        assert passed is True

        # At maximum boundary
        token_data = {
            'volume_24h': 80000,
            'liquidity': 100000,
        }
        passed, _ = tier2_filters.check_volume_liquidity_ratio(token_data)
        assert passed is True

    def test_tokens_per_dollar_pass(self, tier2_filters):
        """Test tokens per dollar check passes for acceptable value."""
        token_data = {
            'price': 0.15,  # SOL
            'sol_price_usd': 100,
        }
        passed, reason = tier2_filters.check_tokens_per_dollar(token_data)
        assert passed is True
        assert "OK" in reason

    def test_tokens_per_dollar_too_high(self, tier2_filters):
        """Test tokens per dollar check fails for too many tokens/$."""
        # For 20,000 tokens per $1: price_usd = 1/20000 = 0.00005
        # With SOL = $100: price_sol = 0.00005 / 100 = 0.0000005
        token_data = {
            'price': 0.0000005,  # Very cheap token (20,000 tokens per $1)
            'sol_price_usd': 100,
        }
        passed, reason = tier2_filters.check_tokens_per_dollar(token_data)
        assert passed is False
        assert "too many" in reason.lower()

    def test_top_holder_concentration_pass(self, tier2_filters):
        """Test top holder check passes for acceptable concentration."""
        token_data = {'top_holder_percent': 15}
        passed, reason = tier2_filters.check_top_holder_concentration(token_data)
        assert passed is True
        assert "OK" in reason

    def test_top_holder_concentration_too_high(self, tier2_filters):
        """Test top holder check fails for high concentration."""
        token_data = {'top_holder_percent': 25}
        passed, reason = tier2_filters.check_top_holder_concentration(token_data)
        assert passed is False
        assert "too high" in reason.lower()

    def test_top_holder_at_boundary(self, tier2_filters):
        """Test top holder check at exact boundary."""
        token_data = {'top_holder_percent': 20}
        passed, _ = tier2_filters.check_top_holder_concentration(token_data)
        assert passed is True

    def test_run_all_checks_pass(self, tier2_filters):
        """Test all TIER 2 checks pass for valid token."""
        token_data = {
            'symbol': 'TEST',
            'volume_24h': 50000,
            'liquidity': 100000,
            'price': 0.15,
            'sol_price_usd': 100,
            'top_holder_percent': 15,
        }
        all_passed, results = tier2_filters.run_all_checks(token_data)
        assert all_passed is True
        assert len(results) == 3
        assert all(passed for passed, _ in results.values())

    def test_run_all_checks_fail(self, tier2_filters):
        """Test TIER 2 checks fail when one check fails."""
        token_data = {
            'symbol': 'TEST',
            'volume_24h': 20000,  # V/L ratio too low (0.2)
            'liquidity': 100000,
            'price': 0.15,
            'sol_price_usd': 100,
            'top_holder_percent': 15,
        }
        all_passed, results = tier2_filters.run_all_checks(token_data)
        assert all_passed is False


class TestDecisionEngine:
    """Test the complete decision engine."""

    @pytest.fixture
    def decision_engine(self):
        """Create decision engine with default config."""
        config = {
            'tier1': {
                'min_price': 0.10,
                'max_price': 1.0,
                'min_liquidity': 50000,
                'min_security_score': 80,
            },
            'tier2': {
                'min_volume_liquidity_ratio': 0.3,
                'max_volume_liquidity_ratio': 0.8,
                'max_tokens_per_dollar': 10000,
                'max_top_holder_percent': 20,
            },
            'position': {
                'entry_size': 0.1,
                'take_profit_percent': 15,
                'stop_loss_percent': 8,
                'max_hold_hours': 4,
            },
        }
        return DecisionEngine(config)

    def test_evaluate_token_all_pass(self, decision_engine):
        """Test token evaluation when all checks pass."""
        token_data = {
            'symbol': 'GOODTOKEN',
            'address': '0x123',
            'price': 0.15,
            'liquidity': 75000,
            'security_score': 85,
            'contract_verified': True,
            'volume_24h': 40000,
            'sol_price_usd': 100,
            'top_holder_percent': 15,
        }
        should_trade, details = decision_engine.evaluate_token(token_data)
        assert should_trade is True
        assert details['decision'] == 'TRADE'
        assert details['tier1_passed'] is True
        assert details['tier2_passed'] is True
        assert details['position_params'] is not None

    def test_evaluate_token_tier1_fail(self, decision_engine):
        """Test token evaluation when TIER 1 fails."""
        token_data = {
            'symbol': 'BADTOKEN',
            'address': '0x456',
            'price': 0.05,  # Too low
            'liquidity': 75000,
            'security_score': 85,
            'contract_verified': True,
            'volume_24h': 40000,
            'sol_price_usd': 100,
            'top_holder_percent': 15,
        }
        should_trade, details = decision_engine.evaluate_token(token_data)
        assert should_trade is False
        assert details['decision'] == 'REJECT'
        assert details['tier1_passed'] is False
        assert "TIER 1 FAILED" in details['rejection_reason']

    def test_evaluate_token_tier2_fail(self, decision_engine):
        """Test token evaluation when TIER 2 fails."""
        token_data = {
            'symbol': 'OKTOKEN',
            'address': '0x789',
            'price': 0.15,
            'liquidity': 75000,
            'security_score': 85,
            'contract_verified': True,
            'volume_24h': 15000,  # V/L ratio too low (0.2)
            'sol_price_usd': 100,
            'top_holder_percent': 15,
        }
        should_trade, details = decision_engine.evaluate_token(token_data)
        assert should_trade is False
        assert details['decision'] == 'REJECT'
        assert details['tier1_passed'] is True
        assert details['tier2_passed'] is False
        assert "TIER 2 FAILED" in details['rejection_reason']

    def test_position_parameters(self, decision_engine):
        """Test position parameters are correctly set."""
        token_data = {
            'symbol': 'TEST',
            'address': '0xabc',
            'price': 0.20,
            'liquidity': 75000,
            'security_score': 85,
            'contract_verified': True,
            'volume_24h': 40000,
            'sol_price_usd': 100,
            'top_holder_percent': 15,
        }
        should_trade, details = decision_engine.evaluate_token(token_data)
        assert should_trade is True

        params = details['position_params']
        assert params['entry_size_sol'] == 0.1
        assert params['take_profit_percent'] == 15
        assert params['stop_loss_percent'] == 8
        assert params['max_hold_hours'] == 4
        assert params['entry_price'] == 0.20


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
