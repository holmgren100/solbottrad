import logging
from typing import Dict, Optional, List
from datetime import datetime
from dataclasses import dataclass, asdict
import json

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

    def __init__(self, initial_capital: float = 1000.0, stop_loss_percent: float = 5.0, take_profit_percent: float = 10.0):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions: Dict[str, Position] = {}
        self.trade_history: List[Trade] = []
        self.stop_loss_percent = stop_loss_percent
        self.take_profit_percent = take_profit_percent
        self.logger = logging.getLogger('trading_bot.paper_trading')

        self.logger.info(f"Paper trading initialized with ${initial_capital:.2f}")

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
