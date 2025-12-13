"""
Market analysis and volatility assessment.
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
import statistics
from ..monitoring.logger import get_logger

logger = get_logger(__name__)


@dataclass
class MarketSignal:
    """Represents a market signal for trading."""
    token_address: str
    signal_type: str  # 'buy', 'sell', 'hold'
    strength: float  # 0-1
    confidence: float  # 0-1
    reasons: List[str]
    timestamp: datetime
    price: float
    volume_24h: float
    liquidity: float


class MarketAnalyzer:
    """Analyzes market data to generate trading signals."""

    def __init__(
        self,
        min_liquidity_usd: float = 30000,
        max_liquidity_usd: float = 100000,
        min_volume_24h: float = 20000,
        min_volume_liquidity_ratio: float = 0.1,
        max_entry_price: float = 0.001,
        min_tokens_per_dollar: float = 0.1,
        max_tokens_per_dollar: float = 10000,
        # BATCH 9 OPTIMIZATIONS
        min_total_transactions: int = 1000,  # Skip low activity tokens
        min_buy_sell_ratio: float = 0.8,     # Skip dumping tokens
        golden_liq_min: float = 30000,       # Golden range minimum
        golden_liq_max: float = 75000,       # Golden range maximum
        # MOMENTUM FILTERS (455-trade research)
        enable_momentum_filters: bool = True,
        min_price_change_1h: float = 10,
        min_price_change_5min: float = 3,
        min_price_change_1min: float = 1,
        max_price_change_1h: float = 50,
        min_volume_spike_ratio: float = 3.0,
        min_buy_pressure_recent: float = 60,
        require_acceleration: bool = True
    ):
        """
        Initialize market analyzer with 455-TRADE OPTIMIZED filters.

        BATCH 9 + 455-TRADE IMPROVEMENTS (Path to 60%+ win rate):
        - Activity filter: Skip tokens with <1000 txns/hour (+12-15% win rate)
        - Buy/sell ratio: Skip dumping tokens (<0.8 ratio) (+3-5% win rate)
        - Stricter price: Max $0.001 instead of $0.01 (+3-5% win rate)
        - Golden liquidity: Prioritize $30-75k range (+5-8% win rate)
        - Momentum filters: Require climbing tokens (+8-12% win rate)
        - Max liquidity cap: Block $200k+ crowded tokens (+2-4% win rate)

        Args:
            min_liquidity_usd: Minimum liquidity threshold ($30k)
            max_liquidity_usd: Maximum liquidity threshold ($100k - avoid crowded)
            min_volume_24h: Minimum 24h volume ($20k)
            min_volume_liquidity_ratio: Minimum volume/liquidity ratio (0.1 = 10%)
            max_entry_price: Maximum token price ($0.001 max - 455-trade research!)
            min_tokens_per_dollar: Minimum tokens per $1 (avoid expensive)
            max_tokens_per_dollar: Maximum tokens per $1 (avoid worthless)
            min_total_transactions: Minimum total txns in 1h (1000)
            min_buy_sell_ratio: Minimum buy/sell ratio (0.8)
            golden_liq_min: Golden liquidity minimum ($30k)
            golden_liq_max: Golden liquidity maximum ($75k)
            enable_momentum_filters: Enable momentum checks
            min_price_change_1h: Minimum 1h price change (10%)
            min_price_change_5min: Minimum 5min price change (3%)
            min_price_change_1min: Minimum 1min price change (1%)
            max_price_change_1h: Maximum 1h price change (50% - avoid exhausted)
            min_volume_spike_ratio: Minimum 1h/avg volume ratio (3.0x)
            min_buy_pressure_recent: Minimum recent buy pressure (60%)
            require_acceleration: Require accelerating momentum
        """
        # TIER 2 FILTERS
        self.min_liquidity_usd = min_liquidity_usd
        self.max_liquidity_usd = max_liquidity_usd
        self.min_volume_24h = min_volume_24h
        self.min_volume_liquidity_ratio = min_volume_liquidity_ratio
        self.max_entry_price = max_entry_price
        self.min_tokens_per_dollar = min_tokens_per_dollar
        self.max_tokens_per_dollar = max_tokens_per_dollar

        # BATCH 9 OPTIMIZATIONS
        self.min_total_transactions = min_total_transactions
        self.min_buy_sell_ratio = min_buy_sell_ratio
        self.golden_liq_min = golden_liq_min
        self.golden_liq_max = golden_liq_max

        # MOMENTUM FILTERS (455-trade research)
        self.enable_momentum_filters = enable_momentum_filters
        self.min_price_change_1h = min_price_change_1h
        self.min_price_change_5min = min_price_change_5min
        self.min_price_change_1min = min_price_change_1min
        self.max_price_change_1h = max_price_change_1h
        self.min_volume_spike_ratio = min_volume_spike_ratio
        self.min_buy_pressure_recent = min_buy_pressure_recent
        self.require_acceleration = require_acceleration

        self.price_history: Dict[str, List[Dict]] = {}

    def record_price(self, token_address: str, price: float, volume: float):
        """
        Record a price data point.

        Args:
            token_address: Token address
            price: Token price
            volume: Trading volume
        """
        if token_address not in self.price_history:
            self.price_history[token_address] = []

        self.price_history[token_address].append({
            'price': price,
            'volume': volume,
            'timestamp': datetime.now()
        })

        # Keep only last 100 data points per token
        if len(self.price_history[token_address]) > 100:
            self.price_history[token_address] = self.price_history[token_address][-100:]

    def apply_tier2_filters(self, profile: Dict) -> tuple[bool, str]:
        """
        Apply BATCH 9 OPTIMIZED TIER 2 filters - 10 comprehensive binary checks.

        This replaces complex scoring with simple pass/fail filters.
        BATCH 9 adds 4 new filters based on 384-trade analysis.

        Args:
            profile: Token profile with price, liquidity, volume, and transaction data

        Returns:
            Tuple of (should_trade: bool, reason: str)
        """
        liquidity = profile.get('liquidity_usd', 0)
        volume_24h = profile.get('volume_24h', 0)
        price = profile.get('price_usd', 0)

        # === FILTER 1: MINIMUM LIQUIDITY (blocks low-quality tokens) ===
        if liquidity < self.min_liquidity_usd:
            return False, f"TIER2: Liquidity ${liquidity:,.0f} < ${self.min_liquidity_usd:,.0f}"

        # === FILTER 2: MAXIMUM LIQUIDITY (blocks crowded tokens) ===
        # 455-trade research: Winners avg $63k, Losers avg $329k (-80.7%!)
        # $200k+ tokens had only 9.1% win rate
        if liquidity > self.max_liquidity_usd:
            return False, f"TIER2: Liquidity ${liquidity:,.0f} > ${self.max_liquidity_usd:,.0f} - too crowded"

        # === FILTER 3: VOLUME - ZERO CHECK (blocks dead/honeypot tokens) ===
        if volume_24h == 0:
            return False, "TIER2: Zero volume - honeypot/dead token"

        # === FILTER 3: VOLUME - MINIMUM THRESHOLD (blocks inactive tokens) ===
        if volume_24h < self.min_volume_24h:
            return False, f"TIER2: Volume ${volume_24h:,.0f} < ${self.min_volume_24h:,.0f}"

        # === FILTER 4: VOLUME/LIQUIDITY RATIO (blocks wash trading) ===
        ratio = volume_24h / liquidity if liquidity > 0 else 0
        if ratio < self.min_volume_liquidity_ratio:
            return False, f"TIER2: V/L ratio {ratio:.3f} < {self.min_volume_liquidity_ratio} - wash trading"

        # === FILTER 5: PRICE - INVALID/TOO HIGH (blocks expensive tokens) ===
        if price <= 0:
            return False, "TIER2: Invalid price"

        if price > self.max_entry_price:
            return False, f"TIER2: Price ${price:.6f} > ${self.max_entry_price:.2f} - too expensive"

        # === FILTER 6: TOKENS PER DOLLAR RANGE (blocks worthless/overpriced tokens) ===
        tokens_per_dollar = 1 / price if price > 0 else 0

        if tokens_per_dollar < self.min_tokens_per_dollar:
            return False, f"TIER2: Only {tokens_per_dollar:.4f} tokens/$1 - too expensive"

        if tokens_per_dollar > self.max_tokens_per_dollar:
            return False, f"TIER2: {tokens_per_dollar:,.0f} tokens/$1 - worthless token"

        # === BATCH 9 FILTER 7: TRANSACTION ACTIVITY (blocks low activity tokens) ===
        # Analysis showed 32% of trades had <500 txns with only 19.5% win rate
        # Filtering <1000 txns expected to increase win rate by +12-15%
        txns_h1_buys = profile.get('txns_h1_buys', 0)
        txns_h1_sells = profile.get('txns_h1_sells', 0)
        total_txns = txns_h1_buys + txns_h1_sells

        if total_txns < self.min_total_transactions:
            return False, f"TIER2: Only {total_txns} txns/1h < {self.min_total_transactions} - low activity"

        # === BATCH 9 FILTER 8: BUY/SELL RATIO (blocks dumping tokens) ===
        # Analysis showed tokens with <0.8 ratio had only 14.7% win rate
        # Filtering <0.8 expected to increase win rate by +3-5%
        buy_sell_ratio = txns_h1_buys / txns_h1_sells if txns_h1_sells > 0 else 0

        if buy_sell_ratio < self.min_buy_sell_ratio:
            return False, f"TIER2: Buy/sell ratio {buy_sell_ratio:.2f} < {self.min_buy_sell_ratio} - dumping"

        # === BATCH 9 FILTER 9 & 10: GOLDEN LIQUIDITY PRIORITY ===
        # Analysis showed $30-75k liquidity had 40.8% win rate (best range!)
        # This doesn't block, but will be used for prioritization
        in_golden_range = self.golden_liq_min <= liquidity <= self.golden_liq_max

        # === 455-TRADE MOMENTUM FILTERS (Reduce no-momentum 50% → 30%) ===
        # Research: 50.4% no momentum (1.8% win) vs 30.1% runners (94.1% win)
        # Max gain difference: 1036% (61.8% vs 5.4%)!
        if self.enable_momentum_filters:
            # FILTER 11: 1H PRICE CHANGE - Must be climbing
            price_change_1h = profile.get('price_change_h1', 0)
            if price_change_1h < self.min_price_change_1h:
                return False, f"TIER2: Price change 1h {price_change_1h:.1f}% < {self.min_price_change_1h}% - not climbing"

            # FILTER 12: 1H PRICE CHANGE - Not exhausted
            if price_change_1h > self.max_price_change_1h:
                return False, f"TIER2: Price change 1h {price_change_1h:.1f}% > {self.max_price_change_1h}% - exhausted"

            # FILTER 13: 5MIN PRICE CHANGE - Recent momentum required
            price_change_5m = profile.get('price_change_m5', 0)
            if price_change_5m < self.min_price_change_5min:
                return False, f"TIER2: Price change 5min {price_change_5m:.1f}% < {self.min_price_change_5min}% - no recent momentum"

            # FILTER 14: 1MIN PRICE CHANGE - Active climbing required
            price_change_1m = profile.get('price_change_m1', 0)
            if price_change_1m < self.min_price_change_1min:
                return False, f"TIER2: Price change 1min {price_change_1m:.1f}% < {self.min_price_change_1min}% - not actively climbing"

            # FILTER 15: VOLUME SPIKE - High activity required
            volume_1h = profile.get('volume_1h', 0)
            volume_24h_avg_hourly = volume_24h / 24 if volume_24h > 0 else 0
            volume_spike_ratio = volume_1h / volume_24h_avg_hourly if volume_24h_avg_hourly > 0 else 0
            if volume_spike_ratio < self.min_volume_spike_ratio:
                return False, f"TIER2: Volume spike ratio {volume_spike_ratio:.1f}x < {self.min_volume_spike_ratio}x - low activity"

            # FILTER 16: BUY PRESSURE - Recent buying required
            # Calculate recent buy pressure from last 10min of transactions
            buys_recent = profile.get('txns_m5_buys', txns_h1_buys / 12)  # Fallback to 5min estimate
            sells_recent = profile.get('txns_m5_sells', txns_h1_sells / 12)
            total_recent = buys_recent + sells_recent
            buy_pressure = (buys_recent / total_recent * 100) if total_recent > 0 else 0
            if buy_pressure < self.min_buy_pressure_recent:
                return False, f"TIER2: Recent buy pressure {buy_pressure:.1f}% < {self.min_buy_pressure_recent}% - weak buying"

            # FILTER 17: ACCELERATION - Momentum must be increasing (optional)
            if self.require_acceleration:
                # Check if 1min > 5min > 1h momentum rate (accelerating)
                # Rate = % change / time period
                rate_1m = price_change_1m / 1
                rate_5m = price_change_5m / 5
                rate_1h = price_change_1h / 60
                if not (rate_1m >= rate_5m >= rate_1h):
                    return False, f"TIER2: Momentum not accelerating (1m:{rate_1m:.2f} 5m:{rate_5m:.2f} 1h:{rate_1h:.2f})"

        # === ALL FILTERS PASSED ===
        golden_emoji = "🌟" if in_golden_range else "✅"
        momentum_emoji = "🚀" if self.enable_momentum_filters else ""
        logger.info(
            f"TIER2: {golden_emoji}{momentum_emoji} PASS - Liq ${liquidity:,.0f}{' (GOLDEN!)' if in_golden_range else ''}, "
            f"Vol ${volume_24h:,.0f}, "
            f"V/L {ratio:.2f}, "
            f"Price ${price:.6f}, "
            f"{tokens_per_dollar:.2f} tokens/$1, "
            f"{total_txns} txns, "
            f"B/S {buy_sell_ratio:.2f}"
        )
        return True, f"TIER2: {golden_emoji}{momentum_emoji} All checks passed{' - GOLDEN RANGE!' if in_golden_range else ''}"

    def analyze_token(self, profile: Dict) -> MarketSignal:
        """
        Analyze a token using SIMPLIFIED BINARY TIER 2 filters.

        Replaces complex scoring with simple pass/fail logic.

        Args:
            profile: Token profile from DexScreener

        Returns:
            MarketSignal with binary buy/hold decision
        """
        token_address = profile.get('address', '')
        price = profile.get('price_usd', 0)
        volume_24h = profile.get('volume_24h', 0)
        liquidity = profile.get('liquidity_usd', 0)

        # === APPLY TIER 2 FILTERS (BINARY PASS/FAIL) ===
        should_trade, reason = self.apply_tier2_filters(profile)

        if should_trade:
            # PASSED ALL FILTERS → BUY SIGNAL
            signal_type = 'buy'
            strength = 1.0  # Binary: either buy (1.0) or don't
            confidence = 0.8  # High confidence when filters pass
            reasons = [reason]  # "TIER2: ✅ All checks passed"
        else:
            # FAILED FILTER → HOLD
            signal_type = 'hold'
            strength = 0.0
            confidence = 0.2  # Low confidence, don't trade
            reasons = [reason]  # Specific failure reason from filter

        return MarketSignal(
            token_address=token_address,
            signal_type=signal_type,
            strength=strength,
            confidence=confidence,
            reasons=reasons,
            timestamp=datetime.now(),
            price=price,
            volume_24h=volume_24h,
            liquidity=liquidity
        )

    def calculate_volatility(self, token_address: str) -> float:
        """
        Calculate price volatility for a token.

        Args:
            token_address: Token address

        Returns:
            Volatility score (standard deviation of returns)
        """
        if token_address not in self.price_history:
            return 0.0

        history = self.price_history[token_address]
        if len(history) < 2:
            return 0.0

        # Calculate returns
        returns = []
        for i in range(1, len(history)):
            prev_price = history[i-1]['price']
            curr_price = history[i]['price']
            if prev_price > 0:
                return_pct = (curr_price - prev_price) / prev_price
                returns.append(return_pct)

        if not returns:
            return 0.0

        # Return standard deviation of returns
        return statistics.stdev(returns) if len(returns) > 1 else 0.0

    def get_price_trend(self, token_address: str, periods: int = 10) -> str:
        """
        Determine price trend direction.

        Args:
            token_address: Token address
            periods: Number of periods to analyze

        Returns:
            'uptrend', 'downtrend', or 'sideways'
        """
        if token_address not in self.price_history:
            return 'unknown'

        history = self.price_history[token_address][-periods:]
        if len(history) < 2:
            return 'unknown'

        prices = [h['price'] for h in history]
        first_price = prices[0]
        last_price = prices[-1]

        change_pct = ((last_price - first_price) / first_price * 100) if first_price > 0 else 0

        if change_pct > 5:
            return 'uptrend'
        elif change_pct < -5:
            return 'downtrend'
        else:
            return 'sideways'

    def calculate_risk_score(self, profile: Dict) -> float:
        """
        Calculate risk score for a token (0=low risk, 1=high risk).

        Args:
            profile: Token profile

        Returns:
            Risk score between 0 and 1
        """
        risk_score = 0.0

        # Liquidity risk
        liquidity = profile['liquidity_usd']
        if liquidity < 10000:
            risk_score += 0.4
        elif liquidity < 50000:
            risk_score += 0.2
        elif liquidity < 100000:
            risk_score += 0.1

        # Volatility risk
        token_address = profile['address']
        volatility = self.calculate_volatility(token_address)
        if volatility > 0.1:  # >10% volatility
            risk_score += 0.3
        elif volatility > 0.05:  # >5% volatility
            risk_score += 0.15

        # Age risk (newer pairs are riskier)
        pair_created_at = profile.get('pair_created_at')
        if pair_created_at:
            try:
                created_date = datetime.fromtimestamp(pair_created_at / 1000)
                age_hours = (datetime.now() - created_date).total_seconds() / 3600
                if age_hours < 24:
                    risk_score += 0.3
                elif age_hours < 72:
                    risk_score += 0.15
            except Exception:
                risk_score += 0.2

        return min(risk_score, 1.0)

    def should_trade(self, signal: MarketSignal, min_confidence: float = 0.7) -> bool:
        """
        Determine if a signal warrants trading action.

        Args:
            signal: Market signal to evaluate
            min_confidence: Minimum confidence threshold

        Returns:
            True if should trade, False otherwise
        """
        if signal.signal_type == 'hold':
            return False

        if signal.confidence < min_confidence:
            return False

        if signal.liquidity < self.min_liquidity_usd:
            return False

        return True

    def calculate_golden_liquidity_score(self, liquidity: float) -> float:
        """
        Calculate priority score based on proximity to golden liquidity range.

        BATCH 9 Analysis: $30-50k liquidity = 43.3% win rate (best range!)
        This score prioritizes tokens in the golden range.

        Args:
            liquidity: Token liquidity in USD

        Returns:
            Score 0-1 (1.0 = perfect golden range, <1.0 = outside range)
        """
        # Perfect score for golden range
        if self.golden_liq_min <= liquidity <= self.golden_liq_max:
            # Within range: score based on how centered it is
            mid_point = (self.golden_liq_min + self.golden_liq_max) / 2
            distance_from_center = abs(liquidity - mid_point)
            max_distance = (self.golden_liq_max - self.golden_liq_min) / 2
            return 1.0 - (distance_from_center / max_distance) * 0.2  # 0.8-1.0 range

        # Below golden range: penalize more as it gets lower
        elif liquidity < self.golden_liq_min:
            # Score drops as distance from golden_liq_min increases
            distance = self.golden_liq_min - liquidity
            max_distance = self.golden_liq_min - self.min_liquidity_usd
            if max_distance > 0:
                penalty = min(distance / max_distance, 1.0) * 0.4
                return 0.6 - penalty  # 0.2-0.6 range
            return 0.6

        # Above golden range: smaller penalty (high liquidity is safer)
        else:
            # Score drops slowly as liquidity increases beyond golden range
            distance = liquidity - self.golden_liq_max
            max_distance = self.golden_liq_max * 2  # Arbitrary: 2x golden_liq_max
            if max_distance > 0:
                penalty = min(distance / max_distance, 1.0) * 0.3
                return 0.7 - penalty  # 0.4-0.7 range
            return 0.7
