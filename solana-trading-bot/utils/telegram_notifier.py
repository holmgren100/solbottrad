from datetime import datetime
from typing import Optional
from telegram import Bot
from telegram.error import TelegramError
from config.settings import settings
from utils.logger import setup_logger

class TelegramNotifier:
    """
    Utility class for sending notifications via Telegram.
    Handles message formatting and error handling.
    """

    def __init__(self):
        self.logger = setup_logger(__name__)

        # Get Telegram configuration from settings
        self.bot_token = settings.TELEGRAM_BOT_TOKEN
        self.chat_id = settings.TELEGRAM_CHAT_ID

        # Initialize Telegram bot
        try:
            self.bot = Bot(token=self.bot_token)
            self.logger.info("TelegramNotifier initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize TelegramNotifier: {str(e)}")
            raise

    async def send_notification(self, message: str, parse_mode: Optional[str] = None) -> bool:
        """
        Send a notification message via Telegram.

        Args:
            message (str): The message to send
            parse_mode (Optional[str]): Message parse mode (HTML, Markdown, etc.)

        Returns:
            bool: True if message was sent successfully

        Raises:
            TelegramError: If sending the message fails
        """
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode=parse_mode
            )
            self.logger.debug(f"Sent notification: {message[:100]}...")
            return True

        except TelegramError as e:
            self.logger.error(f"Failed to send Telegram notification: {str(e)}")
            raise

    async def send_trade_notification(self, trade_type: str, token: str, amount: float, price: float) -> bool:
        """
        Send a formatted trade notification.

        Args:
            trade_type (str): Type of trade ('BUY' or 'SELL')
            token (str): Token symbol
            amount (float): Trade amount
            price (float): Token price

        Returns:
            bool: True if message was sent successfully
        """
        try:
            message = (
                f"🤖 Trade Alert!\n\n"
                f"Type: {'🟢 BUY' if trade_type.upper() == 'BUY' else '🔴 SELL'}\n"
                f"Token: {token}\n"
                f"Amount: {amount:.4f}\n"
                f"Price: ${price:.6f}\n"
                f"Total: ${amount * price:.2f}"
            )

            return await self.send_notification(message)

        except Exception as e:
            self.logger.error(f"Failed to send trade notification: {str(e)}")
            raise

    async def send_error_notification(self, error_message: str, severity: str = "WARNING") -> bool:
        """
        Send an error notification with severity level.

        Args:
            error_message (str): The error message
            severity (str): Error severity (WARNING, ERROR, CRITICAL)

        Returns:
            bool: True if message was sent successfully
        """
        try:
            emoji = {
                "WARNING": "⚠️",
                "ERROR": "❌",
                "CRITICAL": "🚨"
            }.get(severity.upper(), "ℹ️")

            message = (
                f"{emoji} {severity}\n\n"
                f"Error: {error_message}\n"
                f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )

            return await self.send_notification(message)

        except Exception as e:
            self.logger.error(f"Failed to send error notification: {str(e)}")
            raise

    async def send_volume_alert(self, token: str, volume: float, price: float, change: float) -> bool:
        """
        Send a volume alert notification.

        Args:
            token (str): Token symbol
            volume (float): Trading volume
            price (float): Current price
            change (float): Price change percentage

        Returns:
            bool: True if message was sent successfully
        """
        try:
            emoji = "📈" if change >= 0 else "📉"
            message = (
                f"📊 Volume Alert!\n\n"
                f"Token: {token}\n"
                f"24h Volume: ${volume:,.2f}\n"
                f"Price: ${price:.6f}\n"
                f"Change: {emoji} {change:+.2f}%"
            )

            return await self.send_notification(message)

        except Exception as e:
            self.logger.error(f"Failed to send volume alert: {str(e)}")
            raise

# Example usage and testing
async def test_telegram_notifier():
    """Test function for TelegramNotifier"""
    notifier = TelegramNotifier()
    try:
        # Test basic notification
        await notifier.send_notification("Test notification from Trading Bot")

        # Test trade notification
        await notifier.send_trade_notification(
            trade_type="BUY",
            token="SOL",
            amount=1.5,
            price=123.45
        )

        # Test error notification
        await notifier.send_error_notification(
            "Test error message",
            severity="WARNING"
        )

        # Test volume alert
        await notifier.send_volume_alert(
            token="SOL",
            volume=1000000,
            price=123.45,
            change=5.67
        )

        print("All notifications sent successfully!")
        return True

    except Exception as e:
        print(f"Error testing notifications: {e}")
        return False

if __name__ == "__main__":
    import asyncio
    from datetime import datetime
    asyncio.run(test_telegram_notifier())