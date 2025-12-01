"""
Live Trading Engine for real Solana swaps via Jupiter.
Manages real wallet, executes actual trades, tracks on-chain positions.
"""

import asyncio
import os
import json
from typing import Dict, Optional
from datetime import datetime
from .position_manager import PositionManager, Position, Trade
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

        # Trading state (tracked separately from wallet balance)
        self.starting_balance = 0.0  # Will be set on first balance check
        self.total_invested = 0.0  # Currently invested in open positions

        # Partial profit taking settings (from environment)
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
        Get current SOL balance from wallet.

        Returns:
            SOL balance
        """
        # TODO: Implement RPC call to get wallet balance
        # For now, return placeholder
        logger.warning("⚠️  Wallet balance check not yet implemented - using placeholder")
        return 1.0  # Placeholder

    async def execute_buy(
        self,
        token_address: str,
        amount_usd: float,
        price: float,
        stop_loss: float,
        take_profit: float,
        analysis_data: Optional[Dict] = None
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

            # Open position in position manager
            position = self.position_manager.open_position(
                token_address=token_address,
                entry_price=price,
                amount_usd=actual_sol_spent * sol_price_usd,  # Actual USD spent
                stop_loss=stop_loss,
                take_profit=take_profit,
                use_trailing_stop=True,
                trailing_stop_percent=10.0
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

                # Check if we've hit a new profit milestone
                milestone = position.check_profit_milestone()
                if milestone:
                    # Map milestone to sell percentage
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
                        # Calculate quantity to sell (percentage of INITIAL quantity)
                        sell_quantity = (sell_pct / 100) * position.initial_quantity
                        sell_quantity = min(sell_quantity, position.quantity)  # Don't sell more than we have

                        if sell_quantity > 0:
                            sell_value = sell_quantity * position.current_price

                            logger.info(
                                f"💰 [LIVE] PROFIT MILESTONE +{milestone}%: {token_address[:8]}... "
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
        """Load state from file."""
        try:
            # Log absolute path for debugging
            abs_path = os.path.abspath(self.state_file)
            logger.info(f"🔍 [LIVE] Checking for state file at: {abs_path}")

            if not os.path.exists(self.state_file):
                logger.warning(f"📝 No previous live trading state found at {abs_path}")
                logger.warning("🆕 Starting fresh - no positions to restore")
                return

            logger.info(f"📂 [LIVE] Loading live trading state from {abs_path}...")

            with open(self.state_file, 'r') as f:
                state = json.load(f)

            # Restore balances
            self.starting_balance = state.get('starting_balance', 0.0)
            self.total_invested = state.get('total_invested', 0.0)

            logger.info(f"💰 [LIVE] Restoring balances: starting=${self.starting_balance:.2f}, invested=${self.total_invested:.2f}")

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
