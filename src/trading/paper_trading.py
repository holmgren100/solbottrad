import logging
from typing import Dict, Optional, List
from datetime import datetime
from dataclasses import dataclass, asdict
import json
import os

@dataclass
class Position:
    token_address: str
    symbol: str
    entry_price: float
    current_price: float
    quantity: float
    position_size_usd: float
    stop_loss: float
    take_profit: float
    entry_time: datetime
    pnl: float = 0.0
    pnl_percent: float = 0.0

    def to_dict(self):
        data = asdict(self)
        data['entry_time'] = self.entry_time.isoformat()
        return data

@dataclass
class Trade:
    timestamp: datetime
    action: str  # 'buy' or 'sell'
    token_address: str
    symbol: str
    price: float
    quantity: float
    total_usd: float
    fees: float = 0.0

    def to_dict(self):
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data

class PaperTradingEngine:
    """Simulated trading engine for paper trading"""

    def __init__(self, initial_capital: float = 1000.0, stop_loss_percent: float = 5.0, take_profit_percent: float = 10.0, state_file: str = 'paper_trading_state.json'):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions: Dict[str, Position] = {}
        self.trade_history: List[Trade] = []
        self.stop_loss_percent = stop_loss_percent
        self.take_profit_percent = take_profit_percent
        self.logger = logging.getLogger('trading_bot.paper_trading')
        self.state_file = state_file

        # Load previous state if exists
        self.load_state()

        self.logger.info(f"Paper trading initialized with ${self.cash:.2f} cash, {len(self.positions)} positions")

    async def execute_buy(self, token_address: str, symbol: str, price: float, amount_usd: float) -> Dict:
        """Execute a paper buy order"""
        try:
            # Check if we have enough cash
            if amount_usd > self.cash:
                self.logger.warning(f"Insufficient cash: ${self.cash:.2f} < ${amount_usd:.2f}")
                return {'success': False, 'reason': 'Insufficient funds'}

            # Check if position already exists
            if token_address in self.positions:
                self.logger.warning(f"Position already exists for {symbol}")
                return {'success': False, 'reason': 'Position already exists'}

            # Calculate quantity
            quantity = amount_usd / price
            fees = amount_usd * 0.001  # 0.1% fee
            total_cost = amount_usd + fees

            # Calculate stop loss and take profit
            stop_loss = price * (1 - self.stop_loss_percent / 100)
            take_profit = price * (1 + self.take_profit_percent / 100)

            # Create position
            position = Position(
                token_address=token_address,
                symbol=symbol,
                entry_price=price,
                current_price=price,
                quantity=quantity,
                position_size_usd=amount_usd,
                stop_loss=stop_loss,
                take_profit=take_profit,
                entry_time=datetime.now()
            )

            # Record trade
            trade = Trade(
                timestamp=datetime.now(),
                action='buy',
                token_address=token_address,
                symbol=symbol,
                price=price,
                quantity=quantity,
                total_usd=amount_usd,
                fees=fees
            )

            # Update state
            self.cash -= total_cost
            self.positions[token_address] = position
            self.trade_history.append(trade)

            self.logger.info(f"PAPER BUY: {quantity:.4f} {symbol} @ ${price:.8f} = ${amount_usd:.2f}")
            self.logger.info(f"  Stop Loss: ${stop_loss:.8f} | Take Profit: ${take_profit:.8f}")
            self.logger.info(f"  Remaining Cash: ${self.cash:.2f}")

            # Save state
            self.save_state()

            return {
                'success': True,
                'position': position.to_dict(),
                'trade': trade.to_dict(),
                'remaining_cash': self.cash
            }

        except Exception as e:
            self.logger.error(f"Error executing paper buy: {e}")
            return {'success': False, 'reason': str(e)}

    async def execute_sell(self, token_address: str, price: float) -> Dict:
        """Execute a paper sell order"""
        try:
            # Check if position exists
            if token_address not in self.positions:
                self.logger.warning(f"No position found for {token_address}")
                return {'success': False, 'reason': 'No position found'}

            position = self.positions[token_address]

            # Calculate proceeds
            proceeds = position.quantity * price
            fees = proceeds * 0.001  # 0.1% fee
            net_proceeds = proceeds - fees

            # Calculate P&L
            pnl = net_proceeds - position.position_size_usd
            pnl_percent = (pnl / position.position_size_usd) * 100

            # Record trade
            trade = Trade(
                timestamp=datetime.now(),
                action='sell',
                token_address=token_address,
                symbol=position.symbol,
                price=price,
                quantity=position.quantity,
                total_usd=proceeds,
                fees=fees
            )

            # Update state
            self.cash += net_proceeds
            del self.positions[token_address]
            self.trade_history.append(trade)

            self.logger.info(f"PAPER SELL: {position.quantity:.4f} {position.symbol} @ ${price:.8f} = ${proceeds:.2f}")
            self.logger.info(f"  P&L: ${pnl:.2f} ({pnl_percent:+.2f}%)")
            self.logger.info(f"  New Cash Balance: ${self.cash:.2f}")

            # Save state
            self.save_state()

            return {
                'success': True,
                'trade': trade.to_dict(),
                'pnl': pnl,
                'pnl_percent': pnl_percent,
                'new_cash': self.cash
            }

        except Exception as e:
            self.logger.error(f"Error executing paper sell: {e}")
            return {'success': False, 'reason': str(e)}

    def update_position_prices(self, token_address: str, current_price: float):
        """Update current price for a position"""
        if token_address in self.positions:
            position = self.positions[token_address]
            position.current_price = current_price

            # Calculate P&L
            current_value = position.quantity * current_price
            position.pnl = current_value - position.position_size_usd
            position.pnl_percent = (position.pnl / position.position_size_usd) * 100

    def get_portfolio_value(self) -> float:
        """Get total portfolio value (cash + positions)"""
        positions_value = sum(p.quantity * p.current_price for p in self.positions.values())
        return self.cash + positions_value

    def save_state(self):
        """Save current state to file"""
        try:
            state = {
                'cash': self.cash,
                'initial_capital': self.initial_capital,
                'positions': {},
                'trade_history': []
            }

            # Serialize positions
            for token_address, position in self.positions.items():
                state['positions'][token_address] = position.to_dict()

            # Serialize trade history (last 100 trades only)
            for trade in self.trade_history[-100:]:
                state['trade_history'].append(trade.to_dict())

            # Write to file
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)

            self.logger.debug(f"State saved to {self.state_file}")

        except Exception as e:
            self.logger.error(f"Error saving state: {e}")

    def load_state(self):
        """Load state from file"""
        try:
            if not os.path.exists(self.state_file):
                self.logger.info("No previous state found, starting fresh")
                return

            with open(self.state_file, 'r') as f:
                state = json.load(f)

            # Restore cash and capital
            self.cash = state.get('cash', self.initial_capital)
            self.initial_capital = state.get('initial_capital', self.initial_capital)

            # Restore positions
            for token_address, pos_data in state.get('positions', {}).items():
                position = Position(
                    token_address=pos_data['token_address'],
                    symbol=pos_data['symbol'],
                    entry_price=pos_data['entry_price'],
                    current_price=pos_data['current_price'],
                    quantity=pos_data['quantity'],
                    position_size_usd=pos_data['position_size_usd'],
                    stop_loss=pos_data['stop_loss'],
                    take_profit=pos_data['take_profit'],
                    entry_time=datetime.fromisoformat(pos_data['entry_time']),
                    pnl=pos_data.get('pnl', 0.0),
                    pnl_percent=pos_data.get('pnl_percent', 0.0)
                )
                self.positions[token_address] = position

            # Restore trade history
            for trade_data in state.get('trade_history', []):
                trade = Trade(
                    timestamp=datetime.fromisoformat(trade_data['timestamp']),
                    action=trade_data['action'],
                    token_address=trade_data['token_address'],
                    symbol=trade_data['symbol'],
                    price=trade_data['price'],
                    quantity=trade_data['quantity'],
                    total_usd=trade_data['total_usd'],
                    fees=trade_data.get('fees', 0.0)
                )
                self.trade_history.append(trade)

            self.logger.info(f"State loaded: ${self.cash:.2f} cash, {len(self.positions)} positions, {len(self.trade_history)} trades")

        except Exception as e:
            self.logger.error(f"Error loading state: {e}")

    def get_statistics(self) -> Dict:
        """Get trading statistics"""
        total_trades = len(self.trade_history)
        buys = [t for t in self.trade_history if t.action == 'buy']
        sells = [t for t in self.trade_history if t.action == 'sell']

        portfolio_value = self.get_portfolio_value()
        total_pnl = portfolio_value - self.initial_capital
        total_pnl_percent = (total_pnl / self.initial_capital) * 100

        return {
            'initial_capital': self.initial_capital,
            'current_cash': self.cash,
            'portfolio_value': portfolio_value,
            'total_pnl': total_pnl,
            'total_pnl_percent': total_pnl_percent,
            'total_trades': total_trades,
            'total_buys': len(buys),
            'total_sells': len(sells),
            'open_positions': len(self.positions)
        }
