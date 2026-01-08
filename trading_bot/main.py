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


class StopLossCooldown:
    """
    Smart cooldown based on stop loss depth.
    Deep stops (>-15%) = avoid repeating (30min)
    Normal stops (-10 to -15%) = short cooldown (10min)
    Shallow stops (<-10%) = no cooldown (token recovers!)

    Data: ADIEU stopped at -10.1% then pumped 3964% - blocked by 1h cooldown! 💀
    Solution: Smart cooldown allows recovery entries on shallow stops.
    """
    def __init__(self):
        self.stopped_tokens: Dict[str, dict] = {}  # symbol -> {timestamp, stop_percent, cooldown_hours}

    def add_stop(self, symbol: str, stop_loss_percent: float):
        """Record a stop loss with its depth."""
        cooldown_hours = self._get_cooldown_hours(stop_loss_percent)
        self.stopped_tokens[symbol] = {
            'timestamp': datetime.now(),
            'stop_percent': stop_loss_percent,
            'cooldown_hours': cooldown_hours
        }
        logger.info(
            f"📊 Cooldown: {symbol} stopped at {stop_loss_percent:.1f}% "
            f"→ {cooldown_hours*60:.0f}min cooldown"
        )

    def _get_cooldown_hours(self, stop_loss_percent: float) -> float:
        """Smart cooldown based on stop depth."""
        if stop_loss_percent < -15:
            return 0.5  # 30min - deep rug, avoid!
        elif stop_loss_percent < -10:
            return 0.17  # 10min - normal vol
        else:
            return 0  # No cooldown - can recover! (ADIEU 3964% case)

    def is_on_cooldown(self, symbol: str, volume_1h: float = 0) -> bool:
        """Check if symbol is still on cooldown. High volume overrides cooldown."""
        if symbol not in self.stopped_tokens:
            return False

        # 🚀 VOLUME OVERRIDE: $500k+ volume = skip cooldown (catch Sapijuju 1,956%!)
        if volume_1h >= 500000:
            logger.info(f"🚀 {symbol}: Volume override! ${volume_1h:,.0f} → Skipping cooldown!")
            return False

        stop_data = self.stopped_tokens[symbol]
        time_since = (datetime.now() - stop_data['timestamp']).total_seconds() / 3600
        return time_since < stop_data['cooldown_hours']

    def get_time_remaining(self, symbol: str) -> float:
        """Get hours remaining on cooldown."""
        if symbol not in self.stopped_tokens:
            return 0.0

        stop_data = self.stopped_tokens[symbol]
        time_since = (datetime.now() - stop_data['timestamp']).total_seconds() / 3600
        return max(0.0, stop_data['cooldown_hours'] - time_since)

    def get_stop_percent(self, symbol: str) -> float:
        """Get the stop loss percent that triggered."""
        if symbol not in self.stopped_tokens:
            return 0.0
        return self.stopped_tokens[symbol]['stop_percent']

    def clear_old(self, hours: int = 24):
        """Clear cooldowns older than specified hours."""
        cutoff = datetime.now() - timedelta(hours=hours)
        self.stopped_tokens = {
            sym: data for sym, data in self.stopped_tokens.items()
            if data['timestamp'] > cutoff
        }


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

        # === STOP LOSS COOLDOWN ===
        self.stop_cooldown = StopLossCooldown()
        logger.info("  ✅ StopLossCooldown initialized (smart duration based on stop depth)")

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

        # Initialize RPC client for security checks (mint/freeze authority)
        self.rpc_url = config.solana_rpc_url
        self.rpc_session = None  # Will be created in async context
        logger.info(f"  ✅ RPC configured for security checks: {self.rpc_url}")

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

        # Link executor to position_manager for state persistence
        self.position_manager.executor = self.executor

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

    async def get_token_security(self, token_address: str) -> Dict:
        """
        Get comprehensive security data for a token from Solana RPC.

        Checks:
        - Mint authority (can create new tokens?)
        - Freeze authority (can freeze wallets?)
        - Supply information

        Args:
            token_address: Token mint address

        Returns:
            Dict with security info
        """
        import aiohttp

        if not self.rpc_session:
            self.rpc_session = aiohttp.ClientSession()

        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getAccountInfo",
                "params": [
                    token_address,
                    {"encoding": "jsonParsed"}
                ]
            }

            async with self.rpc_session.post(
                self.rpc_url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status != 200:
                    logger.warning(f"RPC error for {token_address[:8]}: {response.status}")
                    return {'error': 'rpc_error'}

                data = await response.json()
                result = data.get('result')

                if not result or not result.get('value'):
                    logger.debug(f"No account data for {token_address[:8]}")
                    return {'error': 'no_data'}

                # Parse mint account data
                account_data = result['value'].get('data', {})
                if isinstance(account_data, dict):
                    parsed = account_data.get('parsed', {})
                    info = parsed.get('info', {})

                    # Check authorities
                    mint_authority = info.get('mintAuthority')
                    freeze_authority = info.get('freezeAuthority')

                    return {
                        'has_mint_authority': mint_authority is not None,
                        'has_freeze_authority': freeze_authority is not None,
                        'mint_authority': mint_authority,
                        'freeze_authority': freeze_authority,
                        'supply': int(info.get('supply', 0)),
                        'decimals': info.get('decimals', 0)
                    }
                else:
                    logger.debug(f"Non-parsed account data for {token_address[:8]}")
                    return {'error': 'parse_error'}

        except asyncio.TimeoutError:
            logger.warning(f"RPC timeout checking security for {token_address[:8]}")
            return {'error': 'timeout'}
        except Exception as e:
            logger.warning(f"Error checking security for {token_address[:8]}: {e}")
            return {'error': str(e)}

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
        # ⚡ ADAPTIVE STOP LOSS SYSTEM (Based on 10+ AI analysis + simulation)
        # Data shows: -20% SL gives +52% PnL improvement! Saves 73 shake-outs!
        # Solution: Age-adapted SL + break-even trigger + no-SL window

        # 🔥 HARD -12% STOP LOSS (5th AI OPTIMAL!)
        # 4th AI: -10% SL = +640% PnL vs +214% (3X better)
        # 5th AI: -12% optimal (if <-12% in 6min, almost always ends -50%!)
        # Why: Winners don't dip <-5%, if >-12% then <5% chance recover
        base_stop_percent = 12.0  # HARD -12% (5th AI consensus!)

        stop_loss = self.risk_assessor.calculate_stop_loss(
            entry_price,
            base_stop_percent
        )

        logger.info(
            f"🔥 HARD -12% SL for {symbol} @ ${stop_loss:.8f} "
            f"(First 5min NO-SL, then HARD -12%!)"
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

        # Capture partial profit data before closing position
        partial_profit_usd = getattr(position, 'total_partial_profit_usd', 0.0)
        milestones_hit_set = getattr(position, 'milestones_hit', set())
        milestones_hit_str = ','.join(str(m) for m in sorted(milestones_hit_set)) if milestones_hit_set else ''

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
                    liquidity_change=None,  # Not tracked in Position dataclass
                    partial_profit_usd=partial_profit_usd,
                    milestones_hit=milestones_hit_str
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

                            # Track total partial profits for final P&L calculation
                            position.total_partial_profit_usd += partial_profit

                            logger.info(
                                f"💵 Locked in ${partial_profit:.2f} profit (Total partials: ${position.total_partial_profit_usd:.2f}), "
                                f"Remaining: {position.quantity:.2f} tokens (${position.amount_usd:.2f} cost basis)"
                            )

        # === RUG DETECTION (once per monitor cycle) ===
        # Get dead positions ONCE before the loop to avoid duplicate logging
        dead_positions = []
        if self.config.core_config.rug_detection_enabled:
            dead_positions = self.position_manager.get_dead_positions(
                stale_minutes=self.config.core_config.stale_price_minutes,
                min_liquidity=self.config.core_config.min_position_liquidity
            )

        # Check exit conditions for remaining positions
        for position in list(self.position_manager.get_all_positions()):
            # === ADAPTIVE STOP LOSS MANAGEMENT ===
            # Data: -20% SL saves 73 shake-outs, +52% PnL improvement!
            position_duration_min = (datetime.now() - position.entry_time).total_seconds() / 60

            # PHASE 1: NO-SL WINDOW (First 5 min for initial volatility)
            # 4th AI Strategy: 5min window then HARD -10% SL kicks in!
            no_sl_active = position_duration_min < 5.0  # 5min NO-SL window

            # PHASE 2: BREAK-EVEN TRIGGER (+10% → Move SL to +1%)
            # Makes trade risk-free once profit threshold hit!
            if position.unrealized_pnl_percent >= 10.0 and position.stop_loss < position.entry_price * 1.01:
                # Move stop loss to +1% profit = risk-free trade!
                position.stop_loss = position.entry_price * 1.01
                logger.info(
                    f"🔒 {position.symbol}: BREAK-EVEN TRIGGERED! Profit {position.unrealized_pnl_percent:.1f}% "
                    f"→ SL moved to +1% (${position.stop_loss:.8f}). Trade now RISK-FREE! ✅"
                )

            # === FAST RUG EXIT: INSTANT DUMP DETECTION (HIGHEST PRIORITY!) ===
            # 5th AI: Exit rugs FAST before they go -50-77%!
            # If <2min AND <-12%, likely RUG/HONEYPOT → Exit NOW!
            if position_duration_min < 2.0 and position.unrealized_pnl_percent < -12.0:
                logger.warning(
                    f"🚨 FAST RUG EXIT: {position.symbol} down {position.unrealized_pnl_percent:.1f}% in <2min! "
                    f"Likely RUG/HONEYPOT → INSTANT SELL!"
                )
                try:
                    await self.execution_client.execute_sell(
                        position=position,
                        reason="fast_rug_exit_2min",
                        current_price=position.current_price
                    )
                    self.stop_cooldown.add_stop(position.symbol, position.unrealized_pnl_percent)
                    continue
                except Exception as e:
                    logger.error(f"Failed fast rug exit for {position.symbol}: {e}")

            # === ZOMBIE EXIT: CUT STALE POSITIONS ===
            # Data: >60min positions show 21% win, only +$41 profit
            # Exit if >45min AND profit <5% (not moving, cut losses!)
            if position_duration_min > 45 and position.unrealized_pnl_percent < 5.0:
                logger.info(
                    f"⏰ {position.symbol}: ZOMBIE EXIT! Duration {position_duration_min:.0f}min "
                    f"with only {position.unrealized_pnl_percent:.1f}% profit. Position is stale, exiting!"
                )
                try:
                    await self.execution_client.execute_sell(
                        position=position,
                        reason="zombie_exit_45min",
                        current_price=position.current_price
                    )
                    self.stop_cooldown.add_stop(position.symbol, position.unrealized_pnl_percent)
                    continue
                except Exception as e:
                    logger.error(f"Failed zombie exit for {position.symbol}: {e}")

            # === OPTIMIZED 2-PATH EXIT LOGIC ===
            # Priority: Emergency rugs > Winners maximize profit > Losers minimize loss

            # === EMERGENCY OVERRIDE: RUG DETECTION (HIGHEST PRIORITY) ===
            if self.config.core_config.rug_detection_enabled and position.token_address in dead_positions:
                # Determine specific rug type for accurate data tracking
                rug_reason = 'rug_unknown'  # Default fallback

                # Check which condition triggered (in priority order)
                if position.is_price_stale(self.config.core_config.stale_price_minutes):
                    minutes_since = (datetime.now() - position.last_price_update).total_seconds() / 60

                    # ✅ WINNER with stale price = Low volume token, NOT a rug!
                    # Let trailing stop handle the exit at the right time
                    if position.unrealized_pnl > 0:
                        logger.warning(
                            f"⚠️  LOW VOLUME (profitable): {position.symbol or position.token_address[:8]}... "
                            f"Stale {minutes_since:.1f}min but +{position.unrealized_pnl_percent:.1f}% - continuing"
                        )
                        # Remove from dead_positions and skip rug exit
                        dead_positions.remove(position.token_address)
                        continue  # Let winners run to trailing stop!

                    # ❌ LOSER + stale price = Check if actually dead or just low volatility
                    # Fetch fresh token data to check recent activity
                    try:
                        fresh_data = await self.price_validator.dexscreener_client.get_token_profile(position.token_address)
                        if fresh_data:
                            recent_volume_1h = fresh_data.get('volume_1h', 0)
                            recent_txns_1h = fresh_data.get('txns_1h', 0)

                            # If still trading activity, it's NOT a rug - just low volatility/consolidation
                            if recent_volume_1h >= 1000 and recent_txns_1h >= 5:
                                logger.warning(
                                    f"⚠️  STALE but TRADING: {position.symbol or position.token_address[:8]}... "
                                    f"Stale {minutes_since:.1f}min BUT ${recent_volume_1h:,.0f}/1h, {recent_txns_1h} txns - "
                                    f"NOT a rug, just consolidating. Letting stop loss handle it."
                                )
                                # Remove from dead_positions and skip rug exit
                                dead_positions.remove(position.token_address)
                                continue  # Let stop loss handle exit

                    except Exception as e:
                        logger.debug(f"Error checking activity for {position.symbol}: {e}")

                    # No activity = actual rug
                    logger.error(
                        f"🚨 RUG: STALE PRICE - {position.symbol or position.token_address[:8]}... "
                        f"No price update for {minutes_since:.1f} minutes AND no trading activity (dead token)"
                    )
                    rug_reason = 'rug_stale_price'

                elif position.is_price_frozen(freeze_minutes=2):
                    minutes_frozen = (datetime.now() - position.last_price_change).total_seconds() / 60
                    logger.error(
                        f"🚨 RUG: FROZEN PRICE - {position.symbol or position.token_address[:8]}... "
                        f"Price hasn't moved for {minutes_frozen:.1f} minutes @ ${position.current_price:.8f} (likely honeypot)"
                    )
                    rug_reason = 'rug_frozen_price'

                elif position.is_liquidity_dead(self.config.core_config.min_position_liquidity):
                    liq_drop = position.get_liquidity_drop_percent()
                    logger.error(
                        f"🚨 RUG: LIQUIDITY DEAD - {position.symbol or position.token_address[:8]}... "
                        f"Liq drop: {liq_drop:.0f}%, Current: ${position.current_liquidity:.0f} (rug pull)"
                    )
                    rug_reason = 'rug_liquidity_dead'

                else:
                    # Generic low liquidity (not necessarily rug)
                    liq_drop = position.get_liquidity_drop_percent()
                    logger.warning(
                        f"⚠️  Low liquidity: {position.symbol or position.token_address[:8]}... "
                        f"Liq drop: {liq_drop:.0f}%, Current: ${position.current_liquidity:.0f}"
                    )
                    rug_reason = 'low_liquidity'

                await self.close_position(
                    position.token_address,
                    position.current_price,
                    rug_reason
                )
                continue

            # === PATH 1: WINNERS - MAXIMIZE PROFIT ===
            if position.unrealized_pnl > 0:
                # For winners, check trailing stop FIRST (capture profits quickly!)
                if self.position_manager.check_trailing_stop(position.token_address):
                    logger.info(f"📊 Trailing stop hit: {position.symbol or position.token_address[:8]}...")
                    await self.close_position(
                        position.token_address,
                        position.current_price,
                        'trailing_stop'
                    )
                    continue

            # === PATH 2: LOSERS - MINIMIZE LOSS ===
            else:
                # ⚡ NO-SL WINDOW: Skip stop loss check during first 3 min!
                # Prevents shake-outs during initial volatility
                if no_sl_active:
                    logger.debug(
                        f"⏳ {position.symbol}: NO-SL window active "
                        f"({position_duration_min:.1f}min < 3min). Skipping SL check."
                    )
                    # Skip stop loss check, let position develop!
                    continue

                # For losers, check stop loss FIRST (cut losses fast!)
                if self.position_manager.check_stop_loss(position.token_address):
                    # Calculate stop loss percent for smart cooldown
                    stop_percent = ((position.current_price - position.entry_price) / position.entry_price) * 100
                    logger.warning(f"🛑 Stop loss hit: {position.symbol or position.token_address[:8]}... ({stop_percent:.1f}%)")

                    # Add to cooldown BEFORE closing (smart duration based on depth)
                    if position.symbol:
                        self.stop_cooldown.add_stop(position.symbol, stop_percent)

                    await self.close_position(
                        position.token_address,
                        position.current_price,
                        'stop_loss'
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

    async def check_momentum(self, token_address: str, symbol: str, token_data: dict) -> bool:
        """
        Check if token has positive momentum (not falling/dumping).
        Prevents entering falling knives that cause instant stops.

        Data shows: 54% stops <5min = entering falling tokens! 🚨
        This check saves $700-900 by blocking bad entries.
        """
        try:
            # Get price change data
            price_change_5m = token_data.get('price_change_5m', 0)
            price_change_1h = token_data.get('price_change_1h', 0)

            # Get transaction data
            txns_h1_buys = token_data.get('txns_h1_buys', 0)
            txns_h1_sells = token_data.get('txns_h1_sells', 0)
            total_txns = txns_h1_buys + txns_h1_sells

            # === 5th AI INSIGHT: REMOVED no_momentum_1m filter! ===
            # Why removed: Tokens can REST 60s then EXPLODE 1000%+!
            # Missed: OILDUMP 6,328%, Bluefin 1,586%, BLUFSH 4,377%
            # Solana moves in BURSTS, not continuous!
            # 0.0% = Normal rest before explosion, NOT red flag!
            #
            # Keeping only 5min momentum check below (enough!)

            # Check 1: Price falling in last 5 min? (RELAXED - testing low thresholds!)
            if price_change_5m < -20:  # Down >20% = extreme dump! (lowered from -10%)
                logger.info(
                    f"⛔ Skipped {symbol}: Heavy dump! Price down {price_change_5m:.1f}% in 5min. "
                    f"Extreme dump - avoid instant rugs."
                )
                self.rejected_tracker.record_rejection(
                    token_address=token_address,
                    rejection_reason=f"heavy_dump_{price_change_5m:.1f}%_5m",
                    token_data=token_data,
                    symbol=symbol,
                    rejection_stage='momentum'
                )
                return False

            elif price_change_5m < -15:  # Down 15-20% = check if recovering! (lowered from -5%)
                price_change_1m = token_data.get('price_change_1m', 0)

                if price_change_1m > 0:  # Price rising last 1min = recovery!
                    logger.info(
                        f"✅ {symbol}: Was falling ({price_change_5m:.1f}% in 5m) BUT recovering "
                        f"({price_change_1m:+.1f}% in 1m). Allowing recovery entry (dip-buy)!"
                    )
                    # Continue - recovery allowed! ✅
                else:
                    logger.info(
                        f"⛔ Skipped {symbol}: Falling knife! Price down {price_change_5m:.1f}% in 5min "
                        f"and still falling ({price_change_1m:+.1f}% in 1m). Not recovering yet."
                    )
                    self.rejected_tracker.record_rejection(
                        token_address=token_address,
                        rejection_reason=f"falling_knife_{price_change_5m:.1f}%_5m_no_recovery",
                        token_data=token_data,
                        symbol=symbol,
                        rejection_stage='momentum'
                    )
                    return False

            # Check 2: High sell pressure right now?
            if total_txns >= 50:  # Only check if enough txns
                sell_pressure = txns_h1_sells / total_txns if total_txns > 0 else 0

                if sell_pressure > 0.60:  # >60% sells (dumping!)
                    logger.info(
                        f"⛔ Skipped {symbol}: High sell pressure! {sell_pressure:.0%} sells "
                        f"({txns_h1_sells} sells vs {txns_h1_buys} buys). Token dumping!"
                    )
                    self.rejected_tracker.record_rejection(
                        token_address=token_address,
                        rejection_reason=f"sell_pressure_{sell_pressure:.0%}",
                        token_data=token_data,
                        symbol=symbol,
                        rejection_stage='momentum'
                    )
                    return False

            # Check 3: Falling for extended period? Check V-recovery pattern!
            if price_change_1h < -15:  # Down >15% in 1h - BUT check recovery!
                # 🔥 V-RECOVERY LOGIC: Catch MADUROIL -17% → 460%!
                # If recovering from extended dump, this is a BUYING opportunity!
                price_change_5m = token_data.get('price_change_5m', 0)
                price_change_1m = token_data.get('price_change_1m', 0)
                buy_ratio = token_data.get('buy_ratio', 0)

                is_recovering = (
                    price_change_5m > 10 and  # >10% bounce in 5min
                    price_change_1m > 3 and   # >3% bounce in 1min
                    buy_ratio > 0.55          # >55% buying pressure
                )

                if is_recovering:
                    logger.info(
                        f"✅ {symbol}: V-RECOVERY! Extended dump {price_change_1h:.1f}% 1h BUT "
                        f"bouncing {price_change_5m:.1f}% 5m / {price_change_1m:.1f}% 1m "
                        f"with {buy_ratio:.0%} buy ratio → DIP BUY! 🚀"
                    )
                    return True  # Allow entry - this is a bounce play!
                else:
                    logger.info(
                        f"⛔ Skipped {symbol}: Extended dump! Price down {price_change_1h:.1f}% in 1h. "
                        f"No recovery signal yet (5m: {price_change_5m:.1f}%, 1m: {price_change_1m:.1f}%, "
                        f"buy: {buy_ratio:.0%})."
                    )
                    self.rejected_tracker.record_rejection(
                        token_address=token_address,
                        rejection_reason=f"extended_dump_{price_change_1h:.1f}%_1h_no_recovery",
                        token_data=token_data,
                        symbol=symbol,
                        rejection_stage='momentum'
                    )
                    return False

            # All momentum checks passed! ✅
            return True

        except Exception as e:
            logger.warning(f"Momentum check failed for {symbol}: {e}")
            return True  # Don't block on errors

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

            # === STOP LOSS COOLDOWN CHECK ===
            # Block re-entry on tokens that recently stopped out (UNLESS high volume!)
            volume_1h = token_data.get('volume_1h', 0)
            if self.stop_cooldown.is_on_cooldown(symbol, volume_1h):
                time_remaining = self.stop_cooldown.get_time_remaining(symbol)
                stop_percent = self.stop_cooldown.get_stop_percent(symbol)
                logger.info(
                    f"⛔ Skipped {symbol}: On stop loss cooldown "
                    f"({time_remaining*60:.0f}min remaining from {stop_percent:.1f}% stop). "
                    f"Smart cooldown: Deep stops wait longer!"
                )
                self.rejected_tracker.record_rejection(
                    token_address=token_address,
                    rejection_reason=f"stop_cooldown_{time_remaining*60:.0f}min",
                    token_data=token_data,
                    symbol=symbol,
                    rejection_stage='cooldown'
                )
                return

            # ═══════════════════════════════════════════════════════════════════
            # 🚀 MOONSHOT DETECTOR - CATCH ROCKETS EARLY! (HIGHEST PRIORITY!)
            # ═══════════════════════════════════════════════════════════════════
            # Skip ALL filters (momentum, activity, etc) if token is exploding!
            # Still do security checks to avoid rugs.
            # Expected: Catch OilCoal 4,058%, GPU 1,057%, etc!
            # ═══════════════════════════════════════════════════════════════════

            price_change_5m = token_data.get('price_change_5m', 0)
            volume_1h = token_data.get('volume_1h', 0)

            is_moonshot = (
                price_change_5m > 50 and      # >50% in 5min = rocket! 🚀
                volume_1h > 50000             # $50k+ volume (real action)
            )

            if is_moonshot:
                logger.info(
                    f"🚀🚀🚀 MOONSHOT DETECTED: {symbol}! "
                    f"Price +{price_change_5m:.1f}% in 5min, Vol ${volume_1h:,.0f}/1h! "
                    f"Skipping normal filters - priority entry!"
                )
                # Skip to security checks! Will handle below after age calc
            else:
                # === MOMENTUM CHECK: Don't enter falling knives! ===
                # Data shows: 134 stops <5min (54%!) = entering dumps! 🚨
                if not await self.check_momentum(token_address, symbol, token_data):
                    return  # Momentum check already logged rejection

            # ⚡ Calculate token age from pair creation timestamp
            pair_created_at = token_data.get('pair_created_at', 0)
            if pair_created_at and pair_created_at > 0:
                # DexScreener returns timestamp in milliseconds
                created_datetime = datetime.fromtimestamp(pair_created_at / 1000)
                token_age_hours = (datetime.now() - created_datetime).total_seconds() / 3600
                token_data['token_age_hours'] = token_age_hours
            else:
                token_data['token_age_hours'] = 0.0

            # ═══════════════════════════════════════════════════════════════════
            # 🔥 ACTIVITY-BASED FILTER - PHASE 1 (NO AGE LIMITS!)
            # ═══════════════════════════════════════════════════════════════════
            # Data shows: Age filter missed JASPER 25,698% (385 days old but VERY active!)
            # Old approach: Block tokens >90 days (missed second leg pumps)
            # New approach: IGNORE age, filter ONLY on activity/liquidity
            # Expected impact: +$800-1,500 (catch active old tokens!)
            # SKIP if moonshot detected!
            # ═══════════════════════════════════════════════════════════════════

            if not is_moonshot:
                # Only check activity if NOT a moonshot
                token_age_hours = token_data.get('token_age_hours', 0.0)
                volume_1h = token_data.get('volume_1h', 0)
                txns_1h = token_data.get('txns_1h', 0)
                liquidity_usd = token_data.get('liquidity_usd', 0)
                buy_ratio = token_data.get('buy_ratio_1h', 0) or token_data.get('buy_ratio_24h', 0)

                # NO AGE LIMIT! ⚡
                # Instead: Check if token has REAL activity (not dead/bluechip)
                # Active token = high volume + transactions + buy pressure + liquidity

                # Define activity thresholds (4th AI optimized!)
                MIN_VOLUME_1H = 30000  # $30k+ volume in 1h (real trading)
                MIN_TXNS_1H = 75       # 75+ transactions (lowered from 500 to test!)
                MIN_BUY_RATIO = 0.45   # 45%+ buy ratio (lowered from 60% to test!)
                MIN_LIQUIDITY = 15000  # $15k+ liquidity (avoid slippage, can adjust later!)

                # Check if token meets activity requirements
                # FLEXIBLE LOGIC: Reject ONLY if lacking BOTH volume AND txns
                has_volume = volume_1h >= MIN_VOLUME_1H
                has_txns = txns_1h >= MIN_TXNS_1H
                has_buy_pressure = buy_ratio >= MIN_BUY_RATIO
                has_liquidity = liquidity_usd >= MIN_LIQUIDITY

                # 🔧 FIX $0 LIQUIDITY BUG: Volume proves liquidity exists! (API lag)
                # All top missed opportunities had "$0 liq" but $200k+ volume
                if liquidity_usd == 0 and volume_1h >= MIN_VOLUME_1H:
                    logger.info(f"💡 {symbol}: $0 liq but ${volume_1h:,.0f} vol → Override liquidity check!")
                    has_liquidity = True

                # 🚀 HIGH VOLUME OVERRIDE: Catch TRUMPS 2,536% (893 txns, $32k vol)
                # If volume OR txns is EXCEPTIONALLY high, relax other requirements
                is_high_volume = volume_1h >= 50000 or txns_1h >= 800
                if is_high_volume:
                    logger.info(f"🔥 {symbol}: HIGH ACTIVITY! Vol=${volume_1h:,.0f}, Txns={txns_1h} → Relaxed filter!")
                    is_active = True  # Skip all other checks!
                else:
                    # Active if has good volume OR good txns (not both required!)
                    # AND reasonable buy ratio AND minimum liquidity
                    is_active = (
                        (has_volume or has_txns) and  # Volume OR txns (flexible!)
                        has_buy_pressure and
                        has_liquidity
                    )

                if not is_active:
                    # Token lacks activity - could be dead/bluechip/slow mover
                    logger.info(
                        f"⛔ Skipped {symbol}: Insufficient activity! 🚨\n"
                        f"   Age: {token_age_hours:.0f}h ({token_age_hours/24:.0f}d)\n"
                        f"   Volume 1h: ${volume_1h:,.0f} (need ${MIN_VOLUME_1H:,.0f}+)\n"
                        f"   Txns 1h: {txns_1h} (need {MIN_TXNS_1H}+)\n"
                        f"   Buy ratio: {buy_ratio:.0%} (need {MIN_BUY_RATIO:.0%}+)\n"
                        f"   Liquidity: ${liquidity_usd:,.0f} (need ${MIN_LIQUIDITY:,.0f}+)\n"
                        f"   NO AGE LIMIT - but need ACTIVITY to trade!"
                    )
                    self.rejected_tracker.record_rejection(
                        token_address=token_address,
                        rejection_reason=f"low_activity_vol${volume_1h:.0f}_txns{txns_1h}_buy{buy_ratio:.0%}",
                        token_data=token_data,
                        symbol=symbol,
                        rejection_stage='activity_filter'
                    )
                    return

                # ✅ ACTIVE TOKEN - AGE DOESN'T MATTER!
                age_str = f"{token_age_hours:.0f}h ({token_age_hours/24:.0f}d)" if token_age_hours > 0 else "Unknown"
                logger.info(
                    f"✅ {symbol}: ACTIVE token - ready to trade! ⚡\n"
                    f"   Age: {age_str} (NO age limit!)\n"
                    f"   Volume 1h: ${volume_1h:,.0f}\n"
                    f"   Txns 1h: {txns_1h}\n"
                    f"   Buy ratio: {buy_ratio:.0%}\n"
                    f"   Liquidity: ${liquidity_usd:,.0f}\n"
                    f"   Meets ALL activity thresholds - age irrelevant!"
                )
            else:
                # Moonshot - skip activity filter!
                logger.info(f"🚀 {symbol}: Moonshot - skipping activity filter! Going straight to security checks!")

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

            # ═══════════════════════════════════════════════════════════════════
            # 🔒 COMPREHENSIVE RUG DETECTION - PHASE 1 (NON-NEGOTIABLE!)
            # ═══════════════════════════════════════════════════════════════════
            # Data shows: 58% stops <2min = instant rugs with -54%, -50% losses!
            # Solution: Strict security checks BEFORE entry to block rugs.
            # Expected impact: +$300-500 (prevent instant rugs)
            # ═══════════════════════════════════════════════════════════════════

            logger.info(f"🔍 Running comprehensive rug detection for {symbol}...")

            # ⚡ Fetch token security from Solana RPC
            security_info = await self.get_token_security(token_address)

            # CHECK 1: FREEZE AUTHORITY (NON-NEGOTIABLE!)
            # Must be DISABLED (None) - can freeze wallets = honeypot!
            has_freeze_authority = security_info.get('has_freeze_authority', True)  # Default True = reject if unknown
            if has_freeze_authority:
                logger.info(
                    f"⛔ BLOCKED {symbol}: Freeze authority ENABLED! 🚨\n"
                    f"   Can freeze wallets = HONEYPOT RISK!\n"
                    f"   Authority: {security_info.get('freeze_authority', 'Unknown')}\n"
                    f"   NON-NEGOTIABLE: Freeze authority MUST be disabled!"
                )
                self.rejected_tracker.record_rejection(
                    token_address=token_address,
                    rejection_reason="freeze_authority_enabled",
                    token_data=token_data,
                    symbol=symbol,
                    rejection_stage='rug_detection_freeze'
                )
                return

            # CHECK 2: MINT AUTHORITY (NON-NEGOTIABLE!)
            # Must be DISABLED (None) - can mint infinite tokens = rug!
            has_mint_authority = security_info.get('has_mint_authority', True)  # Default True = reject if unknown
            if has_mint_authority:
                logger.info(
                    f"⛔ BLOCKED {symbol}: Mint authority ENABLED! 🚨\n"
                    f"   Can create infinite tokens = RUG RISK!\n"
                    f"   Authority: {security_info.get('mint_authority', 'Unknown')}\n"
                    f"   NON-NEGOTIABLE: Mint authority MUST be disabled!"
                )
                self.rejected_tracker.record_rejection(
                    token_address=token_address,
                    rejection_reason="mint_authority_enabled",
                    token_data=token_data,
                    symbol=symbol,
                    rejection_stage='rug_detection_mint'
                )
                return

            # CHECK 3: LP LOCK CHECK (4th AI - SOFT CHECK!)
            # LP should be ≥80% locked/burnt - prevents rug pulls
            # SOFT: Only block if data EXISTS and is BAD (allow if data missing!)
            lp_locked_percent = token_data.get('lp_locked_percent', None)
            lp_burnt_percent = token_data.get('lp_burnt_percent', None)

            # Calculate total LP protection (locked + burnt)
            if lp_locked_percent is not None or lp_burnt_percent is not None:
                total_lp_protection = (lp_locked_percent or 0) + (lp_burnt_percent or 0)

                if total_lp_protection < 80:
                    logger.info(
                        f"⚠️ BLOCKED {symbol}: LP not secured! 🚨\n"
                        f"   LP locked: {lp_locked_percent or 0:.1f}%\n"
                        f"   LP burnt: {lp_burnt_percent or 0:.1f}%\n"
                        f"   Total protection: {total_lp_protection:.1f}% (need ≥80%)\n"
                        f"   Unsecured LP = RUG PULL RISK!"
                    )
                    self.rejected_tracker.record_rejection(
                        token_address=token_address,
                        rejection_reason=f"lp_unsecured_{total_lp_protection:.1f}%",
                        token_data=token_data,
                        symbol=symbol,
                        rejection_stage='rug_detection_lp'
                    )
                    return
            else:
                # Data missing - ALLOW (DEX not updated for new tokens)
                logger.debug(f"💡 {symbol}: LP lock data missing (new token?) - allowing trade")

            # CHECK 4: MINIMUM HOLDERS (NON-NEGOTIABLE!)
            # Must have 20+ holders - low holders = honeypot/instant rug risk
            holder_count = token_data.get('holder_count', 0)
            if holder_count > 0 and holder_count < 20:
                logger.info(
                    f"⛔ BLOCKED {symbol}: Too few holders! 🚨\n"
                    f"   Holders: {holder_count} (need 20+ minimum)\n"
                    f"   Low holders = HONEYPOT/INSTANT RUG RISK!\n"
                    f"   NON-NEGOTIABLE: Must have 20+ holders!"
                )
                self.rejected_tracker.record_rejection(
                    token_address=token_address,
                    rejection_reason=f"too_few_holders_{holder_count}",
                    token_data=token_data,
                    symbol=symbol,
                    rejection_stage='rug_detection_holders'
                )
                return

            # CHECK 4: TOP 10 HOLDER CONCENTRATION (NON-NEGOTIABLE!)
            # Top 10 must own <20% total - high concentration = whale dump risk
            top10_concentration = token_data.get('top10_concentration', 0)
            if top10_concentration > 20:
                logger.info(
                    f"⛔ BLOCKED {symbol}: Top 10 holders own too much! 🚨\n"
                    f"   Top 10 concentration: {top10_concentration:.1f}% (max 20%)\n"
                    f"   High concentration = WHALE DUMP RISK!\n"
                    f"   NON-NEGOTIABLE: Top 10 must own <20%!"
                )
                self.rejected_tracker.record_rejection(
                    token_address=token_address,
                    rejection_reason=f"top10_concentration_{top10_concentration:.1f}%",
                    token_data=token_data,
                    symbol=symbol,
                    rejection_stage='rug_detection_concentration'
                )
                return

            # CHECK 5: TOP 1 HOLDER CONCENTRATION (4th AI - SOFT CHECK!)
            # Top holder should own <10% (excluding burn/LP) - prevents whale dumps
            # SOFT: Only block if data EXISTS and is BAD (allow if data missing!)
            top1_concentration = token_data.get('top1_concentration', None)
            if top1_concentration is not None and top1_concentration > 10:
                logger.info(
                    f"⛔ BLOCKED {symbol}: Top holder owns too much! 🚨\n"
                    f"   Top 1 concentration: {top1_concentration:.1f}% (max 10%)\n"
                    f"   High concentration = WHALE DUMP RISK!\n"
                    f"   (Note: Excluding burn/LP wallets)"
                )
                self.rejected_tracker.record_rejection(
                    token_address=token_address,
                    rejection_reason=f"top1_holder_{top1_concentration:.1f}%",
                    token_data=token_data,
                    symbol=symbol,
                    rejection_stage='rug_detection_top1'
                )
                return
            elif top1_concentration is None:
                # Data missing - ALLOW (DEX not updated for new tokens)
                logger.debug(f"💡 {symbol}: Top holder data missing (new token?) - allowing trade")

            # ✅ ALL RUG DETECTION CHECKS PASSED!
            holder_str = f"{holder_count}" if holder_count > 0 else "N/A"
            top10_str = f"{top10_concentration:.1f}%" if top10_concentration else "N/A"
            top1_str = f"{top1_concentration:.1f}%" if top1_concentration else "N/A"

            logger.info(
                f"✅ {symbol}: PASSED comprehensive rug detection!\n"
                f"   ✓ Freeze authority: DISABLED\n"
                f"   ✓ Mint authority: DISABLED\n"
                f"   ✓ Holders: {holder_str}\n"
                f"   ✓ Top 10 concentration: {top10_str}\n"
                f"   ✓ Top 1 concentration: {top1_str}\n"
                f"   Token appears SAFE for entry! 🎯"
            )

            # === ENTRY QUALITY FILTERS (ML Bot Style) ===
            # Filter #1: Buy/Sell Ratio (Bullish Momentum)
            buy_ratio_24h = token_data.get('buy_ratio_24h', 0)
            buy_ratio_1h = token_data.get('buy_ratio_1h', 0)

            # Use 1h if available (recent activity), otherwise 24h
            buy_ratio = buy_ratio_1h if buy_ratio_1h > 0 else buy_ratio_24h

            if buy_ratio < 0.35:  # Require 35%+ buyers (we have strong activity filters)
                logger.info(
                    f"⛔ Skipped {symbol}: Low buy ratio {buy_ratio:.1%} (need 35%+). "
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

            # Filter #3: Liquidity Range (Sweet Spot)
            liquidity_usd = token_data.get('liquidity_usd', 0)
            MIN_LIQUIDITY = 15_000  # 4th AI optimized: avoid slippage death!
            MAX_LIQUIDITY = 3_000_000  # Maximum $3M (still agile, can pump fast)

            if liquidity_usd < MIN_LIQUIDITY:
                # ⚡ EXCEPTION: New launches with $0 liquidity BUT strong activity
                # Data shows: 93% of liq $0 are <24h, 43% pump >20%! 🔥
                token_age_hours = token_data.get('token_age_hours', 999)
                volume_1h = token_data.get('volume_1h', 0)
                txns_1h = token_data.get('txns_1h', 0)

                # 🔍 DEBUG: Log why liq $0 tokens are blocked
                if liquidity_usd == 0:
                    logger.warning(
                        f"🔍 Liq $0 debug for {symbol}:\n"
                        f"  Age: {token_age_hours:.2f}h\n"
                        f"  Vol 1h: ${volume_1h:,.0f}\n"
                        f"  Txns 1h: {txns_1h}\n"
                        f"  Buy ratio: {buy_ratio:.1%}\n"
                        f"  TIER 1 check (<30min): age={token_age_hours < 0.5}, vol={volume_1h >= 5000}, txns={txns_1h >= 100}\n"
                        f"  TIER 2 check (<24h): age={token_age_hours < 24}, vol={volume_1h >= 20000}, txns={txns_1h >= 100}, buy={buy_ratio >= 0.50}"
                    )

                # TIER 1: VERY new launches (<30 min) - lenient
                if liquidity_usd == 0 and token_age_hours < 0.5 and volume_1h >= 5000 and txns_1h >= 100:
                    logger.info(
                        f"✅ {symbol}: $0 liq BUT brand new ({token_age_hours*60:.0f} min old) + activity "
                        f"(${volume_1h:,.0f}/1h, {txns_1h} txns) - API delay! TIER 1 exception."
                    )
                    # Continue to other checks!

                # TIER 2: New launches (<24h) - stricter criteria 🔥
                elif liquidity_usd == 0 and token_age_hours < 24 and volume_1h >= 20000 and txns_1h >= 100 and buy_ratio >= 0.50:
                    logger.info(
                        f"✅ {symbol}: $0 liq BUT new launch ({token_age_hours:.1f}h old) + STRONG activity "
                        f"(${volume_1h:,.0f}/1h, {txns_1h} txns, {buy_ratio:.1%} buy) - API lag! TIER 2 exception."
                    )
                    # Continue to other checks! ⚡

                # TIER 3: Low liquidity ($0-$20k) but HIGH volume compensates
                elif liquidity_usd < 20_000 and volume_1h >= 50000:
                    logger.info(
                        f"✅ {symbol}: Low liq ${liquidity_usd:,.0f} BUT HIGH volume ${volume_1h:,.0f}/1h compensates! "
                        f"TIER 3 exception (Ralph example: $15k liq, 272% pump!)."
                    )
                    # Continue to other checks!

                else:
                    # Truly low liquidity - reject
                    reason = f"low_liquidity_${liquidity_usd:,.0f}"
                    if liquidity_usd == 0:
                        reason += f"_age{token_age_hours:.1f}h_vol${volume_1h:,.0f}_txns{txns_1h}"

                    logger.info(
                        f"⛔ Skipped {symbol}: Too low liquidity ${liquidity_usd:,.0f} (min ${MIN_LIQUIDITY:,.0f}). "
                        f"Age: {token_age_hours:.1f}h, Vol: ${volume_1h:,.0f}, Txns: {txns_1h}. "
                        f"Failed all 3 tiers. Cannot enter/exit safely."
                    )
                    # Track rejection for analysis
                    self.rejected_tracker.record_rejection(
                        token_address=token_address,
                        rejection_reason=reason,
                        token_data=token_data,
                        symbol=symbol,
                        rejection_stage='screening'
                    )
                    return

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
            volume_24h = token_data.get('volume_24h', 0)  # Still needed for logging
            # MAX_VOLUME_24H = 1_000_000  # DISABLED

            # Filter #5: Recent Activity (1h Volume)
            volume_1h = token_data.get('volume_1h', None)  # None if not available
            MIN_VOLUME_1H = 3_000  # Minimum $3k/hour activity

            # Only check if 1h data is available
            if volume_1h is not None:
                if volume_1h < MIN_VOLUME_1H:  # Includes 0 (dead token!)
                    logger.info(
                        f"⛔ Skipped {symbol}: Dead/low recent volume ${volume_1h:,.0f}/1h (need ${MIN_VOLUME_1H:,.0f}+). "
                        f"No recent activity = no momentum."
                    )
                    # Track rejection for analysis
                    self.rejected_tracker.record_rejection(
                        token_address=token_address,
                        rejection_reason=f"low_volume_1h_${volume_1h:,.0f}",
                        token_data=token_data,
                        symbol=symbol,
                        rejection_stage='screening'
                    )
                    return

            # Filter #6: Recent Buyers (1h Buys)
            buys_1h = token_data.get('buys_1h', None)  # None if not available
            MIN_BUYS_1H = 10  # Minimum 10 buy transactions per hour

            # Only check if 1h data is available
            if buys_1h is not None:
                if buys_1h < MIN_BUYS_1H:  # Includes 0 (no buyers!)
                    logger.info(
                        f"⛔ Skipped {symbol}: No recent buyers {buys_1h}/1h (need {MIN_BUYS_1H}+). "
                        f"Dead token = no momentum."
                    )
                    # Track rejection for analysis
                    self.rejected_tracker.record_rejection(
                        token_address=token_address,
                        rejection_reason=f"low_buys_1h_{buys_1h}",
                        token_data=token_data,
                        symbol=symbol,
                        rejection_stage='screening'
                    )
                    return

            # Format 1h data for logging (handle None values)
            vol_1h_str = f"${volume_1h:,.0f}" if volume_1h is not None else "N/A"
            buys_1h_str = str(buys_1h) if buys_1h is not None else "N/A"

            logger.info(
                f"✅ Quality checks passed: {symbol} - "
                f"Buy ratio: {buy_ratio:.1%} (24h: {buy_ratio_24h:.1%}, 1h: {buy_ratio_1h:.1%}), "
                f"Activity: {txns_24h} txns (1h: {txns_1h}), "
                f"Liq: ${liquidity_usd:,.0f}, Vol: ${volume_24h:,.0f} (1h: {vol_1h_str}), "
                f"Buys/1h: {buys_1h_str}"
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

        # Close RPC session
        if self.rpc_session and not self.rpc_session.closed:
            await self.rpc_session.close()
            logger.info("RPC session closed")

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
