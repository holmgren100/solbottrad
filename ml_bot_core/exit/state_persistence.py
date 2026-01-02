"""
State Persistence - Save and load bot state between restarts.

Saves:
- Open positions
- Closed trades
- Trading statistics
"""

import json
import os
from typing import Dict, List, Optional
from datetime import datetime
from dataclasses import asdict
from ..monitoring.logger import get_logger

logger = get_logger(__name__)


class StatePersistence:
    """Handles saving and loading bot state to/from disk."""

    def __init__(self, state_file: str = "bot_state.json"):
        """
        Initialize state persistence.

        Args:
            state_file: Path to state file
        """
        self.state_file = state_file

    def save_state(
        self,
        open_positions: Dict,
        closed_trades: List,
        portfolio_value: float,
        executor_state: Dict = None
    ) -> bool:
        """
        Save current bot state to disk.

        Args:
            open_positions: Dictionary of open Position objects
            closed_trades: List of closed Trade objects
            portfolio_value: Current portfolio value
            executor_state: Executor state (current_capital, total_invested, initial_capital)

        Returns:
            True if successful
        """
        try:
            state = {
                'timestamp': datetime.now().isoformat(),
                'portfolio_value': portfolio_value,
                'executor_state': executor_state or {},
                'open_positions': {},
                'closed_trades': [],
                'statistics': {
                    'total_trades': len(closed_trades),
                    'wins': sum(1 for t in closed_trades if t.pnl > 0),
                    'losses': sum(1 for t in closed_trades if t.pnl < 0),
                    'total_pnl': sum(t.pnl for t in closed_trades),
                }
            }

            # Convert positions to serializable format
            for address, position in open_positions.items():
                pos_dict = {
                    'token_address': position.token_address,
                    'entry_price': position.entry_price,
                    'current_price': position.current_price,
                    'amount_usd': position.amount_usd,
                    'quantity': position.quantity,
                    'entry_time': position.entry_time.isoformat(),
                    'stop_loss': position.stop_loss,
                    'take_profit': position.take_profit,
                    'use_trailing_stop': position.use_trailing_stop,
                    'trailing_stop_percent': position.trailing_stop_percent,
                    'highest_price': position.highest_price,
                    'trailing_stop_price': position.trailing_stop_price,
                    'symbol': position.symbol,
                    'current_liquidity': position.current_liquidity,
                    'entry_liquidity': position.entry_liquidity,
                    'initial_quantity': position.initial_quantity,
                    'milestones_hit': list(position.milestones_hit) if position.milestones_hit else [],
                    'total_partial_profit_usd': getattr(position, 'total_partial_profit_usd', 0.0),  # Save partial profits
                }
                state['open_positions'][address] = pos_dict

            # Convert trades to serializable format
            for trade in closed_trades:
                trade_dict = {
                    'token_address': trade.token_address,
                    'action': trade.action,
                    'price': trade.price,
                    'amount_usd': trade.amount_usd,
                    'quantity': trade.quantity,
                    'timestamp': trade.timestamp.isoformat(),
                    'pnl': trade.pnl,
                    'pnl_percent': trade.pnl_percent,
                    'reason': trade.reason,
                    'symbol': trade.symbol,
                    'entry_price': trade.entry_price if hasattr(trade, 'entry_price') else 0.0,
                    'entry_time': trade.entry_time.isoformat() if hasattr(trade, 'entry_time') and trade.entry_time else None,
                }
                state['closed_trades'].append(trade_dict)

            # Write to file with atomic write (temp file + rename)
            temp_file = f"{self.state_file}.tmp"
            with open(temp_file, 'w') as f:
                json.dump(state, f, indent=2)

            # Atomic rename
            os.replace(temp_file, self.state_file)

            logger.debug(f"💾 State saved: {len(open_positions)} positions, {len(closed_trades)} trades")
            return True

        except Exception as e:
            logger.error(f"Failed to save state: {e}")
            return False

    def load_state(self) -> Optional[Dict]:
        """
        Load bot state from disk.

        Returns:
            State dictionary or None if not found/error
        """
        try:
            if not os.path.exists(self.state_file):
                logger.info("No saved state found - starting fresh")
                return None

            with open(self.state_file, 'r') as f:
                state = json.load(f)

            logger.info(
                f"📂 Loaded state: {len(state.get('open_positions', {}))} positions, "
                f"{len(state.get('closed_trades', []))} trades"
            )

            return state

        except Exception as e:
            logger.error(f"Failed to load state: {e}")
            return None

    def clear_state(self) -> bool:
        """
        Delete state file (for fresh start).

        Returns:
            True if successful
        """
        try:
            if os.path.exists(self.state_file):
                os.remove(self.state_file)
                logger.info("🗑️  State file deleted")
            return True
        except Exception as e:
            logger.error(f"Failed to delete state: {e}")
            return False
