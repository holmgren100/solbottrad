import asyncio
from telegram import Bot
from telegram.error import TelegramError
from typing import Optional
import logging

class TelegramNotifier:
    """Send notifications via Telegram"""

    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.bot = Bot(token=bot_token)
        self.logger = logging.getLogger('trading_bot.telegram')

    async def send_message(self, message: str) -> bool:
        """Send a message to Telegram"""
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode='HTML'
            )
            self.logger.debug(f"Telegram message sent: {message[:50]}...")
            return True
        except TelegramError as e:
            self.logger.error(f"Telegram error: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error sending Telegram: {e}")
            return False

    async def notify_trade(self, action: str, symbol: str, amount: float, price: float, position_size: float):
        """Notify about trade execution"""
        emoji = "🟢" if action == "buy" else "🔴"
        message = f"""
{emoji} <b>{action.upper()} SIGNAL</b>

<b>Token:</b> {symbol}
<b>Price:</b> ${price:.8f}
<b>Amount:</b> ${amount:.2f}
<b>Position Size:</b> ${position_size:.2f}
<b>Mode:</b> Paper Trading
"""
        await self.send_message(message.strip())

    async def notify_opportunity(self, symbol: str, confidence: float, signal_type: str):
        """Notify about trading opportunity"""
        message = f"""
🎯 <b>TRADING OPPORTUNITY</b>

<b>Token:</b> {symbol}
<b>Signal:</b> {signal_type.upper()}
<b>Confidence:</b> {confidence:.1%}
"""
        await self.send_message(message.strip())

    async def notify_error(self, error_message: str):
        """Notify about errors"""
        message = f"⚠️ <b>ERROR</b>\n\n{error_message}"
        await self.send_message(message)

    async def notify_status(self, status: str):
        """Notify about bot status"""
        await self.send_message(f"ℹ️ {status}")
