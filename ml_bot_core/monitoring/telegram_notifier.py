"""
Telegram notification system for sending alerts and updates.
"""

import asyncio
from typing import Optional
from telegram import Bot
from telegram.error import TelegramError
from .logger import get_logger

logger = get_logger(__name__)


class TelegramNotifier:
    """Handles sending notifications via Telegram."""

    def __init__(self, bot_token: str, chat_id: str):
        """
        Initialize the Telegram notifier.

        Args:
            bot_token: Telegram bot token
            chat_id: Telegram chat ID to send messages to
        """
        self.bot = Bot(token=bot_token)
        self.chat_id = chat_id
        self._enabled = True

    async def send_message(self, message: str, parse_mode: Optional[str] = 'Markdown') -> bool:
        """
        Send a message via Telegram.

        Args:
            message: Message text to send
            parse_mode: Parse mode for formatting (Markdown or HTML)

        Returns:
            True if successful, False otherwise
        """
        if not self._enabled:
            logger.debug("Telegram notifications disabled, skipping message")
            return False

        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode=parse_mode
            )
            logger.debug(f"Telegram message sent: {message[:50]}...")
            return True
        except TelegramError as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending Telegram message: {e}")
            return False

    async def send_alert(self, title: str, message: str, level: str = 'INFO') -> bool:
        """
        Send a formatted alert message.

        Args:
            title: Alert title
            message: Alert message
            level: Alert level (INFO, WARNING, ERROR, CRITICAL)

        Returns:
            True if successful, False otherwise
        """
        emoji_map = {
            'INFO': 'ℹ️',
            'WARNING': '⚠️',
            'ERROR': '❌',
            'CRITICAL': '🚨'
        }

        emoji = emoji_map.get(level.upper(), 'ℹ️')
        formatted_message = f"{emoji} *{title}*\n\n{message}"

        return await self.send_message(formatted_message)

    async def send_trade_signal(
        self,
        token_address: str,
        action: str,
        confidence: float,
        price: float,
        reasons: list[str]
    ) -> bool:
        """
        Send a trade signal notification.

        Args:
            token_address: Token contract address
            action: Trade action (BUY/SELL)
            confidence: Confidence score (0-1)
            price: Current token price
            reasons: List of reasons for the trade

        Returns:
            True if successful, False otherwise
        """
        message = f"""
🎯 *Trade Signal: {action}*

*Token:* `{token_address[:8]}...{token_address[-8:]}`
*Price:* ${price:.8f}
*Confidence:* {confidence:.1%}

*Reasons:*
{chr(10).join(f'• {reason}' for reason in reasons)}
"""
        return await self.send_message(message.strip())

    async def send_trade_execution(
        self,
        token_address: str,
        action: str,
        amount: float,
        price: float,
        status: str
    ) -> bool:
        """
        Send a trade execution notification.

        Args:
            token_address: Token contract address
            action: Trade action (BUY/SELL)
            amount: Amount traded
            price: Execution price
            status: Execution status

        Returns:
            True if successful, False otherwise
        """
        emoji = '✅' if status == 'SUCCESS' else '❌'
        message = f"""
{emoji} *Trade {action}: {status}*

*Token:* `{token_address[:8]}...{token_address[-8:]}`
*Amount:* ${amount:.2f}
*Price:* ${price:.8f}
"""
        return await self.send_message(message.strip())

    async def send_startup_message(self) -> bool:
        """Send a startup notification."""
        message = """
🤖 *Trading Bot Started*

The Solana trading bot is now running and monitoring markets.
"""
        return await self.send_message(message.strip())

    async def send_shutdown_message(self) -> bool:
        """Send a shutdown notification."""
        message = """
🛑 *Trading Bot Stopped*

The Solana trading bot has been shut down.
"""
        return await self.send_message(message.strip())

    def disable(self):
        """Disable notifications."""
        self._enabled = False
        logger.info("Telegram notifications disabled")

    def enable(self):
        """Enable notifications."""
        self._enabled = True
        logger.info("Telegram notifications enabled")
