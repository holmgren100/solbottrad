"""
Live Trading Engine for real Solana swaps via Jupiter.
Manages real wallet, executes actual trades, tracks on-chain positions.
"""

import asyncio
import os
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

        # Partial profit taking settings (from environment)
        self.partial_profit_enabled = os.getenv('PARTIAL_PROFIT_ENABLED', 'true').lower() == 'true'
        self.profit_milestone_100 = float(os.getenv('PROFIT_MILESTONE_100', '15'))
        self.profit_milestone_200 = float(os.getenv('PROFIT_MILESTONE_200', '20'))
        self.profit_milestone_300 = float(os.getenv('PROFIT_MILESTONE_300', '15'))
        self.profit_milestone_400 = float(os.getenv('PROFIT_MILESTONE_400', '10'))
        self.profit_milestone_500 = float(os.getenv('PROFIT_MILESTONE_500', '10'))
        self.profit_milestone_600 = float(os.getenv('PROFIT_MILESTONE_600', '10'))
        self.profit_milestone_700 = float(os.getenv('PROFIT_MILESTONE_700', '10'))

        logger.info(
            f"✅ LiveTradingEngine initialized - "
            f"Wallet: {jupiter_executor.wallet.get_public_key()[:8]}..."
        )

        if self.partial_profit_enabled:
            logger.info(
                f"💰 Partial profit taking ENABLED: "
                f"+100%={self.profit_milestone_100:.0f}%, "
                f"+200%={self.profit_milestone_200:.0f}%, "
                f"+300%={self.profit_milestone_300:.0f}%, "
                f"+400%={self.profit_milestone_400:.0f}%, "
                f"+500%={self.profit_milestone_500:.0f}%, "
                f"+600%={self.profit_milestone_600:.0f}%, "
                f"+700%={self.profit_milestone_700:.0f}%"
            )
        else:
            logger.info("💰 Partial profit taking DISABLED")

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
        reason: str = 'manual',
        amount_tokens: Optional[float] = None
    ) -> Dict:
        """
        Execute a real sell order on-chain.

        Args:
            token_address: Token to sell
            price: Current token price
            reason: Reason for selling
            amount_tokens: Optional - amount of tokens to sell (if None, sells full position)

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

            # Determine sell amount
            if amount_tokens is None:
                # Full sell
                sell_quantity = position.quantity
                is_partial = False
            else:
                # Partial sell
                sell_quantity = min(amount_tokens, position.quantity)
                is_partial = (sell_quantity < position.quantity)

            logger.info(
                f"🔴 [LIVE] {'PARTIAL ' if is_partial else ''}SELL: "
                f"{sell_quantity:.4f} {token_address[:8]}... @ ${price:.8f} ({reason})"
            )

            # Execute real swap via Jupiter
            swap_result = await self.jupiter_executor.sell_token(
                token_mint=token_address,
                amount_tokens=sell_quantity,
                slippage_percent=5.0
            )

            if not swap_result.get('success'):
                logger.error(f"❌ Sell swap failed: {swap_result.get('error', 'Unknown')}")
                return {
                    'status': 'failed',
                    'reason': swap_result.get('error', 'swap_failed')
                }

            # Calculate profit on this sell
            cost_basis = position.entry_price * sell_quantity
            sell_value = price * sell_quantity
            pnl = sell_value - cost_basis
            pnl_percent = ((price - position.entry_price) / position.entry_price) * 100 if position.entry_price > 0 else 0

            if is_partial:
                # Partial sell - update position
                position.quantity -= sell_quantity
                position.amount_usd = position.quantity * position.entry_price
                self.total_invested -= cost_basis

                logger.info(
                    f"✅ [LIVE] PARTIAL SELL CONFIRMED: {sell_quantity:.4f} tokens → {swap_result.get('output_amount', 0):.6f} SOL, "
                    f"P&L: ${pnl:.2f} ({pnl_percent:+.1f}%), "
                    f"Remaining: {position.quantity:.4f} tokens, "
                    f"Signature: {swap_result.get('signature', 'N/A')[:16]}..."
                )

                return {
                    'status': 'success',
                    'action': 'partial_sell',
                    'token_address': token_address,
                    'price': price,
                    'quantity': sell_quantity,
                    'pnl': pnl,
                    'pnl_percent': pnl_percent,
                    'signature': swap_result.get('signature'),
                    'fees': swap_result.get('fees', {}),
                    'reason': reason,
                    'remaining_quantity': position.quantity,
                    'timestamp': datetime.now().isoformat()
                }
            else:
                # Full sell - close position
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

        # Check for dead/rugged positions (low liquidity, frozen price, stale data)
        dead_positions = self.position_manager.get_dead_positions(
            stale_minutes=10,
            min_liquidity=8000.0,  # $8k minimum liquidity to sell
            freeze_minutes=5
        )

        for token_address in dead_positions:
            position = self.position_manager.get_position(token_address)
            if position:
                # Use current price if available, otherwise assume minimal value
                exit_price = position.current_price if position.current_price > 0 else 0.00000001

                logger.error(
                    f"💀 [LIVE] DEAD TOKEN DETECTED: {token_address[:8]}... "
                    f"Entry: ${position.entry_price:.8f}, "
                    f"Current: ${position.current_price:.8f}, "
                    f"Liquidity: ${position.current_liquidity:.0f}"
                )
                await self.execute_sell(token_address, exit_price, reason='low_liquidity')

        # Check for profit milestones (partial profit-taking)
        if self.partial_profit_enabled:
            for token_address in list(self.position_manager.open_positions.keys()):
                position = self.position_manager.get_position(token_address)
                if not position or position.initial_quantity == 0:
                    continue

                # Check if we've hit a new profit milestone
                milestone = position.check_profit_milestone()
                if milestone:
                    # Map milestone to sell percentage
                    sell_pct = 0
                    if milestone == 100:
                        sell_pct = self.profit_milestone_100
                    elif milestone == 200:
                        sell_pct = self.profit_milestone_200
                    elif milestone == 300:
                        sell_pct = self.profit_milestone_300
                    elif milestone == 400:
                        sell_pct = self.profit_milestone_400
                    elif milestone == 500:
                        sell_pct = self.profit_milestone_500
                    elif milestone == 600:
                        sell_pct = self.profit_milestone_600
                    elif milestone == 700:
                        sell_pct = self.profit_milestone_700

                    if sell_pct > 0:
                        # Calculate quantity to sell (percentage of INITIAL quantity)
                        sell_quantity = (sell_pct / 100) * position.initial_quantity
                        sell_quantity = min(sell_quantity, position.quantity)  # Don't sell more than we have

                        if sell_quantity > 0:
                            sell_value = sell_quantity * position.current_price

                            logger.info(
                                f"💰 [LIVE] PROFIT MILESTONE +{milestone}%: {token_address[:8]}... "
                                f"Selling {sell_pct:.0f}% ({sell_quantity:.4f} tokens) = ${sell_value:.2f}"
                            )

                            # Execute partial sell
                            await self.execute_sell(
                                token_address=token_address,
                                price=position.current_price,
                                reason=f'milestone_{milestone}',
                                amount_tokens=sell_quantity
                            )

                            # Mark milestone as hit
                            position.milestones_hit.add(milestone)

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

        return {
            'portfolio_value': portfolio_value,
            'total_invested': self.total_invested,
            'total_pnl': total_pnl,
            'realized_pnl': stats['total_realized_pnl'],
            'unrealized_pnl': stats['total_unrealized_pnl'],
            'open_positions': stats['open_positions'],
            'total_trades': stats['total_trades'],
            'winning_trades': stats['winning_trades'],
            'losing_trades': stats['losing_trades'],
            'win_rate': stats['win_rate'],
            'timestamp': datetime.now().isoformat()
        }
