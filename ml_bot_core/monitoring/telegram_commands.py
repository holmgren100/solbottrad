"""
Telegram bot command handler for controlling the trading bot.
Allows users to check status, modify settings, and control the bot via Telegram.
"""

import asyncio
from typing import Optional, Callable
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from ..monitoring.logger import get_logger

logger = get_logger(__name__)


class TelegramCommandHandler:
    """Handle Telegram commands for bot control."""

    def __init__(self, bot_token: str, chat_id: str, bot_instance):
        """
        Initialize Telegram command handler.

        Args:
            bot_token: Telegram bot token
            chat_id: Telegram chat ID for authorized user
            bot_instance: Reference to the main trading bot instance
        """
        self.bot_token = bot_token
        self.authorized_chat_id = str(chat_id)
        self.bot = bot_instance
        self.application = None
        self.running = False

    def is_authorized(self, update: Update) -> bool:
        """Check if the user is authorized to send commands."""
        return str(update.effective_chat.id) == self.authorized_chat_id

    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show current bot status and positions."""
        if not self.is_authorized(update):
            await update.message.reply_text("⛔ Unauthorized")
            return

        try:
            positions = self.bot.position_manager.get_all_positions()
            stats = self.bot.get_statistics()

            message = "📊 *Trading Bot Status*\n\n"
            message += f"💰 *Portfolio*\n"
            message += f"Total P&L: ${stats.get('total_realized_pnl', 0):.2f}\n"
            message += f"Unrealized P&L: ${stats.get('total_unrealized_pnl', 0):.2f}\n\n"

            if positions:
                message += f"📈 *Open Positions ({len(positions)})*\n"
                for pos in positions:
                    pnl_pct = pos.unrealized_pnl_percent
                    emoji = "🟢" if pnl_pct > 0 else "🔴" if pnl_pct < 0 else "⚪"
                    message += f"{emoji} {pos.token_address[:8]}...\n"
                    message += f"   Entry: ${pos.entry_price:.8f}\n"
                    message += f"   Current: ${pos.current_price:.8f}\n"
                    message += f"   P&L: {pnl_pct:+.2f}%\n"
                    message += f"   Size: ${pos.amount_usd:.2f}\n\n"
            else:
                message += "📭 No open positions\n\n"

            message += f"📊 *Statistics*\n"
            message += f"Total Trades: {stats.get('total_trades', 0)}\n"
            message += f"Win Rate: {stats.get('win_rate', 0)*100:.1f}%\n"
            message += f"Wins/Losses: {stats.get('winning_trades', 0)}/{stats.get('losing_trades', 0)}\n"

            await update.message.reply_text(message, parse_mode='Markdown')

        except Exception as e:
            logger.error(f"Error in /status command: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")

    async def cmd_close(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Manually close a position."""
        if not self.is_authorized(update):
            await update.message.reply_text("⛔ Unauthorized")
            return

        try:
            if not context.args or len(context.args) != 1:
                await update.message.reply_text("Usage: /close <token_address>\nExample: /close So111111...")
                return

            token_address = context.args[0]

            # Find matching position
            positions = self.bot.position_manager.get_all_positions()
            matching_pos = None
            for pos in positions:
                if pos.token_address.startswith(token_address):
                    matching_pos = pos
                    break

            if not matching_pos:
                await update.message.reply_text(f"❌ No position found for {token_address}")
                return

            # Fetch current price
            await update.message.reply_text(f"🔄 Fetching current price for {matching_pos.token_address[:8]}...")

            price_data = await self.bot.price_validator.get_validated_price(
                matching_pos.token_address,
                entry_price=matching_pos.entry_price
            )
            current_price = price_data['price'] if price_data else matching_pos.current_price

            # Close the position
            trade = await self.bot.close_position(
                matching_pos.token_address,
                current_price,
                reason='manual_telegram'
            )

            if trade:
                await update.message.reply_text(
                    f"✅ Closed position\n"
                    f"Token: {matching_pos.token_address[:8]}...\n"
                    f"Entry: ${matching_pos.entry_price:.8f}\n"
                    f"Exit: ${current_price:.8f}\n"
                    f"P&L: ${trade.pnl:.2f} ({trade.pnl_percent:+.2f}%)"
                )
            else:
                await update.message.reply_text(f"❌ Failed to close position")

        except Exception as e:
            logger.error(f"Error in /close command: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")

    async def cmd_closeall(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Close all open positions at current market prices."""
        if not self.is_authorized(update):
            await update.message.reply_text("⛔ Unauthorized")
            return

        try:
            positions = self.bot.position_manager.get_all_positions()

            if not positions:
                await update.message.reply_text("📭 No open positions to close")
                return

            await update.message.reply_text(f"🔄 Closing {len(positions)} position(s)...")

            closed_count = 0
            total_pnl = 0
            results = []

            for pos in positions:
                try:
                    # Fetch current price
                    price_data = await self.bot.price_validator.get_validated_price(
                        pos.token_address,
                        entry_price=pos.entry_price
                    )
                    current_price = price_data['price'] if price_data else pos.current_price

                    # Close the position
                    trade = await self.bot.close_position(
                        pos.token_address,
                        current_price,
                        reason='manual_closeall'
                    )

                    if trade:
                        closed_count += 1
                        total_pnl += trade.pnl
                        pnl_pct = trade.pnl_percent
                        emoji = "🟢" if pnl_pct > 0 else "🔴" if pnl_pct < 0 else "⚪"
                        results.append(f"{emoji} {pos.token_address[:8]}: {pnl_pct:+.2f}%")
                    else:
                        results.append(f"❌ {pos.token_address[:8]}: Failed")

                except Exception as e:
                    logger.error(f"Error closing {pos.token_address[:8]}: {e}")
                    results.append(f"❌ {pos.token_address[:8]}: Error")

            # Send summary
            message = f"✅ Closed {closed_count}/{len(positions)} positions\n"
            message += f"Total P&L: ${total_pnl:.2f}\n\n"
            message += "Results:\n" + "\n".join(results)

            await update.message.reply_text(message)

        except Exception as e:
            logger.error(f"Error in /closeall command: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")

    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show available commands."""
        if not self.is_authorized(update):
            await update.message.reply_text("⛔ Unauthorized")
            return

        message = """
🤖 *Trading Bot Commands*

*Status & Info*
/status - View portfolio and positions

*Controls*
/close <token> - Close a position
/closeall - Close ALL positions at current prices

*Examples*
/close So111111
"""
        await update.message.reply_text(message, parse_mode='Markdown')

    async def start(self):
        """Start the Telegram command handler."""
        if self.running:
            return

        logger.info("Starting Telegram command handler...")

        # Create application
        self.application = Application.builder().token(self.bot_token).build()

        # Register command handlers
        self.application.add_handler(CommandHandler("status", self.cmd_status))
        self.application.add_handler(CommandHandler("close", self.cmd_close))
        self.application.add_handler(CommandHandler("closeall", self.cmd_closeall))
        self.application.add_handler(CommandHandler("help", self.cmd_help))

        # Start polling
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()

        self.running = True
        logger.info("Telegram command handler started")

    async def stop(self):
        """Stop the Telegram command handler."""
        if not self.running:
            return

        logger.info("Stopping Telegram command handler...")

        if self.application:
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()

        self.running = False
        logger.info("Telegram command handler stopped")
