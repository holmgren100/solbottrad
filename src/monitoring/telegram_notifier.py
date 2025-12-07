"""
Telegram notification system for sending alerts and updates.
"""

import asyncio
from typing import Optional
from telegram import Bot
from telegram.error import TelegramError
from .logger import get_logger

logger = get_logger(__name__)


def escape_markdown(text: str) -> str:
    """
    Escape special characters for Telegram Markdown.

    Args:
        text: Text to escape

    Returns:
        Escaped text safe for Telegram Markdown
    """
    # Telegram Markdown special characters that need escaping
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']

    escaped_text = text
    for char in special_chars:
        escaped_text = escaped_text.replace(char, f'\\{char}')

    return escaped_text


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
        Send a formatted alert message with priority levels.

        Args:
            title: Alert title
            message: Alert message
            level: Alert level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

        Returns:
            True if successful, False otherwise
        """
        # Priority levels - only send based on configured level
        priority_order = {'DEBUG': 0, 'INFO': 1, 'WARNING': 2, 'ERROR': 3, 'CRITICAL': 4}

        emoji_map = {
            'DEBUG': '🔵',
            'INFO': '🟢',
            'WARNING': '🟡',
            'ERROR': '🔴',
            'CRITICAL': '🚨'
        }

        emoji = emoji_map.get(level.upper(), '🟢')
        # Escape special markdown characters in title and message to prevent parsing errors
        safe_title = escape_markdown(title)
        safe_message = escape_markdown(message)
        formatted_message = f"{emoji} *{safe_title}*\n\n{safe_message}"

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
        DEPRECATED: Use send_entry_notification or send_exit_notification instead.
        This method is kept for backwards compatibility but should not be used
        for scanning signals (to prevent flooding).

        Args:
            token_address: Token contract address
            action: Trade action (BUY/SELL)
            confidence: Confidence score (0-1)
            price: Current token price
            reasons: List of reasons for the trade

        Returns:
            True if successful, False otherwise
        """
        # Only send for actual trades, not scanning signals
        logger.debug(f"Trade signal method called for {token_address[:8]} - use send_entry_notification instead")
        return False

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

    async def send_entry_notification(
        self,
        token_address: str,
        symbol: str,
        entry_price: float,
        position_size: float,
        score: int,
        confidence: str,
        token_data: dict,
        rugcheck_data: dict = None,
        market_data: dict = None,
        score_breakdown: dict = None,
        warnings: list = None,
        is_pumpfun: bool = False,
        source: str = None
    ) -> bool:
        """
        Send enhanced entry notification with comprehensive data.
        ONLY called when actually entering a position.

        Args:
            token_address: Token mint address
            symbol: Token symbol
            entry_price: Entry price
            position_size: Position size in USD
            score: Token score 0-100 (opportunity score from score-based selection)
            confidence: Confidence level (high/medium/low)
            token_data: Token data from aggregator
            rugcheck_data: RugCheck analysis (optional)
            market_data: Market conditions (optional)
            score_breakdown: Score breakdown by factor (optional)
            warnings: List of warnings (optional)
            is_pumpfun: Whether this is a pump.fun token
            source: Token source (jupiter/coingecko/dexscreener/birdeye/apify)

        Returns:
            True if successful
        """
        from datetime import datetime

        # Get token age
        pair_created_at = token_data.get('pair_created_at', 0)
        if pair_created_at > 0:
            age_hours = (datetime.now().timestamp() - pair_created_at / 1000) / 3600
        else:
            age_hours = 0

        # Emojis
        token_emoji = '🚀' if is_pumpfun else '📈'
        confidence_emoji = '🟢' if confidence == 'high' else '🟡' if confidence == 'medium' else '🟠'

        # Use provided source if available, otherwise fall back to token_data
        display_source = (source or token_data.get('primary_source', 'UNKNOWN')).upper()

        message = (
            f"{confidence_emoji} *ENTERED: {symbol}* {token_emoji}\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"💰 Position: ${position_size:.2f}\n"
            f"💲 Entry: ${entry_price:.8f}\n"
            f"📊 Score: {score}/100 ({score:.1f})\n"
            f"\n"
            f"📍 Source: {display_source}\n"
            f"💧 Liquidity: ${token_data.get('liquidity_usd', 0):,.0f}\n"
            f"📈 Volume 24h: ${token_data.get('volume_24h', 0):,.0f}\n"
            f"⏰ Age: {age_hours:.1f}h\n"
            f"🔗 Data: {token_data.get('sources_count', 1)} sources\n"
        )

        # Add score breakdown if available
        if score_breakdown:
            message += f"\n✅ *Score Breakdown:*\n"
            for factor, points in score_breakdown.items():
                message += f"  • {factor}: {points} pts\n"

        # Add RugCheck if available
        if rugcheck_data:
            message += (
                f"\n🛡️ *RugCheck:*\n"
                f"  • Safety: {rugcheck_data.get('risk_score', 0)}/100\n"
                f"  • Risk: {rugcheck_data.get('risk_level', 'unknown')}\n"
            )

        # Add market conditions if available
        if market_data:
            sol_health = market_data.get('sol_health', {})
            message += (
                f"\n📈 *Market: {market_data.get('market_state', 'unknown').upper()}*\n"
                f"  • SOL: ${sol_health.get('price', 0):.2f} ({sol_health.get('change_1h', 0):+.1f}%)\n"
            )

        # Add warnings if any
        if warnings:
            message += f"\n⚠️ *Warnings:*\n"
            for warning in warnings[:3]:  # Max 3
                message += f"  • {warning}\n"

        message += f"\n🔗 `{token_address[:8]}...{token_address[-4:]}`"

        return await self.send_message(message)

    async def send_exit_notification(
        self,
        token_address: str,
        symbol: str,
        entry_price: float,
        exit_price: float,
        position_size: float,
        pnl: float,
        pnl_percent: float,
        hold_time_hours: float,
        exit_reason: str,
        liquidity_change: dict = None
    ) -> bool:
        """
        Send enhanced exit notification with comprehensive data.
        ONLY called when actually exiting a position.

        Args:
            token_address: Token mint address
            symbol: Token symbol
            entry_price: Entry price
            exit_price: Exit price
            position_size: Position size in USD
            pnl: Profit/loss in USD
            pnl_percent: Profit/loss percentage
            hold_time_hours: How long position was held
            exit_reason: Reason for exit
            liquidity_change: Liquidity changes during hold (optional)

        Returns:
            True if successful
        """
        # Determine emoji based on outcome
        if pnl_percent > 0:
            outcome_emoji = '🟢'
            outcome_text = 'WIN'
        elif pnl_percent < 0:
            outcome_emoji = '🔴'
            outcome_text = 'LOSS'
        else:
            outcome_emoji = '⚪'
            outcome_text = 'BREAKEVEN'

        # Exit reason emojis
        reason_emojis = {
            'trailing_stop': '📈',
            'stop_loss': '🛑',
            'take_profit': '🎯',
            'force_exit': '🚨',
            'manual': '👤',
            'max_age': '⏰',
            'low_liquidity': '💧'
        }
        reason_emoji = reason_emojis.get(exit_reason.lower(), '📊')

        message = (
            f"{outcome_emoji} *EXITED: {symbol}* {reason_emoji}\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"💰 P&L: ${pnl:+.2f} ({pnl_percent:+.2f}%)\n"
            f"📊 Outcome: *{outcome_text}*\n"
            f"\n"
            f"💲 Entry: ${entry_price:.8f}\n"
            f"💲 Exit: ${exit_price:.8f}\n"
            f"💼 Size: ${position_size:.2f}\n"
            f"⏱️ Hold: {hold_time_hours:.1f}h\n"
            f"📝 Reason: {exit_reason.replace('_', ' ').title()}\n"
        )

        # Add liquidity changes if available
        if liquidity_change:
            entry_liq = liquidity_change.get('entry', 0)
            exit_liq = liquidity_change.get('exit', 0)
            change_pct = liquidity_change.get('change_percent', 0)

            message += (
                f"\n💧 *Liquidity:*\n"
                f"  • Entry: ${entry_liq:,.0f}\n"
                f"  • Exit: ${exit_liq:,.0f}\n"
                f"  • Change: {change_pct:+.1f}%\n"
            )

        message += f"\n🔗 `{token_address[:8]}...{token_address[-4:]}`"

        return await self.send_message(message)

    async def send_market_crash_alert(
        self,
        btc_change: float,
        eth_change: float,
        sol_change: float,
        market_state: str
    ) -> bool:
        """
        Send CRITICAL alert for market crashes.

        Args:
            btc_change: BTC 1h change %
            eth_change: ETH 1h change %
            sol_change: SOL 1h change %
            market_state: Market state (crash/warning)

        Returns:
            True if successful
        """
        if market_state == 'crash':
            emoji = '🚨'
            title = 'MARKET CRASH DETECTED'
            action = 'Trading STOPPED'
        else:
            emoji = '⚠️'
            title = 'Market Warning'
            action = 'Reducing position sizes'

        message = (
            f"{emoji} *{title}*\n\n"
            f"Major crypto markets dumping:\n"
            f"  • BTC: {btc_change:+.1f}%\n"
            f"  • ETH: {eth_change:+.1f}%\n"
            f"  • SOL: {sol_change:+.1f}%\n\n"
            f"🛡️ Action: {action}\n"
            f"💡 All positions being monitored closely"
        )

        level = 'CRITICAL' if market_state == 'crash' else 'WARNING'
        return await self.send_alert(title, message, level=level)

    async def send_api_status_alert(
        self,
        api_name: str,
        status: str,
        error_message: str = None
    ) -> bool:
        """
        Send alert when API goes down or recovers.

        Args:
            api_name: Name of the API
            status: Status (down/recovered)
            error_message: Error message if down

        Returns:
            True if successful
        """
        if status == 'down':
            emoji = '🔴'
            title = f'API Down: {api_name}'
            level = 'ERROR'
            msg = f"API {api_name} is not responding.\n"
            if error_message:
                msg += f"Error: {error_message}\n"
            msg += f"\nFalling back to other data sources."
        else:
            emoji = '🟢'
            title = f'API Recovered: {api_name}'
            level = 'INFO'
            msg = f"API {api_name} is back online."

        return await self.send_alert(title, msg, level=level)

    async def send_force_exit_alert(
        self,
        token_address: str,
        symbol: str,
        reason: str,
        entry_liquidity: float,
        current_liquidity: float,
        drop_percent: float
    ) -> bool:
        """
        Send CRITICAL alert for force exits.

        Args:
            token_address: Token mint address
            symbol: Token symbol
            reason: Reason for force exit
            entry_liquidity: Entry liquidity
            current_liquidity: Current liquidity
            drop_percent: Liquidity drop percentage

        Returns:
            True if successful
        """
        message = (
            f"🚨 *FORCE EXIT: {symbol}*\n\n"
            f"Position force closed due to:\n"
            f"*{reason}*\n\n"
            f"💧 Liquidity:\n"
            f"  • Entry: ${entry_liquidity:,.0f}\n"
            f"  • Current: ${current_liquidity:,.0f}\n"
            f"  • Drop: {drop_percent:.0f}%\n\n"
            f"🔗 `{token_address[:8]}...{token_address[-4:]}`"
        )

        return await self.send_alert('Force Exit', message, level='CRITICAL')
