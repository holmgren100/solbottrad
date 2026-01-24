"""
Trade Executor - Handles Trade Execution

Supports:
- Paper trading (simulation)
- Live trading (future implementation)
"""

import asyncio
import logging
from typing import Optional, Dict
from datetime import datetime

logger = logging.getLogger(__name__)


class PaperTradingExecutor:
    """
    Paper trading executor - simulates trades without real blockchain transactions.

    Tracks:
    - Available balance
    - Open positions
    - Trade history
    """

    def __init__(self, initial_capital: float = 1000.0):
        """
        Initialize paper trading executor.

        Args:
            initial_capital: Starting capital in USD
        """
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.total_invested = 0.0

        # Simulated transaction fees
        self.buy_fee_percent = 0.3
        self.sell_fee_percent = 0.3
        self.buy_slippage_percent = 0.5
        self.sell_slippage_percent = 1.0

        logger.info(f"Paper trading initialized with ${initial_capital:.2f} USD capital")

    async def execute_buy(
        self,
        token_address: str,
        amount_usd: float,
        price_usd: float,
        symbol: str = ""
    ) -> Optional[Dict]:
        """
        Execute buy order (paper trading).

        Args:
            token_address: Token to buy
            amount_usd: Amount in USD to spend
            price_usd: Current token price
            symbol: Token symbol

        Returns:
            Trade details dict or None if failed
        """
        try:
            # Check available capital
            if amount_usd > self.current_capital:
                logger.warning(
                    f"Insufficient capital: Need ${amount_usd:.2f} USD, "
                    f"Have ${self.current_capital:.2f} USD"
                )
                return None

            # Calculate effective price with fees and slippage
            total_fee_percent = self.buy_fee_percent + self.buy_slippage_percent
            effective_price = price_usd * (1 + total_fee_percent / 100)

            # Calculate tokens received
            amount_after_fees = amount_usd * (1 - total_fee_percent / 100)
            tokens_received = amount_after_fees / effective_price

            # Update capital (only update cash, don't track total_invested manually)
            self.current_capital -= amount_usd
            # Note: total_invested will be calculated from position_manager in get_balance()

            trade_details = {
                'type': 'buy',
                'token_address': token_address,
                'symbol': symbol,
                'amount_usd': amount_usd,
                'price_usd': price_usd,
                'effective_price': effective_price,
                'tokens_received': tokens_received,
                'fees_percent': total_fee_percent,
                'timestamp': datetime.now().isoformat(),
                'paper_trading': True
            }

            logger.info(
                f"📈 BUY executed (paper): {symbol or token_address[:8]}... "
                f"${amount_usd:.2f} USD @ ${price_usd:.8f} "
                f"(effective: ${effective_price:.8f}, fees: {total_fee_percent:.1f}%)"
            )

            return trade_details

        except Exception as e:
            logger.error(f"Error executing buy: {e}", exc_info=True)
            return None

    async def execute_sell(
        self,
        token_address: str,
        tokens_amount: float,
        price_usd: float,
        symbol: str = ""
    ) -> Optional[Dict]:
        """
        Execute sell order (paper trading).

        Args:
            token_address: Token to sell
            tokens_amount: Amount of tokens to sell
            price_usd: Current token price
            symbol: Token symbol

        Returns:
            Trade details dict or None if failed
        """
        try:
            # Calculate effective price with fees and slippage
            total_fee_percent = self.sell_fee_percent + self.sell_slippage_percent
            effective_price = price_usd * (1 - total_fee_percent / 100)

            # Calculate USD received
            gross_amount = tokens_amount * effective_price
            amount_after_fees = gross_amount * (1 - total_fee_percent / 100)

            # Update capital (only update cash, don't track total_invested manually)
            self.current_capital += amount_after_fees
            # Note: total_invested will be calculated from position_manager in get_balance()

            trade_details = {
                'type': 'sell',
                'token_address': token_address,
                'symbol': symbol,
                'tokens_amount': tokens_amount,
                'price_usd': price_usd,
                'effective_price': effective_price,
                'usd_received': amount_after_fees,
                'fees_percent': total_fee_percent,
                'timestamp': datetime.now().isoformat(),
                'paper_trading': True
            }

            logger.info(
                f"📉 SELL executed (paper): {symbol or token_address[:8]}... "
                f"{tokens_amount:.2f} tokens @ ${price_usd:.8f} "
                f"→ ${amount_after_fees:.2f} USD "
                f"(fees: {total_fee_percent:.1f}%)"
            )

            return trade_details

        except Exception as e:
            logger.error(f"Error executing sell: {e}", exc_info=True)
            return None

    def get_balance(self) -> Dict:
        """
        Get current balance information.

        Returns:
            Balance details dict
        """
        # Calculate total_invested from position_manager (cost basis of open positions)
        total_invested = 0.0
        unrealized_pnl = 0.0

        if hasattr(self, 'position_manager'):
            # Sum cost basis of all open positions
            for position in self.position_manager.get_all_positions():
                total_invested += position.amount_usd  # Cost basis

            # Get unrealized P&L
            unrealized_pnl = self.position_manager.get_unrealized_pnl()

        # Calculate total value and P&L
        total_value = self.current_capital + total_invested + unrealized_pnl
        total_pnl = total_value - self.initial_capital

        return {
            'available_balance': self.current_capital,
            'total_invested': total_invested,  # Calculated from positions, not tracked
            'initial_capital': self.initial_capital,
            'total_pnl': total_pnl,
            'total_pnl_percent': (
                total_pnl / self.initial_capital * 100
            ) if self.initial_capital > 0 else 0
        }

    def print_balance(self):
        """Print current balance."""
        balance = self.get_balance()

        logger.info("=" * 60)
        logger.info("PAPER TRADING BALANCE")
        logger.info("=" * 60)
        logger.info(f"Available: ${balance['available_balance']:.2f} USD")
        logger.info(f"Invested: ${balance['total_invested']:.2f} USD")
        logger.info(f"Total PnL: ${balance['total_pnl']:.2f} ({balance['total_pnl_percent']:+.1f}%)")
        logger.info("=" * 60)

    def get_performance_summary(self) -> Dict:
        """
        Get performance summary for Telegram /status command.

        Returns:
            Performance summary dict
        """
        balance = self.get_balance()

        # Get trade statistics from position_manager if available
        stats = {'total_trades': 0, 'win_rate': 0.0, 'winning_trades': 0, 'losing_trades': 0}
        if hasattr(self, 'position_manager'):
            pm_stats = self.position_manager.get_statistics()
            stats = {
                'total_trades': pm_stats.get('total_trades', 0),
                'win_rate': pm_stats.get('win_rate', 0.0),
                'winning_trades': pm_stats.get('winning_trades', 0),
                'losing_trades': pm_stats.get('losing_trades', 0)
            }

        return {
            'portfolio_value': balance['available_balance'] + balance['total_invested'],
            'current_capital': balance['available_balance'],
            'invested_capital': balance['total_invested'],
            'total_pnl': balance['total_pnl'],
            'total_return_percent': balance['total_pnl_percent'],
            'initial_capital': balance['initial_capital'],
            'total_trades': stats['total_trades'],
            'win_rate': stats['win_rate'],
            'winning_trades': stats['winning_trades'],
            'losing_trades': stats['losing_trades']
        }

    def get_state(self) -> Dict:
        """
        Get executor state for persistence.

        Returns:
            State dict with current_capital, total_invested, initial_capital
        """
        return {
            'current_capital': self.current_capital,
            'total_invested': self.total_invested,
            'initial_capital': self.initial_capital
        }

    def restore_state(self, state: Dict):
        """
        Restore executor state from saved data.

        Args:
            state: State dict with current_capital, total_invested, initial_capital
        """
        self.current_capital = state.get('current_capital', self.initial_capital)
        self.total_invested = state.get('total_invested', 0.0)
        self.initial_capital = state.get('initial_capital', self.initial_capital)

        logger.info(
            f"📂 Restored executor state: "
            f"Capital ${self.current_capital:.2f}, "
            f"Invested ${self.total_invested:.2f}, "
            f"Initial ${self.initial_capital:.2f}"
        )


class LiveTradingExecutor:
    """
    Live trading executor - executes real trades on Solana blockchain.

    🚨 NOT IMPLEMENTED YET - Use paper trading first!
    """

    def __init__(self, wallet_private_key: str):
        """
        Initialize live trading executor.

        Args:
            wallet_private_key: Solana wallet private key
        """
        raise NotImplementedError(
            "Live trading not implemented yet. Use paper trading mode first "
            "to validate strategy!"
        )
