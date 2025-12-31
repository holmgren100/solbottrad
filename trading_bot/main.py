"""
ML Bot 2 Foundation - Main Trading Bot

Integrates:
- 🔒 Protected core (RiskAssessor, PositionManager, PriceValidator)
- ✅ Optional enhancements (CSVTracker, SafetyFilters)

Architecture Pattern:
- Core is NEVER modified
- Enhancements wrap around core
- All features toggleable via .env

Performance Target:
- 71.7%+ win rate (ML Bot 2 baseline)
- $30+ avg profit per trade
- 9x+ profit factor

Usage:
    python trading_bot/main.py
"""

import asyncio
import logging
import sys
from datetime import datetime
from typing import Dict, Optional

# Add parent directory to path for imports
sys.path.insert(0, '.')

from ml_bot_core import RiskAssessor, PositionManager, PriceValidator, DEFAULT_CONFIG
from ml_bot_core.monitoring.logger import configure_logging
from enhanced_modules import CSVTracker, SafetyFilters
from trading_bot.config import load_config, BotConfig

logger = logging.getLogger(__name__)


class MLBot2Foundation:
    """
    ML Bot 2 Foundation - Protected Core + Optional Enhancements

    This bot demonstrates the architecture pattern:
    1. Protected core handles selection and exits (NEVER modified)
    2. Optional enhancements wrap around core (toggleable)
    3. Configuration via .env (easy A/B testing)
    """

    def __init__(self, config: BotConfig):
        """
        Initialize ML Bot 2 Foundation.

        Args:
            config: Bot configuration
        """
        self.config = config
        self.running = False

        # === 🔒 PROTECTED CORE (Never Modified!) ===
        logger.info("Initializing protected core...")

        self.risk_assessor = RiskAssessor(
            max_position_size=config.default_position_size
        )
        logger.info("  ✅ RiskAssessor initialized")

        self.position_manager = PositionManager(
            max_open_positions=config.core_config.max_open_positions
        )
        logger.info("  ✅ PositionManager initialized")

        # Initialize PriceValidator with API clients
        from trading_bot.api_clients import DexScreenerClient, JupiterClient, SolscanClient
        dexscreener_client = DexScreenerClient(api_key=config.dexscreener_api_key)
        jupiter_client = JupiterClient()

        self.price_validator = PriceValidator(
            dexscreener_client=dexscreener_client,
            jupiter_client=jupiter_client
        )
        logger.info("  ✅ PriceValidator initialized")

        # Initialize SolscanClient for holder analysis
        if config.solscan_api_key:
            self.solscan_client = SolscanClient(api_key=config.solscan_api_key)
            logger.info("  ✅ SolscanClient initialized (holder analysis enabled)")
        else:
            self.solscan_client = None
            logger.warning("  ⚠️  SolscanClient disabled - no API key (holder data unavailable)")

        # === ✅ OPTIONAL ENHANCEMENTS ===
        logger.info("Initializing enhancement modules...")

        # CSV Tracker (recommended!)
        if config.enable_csv_tracking:
            self.csv_tracker = CSVTracker(
                enabled=True,
                auto_export=config.csv_auto_export
            )
            self.csv_tracker.export_path = config.csv_export_path
            logger.info(f"  ✅ CSVTracker enabled (export to {config.csv_export_path})")
        else:
            self.csv_tracker = None
            logger.warning("  ⚠️  CSVTracker disabled - no data for optimization!")

        # Rejected Tracker (learn from what you're missing!)
        from enhanced_modules import RejectedTracker
        self.rejected_tracker = RejectedTracker(export_path='data/rejected_trades.csv')
        logger.info("  ✅ RejectedTracker enabled (learn from rejected tokens)")

        # Safety Filters (test impact!)
        if config.enable_safety_filters:
            self.safety_filters = SafetyFilters(
                enabled=True,
                config=config.safety_config
            )
            logger.info(f"  ✅ SafetyFilters enabled: {self.safety_filters}")
            logger.warning("  ⚠️  Testing safety filters - compare results to baseline!")
        else:
            self.safety_filters = None
            logger.info("  ℹ️  SafetyFilters disabled (ML Bot 2 baseline mode)")

        # === 📱 TELEGRAM NOTIFICATIONS ===
        if config.telegram_bot_token and config.telegram_chat_id:
            from ml_bot_core.monitoring.telegram_notifier import TelegramNotifier
            from ml_bot_core.monitoring.telegram_commands import TelegramCommandHandler

            self.notifier = TelegramNotifier(
                bot_token=config.telegram_bot_token,
                chat_id=config.telegram_chat_id
            )
            self.command_handler = TelegramCommandHandler(
                bot_token=config.telegram_bot_token,
                chat_id=config.telegram_chat_id,
                bot_instance=self
            )
            logger.info("  ✅ Telegram notifications and commands enabled")
        else:
            self.notifier = None
            self.command_handler = None
            logger.info("  ℹ️  Telegram notifications disabled (no credentials)")

        # === 🔍 TOKEN SCANNER ===
        from trading_bot.scanner import TokenScanner
        self.scanner = TokenScanner(
            min_liquidity=1000,  # Lowered to let Jupiter tokens through (they often lack liquidity data)
            min_volume_24h=1000,  # Lowered to match working bot settings
            dexscreener_api_key=config.dexscreener_api_key,
            position_manager=self.position_manager
        )
        logger.info("  ✅ TokenScanner initialized (with trade history filter)")

        # === 💰 TRADE EXECUTOR ===
        from trading_bot.executor import PaperTradingExecutor
        if config.paper_trading:
            self.executor = PaperTradingExecutor(initial_capital=config.paper_initial_capital)
            logger.info(f"  ✅ PaperTradingExecutor initialized (${config.paper_initial_capital:.2f} USD)")
        else:
            raise NotImplementedError("Live trading not implemented yet! Use PAPER_TRADING_MODE=true")

        # Compatibility attributes for TelegramCommandHandler
        self.trading_engine = self.executor  # Alias for telegram commands
        self.trading_engine.position_manager = self.position_manager  # Add position_manager to executor
        self.trading_engine.stuck_liquidity_threshold = 1000.0  # Compatibility attribute
        self.trading_engine.stuck_time_hours = 24.0  # Compatibility attribute
        self.trading_engine.max_position_age_hours = 72.0  # Compatibility attribute

        # Connect executor to position_manager for state persistence
        self.position_manager.executor = self.executor
        # Reload executor state if it was saved (position_manager loads state in __init__ but executor didn't exist yet)
        if self.position_manager.enable_persistence and self.position_manager.state_persistence:
            state = self.position_manager.state_persistence.load_state()
            if state and state.get('executor_state'):
                self.executor.restore_state(state['executor_state'])
                logger.info("  ✅ Executor state restored from saved data")

        self.settings = type('Settings', (), {
            'is_paper_trading': lambda self: config.paper_trading,  # Fixed: lambda needs self parameter
            'trading': type('Trading', (), {
                'max_position_size': config.default_position_size,
                'min_liquidity_usd': config.core_config.min_position_liquidity,
                'min_confidence_score': 0.5  # Default value
            })()
        })()

        logger.info("✅ Initialization complete!")

    async def analyze_token(
        self,
        token_address: str,
        market_data: Dict,
        security_data: Dict,
        sentiment_score: Dict,
        price_prediction: Dict
    ) -> tuple[bool, float, str]:
        """
        Analyze token with optional pre-filters + protected core.

        Flow:
        1. Optional safety pre-filter (if enabled)
        2. 🔒 Protected core RiskAssessor (always runs)
        3. Optional CSV tracking (if enabled)

        Args:
            token_address: Token contract address
            market_data: Market data (liquidity, volume, etc.)
            security_data: Security analysis (mint authority, etc.)
            sentiment_score: Sentiment analysis results
            price_prediction: Price prediction results

        Returns:
            Tuple of (should_trade, risk_score, reason)
        """
        # === OPTIONAL: Safety Pre-Filter ===
        if self.safety_filters and self.safety_filters.enabled:
            # Prepare token data for safety check
            token_data = {
                'lp_locked': security_data.get('lp_locked', False),
                'lp_burned': security_data.get('lp_burned', False),
                'lp_lock_days': security_data.get('lp_lock_days', 0),
                'top10_concentration': security_data.get('top10_concentration', 100.0),
                'top1_concentration': security_data.get('top1_concentration', 100.0),
                'mint_authority_active': security_data.get('is_mintable', False),
                'freeze_authority_active': security_data.get('has_freeze_authority', False),
                'ownership_renounced': security_data.get('ownership_renounced', False),
            }

            passed, reason = self.safety_filters.check_all(token_data)

            if not passed:
                logger.info(f"🚫 Safety filter blocked: {token_address[:8]}... - {reason}")

                # Track rejection if CSV enabled
                if self.csv_tracker:
                    # Could log rejections separately for analysis
                    pass

                return False, 1.0, f"safety_filter_{reason}"

        # === 🔒 PROTECTED CORE: Risk Assessment ===
        # This is NEVER bypassed - always runs!
        assessment = self.risk_assessor.assess_risk(
            token_address=token_address,
            market_data=market_data,
            security_data=security_data,
            sentiment_score=sentiment_score,
            price_prediction=price_prediction
        )

        should_trade = assessment.should_trade
        risk_score = assessment.risk_score
        reason = assessment.overall_risk

        if should_trade:
            logger.info(
                f"✅ Token approved: {token_address[:8]}... "
                f"(risk: {risk_score:.2f}, position: {assessment.recommended_position_size:.2f})"
            )
        else:
            logger.info(
                f"❌ Token rejected: {token_address[:8]}... "
                f"(risk: {risk_score:.2f} - {reason})"
            )

        # === OPTIONAL: Track Analysis ===
        if self.csv_tracker:
            # Could log all analyses for review
            pass

        return should_trade, risk_score, reason

    async def open_position(
        self,
        token_address: str,
        entry_price: float,
        amount_usd: float,
        symbol: str = '',
        entry_liquidity: float = 0.0,
        **kwargs  # Accept all additional tracking fields
    ) -> Optional[object]:
        """
        Open a new position using protected core.

        Args:
            token_address: Token address
            entry_price: Entry price
            amount_usd: Position size in USD
            symbol: Token symbol (optional)
            entry_liquidity: Entry liquidity for drop % tracking

        Returns:
            Position object or None if failed
        """
        # Calculate stop loss and take profit
        stop_loss = self.risk_assessor.calculate_stop_loss(
            entry_price,
            self.config.core_config.stop_loss_percent
        )
        take_profit = self.risk_assessor.calculate_take_profit(
            entry_price,
            self.config.core_config.take_profit_percent
        )

        # 🔒 PROTECTED CORE: Open position
        position = self.position_manager.open_position(
            token_address=token_address,
            entry_price=entry_price,
            amount_usd=amount_usd,
            stop_loss=stop_loss,
            take_profit=take_profit,
            use_trailing_stop=self.config.core_config.use_trailing_stop,
            trailing_stop_percent=self.config.core_config.trailing_stop_percent,
            entry_liquidity=entry_liquidity,
            symbol=symbol,  # Pass symbol to position
            **kwargs  # Pass all additional tracking fields
        )

        if position:

            logger.info(
                f"📈 Position opened: {symbol or token_address[:8]}... "
                f"@ ${entry_price:.8f}, size: ${amount_usd:.2f}, "
                f"mode: {'trailing stop' if position.use_trailing_stop else 'fixed TP/SL'}"
            )

        return position

    async def close_position(
        self,
        token_address: str,
        exit_price: float,
        reason: str
    ) -> Optional[object]:
        """
        Close position and optionally track in CSV.

        Args:
            token_address: Token address
            exit_price: Exit price
            reason: Close reason (trailing_stop, stop_loss, etc.)

        Returns:
            Trade object or None if failed
        """
        # Get position before closing (for CSV tracking)
        position = self.position_manager.get_position(token_address)

        if not position:
            logger.warning(f"Cannot close position - no position found for {token_address[:8]}...")
            return None

        # ⚡ Fetch fresh token data at exit for volume/sentiment tracking
        try:
            fresh_data = await self.price_validator.dexscreener_client.get_token_profile(token_address)
            if fresh_data:
                # Update position with exit volumes and sentiment
                position.exit_volume_24h = fresh_data.get('volume_24h', 0.0)
                position.exit_volume_1h = fresh_data.get('volume_1h', 0.0)
                position.exit_txns_h1_buys = fresh_data.get('buys_1h', 0)
                position.exit_txns_h1_sells = fresh_data.get('sells_1h', 0)
                logger.debug(
                    f"📊 Exit data: Vol 24h: ${fresh_data.get('volume_24h', 0):,.0f}, "
                    f"1h: ${fresh_data.get('volume_1h', 0):,.0f}, "
                    f"Buys/Sells: {fresh_data.get('buys_1h', 0)}/{fresh_data.get('sells_1h', 0)}"
                )
            else:
                logger.debug(f"No fresh data available at exit for {token_address[:8]}...")
        except Exception as e:
            logger.debug(f"Error fetching exit data for {token_address[:8]}...: {e}")

        # 🔒 PROTECTED CORE: Close position
        trade = self.position_manager.close_position(
            token_address=token_address,
            exit_price=exit_price,
            reason=reason
        )

        if trade:
            logger.info(
                f"📉 Position closed: {trade.symbol or token_address[:8]}... "
                f"@ ${exit_price:.8f}, "
                f"PnL: ${trade.pnl:.2f} ({trade.pnl_percent:+.1f}%), "
                f"Reason: {reason}"
            )

            # === RETURN CAPITAL TO EXECUTOR ===
            # Execute sell to return capital (simulates selling tokens back to USD)
            sell_result = await self.executor.execute_sell(
                token_address=token_address,
                tokens_amount=trade.quantity,
                price_usd=exit_price,
                symbol=trade.symbol
            )

            if sell_result:
                logger.debug(f"Capital returned to executor: ${sell_result['usd_received']:.2f} USD")
            else:
                logger.error(f"Failed to return capital for {trade.symbol}")

            # === SEND EXIT NOTIFICATION ===
            if self.notifier:
                # Calculate hold time
                from datetime import datetime
                hold_time_hours = (datetime.now() - trade.entry_time).total_seconds() / 3600

                await self.notifier.send_exit_notification(
                    token_address=token_address,
                    symbol=trade.symbol,
                    entry_price=trade.entry_price,
                    exit_price=exit_price,
                    position_size=trade.amount_usd,
                    pnl=trade.pnl,
                    pnl_percent=trade.pnl_percent,
                    hold_time_hours=hold_time_hours,
                    exit_reason=reason,
                    liquidity_change=None  # Not tracked in Position dataclass
                )

            # === OPTIONAL: Track in CSV ===
            if self.csv_tracker and position:
                self.csv_tracker.log_trade(
                    position=position,
                    exit_reason=reason,
                    exit_price=exit_price
                )

        return trade

    async def monitor_positions(self):
        """
        Monitor all open positions and check exit conditions.

        Uses protected core PositionManager to:
        - Update prices
        - Check partial profits (if enabled)
        - Check stop loss
        - Check trailing stop
        - Detect rugs
        """
        positions = self.position_manager.get_all_positions()

        if not positions:
            return

        logger.debug(f"Monitoring {len(positions)} position(s)...")

        # Update all prices first
        for position in positions:
            # Get current price from PriceValidator
            try:
                price_data = await self.price_validator.get_validated_price(
                    position.token_address,
                    entry_price=position.entry_price
                )

                if not price_data or price_data[0] is None:
                    logger.warning(f"⚠️  No price data for {position.symbol or position.token_address[:8]}...")
                    continue

                # CRITICAL FIX: get_validated_price() returns TUPLE (price, liquidity, source), NOT dict!
                current_price, current_liquidity, data_source = price_data

                # Ensure liquidity is a number (not None)
                if current_liquidity is None:
                    current_liquidity = 0

                # Update position
                self.position_manager.update_position_price(
                    position.token_address,
                    current_price,
                    current_liquidity
                )

            except Exception as e:
                logger.error(f"Error getting price for {position.token_address[:8]}...: {e}")
                continue

        # === PARTIAL PROFIT TAKING (before stop loss/trailing stop checks) ===
        if self.config.partial_profit_settings.get('enabled', False):
            for position in list(self.position_manager.get_all_positions()):
                if position.initial_quantity == 0:
                    continue

                milestone = position.check_profit_milestone()
                if milestone:
                    # Determine sell percentage based on milestone
                    sell_pct = self.config.partial_profit_settings.get(f'milestone_{milestone}', 0)

                    if sell_pct > 0:
                        # Calculate quantity to sell (percentage of INITIAL quantity, not current)
                        sell_quantity = (sell_pct / 100) * position.initial_quantity
                        sell_quantity = min(sell_quantity, position.quantity)  # Don't sell more than we have

                        if sell_quantity > 0:
                            # Calculate proceeds
                            sell_value = sell_quantity * position.current_price

                            logger.info(
                                f"💰 PARTIAL PROFIT at +{milestone}%: {position.symbol or position.token_address[:8]}... "
                                f"Selling {sell_pct}% ({sell_quantity:.2f} tokens) = ${sell_value:.2f}"
                            )

                            # Update position in position manager
                            position.quantity -= sell_quantity
                            position.amount_usd = position.quantity * position.entry_price  # Update cost basis
                            position.milestones_hit.add(milestone)

                            # Update executor balance (add proceeds)
                            self.executor.current_capital += sell_value

                            # Calculate profit on this partial sell
                            cost_basis = position.entry_price * sell_quantity
                            partial_profit = sell_value - cost_basis

                            logger.info(
                                f"💵 Locked in ${partial_profit:.2f} profit, "
                                f"Remaining: {position.quantity:.2f} tokens (${position.amount_usd:.2f} cost basis)"
                            )

        # Check exit conditions for remaining positions
        for position in list(self.position_manager.get_all_positions()):
            # === EXIT PRIORITY (ML Bot Style) ===
            # 1. DRAWDOWN PRIMARY - Loser pattern detection (>30% drawdown)
            # 2. Stop Loss - Safety net
            # 3. Rug Detection - Severe only (70% liq drop + frozen)
            # 4. Trailing Stop - After winners develop
            # 5. Winner Hold Logic - Don't exit winners too early!

            # 1. DRAWDOWN PRIMARY - Check loser pattern FIRST!
            if position.is_loser_pattern():
                drawdown = position.get_drawdown_percent()
                duration = position.get_duration_minutes()
                logger.warning(
                    f"🚨 LOSER PATTERN: {position.symbol or position.token_address[:8]}... "
                    f"Drawdown: {drawdown:.1f}% (>{30}%), Duration: {duration:.0f}min"
                )
                await self.close_position(
                    position.token_address,
                    position.current_price,
                    'stop_loss'  # Use stop_loss reason for loser pattern
                )
                continue

            # 2. Stop Loss - Safety net (should rarely trigger if drawdown works)
            if self.position_manager.check_stop_loss(position.token_address):
                logger.warning(f"🛑 Stop loss hit: {position.symbol or position.token_address[:8]}...")
                await self.close_position(
                    position.token_address,
                    position.current_price,
                    'stop_loss'
                )
                continue

            # 3. Rug Detection - RELAXED (only severe cases)
            if self.config.core_config.rug_detection_enabled:
                dead_positions = self.position_manager.get_dead_positions(
                    stale_minutes=self.config.core_config.stale_price_minutes,
                    min_liquidity=self.config.core_config.min_position_liquidity
                )

                if position.token_address in dead_positions:
                    # === WINNER HOLD LOGIC ===
                    # If position shows winner pattern (low drawdown), hold longer!
                    # Don't exit on small liquidity fluctuations
                    if position.is_winner_pattern():
                        duration = position.get_duration_minutes()
                        drawdown = position.get_drawdown_percent()

                        # Winner pattern: Hold 25-35 min minimum (ML Bot style)
                        if duration < 25:
                            logger.info(
                                f"✅ WINNER HOLD: {position.symbol or position.token_address[:8]}... "
                                f"Low drawdown {drawdown:.1f}% - holding to 25+ min (now {duration:.0f}min)"
                            )
                            continue  # Skip exit, keep holding!

                        # Optimal exit window: 25-35 min
                        if duration < 35:
                            logger.info(
                                f"✅ WINNER OPTIMAL: {position.symbol or position.token_address[:8]}... "
                                f"In optimal window ({duration:.0f}min) - can exit or hold to 35min"
                            )
                            # Exit at optimal time
                        else:
                            logger.info(
                                f"✅ WINNER MATURE: {position.symbol or position.token_address[:8]}... "
                                f"Held {duration:.0f}min - time to exit"
                            )

                    # Log detailed rug info
                    liq_drop = position.get_liquidity_drop_percent()
                    logger.error(
                        f"🚨 Rug detected: {position.symbol or position.token_address[:8]}... "
                        f"Liq drop: {liq_drop:.0f}%, Current: ${position.current_liquidity:.0f}"
                    )
                    await self.close_position(
                        position.token_address,
                        position.current_price,
                        'low_liquidity'
                    )
                    continue

            # 4. Trailing Stop - Unchanged for now
            if self.position_manager.check_trailing_stop(position.token_address):
                logger.info(f"📊 Trailing stop hit: {position.symbol or position.token_address[:8]}...")
                await self.close_position(
                    position.token_address,
                    position.current_price,
                    'trailing_stop'
                )
                continue

    def get_statistics(self) -> Dict:
        """
        Get trading statistics.

        Returns:
            Dictionary with stats from PositionManager
        """
        stats = self.position_manager.get_statistics()

        if self.csv_tracker:
            csv_stats = self.csv_tracker.get_statistics()
            stats['csv_trades'] = csv_stats.get('total_trades', 0)

        return stats

    def print_statistics(self):
        """Print current trading statistics."""
        stats = self.get_statistics()

        logger.info("=" * 60)
        logger.info("TRADING STATISTICS")
        logger.info("=" * 60)
        logger.info(f"Open Positions: {stats['open_positions']}")
        logger.info(f"Total Trades: {stats['total_trades']}")
        logger.info(f"Win Rate: {stats['win_rate']:.1%}")
        logger.info(f"Total PnL: ${stats['total_realized_pnl']:.2f}")
        logger.info(f"Unrealized PnL: ${stats['total_unrealized_pnl']:.2f}")
        logger.info("=" * 60)

    async def start(self):
        """Start the trading bot."""
        logger.info("=" * 60)
        logger.info("🚀 ML BOT 2 FOUNDATION STARTING")
        logger.info("=" * 60)
        logger.info(f"Mode: {'PAPER TRADING' if self.config.paper_trading else 'LIVE TRADING ⚠️'}")
        logger.info(f"Target: 71.7%+ win rate (ML Bot 2 baseline)")
        logger.info("=" * 60)

        self.running = True

        # Send startup notification
        if self.notifier:
            await self.notifier.send_startup_message()

        # Start Telegram command handler
        if self.command_handler:
            await self.command_handler.start()
            logger.info("  ✅ Telegram commands started (/help, /status, /close)")

        # Initialize API clients
        await self.scanner.__aenter__()

        try:
            # Main trading loop
            scan_interval = self.config.core_config.scan_interval
            monitor_interval = self.config.core_config.monitor_interval

            logger.info(f"Scan interval: {scan_interval}s, Monitor interval: {monitor_interval}s")
            logger.info("Bot is running... (Ctrl+C to stop)")
            logger.info("")

            scan_counter = 0
            monitor_counter = 0

            while self.running:
                # === SCAN FOR NEW TOKENS ===
                if scan_counter <= 0:
                    await self.scan_and_trade()
                    scan_counter = scan_interval

                # === MONITOR OPEN POSITIONS ===
                if monitor_counter <= 0:
                    await self.monitor_positions()
                    monitor_counter = monitor_interval

                    # Print stats periodically
                    if len(self.position_manager.get_all_positions()) > 0:
                        self.print_statistics()

                # Sleep for 1 second and decrement counters
                await asyncio.sleep(1)
                scan_counter -= 1
                monitor_counter -= 1

        finally:
            # Cleanup
            await self.scanner.__aexit__(None, None, None)

    async def scan_and_trade(self):
        """Scan for new tokens and execute trades."""
        try:
            # Check if we have room for more positions
            open_positions = len(self.position_manager.get_all_positions())
            max_positions = self.config.core_config.max_open_positions

            if open_positions >= max_positions:
                logger.info(f"Max positions reached ({open_positions}/{max_positions})")
                return

            # Scan for new tokens (increased from 10 to 50 for better sample size)
            tokens = await self.scanner.scan_new_tokens(limit=50)

            if not tokens:
                logger.debug("No new tokens found this scan")
                return

            # Analyze each token
            for token in tokens:
                if not self.running:
                    break

                # Check if we still have room
                if len(self.position_manager.get_all_positions()) >= max_positions:
                    logger.info("Max positions reached during scan")
                    break

                await self.analyze_and_trade_token(token)

        except Exception as e:
            logger.error(f"Error in scan_and_trade: {e}", exc_info=True)

    async def analyze_and_trade_token(self, token_data: dict):
        """
        Analyze token and execute trade if approved.

        Args:
            token_data: Token data from scanner
        """
        try:
            token_address = token_data['address']
            symbol = token_data.get('symbol', '')

            logger.info(f"Analyzing: {symbol} ({token_address[:8]}...)")

            # ⚡ Calculate token age from pair creation timestamp
            pair_created_at = token_data.get('pair_created_at', 0)
            if pair_created_at and pair_created_at > 0:
                # DexScreener returns timestamp in milliseconds
                created_datetime = datetime.fromtimestamp(pair_created_at / 1000)
                token_age_hours = (datetime.now() - created_datetime).total_seconds() / 3600
                token_data['token_age_hours'] = token_age_hours
            else:
                token_data['token_age_hours'] = 0.0

            # ⚡ Fetch holder analysis from Solscan (if available)
            if self.solscan_client:
                try:
                    async with self.solscan_client:
                        holder_data = await self.solscan_client.get_holder_analysis(token_address)
                        if holder_data:
                            token_data['holder_count'] = holder_data.get('total_holders', 0)
                            token_data['top10_concentration'] = holder_data.get('top10_concentration', 0.0)
                            token_data['top1_concentration'] = holder_data.get('top1_concentration', 0.0)
                            logger.debug(
                                f"📊 Holder analysis: {holder_data['total_holders']} holders, "
                                f"Top1: {holder_data['top1_concentration']:.1f}%, "
                                f"Top10: {holder_data['top10_concentration']:.1f}%"
                            )
                        else:
                            logger.debug(f"No holder data available for {symbol}")
                except Exception as e:
                    logger.debug(f"Error fetching holder analysis for {symbol}: {e}")

            # === ENTRY QUALITY FILTERS (ML Bot Style) ===
            # Filter #1: Buy/Sell Ratio (Bullish Momentum)
            buy_ratio_24h = token_data.get('buy_ratio_24h', 0)
            buy_ratio_1h = token_data.get('buy_ratio_1h', 0)

            # Use 1h if available (recent activity), otherwise 24h
            buy_ratio = buy_ratio_1h if buy_ratio_1h > 0 else buy_ratio_24h

            if buy_ratio < 0.50:  # Require 50%+ buyers (data collection mode)
                logger.info(
                    f"⛔ Skipped {symbol}: Low buy ratio {buy_ratio:.1%} (need 50%+). "
                    f"24h: {buy_ratio_24h:.1%}, 1h: {buy_ratio_1h:.1%}"
                )
                # Track rejection for analysis
                self.rejected_tracker.record_rejection(
                    token_address=token_address,
                    rejection_reason=f"low_buy_ratio_{buy_ratio:.1%}",
                    token_data=token_data,
                    symbol=symbol,
                    rejection_stage='screening'
                )
                return

            # Filter #2: Activity Check (Real Interest)
            txns_24h = token_data.get('txns_24h', 0)
            txns_1h = token_data.get('txns_1h', 0)

            if txns_24h < 50:  # Minimum 50 transactions (ML Bot 2 standard)
                logger.info(
                    f"⛔ Skipped {symbol}: Low activity {txns_24h} txns (need 50+). "
                    f"24h: {txns_24h}, 1h: {txns_1h}"
                )
                # Track rejection for analysis
                self.rejected_tracker.record_rejection(
                    token_address=token_address,
                    rejection_reason=f"low_activity_{txns_24h}_txns",
                    token_data=token_data,
                    symbol=symbol,
                    rejection_stage='screening'
                )
                return

            # Filter #3: MAX Liquidity (Skip Bluechips)
            liquidity_usd = token_data.get('liquidity_usd', 0)
            MAX_LIQUIDITY = 1_000_000  # Skip tokens with >$1M liquidity (data collection mode - raised from 500k)

            if liquidity_usd > MAX_LIQUIDITY:
                logger.info(
                    f"⛔ Skipped {symbol}: Too high liquidity ${liquidity_usd:,.0f} (max ${MAX_LIQUIDITY:,.0f}). "
                    f"This is an established token, not a new opportunity."
                )
                # Track rejection for analysis
                self.rejected_tracker.record_rejection(
                    token_address=token_address,
                    rejection_reason=f"high_liquidity_${liquidity_usd:,.0f}",
                    token_data=token_data,
                    symbol=symbol,
                    rejection_stage='screening'
                )
                return

            # Filter #4: MAX Volume (DISABLED - Data shows high volume = runners!)
            # Analysis: 59 rejected high volume trades had +4,038% avg gain! 🔥
            # High volume with good metrics = opportunity, not risk!
            # volume_24h = token_data.get('volume_24h', 0)
            # MAX_VOLUME_24H = 1_000_000  # DISABLED

            logger.info(
                f"✅ Quality checks passed: {symbol} - "
                f"Buy ratio: {buy_ratio:.1%} (24h: {buy_ratio_24h:.1%}, 1h: {buy_ratio_1h:.1%}), "
                f"Activity: {txns_24h} txns, "
                f"Liq: ${liquidity_usd:,.0f}, Vol: ${volume_24h:,.0f}"
            )

            # Prepare data for risk assessment
            market_data = {
                'price_usd': token_data.get('price_usd', 0),
                'liquidity_usd': token_data.get('liquidity_usd', 0),
                'volume_24h': token_data.get('volume_24h', 0),
                'price_change_5m': token_data.get('price_change_5m', 0),
                'price_change_1h': token_data.get('price_change_1h', 0),
                'txns_24h': txns_24h,
                'txns_1h': txns_1h,
                'buy_ratio_24h': buy_ratio_24h,
                'buy_ratio_1h': buy_ratio_1h,
                # Phase 2: Preserve source information from scanner
                'source': token_data.get('source', 'unknown'),
                'sources': token_data.get('sources', []),
                'source_count': token_data.get('source_count', 1),
                'sources_count': token_data.get('source_count', 1),  # Telegram notifier expects this
                # Preserve additional metadata for notifications
                'pair_created_at': token_data.get('pair_created_at', 0),
                'dex_id': token_data.get('dex_id', 'unknown'),
            }

            # For now, use simplified security data
            # In full implementation, would fetch from Solscan, etc.
            security_data = {
                'is_mintable': False,
                'has_freeze_authority': False,
                'ownership_renounced': True,
            }

            # Simplified sentiment and prediction
            sentiment_score = {'score': 0.5}
            price_prediction = {'confidence': 0.6}

            # === 🔒 ANALYZE WITH PROTECTED CORE ===
            should_trade, risk_score, reason = await self.analyze_token(
                token_address=token_address,
                market_data=market_data,
                security_data=security_data,
                sentiment_score=sentiment_score,
                price_prediction=price_prediction
            )

            if not should_trade:
                logger.debug(f"Token rejected: {symbol} - {reason}")
                # Track rejection for analysis (safety filter or risk assessor)
                self.rejected_tracker.record_rejection(
                    token_address=token_address,
                    rejection_reason=reason,
                    token_data=token_data,
                    symbol=symbol,
                    rejection_stage='safety_filter' if 'safety_filter' in reason else 'risk_assessor'
                )
                return

            # === EXECUTE TRADE ===
            entry_price = market_data['price_usd']
            position_size_usd = self.config.default_position_size  # Position size in USD

            # Check executor capital
            balance = self.executor.get_balance()
            if balance['available_balance'] < position_size_usd:
                logger.warning(f"Insufficient capital: {balance['available_balance']:.2f} USD < {position_size_usd:.2f} USD")
                return

            # === FRESH LIQUIDITY CHECK (right before buying) ===
            # Re-validate liquidity hasn't dried up since initial scan
            try:
                # get_validated_price returns tuple: (price, liquidity, source)
                validated_price, fresh_liquidity, data_source = await self.price_validator.get_validated_price(
                    token_address,
                    entry_price=entry_price
                )

                if validated_price is None or fresh_liquidity is None:
                    logger.warning(f"Cannot verify price/liquidity for {symbol} - skipping")
                    return

                min_liquidity = self.config.core_config.min_position_liquidity

                if fresh_liquidity < min_liquidity:
                    logger.warning(
                        f"Liquidity too low for {symbol}: ${fresh_liquidity:,.0f} < ${min_liquidity:,.0f} - skipping"
                    )
                    return

                # Use fresh validated price for entry
                entry_price = validated_price
                logger.debug(f"Liquidity verified: ${fresh_liquidity:,.0f} (min: ${min_liquidity:,.0f}) from {data_source}")

            except Exception as e:
                logger.error(f"Error checking liquidity for {symbol}: {e}")
                return

            # Execute buy
            trade_result = await self.executor.execute_buy(
                token_address=token_address,
                amount_usd=position_size_usd,
                price_usd=entry_price,
                symbol=symbol
            )

            if not trade_result:
                logger.error(f"Failed to execute buy for {symbol}")
                return

            # === 🔒 OPEN POSITION IN PROTECTED CORE ===
            position = await self.open_position(
                token_address=token_address,
                entry_price=entry_price,
                amount_usd=position_size_usd,
                symbol=symbol,
                entry_liquidity=fresh_liquidity,  # Track entry liquidity for drop % calculation
                # ⚡ CRITICAL ANALYSIS FIELDS from token_data
                volume_24h=token_data.get('volume_24h', 0.0),
                volume_1h=token_data.get('volume_1h', 0.0),
                dex_platform=token_data.get('dex_id', 'unknown'),
                token_source=token_data.get('source', 'unknown'),
                data_provider=data_source,  # DexScreener or Jupiter (from validation)
                txns_h1_buys=token_data.get('txns_h1_buys', 0),
                txns_h1_sells=token_data.get('txns_h1_sells', 0),
                buy_ratio_24h=token_data.get('buy_ratio_24h', 0.0),
                buy_ratio_1h=token_data.get('buy_ratio_1h', 0.0),
                holder_count=token_data.get('holder_count', 0),
                top10_concentration=token_data.get('top10_concentration', 0.0),
                top1_concentration=token_data.get('top1_concentration', 0.0),
                lp_locked=token_data.get('lp_locked', False),
                lp_burned=token_data.get('lp_burned', False),
                lp_lock_days=token_data.get('lp_lock_days', 0),
                lp_burned_percent=token_data.get('lp_burned_percent', 0.0),
                token_age_hours=token_data.get('token_age_hours', 0.0),
                # ⚡ TIMING ANALYSIS FIELDS
                price_change_5m=token_data.get('price_change_5m', 0.0),
                price_change_1h=token_data.get('price_change_1h', 0.0),
            )

            if position:
                logger.info(f"✅ Position opened successfully: {symbol}")

                # Send enhanced entry notification
                if self.notifier:
                    # Get actual source from market data (Phase 2 multi-source tracking)
                    # If token found by multiple sources, show all of them!
                    sources = market_data.get('sources', [])
                    if sources and len(sources) > 1:
                        # Multi-source token - show all sources
                        actual_source = ' + '.join(sources)
                    elif sources and len(sources) == 1:
                        # Single source
                        actual_source = sources[0]
                    else:
                        # Fallback to 'source' field if 'sources' array not available
                        actual_source = market_data.get('source', 'UNKNOWN')

                    await self.notifier.send_entry_notification(
                        token_address=token_address,
                        symbol=symbol,
                        entry_price=entry_price,
                        position_size=position_size_usd,
                        score=int(risk_score * 100),  # Convert 0-1 to 0-100
                        confidence=risk_score,
                        token_data=market_data,
                        rugcheck_data=None,
                        source=actual_source
                    )
            else:
                logger.error(f"Failed to open position for {symbol}")

        except Exception as e:
            logger.error(f"Error analyzing/trading token: {e}", exc_info=True)

    async def stop(self):
        """Stop the trading bot."""
        logger.info("Stopping bot...")
        self.running = False

        # Export final statistics
        self.print_statistics()

        # Export CSV
        if self.csv_tracker:
            trades_exported = self.csv_tracker.export_csv()
            logger.info(f"Exported {trades_exported} trades to CSV")

        # Send shutdown notification
        if self.notifier:
            await self.notifier.send_shutdown_message()

        logger.info("Bot stopped.")


async def main():
    """Main entry point."""
    bot = None
    try:
        # Load configuration
        logger.info("Loading configuration...")
        config = load_config()

        # Create bot instance
        bot = MLBot2Foundation(config)

        # Start bot (runs until Ctrl+C)
        await bot.start()

    except KeyboardInterrupt:
        logger.info("\n\nShutdown requested...")
        if bot:
            await bot.stop()
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        if bot:
            await bot.stop()
        sys.exit(1)


if __name__ == '__main__':
    # Configure logging
    configure_logging(level=logging.INFO)

    # Run main
    asyncio.run(main())
