"""
Fearless Momentum Runner v2.0 - Main Orchestrator

The complete trading bot that ties all phases together:
- Phase 1: Entry Logic (indicators, strategies, filters)
- Phase 2: Position Management (breakeven, pyramids, partials)
- Phase 3: Exit Logic (stops, weakness, time exits)
- Phase 4: Orchestration (scanning, monitoring, execution)

Target: 50-60% win rate, catch 500-1700% runners while preserving capital.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# Phase 1: Entry Logic
from src.api.jupiter_client import JupiterClient
from src.api.dexscreener_client import DexScreenerClient
from src.strategies.momentum_entry import MomentumEntry
from src.strategies.trend_confirmation import TrendConfirmation
from src.strategies.anti_fomo import AntiFOMO
from src.filters.safety_check import SafetyCheck
from src.data.logger import DataLogger

# Phase 2: Position Management
from src.position.position_manager import PositionManager
from src.position.breakeven_handler import BreakevenHandler
from src.position.pyramid_manager import PyramidManager
from src.position.partial_profits import PartialProfits
from src.execution.jupiter_executor import JupiterExecutor

# Phase 3: Exit Logic
from src.exit.exit_manager import ExitManager

# Phase 4: Orchestration
from src.utils.token_data_gatherer import TokenDataGatherer
from src.monitoring.health_check import HealthCheck
from src.monitoring.telegram_notifier import TelegramNotifier

# Configuration
from config.parameters import (
    SCAN_INTERVAL_SECONDS,
    HEALTH_CHECK_INTERVAL_SEC,
    MAX_SCAN_RETRIES,
    SCAN_RETRY_DELAY_SEC,
    MAX_CONCURRENT_POSITIONS,
    DEFAULT_POSITION_SIZE_SOL,
    DISCOVERY_TOKEN_LIMIT,
    MIN_LIQUIDITY_USD,
    MIN_VOLUME_24H_USD,
    TELEGRAM_ENABLED,
    NOTIFY_ON_ENTRY,
    NOTIFY_ON_EXIT,
    NOTIFY_ON_BREAKEVEN,
    NOTIFY_ON_PYRAMID,
    NOTIFY_ON_PARTIAL
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_bot.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class MomentumBot:
    """
    Main trading bot orchestrator.

    Manages the complete trading lifecycle:
    - Scan for opportunities
    - Enter positions
    - Manage positions (breakeven, pyramids, partials)
    - Exit positions (stops, weakness, time)
    """

    def __init__(self, mock_mode: bool = True):
        """
        Initialize the trading bot.

        Args:
            mock_mode: If True, use mock execution (paper trading)
        """
        logger.info("=" * 60)
        logger.info("Initializing Fearless Momentum Runner v2.0...")
        logger.info("=" * 60)

        # State tracking
        self.running = False
        self.mock_mode = mock_mode
        self.last_scan_time = None
        self.last_health_check = None
        self.scan_count = 0
        self.entry_count = 0
        self.exit_count = 0
        self.win_count = 0

        # Phase 1: Entry Logic
        logger.info("Loading Phase 1: Entry Logic...")
        self.jupiter_client = JupiterClient()
        self.dexscreener_client = DexScreenerClient()
        self.momentum_entry = MomentumEntry()
        self.trend_confirmation = TrendConfirmation()
        self.anti_fomo = AntiFOMO()
        self.safety_check = SafetyCheck()
        self.data_logger = DataLogger()

        # Phase 2: Position Management
        logger.info("Loading Phase 2: Position Management...")
        self.breakeven_handler = BreakevenHandler()
        self.pyramid_manager = PyramidManager()
        self.partial_profits = PartialProfits()
        self.jupiter_executor = JupiterExecutor(mock_mode=mock_mode)
        self.position_manager = PositionManager(
            breakeven_handler=self.breakeven_handler,
            pyramid_manager=self.pyramid_manager,
            partial_profits=self.partial_profits
        )

        # Phase 3: Exit Logic
        logger.info("Loading Phase 3: Exit Logic...")
        self.exit_manager = ExitManager()

        # Phase 4: Orchestration
        logger.info("Loading Phase 4: Orchestration...")
        self.token_gatherer = TokenDataGatherer()
        self.health_check = HealthCheck()
        self.telegram = TelegramNotifier() if TELEGRAM_ENABLED else None

        logger.info("=" * 60)
        logger.info(f"✅ Bot initialized - {'MOCK MODE' if mock_mode else 'LIVE MODE'}")
        logger.info("=" * 60)

    async def run(self):
        """Main bot loop - runs forever."""
        logger.info("🚀 Fearless Momentum Runner v2.0 STARTED!")
        logger.info(f"   Mode: {'MOCK (Paper Trading)' if self.mock_mode else 'LIVE'}")
        logger.info(f"   Scan interval: {SCAN_INTERVAL_SECONDS}s")
        logger.info(f"   Max positions: {MAX_CONCURRENT_POSITIONS}")
        logger.info("")

        self.running = True

        # Send startup notification
        if self.telegram:
            self.telegram.send_startup_notification()

        try:
            while self.running:
                try:
                    # 1. Scan for new entry opportunities
                    await self.scan_tokens()

                    # 2. Update existing positions
                    await self.update_positions()

                    # 3. Health check (every 5 minutes)
                    await self.periodic_health_check()

                    # 4. Sleep before next cycle
                    await asyncio.sleep(SCAN_INTERVAL_SECONDS)

                except KeyboardInterrupt:
                    logger.info("\n⏹️ Shutdown requested by user")
                    break

                except Exception as e:
                    logger.error(f"❌ Main loop error: {e}", exc_info=True)

                    if self.telegram:
                        self.telegram.send_error_alert(str(e), "Main loop")

                    # Wait longer before retrying after error
                    await asyncio.sleep(60)

        finally:
            await self.shutdown()

    async def scan_tokens(self):
        """Scan for new entry opportunities."""
        try:
            # Check if at max positions
            if self.position_manager.get_position_count() >= MAX_CONCURRENT_POSITIONS:
                logger.debug(
                    f"At max positions ({MAX_CONCURRENT_POSITIONS}) - skipping scan"
                )
                return

            logger.info(f"\n{'='*60}")
            logger.info(f"🔍 SCAN #{self.scan_count + 1} - Looking for opportunities...")
            logger.info(f"{'='*60}")

            # Get trending tokens from Jupiter
            trending_tokens = await self._get_trending_tokens()

            if not trending_tokens:
                logger.warning("No trending tokens found")
                self.last_scan_time = datetime.now()
                return

            logger.info(f"Found {len(trending_tokens)} trending tokens to analyze")

            # Analyze each token
            opportunities = 0

            for token_address in trending_tokens:
                # Check if already have position
                if self.position_manager.get_position(token_address):
                    logger.debug(f"Already have position in {token_address[:8]}")
                    continue

                # Check if at max positions
                if self.position_manager.get_position_count() >= MAX_CONCURRENT_POSITIONS:
                    logger.info("Reached max positions during scan - stopping")
                    break

                # Analyze token
                entered = await self._analyze_and_enter(token_address)

                if entered:
                    opportunities += 1

            self.scan_count += 1
            self.last_scan_time = datetime.now()

            logger.info(
                f"✅ Scan complete: {opportunities} entries from {len(trending_tokens)} tokens"
            )

        except Exception as e:
            logger.error(f"Error in scan_tokens: {e}", exc_info=True)

    async def _get_trending_tokens(self) -> List[str]:
        """Get trending tokens from Jupiter."""
        try:
            # For now, use a curated list or get from Jupiter API
            # In production, Jupiter has a trending tokens endpoint

            logger.debug("Getting trending tokens from Jupiter...")

            # TODO: Implement Jupiter trending tokens API
            # For now, return empty list (Phase 4 mock mode)

            return []

        except Exception as e:
            logger.error(f"Error getting trending tokens: {e}")
            return []

    async def _analyze_and_enter(self, token_address: str) -> bool:
        """
        Analyze token and enter if passes all checks.

        Returns:
            True if entered position
        """
        try:
            logger.debug(f"\nAnalyzing {token_address[:8]}...")

            # Step 1: Quick safety check (LP + Mint)
            safety = self.token_gatherer.verify_safety(token_address)

            if not safety["passed"]:
                logger.debug(
                    f"❌ {token_address[:8]} failed safety: "
                    f"LP={safety['lp_burned']}, Mint={safety['mint_revoked']}"
                )
                self.data_logger.log_rejection(
                    token_address, "SAFETY_FAIL", "LP or Mint not safe"
                )
                return False

            # Step 2: Gather complete token data
            token_data = self.token_gatherer.gather_complete_data(token_address)

            if not token_data:
                logger.debug(f"❌ {token_address[:8]} - could not gather data")
                return False

            # Check liquidity/volume minimums
            if token_data["liquidity"] < MIN_LIQUIDITY_USD:
                logger.debug(
                    f"❌ {token_data['symbol']} - low liquidity ${token_data['liquidity']:,.0f}"
                )
                self.data_logger.log_rejection(
                    token_address, "LOW_LIQUIDITY", f"${token_data['liquidity']:,.0f}"
                )
                return False

            if token_data["volume_24h"] < MIN_VOLUME_24H_USD:
                logger.debug(
                    f"❌ {token_data['symbol']} - low volume ${token_data['volume_24h']:,.0f}"
                )
                self.data_logger.log_rejection(
                    token_address, "LOW_VOLUME", f"${token_data['volume_24h']:,.0f}"
                )
                return False

            # Step 3: Check momentum pattern (80+ score)
            momentum_result = self.momentum_entry.check_pattern(token_data)

            if not momentum_result["match"]:
                logger.debug(
                    f"❌ {token_data['symbol']} - momentum score {momentum_result['score']}/100"
                )
                self.data_logger.log_rejection(
                    token_address, "MOMENTUM_FAIL", f"Score {momentum_result['score']}/100"
                )
                return False

            # Step 4: Check trend confirmation
            trend_result = self.trend_confirmation.check_trend(token_data)

            if not trend_result["confirmed"]:
                logger.debug(f"❌ {token_data['symbol']} - trend not confirmed")
                self.data_logger.log_rejection(
                    token_address, "TREND_FAIL", trend_result["reason"]
                )
                return False

            # Step 5: Check anti-FOMO
            fomo_result = self.anti_fomo.should_wait(token_data)

            if fomo_result["wait"]:
                logger.debug(f"❌ {token_data['symbol']} - FOMO detected: {fomo_result['reason']}")
                self.data_logger.log_rejection(
                    token_address, "FOMO_BLOCK", fomo_result["reason"]
                )
                return False

            # ALL CHECKS PASSED - ENTER POSITION!
            logger.info("")
            logger.info(f"🎯 ENTRY SIGNAL: {token_data['symbol']}")
            logger.info(f"   Momentum Score: {momentum_result['score']}/100")
            logger.info(f"   Signals: {', '.join(momentum_result['signals'])}")

            await self.enter_position(token_data, momentum_result)

            return True

        except Exception as e:
            logger.error(f"Error analyzing token: {e}", exc_info=True)
            return False

    async def enter_position(self, token_data: Dict, momentum_result: Dict):
        """
        Enter a new position.

        Args:
            token_data: Complete token data
            momentum_result: Momentum check result
        """
        try:
            token_address = token_data["address"]
            symbol = token_data["symbol"]
            entry_price = token_data["price"]
            size_sol = DEFAULT_POSITION_SIZE_SOL

            logger.info(f"\n{'='*60}")
            logger.info(f"💰 ENTERING POSITION: {symbol}")
            logger.info(f"{'='*60}")

            # Execute buy
            buy_result = self.jupiter_executor.execute_buy(
                token_address=token_address,
                amount_sol=size_sol,
                slippage_bps=100
            )

            if not buy_result["success"]:
                logger.error(f"❌ Buy failed: {buy_result['error']}")
                return

            logger.info(
                f"✅ Buy executed: {buy_result['tokens_received']:.2f} tokens "
                f"@ {buy_result['price']:.8f} SOL/token"
            )

            # Create position
            position = self.position_manager.open_position(
                token_address=token_address,
                symbol=symbol,
                entry_price=entry_price,
                size_sol=size_sol
            )

            # Log trade
            self.data_logger.log_trade(
                token_address=token_address,
                symbol=symbol,
                action="ENTRY",
                price=entry_price,
                size_sol=size_sol,
                pnl_percent=0,
                reason=f"Momentum {momentum_result['score']}/100",
                metadata={
                    "momentum_score": momentum_result["score"],
                    "signals": momentum_result["signals"],
                    "signature": buy_result["signature"]
                }
            )

            # Send Telegram notification
            if self.telegram and NOTIFY_ON_ENTRY:
                self.telegram.send_entry_notification(
                    position=position.to_dict(),
                    momentum_score=momentum_result["score"],
                    signals=momentum_result["signals"]
                )

            self.entry_count += 1

            logger.info(f"✅ Position opened: {symbol} ({self.entry_count} total entries)")
            logger.info(f"{'='*60}\n")

        except Exception as e:
            logger.error(f"Error entering position: {e}", exc_info=True)

    async def update_positions(self):
        """Update all open positions and check for exits/actions."""
        try:
            positions = self.position_manager.get_all_positions()

            if not positions:
                return  # No positions to update

            logger.debug(f"\n📊 Updating {len(positions)} open positions...")

            for position in positions:
                try:
                    await self._update_single_position(position)
                except Exception as e:
                    logger.error(
                        f"Error updating position {position.symbol}: {e}",
                        exc_info=True
                    )

        except Exception as e:
            logger.error(f"Error in update_positions: {e}", exc_info=True)

    async def _update_single_position(self, position):
        """Update a single position."""
        try:
            token_address = position.token_address

            # Get current price
            price_update = self.token_gatherer.gather_price_update(token_address)

            if not price_update:
                logger.warning(f"Could not get price update for {position.symbol}")
                return

            current_price = price_update["price"]

            # Get full token data for exit checks
            token_data = self.token_gatherer.gather_complete_data(token_address)

            if not token_data:
                logger.warning(f"Could not gather full data for {position.symbol}")
                # Use price-only update
                token_data = price_update

            # Update position and check triggers (breakeven, pyramids, partials)
            actions = self.position_manager.update_position(
                token_address,
                current_price,
                token_data
            )

            # Handle breakeven trigger
            if actions.get("breakeven"):
                await self._handle_breakeven(position, actions["breakeven"])

            # Handle pyramid trigger
            if actions.get("pyramid"):
                await self._handle_pyramid(position, actions["pyramid"], token_data)

            # Handle partial profits
            for partial in actions.get("partials", []):
                await self._handle_partial(position, partial, current_price)

            # Check exit conditions
            exit_decision = self.exit_manager.check_exit_conditions(position, token_data)

            if exit_decision["should_exit"]:
                await self.exit_position(position, exit_decision, current_price)

            else:
                # Log status
                logger.debug(
                    f"  {position.symbol}: {position.pnl_percent:+.1f}% "
                    f"(${current_price:.8f}) - {position.hold_time_minutes}m"
                )

        except Exception as e:
            logger.error(f"Error updating position: {e}", exc_info=True)

    async def _handle_breakeven(self, position, breakeven_result: Dict):
        """Handle breakeven trigger."""
        try:
            if not breakeven_result["triggered"]:
                return

            logger.info(f"\n🛡️ BREAKEVEN: {position.symbol} at +{position.pnl_percent:.1f}%")

            # Execute 40% sell
            sell_pct = breakeven_result["sell_percent"]
            sell_amount = position.current_size_sol * (sell_pct / 100)

            sell_result = self.jupiter_executor.execute_sell(
                token_address=position.token_address,
                amount_tokens=sell_amount,
                slippage_bps=100
            )

            if sell_result["success"]:
                # Update position
                position.take_partial(sell_pct, position.current_price, "BREAKEVEN_50")

                logger.info(
                    f"   Sold {sell_pct}% - position now RISK-FREE!"
                )

                # Notify
                if self.telegram and NOTIFY_ON_BREAKEVEN:
                    self.telegram.send_breakeven_notification(position.to_dict())

        except Exception as e:
            logger.error(f"Error handling breakeven: {e}", exc_info=True)

    async def _handle_pyramid(self, position, pyramid_result: Dict, token_data: Dict):
        """Handle pyramid add."""
        try:
            if not pyramid_result["should_add"]:
                return

            stage = pyramid_result["stage"]
            size_sol = pyramid_result["size_sol"]

            logger.info(
                f"\n🔺 PYRAMID STAGE {stage}: {position.symbol} at +{position.pnl_percent:.1f}%"
            )

            # Execute buy
            buy_result = self.jupiter_executor.execute_buy(
                token_address=position.token_address,
                amount_sol=size_sol,
                slippage_bps=100
            )

            if buy_result["success"]:
                # Update position
                position.add_to_position(size_sol, position.current_price, f"PYRAMID_{stage}")

                # Mark as triggered
                if stage == 1:
                    position.pyramid_1_triggered = True
                elif stage == 2:
                    position.pyramid_2_triggered = True

                logger.info(f"   Added {size_sol:.4f} SOL - total: {position.current_size_sol:.4f} SOL")

                # Notify
                if self.telegram and NOTIFY_ON_PYRAMID:
                    self.telegram.send_pyramid_notification(
                        position.to_dict(),
                        stage,
                        pyramid_result["size_percent"]
                    )

        except Exception as e:
            logger.error(f"Error handling pyramid: {e}", exc_info=True)

    async def _handle_partial(self, position, partial_result: Dict, current_price: float):
        """Handle partial profit."""
        try:
            if not partial_result["should_sell"]:
                return

            sell_pct = partial_result["sell_pct"]
            trigger_pct = partial_result["trigger_pct"]
            partial_name = partial_result["partial_name"]

            logger.info(
                f"\n💰 PARTIAL PROFIT: {position.symbol} at +{position.pnl_percent:.1f}%"
            )

            # Execute sell
            sell_amount = position.current_size_sol * (sell_pct / 100)

            sell_result = self.jupiter_executor.execute_sell(
                token_address=position.token_address,
                amount_tokens=sell_amount,
                slippage_bps=100
            )

            if sell_result["success"]:
                # Update position
                position.take_partial(sell_pct, current_price, partial_name)

                logger.info(f"   Sold {sell_pct}% - remaining: {position.current_size_sol:.4f} SOL")

                # Notify
                if self.telegram and NOTIFY_ON_PARTIAL:
                    self.telegram.send_partial_notification(
                        position.to_dict(),
                        sell_pct,
                        trigger_pct
                    )

        except Exception as e:
            logger.error(f"Error handling partial: {e}", exc_info=True)

    async def exit_position(self, position, exit_decision: Dict, current_price: float):
        """Exit a position."""
        try:
            logger.info(f"\n{'='*60}")
            logger.info(f"🚪 EXITING POSITION: {position.symbol}")
            logger.info(f"   Reason: {exit_decision['reason']}")
            logger.info(f"   P&L: {position.pnl_percent:+.1f}%")
            logger.info(f"{'='*60}")

            # Execute sell
            sell_result = self.jupiter_executor.execute_sell(
                token_address=position.token_address,
                amount_tokens=position.current_size_sol,
                slippage_bps=100
            )

            if not sell_result["success"]:
                logger.error(f"❌ Sell failed: {sell_result['error']}")
                return

            # Close position
            summary = self.position_manager.close_position(
                token_address=position.token_address,
                exit_price=current_price,
                reason=exit_decision["reason"]
            )

            # Log trade
            self.data_logger.log_trade(
                token_address=position.token_address,
                symbol=position.symbol,
                action="EXIT",
                price=current_price,
                size_sol=position.current_size_sol,
                pnl_percent=summary["final_pnl_percent"],
                reason=exit_decision["reason"],
                metadata={
                    "exit_type": exit_decision["exit_type"],
                    "hold_time_minutes": summary["hold_time_minutes"],
                    "signature": sell_result["signature"]
                }
            )

            # Update stats
            self.exit_count += 1
            if summary["final_pnl_percent"] > 0:
                self.win_count += 1

            win_rate = (self.win_count / self.exit_count * 100) if self.exit_count > 0 else 0

            # Notify
            if self.telegram and NOTIFY_ON_EXIT:
                self.telegram.send_exit_notification(
                    position=summary,
                    exit_reason=exit_decision["reason"],
                    duration_minutes=summary["hold_time_minutes"],
                    win_rate=win_rate,
                    total_trades=self.exit_count
                )

            logger.info(f"✅ Position closed: {position.symbol}")
            logger.info(f"   Win rate: {win_rate:.1f}% ({self.win_count}/{self.exit_count})")
            logger.info(f"{'='*60}\n")

        except Exception as e:
            logger.error(f"Error exiting position: {e}", exc_info=True)

    async def periodic_health_check(self):
        """Run periodic health check."""
        try:
            now = datetime.now()

            # Only run every HEALTH_CHECK_INTERVAL_SEC
            if self.last_health_check:
                elapsed = (now - self.last_health_check).total_seconds()
                if elapsed < HEALTH_CHECK_INTERVAL_SEC:
                    return

            position_count = self.position_manager.get_position_count()

            health = self.health_check.check_system_health(
                last_scan_time=self.last_scan_time,
                position_count=position_count
            )

            self.last_health_check = now

            # Send alert if issues
            if health["status"] != "healthy" and self.telegram:
                self.telegram.send_health_alert(health)

        except Exception as e:
            logger.error(f"Error in health check: {e}")

    async def shutdown(self):
        """Clean shutdown."""
        logger.info("\n" + "=" * 60)
        logger.info("⏹️ SHUTTING DOWN...")
        logger.info("=" * 60)

        self.running = False

        # Close all positions
        positions = self.position_manager.get_all_positions()

        if positions:
            logger.info(f"Closing {len(positions)} open positions...")

            for position in positions:
                try:
                    await self.exit_position(
                        position,
                        {"reason": "Bot shutdown", "exit_type": "shutdown"},
                        position.current_price
                    )
                except Exception as e:
                    logger.error(f"Error closing position on shutdown: {e}")

        # Send shutdown notification
        if self.telegram:
            self.telegram.send_shutdown_notification()

        # Print final stats
        logger.info("\n" + "=" * 60)
        logger.info("FINAL STATISTICS")
        logger.info("=" * 60)
        logger.info(f"Total scans: {self.scan_count}")
        logger.info(f"Total entries: {self.entry_count}")
        logger.info(f"Total exits: {self.exit_count}")

        if self.exit_count > 0:
            win_rate = (self.win_count / self.exit_count) * 100
            logger.info(f"Win rate: {win_rate:.1f}% ({self.win_count}/{self.exit_count})")

        logger.info("=" * 60)
        logger.info("✅ Shutdown complete")
        logger.info("=" * 60)


# Example/testing
if __name__ == "__main__":
    import sys

    print("=" * 60)
    print("Fearless Momentum Runner v2.0")
    print("=" * 60)
    print("\nThis is the main orchestrator module.")
    print("To run the bot, use: python run.py")
    print()

    sys.exit(0)
