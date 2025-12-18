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
            max_position_size=config.paper_sol_balance / config.core_config.max_open_positions
        )
        logger.info("  ✅ RiskAssessor initialized")

        self.position_manager = PositionManager(
            max_open_positions=config.core_config.max_open_positions
        )
        logger.info("  ✅ PositionManager initialized")

        # Initialize PriceValidator with API clients
        from trading_bot.api_clients import DexScreenerClient, JupiterClient
        dexscreener_client = DexScreenerClient(api_key=config.dexscreener_api_key)
        jupiter_client = JupiterClient()

        self.price_validator = PriceValidator(
            dexscreener_client=dexscreener_client,
            jupiter_client=jupiter_client
        )
        logger.info("  ✅ PriceValidator initialized")

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

        # === 🔍 TOKEN SCANNER ===
        from trading_bot.scanner import TokenScanner
        self.scanner = TokenScanner(
            min_liquidity=config.core_config.min_position_liquidity,
            min_volume_24h=10000,
            dexscreener_api_key=config.dexscreener_api_key
        )
        logger.info("  ✅ TokenScanner initialized")

        # === 💰 TRADE EXECUTOR ===
        from trading_bot.executor import PaperTradingExecutor
        if config.paper_trading:
            self.executor = PaperTradingExecutor(initial_balance=config.paper_sol_balance)
            logger.info(f"  ✅ PaperTradingExecutor initialized (${config.paper_sol_balance:.2f} SOL)")
        else:
            raise NotImplementedError("Live trading not implemented yet! Use PAPER_TRADING_MODE=true")

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
        symbol: str = ''
    ) -> Optional[object]:
        """
        Open a new position using protected core.

        Args:
            token_address: Token address
            entry_price: Entry price
            amount_usd: Position size in USD
            symbol: Token symbol (optional)

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
            trailing_stop_percent=self.config.core_config.trailing_stop_percent
        )

        if position:
            position.symbol = symbol  # Set symbol for display

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

                if not price_data:
                    logger.warning(f"⚠️  No price data for {position.symbol or position.token_address[:8]}...")
                    continue

                current_price = price_data['price']
                current_liquidity = price_data.get('liquidity', 0)

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
                            self.executor.available_balance += sell_value

                            # Calculate profit on this partial sell
                            cost_basis = position.entry_price * sell_quantity
                            partial_profit = sell_value - cost_basis

                            logger.info(
                                f"💵 Locked in ${partial_profit:.2f} profit, "
                                f"Remaining: {position.quantity:.2f} tokens (${position.amount_usd:.2f} cost basis)"
                            )

        # Check exit conditions for remaining positions
        for position in list(self.position_manager.get_all_positions()):
            # 1. Stop Loss
            if self.position_manager.check_stop_loss(position.token_address):
                logger.warning(f"🛑 Stop loss hit: {position.symbol or position.token_address[:8]}...")
                await self.close_position(
                    position.token_address,
                    position.current_price,
                    'stop_loss'
                )
                continue

            # 2. Trailing Stop
            if self.position_manager.check_trailing_stop(position.token_address):
                logger.info(f"📊 Trailing stop hit: {position.symbol or position.token_address[:8]}...")
                await self.close_position(
                    position.token_address,
                    position.current_price,
                    'trailing_stop'
                )
                continue

            # 3. Rug Detection
            if self.config.core_config.rug_detection_enabled:
                dead_positions = self.position_manager.get_dead_positions(
                    stale_minutes=self.config.core_config.stale_price_minutes,
                    min_liquidity=self.config.core_config.min_position_liquidity
                )

                if position.token_address in dead_positions:
                    logger.error(f"🚨 Rug detected: {position.symbol or position.token_address[:8]}...")
                    await self.close_position(
                        position.token_address,
                        position.current_price,
                        'low_liquidity'
                    )

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

            # Scan for new tokens
            tokens = await self.scanner.scan_new_tokens(limit=10)

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

            # Prepare data for risk assessment
            market_data = {
                'price_usd': token_data.get('price_usd', 0),
                'liquidity_usd': token_data.get('liquidity_usd', 0),
                'volume_24h': token_data.get('volume_24h', 0),
                'price_change_5m': token_data.get('price_change_5m', 0),
                'price_change_1h': token_data.get('price_change_1h', 0),
                'txns_24h': token_data.get('txns_24h', 0),
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
                return

            # === EXECUTE TRADE ===
            entry_price = market_data['price_usd']
            position_size = 70.0  # From config, would use recommended_position_size from assessment

            # Check executor balance
            balance = self.executor.get_balance()
            if balance['available_balance'] < position_size:
                logger.warning(f"Insufficient balance: ${balance['available_balance']:.2f} < ${position_size:.2f}")
                return

            # Execute buy
            trade_result = await self.executor.execute_buy(
                token_address=token_address,
                amount_sol=position_size,
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
                amount_usd=position_size,
                symbol=symbol
            )

            if position:
                logger.info(f"✅ Position opened successfully: {symbol}")
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
