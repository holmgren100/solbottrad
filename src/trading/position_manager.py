import logging
from typing import Dict, List, Optional
from datetime import datetime

class PositionManager:
    """Manage trading positions and monitor for stop loss / take profit"""

    def __init__(self, paper_trading_engine):
        self.engine = paper_trading_engine
        self.logger = logging.getLogger('trading_bot.position_manager')

    async def check_positions(self, price_data: Dict[str, float]) -> List[Dict]:
        """Check all positions for stop loss or take profit triggers"""
        actions = []

        for token_address, position in list(self.engine.positions.items()):
            if token_address in price_data:
                current_price = price_data[token_address]

                # Update position price
                self.engine.update_position_prices(token_address, current_price)

                # Check stop loss
                if current_price <= position.stop_loss:
                    self.logger.warning(f"🛑 STOP LOSS triggered for {position.symbol}: ${current_price:.8f} <= ${position.stop_loss:.8f}")
                    actions.append({
                        'action': 'sell',
                        'token_address': token_address,
                        'symbol': position.symbol,
                        'price': current_price,
                        'reason': 'stop_loss'
                    })

                # Check take profit
                elif current_price >= position.take_profit:
                    self.logger.info(f"🎯 TAKE PROFIT triggered for {position.symbol}: ${current_price:.8f} >= ${position.take_profit:.8f}")
                    actions.append({
                        'action': 'sell',
                        'token_address': token_address,
                        'symbol': position.symbol,
                        'price': current_price,
                        'reason': 'take_profit'
                    })

        return actions

    def get_open_positions(self) -> List[Dict]:
        """Get all open positions with current P&L"""
        positions = []

        for position in self.engine.positions.values():
            positions.append({
                'symbol': position.symbol,
                'token_address': position.token_address,
                'entry_price': position.entry_price,
                'current_price': position.current_price,
                'quantity': position.quantity,
                'position_size': position.position_size_usd,
                'pnl': position.pnl,
                'pnl_percent': position.pnl_percent,
                'stop_loss': position.stop_loss,
                'take_profit': position.take_profit,
                'entry_time': position.entry_time
            })

        return positions

    def get_position(self, token_address: str) -> Optional[Dict]:
        """Get specific position"""
        if token_address in self.engine.positions:
            position = self.engine.positions[token_address]
            return {
                'symbol': position.symbol,
                'entry_price': position.entry_price,
                'current_price': position.current_price,
                'quantity': position.quantity,
                'position_size': position.position_size_usd,
                'pnl': position.pnl,
                'pnl_percent': position.pnl_percent
            }
        return None

    def has_position(self, token_address: str) -> bool:
        """Check if position exists for token"""
        return token_address in self.engine.positions
