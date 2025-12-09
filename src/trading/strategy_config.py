"""
Strategy configuration based on token age.
Different profit-taking strategies for different token types.
"""

import os
from dataclasses import dataclass
from typing import Dict
from datetime import datetime
from ..monitoring.logger import get_logger

logger = get_logger(__name__)


@dataclass
class StrategyProfile:
    """Profit-taking strategy profile for a token type."""
    name: str
    age_range_hours: tuple  # (min_hours, max_hours)

    # Profit milestones (percentage of initial position to sell at each level)
    milestone_50: float = 0.0
    milestone_100: float = 0.0
    milestone_150: float = 0.0
    milestone_200: float = 0.0
    milestone_300: float = 0.0
    milestone_400: float = 0.0
    milestone_500: float = 0.0
    milestone_600: float = 0.0
    milestone_700: float = 0.0

    # Trailing stop configuration
    trailing_stop_percent: float = 10.0

    # Risk adjustment
    position_size_multiplier: float = 1.0  # Adjust position size based on risk

    def get_milestone_percentage(self, milestone: int) -> float:
        """Get sell percentage for a specific milestone."""
        milestone_map = {
            50: self.milestone_50,
            100: self.milestone_100,
            150: self.milestone_150,
            200: self.milestone_200,
            300: self.milestone_300,
            400: self.milestone_400,
            500: self.milestone_500,
            600: self.milestone_600,
            700: self.milestone_700
        }
        return milestone_map.get(milestone, 0.0)


