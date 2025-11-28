"""
Live Trading Engine for real Solana swaps via Jupiter.
Manages real wallet, executes actual trades, tracks on-chain positions.
"""

import asyncio
from typing import Dict, Optional
from datetime import datetime
from .position_manager import PositionManager
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
        max_open_positions: int = 12
    ):
        """
        Initialize live trading engine.

        Args:
            jupiter_executor: Jupiter executor configured with wallet
            position_manager: Optional position manager (creates new if not provided)
            max_open_positions: Maximum simultaneous positions
        """
        self.jupiter_executor = jupiter_executor
        self.position_manager = position_manager or PositionManager(max_open_positions)

        # Trading state (tracked separately from wallet balance)
        self.starting_balance = 0.0  # Will be set on first balance check
        self.total_invested = 0.0  # Currently invested in open positions

        logger.info(
            f"✅ LiveTradingEngine initialized - "
            f"Wallet: {jupiter_executor.wallet.get_public_key()[:8]}..."
        )

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
        reason: str = 'manual'
    ) -> Dict:
        """
        Execute a real sell order on-chain.

        Args:
            token_address: Token to sell
            price: Current token price
            reason: Reason for selling

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

            logger.info(f"🔴 [LIVE] SELL: {position.quantity:.4f} {token_address[:8]}... @ ${price:.8f} ({reason})")

            # Execute real swap via Jupiter
            swap_result = await self.jupiter_executor.sell_token(
                token_mint=token_address,
                amount_tokens=position.quantity,
                slippage_percent=5.0
            )

            if not swap_result.get('success'):
                logger.error(f"❌ Sell swap failed: {swap_result.get('error', 'Unknown')}")
                return {
                    'status': 'failed',
                    'reason': swap_result.get('error', 'swap_failed')
                }

            # Close position
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
        Get total portfolio value (wallet balance + position values).

        Returns:
            Total portfolio value in USD
        """
        # TODO: Implement real wallet balance check
        # For now, calculate from positions
        wallet_balance_usd = 200.0  # Placeholder (1 SOL @ $200)
        positions_value_usd = self.position_manager.get_total_exposure()

        return wallet_balance_usd + positions_value_usd

    def get_performance_summary(self) -> Dict:
        """
        Get performance summary for live trading.

        Returns:
            Performance metrics dictionary
        """
        stats = self.position_manager.get_statistics()
        portfolio_value = self.get_portfolio_value()

        # Calculate P&L (would need accurate starting balance)
        total_pnl = stats['total_realized_pnl'] + stats['total_unrealized_pnl']

        # Calculate total return percentage
        total_return_percent = 0.0
        if self.starting_balance > 0:
            total_return_percent = ((portfolio_value - self.starting_balance) / self.starting_balance) * 100

        return {
            'portfolio_value': portfolio_value,
            'current_capital': portfolio_value - self.total_invested,  # Free cash
            'invested_capital': self.total_invested,  # In positions
            'total_pnl': total_pnl,
            'total_return_percent': total_return_percent,
            'realized_pnl': stats['total_realized_pnl'],
            'unrealized_pnl': stats['total_unrealized_pnl'],
            'open_positions': stats['open_positions'],
            'total_trades': stats['total_trades'],
            'winning_trades': stats['winning_trades'],
            'losing_trades': stats['losing_trades'],
            'win_rate': stats['win_rate'],
            'timestamp': datetime.now().isoformat()
        }
