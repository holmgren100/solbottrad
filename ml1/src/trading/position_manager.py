"""
Position management and portfolio tracking.
"""

from typing import Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass, field
import csv
import os
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
    # Volume fallback flag (high risk trade with reduced position size)
    volume_fallback: bool = False  # True if entered with volume fallback (missing liquidity data)

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
    volume_fallback: bool = False  # True if entered with volume fallback (high risk/reduced size)


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
        trailing_stop_percent: float = 15.0,
        volume_fallback: bool = False
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
            volume_fallback: Whether this trade used volume fallback (high risk/reduced size)

        Returns:
            Position object if successful, None otherwise
        """
        if not self.can_open_position():
            logger.warning(f"Cannot open position - max positions reached ({self.max_open_positions})")
            return None

        if token_address in self.open_positions:
            logger.warning(f"Position already exists for {token_address}")
            return None

        # Validate entry price (critical bug fix)
        if entry_price <= 0:
            logger.error(
                f"❌ Invalid entry price ${entry_price} for {token_address[:8]}... "
                f"- cannot open position"
            )
            return None

        quantity = amount_usd / entry_price

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
            last_known_price=entry_price,  # Initialize for frozen price detection
            volume_fallback=volume_fallback  # Track if this is a high-risk volume fallback trade
        )

        self.open_positions[token_address] = position

        # Record buy trade
        buy_trade = Trade(
            token_address=token_address,
            action='buy',
            price=entry_price,
            amount_usd=amount_usd,
            quantity=quantity,
            timestamp=datetime.now(),
            volume_fallback=volume_fallback
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
            entry_time=position.entry_time,  # Store entry time for duration calculation
            volume_fallback=position.volume_fallback  # Preserve volume fallback flag from position
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

    def force_close_position(
        self,
        token_address: str,
        reason: str = 'forced_cleanup'
    ) -> Optional[Trade]:
        """
        Force close a position even if can't sell on market.
        Accepts the loss to free up position slot.

        Use cases:
        - Stuck with zero liquidity
        - Rugged token can't be sold
        - Position too old (>48h)
        - Manual cleanup needed

        Args:
            token_address: Token contract address
            reason: Reason for forced closure

        Returns:
            Trade object if successful, None otherwise
        """
        if token_address not in self.open_positions:
            logger.warning(f"No open position for {token_address}")
            return None

        position = self.open_positions[token_address]

        # Calculate loss (assume position is worthless or write it off)
        pnl = -position.amount_usd  # Total loss
        pnl_percent = -100.0

        # Create sell trade (even though we couldn't actually sell)
        sell_trade = Trade(
            token_address=token_address,
            action='sell',
            price=0.0,  # Worthless
            amount_usd=0.0,  # Got nothing
            quantity=position.quantity,
            timestamp=datetime.now(),
            pnl=pnl,
            pnl_percent=pnl_percent,
            reason=reason,  # 'forced_cleanup', 'stuck_position', etc.
            symbol=getattr(position, 'symbol', token_address[:8]),
            entry_price=position.entry_price,
            entry_time=position.entry_time,
            volume_fallback=position.volume_fallback
        )

        self.closed_trades.append(sell_trade)
        self.daily_trades.append(sell_trade)

        # Remove from open positions
        del self.open_positions[token_address]

        logger.warning(
            f"🗑️  FORCED CLEANUP {token_address[:8]}... - Position written off:\n"
            f"   Reason: {reason}\n"
            f"   Loss: ${position.amount_usd:.2f}\n"
            f"   Position slot freed for new trades"
        )

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

    def is_position_stuck(
        self,
        token_address: str,
        min_liquidity: float = 1000.0,
        stuck_hours: float = 6.0
    ) -> bool:
        """
        Detect if position is stuck (can't be sold).

        Criteria:
        - Zero or very low liquidity (<$1k)
        - No price movement for >6 hours
        - Failed sell attempts

        Args:
            token_address: Token contract address
            min_liquidity: Minimum liquidity threshold (default $1k)
            stuck_hours: Hours to consider stuck (default 6h)

        Returns:
            True if position is stuck
        """
        if token_address not in self.open_positions:
            return False

        position = self.open_positions[token_address]
        age_hours = (datetime.now() - position.entry_time).total_seconds() / 3600

        # Stuck if very low liquidity AND been stuck for >6 hours
        if position.current_liquidity < min_liquidity and age_hours > stuck_hours:
            return True

        # Or price frozen for >12 hours (even if liquidity shows)
        if position.is_price_frozen(freeze_minutes=int(stuck_hours * 2 * 60)):
            return True

        return False

    def get_stuck_positions(
        self,
        min_liquidity: float = 1000.0,
        stuck_hours: float = 6.0
    ) -> List[str]:
        """
        Get all stuck positions.

        Args:
            min_liquidity: Minimum liquidity threshold
            stuck_hours: Hours to consider stuck

        Returns:
            List of stuck position token addresses
        """
        stuck = []
        for token_address in self.open_positions:
            if self.is_position_stuck(token_address, min_liquidity, stuck_hours):
                stuck.append(token_address)
        return stuck

    def cleanup_old_positions(self, max_age_hours: float = 48.0) -> List[Trade]:
        """
        Force close positions older than max age.

        Args:
            max_age_hours: Maximum position age in hours (default 48h)

        Returns:
            List of closed trades
        """
        closed_trades = []

        for token_address, position in list(self.open_positions.items()):
            age_hours = (datetime.now() - position.entry_time).total_seconds() / 3600

            if age_hours > max_age_hours:
                logger.warning(
                    f"⏰ Position {token_address[:8]}... is {age_hours:.1f}h old "
                    f"(max {max_age_hours}h) - FORCING CLEANUP"
                )
                trade = self.force_close_position(token_address, reason='max_age_exceeded')
                if trade:
                    closed_trades.append(trade)

        return closed_trades

    def cleanup_stuck_positions(
        self,
        min_liquidity: float = 1000.0,
        stuck_hours: float = 6.0
    ) -> List[Trade]:
        """
        Force close all stuck positions.

        Args:
            min_liquidity: Minimum liquidity threshold
            stuck_hours: Hours to consider stuck

        Returns:
            List of closed trades
        """
        stuck_positions = self.get_stuck_positions(min_liquidity, stuck_hours)
        closed_trades = []

        for token_address in stuck_positions:
            logger.warning(f"🚫 STUCK POSITION detected: {token_address[:8]}... - Forcing cleanup")
            trade = self.force_close_position(token_address, reason='stuck_position')
            if trade:
                closed_trades.append(trade)

        return closed_trades

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

    def export_to_csv(self, filepath: str = 'data/trade_history.csv') -> int:
        """
        Export all closed trades to a CSV file for easy analysis in Excel.

        Args:
            filepath: Path to save CSV file

        Returns:
            Number of trades exported
        """
        # Create data directory if it doesn't exist
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        # Get only sell trades (actual closed positions)
        sell_trades = [t for t in self.closed_trades if t.action == 'sell']

        if not sell_trades:
            logger.info("No trades to export")
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
            'Quantity',             # NEW - Total tokens bought
            'Tokens per Dollar',    # NEW - Critical risk metric!
            'PnL ($)',
            'PnL (%)',
            'Win/Loss',
            'Duration',
            'Close Reason',
            'Volume Fallback'
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

                # Calculate tokens per dollar (critical risk metric)
                # Use entry price and quantity to calculate how many tokens per dollar
                if trade.entry_price > 0 and trade.quantity > 0:
                    # Calculate original position size (before any sells)
                    original_position_usd = trade.quantity * trade.entry_price
                    tokens_per_dollar = trade.quantity / original_position_usd if original_position_usd > 0 else 0
                else:
                    tokens_per_dollar = 0

                # Write row
                writer.writerow({
                    'Date': trade.timestamp.strftime('%Y-%m-%d'),
                    'Time': trade.timestamp.strftime('%H:%M:%S'),
                    'Token Address': trade.token_address,  # Full address for verification
                    'Token': trade.token_address[:16] + '...',  # Shortened for readability
                    'Symbol': trade.symbol or trade.token_address[:8],
                    'Entry Price': f"${trade.entry_price:.8f}",
                    'Exit Price': f"${trade.price:.8f}",
                    'Position Size ($)': f"${trade.amount_usd:.2f}",
                    'Quantity': f"{trade.quantity:,.0f}",
                    'Tokens per Dollar': f"{tokens_per_dollar:,.0f}",
                    'PnL ($)': f"${trade.pnl:.2f}",
                    'PnL (%)': f"{trade.pnl_percent:+.2f}%",
                    'Win/Loss': win_loss,
                    'Duration': duration_str,
                    'Close Reason': close_reason,
                    'Volume Fallback': 'YES' if trade.volume_fallback else 'NO'
                })

        logger.info(f"Exported {len(sell_trades)} trades to {filepath}")
        return len(sell_trades)
