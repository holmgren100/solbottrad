"""
Paper trading engine for testing strategies without real funds.
"""

from typing import Dict, Optional
from datetime import datetime
from .position_manager import PositionManager, Trade
from ..monitoring.logger import get_logger

logger = get_logger(__name__)


class PaperTradingEngine:
    """Simulated trading engine for testing."""

    def __init__(self, initial_capital: float = 1000.0):
        """
        Initialize paper trading engine.

        Args:
            initial_capital: Starting capital in USD
        """
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.position_manager = PositionManager(max_open_positions=5)
        self.total_invested = 0.0

        logger.info(f"Paper trading engine initialized with ${initial_capital:.2f}")

    async def execute_buy(
        self,
        token_address: str,
        amount_usd: float,
        price: float,
        stop_loss: float,
        take_profit: float
    ) -> Dict:
        """
        Execute a simulated buy order.

        Args:
            token_address: Token contract address
            amount_usd: Amount to invest in USD
            price: Current token price
            stop_loss: Stop loss price
            take_profit: Take profit price

        Returns:
            Execution result dictionary
        """
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
            take_profit=take_profit
        )

        if not position:
            return {
                'status': 'failed',
                'reason': 'position_creation_failed'
            }

        # Deduct from capital
        self.current_capital -= amount_usd
        self.total_invested += amount_usd

        logger.info(
            f"[PAPER] BUY {token_address[:8]}... "
            f"@ ${price:.8f}, size: ${amount_usd:.2f}, "
            f"capital: ${self.current_capital:.2f}"
        )

        return {
            'status': 'success',
            'action': 'buy',
            'token_address': token_address,
            'price': price,
            'amount_usd': amount_usd,
            'quantity': position.quantity,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
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

    async def update_prices(self, price_updates: Dict[str, float]):
        """
        Update positions with current prices and check stop loss/take profit.

        Args:
            price_updates: Dictionary of token_address -> current_price
        """
        for token_address, current_price in price_updates.items():
            if token_address not in self.position_manager.open_positions:
                continue

            # Update position price
            self.position_manager.update_position_price(token_address, current_price)

            # Check stop loss
            if self.position_manager.check_stop_loss(token_address):
                logger.info(f"Stop loss triggered for {token_address[:8]}...")
                await self.execute_sell(token_address, current_price, reason='stop_loss')

            # Check take profit
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
        self.position_manager = PositionManager(max_open_positions=5)
        logger.info("Paper trading engine reset")

    async def health_check(self) -> bool:
        """
        Health check for paper trading engine.

        Returns:
            True if healthy
        """
        return True  # Paper trading is always healthy
