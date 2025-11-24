"""
Paper trading engine for testing strategies without real funds.
"""

from typing import Dict, Optional
from datetime import datetime
import json
import os
from .position_manager import PositionManager, Trade, Position
from ..monitoring.logger import get_logger

logger = get_logger(__name__)


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
        self.stale_price_minutes = float(os.getenv('STALE_PRICE_MINUTES', '5'))
        self.min_position_liquidity = float(os.getenv('MIN_POSITION_LIQUIDITY', '5000.0'))

        # Read trailing stop settings from environment
        self.use_trailing_stop = os.getenv('USE_TRAILING_STOP', 'true').lower() == 'true'
        self.trailing_stop_percent = float(os.getenv('TRAILING_STOP_PERCENT', '15.0'))

        # Read partial profit taking settings from environment
        self.partial_profit_enabled = os.getenv('PARTIAL_PROFIT_ENABLED', 'false').lower() == 'true'
        self.profit_milestone_100 = float(os.getenv('PROFIT_MILESTONE_100', '25'))
        self.profit_milestone_200 = float(os.getenv('PROFIT_MILESTONE_200', '15'))
        self.profit_milestone_300 = float(os.getenv('PROFIT_MILESTONE_300', '10'))
        self.profit_milestone_500 = float(os.getenv('PROFIT_MILESTONE_500', '10'))

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

    async def execute_buy(
        self,
        token_address: str,
        amount_usd: float,
        price: float,
        stop_loss: float,
        take_profit: float,
        use_trailing_stop: Optional[bool] = None,
        trailing_stop_percent: Optional[float] = None
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

        Returns:
            Execution result dictionary
        """
        # Use .env settings if not explicitly provided
        if use_trailing_stop is None:
            use_trailing_stop = self.use_trailing_stop
        if trailing_stop_percent is None:
            trailing_stop_percent = self.trailing_stop_percent
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

        # Check if we can open more positions
        if not self.position_manager.can_open_position():
            logger.warning("Max positions reached")
            return {
                'status': 'failed',
                'reason': 'max_positions_reached'
            }

        # Open position
        position = self.position_manager.open_position(
            token_address=token_address,
            entry_price=price,
            amount_usd=amount_usd,
            stop_loss=stop_loss,
            take_profit=take_profit,
            use_trailing_stop=use_trailing_stop,
            trailing_stop_percent=trailing_stop_percent
        )

        if not position:
            return {
                'status': 'failed',
                'reason': 'position_creation_failed'
            }

        # Deduct from capital
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
        reason: str = 'manual'
    ) -> Dict:
        """
        Execute a simulated sell order.

        Args:
            token_address: Token contract address
            price: Current token price
            reason: Reason for selling

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

        # Close position
        trade = self.position_manager.close_position(
            token_address=token_address,
            exit_price=price,
            reason=reason
        )

        if not trade:
            return {
                'status': 'failed',
                'reason': 'close_failed'
            }

        # Add proceeds to capital
        proceeds = trade.amount_usd
        capital_before = self.current_capital
        self.current_capital += proceeds
        self.total_invested -= position.amount_usd

        logger.info(
            f"[PAPER] SELL {token_address[:8]}... "
            f"@ ${price:.8f}, proceeds: ${proceeds:.2f}, "
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
                min_liquidity=self.min_position_liquidity
            )
        else:
            dead_positions = []

        for token_address in dead_positions:
            position = self.position_manager.get_position(token_address)
            if position:
                # Close at effectively $0 (rugged/dead token has no value)
                logger.error(
                    f"💀 AUTO-CLOSING DEAD TOKEN: {token_address[:8]}... "
                    f"Entry: ${position.entry_price:.8f}, "
                    f"Last known: ${position.current_price:.8f}, "
                    f"Loss: ${position.amount_usd:.2f}"
                )
                await self.execute_sell(token_address, 0.00000001, reason='rugged/dead')

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
                    elif milestone == 500:
                        sell_pct = self.profit_milestone_500

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

                            # Reduce position quantity
                            position.quantity -= sell_quantity
                            position.milestones_hit.add(milestone)

                            # Add proceeds to capital
                            self.current_capital += sell_value

                            # Calculate profit on this partial sell
                            cost_basis = (position.entry_price * sell_quantity)
                            partial_profit = sell_value - cost_basis

                            logger.info(
                                f"💵 Locked in ${partial_profit:.2f} profit, "
                                f"Remaining: {position.quantity:.2f} tokens (continues with trailing stop)"
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
                    current_liquidity=pos_data.get('current_liquidity', 0.0),
                    price_update_failures=pos_data.get('price_update_failures', 0),
                    initial_quantity=pos_data.get('initial_quantity', pos_data['quantity']),  # Partial profit tracking
                    milestones_hit=set(pos_data.get('milestones_hit', []))  # Convert list back to set
                )
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
