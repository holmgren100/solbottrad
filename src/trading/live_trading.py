"""
Live Trading Engine for real Solana swaps via Jupiter.
Manages real wallet, executes actual trades, tracks on-chain positions.
"""

import asyncio
import os
import json
import httpx
from typing import Dict, Optional
from datetime import datetime
from .position_manager import PositionManager, Position, Trade
from .strategy_config import StrategySelector, StrategyProfile
from ..blockchain.jupiter_executor import JupiterSwapExecutor
from ..monitoring.logger import get_logger

logger = get_logger(__name__)


class LiveTradingEngine:
    """
    Live trading engine that executes real swaps on Solana via Jupiter.

    Similar to PaperTradingEngine but uses real wallet and blockchain transactions.
    """

    def __init__(
        self,
        jupiter_executor: JupiterSwapExecutor,
        position_manager: Optional[PositionManager] = None,
        max_open_positions: int = 12,
        state_file: str = 'live_trading_state.json'
    ):
        """
        Initialize live trading engine.

        Args:
            jupiter_executor: Jupiter executor configured with wallet
            position_manager: Optional position manager (creates new if not provided)
            max_open_positions: Maximum simultaneous positions
            state_file: Path to state file for persistence
        """
        self.jupiter_executor = jupiter_executor
        self.position_manager = position_manager or PositionManager(max_open_positions)
        self.state_file = state_file

        # Store RPC URL for direct HTTP requests
        # (Workaround for httpx 0.28+ compatibility with solana library)
        self.rpc_url = jupiter_executor.rpc_url

        # Trading state (tracked separately from wallet balance)
        self.starting_balance = 0.0  # Will be set from actual wallet on first check
        self.total_invested = 0.0  # Currently invested in open positions

        # Age-based strategies (optional - can disable to use golden settings)
        self.enable_age_strategies = os.getenv('ENABLE_AGE_BASED_STRATEGIES', 'false').lower() == 'true'
        if self.enable_age_strategies:
            self.strategy_selector = StrategySelector()
            logger.info("✅ Age-based profit strategies ENABLED")
        else:
            self.strategy_selector = None
            logger.info("🔒 Age-based strategies DISABLED - using golden settings")

        # Trailing stop settings (from environment) - used as fallback
        self.use_trailing_stop = os.getenv('USE_TRAILING_STOP', 'true').lower() == 'true'
        self.trailing_stop_percent = float(os.getenv('TRAILING_STOP_PERCENT', '10.0'))

        # Partial profit taking settings (from environment) - used as fallback
        self.partial_profit_enabled = os.getenv('PARTIAL_PROFIT_ENABLED', 'true').lower() == 'true'
        self.profit_milestone_100 = float(os.getenv('PROFIT_MILESTONE_100', '15'))
        self.profit_milestone_200 = float(os.getenv('PROFIT_MILESTONE_200', '20'))
        self.profit_milestone_300 = float(os.getenv('PROFIT_MILESTONE_300', '15'))
        self.profit_milestone_400 = float(os.getenv('PROFIT_MILESTONE_400', '10'))
        self.profit_milestone_500 = float(os.getenv('PROFIT_MILESTONE_500', '10'))
        self.profit_milestone_600 = float(os.getenv('PROFIT_MILESTONE_600', '10'))
        self.profit_milestone_700 = float(os.getenv('PROFIT_MILESTONE_700', '10'))

        # Stuck position management settings (for /cleanup command)
        self.auto_cleanup_enabled = os.getenv('AUTO_CLEANUP_ENABLED', 'true').lower() == 'true'
        self.max_position_age_hours = float(os.getenv('MAX_POSITION_AGE_HOURS', '48'))
        self.stuck_liquidity_threshold = float(os.getenv('STUCK_LIQUIDITY_THRESHOLD', '1000'))
        self.stuck_time_hours = float(os.getenv('STUCK_TIME_HOURS', '6'))
        self.force_close_on_rug = os.getenv('FORCE_CLOSE_ON_RUG', 'true').lower() == 'true'
        self.min_exit_liquidity = float(os.getenv('MIN_EXIT_LIQUIDITY', '15000'))

        logger.info(
            f"✅ LiveTradingEngine initialized - "
            f"Wallet: {jupiter_executor.wallet.get_public_key()[:8]}..."
        )

        if self.partial_profit_enabled:
            logger.info(
                f"💰 Partial profit taking ENABLED: "
                f"+100%={self.profit_milestone_100:.0f}%, "
                f"+200%={self.profit_milestone_200:.0f}%, "
                f"+300%={self.profit_milestone_300:.0f}%, "
                f"+400%={self.profit_milestone_400:.0f}%, "
                f"+500%={self.profit_milestone_500:.0f}%, "
                f"+600%={self.profit_milestone_600:.0f}%, "
                f"+700%={self.profit_milestone_700:.0f}%"
            )
        else:
            logger.info("💰 Partial profit taking DISABLED")

        # Load saved state (positions, balances) from previous session
        self.load_state()

    async def get_wallet_balance(self) -> float:
        """
        Get current SOL balance from wallet by reading from blockchain.
        Uses direct HTTP RPC call to avoid httpx compatibility issues.

        Returns:
            SOL balance in SOL (not lamports)
        """
        try:
            if not self.jupiter_executor.wallet:
                logger.error("❌ No wallet loaded - cannot get balance")
                return 0.0

            # Get wallet public key
            pubkey_str = self.jupiter_executor.wallet.get_public_key()

            # Make direct RPC call using httpx
            async with httpx.AsyncClient(timeout=30.0) as client:
                payload = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "getBalance",
                    "params": [pubkey_str]
                }

                response = await client.post(self.rpc_url, json=payload)
                response.raise_for_status()

                data = response.json()

                if "error" in data:
                    logger.error(f"❌ RPC error getting balance: {data['error']}")
                    return 0.0

                if "result" not in data or "value" not in data["result"]:
                    logger.error(f"❌ Invalid RPC response format: {data}")
                    return 0.0

                # Convert lamports to SOL (1 SOL = 1e9 lamports)
                balance_lamports = data["result"]["value"]
                balance_sol = balance_lamports / 1e9

                logger.info(f"💰 Wallet balance: {balance_sol:.4f} SOL ({balance_lamports:,} lamports)")
                return balance_sol

        except Exception as e:
            logger.error(f"❌ Error getting wallet balance: {e}", exc_info=True)
            return 0.0

    async def init_wallet_balance(self, sol_price_usd: float = 240.0):
        """
        Initialize starting balance from actual wallet.
        Should be called ONCE after engine creation, before trading starts.

        Args:
            sol_price_usd: Current SOL price in USD (for conversion)
        """
        try:
            # Get actual wallet balance from blockchain
            balance_sol = await self.get_wallet_balance()

            if balance_sol <= 0:
                logger.error("❌ Wallet has zero or negative balance - cannot trade!")
                return

            # Convert to USD
            balance_usd = balance_sol * sol_price_usd

            # Set as starting balance ONLY if not already set
            if self.starting_balance == 0.0:
                self.starting_balance = balance_usd
                logger.info(
                    f"✅ Starting balance initialized from wallet: "
                    f"{balance_sol:.4f} SOL = ${balance_usd:.2f} USD (@ ${sol_price_usd}/SOL)"
                )
            else:
                # Already set (from state file or previous call)
                current_balance = balance_usd
                logger.info(
                    f"📊 Current wallet: {balance_sol:.4f} SOL = ${current_balance:.2f} USD"
                )
                logger.info(
                    f"📊 Starting balance (from state): ${self.starting_balance:.2f} USD"
                )

                # Warn if current balance is very different from starting balance
                # (user may have added/removed SOL)
                difference = abs(current_balance - self.starting_balance)
                if difference > self.starting_balance * 0.5:  # >50% difference
                    logger.warning(
                        f"⚠️  Large wallet balance difference detected!\n"
                        f"   Starting: ${self.starting_balance:.2f}\n"
                        f"   Current:  ${current_balance:.2f}\n"
                        f"   Diff:     ${difference:.2f}\n"
                        f"   → User may have added/removed SOL from wallet\n"
                        f"   → P&L calculations will be based on starting balance"
                    )

        except Exception as e:
            logger.error(f"❌ Error initializing wallet balance: {e}", exc_info=True)

    async def execute_buy(
        self,
        token_address: str,
        amount_usd: float,
        price: float,
        stop_loss: float,
        take_profit: float,
        analysis_data: Optional[Dict] = None,
        pair_created_at: Optional[int] = None
    ) -> Dict:
        """
        Execute a real buy order on-chain.

        Args:
            token_address: Token mint address to buy
            amount_usd: Amount in USD to spend
            price: Expected token price
            stop_loss: Stop loss price
            take_profit: Take profit price
            analysis_data: Optional analysis data for ML
            pair_created_at: Unix timestamp when pair was created (for age-based strategy)

        Returns:
            Execution result dictionary
        """
        try:
            # Check if we can open new position
            if not self.position_manager.can_open_position():
                logger.warning(f"❌ Cannot open position - max positions reached")
                return {
                    'status': 'failed',
                    'reason': 'max_positions_reached'
                }

            # Check if position already exists
            if token_address in self.position_manager.open_positions:
                logger.warning(f"❌ Position already exists for {token_address[:8]}...")
                return {
                    'status': 'failed',
                    'reason': 'position_exists'
                }

            # Convert USD amount to SOL (assuming SOL price ~ $200)
            # TODO: Get real SOL price from oracle
            sol_price_usd = 200.0  # Placeholder
            amount_sol = amount_usd / sol_price_usd

            logger.info(f"🟢 [LIVE] BUY: {token_address[:8]}... for {amount_sol:.4f} SOL (${amount_usd:.2f})")

            # Execute real swap via Jupiter
            swap_result = await self.jupiter_executor.buy_token(
                token_mint=token_address,
                amount_sol=amount_sol,
                slippage_percent=5.0
            )

            if not swap_result.get('success'):
                logger.error(f"❌ Swap failed: {swap_result.get('error', 'Unknown')}")
                return {
                    'status': 'failed',
                    'reason': swap_result.get('error', 'swap_failed')
                }

            # Extract actual output amount from swap
            actual_tokens_received = swap_result.get('output_amount', 0)
            actual_sol_spent = swap_result.get('input_amount', amount_sol)

            # Select strategy based on token age (if age-based strategies enabled)
            strategy = None
            if self.enable_age_strategies and self.strategy_selector and pair_created_at and pair_created_at > 0:
                strategy = self.strategy_selector.select_strategy(pair_created_at)
                # Apply strategy-specific position size multiplier
                adjusted_amount = actual_sol_spent * sol_price_usd * strategy.position_size_multiplier
                logger.info(
                    f"📊 Using strategy: {strategy.name} | "
                    f"Trailing: {strategy.trailing_stop_percent}% | "
                    f"Position multiplier: {strategy.position_size_multiplier}x"
                )
            elif pair_created_at:
                logger.info("📊 Using golden settings (age-based strategies disabled)")
                strategy = None
            else:
                # No age data
                if self.enable_age_strategies and self.strategy_selector:
                    strategy = self.strategy_selector.established
                    adjusted_amount = actual_sol_spent * sol_price_usd
                    logger.info("📊 Using default strategy: established (no age data)")
                else:
                    strategy = None
                    adjusted_amount = actual_sol_spent * sol_price_usd
                    logger.info("📊 Using golden settings (no age data)")

            # Open position in position manager
            position = self.position_manager.open_position(
                token_address=token_address,
                entry_price=price,
                amount_usd=adjusted_amount,  # Strategy-adjusted amount
                stop_loss=stop_loss,
                take_profit=take_profit,
                use_trailing_stop=self.use_trailing_stop,
                trailing_stop_percent=strategy.trailing_stop_percent,  # Strategy-specific
                strategy_name=strategy.name,
                pair_created_at=pair_created_at or 0
            )

            if not position:
                logger.error(f"❌ Failed to create position for {token_address[:8]}...")
                return {
                    'status': 'failed',
                    'reason': 'position_creation_failed'
                }

            # Update tracking
            self.total_invested += actual_sol_spent * sol_price_usd

            logger.info(
                f"✅ [LIVE] BUY CONFIRMED: {actual_tokens_received:.4f} tokens @ ${price:.8f}, "
                f"Signature: {swap_result.get('signature', 'N/A')[:16]}..."
            )

            # Save state after successful buy
            self.save_state()

            return {
                'status': 'success',
                'action': 'buy',
                'token_address': token_address,
                'amount_usd': actual_sol_spent * sol_price_usd,
                'quantity': actual_tokens_received,
                'price': price,
                'signature': swap_result.get('signature'),
                'fees': swap_result.get('fees', {}),
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"❌ Error executing live buy: {e}", exc_info=True)
            return {
                'status': 'failed',
                'reason': str(e)
            }

    async def execute_sell(
        self,
        token_address: str,
        price: float,
        reason: str = 'manual',
        amount_tokens: Optional[float] = None
    ) -> Dict:
        """
        Execute a real sell order on-chain.

        Args:
            token_address: Token to sell
            price: Current token price
            reason: Reason for selling
            amount_tokens: Optional - amount of tokens to sell (if None, sells full position)

        Returns:
            Execution result dictionary
        """
        try:
            # Check if position exists
            position = self.position_manager.get_position(token_address)
            if not position:
                logger.warning(f"❌ No position to sell for {token_address[:8]}...")
                return {
                    'status': 'failed',
                    'reason': 'no_position'
                }

            # Determine sell amount
            if amount_tokens is None:
                # Full sell
                sell_quantity = position.quantity
                is_partial = False
            else:
                # Partial sell
                sell_quantity = min(amount_tokens, position.quantity)
                is_partial = (sell_quantity < position.quantity)

            logger.info(
                f"🔴 [LIVE] {'PARTIAL ' if is_partial else ''}SELL: "
                f"{sell_quantity:.4f} {token_address[:8]}... @ ${price:.8f} ({reason})"
            )

            # Execute real swap via Jupiter
            swap_result = await self.jupiter_executor.sell_token(
                token_mint=token_address,
                amount_tokens=sell_quantity,
                slippage_percent=5.0
            )

            if not swap_result.get('success'):
                logger.error(f"❌ Sell swap failed: {swap_result.get('error', 'Unknown')}")

                # Track failed sell attempts for stuck position detection
                position.failed_sell_attempts += 1

                # Force close after 20 failed attempts (~7 minutes of trying every 20 seconds)
                if position.failed_sell_attempts >= 20:
                    logger.error(
                        f"🚫 [LIVE] STUCK POSITION - Failed to sell {position.failed_sell_attempts} times!\n"
                        f"   Token: {token_address[:8]}...\n"
                        f"   Entry: ${position.entry_price:.8f}, Value: ${position.amount_usd:.2f}\n"
                        f"   Liquidity: ${position.current_liquidity:.0f}\n"
                        f"   ⚠️  FORCE CLOSING to free position slot (writing off loss)"
                    )

                    # Force close the position
                    trade = self.position_manager.force_close_position(
                        token_address,
                        reason='stuck_no_route'
                    )

                    if trade:
                        # Update tracking
                        self.total_invested -= position.amount_usd

                        # Save state after force close
                        self.save_state()

                        logger.warning(
                            f"✅ [LIVE] STUCK POSITION CLOSED: {token_address[:8]}... "
                            f"Written off ${position.amount_usd:.2f} to free slot"
                        )

                        return {
                            'status': 'force_closed',
                            'reason': 'stuck_no_route',
                            'token_address': token_address,
                            'loss': position.amount_usd
                        }

                return {
                    'status': 'failed',
                    'reason': swap_result.get('error', 'swap_failed'),
                    'failed_attempts': position.failed_sell_attempts
                }

            # Reset failed sell attempts on successful sell
            position.failed_sell_attempts = 0

            # Calculate profit on this sell
            cost_basis = position.entry_price * sell_quantity
            sell_value = price * sell_quantity
            pnl = sell_value - cost_basis
            pnl_percent = ((price - position.entry_price) / position.entry_price) * 100 if position.entry_price > 0 else 0

            if is_partial:
                # Partial sell - update position
                position.quantity -= sell_quantity
                position.amount_usd = position.quantity * position.entry_price
                self.total_invested -= cost_basis

                logger.info(
                    f"✅ [LIVE] PARTIAL SELL CONFIRMED: {sell_quantity:.4f} tokens → {swap_result.get('output_amount', 0):.6f} SOL, "
                    f"P&L: ${pnl:.2f} ({pnl_percent:+.1f}%), "
                    f"Remaining: {position.quantity:.4f} tokens, "
                    f"Signature: {swap_result.get('signature', 'N/A')[:16]}..."
                )

                # Save state after partial sell
                self.save_state()

                return {
                    'status': 'success',
                    'action': 'partial_sell',
                    'token_address': token_address,
                    'price': price,
                    'quantity': sell_quantity,
                    'pnl': pnl,
                    'pnl_percent': pnl_percent,
                    'signature': swap_result.get('signature'),
                    'fees': swap_result.get('fees', {}),
                    'reason': reason,
                    'remaining_quantity': position.quantity,
                    'timestamp': datetime.now().isoformat()
                }
            else:
                # Full sell - close position
                trade = self.position_manager.close_position(
                    token_address=token_address,
                    exit_price=price,
                    reason=reason
                )

                if not trade:
                    logger.error(f"❌ Failed to close position for {token_address[:8]}...")
                    return {
                        'status': 'failed',
                        'reason': 'position_close_failed'
                    }

                # Update tracking
                self.total_invested -= position.amount_usd

            logger.info(
                f"✅ [LIVE] SELL CONFIRMED: {position.quantity:.4f} tokens → {swap_result.get('output_amount', 0):.6f} SOL, "
                f"P&L: ${trade.pnl:.2f} ({trade.pnl_percent:+.1f}%), "
                f"Signature: {swap_result.get('signature', 'N/A')[:16]}..."
            )

            # Save state after full sell
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
                'signature': swap_result.get('signature'),
                'fees': swap_result.get('fees', {}),
                'reason': reason,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"❌ Error executing live sell: {e}", exc_info=True)
            return {
                'status': 'failed',
                'reason': str(e)
            }

    async def update_prices(self, price_updates: Dict[str, float], liquidity_data: Dict[str, float] = None):
        """
        Update position prices and check stop loss/take profit.

        Args:
            price_updates: Dictionary of token_address -> current_price
            liquidity_data: Optional liquidity data
        """
        if liquidity_data is None:
            liquidity_data = {}

        # Update all prices
        for token_address, current_price in price_updates.items():
            if token_address not in self.position_manager.open_positions:
                continue

            liquidity = liquidity_data.get(token_address, 0.0)
            self.position_manager.update_position_price(token_address, current_price, liquidity)

        # TIERED EXIT SYSTEM: Check liquidity degradation vs entry thresholds
        # Entry requirement: MIN_ENTRY_LIQUIDITY = $40k
        # This catches deteriorating tokens BEFORE they become completely dead
        MIN_ENTRY_LIQUIDITY = 40000.0  # Match the entry filter
        WARNING_THRESHOLD = MIN_ENTRY_LIQUIDITY * 0.7  # 30% drop = $28k
        DANGER_THRESHOLD = MIN_ENTRY_LIQUIDITY * 0.5   # 50% drop = $20k
        CRITICAL_THRESHOLD = 1000.0  # Absolute minimum to attempt sell
        MIN_VOLUME_TO_SELL = 5000.0  # Need at least $5k volume to try selling

        for token_address in list(self.position_manager.open_positions.keys()):
            position = self.position_manager.get_position(token_address)
            if not position:
                continue

            current_liq = position.current_liquidity

            # DANGER ZONE: 50% drop from entry minimum
            if current_liq < DANGER_THRESHOLD and current_liq >= CRITICAL_THRESHOLD:
                logger.warning(
                    f"⚠️  DANGER: {token_address[:8]}... liquidity at ${current_liq:,.0f} "
                    f"(below ${DANGER_THRESHOLD:,.0f} = 50% of entry min)"
                )
                # Try to sell if there's enough volume
                # Volume check would go here if we had volume data
                # For now, try to sell cautiously
                exit_price = position.current_price if position.current_price > 0 else 0.00000001
                await self.execute_sell(token_address, exit_price, reason='degraded_liquidity')
                continue

            # WARNING ZONE: 30% drop from entry minimum
            elif current_liq < WARNING_THRESHOLD:
                logger.warning(
                    f"⚠️  WARNING: {token_address[:8]}... liquidity degrading "
                    f"(${current_liq:,.0f} < ${WARNING_THRESHOLD:,.0f}, 70% of entry min) - monitoring closely"
                )

        # Check for dead/rugged positions (low liquidity, frozen price, stale data)
        dead_positions = self.position_manager.get_dead_positions(
            stale_minutes=10,
            min_liquidity=8000.0,  # $8k minimum liquidity to sell
            freeze_minutes=5
        )

        for token_address in dead_positions:
            position = self.position_manager.get_position(token_address)
            if position:
                logger.error(
                    f"💀 [LIVE] DEAD TOKEN DETECTED: {token_address[:8]}... "
                    f"Entry: ${position.entry_price:.8f}, "
                    f"Current: ${position.current_price:.8f}, "
                    f"Liquidity: ${position.current_liquidity:.0f}"
                )

                # CRITICAL: Don't try to sell tokens with very low/zero liquidity!
                # Attempting to sell can result in catastrophic fees (>$900)
                # Better to write off the position than pay more in fees than it's worth
                if position.current_liquidity < self.min_exit_liquidity:
                    logger.error(
                        f"🚫 [LIVE] INSUFFICIENT LIQUIDITY to sell safely!\n"
                        f"   Position Value: ${position.amount_usd:.2f}\n"
                        f"   Liquidity: ${position.current_liquidity:.0f} < ${self.min_exit_liquidity:.0f}\n"
                        f"   ⚠️  FORCE CLOSING (write-off) to avoid catastrophic fees"
                    )

                    # Force close WITHOUT attempting to sell
                    trade = self.position_manager.force_close_position(
                        token_address,
                        reason='insufficient_liquidity'
                    )

                    if trade:
                        # Update tracking
                        self.total_invested -= position.amount_usd

                        # Save state after force close
                        self.save_state()

                        logger.warning(
                            f"✅ [LIVE] DEAD POSITION CLOSED: {token_address[:8]}... "
                            f"Written off ${position.amount_usd:.2f} to avoid fee disaster"
                        )
                else:
                    # Liquidity is low but above minimum - attempt cautious sell
                    exit_price = position.current_price if position.current_price > 0 else 0.00000001
                    await self.execute_sell(token_address, exit_price, reason='low_liquidity')

        # Check for profit milestones (partial profit-taking)
        if self.partial_profit_enabled:
            for token_address in list(self.position_manager.open_positions.keys()):
                position = self.position_manager.get_position(token_address)
                if not position or position.initial_quantity == 0:
                    continue

                # Get strategy profile for this position
                strategy = self.strategy_selector.get_strategy_by_name(position.strategy_name)

                # Check if we've hit a new profit milestone (using strategy-specific milestones)
                milestone = position.check_profit_milestone(strategy)
                if milestone:
                    # Get sell percentage from strategy
                    sell_pct = strategy.get_milestone_percentage(milestone)

                    if sell_pct > 0:
                        # Calculate quantity to sell (percentage of INITIAL quantity)
                        sell_quantity = (sell_pct / 100) * position.initial_quantity
                        sell_quantity = min(sell_quantity, position.quantity)  # Don't sell more than we have

                        if sell_quantity > 0:
                            sell_value = sell_quantity * position.current_price

                            logger.info(
                                f"💰 [LIVE] PROFIT MILESTONE +{milestone}% ({strategy.name}): {token_address[:8]}... "
                                f"Selling {sell_pct:.0f}% ({sell_quantity:.4f} tokens) = ${sell_value:.2f}"
                            )

                            # Execute partial sell
                            await self.execute_sell(
                                token_address=token_address,
                                price=position.current_price,
                                reason=f'milestone_{milestone}',
                                amount_tokens=sell_quantity
                            )

                            # Mark milestone as hit
                            position.milestones_hit.add(milestone)

        # Check for stop loss/take profit/trailing stop triggers
        for token_address in list(self.position_manager.open_positions.keys()):
            position = self.position_manager.get_position(token_address)
            if not position:
                continue

            current_price = position.current_price

            # Check stop loss
            if self.position_manager.check_stop_loss(token_address):
                logger.info(f"⛔ [LIVE] Stop loss triggered for {token_address[:8]}...")
                await self.execute_sell(token_address, current_price, reason='stop_loss')

            # Check trailing stop
            elif self.position_manager.check_trailing_stop(token_address):
                logger.info(f"📉 [LIVE] Trailing stop triggered for {token_address[:8]}...")
                await self.execute_sell(token_address, current_price, reason='trailing_stop')

            # Check take profit
            elif self.position_manager.check_take_profit(token_address):
                logger.info(f"🎯 [LIVE] Take profit triggered for {token_address[:8]}...")
                await self.execute_sell(token_address, current_price, reason='take_profit')

    def get_portfolio_value(self) -> float:
        """
        Get total portfolio value based on starting balance and P&L.

        Returns:
            Total portfolio value in USD
        """
        # Calculate from starting balance + realized/unrealized P&L
        stats = self.position_manager.get_statistics()
        total_pnl = stats['total_realized_pnl'] + stats['total_unrealized_pnl']

        # Portfolio value = starting capital + all profits/losses
        portfolio_value = self.starting_balance + total_pnl

        return max(portfolio_value, 0.0)  # Never negative

    def get_performance_summary(self) -> Dict:
        """
        Get performance summary for live trading.

        Returns:
            Performance metrics dictionary (compatible with paper trading format)
        """
        stats = self.position_manager.get_statistics()
        portfolio_value = self.get_portfolio_value()

        # Calculate P&L from realized + unrealized
        total_pnl = stats['total_realized_pnl'] + stats['total_unrealized_pnl']

        # Calculate current capital (free cash not invested)
        current_capital = portfolio_value - self.total_invested

        # Calculate total return percent
        initial_capital = self.starting_balance if self.starting_balance > 0 else portfolio_value
        total_return_percent = (total_pnl / initial_capital * 100) if initial_capital > 0 else 0

        return {
            'initial_capital': initial_capital,
            'current_capital': current_capital,
            'invested_capital': self.total_invested,
            'portfolio_value': portfolio_value,
            'total_pnl': total_pnl,
            'total_return_percent': total_return_percent,
            'realized_pnl': stats['total_realized_pnl'],
            'unrealized_pnl': stats['total_unrealized_pnl'],
            'open_positions': stats['open_positions'],
            'total_trades': stats['total_trades'],
            'winning_trades': stats['winning_trades'],
            'losing_trades': stats['losing_trades'],
            'win_rate': stats['win_rate'],
            'avg_win': stats.get('avg_win', 0),
            'avg_loss': stats.get('avg_loss', 0),
            'timestamp': datetime.now().isoformat()
        }

    def save_state(self):
        """Save current state to file for persistence."""
        try:
            abs_path = os.path.abspath(self.state_file)
            logger.info(f"💾 [LIVE] Saving state to {abs_path}...")

            state = {
                'starting_balance': self.starting_balance,
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
                    'last_price_change': pos.last_price_change.isoformat(),
                    'last_known_price': pos.last_known_price,
                    'current_liquidity': pos.current_liquidity,
                    'price_update_failures': pos.price_update_failures,
                    'initial_quantity': pos.initial_quantity,
                    'milestones_hit': list(pos.milestones_hit),
                    'failed_sell_attempts': pos.failed_sell_attempts
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
                f"✅ [LIVE] State saved successfully: ${self.total_invested:.2f} invested, "
                f"{len(self.position_manager.open_positions)} position(s), "
                f"{len(state['trades'])} trade(s)"
            )
            if len(self.position_manager.open_positions) > 0:
                logger.info(f"📊 [LIVE] Saved positions: {list(self.position_manager.open_positions.keys())}")

        except Exception as e:
            logger.error(f"❌ [LIVE] Error saving state to {abs_path}: {e}", exc_info=True)

    def load_state(self):
        """
        Load state from file.

        IMPORTANT: This runs during __init__ (before async context), so we can't
        call async get_wallet_balance() here. Starting balance will be set to 0
        and should be updated by calling init_wallet_balance() after engine is created.
        """
        try:
            # Log absolute path for debugging
            abs_path = os.path.abspath(self.state_file)
            logger.info(f"🔍 [LIVE] Checking for state file at: {abs_path}")

            if not os.path.exists(self.state_file):
                logger.warning(f"📝 No previous live trading state found at {abs_path}")
                logger.warning("🆕 Starting fresh - no positions to restore")
                logger.warning("⚠️  Call init_wallet_balance() after engine creation to set starting balance")
                return

            logger.info(f"📂 [LIVE] Loading live trading state from {abs_path}...")

            with open(self.state_file, 'r') as f:
                state = json.load(f)

            # Restore invested amount (safe to trust this)
            self.total_invested = state.get('total_invested', 0.0)

            # Restore starting_balance from state file
            # This is CRITICAL for accurate P&L tracking across restarts
            # Without this, we'd double-count realized profits from previous sessions
            saved_starting_balance = state.get('starting_balance', 0.0)
            if saved_starting_balance > 0:
                self.starting_balance = saved_starting_balance
                logger.info(f"💰 [LIVE] Restored starting balance: ${self.starting_balance:.2f}")
            else:
                logger.warning(f"⚠️  No starting balance in state file - will be set from actual wallet")

            logger.info(f"💰 [LIVE] Restored: starting=${self.starting_balance:.2f}, invested=${self.total_invested:.2f}")

            # Restore positions
            loaded_positions = 0
            for token_addr, pos_data in state.get('positions', {}).items():
                position = Position(
                    token_address=pos_data['token_address'],
                    entry_price=pos_data['entry_price'],
                    current_price=pos_data['current_price'],
                    amount_usd=pos_data['amount_usd'],
                    quantity=pos_data['quantity'],
                    stop_loss=pos_data['stop_loss'],
                    take_profit=pos_data['take_profit'],
                    entry_time=datetime.fromisoformat(pos_data['entry_time'])
                )

                # Restore trailing stop data
                position.use_trailing_stop = pos_data.get('use_trailing_stop', False)
                position.trailing_stop_percent = pos_data.get('trailing_stop_percent', 0.0)
                position.highest_price = pos_data.get('highest_price', pos_data['entry_price'])
                position.trailing_stop_price = pos_data.get('trailing_stop_price', 0.0)

                # Restore price tracking data
                position.last_price_update = datetime.fromisoformat(pos_data['last_price_update'])
                position.last_price_change = datetime.fromisoformat(pos_data['last_price_change'])
                position.last_known_price = pos_data.get('last_known_price', pos_data['current_price'])
                position.current_liquidity = pos_data.get('current_liquidity', 0.0)
                position.price_update_failures = pos_data.get('price_update_failures', 0)

                # Restore partial profit data
                position.initial_quantity = pos_data.get('initial_quantity', pos_data['quantity'])
                position.milestones_hit = set(pos_data.get('milestones_hit', []))

                # Restore stuck position tracking
                position.failed_sell_attempts = pos_data.get('failed_sell_attempts', 0)

                self.position_manager.open_positions[token_addr] = position
                loaded_positions += 1

            # Restore trades
            loaded_trades = 0
            for trade_data in state.get('trades', []):
                trade = Trade(
                    token_address=trade_data['token_address'],
                    action=trade_data['action'],
                    price=trade_data['price'],
                    amount_usd=trade_data['amount_usd'],
                    quantity=trade_data['quantity'],
                    pnl=trade_data.get('pnl', 0.0),
                    pnl_percent=trade_data.get('pnl_percent', 0.0),
                    timestamp=datetime.fromisoformat(trade_data['timestamp'])
                )
                self.position_manager.closed_trades.append(trade)
                loaded_trades += 1

            if loaded_positions > 0:
                logger.info(
                    f"✅ [LIVE] State loaded successfully: ${self.total_invested:.2f} invested, "
                    f"{loaded_positions} position(s), {loaded_trades} trade(s)"
                )
                logger.info(f"📊 [LIVE] Restored positions: {list(self.position_manager.open_positions.keys())}")
            else:
                logger.warning("⚠️  [LIVE] State file loaded but NO positions found")

        except Exception as e:
            logger.error(f"❌ Error loading state from {self.state_file}: {e}", exc_info=True)
            logger.error("Starting with fresh state due to error")
