"""
Telegram Notifier - Send Trading Notifications

Sends Telegram notifications for:
- Entry signals
- Exit signals
- Breakeven triggers
- Pyramid adds
- Partial profits
- Health alerts
- Errors

Configurable via environment variables.
"""

import logging
import os
import requests
from typing import Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """
    Sends trading notifications via Telegram.

    Uses Telegram Bot API to send messages.
    """

    def __init__(self):
        """Initialize Telegram notifier."""
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID", "")

        self.enabled = bool(self.bot_token and self.chat_id)

        if self.enabled:
            logger.info("Telegram Notifier initialized - notifications ENABLED")
        else:
            logger.warning("Telegram Notifier initialized - notifications DISABLED (no credentials)")

    def send_message(self, message: str) -> bool:
        """
        Send a message via Telegram.

        Args:
            message: Message text to send

        Returns:
            True if sent successfully
        """
        if not self.enabled:
            logger.debug("Telegram disabled - skipping notification")
            return False

        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"

            payload = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "HTML",
                "disable_web_page_preview": True
            }

            response = requests.post(url, json=payload, timeout=10)

            if response.status_code == 200:
                logger.debug("Telegram notification sent")
                return True
            else:
                logger.error(f"Telegram API error: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            logger.error(f"Error sending Telegram message: {e}")
            return False

    def send_entry_notification(self, position: Dict, momentum_score: int, signals: list) -> bool:
        """
        Send entry signal notification.

        Args:
            position: Position dict with token info
            momentum_score: Momentum score (0-100)
            signals: List of active signals

        Returns:
            True if sent
        """
        try:
            signal_list = "\n".join([f"  • {s}" for s in signals])

            message = f"""
🎯 <b>ENTRY SIGNAL</b>

<b>Token:</b> {position.get('symbol', 'UNKNOWN')}
<b>Price:</b> ${position.get('entry_price', 0):.8f}
<b>Size:</b> {position.get('size_sol', 0):.4f} SOL

<b>Momentum Score:</b> {momentum_score}/100

<b>Signals:</b>
{signal_list}

<b>Stop Loss:</b> -25%
<b>Target:</b> Risk-free at +50%
"""

            return self.send_message(message.strip())

        except Exception as e:
            logger.error(f"Error formatting entry notification: {e}")
            return False

    def send_exit_notification(
        self,
        position: Dict,
        exit_reason: str,
        duration_minutes: int,
        win_rate: float = 0,
        total_trades: int = 0
    ) -> bool:
        """
        Send exit notification.

        Args:
            position: Position dict with exit info
            exit_reason: Reason for exit
            duration_minutes: Position duration in minutes
            win_rate: Overall win rate (optional)
            total_trades: Total trades count (optional)

        Returns:
            True if sent
        """
        try:
            entry_price = position.get('entry_price', 0)
            exit_price = position.get('exit_price', position.get('current_price', 0))
            pnl_percent = position.get('pnl_percent', 0)
            pnl_sol = position.get('pnl_sol', 0)
            symbol = position.get('symbol', 'UNKNOWN')

            # Format duration
            if duration_minutes < 60:
                duration_str = f"{duration_minutes}m"
            else:
                hours = duration_minutes // 60
                mins = duration_minutes % 60
                duration_str = f"{hours}h {mins}m" if mins > 0 else f"{hours}h"

            # Emoji based on P&L
            emoji = "🎉" if pnl_percent > 0 else "😢"

            message = f"""
{emoji} <b>EXIT</b>

<b>Token:</b> {symbol}
<b>Entry:</b> ${entry_price:.8f}
<b>Exit:</b> ${exit_price:.8f}
<b>P&L:</b> {pnl_percent:+.1f}% ({pnl_sol:+.4f} SOL)

<b>Reason:</b> {exit_reason}
<b>Duration:</b> {duration_str}
"""

            if total_trades > 0:
                message += f"\n<b>Total Trades:</b> {total_trades}\n<b>Win Rate:</b> {win_rate:.1f}%"

            return self.send_message(message.strip())

        except Exception as e:
            logger.error(f"Error formatting exit notification: {e}")
            return False

    def send_breakeven_notification(self, position: Dict) -> bool:
        """
        Send breakeven trigger notification.

        Args:
            position: Position dict

        Returns:
            True if sent
        """
        try:
            message = f"""
🛡️ <b>BREAKEVEN TRIGGERED</b>

<b>Token:</b> {position.get('symbol', 'UNKNOWN')}
<b>Profit:</b> +{position.get('pnl_percent', 0):.1f}%

<b>Position is now RISK-FREE!</b>
• Stop moved to entry +2%
• Selling 40% to recover initial investment

Remaining position rides for free! 🚀
"""

            return self.send_message(message.strip())

        except Exception as e:
            logger.error(f"Error formatting breakeven notification: {e}")
            return False

    def send_pyramid_notification(self, position: Dict, stage: int, size_pct: float) -> bool:
        """
        Send pyramid add notification.

        Args:
            position: Position dict
            stage: Pyramid stage (1 or 2)
            size_pct: Size percentage added

        Returns:
            True if sent
        """
        try:
            message = f"""
🔺 <b>PYRAMID STAGE {stage}</b>

<b>Token:</b> {position.get('symbol', 'UNKNOWN')}
<b>Profit:</b> +{position.get('pnl_percent', 0):.1f}%

<b>Adding {size_pct}% to winning position!</b>

Momentum still strong - maximize the runner! 📈
"""

            return self.send_message(message.strip())

        except Exception as e:
            logger.error(f"Error formatting pyramid notification: {e}")
            return False

    def send_partial_notification(self, position: Dict, sell_pct: float, trigger_pct: int) -> bool:
        """
        Send partial profit notification.

        Args:
            position: Position dict
            sell_pct: Percentage being sold
            trigger_pct: Trigger percentage (500 or 1000)

        Returns:
            True if sent
        """
        try:
            message = f"""
💰 <b>PARTIAL PROFIT</b>

<b>Token:</b> {position.get('symbol', 'UNKNOWN')}
<b>Profit:</b> +{position.get('pnl_percent', 0):.1f}%

<b>Selling {sell_pct}% at +{trigger_pct}%!</b>

Locking in gains, letting winners run! 🎯
"""

            return self.send_message(message.strip())

        except Exception as e:
            logger.error(f"Error formatting partial notification: {e}")
            return False

    def send_health_alert(self, health_status: Dict) -> bool:
        """
        Send system health alert.

        Args:
            health_status: Health check result dict

        Returns:
            True if sent
        """
        try:
            status = health_status.get("status", "unknown")
            issues = health_status.get("issues", [])
            warnings = health_status.get("warnings", [])

            if status == "healthy":
                return False  # Don't send notifications for healthy status

            emoji = "⚠️" if status == "warning" else "❌"

            message = f"""
{emoji} <b>SYSTEM HEALTH ALERT</b>

<b>Status:</b> {status.upper()}
"""

            if issues:
                issue_list = "\n".join([f"  • {i}" for i in issues])
                message += f"\n<b>Issues:</b>\n{issue_list}\n"

            if warnings:
                warning_list = "\n".join([f"  • {w}" for w in warnings])
                message += f"\n<b>Warnings:</b>\n{warning_list}\n"

            message += f"\n<i>Time:</i> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

            return self.send_message(message.strip())

        except Exception as e:
            logger.error(f"Error formatting health alert: {e}")
            return False

    def send_error_alert(self, error_message: str, context: str = "") -> bool:
        """
        Send error alert notification.

        Args:
            error_message: Error message
            context: Optional context info

        Returns:
            True if sent
        """
        try:
            message = f"""
❌ <b>ERROR ALERT</b>

<b>Error:</b> {error_message}
"""

            if context:
                message += f"\n<b>Context:</b> {context}"

            message += f"\n\n<i>Time:</i> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

            return self.send_message(message.strip())

        except Exception as e:
            logger.error(f"Error formatting error alert: {e}")
            return False

    def send_startup_notification(self) -> bool:
        """Send bot startup notification."""
        try:
            message = """
🚀 <b>BOT STARTED</b>

Fearless Momentum Runner v2.0 is now running!

Ready to hunt for 500-1700% runners! 🎯
"""

            return self.send_message(message.strip())

        except Exception as e:
            logger.error(f"Error sending startup notification: {e}")
            return False

    def send_shutdown_notification(self) -> bool:
        """Send bot shutdown notification."""
        try:
            message = """
⏹️ <b>BOT STOPPED</b>

Fearless Momentum Runner has been stopped.
"""

            return self.send_message(message.strip())

        except Exception as e:
            logger.error(f"Error sending shutdown notification: {e}")
            return False

    def send_daily_summary(self, stats: dict) -> bool:
        """
        Send daily trading summary.

        Args:
            stats: Dict with daily statistics from DataLogger

        Returns:
            True if sent
        """
        try:
            if stats.get("total_trades", 0) == 0:
                return False  # Don't send if no trades

            total_trades = stats["total_trades"]
            wins = stats["wins"]
            losses = stats["losses"]
            win_rate = stats["win_rate"]
            total_pnl = stats["total_pnl"]
            total_pnl_sol = stats["total_pnl_sol"]
            best_trade = stats["best_trade"]
            worst_trade = stats["worst_trade"]
            avg_duration = stats["avg_duration"]
            big_winners = stats["big_winners"]
            breakeven_count = stats["breakeven_count"]
            pyramid_count = stats["pyramid_count"]

            # Emoji based on performance
            if win_rate >= 60:
                emoji = "🎉"
            elif win_rate >= 50:
                emoji = "✅"
            elif win_rate >= 40:
                emoji = "📊"
            else:
                emoji = "📉"

            message = f"""
{emoji} <b>DAILY SUMMARY - {datetime.now().strftime('%Y-%m-%d')}</b>

🎯 <b>Performance:</b>
• Total Trades: {total_trades}
• Wins: {wins} | Losses: {losses}
• Win Rate: {win_rate:.1f}%
• Total P&L: {total_pnl:+.1f}% ({total_pnl_sol:+.3f} SOL)

📈 <b>Best/Worst:</b>
• Best Trade: {best_trade:+.1f}%
• Worst Trade: {worst_trade:+.1f}%
• Avg Duration: {avg_duration} min

💎 <b>Highlights:</b>
• Runners Caught (500%+): {big_winners}
• Breakeven Triggered: {breakeven_count}
• Pyramids Added: {pyramid_count}

⏱️ <i>Generated: {datetime.now().strftime('%H:%M:%S')}</i>
"""

            return self.send_message(message.strip())

        except Exception as e:
            logger.error(f"Error sending daily summary: {e}")
            return False


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    notifier = TelegramNotifier()

    print(f"Telegram enabled: {notifier.enabled}")

    if notifier.enabled:
        print("\nSending test notifications...")

        # Test entry notification
        test_position = {
            "symbol": "TEST",
            "entry_price": 0.001,
            "size_sol": 0.1,
            "pnl_percent": 150,
            "pnl_sol": 0.05
        }

        notifier.send_entry_notification(
            test_position,
            momentum_score=85,
            signals=["MACD growing", "Volume spike 5x", "RSI sweet spot"]
        )

        # Test breakeven notification
        notifier.send_breakeven_notification(test_position)

    else:
        print("\nSet TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID to test notifications")
