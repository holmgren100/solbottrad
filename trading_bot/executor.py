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

    def __init__(self, initial_balance: float = 1000.0):
        """
        Initialize paper trading executor.

        Args:
            initial_balance: Starting balance in SOL
        """
        self.initial_balance = initial_balance
        self.available_balance = initial_balance
        self.total_invested = 0.0

        # Simulated transaction fees
        self.buy_fee_percent = 0.3
        self.sell_fee_percent = 0.3
        self.buy_slippage_percent = 0.5
        self.sell_slippage_percent = 1.0

        logger.info(f"Paper trading initialized with ${initial_balance:.2f} SOL balance")

    async def execute_buy(
        self,
        token_address: str,
        amount_sol: float,
        price_usd: float,
        symbol: str = ""
    ) -> Optional[Dict]:
        """
        Execute buy order (paper trading).

        Args:
            token_address: Token to buy
            amount_sol: Amount in SOL to spend
            price_usd: Current token price
            symbol: Token symbol

        Returns:
            Trade details dict or None if failed
        """
        try:
            # Check available balance
            if amount_sol > self.available_balance:
                logger.warning(
                    f"Insufficient balance: Need ${amount_sol:.2f}, "
                    f"Have ${self.available_balance:.2f}"
                )
                return None

            # Calculate effective price with fees and slippage
            total_fee_percent = self.buy_fee_percent + self.buy_slippage_percent
            effective_price = price_usd * (1 + total_fee_percent / 100)

            # Calculate tokens received
            amount_after_fees = amount_sol * (1 - total_fee_percent / 100)
            tokens_received = amount_after_fees / effective_price

            # Update balances
            self.available_balance -= amount_sol
            self.total_invested += amount_sol

            trade_details = {
                'type': 'buy',
                'token_address': token_address,
                'symbol': symbol,
                'amount_sol': amount_sol,
                'price_usd': price_usd,
                'effective_price': effective_price,
                'tokens_received': tokens_received,
                'fees_percent': total_fee_percent,
                'timestamp': datetime.now().isoformat(),
                'paper_trading': True
            }

            logger.info(
                f"📈 BUY executed (paper): {symbol or token_address[:8]}... "
                f"${amount_sol:.2f} @ ${price_usd:.8f} "
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

            # Calculate SOL received
            gross_amount = tokens_amount * effective_price
            amount_after_fees = gross_amount * (1 - total_fee_percent / 100)

            # Update balances
            self.available_balance += amount_after_fees
            self.total_invested -= amount_after_fees

            trade_details = {
                'type': 'sell',
                'token_address': token_address,
                'symbol': symbol,
                'tokens_amount': tokens_amount,
                'price_usd': price_usd,
                'effective_price': effective_price,
                'sol_received': amount_after_fees,
                'fees_percent': total_fee_percent,
                'timestamp': datetime.now().isoformat(),
                'paper_trading': True
            }

            logger.info(
                f"📉 SELL executed (paper): {symbol or token_address[:8]}... "
                f"{tokens_amount:.2f} tokens @ ${price_usd:.8f} "
                f"→ ${amount_after_fees:.2f} SOL "
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
        return {
            'available_balance': self.available_balance,
            'total_invested': self.total_invested,
            'initial_balance': self.initial_balance,
            'total_pnl': self.available_balance + self.total_invested - self.initial_balance,
            'total_pnl_percent': (
                (self.available_balance + self.total_invested - self.initial_balance) /
                self.initial_balance * 100
            ) if self.initial_balance > 0 else 0
        }

    def print_balance(self):
        """Print current balance."""
        balance = self.get_balance()

        logger.info("=" * 60)
        logger.info("PAPER TRADING BALANCE")
        logger.info("=" * 60)
        logger.info(f"Available: ${balance['available_balance']:.2f} SOL")
        logger.info(f"Invested: ${balance['total_invested']:.2f} SOL")
        logger.info(f"Total PnL: ${balance['total_pnl']:.2f} ({balance['total_pnl_percent']:+.1f}%)")
        logger.info("=" * 60)


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
