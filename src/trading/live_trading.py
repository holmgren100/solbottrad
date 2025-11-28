"""
Live Trading Engine for real Solana swaps via Jupiter.
Manages real wallet, executes actual trades, tracks on-chain positions.
"""

import asyncio
import json
import os
from typing import Dict, Optional
from datetime import datetime
from .position_manager import PositionManager, Position, Trade
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
        max_open_positions: int = 12,
        state_file: str = "live_trading_state.json"
    ):
        """
        Initialize live trading engine.

        Args:
            jupiter_executor: Jupiter executor configured with wallet
            position_manager: Optional position manager (creates new if not provided)
            max_open_positions: Maximum simultaneous positions
            state_file: Path to state file for position persistence
        """
        self.jupiter_executor = jupiter_executor
        self.position_manager = position_manager or PositionManager(max_open_positions)
        self.state_file = state_file

        # Trading state (tracked separately from wallet balance)
        self.starting_balance = 0.0  # Will be set on first balance check
        self.total_invested = 0.0  # Currently invested in open positions

        logger.info(
            f"✅ LiveTradingEngine initialized - "
            f"Wallet: {jupiter_executor.wallet.get_public_key()[:8]}..."
        )

        # Load previous positions if any
        self.load_state()

    async def get_wallet_balance(self) -> float:
        """
        Get current SOL balance from wallet.

        Returns:
            SOL balance in SOL (not lamports)
        """
        try:
            import aiohttp

            # Get wallet public key
            wallet_pubkey = str(self.jupiter_executor.wallet.get_public_key())

            # Make RPC call to get balance
            payload = {
                'jsonrpc': '2.0',
                'id': 1,
                'method': 'getBalance',
                'params': [wallet_pubkey]
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.jupiter_executor.rpc_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        if 'result' in result and 'value' in result['result']:
                            balance_lamports = result['result']['value']
                            balance_sol = balance_lamports / 1e9  # Convert to SOL
                            logger.debug(f"💰 Wallet balance: {balance_sol:.6f} SOL")
                            return balance_sol

            logger.error("Failed to get wallet balance from RPC")
            return 0.0

        except Exception as e:
            logger.error(f"Error getting wallet balance: {e}")
            return 0.0

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

            # Save state after successful buy
            self.save_state()

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

            # Save state after successful sell
            self.save_state()

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

    def save_state(self):
        """Save current positions and state to file for persistence."""
        try:
            state = {
                'starting_balance': self.starting_balance,
                'total_invested': self.total_invested,
                'positions': {},
                'trades': []
            }

            # Save positions
            for token_addr, pos in self.position_manager.open_positions.items():
                state['positions'][token_addr] = {
                    'token_address': pos.token_address,
                    'entry_price': pos.entry_price,
                    'current_price': pos.current_price,
                    'amount_usd': pos.amount_usd,
                    'quantity': pos.quantity,
                    'stop_loss': pos.stop_loss,
                    'take_profit': pos.take_profit,
                    'entry_time': pos.entry_time.isoformat(),
                    'use_trailing_stop': pos.use_trailing_stop,
                    'trailing_stop_percent': pos.trailing_stop_percent,
                    'highest_price': pos.highest_price,
                    'trailing_stop_price': pos.trailing_stop_price,
                    'last_price_update': pos.last_price_update.isoformat(),
                    'last_price_change': pos.last_price_change.isoformat(),
                    'last_known_price': pos.last_known_price,
                    'current_liquidity': pos.current_liquidity,
                    'price_update_failures': pos.price_update_failures,
                    'initial_quantity': pos.initial_quantity,
                    'milestones_hit': list(pos.milestones_hit)
                }

            # Save recent trades (last 100)
            for trade in self.position_manager.closed_trades[-100:]:
                state['trades'].append({
                    'token_address': trade.token_address,
                    'action': trade.action,
                    'price': trade.price,
                    'amount_usd': trade.amount_usd,
                    'quantity': trade.quantity,
                    'pnl': trade.pnl,
                    'pnl_percent': trade.pnl_percent,
                    'timestamp': trade.timestamp.isoformat()
                })

            # Write to file
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)

            logger.info(
                f"💾 Live trading state saved: "
                f"{len(self.position_manager.open_positions)} positions → {self.state_file}"
            )

        except Exception as e:
            logger.error(f"❌ Error saving live trading state: {e}", exc_info=True)

    def load_state(self):
        """Load positions and state from file."""
        try:
            if not os.path.exists(self.state_file):
                logger.info(f"📝 No previous state file, starting fresh")
                return

            logger.info(f"📂 Loading live trading state from {self.state_file}...")

            with open(self.state_file, 'r') as f:
                state = json.load(f)

            # Restore trading state
            self.starting_balance = state.get('starting_balance', 0.0)
            self.total_invested = state.get('total_invested', 0.0)

            # Restore positions
            restored_count = 0
            for token_addr, pos_data in state.get('positions', {}).items():
                position = Position(
                    token_address=pos_data['token_address'],
                    entry_price=pos_data['entry_price'],
                    current_price=pos_data['current_price'],
                    amount_usd=pos_data['amount_usd'],
                    quantity=pos_data['quantity'],
                    entry_time=datetime.fromisoformat(pos_data['entry_time']),
                    stop_loss=pos_data['stop_loss'],
                    take_profit=pos_data['take_profit'],
                    use_trailing_stop=pos_data.get('use_trailing_stop', True),
                    trailing_stop_percent=pos_data.get('trailing_stop_percent', 0.10),
                    highest_price=pos_data.get('highest_price', pos_data['entry_price']),
                    trailing_stop_price=pos_data.get('trailing_stop_price', pos_data['stop_loss']),
                    last_price_update=datetime.fromisoformat(pos_data.get('last_price_update', pos_data['entry_time'])),
                    last_price_change=datetime.fromisoformat(pos_data.get('last_price_change', pos_data['entry_time'])),
                    last_known_price=pos_data.get('last_known_price', pos_data['entry_price']),
                    current_liquidity=pos_data.get('current_liquidity', 0.0),
                    price_update_failures=pos_data.get('price_update_failures', 0),
                    initial_quantity=pos_data.get('initial_quantity', pos_data['quantity']),
                    milestones_hit=set(pos_data.get('milestones_hit', []))
                )
                self.position_manager.open_positions[token_addr] = position
                pnl_pct = position.unrealized_pnl_percent
                restored_count += 1
                logger.info(f"   ✓ Restored: {token_addr[:8]}... ({pnl_pct:+.2f}%)")

            # Restore trades
            for trade_data in state.get('trades', []):
                trade = Trade(
                    token_address=trade_data['token_address'],
                    action=trade_data['action'],
                    price=trade_data['price'],
                    amount_usd=trade_data['amount_usd'],
                    quantity=trade_data['quantity'],
                    timestamp=datetime.fromisoformat(trade_data['timestamp']),
                    pnl=trade_data.get('pnl', 0.0),
                    pnl_percent=trade_data.get('pnl_percent', 0.0)
                )
                self.position_manager.closed_trades.append(trade)

            logger.info(
                f"✅ Loaded {restored_count} positions, "
                f"{len(state.get('trades', []))} trades from {self.state_file}"
            )

        except Exception as e:
            logger.error(f"❌ Error loading live trading state: {e}", exc_info=True)
