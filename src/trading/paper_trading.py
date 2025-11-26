"""
Paper trading engine for testing strategies without real funds.
Now includes Jupiter + Jito simulation for realistic execution modeling.
"""

from typing import Dict, Optional
from datetime import datetime
import json
import os
import uuid
from .position_manager import PositionManager, Trade, Position
from ..blockchain.jupiter_executor import JupiterSwapExecutor
from ..monitoring.logger import get_logger

logger = get_logger(__name__)

# For ML data collection - will be set by main bot
_ml_collector = None
_trade_contexts = {}  # Store analysis context for each trade


def set_ml_collector(collector):
    """Set the ML data collector (called by main bot)."""
    global _ml_collector
    _ml_collector = collector


class PaperTradingEngine:
    """Simulated trading engine for testing."""

    def __init__(self, initial_capital: float = 1000.0, state_file: str = 'paper_trading_state.json'):
        """
        Initialize paper trading engine.

        Args:
            initial_capital: Starting capital in USD
            state_file: Path to state file for persistence
        """
        # Read rug detection settings from environment
        self.rug_detection_enabled = os.getenv('RUG_DETECTION_ENABLED', 'true').lower() == 'true'
        self.stale_price_minutes = float(os.getenv('STALE_PRICE_MINUTES', '5'))
        self.frozen_price_minutes = float(os.getenv('FROZEN_PRICE_MINUTES', '15'))
        self.min_position_liquidity = float(os.getenv('MIN_POSITION_LIQUIDITY', '5000.0'))

        # Read trailing stop settings from environment
        self.use_trailing_stop = os.getenv('USE_TRAILING_STOP', 'true').lower() == 'true'
        self.trailing_stop_percent = float(os.getenv('TRAILING_STOP_PERCENT', '15.0'))

        # Read partial profit taking settings from environment
        self.partial_profit_enabled = os.getenv('PARTIAL_PROFIT_ENABLED', 'false').lower() == 'true'
        self.profit_milestone_100 = float(os.getenv('PROFIT_MILESTONE_100', '25'))
        self.profit_milestone_200 = float(os.getenv('PROFIT_MILESTONE_200', '15'))
        self.profit_milestone_300 = float(os.getenv('PROFIT_MILESTONE_300', '10'))
        self.profit_milestone_400 = float(os.getenv('PROFIT_MILESTONE_400', '10'))
        self.profit_milestone_500 = float(os.getenv('PROFIT_MILESTONE_500', '10'))
        self.profit_milestone_600 = float(os.getenv('PROFIT_MILESTONE_600', '10'))
        self.profit_milestone_700 = float(os.getenv('PROFIT_MILESTONE_700', '10'))

        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        # Read max positions from .env (was hardcoded to 5)
        max_positions = int(os.getenv('MAX_OPEN_POSITIONS', '7'))
        self.position_manager = PositionManager(max_open_positions=max_positions)
        self.total_invested = 0.0

        # Use absolute path for state file
        if not os.path.isabs(state_file):
            self.state_file = os.path.join(os.getcwd(), state_file)
        else:
            self.state_file = state_file

        logger.info(f"State file location: {self.state_file}")

        # Initialize Jupiter executor for realistic simulation
        rpc_url = os.getenv('SOLANA_RPC_URL', 'https://api.mainnet-beta.solana.com')
        use_jito = os.getenv('USE_JITO_BUNDLES', 'true').lower() == 'true'
        self.jupiter_executor = JupiterSwapExecutor(
            rpc_url=rpc_url,
            use_jito=use_jito,
            paper_trading=True  # Always True in paper trading mode
        )
        logger.info(f"✅ Jupiter executor initialized (Paper Mode, Jito: {use_jito})")

        # Load previous state if exists
        self.load_state()

        logger.info(
            f"Paper trading engine initialized: ${self.current_capital:.2f} capital, "
            f"{len(self.position_manager.open_positions)} positions"
        )

        # Log trailing stop settings
        if self.use_trailing_stop:
            logger.info(
                f"📈 Trailing stop ENABLED: {self.trailing_stop_percent:.0f}% below peak "
                f"(exits sooner, captures pumps, avoids rugs)"
            )
        else:
            logger.info(f"🎯 Fixed take profit at {os.getenv('TAKE_PROFIT_PERCENT', '20')}%")

        # Log rug detection settings
        if self.rug_detection_enabled:
            logger.info(
                f"🛡️  Rug protection ENABLED: "
                f"Liquidity threshold ${self.min_position_liquidity:.0f}, "
                f"Stale price timeout {self.stale_price_minutes:.0f} min"
            )
        else:
            logger.warning("⚠️  Rug protection DISABLED")

        # Log partial profit taking settings
        if self.partial_profit_enabled:
            logger.info(
                f"💰 Partial profit taking ENABLED: "
                f"+100%={self.profit_milestone_100:.0f}%, "
                f"+200%={self.profit_milestone_200:.0f}%, "
                f"+300%={self.profit_milestone_300:.0f}%, "
                f"+500%={self.profit_milestone_500:.0f}% "
                f"(locks profits before crashes!)"
            )
        else:
            logger.info("💰 Partial profit taking DISABLED")

    def store_trade_context(self, token_address: str, analysis_data: Dict):
        """
        Store analysis context for ML data collection.

        Args:
            token_address: Token address
            analysis_data: Full analysis data from token analysis
        """
        global _trade_contexts
        _trade_contexts[token_address] = {
            'timestamp': datetime.now(),
            'analysis': analysis_data
        }

    def _record_ml_trade(self, trade: Trade, position: Position, exit_reason: str):
        """
        Record completed trade for ML training.

        Args:
            trade: Trade object
            position: Position object (before closing)
            exit_reason: Reason for exit
        """
        global _ml_collector, _trade_contexts

        if not _ml_collector:
            return  # ML collection not enabled

        try:
            from ..data import MLTradeRecord

            # Get stored analysis context
            context = _trade_contexts.get(trade.token_address, {})
            analysis = context.get('analysis', {})

            # Extract data from analysis
            market_data = analysis.get('market_data', {})
            risk_assessment_raw = analysis.get('risk_assessment', {})
            price_prediction_raw = analysis.get('price_prediction', {})
            sentiment_raw = analysis.get('sentiment', {})
            security = analysis.get('security', {})

            # Handle risk_assessment being either dict or RiskAssessment object
            if hasattr(risk_assessment_raw, '__dict__'):
                # It's an object, convert to dict
                risk_assessment = {
                    'risk_score': getattr(risk_assessment_raw, 'risk_score', 0),
                    'risk_factors': getattr(risk_assessment_raw, 'risk_factors', {})
                }
            else:
                # It's already a dict
                risk_assessment = risk_assessment_raw

            # Handle price_prediction being either dict or PricePrediction object
            if hasattr(price_prediction_raw, '__dict__'):
                price_prediction = {
                    'predicted_direction': getattr(price_prediction_raw, 'predicted_direction', ''),
                    'confidence': getattr(price_prediction_raw, 'confidence', 0),
                    'predicted_change_percent': getattr(price_prediction_raw, 'predicted_change_percent', 0)
                }
            else:
                price_prediction = price_prediction_raw

            # Handle sentiment being either dict or SentimentScore object
            if hasattr(sentiment_raw, '__dict__'):
                sentiment = {
                    'overall_score': getattr(sentiment_raw, 'overall_score', 0.5),
                    'confidence': getattr(sentiment_raw, 'confidence', 0),
                    'coordination_risk': getattr(sentiment_raw, 'coordination_risk', 0)
                }
            else:
                sentiment = sentiment_raw

            # Calculate hold duration
            hold_duration = (trade.timestamp - position.entry_time).total_seconds() / 60  # minutes

            # Create ML trade record
            ml_record = MLTradeRecord(
                trade_id=str(uuid.uuid4()),
                token_address=trade.token_address,
                token_symbol=getattr(trade, 'symbol', None) or getattr(trade, 'token_symbol', None) or trade.token_address[:8],
                action='completed',
                entry_time=position.entry_time,
                exit_time=trade.timestamp,
                hold_duration_minutes=hold_duration,
                entry_price=position.entry_price,
                exit_price=trade.price,
                highest_price_reached=position.highest_price,
                lowest_price_reached=position.entry_price,  # We don't track lowest (could add)
                amount_usd=trade.amount_usd,
                quantity=trade.quantity,
                position_size_percent_of_portfolio=(trade.amount_usd / self.get_portfolio_value() * 100) if self.get_portfolio_value() > 0 else 0,
                pnl_usd=trade.pnl,
                pnl_percent=trade.pnl_percent,
                win=trade.pnl > 0,
                exit_reason=exit_reason,
                # Market conditions at entry
                entry_liquidity_usd=market_data.get('liquidity_usd', 0),
                entry_volume_24h=market_data.get('volume_24h', 0),
                entry_price_change_24h=market_data.get('price_change_24h', 0),
                entry_holder_count=market_data.get('holder_count', 0),
                entry_market_cap=market_data.get('market_cap', 0),
                # Market conditions at exit (we don't have this - could fetch)
                exit_liquidity_usd=position.current_liquidity,
                exit_volume_24h=0,
                exit_price_change_24h=0,
                # Token characteristics
                token_age_hours=security.get('token_age_hours', 0),
                is_mintable=security.get('is_mintable', False),
                has_freeze_authority=security.get('has_freeze_authority', False),
                is_verified=security.get('is_verified', False),
                ownership_renounced=security.get('ownership_renounced', False),
                # Risk scores
                overall_risk_score=risk_assessment.get('risk_score', 0),
                liquidity_risk=risk_assessment.get('risk_factors', {}).get('liquidity', 0),
                security_risk=risk_assessment.get('risk_factors', {}).get('security', 0),
                volatility_risk=risk_assessment.get('risk_factors', {}).get('volatility', 0),
                sentiment_risk=risk_assessment.get('risk_factors', {}).get('sentiment', 0),
                age_risk=risk_assessment.get('risk_factors', {}).get('age', 0),
                # Signals & predictions
                sentiment_score=sentiment.get('overall_score', 0.5),
                sentiment_confidence=sentiment.get('confidence', 0),
                coordination_risk=sentiment.get('coordination_risk', 0),
                price_prediction_direction=price_prediction.get('predicted_direction', ''),
                price_prediction_confidence=price_prediction.get('confidence', 0),
                predicted_change_percent=price_prediction.get('predicted_change_percent', 0),
                # Portfolio context
                portfolio_value_at_entry=self.get_portfolio_value(),
                open_positions_count=len(self.position_manager.open_positions),
                daily_trades_before_this=len([t for t in self.position_manager.closed_trades if t.timestamp.date() == datetime.now().date()]),
                # Execution
                execution_method='jupiter',
                # Trailing stop
                used_trailing_stop=position.use_trailing_stop,
                trailing_stop_percent=position.trailing_stop_percent,
                max_drawdown_from_peak_percent=((position.highest_price - trade.price) / position.highest_price * 100) if position.highest_price > 0 else 0,
                # Partial profits
                is_partial_sell=False,  # Could enhance this
                milestones_hit=list(position.milestones_hit),
                partial_sell_count=len(position.milestones_hit),
                # Metadata
                paper_trading=True
            )

            # Record to ML collector
            _ml_collector.record_trade(ml_record)
            logger.debug(f"📊 ML trade recorded: {trade.symbol or trade.token_address[:8]} ({trade.pnl_percent:+.2f}%)")

            # Clean up context
            if trade.token_address in _trade_contexts:
                del _trade_contexts[trade.token_address]

        except Exception as e:
            logger.error(f"❌ Error recording ML trade: {e}", exc_info=True)

    async def execute_buy(
        self,
        token_address: str,
        amount_usd: float,
        price: float,
        stop_loss: float,
        take_profit: float,
        use_trailing_stop: Optional[bool] = None,
        trailing_stop_percent: Optional[float] = None,
        analysis_data: Optional[Dict] = None
    ) -> Dict:
        """
        Execute a simulated buy order.

        Args:
            token_address: Token contract address
            amount_usd: Amount to invest in USD
            price: Current token price
            stop_loss: Stop loss price
            take_profit: Take profit price (ignored if using trailing stop)
            use_trailing_stop: Whether to use trailing stop (reads from .env if None)
            trailing_stop_percent: Percent to trail below peak (reads from .env if None)

        Returns:
            Execution result dictionary
        """
        # Use .env settings if not explicitly provided
        if use_trailing_stop is None:
            use_trailing_stop = self.use_trailing_stop
        if trailing_stop_percent is None:
            trailing_stop_percent = self.trailing_stop_percent
        # Check if we have enough capital
        if amount_usd > self.current_capital:
            logger.warning(
                f"Insufficient capital: ${self.current_capital:.2f} < ${amount_usd:.2f}"
            )
            return {
                'status': 'failed',
                'reason': 'insufficient_capital',
                'available_capital': self.current_capital
            }

        # Check if we can open more positions
        if not self.position_manager.can_open_position():
            logger.warning("Max positions reached")
            return {
                'status': 'failed',
                'reason': 'max_positions_reached'
            }

        # Store analysis context for ML data collection
        if analysis_data:
            self.store_trade_context(token_address, analysis_data)

        # Open position
        position = self.position_manager.open_position(
            token_address=token_address,
            entry_price=price,
            amount_usd=amount_usd,
            stop_loss=stop_loss,
            take_profit=take_profit,
            use_trailing_stop=use_trailing_stop,
            trailing_stop_percent=trailing_stop_percent
        )

        if not position:
            return {
                'status': 'failed',
                'reason': 'position_creation_failed'
            }

        # Deduct from capital
        self.current_capital -= amount_usd
        self.total_invested += amount_usd

        mode_str = f"trailing {trailing_stop_percent}%" if use_trailing_stop else f"TP ${take_profit:.8f}"
        logger.info(
            f"[PAPER] BUY {token_address[:8]}... "
            f"@ ${price:.8f}, size: ${amount_usd:.2f}, "
            f"{mode_str}, capital: ${self.current_capital:.2f}"
        )

        # Save state after trade
        self.save_state()

        return {
            'status': 'success',
            'action': 'buy',
            'token_address': token_address,
            'price': price,
            'amount_usd': amount_usd,
            'quantity': position.quantity,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'use_trailing_stop': use_trailing_stop,
            'trailing_stop_percent': trailing_stop_percent,
            'remaining_capital': self.current_capital,
            'timestamp': datetime.now().isoformat()
        }

    async def execute_sell(
        self,
        token_address: str,
        price: float,
        reason: str = 'manual'
    ) -> Dict:
        """
        Execute a simulated sell order.

        Args:
            token_address: Token contract address
            price: Current token price
            reason: Reason for selling

        Returns:
            Execution result dictionary
        """
        # Check if position exists
        position = self.position_manager.get_position(token_address)
        if not position:
            logger.warning(f"No position to sell for {token_address}")
            return {
                'status': 'failed',
                'reason': 'no_position'
            }

        # Record position state before closing (for ML)
        position_snapshot = Position(
            token_address=position.token_address,
            entry_price=position.entry_price,
            current_price=position.current_price,
            amount_usd=position.amount_usd,
            quantity=position.quantity,
            entry_time=position.entry_time,
            stop_loss=position.stop_loss,
            take_profit=position.take_profit,
            use_trailing_stop=position.use_trailing_stop,
            trailing_stop_percent=position.trailing_stop_percent,
            highest_price=position.highest_price,
            trailing_stop_price=position.trailing_stop_price,
            last_price_update=position.last_price_update,
            current_liquidity=position.current_liquidity,
            price_update_failures=position.price_update_failures,
            initial_quantity=position.initial_quantity,
            milestones_hit=position.milestones_hit.copy(),
            symbol=position.symbol
        )

        # Close position
        trade = self.position_manager.close_position(
            token_address=token_address,
            exit_price=price,
            reason=reason
        )

        if not trade:
            return {
                'status': 'failed',
                'reason': 'close_failed'
            }

        # Record trade for ML training
        self._record_ml_trade(trade, position_snapshot, reason)

        # Add proceeds to capital
        proceeds = trade.amount_usd
        capital_before = self.current_capital
        self.current_capital += proceeds
        self.total_invested -= position.amount_usd

        logger.info(
            f"[PAPER] SELL {token_address[:8]}... "
            f"@ ${price:.8f}, proceeds: ${proceeds:.2f}, "
            f"capital: ${capital_before:.2f} → ${self.current_capital:.2f}, "
            f"PnL: ${trade.pnl:.2f} ({trade.pnl_percent:+.1f}%)"
        )

        # Save state after trade
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
            'reason': reason,
            'remaining_capital': self.current_capital,
            'timestamp': datetime.now().isoformat()
        }

    async def update_prices(self, price_updates: Dict[str, float], liquidity_data: Dict[str, float] = None):
        """
        Update positions with current prices and check stop loss/take profit/trailing stop.

        Args:
            price_updates: Dictionary of token_address -> current_price
            liquidity_data: Dictionary of token_address -> liquidity_usd (optional)
        """
        if liquidity_data is None:
            liquidity_data = {}

        # First, update all prices so we have fresh timestamps
        # (prevents false positives when bot restarts after being offline)
        for token_address, current_price in price_updates.items():
            if token_address not in self.position_manager.open_positions:
                continue

            liquidity = liquidity_data.get(token_address, 0.0)

            # Update position price and liquidity (updates last_price_update timestamp)
            self.position_manager.update_position_price(token_address, current_price, liquidity)

        # NOW check for dead/rugged positions (after applying fresh data)
        # This prevents false positives when restarting after being offline
        if self.rug_detection_enabled:
            dead_positions = self.position_manager.get_dead_positions(
                stale_minutes=self.stale_price_minutes,
                min_liquidity=self.min_position_liquidity,
                freeze_minutes=self.frozen_price_minutes
            )
        else:
            dead_positions = []

        for token_address in dead_positions:
            position = self.position_manager.get_position(token_address)
            if position:
                # Use current price if available, otherwise assume rugged ($0)
                exit_price = position.current_price if position.current_price > 0 else 0.00000001
                potential_loss = position.amount_usd - (position.quantity * exit_price)

                logger.error(
                    f"💀 AUTO-CLOSING DEAD TOKEN: {token_address[:8]}... "
                    f"Entry: ${position.entry_price:.8f}, "
                    f"Last known: ${position.current_price:.8f}, "
                    f"Exit at: ${exit_price:.8f}, "
                    f"Potential loss: ${potential_loss:.2f}"
                )
                await self.execute_sell(token_address, exit_price, reason='low_liquidity')

        # Check for partial profit milestones (before stop loss/take profit checks)
        if self.partial_profit_enabled:
            for token_address in list(self.position_manager.open_positions.keys()):
                position = self.position_manager.get_position(token_address)
                if not position or position.initial_quantity == 0:
                    continue

                milestone = position.check_profit_milestone()
                if milestone:
                    # Determine sell percentage based on milestone
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
                        # Calculate quantity to sell (percentage of INITIAL quantity, not current)
                        sell_quantity = (sell_pct / 100) * position.initial_quantity
                        sell_quantity = min(sell_quantity, position.quantity)  # Don't sell more than we have

                        if sell_quantity > 0:
                            # Execute partial sell
                            sell_value = sell_quantity * position.current_price
                            logger.info(
                                f"💰 PARTIAL PROFIT at +{milestone}%: {token_address[:8]}... "
                                f"Selling {sell_pct}% ({sell_quantity:.2f} tokens) = ${sell_value:.2f}"
                            )

                            # Reduce position quantity AND amount_usd to reflect smaller position
                            position.quantity -= sell_quantity
                            position.amount_usd = position.quantity * position.entry_price  # Update cost basis
                            position.milestones_hit.add(milestone)

                            # Add proceeds to capital
                            self.current_capital += sell_value
                            # Reduce total_invested since we sold part of the position
                            self.total_invested -= (sell_quantity * position.entry_price)

                            # Calculate profit on this partial sell
                            cost_basis = (position.entry_price * sell_quantity)
                            partial_profit = sell_value - cost_basis

                            logger.info(
                                f"💵 Locked in ${partial_profit:.2f} profit, "
                                f"Remaining: {position.quantity:.2f} tokens (${position.amount_usd:.2f} cost basis)"
                            )

                            # Save state after partial sell
                            self.save_state()

        # Now check stop loss/take profit/trailing stop for remaining positions
        for token_address in list(self.position_manager.open_positions.keys()):
            # Get current position price (don't use undefined variable!)
            position = self.position_manager.get_position(token_address)
            if not position:
                continue

            current_price = position.current_price

            # Check stop loss (regular stop loss, for downside protection)
            if self.position_manager.check_stop_loss(token_address):
                logger.info(f"Stop loss triggered for {token_address[:8]}...")
                await self.execute_sell(token_address, current_price, reason='stop_loss')

            # Check trailing stop (locks in profits)
            elif self.position_manager.check_trailing_stop(token_address):
                await self.execute_sell(token_address, current_price, reason='trailing_stop')

            # Check take profit (only if not using trailing stop)
            elif self.position_manager.check_take_profit(token_address):
                logger.info(f"Take profit triggered for {token_address[:8]}...")
                await self.execute_sell(token_address, current_price, reason='take_profit')

    def get_portfolio_value(self) -> float:
        """
        Get current total portfolio value.

        Returns:
            Portfolio value in USD
        """
        positions_value = sum(
            pos.quantity * pos.current_price
            for pos in self.position_manager.get_all_positions()
        )
        return self.current_capital + positions_value

    def get_performance_summary(self) -> Dict:
        """
        Get comprehensive performance summary.

        Returns:
            Dictionary with performance metrics
        """
        portfolio_value = self.get_portfolio_value()
        total_pnl = portfolio_value - self.initial_capital
        total_return = (total_pnl / self.initial_capital * 100) if self.initial_capital > 0 else 0

        stats = self.position_manager.get_statistics()

        return {
            'initial_capital': self.initial_capital,
            'current_capital': self.current_capital,
            'invested_capital': self.total_invested,
            'portfolio_value': portfolio_value,
            'total_pnl': total_pnl,
            'total_return_percent': total_return,
            'realized_pnl': stats['total_realized_pnl'],
            'unrealized_pnl': stats['total_unrealized_pnl'],
            'open_positions': stats['open_positions'],
            'total_trades': stats['total_trades'],
            'winning_trades': stats['winning_trades'],
            'losing_trades': stats['losing_trades'],
            'win_rate': stats['win_rate'],
            'avg_win': stats['avg_win'],
            'avg_loss': stats['avg_loss'],
            'timestamp': datetime.now().isoformat()
        }

    def reset(self):
        """Reset the paper trading engine to initial state."""
        self.current_capital = self.initial_capital
        self.total_invested = 0.0
        # Use same max_positions from .env as initialization
        max_positions = int(os.getenv('MAX_OPEN_POSITIONS', '7'))
        self.position_manager = PositionManager(max_open_positions=max_positions)
        logger.info("Paper trading engine reset")

    def save_state(self):
        """Save current state to file for persistence."""
        try:
            state = {
                'initial_capital': self.initial_capital,
                'current_capital': self.current_capital,
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
                    'current_liquidity': pos.current_liquidity,
                    'price_update_failures': pos.price_update_failures,
                    'initial_quantity': pos.initial_quantity,  # Partial profit tracking
                    'milestones_hit': list(pos.milestones_hit)  # Convert set to list for JSON
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
                f"💾 State saved: ${self.current_capital:.2f} capital, "
                f"{len(self.position_manager.open_positions)} positions → {self.state_file}"
            )

        except Exception as e:
            logger.error(f"❌ Error saving state to {self.state_file}: {e}", exc_info=True)

    def load_state(self):
        """Load state from file."""
        try:
            if not os.path.exists(self.state_file):
                logger.info(f"📝 No previous state file found at {self.state_file}, starting fresh")
                return

            logger.info(f"📂 Loading state from {self.state_file}...")

            with open(self.state_file, 'r') as f:
                state = json.load(f)

            # Restore capital
            self.initial_capital = state.get('initial_capital', self.initial_capital)
            self.current_capital = state.get('current_capital', self.current_capital)
            self.total_invested = state.get('total_invested', 0.0)

            # Restore positions
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
                    use_trailing_stop=pos_data.get('use_trailing_stop', self.use_trailing_stop),
                    trailing_stop_percent=pos_data.get('trailing_stop_percent', self.trailing_stop_percent),
                    highest_price=pos_data.get('highest_price', pos_data['entry_price']),
                    trailing_stop_price=pos_data.get('trailing_stop_price', pos_data['stop_loss']),
                    last_price_update=datetime.fromisoformat(pos_data.get('last_price_update', pos_data['entry_time'])),
                    current_liquidity=pos_data.get('current_liquidity', 0.0),
                    price_update_failures=pos_data.get('price_update_failures', 0),
                    initial_quantity=pos_data.get('initial_quantity', pos_data['quantity']),  # Partial profit tracking
                    milestones_hit=set(pos_data.get('milestones_hit', []))  # Convert list back to set
                )
                self.position_manager.open_positions[token_addr] = position
                pnl_pct = position.unrealized_pnl_percent
                mode = "🔄 trailing" if position.use_trailing_stop else "🎯 fixed TP"
                logger.info(f"   ✓ Restored position: {token_addr[:8]}... ({pnl_pct:+.2f}%, {mode})")

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
                f"✅ State loaded: ${self.current_capital:.2f} capital, "
                f"{len(self.position_manager.open_positions)} positions, "
                f"{len(self.position_manager.closed_trades)} trades"
            )

        except Exception as e:
            logger.error(f"❌ Error loading state from {self.state_file}: {e}", exc_info=True)
            logger.warning("⚠️  Starting with fresh state due to load error")

    async def health_check(self) -> bool:
        """
        Health check for paper trading engine.

        Returns:
            True if healthy
        """
        return True  # Paper trading is always healthy
