"""
Position management and portfolio tracking.
"""

from typing import Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass, field
import csv
import os
from ..monitoring.logger import get_logger
from .state_persistence import StatePersistence

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
    symbol: str = ''  # Token symbol for display
    # Rug detection fields
    last_price_update: datetime = field(default_factory=datetime.now)  # Track when price was last updated
    last_price_change: datetime = field(default_factory=datetime.now)  # Track when price ACTUALLY changed
    last_known_price: float = 0.0  # Track previous price to detect changes
    current_liquidity: float = 0.0  # Track current liquidity
    price_update_failures: int = 0  # Count consecutive failed price updates
    # Partial profit taking fields
    initial_quantity: float = 0.0  # Track original quantity for partial sells
    milestones_hit: set = field(default_factory=set)  # Track which profit milestones have been taken (100, 200, 300, 500)

    def update_price(self, new_price: float, liquidity: float = 0.0):
        """Update current price and PnL."""
        # Track if price ACTUALLY changed (not just API responding with same price)
        # Use 0.1% threshold to ignore tiny API noise but catch real freezes
        if self.last_known_price > 0:
            price_change_pct = abs((new_price - self.last_known_price) / self.last_known_price) * 100
            if price_change_pct >= 0.1:  # Real change (>0.1%)
                self.last_price_change = datetime.now()
        else:
            # First price update
            self.last_price_change = datetime.now()

        self.last_known_price = new_price  # Store for next comparison
        self.current_price = new_price
        self.last_price_update = datetime.now()
        self.price_update_failures = 0  # Reset failure count on successful update
        self.current_liquidity = liquidity

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

    def check_profit_milestone(self) -> Optional[int]:
        """
        Check if position has hit a new profit milestone.

        Returns:
            Milestone level (100, 200, 300, 500) if new milestone hit, None otherwise
        """
        # Check milestones in order from highest to lowest
        milestones = [700, 600, 500, 400, 300, 200, 100]

        for milestone in milestones:
            if self.unrealized_pnl_percent >= milestone and milestone not in self.milestones_hit:
                return milestone

        return None

    def mark_price_update_failed(self):
        """Mark that a price update failed."""
        self.price_update_failures += 1

    def is_price_stale(self, stale_minutes: int = 10) -> bool:
        """Check if price hasn't been updated recently (possible rug/dead token)."""
        from datetime import timedelta
        time_since_update = datetime.now() - self.last_price_update
        return time_since_update > timedelta(minutes=stale_minutes)

    def is_price_frozen(self, freeze_minutes: int = 15) -> bool:
        """
        Check if price hasn't CHANGED for too long (frozen/stuck price).

        Different from is_price_stale - this checks if APIs are responding
        but the price itself isn't moving (honeypot, frozen, dead token).

        Args:
            freeze_minutes: Minutes without price change to consider frozen

        Returns:
            True if price has been frozen (not changed) for too long
        """
        from datetime import timedelta
        time_since_change = datetime.now() - self.last_price_change
        minutes_frozen = time_since_change.total_seconds() / 60

        # Only flag as frozen if we've held for at least 5 minutes
        # (prevents false positives on new positions)
        minutes_held = (datetime.now() - self.entry_time).total_seconds() / 60
        if minutes_held < 5:
            return False

        return time_since_change > timedelta(minutes=freeze_minutes)

    def is_liquidity_dead(self, min_liquidity: float = 1000.0) -> bool:
        """
        Check if liquidity has dried up (possible rug).

        Returns True if liquidity is below threshold AND we've received at least
        one price update (so we know the liquidity data is real, not just uninitialized).
        """
        # Only check liquidity if we've had at least one price update
        # (last_price_update != entry_time means we got market data)
        has_received_update = self.last_price_update != self.entry_time

        # If we've received updates and liquidity is below threshold, it's dead
        return has_received_update and self.current_liquidity < min_liquidity


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
    reason: str = ''  # Why trade closed: 'trailing_stop', 'manual', 'rugged/dead', etc.
    symbol: str = ''  # Token symbol for readability
    entry_price: float = 0.0  # Entry price (for sell trades)
    entry_time: datetime = None  # Entry time (for calculating duration)


