"""
Position management and portfolio tracking.
"""

from typing import Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass, field
from ..monitoring.logger import get_logger

logger = get_logger(__name__)


@dataclass
class Position:
    """Represents a trading position."""
    token_address: str
    entry_price: float
    current_price: float
    amount_usd: float
    quantity: float
    entry_time: datetime
    stop_loss: float
    take_profit: float
    unrealized_pnl: float = 0.0
    unrealized_pnl_percent: float = 0.0
    # Trailing stop loss fields
    use_trailing_stop: bool = True
    trailing_stop_percent: float = 15.0  # Trail by 15% from peak
    highest_price: float = 0.0  # Track highest price reached
    trailing_stop_price: float = 0.0  # Dynamic trailing stop price

    def update_price(self, new_price: float):
        """Update current price and PnL."""
        self.current_price = new_price
        self.unrealized_pnl = (new_price - self.entry_price) * self.quantity
        if self.entry_price > 0:
            self.unrealized_pnl_percent = ((new_price - self.entry_price) / self.entry_price) * 100

        # Update trailing stop if enabled
        if self.use_trailing_stop:
            # Update highest price if current price is higher
            if new_price > self.highest_price:
                self.highest_price = new_price
                # Calculate new trailing stop (X% below highest price)
                self.trailing_stop_price = self.highest_price * (1 - self.trailing_stop_percent / 100)
                logger.debug(
                    f"Trailing stop updated for {self.token_address[:8]}...: "
                    f"Peak ${self.highest_price:.8f} → Stop ${self.trailing_stop_price:.8f}"
                )


@dataclass
class Trade:
    """Represents a completed trade."""
    token_address: str
    action: str  # 'buy' or 'sell'
    price: float
    amount_usd: float
    quantity: float
    timestamp: datetime
    pnl: float = 0.0
    pnl_percent: float = 0.0


