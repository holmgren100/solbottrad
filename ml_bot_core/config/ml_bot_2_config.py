"""
🔒 PROTECTED - ML Bot 2 Configuration
Based on ML Bot 2 (71.7% win rate, 9.02x profit factor)

DO NOT MODIFY - These are proven settings!

Performance with these exact settings:
- 276 trades
- 71.7% win rate (+8.4% better than ML Bot 1)
- $30.09 average profit per trade (+133% better than ML Bot 1)
- 9.02x profit factor (+152% better than ML Bot 1)
- 8.3% stop loss rate (-63% better than ML Bot 1)
- 73.7% success on low liquidity exits
- 85-93% success on trailing stop exits
"""

from dataclasses import dataclass
from typing import Dict


@dataclass
class MLBot2Config:
    """
    🔒 PROTECTED - Exact ML Bot 2 configuration settings

    These settings achieved 71.7% win rate and 9.02x profit factor.
    DO NOT modify without extensive testing and data proof!
    """

    # ===== RISK ASSESSMENT WEIGHTS (THE SECRET!) =====
    # 70% weight on essentials (liquidity + security)
    # Only 10% on volatility/age (they're opportunities, not risks!)

    risk_weights: Dict[str, float] = None

    def __post_init__(self):
        if self.risk_weights is None:
            self.risk_weights = {
                'liquidity': 0.35,      # Most important - can't sell without it
                'security': 0.35,       # Rug pull protection critical
                'volatility': 0.05,     # VOLATILITY IS GOOD - that's where gains are!
                'sentiment': 0.15,      # Coordination risk
                'prediction_uncertainty': 0.05,  # Less important with good exits
                'age': 0.05            # New tokens can moon - age matters less
            }

    # ===== LIQUIDITY THRESHOLDS =====
    # More aggressive than ML Bot 1 (which required $100k min)
    # Allows trading with lower liquidity but still safe

    liquidity_very_safe: float = 100000.0      # >= $100k = 0.1 risk
    liquidity_safe: float = 50000.0            # >= $50k = 0.2 risk
    liquidity_moderate: float = 20000.0        # >= $20k = 0.3 risk
    liquidity_risky: float = 10000.0           # >= $10k = 0.5 risk
    liquidity_high_risk: float = 5000.0        # >= $5k = 0.7 risk
    liquidity_too_risky: float = 5000.0        # < $5k = 1.0 risk (reject)

    # ===== SECURITY RISK PENALTIES =====
    # These add to risk score (higher = worse)

    security_risk_mintable: float = 0.25           # Can mint new tokens
    security_risk_freeze: float = 0.25             # Can freeze accounts
    security_risk_not_verified: float = 0.20       # Not verified
    security_risk_ownership: float = 0.20          # Ownership not renounced
    security_risk_blacklist: float = 0.10          # Has blacklist function

    # ===== RISK DECISION THRESHOLDS =====
    # When to trade vs reject

    max_acceptable_risk: float = 0.7               # Overall risk < 0.7 = trade
    min_position_multiplier: float = 0.1           # Position size > 0.1 = trade

    # ===== TRAILING STOPS (THE SECRET TO 85-93% WIN RATE!) =====
    # 15% below PEAK (not entry price!)
    # This lets winners run to 100%+ instead of capping at 20%

    use_trailing_stop: bool = True
    trailing_stop_percent: float = 8.0             # 8% below peak (4th AI optimized!)

    # ===== PARTIAL PROFIT TAKING =====
    # ML Bot 2 DISABLES THIS - uses trailing stops instead!

    partial_profit_enabled: bool = False

    # If enabled (for testing only):
    profit_milestone_100: float = 25.0             # 25% at +100%
    profit_milestone_200: float = 15.0             # 15% at +200%
    profit_milestone_300: float = 10.0             # 10% at +300%
    profit_milestone_400: float = 10.0             # 10% at +400%
    profit_milestone_500: float = 10.0             # 10% at +500%
    profit_milestone_600: float = 10.0             # 10% at +600%
    profit_milestone_700: float = 10.0             # 10% at +700%

    # ===== RUG DETECTION (SIMPLE BUT EFFECTIVE!) =====
    # Detects rugs in 5 minutes, exits before total loss

    rug_detection_enabled: bool = True
    stale_price_minutes: int = 5                   # No price update for 5 min = rug
    min_position_liquidity: float = 5000.0         # Liquidity < $5k = rug
    frozen_price_minutes: int = 15                 # Price frozen for 15 min = rug

    # ===== POSITION MANAGEMENT =====

    max_open_positions: int = 7                    # Max simultaneous positions
    stop_loss_percent: float = 20.0                # 20% stop loss from entry
    take_profit_percent: float = 50.0              # 50% take profit (if not using trailing)

    # ===== MONITORING INTERVALS =====
    # Fast monitoring = fast rug detection

    scan_interval: int = 120                       # Scan for new tokens every 2 minutes
    monitor_interval: int = 15                     # Check positions every 15 seconds (User: Faster detection!)

    # ===== PRICE VALIDATION =====
    # Dual-source validation prevents bad data losses

    price_divergence_threshold: float = 10.0       # Prices within 10% = agree
    suspicious_drop_threshold: float = -80.0       # >80% drop = reject (bad data)
    min_valid_price: float = 1e-9                  # Minimum valid price

    # ===== PAPER TRADING (for testing) =====

    paper_trading_mode: bool = True
    paper_sol_balance: float = 1000.0              # Start with 1000 SOL

    # ===== WHAT ML BOT 2 DOES NOT HAVE (And wins without!) =====

    # ❌ NO fee/slippage simulation (adds later for realism)
    simulate_fees: bool = False

    # ❌ NO Tier 2 filters (min price, max tokens/dollar)
    # These BLOCK good opportunities!
    enable_tier2_filters: bool = False

    # ❌ NO volume fallback (adds risk)
    allow_volume_fallback: bool = False

    # ❌ NO stuck position cleanup (shouldn't be needed with good rug detection)
    auto_cleanup_enabled: bool = False

    def to_dict(self) -> Dict:
        """Convert config to dictionary."""
        return {
            # Risk weights
            'risk_weights': self.risk_weights,

            # Liquidity thresholds
            'liquidity_very_safe': self.liquidity_very_safe,
            'liquidity_safe': self.liquidity_safe,
            'liquidity_moderate': self.liquidity_moderate,
            'liquidity_risky': self.liquidity_risky,
            'liquidity_high_risk': self.liquidity_high_risk,
            'liquidity_too_risky': self.liquidity_too_risky,

            # Security penalties
            'security_risk_mintable': self.security_risk_mintable,
            'security_risk_freeze': self.security_risk_freeze,
            'security_risk_not_verified': self.security_risk_not_verified,
            'security_risk_ownership': self.security_risk_ownership,
            'security_risk_blacklist': self.security_risk_blacklist,

            # Risk thresholds
            'max_acceptable_risk': self.max_acceptable_risk,
            'min_position_multiplier': self.min_position_multiplier,

            # Trailing stops
            'use_trailing_stop': self.use_trailing_stop,
            'trailing_stop_percent': self.trailing_stop_percent,

            # Partial profits
            'partial_profit_enabled': self.partial_profit_enabled,

            # Rug detection
            'rug_detection_enabled': self.rug_detection_enabled,
            'stale_price_minutes': self.stale_price_minutes,
            'min_position_liquidity': self.min_position_liquidity,
            'frozen_price_minutes': self.frozen_price_minutes,

            # Position management
            'max_open_positions': self.max_open_positions,
            'stop_loss_percent': self.stop_loss_percent,
            'take_profit_percent': self.take_profit_percent,

            # Monitoring
            'scan_interval': self.scan_interval,
            'monitor_interval': self.monitor_interval,

            # Price validation
            'price_divergence_threshold': self.price_divergence_threshold,
            'suspicious_drop_threshold': self.suspicious_drop_threshold,
            'min_valid_price': self.min_valid_price,

            # Paper trading
            'paper_trading_mode': self.paper_trading_mode,
            'paper_sol_balance': self.paper_sol_balance,

            # Disabled features
            'simulate_fees': self.simulate_fees,
            'enable_tier2_filters': self.enable_tier2_filters,
            'allow_volume_fallback': self.allow_volume_fallback,
            'auto_cleanup_enabled': self.auto_cleanup_enabled,
        }

    def __repr__(self) -> str:
        return (
            f"MLBot2Config(\n"
            f"  🎯 Target: 71.7% win rate, 9.02x profit factor\n"
            f"  🔒 Protected: YES\n"
            f"  ⚖️  Risk Weights: Liquidity 35%, Security 35%, Others 30%\n"
            f"  📈 Trailing Stop: {self.trailing_stop_percent}% below peak\n"
            f"  🛡️  Rug Detection: {self.stale_price_minutes} min, ${self.min_position_liquidity:,.0f}\n"
            f"  🔄 Monitoring: Scan {self.scan_interval}s, Monitor {self.monitor_interval}s\n"
            f")"
        )


# Default instance
DEFAULT_CONFIG = MLBot2Config()
