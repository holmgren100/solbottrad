"""
Paper trading engine for testing strategies without real funds.
Now includes Jupiter + Jito simulation for realistic execution modeling.
"""

from typing import Dict, Optional
from datetime import datetime
import json
import os
import uuid
from .position_manager import PositionManager, Trade, Position
from .strategy_config import StrategySelector, StrategyProfile
from .token_tracker import TokenPerformanceTracker
from .token_filter import TokenFilter
from ..blockchain.jupiter_executor import JupiterSwapExecutor
from ..monitoring.logger import get_logger

logger = get_logger(__name__)

# For ML data collection - will be set by main bot
_ml_collector = None
_trade_contexts = {}  # Store analysis context for each trade


def set_ml_collector(collector):
    """Set the ML data collector (called by main bot)."""
    global _ml_collector
    _ml_collector = collector


class PaperTradingEngine:
    """Simulated trading engine for testing."""

    def __init__(self, initial_capital: float = 1000.0, state_file: str = 'paper_trading_state.json'):
        """
        Initialize paper trading engine.

        Args:
            initial_capital: Starting capital in USD
            state_file: Path to state file for persistence
        """
        # Read rug detection settings from environment
        self.rug_detection_enabled = os.getenv('RUG_DETECTION_ENABLED', 'true').lower() == 'true'
        self.stale_price_minutes = float(os.getenv('STALE_PRICE_MINUTES', '2'))
        self.frozen_price_minutes = float(os.getenv('FROZEN_PRICE_MINUTES', '15'))
        self.min_position_liquidity = float(os.getenv('MIN_POSITION_LIQUIDITY', '5000.0'))

        # BATCH 10 FIX + 455-TRADE OPTIMIZATION: Early liquidity drop detection
        # Analysis showed 100% of trades ended with 0 exit liquidity - exit earlier!
        # 455-trade research: Tighten from 50% to 30% for faster exits
        self.liquidity_drop_threshold = float(os.getenv('LIQUIDITY_DROP_THRESHOLD', '30.0'))  # Exit if liq drops >30%
        self.enable_liquidity_monitoring = os.getenv('ENABLE_LIQUIDITY_MONITORING', 'true').lower() == 'true'

        # 455-TRADE OPTIMIZATION: LP Lock & Rug Prevention
        self.enable_lp_lock_check = os.getenv('ENABLE_LP_LOCK_CHECK', 'true').lower() == 'true'
        self.min_lp_lock_days = int(os.getenv('MIN_LP_LOCK_DAYS', '30'))
        self.allow_lp_burned = os.getenv('ALLOW_LP_BURNED', 'true').lower() == 'true'
        self.skip_unlocked_lp = os.getenv('SKIP_UNLOCKED_LP', 'true').lower() == 'true'

        # 455-TRADE OPTIMIZATION: Holder Concentration
        self.enable_holder_check = os.getenv('ENABLE_HOLDER_CHECK', 'true').lower() == 'true'
        self.max_top_10_concentration = float(os.getenv('MAX_TOP_10_CONCENTRATION', '50'))
        self.max_top_1_concentration = float(os.getenv('MAX_TOP_1_CONCENTRATION', '20'))
        self.max_dev_wallet = float(os.getenv('MAX_DEV_WALLET', '10'))

        # 455-TRADE OPTIMIZATION: Contract Safety
        self.block_mint_authority = os.getenv('BLOCK_MINT_AUTHORITY', 'true').lower() == 'true'
        self.block_freeze_authority = os.getenv('BLOCK_FREEZE_AUTHORITY', 'true').lower() == 'true'
        self.require_renounced = os.getenv('REQUIRE_RENOUNCED', 'false').lower() == 'true'

        # 455-TRADE OPTIMIZATION: Position Sizing Multipliers
        self.prefer_golden_range = os.getenv('PREFER_GOLDEN_RANGE', 'true').lower() == 'true'
        self.golden_range_multiplier = float(os.getenv('GOLDEN_RANGE_MULTIPLIER', '1.2'))
        self.golden_liq_min = float(os.getenv('GOLDEN_LIQUIDITY_MIN', '30000'))
        self.golden_liq_max = float(os.getenv('GOLDEN_LIQUIDITY_MAX', '75000'))
        self.preferred_price_max = float(os.getenv('PREFERRED_PRICE_MAX', '0.0005'))
        self.preferred_price_multiplier = float(os.getenv('PREFERRED_PRICE_MULTIPLIER', '1.3'))

        # Read trailing stop settings from environment
        self.use_trailing_stop = os.getenv('USE_TRAILING_STOP', 'true').lower() == 'true'
        self.trailing_stop_percent = float(os.getenv('TRAILING_STOP_PERCENT', '10.0'))
        self.trailing_stop_activation = float(os.getenv('TRAILING_STOP_ACTIVATION', '5.0'))  # Activation threshold

        # Read partial profit taking settings from environment
        self.partial_profit_enabled = os.getenv('PARTIAL_PROFIT_ENABLED', 'false').lower() == 'true'
        self.profit_milestone_100 = float(os.getenv('PROFIT_MILESTONE_100', '25'))
        self.profit_milestone_200 = float(os.getenv('PROFIT_MILESTONE_200', '15'))
        self.profit_milestone_300 = float(os.getenv('PROFIT_MILESTONE_300', '10'))
        self.profit_milestone_400 = float(os.getenv('PROFIT_MILESTONE_400', '10'))
        self.profit_milestone_500 = float(os.getenv('PROFIT_MILESTONE_500', '10'))
        self.profit_milestone_600 = float(os.getenv('PROFIT_MILESTONE_600', '10'))
        self.profit_milestone_700 = float(os.getenv('PROFIT_MILESTONE_700', '10'))

        # Fee and slippage simulation (realistic trading costs)
        self.simulate_fees = os.getenv('SIMULATE_FEES', 'true').lower() == 'true'
        self.buy_fee_percent = float(os.getenv('BUY_FEE_PERCENT', '0.3'))      # Jupiter + network fees
        self.sell_fee_percent = float(os.getenv('SELL_FEE_PERCENT', '0.3'))    # Jupiter + network fees
        self.buy_slippage_percent = float(os.getenv('BUY_SLIPPAGE_PERCENT', '0.5'))    # Entry slippage
        self.sell_slippage_percent = float(os.getenv('SELL_SLIPPAGE_PERCENT', '1.0'))  # Exit slippage (worse)

        # Track total fees paid for performance analysis
        self.total_fees_paid = 0.0
        self.total_slippage_cost = 0.0

        # Realistic liquidity and volume filters (Nov 30 working settings)
        # Analysis showed 29.4% trades had ZERO liquidity - this prevents those
        self.min_entry_liquidity = float(os.getenv('MIN_ENTRY_LIQUIDITY', '30000'))  # $30k minimum at entry
        self.min_exit_liquidity = float(os.getenv('MIN_EXIT_LIQUIDITY', '15000'))     # $15k minimum at exit
        self.min_24h_volume = float(os.getenv('MIN_24H_VOLUME', '15000'))             # $15k daily volume
        self.max_position_vs_liquidity = float(os.getenv('MAX_POSITION_VS_LIQUIDITY', '0.005'))  # Max 0.5% of pool

        # TIER 2 FILTERS: Price and volume safety (OPTIMIZED from 363-trade analysis!)
        # Analysis: Entry price sweet spot = $0.00035, range $0.0001-0.001 (best performance)
        # Analysis: 2.5k-5k tokens/$ = 29.8% win rate (vs 13.1% for <1k expensive tokens)
        self.min_entry_price = float(os.getenv('MIN_ENTRY_PRICE', '0.0001'))         # Minimum entry price (cheap tokens sweet spot)
        self.max_entry_price = float(os.getenv('MAX_ENTRY_PRICE', '0.001'))          # Maximum entry price (sweet spot range)
        self.min_tokens_per_dollar = float(os.getenv('MIN_TOKENS_PER_DOLLAR', '2500'))  # Min volume (filters expensive tokens)
        self.max_tokens_per_dollar = float(os.getenv('MAX_TOKENS_PER_DOLLAR', '5000'))  # Max volume (sweet spot upper)
        self.max_position_size = float(os.getenv('MAX_POSITION_SIZE', '50'))          # Hard cap ($50 max per top trades)
        self.min_position_size = float(os.getenv('MIN_POSITION_SIZE', '35'))          # Min position ($35 minimum per analysis)

        # Volume fallback (when liquidity data unavailable but volume is high)
        self.allow_volume_fallback = os.getenv('ALLOW_VOLUME_FALLBACK', 'true').lower() == 'true'
        self.min_volume_for_fallback = float(os.getenv('MIN_VOLUME_FOR_FALLBACK', '50000'))  # $50k volume
        self.volume_fallback_position_multiplier = float(os.getenv('VOLUME_FALLBACK_POSITION_MULTIPLIER', '0.5'))  # 50% position

        # Stuck position management (prevents position slots from being blocked)
        self.auto_cleanup_enabled = os.getenv('AUTO_CLEANUP_ENABLED', 'true').lower() == 'true'
        self.max_position_age_hours = float(os.getenv('MAX_POSITION_AGE_HOURS', '48'))  # 48 hours default
        self.stuck_liquidity_threshold = float(os.getenv('STUCK_LIQUIDITY_THRESHOLD', '1000'))  # $1k
        self.stuck_time_hours = float(os.getenv('STUCK_TIME_HOURS', '6'))  # 6 hours
        self.force_close_on_rug = os.getenv('FORCE_CLOSE_ON_RUG', 'true').lower() == 'true'

        # Track rejected trades for analysis
        self.rejected_trades = {
            'low_entry_liquidity': 0,
            'low_volume': 0,
            'position_too_large': 0,
            'position_too_small': 0,      # NEW: Position < $35 (bad tokens filter)
            'low_exit_liquidity': 0,
            'price_too_low': 0,           # NEW: Price < $0.0001 (below sweet spot)
            'price_too_high': 0,          # NEW: Price > $0.001 (above sweet spot)
            'low_volume_expensive': 0,    # NEW: <2.5k tokens/$ (expensive = bad)
            'high_volume_risk': 0,        # NEW: >5k tokens/$ (above sweet spot)
            'volume_fallback_unsafe': 0,   # NEW: Volume fallback blocked by price/tokens checks
            'forced_cleanup': 0           # NEW: Stuck positions force-closed
        }
        self.volume_fallback_trades = 0  # Track risky volume-based trades

        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        # Read max positions from .env (was hardcoded to 5)
        max_positions = int(os.getenv('MAX_OPEN_POSITIONS', '7'))
        self.position_manager = PositionManager(max_open_positions=max_positions)
        self.total_invested = 0.0

        # Use absolute path for state file
        if not os.path.isabs(state_file):
            self.state_file = os.path.join(os.getcwd(), state_file)
        else:
            self.state_file = state_file

        logger.info(f"State file location: {self.state_file}")

        # Initialize Jupiter executor for realistic simulation
        rpc_url = os.getenv('SOLANA_RPC_URL', 'https://api.mainnet-beta.solana.com')
        use_jito = os.getenv('USE_JITO_BUNDLES', 'true').lower() == 'true'
        self.jupiter_executor = JupiterSwapExecutor(
            rpc_url=rpc_url,
            use_jito=use_jito,
            paper_trading=True  # Always True in paper trading mode
        )
        logger.info(f"✅ Jupiter executor initialized (Paper Mode, Jito: {use_jito})")

        # Age-based strategies (optional - can disable to use golden settings)
        self.enable_age_strategies = os.getenv('ENABLE_AGE_BASED_STRATEGIES', 'false').lower() == 'true'
        if self.enable_age_strategies:
            self.strategy_selector = StrategySelector()
            logger.info("✅ Age-based profit strategies ENABLED")
        else:
            self.strategy_selector = None
            logger.info("🔒 Age-based strategies DISABLED - using golden settings")

        # === TOKEN PERFORMANCE TRACKER (INFRASTRUCTURE - DISABLED BY DEFAULT) ===
        # Track historical token performance for learning which tokens are consistent losers/winners
        self.enable_token_tracker = os.getenv('ENABLE_TOKEN_TRACKER', 'false').lower() == 'true'
        if self.enable_token_tracker:
            self.token_tracker = TokenPerformanceTracker()
            logger.info("✅ Token Performance Tracker ENABLED - learning from history")
        else:
            self.token_tracker = None
            logger.info("📊 Token Performance Tracker DISABLED (infrastructure ready, enable when needed)")

        # === BLACKLIST/WHITELIST FILTER (INFRASTRUCTURE - DISABLED BY DEFAULT) ===
        # Manual filtering of known good/bad tokens
        self.enable_token_filter = os.getenv('ENABLE_TOKEN_FILTER', 'false').lower() == 'true'
        if self.enable_token_filter:
            self.token_filter = TokenFilter()
            logger.info("✅ Token Filter ENABLED - blacklist/whitelist active")
        else:
            self.token_filter = None
            logger.info("🚫 Token Filter DISABLED (infrastructure ready, enable when needed)")

        # Auto-blacklist settings (only if tracker enabled)
        self.auto_blacklist_losers = os.getenv('AUTO_BLACKLIST_LOSERS', 'false').lower() == 'true'
        self.auto_blacklist_min_trades = int(os.getenv('AUTO_BLACKLIST_MIN_TRADES', '3'))
        self.auto_blacklist_max_winrate = float(os.getenv('AUTO_BLACKLIST_MAX_WINRATE', '0.0'))

        # Load previous state if exists
        self.load_state()

        logger.info(
            f"Paper trading engine initialized: ${self.current_capital:.2f} capital, "
            f"{len(self.position_manager.open_positions)} positions"
        )

        # Log trailing stop settings
        if self.use_trailing_stop:
            logger.info(
                f"📈 Trailing stop ENABLED: {self.trailing_stop_percent:.0f}% below peak "
                f"(exits sooner, captures pumps, avoids rugs)"
            )
        else:
            logger.info(f"🎯 Fixed take profit at {os.getenv('TAKE_PROFIT_PERCENT', '20')}%")

        # Log rug detection settings
        if self.rug_detection_enabled:
            logger.info(
                f"🛡️  Rug protection ENABLED: "
                f"Liquidity threshold ${self.min_position_liquidity:.0f}, "
                f"Stale price timeout {self.stale_price_minutes:.0f} min"
            )
        else:
            logger.warning("⚠️  Rug protection DISABLED")

        # BATCH 10: Log liquidity monitoring settings
        if self.enable_liquidity_monitoring:
            logger.info(
                f"💧 LIQUIDITY MONITORING ENABLED (BATCH 10 FIX): "
                f"Exit if liquidity drops >{self.liquidity_drop_threshold:.0f}% from entry\n"
                f"   🎯 Prevents 100% liquidity drop issue (exits early at -50% instead of waiting for -100%)"
            )
        else:
            logger.warning("⚠️  Liquidity monitoring DISABLED")

        # Log partial profit taking settings
        if self.partial_profit_enabled:
            logger.info(
                f"💰 Partial profit taking ENABLED: "
                f"+100%={self.profit_milestone_100:.0f}%, "
                f"+200%={self.profit_milestone_200:.0f}%, "
                f"+300%={self.profit_milestone_300:.0f}%, "
                f"+500%={self.profit_milestone_500:.0f}% "
                f"(locks profits before crashes!)"
            )
        else:
            logger.info("💰 Partial profit taking DISABLED")

        # Log fee/slippage simulation settings
        if self.simulate_fees:
            total_round_trip_cost = self.buy_fee_percent + self.sell_fee_percent + self.buy_slippage_percent + self.sell_slippage_percent
            logger.info(
                f"💸 Fee/Slippage simulation ENABLED: "
                f"Buy: {self.buy_fee_percent}% fee + {self.buy_slippage_percent}% slippage, "
                f"Sell: {self.sell_fee_percent}% fee + {self.sell_slippage_percent}% slippage "
                f"(~{total_round_trip_cost:.1f}% total cost per round trip)"
            )
        else:
            logger.info("💸 Fee/Slippage simulation DISABLED (unrealistic profits!)")

        # Log realistic liquidity/volume filters
        logger.info(
            f"🔒 REALISTIC FILTERS ENABLED (prevents 29% of unsellable trades):\n"
            f"   Min Entry Liquidity: ${self.min_entry_liquidity:,.0f}\n"
            f"   Min Exit Liquidity: ${self.min_exit_liquidity:,.0f}\n"
            f"   Min 24h Volume: ${self.min_24h_volume:,.0f}\n"
            f"   Max Position vs Liquidity: {self.max_position_vs_liquidity*100:.1f}%"
        )

        # Log TIER 2 filters
        logger.info(
            f"🎯 TIER 2 FILTERS ENABLED (prevents 80% of high-risk trades!):\n"
            f"   Min Entry Price: ${self.min_entry_price:.2f} (blocks ultra-cheap scam tokens)\n"
            f"   Max Tokens per Dollar: {self.max_tokens_per_dollar:,.0f} (blocks high-volume scams)\n"
            f"   Max Position Size: ${self.max_position_size:.2f} (hard cap for safety)"
        )

        # Log volume fallback settings
        if self.allow_volume_fallback:
            logger.info(
                f"✅ VOLUME FALLBACK ENABLED (PROTECTED by Tier 2 filters!):\n"
                f"   Min Volume for Fallback: ${self.min_volume_for_fallback:,.0f}\n"
                f"   Position Size Multiplier: {self.volume_fallback_position_multiplier*100:.0f}%\n"
                f"   Protection: Also checks price >${self.min_entry_price:.2f} AND tokens/$ <{self.max_tokens_per_dollar:,.0f}\n"
                f"   → Only catches SAFE high-volume opportunities, not scam tokens!"
            )
        else:
            logger.info("🔒 Volume fallback DISABLED (strict liquidity requirement)")

        # Log stuck position management settings
        if self.auto_cleanup_enabled:
            logger.info(
                f"🗑️  AUTO CLEANUP ENABLED (prevents stuck positions from blocking slots!):\n"
                f"   Max Position Age: {self.max_position_age_hours:.0f} hours\n"
                f"   Stuck Liquidity Threshold: ${self.stuck_liquidity_threshold:,.0f}\n"
                f"   Stuck Time: {self.stuck_time_hours:.0f} hours\n"
                f"   Force Close on Rug: {'YES' if self.force_close_on_rug else 'NO'}\n"
                f"   → Positions stuck >6h or >48h old will be force-closed to free slots"
            )
        else:
            logger.warning("⚠️  Auto cleanup DISABLED - stuck positions may block trading slots!")

    def store_trade_context(self, token_address: str, analysis_data: Dict):
        """
        Store analysis context for ML data collection.

        Args:
            token_address: Token address
            analysis_data: Full analysis data from token analysis
        """
        global _trade_contexts
        _trade_contexts[token_address] = {
            'timestamp': datetime.now(),
            'analysis': analysis_data
        }

    def _record_ml_trade(self, trade: Trade, position: Position, exit_reason: str):
        """
        Record completed trade for ML training.

        Args:
            trade: Trade object
            position: Position object (before closing)
            exit_reason: Reason for exit
        """
        global _ml_collector, _trade_contexts

        if not _ml_collector:
            return  # ML collection not enabled

        try:
            from ..data import MLTradeRecord

            # Get stored analysis context
            context = _trade_contexts.get(trade.token_address, {})
            analysis = context.get('analysis', {})

            # Extract data from analysis
            market_data = analysis.get('market_data', {})
            risk_assessment_raw = analysis.get('risk_assessment', {})
            price_prediction_raw = analysis.get('price_prediction', {})
            sentiment_raw = analysis.get('sentiment', {})
            security = analysis.get('security', {})

            # Handle risk_assessment being either dict or RiskAssessment object
            if hasattr(risk_assessment_raw, '__dict__'):
                # It's an object, convert to dict
                risk_assessment = {
                    'risk_score': getattr(risk_assessment_raw, 'risk_score', 0),
                    'risk_factors': getattr(risk_assessment_raw, 'risk_factors', {})
                }
            else:
                # It's already a dict
                risk_assessment = risk_assessment_raw

            # Handle price_prediction being either dict or PricePrediction object
            if hasattr(price_prediction_raw, '__dict__'):
                price_prediction = {
                    'predicted_direction': getattr(price_prediction_raw, 'predicted_direction', ''),
                    'confidence': getattr(price_prediction_raw, 'confidence', 0),
                    'predicted_change_percent': getattr(price_prediction_raw, 'predicted_change_percent', 0)
                }
            else:
                price_prediction = price_prediction_raw

            # Handle sentiment being either dict or SentimentScore object
            if hasattr(sentiment_raw, '__dict__'):
                sentiment = {
                    'overall_score': getattr(sentiment_raw, 'overall_score', 0.5),
                    'confidence': getattr(sentiment_raw, 'confidence', 0),
                    'coordination_risk': getattr(sentiment_raw, 'coordination_risk', 0)
                }
            else:
                sentiment = sentiment_raw

            # Calculate hold duration
            hold_duration = (trade.timestamp - position.entry_time).total_seconds() / 60  # minutes

            # Create ML trade record
            ml_record = MLTradeRecord(
                trade_id=str(uuid.uuid4()),
                token_address=trade.token_address,
                token_symbol=getattr(trade, 'symbol', None) or getattr(trade, 'token_symbol', None) or trade.token_address[:8],
                action='completed',
                entry_time=position.entry_time,
                exit_time=trade.timestamp,
                hold_duration_minutes=hold_duration,
                entry_price=position.entry_price,
                exit_price=trade.price,
                highest_price_reached=position.highest_price,
                lowest_price_reached=position.entry_price,  # We don't track lowest (could add)
                amount_usd=trade.amount_usd,
                quantity=trade.quantity,
                position_size_percent_of_portfolio=(trade.amount_usd / self.get_portfolio_value() * 100) if self.get_portfolio_value() > 0 else 0,
                pnl_usd=trade.pnl,
                pnl_percent=trade.pnl_percent,
                win=trade.pnl > 0,
                exit_reason=exit_reason,
                # Market conditions at entry
                entry_liquidity_usd=market_data.get('liquidity_usd', 0),
                entry_volume_24h=market_data.get('volume_24h', 0),
                entry_price_change_24h=market_data.get('price_change_24h', 0),
                entry_holder_count=market_data.get('holder_count', 0),
                entry_market_cap=market_data.get('market_cap', 0),
                # Market conditions at exit (we don't have this - could fetch)
                exit_liquidity_usd=position.current_liquidity,
                exit_volume_24h=0,
                exit_price_change_24h=0,
                # Token characteristics
                token_age_hours=security.get('token_age_hours', 0),
                is_mintable=security.get('is_mintable', False),
                has_freeze_authority=security.get('has_freeze_authority', False),
                is_verified=security.get('is_verified', False),
                ownership_renounced=security.get('ownership_renounced', False),
                # Risk scores
                overall_risk_score=risk_assessment.get('risk_score', 0),
                liquidity_risk=risk_assessment.get('risk_factors', {}).get('liquidity', 0),
                security_risk=risk_assessment.get('risk_factors', {}).get('security', 0),
                volatility_risk=risk_assessment.get('risk_factors', {}).get('volatility', 0),
                sentiment_risk=risk_assessment.get('risk_factors', {}).get('sentiment', 0),
                age_risk=risk_assessment.get('risk_factors', {}).get('age', 0),
                # Signals & predictions
                sentiment_score=sentiment.get('overall_score', 0.5),
                sentiment_confidence=sentiment.get('confidence', 0),
                coordination_risk=sentiment.get('coordination_risk', 0),
                price_prediction_direction=price_prediction.get('predicted_direction', ''),
                price_prediction_confidence=price_prediction.get('confidence', 0),
                predicted_change_percent=price_prediction.get('predicted_change_percent', 0),
                # Portfolio context
                portfolio_value_at_entry=self.get_portfolio_value(),
                open_positions_count=len(self.position_manager.open_positions),
                daily_trades_before_this=len([t for t in self.position_manager.closed_trades if t.timestamp.date() == datetime.now().date()]),
                # Execution
                execution_method='jupiter',
                # Trailing stop
                used_trailing_stop=position.use_trailing_stop,
                trailing_stop_percent=position.trailing_stop_percent,
                max_drawdown_from_peak_percent=((position.highest_price - trade.price) / position.highest_price * 100) if position.highest_price > 0 else 0,
                # Partial profits
                is_partial_sell=False,  # Could enhance this
                milestones_hit=list(position.milestones_hit),
                partial_sell_count=len(position.milestones_hit),
                # Metadata
                paper_trading=True
            )

            # Record to ML collector
            _ml_collector.record_trade(ml_record)
            logger.debug(f"📊 ML trade recorded: {trade.symbol or trade.token_address[:8]} ({trade.pnl_percent:+.2f}%)")

            # Clean up context
            if trade.token_address in _trade_contexts:
                del _trade_contexts[trade.token_address]

        except Exception as e:
            logger.error(f"❌ Error recording ML trade: {e}", exc_info=True)

    async def execute_buy(
        self,
        token_address: str,
        amount_usd: float,
        price: float,
        stop_loss: float,
        take_profit: float,
        use_trailing_stop: Optional[bool] = None,
        trailing_stop_percent: Optional[float] = None,
        analysis_data: Optional[Dict] = None,
        pair_created_at: Optional[int] = None
    ) -> Dict:
        """
        Execute a simulated buy order.

        Args:
            token_address: Token contract address
            amount_usd: Amount to invest in USD
            price: Current token price
            stop_loss: Stop loss price
            take_profit: Take profit price (ignored if using trailing stop)
            use_trailing_stop: Whether to use trailing stop (reads from .env if None)
            trailing_stop_percent: Percent to trail below peak (reads from .env if None)
            analysis_data: Token analysis data (should include liquidity_usd, volume_24h)
            pair_created_at: Unix timestamp when pair was created (for age-based strategy)

        Returns:
            Execution result dictionary
        """
        # Use .env settings if not explicitly provided
        if use_trailing_stop is None:
            use_trailing_stop = self.use_trailing_stop
        if trailing_stop_percent is None:
            trailing_stop_percent = self.trailing_stop_percent

        # Select strategy based on token age (if age-based strategies enabled)
        strategy = None
        if self.enable_age_strategies and self.strategy_selector and pair_created_at and pair_created_at > 0:
            strategy = self.strategy_selector.select_strategy(pair_created_at)
            # Apply strategy-specific adjustments
            amount_usd = amount_usd * strategy.position_size_multiplier
            trailing_stop_percent = strategy.trailing_stop_percent
            logger.info(
                f"📊 Using strategy: {strategy.name} | "
                f"Trailing: {strategy.trailing_stop_percent}% | "
                f"Position multiplier: {strategy.position_size_multiplier}x"
            )
        elif pair_created_at:
            logger.info("📊 Using golden settings (age-based strategies disabled)")
        else:
            # No age data, use default settings from .env
            logger.debug(f"No token age data, using default .env settings")

        # Track if this trade uses volume fallback (for analysis)
        is_volume_fallback = False

        # TIER 2 FILTER: Check minimum entry price (sweet spot filter)
        if price < self.min_entry_price:
            self.rejected_trades['price_too_low'] += 1
            logger.warning(
                f"❌ REJECTED {token_address[:8]}... - Price too low:\n"
                f"   Entry Price: ${price:.8f} < ${self.min_entry_price:.8f}\n"
                f"   Below sweet spot range"
            )
            return {
                'status': 'failed',
                'reason': 'price_too_low',
                'price': price,
                'min_required': self.min_entry_price
            }

        # TIER 2 FILTER: Check maximum entry price (sweet spot filter - NEW!)
        if price > self.max_entry_price:
            self.rejected_trades['price_too_high'] += 1
            logger.warning(
                f"❌ REJECTED {token_address[:8]}... - Price too high:\n"
                f"   Entry Price: ${price:.8f} > ${self.max_entry_price:.8f}\n"
                f"   Above sweet spot range (expensive tokens = 4.5% win rate)"
            )
            return {
                'status': 'failed',
                'reason': 'price_too_high',
                'price': price,
                'max_allowed': self.max_entry_price
            }

        # TIER 2 FILTER: Check minimum position size (quality filter - NEW!)
        if amount_usd < self.min_position_size:
            self.rejected_trades['position_too_small'] += 1
            logger.warning(
                f"❌ REJECTED {token_address[:8]}... - Position too small:\n"
                f"   Position: ${amount_usd:.2f} < ${self.min_position_size:.2f}\n"
                f"   Small positions = bad tokens (0% win rate per analysis)"
            )
            return {
                'status': 'failed',
                'reason': 'position_too_small',
                'amount_usd': amount_usd,
                'min_required': self.min_position_size
            }

        # TIER 2 FILTER: Check maximum position size (hard cap for safety)
        if amount_usd > self.max_position_size:
            self.rejected_trades['position_too_large'] += 1
            logger.warning(
                f"❌ REJECTED {token_address[:8]}... - Position too large:\n"
                f"   Position: ${amount_usd:.2f} > ${self.max_position_size:.2f} (hard cap)\n"
                f"   Large positions cause excessive slippage!"
            )
            return {
                'status': 'failed',
                'reason': 'position_too_large',
                'amount_usd': amount_usd,
                'max_allowed': self.max_position_size
            }

        # TIER 2 FILTER: Calculate and check tokens per dollar (OPTIMIZED sweet spot filter!)
        # Analysis: 2.5k-5k tokens/$ = 29.8% win rate (BEST!)
        quantity_estimate = amount_usd / price
        tokens_per_dollar = quantity_estimate / amount_usd

        # Check minimum tokens per dollar (filters expensive tokens with low win rate)
        if tokens_per_dollar < self.min_tokens_per_dollar:
            self.rejected_trades['low_volume_expensive'] += 1
            logger.warning(
                f"❌ REJECTED {token_address[:8]}... - Too expensive (low volume):\n"
                f"   Tokens per $1: {tokens_per_dollar:,.0f} < {self.min_tokens_per_dollar:,.0f} minimum\n"
                f"   Total tokens: {quantity_estimate:,.0f}\n"
                f"   Expensive tokens (below minimum threshold based on analysis)"
            )
            return {
                'status': 'failed',
                'reason': 'low_volume_expensive',
                'tokens_per_dollar': tokens_per_dollar,
                'min_required': self.min_tokens_per_dollar
            }

        # Check maximum tokens per dollar (upper bound of sweet spot)
        if tokens_per_dollar > self.max_tokens_per_dollar:
            self.rejected_trades['high_volume_risk'] += 1
            logger.warning(
                f"❌ REJECTED {token_address[:8]}... - Volume too high (above sweet spot):\n"
                f"   Tokens per $1: {tokens_per_dollar:,.0f} > {self.max_tokens_per_dollar:,.0f} max\n"
                f"   Total tokens: {quantity_estimate:,.0f}\n"
                f"   Sweet spot: 2.5k-5k tokens/$ (29.8% win rate)"
            )
            return {
                'status': 'failed',
                'reason': 'high_volume_risk',
                'tokens_per_dollar': tokens_per_dollar,
                'max_allowed': self.max_tokens_per_dollar
            }

        # REALISTIC LIQUIDITY & VOLUME FILTERS (prevents 29% of unsellable trades)
        if analysis_data:
            # Extract liquidity/volume from nested profile (analysis_data contains the full analysis)
            profile = analysis_data.get('profile', {})
            liquidity = profile.get('liquidity_usd', 0)
            volume_24h = profile.get('volume_24h', 0)

            # Check minimum entry liquidity
            if liquidity < self.min_entry_liquidity:
                # PROTECTED VOLUME FALLBACK: Only allow if volume is high AND token passes safety checks
                # This prevents volume fallback from catching ultra-cheap scam tokens!
                if self.allow_volume_fallback and volume_24h >= self.min_volume_for_fallback:
                    # CRITICAL: Verify token passes Tier 2 safety filters (price already checked above)
                    # Re-check tokens/dollar with reduced position size
                    reduced_amount = amount_usd * self.volume_fallback_position_multiplier
                    reduced_quantity = reduced_amount / price
                    reduced_tokens_per_dollar = reduced_quantity / reduced_amount

                    # Volume fallback ONLY allowed if token metrics are safe
                    if reduced_tokens_per_dollar <= self.max_tokens_per_dollar:
                        # SAFE to use volume fallback - token passes all safety checks
                        original_amount = amount_usd
                        amount_usd = reduced_amount
                        self.volume_fallback_trades += 1
                        is_volume_fallback = True
                        logger.warning(
                            f"✅ VOLUME FALLBACK (PROTECTED) {token_address[:8]}... - High volume + SAFE metrics:\n"
                            f"   Liquidity: ${liquidity:,.0f} (missing/low)\n"
                            f"   Volume 24h: ${volume_24h:,.0f} ✅\n"
                            f"   Price: ${price:.8f} (>${self.min_entry_price:.2f} ✓)\n"
                            f"   Tokens/$: {reduced_tokens_per_dollar:,.0f} (<{self.max_tokens_per_dollar:,.0f} ✓)\n"
                            f"   Position reduced: ${original_amount:.2f} → ${amount_usd:.2f} "
                            f"({self.volume_fallback_position_multiplier*100:.0f}% - SAFER)\n"
                            f"   ⚠️  Monitoring will exit if liquidity actually dried up"
                        )
                    else:
                        # Volume fallback REJECTED - unsafe metrics (too many tokens per dollar)
                        self.rejected_trades['volume_fallback_unsafe'] += 1
                        logger.warning(
                            f"❌ REJECTED VOLUME FALLBACK {token_address[:8]}... - UNSAFE metrics:\n"
                            f"   Volume: ${volume_24h:,.0f} (high enough)\n"
                            f"   BUT Tokens/$: {reduced_tokens_per_dollar:,.0f} > {self.max_tokens_per_dollar:,.0f} ❌\n"
                            f"   This is likely a HIGH-RISK cheap scam token!\n"
                            f"   Protected volume fallback blocked the trade ✓"
                        )
                        return {
                            'status': 'failed',
                            'reason': 'volume_fallback_unsafe',
                            'tokens_per_dollar': reduced_tokens_per_dollar,
                            'max_allowed': self.max_tokens_per_dollar
                        }
                else:
                    # No volume fallback or volume too low - reject trade
                    self.rejected_trades['low_entry_liquidity'] += 1
                    logger.warning(
                        f"❌ REJECTED {token_address[:8]}... - Low liquidity: "
                        f"${liquidity:,.0f} < ${self.min_entry_liquidity:,.0f}"
                    )
                    return {
                        'status': 'failed',
                        'reason': 'low_entry_liquidity',
                        'liquidity': liquidity,
                        'min_required': self.min_entry_liquidity
                    }

            # Check minimum 24h volume
            if volume_24h < self.min_24h_volume:
                self.rejected_trades['low_volume'] += 1
                logger.warning(
                    f"❌ REJECTED {token_address[:8]}... - Low volume: "
                    f"${volume_24h:,.0f} < ${self.min_24h_volume:,.0f}"
                )
                return {
                    'status': 'failed',
                    'reason': 'low_volume',
                    'volume_24h': volume_24h,
                    'min_required': self.min_24h_volume
                }

            # === DEAD TOKEN / HONEYPOT DETECTION (Transaction Activity Analysis) ===
            # Extract transaction data from profile
            txns_h1_buys = profile.get('txns_h1_buys', 0)
            txns_h1_sells = profile.get('txns_h1_sells', 0)
            txns_total_h1 = txns_h1_buys + txns_h1_sells

            # HONEYPOT CHECK: Lots of buys but ZERO sells = honeypot (can't sell!)
            if txns_h1_buys > 5 and txns_h1_sells == 0:
                if 'honeypot_detected' not in self.rejected_trades:
                    self.rejected_trades['honeypot_detected'] = 0
                self.rejected_trades['honeypot_detected'] += 1
                logger.warning(
                    f"❌ REJECTED {token_address[:8]}... - HONEYPOT DETECTED:\n"
                    f"   Buys last 1h: {txns_h1_buys}\n"
                    f"   Sells last 1h: {txns_h1_sells} (ZERO SELLS!)\n"
                    f"   This token cannot be sold - honeypot scam!"
                )
                return {
                    'status': 'failed',
                    'reason': 'honeypot_detected',
                    'txns_h1_buys': txns_h1_buys,
                    'txns_h1_sells': txns_h1_sells
                }

            # DEAD TOKEN CHECK: Very few transactions = no activity/dead
            if txns_total_h1 > 0 and txns_total_h1 < 20:
                if 'dead_token_low_activity' not in self.rejected_trades:
                    self.rejected_trades['dead_token_low_activity'] = 0
                self.rejected_trades['dead_token_low_activity'] += 1
                logger.warning(
                    f"❌ REJECTED {token_address[:8]}... - DEAD TOKEN (low activity):\n"
                    f"   Total transactions last 1h: {txns_total_h1} < 20\n"
                    f"   Buys: {txns_h1_buys}, Sells: {txns_h1_sells}\n"
                    f"   Token has minimal trading activity - likely dead/abandoned"
                )
                return {
                    'status': 'failed',
                    'reason': 'dead_token_low_activity',
                    'txns_total_h1': txns_total_h1
                }

            # BUY/SELL IMBALANCE CHECK: Heavy buy pressure with almost no sells = suspicious
            if txns_h1_sells > 0:  # Avoid division by zero
                buy_sell_ratio = txns_h1_buys / txns_h1_sells
                if buy_sell_ratio > 5:
                    if 'suspicious_buy_sell_ratio' not in self.rejected_trades:
                        self.rejected_trades['suspicious_buy_sell_ratio'] = 0
                    self.rejected_trades['suspicious_buy_sell_ratio'] += 1
                    logger.warning(
                        f"❌ REJECTED {token_address[:8]}... - SUSPICIOUS buy/sell ratio:\n"
                        f"   Buys: {txns_h1_buys}, Sells: {txns_h1_sells}\n"
                        f"   Ratio: {buy_sell_ratio:.1f}:1 (>5:1 threshold)\n"
                        f"   Heavy buy pressure with minimal sells - potential manipulation"
                    )
                    return {
                        'status': 'failed',
                        'reason': 'suspicious_buy_sell_ratio',
                        'buy_sell_ratio': buy_sell_ratio
                    }

            # === RUGCHECK-BASED SECURITY FILTERS ===
            # Extract RugCheck data if available
            rug_check = analysis_data.get('rug_check', {}) if analysis_data else {}

            if rug_check:
                # Extract LP lock info from raw RugCheck report
                raw_report = rug_check.get('raw_report', {})
                markets = raw_report.get('markets', [])
                top_holders = raw_report.get('topHolders', [])

                # === 455-TRADE: LP LOCK CHECK (Save $120-150 per 100 trades!) ===
                # Research: 28.3% rug exits (-$199), LP lock prevents ~70%
                if self.enable_lp_lock_check and markets:
                    # Get first market (highest liquidity pair)
                    main_market = markets[0] if markets else {}
                    lp_data = main_market.get('lp', {})
                    lp_locked_pct = float(lp_data.get('lpLockedPct', 0))

                    # Check if LP is burned (best case - 100% locked forever)
                    lp_burned = lp_data.get('lpBurned', False)
                    if lp_burned and self.allow_lp_burned:
                        logger.info(f"✅ LP BURNED {token_address[:8]}... - Safest option!")
                    # Check if LP is locked for minimum duration
                    elif lp_locked_pct < 100 and self.skip_unlocked_lp:
                        # Check lock duration
                        lp_lock_timestamp = lp_data.get('lpLockedUntil', 0)
                        if lp_lock_timestamp > 0:
                            from datetime import datetime, timedelta
                            lock_until = datetime.fromtimestamp(lp_lock_timestamp / 1000)
                            days_locked = (lock_until - datetime.now()).days
                            if days_locked < self.min_lp_lock_days:
                                if 'lp_lock_too_short' not in self.rejected_trades:
                                    self.rejected_trades['lp_lock_too_short'] = 0
                                self.rejected_trades['lp_lock_too_short'] += 1
                                logger.warning(
                                    f"❌ REJECTED {token_address[:8]}... - LP LOCK TOO SHORT:\n"
                                    f"   LP Locked: {days_locked} days < {self.min_lp_lock_days} days minimum\n"
                                    f"   Developer can remove liquidity soon - RUG RISK!"
                                )
                                return {
                                    'status': 'failed',
                                    'reason': 'lp_lock_too_short',
                                    'days_locked': days_locked
                                }
                        else:
                            # LP not locked at all
                            if 'lp_not_locked' not in self.rejected_trades:
                                self.rejected_trades['lp_not_locked'] = 0
                            self.rejected_trades['lp_not_locked'] += 1
                            logger.warning(
                                f"❌ REJECTED {token_address[:8]}... - LIQUIDITY NOT LOCKED:\n"
                                f"   LP Locked: {lp_locked_pct:.1f}% (not permanently locked)\n"
                                f"   Developer can remove liquidity at any time - RUG RISK!"
                            )
                            return {
                                'status': 'failed',
                                'reason': 'lp_not_locked',
                                'lp_locked_pct': lp_locked_pct
                            }

                # === 455-TRADE: HOLDER CONCENTRATION CHECK ===
                if self.enable_holder_check and top_holders and len(top_holders) >= 10:
                    # Calculate total % owned by top 10 holders
                    top10_total_pct = sum(float(h.get('pct', 0)) * 100 for h in top_holders[:10])

                    # Check top 10 concentration
                    if top10_total_pct > self.max_top_10_concentration:
                        if 'top10_concentration' not in self.rejected_trades:
                            self.rejected_trades['top10_concentration'] = 0
                        self.rejected_trades['top10_concentration'] += 1
                        logger.warning(
                            f"❌ REJECTED {token_address[:8]}... - TOP 10 TOO CONCENTRATED:\n"
                            f"   Top 10 holders own: {top10_total_pct:.1f}% > {self.max_top_10_concentration}% threshold\n"
                            f"   Token supply is too concentrated - manipulation risk!"
                        )
                        return {
                            'status': 'failed',
                            'reason': 'top10_concentration',
                            'top10_total_pct': top10_total_pct
                        }

                    # Check top 1 holder concentration
                    if top_holders:
                        top1_pct = float(top_holders[0].get('pct', 0)) * 100
                        if top1_pct > self.max_top_1_concentration:
                            if 'top1_concentration' not in self.rejected_trades:
                                self.rejected_trades['top1_concentration'] = 0
                            self.rejected_trades['top1_concentration'] += 1
                            logger.warning(
                                f"❌ REJECTED {token_address[:8]}... - TOP HOLDER TOO LARGE:\n"
                                f"   Top holder owns: {top1_pct:.1f}% > {self.max_top_1_concentration}% threshold\n"
                                f"   Single whale control - extreme manipulation risk!"
                            )
                            return {
                                'status': 'failed',
                                'reason': 'top1_concentration',
                                'top1_pct': top1_pct
                            }

                # === 455-TRADE: CONTRACT SAFETY CHECKS ===
                if rug_check:
                    raw_report = rug_check.get('raw_report', {})
                    token_meta = raw_report.get('tokenMeta', {})

                    # Check mint authority
                    if self.block_mint_authority:
                        mint_authority = token_meta.get('mintAuthority')
                        if mint_authority and mint_authority != 'null' and mint_authority != '':
                            if 'mint_authority_active' not in self.rejected_trades:
                                self.rejected_trades['mint_authority_active'] = 0
                            self.rejected_trades['mint_authority_active'] += 1
                            logger.warning(
                                f"❌ REJECTED {token_address[:8]}... - MINT AUTHORITY ACTIVE:\n"
                                f"   Mint Authority: {mint_authority[:20]}...\n"
                                f"   Developer can create unlimited tokens - DILUTION RISK!"
                            )
                            return {
                                'status': 'failed',
                                'reason': 'mint_authority_active'
                            }

                    # Check freeze authority
                    if self.block_freeze_authority:
                        freeze_authority = token_meta.get('freezeAuthority')
                        if freeze_authority and freeze_authority != 'null' and freeze_authority != '':
                            if 'freeze_authority_active' not in self.rejected_trades:
                                self.rejected_trades['freeze_authority_active'] = 0
                            self.rejected_trades['freeze_authority_active'] += 1
                            logger.warning(
                                f"❌ REJECTED {token_address[:8]}... - FREEZE AUTHORITY ACTIVE:\n"
                                f"   Freeze Authority: {freeze_authority[:20]}...\n"
                                f"   Developer can freeze your tokens - LOCK RISK!"
                            )
                            return {
                                'status': 'failed',
                                'reason': 'freeze_authority_active'
                            }

                    # Check ownership renounced (optional - not required by default)
                    if self.require_renounced:
                        update_authority = token_meta.get('updateAuthority')
                        if update_authority and update_authority != 'null' and update_authority != '':
                            if 'ownership_not_renounced' not in self.rejected_trades:
                                self.rejected_trades['ownership_not_renounced'] = 0
                            self.rejected_trades['ownership_not_renounced'] += 1
                            logger.warning(
                                f"❌ REJECTED {token_address[:8]}... - OWNERSHIP NOT RENOUNCED:\n"
                                f"   Update Authority: {update_authority[:20]}...\n"
                                f"   Developer retains control - modification risk!"
                            )
                            return {
                                'status': 'failed',
                                'reason': 'ownership_not_renounced'
                            }

            # Check position size vs liquidity (prevent price impact >0.5%)
            if amount_usd > liquidity * self.max_position_vs_liquidity:
                self.rejected_trades['position_too_large'] += 1
                max_safe_position = liquidity * self.max_position_vs_liquidity
                logger.warning(
                    f"❌ REJECTED {token_address[:8]}... - Position too large: "
                    f"${amount_usd:.0f} > ${max_safe_position:.0f} "
                    f"({self.max_position_vs_liquidity*100:.1f}% of ${liquidity:,.0f} liquidity)"
                )
                return {
                    'status': 'failed',
                    'reason': 'position_too_large',
                    'amount_usd': amount_usd,
                    'max_safe_position': max_safe_position,
                    'liquidity': liquidity
                }

        # Check if we have enough capital
        if amount_usd > self.current_capital:
            logger.warning(
                f"Insufficient capital: ${self.current_capital:.2f} < ${amount_usd:.2f}"
            )
            return {
                'status': 'failed',
                'reason': 'insufficient_capital',
                'available_capital': self.current_capital
            }

        # === TOKEN FILTER CHECK (if enabled) ===
        if self.enable_token_filter and self.token_filter:
            # Check whitelist first (highest priority - always allow)
            if self.token_filter.is_whitelisted(token_address):
                logger.info(f"✅ WHITELISTED token {token_address[:8]}... - bypassing other filters")
            # Check blacklist (manual - never trade)
            elif self.token_filter.is_blacklisted(token_address):
                if 'blacklisted' not in self.rejected_trades:
                    self.rejected_trades['blacklisted'] = 0
                self.rejected_trades['blacklisted'] += 1
                logger.warning(f"❌ REJECTED {token_address[:8]}... - Token is BLACKLISTED")
                return {
                    'status': 'failed',
                    'reason': 'blacklisted'
                }

        # === TOKEN PERFORMANCE TRACKER CHECK (if enabled) ===
        if self.enable_token_tracker and self.token_tracker:
            # Check if token is a known consistent loser
            if self.token_tracker.should_avoid_token(
                token_address,
                min_trades=self.auto_blacklist_min_trades,
                max_win_rate=self.auto_blacklist_max_winrate
            ):
                perf = self.token_tracker.get_performance(token_address)
                if 'repeat_loser' not in self.rejected_trades:
                    self.rejected_trades['repeat_loser'] = 0
                self.rejected_trades['repeat_loser'] += 1
                logger.warning(
                    f"❌ REJECTED {token_address[:8]}... - REPEAT LOSER: "
                    f"{perf.total_trades} trades, {perf.win_rate:.0f}% win rate, "
                    f"avg {perf.avg_pnl_percent:+.1f}% PnL"
                )

                # Auto-blacklist if enabled
                if self.auto_blacklist_losers and self.enable_token_filter and self.token_filter:
                    self.token_filter.add_to_blacklist(
                        token_address,
                        reason=f"{perf.total_trades} trades, {perf.win_rate:.0f}% win"
                    )

                return {
                    'status': 'failed',
                    'reason': 'repeat_loser',
                    'total_trades': perf.total_trades,
                    'win_rate': perf.win_rate
                }

            # Log if token is a repeat winner
            if self.token_tracker.is_repeat_winner(token_address):
                perf = self.token_tracker.get_performance(token_address)
                logger.info(
                    f"✅ REPEAT WINNER: {token_address[:8]}... - "
                    f"{perf.total_trades} trades, {perf.win_rate:.0f}% win rate!"
                )

        # Check if we can open more positions
        if not self.position_manager.can_open_position():
            logger.warning("Max positions reached")
            return {
                'status': 'failed',
                'reason': 'max_positions_reached'
            }

        # === 455-TRADE: POSITION SIZING MULTIPLIERS ===
        # Research: Golden range ($30-75k) had 40.8% win, Preferred price (<$0.0005) had 41% win
        original_amount = amount_usd
        position_multiplier = 1.0

        # Apply golden range multiplier
        if self.prefer_golden_range and analysis_data:
            profile = analysis_data.get('profile', {})
            liquidity = profile.get('liquidity_usd', 0)
            if self.golden_liq_min <= liquidity <= self.golden_liq_max:
                position_multiplier *= self.golden_range_multiplier
                logger.info(
                    f"💰 GOLDEN RANGE {token_address[:8]}... - Position multiplier: {self.golden_range_multiplier}x"
                )

        # Apply preferred price multiplier
        if price <= self.preferred_price_max:
            position_multiplier *= self.preferred_price_multiplier
            logger.info(
                f"💎 PREFERRED PRICE {token_address[:8]}... - Price ${price:.8f} ≤ ${self.preferred_price_max:.4f}, "
                f"multiplier: {self.preferred_price_multiplier}x"
            )

        # Apply combined multiplier
        if position_multiplier > 1.0:
            amount_usd = amount_usd * position_multiplier
            # Respect max position size
            if amount_usd > self.max_position_size:
                amount_usd = self.max_position_size
                logger.warning(
                    f"⚠️  Position capped at ${self.max_position_size:.2f} (was ${original_amount * position_multiplier:.2f})"
                )
            else:
                logger.info(
                    f"📈 Position sized up: ${original_amount:.2f} → ${amount_usd:.2f} ({position_multiplier:.2f}x multiplier)"
                )

        # Store analysis context for ML data collection
        if analysis_data:
            self.store_trade_context(token_address, analysis_data)

        # Apply buy fees and slippage if enabled
        actual_entry_price = price
        buy_fee = 0.0
        buy_slippage_cost = 0.0

        if self.simulate_fees:
            # Fee reduces the amount we get (deducted from position size)
            buy_fee = amount_usd * (self.buy_fee_percent / 100)

            # Slippage means we pay a worse price
            slippage_multiplier = 1 + (self.buy_slippage_percent / 100)
            actual_entry_price = price * slippage_multiplier
            buy_slippage_cost = amount_usd * (self.buy_slippage_percent / 100)

            # Track total costs
            self.total_fees_paid += buy_fee
            self.total_slippage_cost += buy_slippage_cost

            logger.debug(
                f"💸 Buy costs: Fee ${buy_fee:.2f} ({self.buy_fee_percent}%), "
                f"Slippage ${buy_slippage_cost:.2f} ({self.buy_slippage_percent}%), "
                f"Entry ${price:.8f} → ${actual_entry_price:.8f}"
            )

        # Extract enhanced tracking data from analysis_data for position tracking
        entry_liquidity = 0.0
        tracking_volume_24h = 0.0
        volume_1h = 0.0
        opportunity_score = 0.0
        token_source = 'unknown'
        dex_platform = 'unknown'
        txns_h1_buys = 0
        txns_h1_sells = 0

        if analysis_data:
            profile = analysis_data.get('profile', {})
            entry_liquidity = profile.get('liquidity_usd', 0.0)
            tracking_volume_24h = profile.get('volume_24h', 0.0)
            volume_1h = profile.get('volume_1h', 0.0)
            # Extract opportunity score from analysis_data (calculated in main.py)
            opportunity_score = analysis_data.get('opportunity_score', 0.0)
            token_source = profile.get('source', 'unknown')
            dex_platform = profile.get('dex_id', 'unknown')
            # Extract transaction activity data (buys/sells from DexScreener)
            # These are already extracted and flattened by dexscreener_client.py
            txns_h1_buys = profile.get('txns_h1_buys', 0)
            txns_h1_sells = profile.get('txns_h1_sells', 0)

        # Calculate configuration percentages for tracking
        config_stop_loss_percent = 0.0
        if actual_entry_price > 0:
            config_stop_loss_percent = ((actual_entry_price - stop_loss) / actual_entry_price) * 100

        config_trailing_activation_percent = self.trailing_stop_activation  # From .env
        config_trailing_distance_percent = trailing_stop_percent  # Same as trailing_stop_percent

        # === EXTRACT 455-TRADE OPTIMIZATION DATA FOR CSV TRACKING ===
        # Position sizing tracking
        golden_range_bonus = False
        preferred_price_bonus = False
        if self.prefer_golden_range and analysis_data:
            profile = analysis_data.get('profile', {})
            liquidity = profile.get('liquidity_usd', 0)
            if self.golden_liq_min <= liquidity <= self.golden_liq_max:
                golden_range_bonus = True
        if price <= self.preferred_price_max:
            preferred_price_bonus = True

        # LP lock data (extract from markets)
        lp_locked = False
        lp_burned = False
        lp_lock_days = 0
        if analysis_data:
            markets = analysis_data.get('markets', [])
            if markets:
                main_market = markets[0]
                lp_data = main_market.get('lp', {})
                lp_burned = lp_data.get('lpBurned', False)
                lp_locked_pct = float(lp_data.get('lpLockedPct', 0))
                lp_locked = lp_locked_pct >= 100 or lp_burned
                lp_lock_timestamp = lp_data.get('lpLockedUntil', 0)
                if lp_lock_timestamp > 0:
                    from datetime import timedelta
                    lock_until = datetime.fromtimestamp(lp_lock_timestamp / 1000)
                    lp_lock_days = (lock_until - datetime.now()).days

        # Holder concentration data
        top10_concentration = 0.0
        top1_concentration = 0.0
        if analysis_data:
            top_holders = analysis_data.get('top_holders', [])
            if top_holders and len(top_holders) >= 10:
                top10_concentration = sum(float(h.get('pct', 0)) * 100 for h in top_holders[:10])
            if top_holders:
                top1_concentration = float(top_holders[0].get('pct', 0)) * 100

        # Contract safety data
        mint_authority_active = False
        freeze_authority_active = False
        ownership_renounced = True
        if analysis_data:
            raw_report = analysis_data.get('raw_report', {})
            token_meta = raw_report.get('tokenMeta', {})
            mint_authority = token_meta.get('mintAuthority')
            freeze_authority = token_meta.get('freezeAuthority')
            update_authority = token_meta.get('updateAuthority')
            mint_authority_active = bool(mint_authority and mint_authority != 'null' and mint_authority != '')
            freeze_authority_active = bool(freeze_authority and freeze_authority != 'null' and freeze_authority != '')
            ownership_renounced = not bool(update_authority and update_authority != 'null' and update_authority != '')

        # Momentum data (extract from profile)
        price_change_1h = 0.0
        price_change_5min = 0.0
        price_change_1min = 0.0
        volume_spike_ratio = 0.0
        buy_pressure_recent = 0.0
        momentum_accelerating = False
        if analysis_data:
            profile = analysis_data.get('profile', {})
            price_change_1h = profile.get('price_change_h1', 0.0)
            price_change_5min = profile.get('price_change_m5', 0.0)
            price_change_1min = profile.get('price_change_m1', 0.0)

            # Calculate volume spike ratio
            volume_1h_calc = profile.get('volume_1h', 0)
            volume_24h_calc = profile.get('volume', 0)
            volume_24h_avg_hourly = volume_24h_calc / 24 if volume_24h_calc > 0 else 0
            volume_spike_ratio = volume_1h_calc / volume_24h_avg_hourly if volume_24h_avg_hourly > 0 else 0

            # Calculate buy pressure
            txns_m5_buys = profile.get('txns_m5_buys', profile.get('txns_h1_buys', 0) / 12)
            txns_m5_sells = profile.get('txns_m5_sells', profile.get('txns_h1_sells', 0) / 12)
            total_recent = txns_m5_buys + txns_m5_sells
            buy_pressure_recent = (txns_m5_buys / total_recent * 100) if total_recent > 0 else 0

            # Check momentum acceleration
            if price_change_1h > 0 and price_change_5min > 0 and price_change_1min > 0:
                rate_1m = price_change_1min / 1
                rate_5m = price_change_5min / 5
                rate_1h = price_change_1h / 60
                momentum_accelerating = (rate_1m >= rate_5m >= rate_1h)

        # Open position with actual entry price (after slippage) and enhanced tracking data
        position = self.position_manager.open_position(
            token_address=token_address,
            entry_price=actual_entry_price,
            amount_usd=amount_usd - buy_fee,  # Reduce position by fee
            stop_loss=stop_loss,
            take_profit=take_profit,
            use_trailing_stop=use_trailing_stop,
            trailing_stop_percent=trailing_stop_percent,
            volume_fallback=is_volume_fallback,  # Mark volume fallback trades for analysis
            # Enhanced tracking fields for analysis
            entry_liquidity=entry_liquidity,
            volume_24h=tracking_volume_24h,
            volume_1h=volume_1h,
            opportunity_score=opportunity_score,  # Score from _calculate_opportunity_score()
            token_source=token_source,
            dex_platform=dex_platform,
            # Configuration tracking (for CSV analysis)
            config_stop_loss_percent=config_stop_loss_percent,
            config_trailing_activation_percent=config_trailing_activation_percent,
            config_trailing_distance_percent=config_trailing_distance_percent,
            # Transaction activity tracking
            txns_h1_buys=txns_h1_buys,
            txns_h1_sells=txns_h1_sells,
            # === 455-TRADE OPTIMIZATION TRACKING ===
            position_multiplier_applied=position_multiplier,
            golden_range_bonus=golden_range_bonus,
            preferred_price_bonus=preferred_price_bonus,
            original_position_size=original_amount,
            lp_locked=lp_locked,
            lp_burned=lp_burned,
            lp_lock_days=lp_lock_days,
            top10_concentration=top10_concentration,
            top1_concentration=top1_concentration,
            mint_authority_active=mint_authority_active,
            freeze_authority_active=freeze_authority_active,
            ownership_renounced=ownership_renounced,
            price_change_1h=price_change_1h,
            price_change_5min=price_change_5min,
            price_change_1min=price_change_1min,
            volume_spike_ratio=volume_spike_ratio,
            buy_pressure_recent=buy_pressure_recent,
            momentum_accelerating=momentum_accelerating
        )

        if not position:
            return {
                'status': 'failed',
                'reason': 'position_creation_failed'
            }

        # Deduct from capital (full amount including fees)
        self.current_capital -= amount_usd
        self.total_invested += amount_usd

        mode_str = f"trailing {trailing_stop_percent}%" if use_trailing_stop else f"TP ${take_profit:.8f}"
        logger.info(
            f"[PAPER] BUY {token_address[:8]}... "
            f"@ ${price:.8f}, size: ${amount_usd:.2f}, "
            f"{mode_str}, capital: ${self.current_capital:.2f}"
        )

        # Save state after trade
        self.save_state()

        return {
            'status': 'success',
            'action': 'buy',
            'token_address': token_address,
            'price': price,
            'amount_usd': amount_usd,
            'quantity': position.quantity,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'use_trailing_stop': use_trailing_stop,
            'trailing_stop_percent': trailing_stop_percent,
            'remaining_capital': self.current_capital,
            'timestamp': datetime.now().isoformat()
        }

    async def execute_sell(
        self,
        token_address: str,
        price: float,
        reason: str = 'manual',
        current_liquidity: float = 0.0,
        volume_24h: float = 0.0
    ) -> Dict:
        """
        Execute a simulated sell order.

        Args:
            token_address: Token contract address
            price: Current token price
            reason: Reason for selling
            current_liquidity: Current liquidity in USD (for realistic exit checks)
            volume_24h: Current 24h volume in USD (for realistic exit checks)

        Returns:
            Execution result dictionary
        """
        # Check if position exists
        position = self.position_manager.get_position(token_address)
        if not position:
            logger.warning(f"No position to sell for {token_address}")
            return {
                'status': 'failed',
                'reason': 'no_position'
            }

        # REALISTIC EXIT LIQUIDITY CHECK (prevents selling tokens with zero liquidity)
        # Analysis showed 29.4% of trades had ZERO liquidity at exit
        if current_liquidity > 0 and current_liquidity < self.min_exit_liquidity:
            self.rejected_trades['low_exit_liquidity'] += 1
            position_value = position.quantity * price

            # FORCE CLOSE if enabled (for live trading - better to accept loss than block slot)
            if self.force_close_on_rug:
                logger.error(
                    f"🚫 CANNOT SELL {token_address[:8]}... - Insufficient liquidity!\n"
                    f"   Exit Liquidity: ${current_liquidity:,.0f} < ${self.min_exit_liquidity:,.0f}\n"
                    f"   Position Value: ${position_value:,.2f}\n"
                    f"   ⚠️  FORCING POSITION CLOSURE (write-off to free slot)"
                )

                # Force close the position
                self.rejected_trades['forced_cleanup'] += 1
                trade = self.position_manager.force_close_position(
                    token_address,
                    reason='insufficient_exit_liquidity'
                )

                # Save state
                self.save_state()

                return {
                    'status': 'forced_close',
                    'reason': 'insufficient_exit_liquidity',
                    'current_liquidity': current_liquidity,
                    'loss': position.amount_usd
                }
            else:
                # Just log and return failure (paper trading mode)
                logger.error(
                    f"🚫 CANNOT SELL {token_address[:8]}... - Liquidity too low!\n"
                    f"   Exit Liquidity: ${current_liquidity:,.0f} < ${self.min_exit_liquidity:,.0f}\n"
                    f"   Position Value: ${position_value:,.2f}\n"
                    f"   In live trading, you'd be STUCK with this token!"
                )
                return {
                    'status': 'failed',
                    'reason': 'insufficient_exit_liquidity',
                    'current_liquidity': current_liquidity,
                    'min_required': self.min_exit_liquidity,
                    'position_value': position_value
                }

        # Warn if position is large relative to liquidity (high price impact expected)
        if current_liquidity > 0:
            position_value = position.quantity * price
            position_vs_liquidity = position_value / current_liquidity
            if position_vs_liquidity > 0.05:  # >5% of liquidity
                logger.warning(
                    f"⚠️  HIGH PRICE IMPACT: {token_address[:8]}... position is "
                    f"{position_vs_liquidity*100:.1f}% of liquidity "
                    f"(${position_value:.0f} vs ${current_liquidity:,.0f})"
                )

        # Apply sell fees and slippage if enabled
        actual_exit_price = price
        sell_fee = 0.0
        sell_slippage_cost = 0.0
        gross_proceeds = position.quantity * price

        if self.simulate_fees:
            # Slippage means we get a worse price
            slippage_multiplier = 1 - (self.sell_slippage_percent / 100)
            actual_exit_price = price * slippage_multiplier
            sell_slippage_cost = gross_proceeds * (self.sell_slippage_percent / 100)

            # Fee is deducted from proceeds
            sell_fee = gross_proceeds * (self.sell_fee_percent / 100)

            # Track total costs
            self.total_fees_paid += sell_fee
            self.total_slippage_cost += sell_slippage_cost

            logger.debug(
                f"💸 Sell costs: Fee ${sell_fee:.2f} ({self.sell_fee_percent}%), "
                f"Slippage ${sell_slippage_cost:.2f} ({self.sell_slippage_percent}%), "
                f"Exit ${price:.8f} → ${actual_exit_price:.8f}"
            )

        # Record position state before closing (for ML)
        position_snapshot = Position(
            token_address=position.token_address,
            entry_price=position.entry_price,
            current_price=position.current_price,
            amount_usd=position.amount_usd,
            quantity=position.quantity,
            entry_time=position.entry_time,
            stop_loss=position.stop_loss,
            take_profit=position.take_profit,
            use_trailing_stop=position.use_trailing_stop,
            trailing_stop_percent=position.trailing_stop_percent,
            highest_price=position.highest_price,
            trailing_stop_price=position.trailing_stop_price,
            last_price_update=position.last_price_update,
            current_liquidity=position.current_liquidity,
            price_update_failures=position.price_update_failures,
            initial_quantity=position.initial_quantity,
            milestones_hit=position.milestones_hit.copy(),
            symbol=position.symbol
        )

        # Close position with actual exit price (after slippage)
        trade = self.position_manager.close_position(
            token_address=token_address,
            exit_price=actual_exit_price,
            reason=reason
        )

        if not trade:
            return {
                'status': 'failed',
                'reason': 'close_failed'
            }

        # Record trade for ML training
        self._record_ml_trade(trade, position_snapshot, reason)

        # === RECORD TO TOKEN PERFORMANCE TRACKER (if enabled) ===
        if self.enable_token_tracker and self.token_tracker:
            self.token_tracker.record_trade(
                token_address=token_address,
                pnl=trade.pnl,
                pnl_percent=trade.pnl_percent,
                symbol=trade.symbol,
                timestamp=trade.timestamp
            )

        # Add proceeds to capital (after fees)
        net_proceeds = trade.amount_usd - sell_fee
        capital_before = self.current_capital
        self.current_capital += net_proceeds
        self.total_invested -= position.amount_usd

        logger.info(
            f"[PAPER] SELL {token_address[:8]}... "
            f"@ ${actual_exit_price:.8f}, proceeds: ${net_proceeds:.2f}, "
            f"capital: ${capital_before:.2f} → ${self.current_capital:.2f}, "
            f"PnL: ${trade.pnl:.2f} ({trade.pnl_percent:+.1f}%)"
        )

        # Save state after trade
        self.save_state()

        return {
            'status': 'success',
            'action': 'sell',
            'token_address': token_address,
            'price': price,
            'amount_usd': trade.amount_usd,
            'quantity': trade.quantity,
            'pnl': trade.pnl,
            'pnl_percent': trade.pnl_percent,
            'reason': reason,
            'remaining_capital': self.current_capital,
            'timestamp': datetime.now().isoformat()
        }

    async def update_prices(self, price_updates: Dict[str, float], liquidity_data: Dict[str, float] = None):
        """
        Update positions with current prices and check stop loss/take profit/trailing stop.

        Args:
            price_updates: Dictionary of token_address -> current_price
            liquidity_data: Dictionary of token_address -> liquidity_usd (optional)
        """
        if liquidity_data is None:
            liquidity_data = {}

        # First, update all prices so we have fresh timestamps
        # (prevents false positives when bot restarts after being offline)
        for token_address, current_price in price_updates.items():
            if token_address not in self.position_manager.open_positions:
                continue

            liquidity = liquidity_data.get(token_address, 0.0)

            # Update position price and liquidity (updates last_price_update timestamp)
            self.position_manager.update_position_price(token_address, current_price, liquidity)

        # NOW check for dead/rugged positions (after applying fresh data)
        # This prevents false positives when restarting after being offline
        if self.rug_detection_enabled:
            dead_positions = self.position_manager.get_dead_positions(
                stale_minutes=self.stale_price_minutes,
                min_liquidity=self.min_position_liquidity,
                freeze_minutes=self.frozen_price_minutes
            )
        else:
            dead_positions = []

        for token_address in dead_positions:
            position = self.position_manager.get_position(token_address)
            if position:
                # Use current price if available, otherwise assume rugged ($0)
                exit_price = position.current_price if position.current_price > 0 else 0.00000001
                potential_loss = position.amount_usd - (position.quantity * exit_price)

                logger.error(
                    f"💀 AUTO-CLOSING DEAD TOKEN: {token_address[:8]}... "
                    f"Entry: ${position.entry_price:.8f}, "
                    f"Last known: ${position.current_price:.8f}, "
                    f"Exit at: ${exit_price:.8f}, "
                    f"Potential loss: ${potential_loss:.2f}"
                )
                await self.execute_sell(token_address, exit_price, reason='low_liquidity')

        # BATCH 10 FIX: Check for rapid liquidity drops (exit before 100% drop!)
        # Analysis showed ALL trades ended with 0 exit liquidity - catch them early!
        if self.enable_liquidity_monitoring:
            for token_address in list(self.position_manager.open_positions.keys()):
                position = self.position_manager.get_position(token_address)
                if not position:
                    continue

                # Calculate liquidity drop % from entry
                if position.entry_liquidity > 0 and position.current_liquidity > 0:
                    liquidity_drop_pct = ((position.entry_liquidity - position.current_liquidity) / position.entry_liquidity) * 100

                    # Early exit if liquidity dropping fast (prevents 100% drop!)
                    if liquidity_drop_pct >= self.liquidity_drop_threshold:
                        exit_price = position.current_price if position.current_price > 0 else 0.00000001

                        logger.warning(
                            f"⚠️ LIQUIDITY DROP ALERT: {token_address[:8]}... "
                            f"Entry liq: ${position.entry_liquidity:,.0f}, "
                            f"Current liq: ${position.current_liquidity:,.0f}, "
                            f"Drop: {liquidity_drop_pct:.1f}% (threshold: {self.liquidity_drop_threshold:.0f}%)\n"
                            f"   🚨 EXITING EARLY to avoid 100% liquidity drop!"
                        )

                        await self.execute_sell(token_address, exit_price, reason='liquidity_drop')

                # Also check if liquidity went to 0 (catch even if entry_liquidity was 0)
                elif position.current_liquidity == 0 and position.entry_liquidity > 0:
                    exit_price = position.current_price if position.current_price > 0 else 0.00000001

                    logger.error(
                        f"🚨 LIQUIDITY DISAPPEARED: {token_address[:8]}... "
                        f"Entry liq: ${position.entry_liquidity:,.0f} → Current: $0\n"
                        f"   💀 Token completely rugged!"
                    )

                    await self.execute_sell(token_address, exit_price, reason='liquidity_disappeared')

        # Check for partial profit milestones (before stop loss/take profit checks)
        if self.partial_profit_enabled:
            for token_address in list(self.position_manager.open_positions.keys()):
                position = self.position_manager.get_position(token_address)
                if not position or position.initial_quantity == 0:
                    continue

                milestone = position.check_profit_milestone()
                if milestone:
                    # Determine sell percentage based on milestone
                    sell_pct = 0
                    if milestone == 100:
                        sell_pct = self.profit_milestone_100
                    elif milestone == 200:
                        sell_pct = self.profit_milestone_200
                    elif milestone == 300:
                        sell_pct = self.profit_milestone_300
                    elif milestone == 400:
                        sell_pct = self.profit_milestone_400
                    elif milestone == 500:
                        sell_pct = self.profit_milestone_500
                    elif milestone == 600:
                        sell_pct = self.profit_milestone_600
                    elif milestone == 700:
                        sell_pct = self.profit_milestone_700

                    if sell_pct > 0:
                        # Calculate quantity to sell (percentage of INITIAL quantity, not current)
                        sell_quantity = (sell_pct / 100) * position.initial_quantity
                        sell_quantity = min(sell_quantity, position.quantity)  # Don't sell more than we have

                        if sell_quantity > 0:
                            # Execute partial sell
                            sell_value = sell_quantity * position.current_price
                            logger.info(
                                f"💰 PARTIAL PROFIT at +{milestone}%: {token_address[:8]}... "
                                f"Selling {sell_pct}% ({sell_quantity:.2f} tokens) = ${sell_value:.2f}"
                            )

                            # Reduce position quantity AND amount_usd to reflect smaller position
                            position.quantity -= sell_quantity
                            position.amount_usd = position.quantity * position.entry_price  # Update cost basis
                            position.milestones_hit.add(milestone)

                            # Add proceeds to capital
                            self.current_capital += sell_value
                            # Reduce total_invested since we sold part of the position
                            self.total_invested -= (sell_quantity * position.entry_price)

                            # Calculate profit on this partial sell
                            cost_basis = (position.entry_price * sell_quantity)
                            partial_profit = sell_value - cost_basis

                            logger.info(
                                f"💵 Locked in ${partial_profit:.2f} profit, "
                                f"Remaining: {position.quantity:.2f} tokens (${position.amount_usd:.2f} cost basis)"
                            )

                            # Save state after partial sell
                            self.save_state()

        # Now check stop loss/take profit/trailing stop for remaining positions
        for token_address in list(self.position_manager.open_positions.keys()):
            # Get current position price (don't use undefined variable!)
            position = self.position_manager.get_position(token_address)
            if not position:
                continue

            current_price = position.current_price

            # Check stop loss (regular stop loss, for downside protection)
            if self.position_manager.check_stop_loss(token_address):
                logger.info(f"Stop loss triggered for {token_address[:8]}...")
                await self.execute_sell(token_address, current_price, reason='stop_loss')

            # Check trailing stop (locks in profits)
            elif self.position_manager.check_trailing_stop(token_address):
                await self.execute_sell(token_address, current_price, reason='trailing_stop')

            # Check take profit (only if not using trailing stop)
            elif self.position_manager.check_take_profit(token_address):
                logger.info(f"Take profit triggered for {token_address[:8]}...")
                await self.execute_sell(token_address, current_price, reason='take_profit')

    def get_portfolio_value(self) -> float:
        """
        Get current total portfolio value.

        Returns:
            Portfolio value in USD
        """
        positions_value = sum(
            pos.quantity * pos.current_price
            for pos in self.position_manager.get_all_positions()
        )
        return self.current_capital + positions_value

    def get_performance_summary(self) -> Dict:
        """
        Get comprehensive performance summary.

        Returns:
            Dictionary with performance metrics
        """
        portfolio_value = self.get_portfolio_value()
        total_pnl = portfolio_value - self.initial_capital
        total_return = (total_pnl / self.initial_capital * 100) if self.initial_capital > 0 else 0

        stats = self.position_manager.get_statistics()

        return {
            'initial_capital': self.initial_capital,
            'current_capital': self.current_capital,
            'invested_capital': self.total_invested,
            'portfolio_value': portfolio_value,
            'total_pnl': total_pnl,
            'total_return_percent': total_return,
            'realized_pnl': stats['total_realized_pnl'],
            'unrealized_pnl': stats['total_unrealized_pnl'],
            'open_positions': stats['open_positions'],
            'total_trades': stats['total_trades'],
            'winning_trades': stats['winning_trades'],
            'losing_trades': stats['losing_trades'],
            'win_rate': stats['win_rate'],
            'avg_win': stats['avg_win'],
            'avg_loss': stats['avg_loss'],
            'timestamp': datetime.now().isoformat()
        }

    def reset(self):
        """Reset the paper trading engine to initial state."""
        self.current_capital = self.initial_capital
        self.total_invested = 0.0
        # Use same max_positions from .env as initialization
        max_positions = int(os.getenv('MAX_OPEN_POSITIONS', '7'))
        self.position_manager = PositionManager(max_open_positions=max_positions)
        logger.info("Paper trading engine reset")

    def save_state(self):
        """Save current state to file for persistence."""
        try:
            state = {
                'initial_capital': self.initial_capital,
                'current_capital': self.current_capital,
                'total_invested': self.total_invested,
                'positions': {},
                'trades': []
            }

            # Save positions
            for token_addr, pos in self.position_manager.open_positions.items():
                state['positions'][token_addr] = {
                    'token_address': pos.token_address,
                    'entry_price': pos.entry_price,
                    'current_price': pos.current_price,
                    'amount_usd': pos.amount_usd,
                    'quantity': pos.quantity,
                    'stop_loss': pos.stop_loss,
                    'take_profit': pos.take_profit,
                    'entry_time': pos.entry_time.isoformat(),
                    'use_trailing_stop': pos.use_trailing_stop,
                    'trailing_stop_percent': pos.trailing_stop_percent,
                    'highest_price': pos.highest_price,
                    'trailing_stop_price': pos.trailing_stop_price,
                    'last_price_update': pos.last_price_update.isoformat(),
                    'last_price_change': pos.last_price_change.isoformat(),  # Frozen price detection
                    'last_known_price': pos.last_known_price,  # Frozen price detection
                    'current_liquidity': pos.current_liquidity,
                    'price_update_failures': pos.price_update_failures,
                    'initial_quantity': pos.initial_quantity,  # Partial profit tracking
                    'milestones_hit': list(pos.milestones_hit)  # Convert set to list for JSON
                }

            # Save recent trades (last 100)
            for trade in self.position_manager.closed_trades[-100:]:
                state['trades'].append({
                    'token_address': trade.token_address,
                    'action': trade.action,
                    'price': trade.price,
                    'amount_usd': trade.amount_usd,
                    'quantity': trade.quantity,
                    'pnl': trade.pnl,
                    'pnl_percent': trade.pnl_percent,
                    'timestamp': trade.timestamp.isoformat()
                })

            # Write to file
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)

            logger.info(
                f"💾 State saved: ${self.current_capital:.2f} capital, "
                f"{len(self.position_manager.open_positions)} positions → {self.state_file}"
            )

        except Exception as e:
            logger.error(f"❌ Error saving state to {self.state_file}: {e}", exc_info=True)

    def load_state(self):
        """Load state from file."""
        try:
            if not os.path.exists(self.state_file):
                logger.info(f"📝 No previous state file found at {self.state_file}, starting fresh")
                return

            logger.info(f"📂 Loading state from {self.state_file}...")

            with open(self.state_file, 'r') as f:
                state = json.load(f)

            # Restore capital
            self.initial_capital = state.get('initial_capital', self.initial_capital)
            self.current_capital = state.get('current_capital', self.current_capital)
            self.total_invested = state.get('total_invested', 0.0)

            # Restore positions
            for token_addr, pos_data in state.get('positions', {}).items():
                position = Position(
                    token_address=pos_data['token_address'],
                    entry_price=pos_data['entry_price'],
                    current_price=pos_data['current_price'],
                    amount_usd=pos_data['amount_usd'],
                    quantity=pos_data['quantity'],
                    entry_time=datetime.fromisoformat(pos_data['entry_time']),
                    stop_loss=pos_data['stop_loss'],
                    take_profit=pos_data['take_profit'],
                    use_trailing_stop=pos_data.get('use_trailing_stop', self.use_trailing_stop),
                    trailing_stop_percent=pos_data.get('trailing_stop_percent', self.trailing_stop_percent),
                    highest_price=pos_data.get('highest_price', pos_data['entry_price']),
                    trailing_stop_price=pos_data.get('trailing_stop_price', pos_data['stop_loss']),
                    last_price_update=datetime.fromisoformat(pos_data.get('last_price_update', pos_data['entry_time'])),
                    last_price_change=datetime.fromisoformat(pos_data.get('last_price_change', pos_data['entry_time'])),  # Frozen price detection
                    last_known_price=pos_data.get('last_known_price', pos_data['entry_price']),  # Frozen price detection
                    current_liquidity=pos_data.get('current_liquidity', 0.0),
                    price_update_failures=pos_data.get('price_update_failures', 0),
                    initial_quantity=pos_data.get('initial_quantity', pos_data['quantity']),  # Partial profit tracking
                    milestones_hit=set(pos_data.get('milestones_hit', []))  # Convert list back to set
                )

                # CRITICAL: Recalculate P&L after restoration (update_price wasn't called)
                position.update_price(position.current_price, position.current_liquidity)

                self.position_manager.open_positions[token_addr] = position
                pnl_pct = position.unrealized_pnl_percent
                mode = "🔄 trailing" if position.use_trailing_stop else "🎯 fixed TP"
                logger.info(f"   ✓ Restored position: {token_addr[:8]}... ({pnl_pct:+.2f}%, {mode})")

            # Restore trades
            for trade_data in state.get('trades', []):
                trade = Trade(
                    token_address=trade_data['token_address'],
                    action=trade_data['action'],
                    price=trade_data['price'],
                    amount_usd=trade_data['amount_usd'],
                    quantity=trade_data['quantity'],
                    timestamp=datetime.fromisoformat(trade_data['timestamp']),
                    pnl=trade_data.get('pnl', 0.0),
                    pnl_percent=trade_data.get('pnl_percent', 0.0)
                )
                self.position_manager.closed_trades.append(trade)

            logger.info(
                f"✅ State loaded: ${self.current_capital:.2f} capital, "
                f"{len(self.position_manager.open_positions)} positions, "
                f"{len(self.position_manager.closed_trades)} trades"
            )

        except Exception as e:
            logger.error(f"❌ Error loading state from {self.state_file}: {e}", exc_info=True)
            logger.warning("⚠️  Starting with fresh state due to load error")

    async def health_check(self) -> bool:
        """
        Health check for paper trading engine.

        Returns:
            True if healthy
        """
        return True  # Paper trading is always healthy