class PositionManager:
    """Manages trading positions and portfolio."""

    def __init__(self, max_open_positions: int = 5):
        """
        Initialize position manager.

        Args:
            max_open_positions: Maximum number of simultaneous positions
        """
        self.max_open_positions = max_open_positions
        self.open_positions: Dict[str, Position] = {}
        self.closed_trades: List[Trade] = []
        self.daily_trades: List[Trade] = []
        self.portfolio_value: float = 0.0

    def can_open_position(self) -> bool:
        """
        Check if a new position can be opened.

        Returns:
            True if can open new position
        """
        return len(self.open_positions) < self.max_open_positions

    def open_position(
        self,
        token_address: str,
        entry_price: float,
        amount_usd: float,
        stop_loss: float,
        take_profit: float,
        use_trailing_stop: bool = True,
        trailing_stop_percent: float = 15.0
    ) -> Optional[Position]:
        """
        Open a new position.

        Args:
            token_address: Token contract address
            entry_price: Entry price
            amount_usd: Position size in USD
            stop_loss: Stop loss price
            take_profit: Take profit price (ignored if using trailing stop)
            use_trailing_stop: Whether to use trailing stop instead of fixed take profit
            trailing_stop_percent: Percent to trail below peak (default 15%)

        Returns:
            Position object if successful, None otherwise
        """
        if not self.can_open_position():
            logger.warning(f"Cannot open position - max positions reached ({self.max_open_positions})")
            return None

        if token_address in self.open_positions:
            logger.warning(f"Position already exists for {token_address}")
            return None

        quantity = amount_usd / entry_price if entry_price > 0 else 0

        position = Position(
            token_address=token_address,
            entry_price=entry_price,
            current_price=entry_price,
            amount_usd=amount_usd,
            quantity=quantity,
            entry_time=datetime.now(),
            stop_loss=stop_loss,
            take_profit=take_profit,
            use_trailing_stop=use_trailing_stop,
            trailing_stop_percent=trailing_stop_percent,
            highest_price=entry_price,  # Initialize with entry price
            trailing_stop_price=stop_loss  # Start with regular stop loss
        )

        self.open_positions[token_address] = position

        # Record buy trade
        buy_trade = Trade(
            token_address=token_address,
            action='buy',
            price=entry_price,
            amount_usd=amount_usd,
            quantity=quantity,
            timestamp=datetime.now()
        )
        self.daily_trades.append(buy_trade)

        mode = "trailing stop" if use_trailing_stop else "fixed TP"
        logger.info(
            f"Opened position: {token_address[:8]}... "
            f"@ ${entry_price:.8f}, size: ${amount_usd:.2f}, mode: {mode}"
        )

        return position

    def close_position(
        self,
        token_address: str,
        exit_price: float,
        reason: str = 'manual'
    ) -> Optional[Trade]:
        """
        Close a position.

        Args:
            token_address: Token contract address
            exit_price: Exit price
            reason: Reason for closing

        Returns:
            Trade object if successful, None otherwise
        """
        if token_address not in self.open_positions:
            logger.warning(f"No open position for {token_address}")
            return None

        position = self.open_positions[token_address]
        position.update_price(exit_price)

        # Calculate PnL
        pnl = position.unrealized_pnl
        pnl_percent = position.unrealized_pnl_percent

        # Create sell trade
        sell_trade = Trade(
            token_address=token_address,
            action='sell',
            price=exit_price,
            amount_usd=position.quantity * exit_price,
            quantity=position.quantity,
            timestamp=datetime.now(),
            pnl=pnl,
            pnl_percent=pnl_percent
        )

        self.closed_trades.append(sell_trade)
        self.daily_trades.append(sell_trade)

        # Remove from open positions
        del self.open_positions[token_address]

        logger.info(
            f"Closed position: {token_address[:8]}... "
            f"@ ${exit_price:.8f}, "
            f"PnL: ${pnl:.2f} ({pnl_percent:+.1f}%), "
            f"Reason: {reason}"
        )

        return sell_trade

    def update_position_price(self, token_address: str, current_price: float):
        """
        Update position with current price.

        Args:
            token_address: Token contract address
            current_price: Current market price
        """
        if token_address in self.open_positions:
            self.open_positions[token_address].update_price(current_price)

    def check_stop_loss(self, token_address: str) -> bool:
        """
        Check if stop loss is hit.

        Args:
            token_address: Token contract address

        Returns:
            True if stop loss triggered
        """
        if token_address not in self.open_positions:
            return False

        position = self.open_positions[token_address]
        return position.current_price <= position.stop_loss

    def check_take_profit(self, token_address: str) -> bool:
        """
        Check if take profit is hit.

        Args:
            token_address: Token contract address

        Returns:
            True if take profit triggered
        """
        if token_address not in self.open_positions:
            return False

        position = self.open_positions[token_address]

        # If using trailing stop, don't check fixed take profit
        if position.use_trailing_stop:
            return False

        return position.current_price >= position.take_profit

    def check_trailing_stop(self, token_address: str) -> bool:
        """
        Check if trailing stop is hit.

        Args:
            token_address: Token contract address

        Returns:
            True if trailing stop triggered
        """
        if token_address not in self.open_positions:
            return False

        position = self.open_positions[token_address]

        # Only check if trailing stop is enabled
        if not position.use_trailing_stop:
            return False

        # Trigger if current price drops below trailing stop price
        if position.current_price <= position.trailing_stop_price:
            gain_pct = ((position.highest_price - position.entry_price) / position.entry_price) * 100
            logger.info(
                f"Trailing stop triggered for {token_address[:8]}...: "
                f"Peak ${position.highest_price:.8f} (+{gain_pct:.1f}%), "
                f"Exit ${position.current_price:.8f}"
            )
            return True

        return False

    def get_position(self, token_address: str) -> Optional[Position]:
        """
        Get position by token address.

        Args:
            token_address: Token contract address

        Returns:
            Position object or None
        """
        return self.open_positions.get(token_address)

    def get_all_positions(self) -> List[Position]:
        """Get all open positions."""
        return list(self.open_positions.values())

    def get_total_exposure(self) -> float:
        """
        Get total USD exposure across all positions.

        Returns:
            Total exposure in USD
        """
        return sum(
            pos.quantity * pos.current_price
            for pos in self.open_positions.values()
        )

    def get_unrealized_pnl(self) -> float:
        """
        Get total unrealized PnL.

        Returns:
            Total unrealized PnL in USD
        """
        return sum(
            pos.unrealized_pnl
            for pos in self.open_positions.values()
        )

    def get_realized_pnl(self) -> float:
        """
        Get total realized PnL from closed trades.

        Returns:
            Total realized PnL in USD
        """
        return sum(
            trade.pnl
            for trade in self.closed_trades
            if trade.action == 'sell'
        )

    def get_daily_pnl(self) -> float:
        """
        Get PnL for today.

        Returns:
            Daily PnL in USD
        """
        today = datetime.now().date()
        return sum(
            trade.pnl
            for trade in self.daily_trades
            if trade.action == 'sell' and trade.timestamp.date() == today
        )

    def get_statistics(self) -> Dict:
        """
        Get trading statistics.

        Returns:
            Dictionary with statistics
        """
        closed_sell_trades = [t for t in self.closed_trades if t.action == 'sell']

        winning_trades = [t for t in closed_sell_trades if t.pnl > 0]
        losing_trades = [t for t in closed_sell_trades if t.pnl < 0]

        total_trades = len(closed_sell_trades)
        win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0

        avg_win = sum(t.pnl for t in winning_trades) / len(winning_trades) if winning_trades else 0
        avg_loss = sum(t.pnl for t in losing_trades) / len(losing_trades) if losing_trades else 0

        return {
            'open_positions': len(self.open_positions),
            'total_trades': total_trades,
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'total_realized_pnl': self.get_realized_pnl(),
            'total_unrealized_pnl': self.get_unrealized_pnl(),
            'daily_pnl': self.get_daily_pnl(),
            'total_exposure': self.get_total_exposure()
        }

    def reset_daily_stats(self):
        """Reset daily statistics."""
        self.daily_trades = []
        logger.info("Daily statistics reset")
