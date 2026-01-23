"""
Position Manager - Track and Manage Trading Positions

Manages the complete lifecycle of a position:
- Opening positions
- Tracking PnL and highest price
- Triggering breakeven, pyramids, partials
- Closing positions

Integrates with:
- BreakevenHandler (at +50%)
- PyramidManager (at +150%, +300%)
- PartialProfits (at +50%, +500%, +1000%)
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

from config.parameters import HARD_STOP_LOSS_PERCENT

logger = logging.getLogger(__name__)


class Position:
    """
    Represents a single trading position.

    Tracks entry, current state, PnL, and position stages.
    """

    def __init__(
        self,
        token_address: str,
        symbol: str,
        entry_price: float,
        size_sol: float,
        timestamp: Optional[datetime] = None
    ):
        """
        Initialize a new position.

        Args:
            token_address: Token mint address
            symbol: Token symbol
            entry_price: Entry price in SOL
            size_sol: Position size in SOL
            timestamp: Entry timestamp (default: now)
        """
        self.token_address = token_address
        self.symbol = symbol
        self.entry_price = entry_price
        self.initial_size_sol = size_sol
        self.current_size_sol = size_sol  # Can change with partials
        self.timestamp = timestamp or datetime.now()

        # Price tracking
        self.current_price = entry_price
        self.highest_price = entry_price
        self.stop_loss = entry_price * (1 + HARD_STOP_LOSS_PERCENT / 100)

        # Position stages tracking
        self.position_stages = []  # List of dicts: {type, pct, price, timestamp}
        self.breakeven_triggered = False
        self.pyramid_1_triggered = False
        self.pyramid_2_triggered = False

        # Add entry stage
        self.position_stages.append({
            "type": "ENTRY",
            "size_sol": size_sol,
            "price": entry_price,
            "timestamp": self.timestamp
        })

        logger.info(
            f"📍 Position opened: {symbol} @ {entry_price:.6f} SOL, "
            f"size: {size_sol:.4f} SOL, stop: {self.stop_loss:.6f}"
        )

    @property
    def pnl_percent(self) -> float:
        """Calculate current PnL percentage."""
        if self.entry_price == 0:
            return 0.0
        return ((self.current_price - self.entry_price) / self.entry_price) * 100

    @property
    def pnl_sol(self) -> float:
        """Calculate current PnL in SOL."""
        return (self.current_price - self.entry_price) * self.current_size_sol

    @property
    def hold_time_minutes(self) -> int:
        """Calculate hold time in minutes."""
        delta = datetime.now() - self.timestamp
        return int(delta.total_seconds() / 60)

    def update_price(self, new_price: float):
        """
        Update current price and highest price.

        Args:
            new_price: New current price
        """
        self.current_price = new_price

        if new_price > self.highest_price:
            self.highest_price = new_price
            logger.debug(f"{self.symbol} new high: {new_price:.6f} SOL")

    def update_stop_loss(self, new_stop: float):
        """
        Update stop loss price.

        Args:
            new_stop: New stop loss price
        """
        old_stop = self.stop_loss
        self.stop_loss = new_stop

        logger.info(
            f"🛡️ {self.symbol} stop loss updated: "
            f"{old_stop:.6f} → {new_stop:.6f} SOL"
        )

    def add_to_position(self, size_sol: float, price: float, stage_name: str):
        """
        Add to position (pyramiding).

        Args:
            size_sol: Additional SOL to add
            price: Add price
            stage_name: Stage name (e.g., "PYRAMID_1")
        """
        self.current_size_sol += size_sol

        self.position_stages.append({
            "type": stage_name,
            "size_sol": size_sol,
            "price": price,
            "timestamp": datetime.now()
        })

        logger.info(
            f"➕ {self.symbol} {stage_name}: +{size_sol:.4f} SOL @ {price:.6f}, "
            f"total size: {self.current_size_sol:.4f} SOL"
        )

    def take_partial(self, percent: float, price: float, stage_name: str):
        """
        Take partial profit.

        Args:
            percent: Percentage to sell (0-100)
            price: Sell price
            stage_name: Stage name (e.g., "PARTIAL_500")
        """
        sol_to_sell = self.current_size_sol * (percent / 100)
        self.current_size_sol -= sol_to_sell

        self.position_stages.append({
            "type": stage_name,
            "size_sol": -sol_to_sell,  # Negative for sell
            "price": price,
            "timestamp": datetime.now()
        })

        logger.info(
            f"💰 {self.symbol} {stage_name}: -{percent}% ({sol_to_sell:.4f} SOL) @ {price:.6f}, "
            f"remaining: {self.current_size_sol:.4f} SOL"
        )

    def to_dict(self) -> Dict:
        """Convert position to dictionary."""
        return {
            "token_address": self.token_address,
            "symbol": self.symbol,
            "entry_price": self.entry_price,
            "current_price": self.current_price,
            "highest_price": self.highest_price,
            "stop_loss": self.stop_loss,
            "initial_size_sol": self.initial_size_sol,
            "current_size_sol": self.current_size_sol,
            "pnl_percent": self.pnl_percent,
            "pnl_sol": self.pnl_sol,
            "hold_time_minutes": self.hold_time_minutes,
            "timestamp": self.timestamp.isoformat(),
            "position_stages": self.position_stages,
            "breakeven_triggered": self.breakeven_triggered,
            "pyramid_1_triggered": self.pyramid_1_triggered,
            "pyramid_2_triggered": self.pyramid_2_triggered,
        }


class PositionManager:
    """
    Manages all open positions.

    Handles opening, updating, and closing positions.
    Auto-triggers breakeven, pyramids, and partials on updates.
    """

    def __init__(
        self,
        breakeven_handler=None,
        pyramid_manager=None,
        partial_profits=None
    ):
        """
        Initialize position manager.

        Args:
            breakeven_handler: BreakevenHandler instance
            pyramid_manager: PyramidManager instance
            partial_profits: PartialProfits instance
        """
        self.positions: Dict[str, Position] = {}  # token_address -> Position
        self.closed_positions: List[Dict] = []

        # Handlers (can be set later)
        self.breakeven_handler = breakeven_handler
        self.pyramid_manager = pyramid_manager
        self.partial_profits = partial_profits

        logger.info("Position Manager initialized")

    def open_position(
        self,
        token_address: str,
        symbol: str,
        entry_price: float,
        size_sol: float
    ) -> Position:
        """
        Open a new position.

        Args:
            token_address: Token mint address
            symbol: Token symbol
            entry_price: Entry price in SOL
            size_sol: Position size in SOL

        Returns:
            New Position object
        """
        if token_address in self.positions:
            logger.warning(f"Position already exists for {symbol}")
            return self.positions[token_address]

        position = Position(token_address, symbol, entry_price, size_sol)
        self.positions[token_address] = position

        logger.info(f"✅ Opened position: {symbol} ({token_address[:8]}...)")

        return position

    def update_position(
        self,
        token_address: str,
        current_price: float,
        token_data: Optional[Dict] = None
    ) -> Dict:
        """
        Update position with new price and trigger checks.

        Auto-triggers:
        - Breakeven at +50%
        - Pyramid at +150%, +300%
        - Partials at +50%, +500%, +1000%

        Args:
            token_address: Token address
            current_price: Current price
            token_data: Optional token data for pyramid checks

        Returns:
            Dict with triggered actions
        """
        position = self.positions.get(token_address)
        if not position:
            logger.warning(f"No position found for {token_address}")
            return {"error": "Position not found"}

        # Update price
        position.update_price(current_price)

        actions = {
            "breakeven": None,
            "pyramid": None,
            "partials": [],
        }

        # Check breakeven
        if self.breakeven_handler and not position.breakeven_triggered:
            breakeven_result = self.breakeven_handler.trigger_breakeven(position)
            if breakeven_result["triggered"]:
                actions["breakeven"] = breakeven_result
                position.breakeven_triggered = True

        # Check pyramids
        if self.pyramid_manager and token_data:
            pyramid_result = self.pyramid_manager.check_pyramid(position, token_data)
            if pyramid_result["should_add"]:
                actions["pyramid"] = pyramid_result

                # Mark stage as triggered
                if pyramid_result["stage"] == 1:
                    position.pyramid_1_triggered = True
                elif pyramid_result["stage"] == 2:
                    position.pyramid_2_triggered = True

        # Check partials
        if self.partial_profits:
            partial_result = self.partial_profits.check_partials(position)
            if partial_result["should_sell"]:
                actions["partials"].append(partial_result)

        return actions

    def close_position(
        self,
        token_address: str,
        exit_price: float,
        reason: str
    ) -> Dict:
        """
        Close a position.

        Args:
            token_address: Token address
            exit_price: Exit price
            reason: Reason for closing

        Returns:
            Dict with position summary
        """
        position = self.positions.get(token_address)
        if not position:
            logger.warning(f"No position to close for {token_address}")
            return {"error": "Position not found"}

        # Update to exit price
        position.update_price(exit_price)

        # Calculate final PnL
        final_pnl_pct = position.pnl_percent
        final_pnl_sol = position.pnl_sol
        hold_time = position.hold_time_minutes

        # Create summary
        summary = {
            **position.to_dict(),
            "exit_price": exit_price,
            "exit_reason": reason,
            "final_pnl_percent": final_pnl_pct,
            "final_pnl_sol": final_pnl_sol,
            "hold_time_minutes": hold_time,
            "closed_at": datetime.now().isoformat()
        }

        # Log result
        emoji = "🎉" if final_pnl_pct > 0 else "😢"
        logger.info(
            f"{emoji} Closed {position.symbol}: "
            f"{final_pnl_pct:+.1f}% ({final_pnl_sol:+.4f} SOL) "
            f"in {hold_time}m - {reason}"
        )

        # Move to closed positions
        self.closed_positions.append(summary)
        del self.positions[token_address]

        return summary

    def get_position(self, token_address: str) -> Optional[Position]:
        """Get position by token address."""
        return self.positions.get(token_address)

    def get_all_positions(self) -> List[Position]:
        """Get all open positions."""
        return list(self.positions.values())

    def get_position_count(self) -> int:
        """Get number of open positions."""
        return len(self.positions)

    def get_total_pnl(self) -> Dict:
        """
        Calculate total PnL across all positions.

        Returns:
            Dict with total_pnl_percent and total_pnl_sol
        """
        if not self.positions:
            return {"total_pnl_percent": 0, "total_pnl_sol": 0}

        total_pnl_sol = sum(p.pnl_sol for p in self.positions.values())

        # Weighted average PnL%
        total_entry_value = sum(
            p.entry_price * p.initial_size_sol for p in self.positions.values()
        )
        total_current_value = sum(
            p.current_price * p.current_size_sol for p in self.positions.values()
        )

        if total_entry_value > 0:
            total_pnl_percent = ((total_current_value - total_entry_value) / total_entry_value) * 100
        else:
            total_pnl_percent = 0

        return {
            "total_pnl_percent": total_pnl_percent,
            "total_pnl_sol": total_pnl_sol
        }


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    # Create position manager
    manager = PositionManager()

    # Open position
    position = manager.open_position(
        token_address="ABC123...",
        symbol="TEST",
        entry_price=0.001,
        size_sol=0.1
    )

    print(f"\nInitial position: {position.pnl_percent:.1f}%")

    # Simulate price movement
    manager.update_position("ABC123...", 0.0015)  # +50%
    print(f"At +50%: {position.pnl_percent:.1f}%")

    manager.update_position("ABC123...", 0.0025)  # +150%
    print(f"At +150%: {position.pnl_percent:.1f}%")

    # Close position
    summary = manager.close_position(
        "ABC123...",
        exit_price=0.006,
        reason="Take profit +500%"
    )

    print(f"\nClosed: {summary['final_pnl_percent']:+.1f}%")
