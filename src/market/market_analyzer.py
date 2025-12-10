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
        min_liquidity_usd: float = 40000,
        min_volume_24h: float = 20000,
        min_volume_liquidity_ratio: float = 0.1,
        max_entry_price: float = 0.01,  # BATCH 9: Stricter $0.01 limit
        min_tokens_per_dollar: float = 0.1,
        max_tokens_per_dollar: float = 10000,
        # BATCH 9 OPTIMIZATIONS
        min_total_transactions: int = 1000,  # Skip low activity tokens
        min_buy_sell_ratio: float = 0.8,     # Skip dumping tokens
        golden_liq_min: float = 30000,       # Golden range minimum
        golden_liq_max: float = 50000        # Golden range maximum
    ):
        """
        Initialize market analyzer with BATCH 9 OPTIMIZED TIER 2 filters.

        BATCH 9 IMPROVEMENTS (Expected +30% win rate):
        - Activity filter: Skip tokens with <1000 txns/hour (+12-15% win rate)
        - Buy/sell ratio: Skip dumping tokens (<0.8 ratio) (+3-5% win rate)
        - Stricter price: Max $0.01 instead of $10 (+3-5% win rate)
        - Golden liquidity: Prioritize $30-50k range (+5-8% win rate)

        Args:
            min_liquidity_usd: Minimum liquidity threshold in USD ($40k default)
            min_volume_24h: Minimum 24h volume threshold in USD ($20k default)
            min_volume_liquidity_ratio: Minimum volume/liquidity ratio (0.1 = 10% turnover)
            max_entry_price: Maximum token price for entry ($0.01 max - BATCH 9 stricter!)
            min_tokens_per_dollar: Minimum tokens per $1 (0.1 = avoid expensive tokens)
            max_tokens_per_dollar: Maximum tokens per $1 (10k = avoid worthless tokens)
            min_total_transactions: Minimum total txns in 1h (1000 = active tokens only)
            min_buy_sell_ratio: Minimum buy/sell ratio (0.8 = avoid dumps)
            golden_liq_min: Golden liquidity range start ($30k)
            golden_liq_max: Golden liquidity range end ($50k)
        """
        # OPTION B: 6 ORIGINAL FILTERS
        self.min_liquidity_usd = min_liquidity_usd
        self.min_volume_24h = min_volume_24h
        self.min_volume_liquidity_ratio = min_volume_liquidity_ratio
        self.max_entry_price = max_entry_price
        self.min_tokens_per_dollar = min_tokens_per_dollar
        self.max_tokens_per_dollar = max_tokens_per_dollar

        # BATCH 9: 4 NEW OPTIMIZATION FILTERS
        self.min_total_transactions = min_total_transactions
        self.min_buy_sell_ratio = min_buy_sell_ratio
        self.golden_liq_min = golden_liq_min
        self.golden_liq_max = golden_liq_max

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

        # === FILTER 1: LIQUIDITY (blocks low-quality tokens) ===
        if liquidity < self.min_liquidity_usd:
            return False, f"TIER2: Liquidity ${liquidity:,.0f} < ${self.min_liquidity_usd:,.0f}"

        # === FILTER 2: VOLUME - ZERO CHECK (blocks dead/honeypot tokens) ===
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
        # Analysis showed $30-50k liquidity had 43.3% win rate (best range!)
        # This doesn't block, but will be used for prioritization
        in_golden_range = self.golden_liq_min <= liquidity <= self.golden_liq_max

        # === ALL FILTERS PASSED ===
        golden_emoji = "🌟" if in_golden_range else "✅"
        logger.info(
            f"TIER2: {golden_emoji} PASS - Liq ${liquidity:,.0f}{' (GOLDEN!)' if in_golden_range else ''}, "
            f"Vol ${volume_24h:,.0f}, "
            f"V/L {ratio:.2f}, "
            f"Price ${price:.6f}, "
            f"{tokens_per_dollar:.2f} tokens/$1, "
            f"{total_txns} txns, "
            f"B/S {buy_sell_ratio:.2f}"
        )
        return True, f"TIER2: {golden_emoji} All checks passed{' - GOLDEN RANGE!' if in_golden_range else ''}"

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