class StrategySelector:
    """Select appropriate trading strategy based on token characteristics."""

    def __init__(self):
        """Initialize strategy selector with default strategies."""

        # Strategy 1: NEW/FRESH TOKENS (0-6 hours)
        # High risk, high reward - take profits aggressively
        self.new_tokens = StrategyProfile(
            name='new_tokens',
            age_range_hours=(0, 6),
            milestone_100=float(os.getenv('STRATEGY_NEW_MILESTONE_100', '20')),
            milestone_200=float(os.getenv('STRATEGY_NEW_MILESTONE_200', '25')),
            milestone_300=float(os.getenv('STRATEGY_NEW_MILESTONE_300', '20')),
            milestone_400=float(os.getenv('STRATEGY_NEW_MILESTONE_400', '15')),
            milestone_500=float(os.getenv('STRATEGY_NEW_MILESTONE_500', '10')),
            trailing_stop_percent=float(os.getenv('STRATEGY_NEW_TRAILING_STOP', '15')),
            position_size_multiplier=float(os.getenv('STRATEGY_NEW_POSITION_MULTIPLIER', '0.8'))  # Slightly smaller for risk
        )

        # Strategy 2: ESTABLISHED TOKENS (6 hours - 3 days)
        # Medium risk - balanced approach (current bot settings)
        self.established = StrategyProfile(
            name='established',
            age_range_hours=(6, 72),  # 6h to 3 days
            milestone_100=float(os.getenv('STRATEGY_MED_MILESTONE_100', '15')),
            milestone_200=float(os.getenv('STRATEGY_MED_MILESTONE_200', '20')),
            milestone_300=float(os.getenv('STRATEGY_MED_MILESTONE_300', '15')),
            milestone_400=float(os.getenv('STRATEGY_MED_MILESTONE_400', '10')),
            milestone_500=float(os.getenv('STRATEGY_MED_MILESTONE_500', '10')),
            milestone_600=float(os.getenv('STRATEGY_MED_MILESTONE_600', '10')),
            milestone_700=float(os.getenv('STRATEGY_MED_MILESTONE_700', '10')),
            trailing_stop_percent=float(os.getenv('STRATEGY_MED_TRAILING_STOP', '15')),
            position_size_multiplier=1.0  # Normal size
        )

        # Strategy 3: MATURE TOKENS (3-7 days)
        # Lower risk - conservative, take profits earlier
        self.mature = StrategyProfile(
            name='mature',
            age_range_hours=(72, 168),  # 3 to 7 days
            milestone_50=float(os.getenv('STRATEGY_MATURE_MILESTONE_50', '30')),
            milestone_100=float(os.getenv('STRATEGY_MATURE_MILESTONE_100', '30')),
            milestone_150=float(os.getenv('STRATEGY_MATURE_MILESTONE_150', '30')),
            milestone_200=float(os.getenv('STRATEGY_MATURE_MILESTONE_200', '10')),
            trailing_stop_percent=float(os.getenv('STRATEGY_MATURE_TRAILING_STOP', '8')),
            position_size_multiplier=float(os.getenv('STRATEGY_MATURE_POSITION_MULTIPLIER', '1.2'))  # Larger for safety
        )

        # Strategy 4: STABLE TOKENS (7+ days)
        # Very low risk - very conservative, tight stops
        self.stable = StrategyProfile(
            name='stable',
            age_range_hours=(168, float('inf')),  # 7+ days
            milestone_50=float(os.getenv('STRATEGY_STABLE_MILESTONE_50', '40')),
            milestone_100=float(os.getenv('STRATEGY_STABLE_MILESTONE_100', '40')),
            milestone_150=float(os.getenv('STRATEGY_STABLE_MILESTONE_150', '20')),
            trailing_stop_percent=float(os.getenv('STRATEGY_STABLE_TRAILING_STOP', '5')),
            position_size_multiplier=float(os.getenv('STRATEGY_STABLE_POSITION_MULTIPLIER', '1.5'))  # Largest for safety
        )

        # All strategies
        self.strategies = [
            self.new_tokens,
            self.established,
            self.mature,
            self.stable
        ]

        logger.info("🎯 Strategy selector initialized with 4 profiles")
        logger.info(f"  - New Tokens (0-6h): {self.new_tokens.trailing_stop_percent}% trailing")
        logger.info(f"  - Established (6h-3d): {self.established.trailing_stop_percent}% trailing")
        logger.info(f"  - Mature (3-7d): {self.mature.trailing_stop_percent}% trailing")
        logger.info(f"  - Stable (7+d): {self.stable.trailing_stop_percent}% trailing")

    def select_strategy(self, pair_created_at: int) -> StrategyProfile:
        """
        Select appropriate strategy based on token age.

        Args:
            pair_created_at: Unix timestamp when pair was created (seconds or milliseconds)

        Returns:
            StrategyProfile for this token
        """
        # Handle invalid timestamps
        if pair_created_at <= 0:
            logger.warning(f"⚠️ Invalid timestamp {pair_created_at}, using established strategy")
            return self.established

        # Calculate token age in hours
        current_time = int(datetime.now().timestamp())

        # DexScreener returns timestamps in milliseconds, convert to seconds if needed
        # Unix timestamp in seconds is ~1.7 billion (10 digits)
        # Unix timestamp in milliseconds is ~1.7 trillion (13 digits)
        if pair_created_at > 10000000000:  # More than 10 digits = milliseconds
            pair_created_at_seconds = pair_created_at // 1000
            logger.debug(f"Converted timestamp from ms to seconds: {pair_created_at} -> {pair_created_at_seconds}")
        else:
            pair_created_at_seconds = pair_created_at

        age_seconds = current_time - pair_created_at_seconds
        age_hours = age_seconds / 3600

        # Sanity check: age should be positive and reasonable (< 1 year)
        if age_hours < 0 or age_hours > 8760:  # 8760 hours = 1 year
            logger.warning(
                f"⚠️ Unrealistic token age {age_hours:.1f}h "
                f"(created_at: {pair_created_at}, current: {current_time}), using established strategy"
            )
            return self.established

        # Select strategy based on age
        for strategy in self.strategies:
            min_hours, max_hours = strategy.age_range_hours
            if min_hours <= age_hours < max_hours:
                logger.info(
                    f"📊 Selected strategy: {strategy.name} "
                    f"(token age: {age_hours:.1f}h)"
                )
                return strategy

        # Default to established if no match
        logger.warning(f"⚠️ Could not determine strategy for age {age_hours:.1f}h, using established")
        return self.established

    def get_strategy_by_name(self, name: str) -> StrategyProfile:
        """Get strategy by name."""
        for strategy in self.strategies:
            if strategy.name == name:
                return strategy
        return self.established

    def get_all_strategies(self) -> Dict[str, StrategyProfile]:
        """Get all strategies as dictionary."""
        return {s.name: s for s in self.strategies}