class PositionManager:
    """Manages trading positions and portfolio."""

    def __init__(self, max_open_positions: int = 5, enable_persistence: bool = True):
        """
        Initialize position manager.

        Args:
            max_open_positions: Maximum number of simultaneous positions
            enable_persistence: Enable state persistence between restarts
        """
        self.max_open_positions = max_open_positions
        self.open_positions: Dict[str, Position] = {}
        self.closed_trades: List[Trade] = []
        self.daily_trades: List[Trade] = []
        self.portfolio_value: float = 0.0

        # State persistence
        self.enable_persistence = enable_persistence
        self.state_persistence = StatePersistence() if enable_persistence else None

        # Load saved state if available
        if self.enable_persistence:
            self._load_state()

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
            trailing_stop_price=stop_loss,  # Start with regular stop loss
            initial_quantity=quantity,  # Track original quantity for partial profit taking
            last_known_price=entry_price  # Initialize for frozen price detection
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

        # Save state after opening position
        self._save_state()

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

        # Create sell trade with full details for CSV export
        sell_trade = Trade(
            token_address=token_address,
            action='sell',
            price=exit_price,
            amount_usd=position.quantity * exit_price,
            quantity=position.quantity,
            timestamp=datetime.now(),
            pnl=pnl,
            pnl_percent=pnl_percent,
            reason=reason,  # Store close reason
            symbol=getattr(position, 'symbol', token_address[:8]),  # Token symbol or short address
            entry_price=position.entry_price,  # Store entry price for reference
            entry_time=position.entry_time  # Store entry time for duration calculation
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

        # Save state after closing position
        self._save_state()

        return sell_trade

    def update_position_price(self, token_address: str, current_price: float, liquidity: float = 0.0):
        """
        Update position with current price and liquidity.

        Args:
            token_address: Token contract address
            current_price: Current market price
            liquidity: Current liquidity in USD
        """
        if token_address in self.open_positions:
            self.open_positions[token_address].update_price(current_price, liquidity)

    def mark_position_price_failed(self, token_address: str):
        """
        Mark that a price update failed for a position.

        Args:
            token_address: Token contract address
        """
        if token_address in self.open_positions:
            self.open_positions[token_address].mark_price_update_failed()

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

    def get_dead_positions(self, stale_minutes: int = 10, min_liquidity: float = 1000.0, freeze_minutes: int = 15) -> List[str]:
        """
        Get positions that are likely rugged or dead (stale price or no liquidity).

        Args:
            stale_minutes: Minutes without price update to consider stale
            min_liquidity: Minimum liquidity threshold in USD
            freeze_minutes: Minutes without price CHANGE to consider frozen

        Returns:
            List of token addresses for dead positions
        """
        dead_positions = []

        for token_address, position in self.open_positions.items():
            # Check if price is stale (no updates in X minutes)
            if position.is_price_stale(stale_minutes):
                minutes_since = (datetime.now() - position.last_price_update).total_seconds() / 60
                logger.warning(
                    f"🚨 DEAD TOKEN DETECTED: {token_address[:8]}... - "
                    f"No price update for {minutes_since:.1f} minutes (likely rugged)"
                )
                dead_positions.append(token_address)
                continue

            # Check if price is FROZEN (APIs responding but price not moving)
            if position.is_price_frozen(freeze_minutes):
                minutes_frozen = (datetime.now() - position.last_price_change).total_seconds() / 60
                logger.warning(
                    f"🚨 FROZEN TOKEN DETECTED: {token_address[:8]}... - "
                    f"Price hasn't changed for {minutes_frozen:.1f} minutes @ ${position.current_price:.8f} "
                    f"(likely honeypot/dead/locked)"
                )
                dead_positions.append(token_address)
                continue

            # Check if liquidity has dried up
            if position.is_liquidity_dead(min_liquidity):
                logger.warning(
                    f"🚨 DEAD TOKEN DETECTED: {token_address[:8]}... - "
                    f"Liquidity dried up (${position.current_liquidity:.2f} < ${min_liquidity:.2f})"
                )
                dead_positions.append(token_address)
                continue

            # Check for multiple consecutive price update failures
            # Lowered from 5 to 3 - faster detection of dead tokens
            if position.price_update_failures >= 3:
                logger.warning(
                    f"🚨 DEAD TOKEN DETECTED: {token_address[:8]}... - "
                    f"{position.price_update_failures} consecutive price update failures"
                )
                dead_positions.append(token_address)
                continue

            # Check if price hasn't actually changed (fake updates / minimal movement)
            # If price moved less than 1% after 5+ minutes, likely honeypot/dead/manipulated
            minutes_held = (datetime.now() - position.entry_time).total_seconds() / 60
            if minutes_held >= 5:
                price_change_pct = abs((position.current_price - position.entry_price) / position.entry_price) * 100
                if price_change_pct < 1.0:  # Less than 1% movement in 5+ minutes
                    logger.warning(
                        f"🚨 DEAD TOKEN DETECTED: {token_address[:8]}... - "
                        f"Minimal price movement ({price_change_pct:.2f}%) for {minutes_held:.1f} minutes (likely honeypot/dead/rugged)"
                    )
                    dead_positions.append(token_address)

        return dead_positions

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

    def export_to_csv(
        self,
        filepath: str = 'data/trade_history.csv',
        timeframe: str = 'all',
        limit: Optional[int] = None
    ) -> int:
        """
        Export closed trades to a CSV file for easy analysis in Excel.

        Args:
            filepath: Path to save CSV file
            timeframe: Time filter ('all', 'daily', 'weekly', 'monthly')
            limit: Maximum number of trades to export (most recent first)

        Returns:
            Number of trades exported
        """
        from datetime import timedelta

        # Create data directory if it doesn't exist
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        # Get only sell trades (actual closed positions)
        sell_trades = [t for t in self.closed_trades if t.action == 'sell']

        if not sell_trades:
            logger.info("No trades to export")
            return 0

        # Filter by timeframe
        if timeframe != 'all':
            now = datetime.now()
            if timeframe == 'daily':
                cutoff = now - timedelta(days=1)
            elif timeframe == 'weekly':
                cutoff = now - timedelta(days=7)
            elif timeframe == 'monthly':
                cutoff = now - timedelta(days=30)
            else:
                cutoff = None

            if cutoff:
                sell_trades = [t for t in sell_trades if t.timestamp >= cutoff]

        # Sort by timestamp (newest first)
        sell_trades = sorted(sell_trades, key=lambda t: t.timestamp, reverse=True)

        # Apply limit if specified
        if limit and limit > 0:
            sell_trades = sell_trades[:limit]

        if not sell_trades:
            logger.info(f"No trades to export for timeframe: {timeframe}")
            return 0

        # Define CSV columns
        fieldnames = [
            'Date',
            'Time',
            'Token',
            'Symbol',
            'Entry Price',
            'Exit Price',
            'Position Size ($)',
            'PnL ($)',
            'PnL (%)',
            'Win/Loss',
            'Duration',
            'Close Reason'
        ]

        # Write to CSV
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for trade in sell_trades:
                # Calculate duration
                if trade.entry_time:
                    duration = trade.timestamp - trade.entry_time
                    duration_str = f"{duration.total_seconds() / 3600:.1f}h"
                else:
                    duration_str = "N/A"

                # Determine win/loss
                win_loss = "WIN" if trade.pnl > 0 else "LOSS" if trade.pnl < 0 else "BREAK-EVEN"

                # Format close reason nicely
                reason_map = {
                    'trailing_stop': 'Trailing Stop',
                    'stop_loss': 'Stop Loss',
                    'take_profit': 'Take Profit',
                    'manual': 'Manual Close',
                    'manual_telegram': 'Manual (Telegram)',
                    'manual_closeall': 'Close All (Telegram)',
                    'rugged/dead': 'Rugged/Dead',
                    'partial_profit': 'Partial Profit'
                }
                close_reason = reason_map.get(trade.reason, trade.reason or 'Unknown')

                # Write row
                writer.writerow({
                    'Date': trade.timestamp.strftime('%Y-%m-%d'),
                    'Time': trade.timestamp.strftime('%H:%M:%S'),
                    'Token': trade.token_address[:16] + '...',  # Shortened for readability
                    'Symbol': trade.symbol or trade.token_address[:8],
                    'Entry Price': f"${trade.entry_price:.8f}",
                    'Exit Price': f"${trade.price:.8f}",
                    'Position Size ($)': f"${trade.amount_usd:.2f}",
                    'PnL ($)': f"${trade.pnl:.2f}",
                    'PnL (%)': f"{trade.pnl_percent:+.2f}%",
                    'Win/Loss': win_loss,
                    'Duration': duration_str,
                    'Close Reason': close_reason
                })

        logger.info(f"Exported {len(sell_trades)} trades to {filepath}")
        return len(sell_trades)

    def _save_state(self):
        """Save current state to disk (if persistence enabled)."""
        if not self.enable_persistence or not self.state_persistence:
            return

        self.state_persistence.save_state(
            self.open_positions,
            self.closed_trades,
            self.portfolio_value
        )

    def _load_state(self):
        """Load saved state from disk (if available)."""
        if not self.enable_persistence or not self.state_persistence:
            return

        state = self.state_persistence.load_state()
        if not state:
            return

        # Restore portfolio value
        self.portfolio_value = state.get('portfolio_value', 0.0)

        # Restore open positions
        for address, pos_dict in state.get('open_positions', {}).items():
            try:
                position = Position(
                    token_address=pos_dict['token_address'],
                    entry_price=pos_dict['entry_price'],
                    current_price=pos_dict['current_price'],
                    amount_usd=pos_dict['amount_usd'],
                    quantity=pos_dict['quantity'],
                    entry_time=datetime.fromisoformat(pos_dict['entry_time']),
                    stop_loss=pos_dict['stop_loss'],
                    take_profit=pos_dict['take_profit'],
                    use_trailing_stop=pos_dict.get('use_trailing_stop', True),
                    trailing_stop_percent=pos_dict.get('trailing_stop_percent', 15.0),
                    highest_price=pos_dict.get('highest_price', pos_dict['entry_price']),
                    trailing_stop_price=pos_dict.get('trailing_stop_price', 0.0),
                    symbol=pos_dict.get('symbol', ''),
                    current_liquidity=pos_dict.get('current_liquidity', 0.0),
                    initial_quantity=pos_dict.get('initial_quantity', pos_dict['quantity']),
                    milestones_hit=set(pos_dict.get('milestones_hit', []))
                )
                self.open_positions[address] = position
                logger.info(f"📂 Restored position: {position.symbol or address[:8]}... @ ${position.entry_price:.8f}")
            except Exception as e:
                logger.error(f"Failed to restore position {address[:8]}...: {e}")

        # Restore closed trades
        for trade_dict in state.get('closed_trades', []):
            try:
                trade = Trade(
                    token_address=trade_dict['token_address'],
                    action=trade_dict['action'],
                    price=trade_dict['price'],
                    amount_usd=trade_dict['amount_usd'],
                    quantity=trade_dict['quantity'],
                    timestamp=datetime.fromisoformat(trade_dict['timestamp']),
                    pnl=trade_dict.get('pnl', 0.0),
                    pnl_percent=trade_dict.get('pnl_percent', 0.0),
                    reason=trade_dict.get('reason', ''),
                    symbol=trade_dict.get('symbol', ''),
                    entry_price=trade_dict.get('entry_price', 0.0),
                    entry_time=datetime.fromisoformat(trade_dict['entry_time']) if trade_dict.get('entry_time') else None
                )
                self.closed_trades.append(trade)
            except Exception as e:
                logger.error(f"Failed to restore trade: {e}")

        stats = state.get('statistics', {})
        logger.info(
            f"📊 Restored statistics: {stats.get('total_trades', 0)} trades, "
            f"{stats.get('wins', 0)}W-{stats.get('losses', 0)}L"
        )
