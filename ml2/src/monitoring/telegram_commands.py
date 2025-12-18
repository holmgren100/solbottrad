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
            if self.bot.settings.is_paper_trading():
                engine = self.bot.trading_engine
                positions = engine.position_manager.get_all_positions()
                stats = engine.get_performance_summary()

                message = "📊 *Trading Bot Status*\n\n"
                message += f"💰 *Portfolio*\n"
                message += f"Total Value: ${stats['portfolio_value']:.2f}\n"
                message += f"Cash: ${stats['current_capital']:.2f}\n"
                message += f"Invested: ${stats['invested_capital']:.2f}\n"
                message += f"P&L: ${stats['total_pnl']:.2f} ({stats['total_return_percent']:+.2f}%)\n\n"

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
                message += f"Total Trades: {stats['total_trades']}\n"
                message += f"Win Rate: {stats['win_rate']*100:.1f}%\n"
                message += f"Wins/Losses: {stats['winning_trades']}/{stats['losing_trades']}\n"

                await update.message.reply_text(message, parse_mode='Markdown')
            else:
                await update.message.reply_text("❌ Live trading not yet implemented")

        except Exception as e:
            logger.error(f"Error in /status command: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")

    async def cmd_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show current bot settings."""
        if not self.is_authorized(update):
            await update.message.reply_text("⛔ Unauthorized")
            return

        try:
            settings = self.bot.settings

            message = "⚙️ *Bot Settings*\n\n"
            message += f"*Trading*\n"
            message += f"Mode: {'📄 Paper' if settings.is_paper_trading() else '💰 Live'}\n"
            message += f"Max Position: ${settings.trading.max_position_size:.2f}\n"
            message += f"Min Liquidity: ${settings.trading.min_liquidity_usd:,.0f}\n"
            message += f"Min Confidence: {settings.trading.min_confidence_score:.2f}\n\n"

            message += f"*Risk Management*\n"
            message += f"Stop Loss: {settings.risk.stop_loss_percent:.0f}%\n"
            message += f"Take Profit: {settings.risk.take_profit_percent:.0f}%\n"
            message += f"Max Portfolio Risk: {settings.risk.max_portfolio_risk_percent:.0f}%\n"
            message += f"Max Daily Trades: {settings.risk.max_daily_trades}\n"
            message += f"Max Open Positions: {settings.risk.max_open_positions}\n\n"

            message += "💡 Use /stop_loss <pct> or /take_profit <pct> to change"

            await update.message.reply_text(message, parse_mode='Markdown')

        except Exception as e:
            logger.error(f"Error in /settings command: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")

    async def cmd_stop_loss(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Change stop loss percentage."""
        if not self.is_authorized(update):
            await update.message.reply_text("⛔ Unauthorized")
            return

        try:
            if not context.args or len(context.args) != 1:
                await update.message.reply_text("Usage: /stop_loss <percentage>\nExample: /stop_loss 15")
                return

            new_sl = float(context.args[0])
            if new_sl <= 0 or new_sl > 50:
                await update.message.reply_text("❌ Stop loss must be between 0 and 50%")
                return

            self.bot.settings.risk.stop_loss_percent = new_sl
            await update.message.reply_text(f"✅ Stop loss updated to {new_sl}%")
            logger.info(f"Stop loss changed to {new_sl}% via Telegram")

        except ValueError:
            await update.message.reply_text("❌ Invalid number format")
        except Exception as e:
            logger.error(f"Error in /stop_loss command: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")

    async def cmd_take_profit(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Change take profit percentage."""
        if not self.is_authorized(update):
            await update.message.reply_text("⛔ Unauthorized")
            return

        try:
            if not context.args or len(context.args) != 1:
                await update.message.reply_text("Usage: /take_profit <percentage>\nExample: /take_profit 40")
                return

            new_tp = float(context.args[0])
            if new_tp <= 0 or new_tp > 200:
                await update.message.reply_text("❌ Take profit must be between 0 and 200%")
                return

            self.bot.settings.risk.take_profit_percent = new_tp
            await update.message.reply_text(f"✅ Take profit updated to {new_tp}%")
            logger.info(f"Take profit changed to {new_tp}% via Telegram")

        except ValueError:
            await update.message.reply_text("❌ Invalid number format")
        except Exception as e:
            logger.error(f"Error in /take_profit command: {e}")
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
            positions = self.bot.trading_engine.position_manager.get_all_positions()
            matching_pos = None
            for pos in positions:
                if pos.token_address.startswith(token_address):
                    matching_pos = pos
                    break

            if not matching_pos:
                await update.message.reply_text(f"❌ No position found for {token_address}")
                return

            # IMPORTANT: Fetch CURRENT price before closing (don't use cached price!)
            await update.message.reply_text(f"🔄 Fetching current price for {matching_pos.token_address[:8]}...")

            dex_profile = await self.bot.dexscreener.get_token_profile(matching_pos.token_address)
            current_price = dex_profile['price_usd'] if dex_profile else matching_pos.current_price

            # If DexScreener fails, try Jupiter
            if not current_price or current_price == 0:
                jupiter_data = await self.bot.jupiter.get_token_price_data(matching_pos.token_address)
                current_price = jupiter_data['price_usd'] if jupiter_data else matching_pos.current_price

            # Fallback to cached price if all sources fail
            if not current_price or current_price == 0:
                current_price = matching_pos.current_price
                await update.message.reply_text(f"⚠️ Using cached price (sources unavailable)")

            # Close the position at CURRENT price
            result = await self.bot.trading_engine.execute_sell(
                matching_pos.token_address,
                current_price,
                reason='manual_telegram'
            )

            if result['status'] == 'success':
                await update.message.reply_text(
                    f"✅ Closed position\n"
                    f"Token: {matching_pos.token_address[:8]}...\n"
                    f"Entry: ${matching_pos.entry_price:.8f}\n"
                    f"Exit: ${current_price:.8f}\n"
                    f"P&L: ${result['pnl']:.2f} ({result['pnl_percent']:+.2f}%)"
                )
                logger.info(f"Position {matching_pos.token_address[:8]} closed via Telegram at ${current_price:.8f}")
            else:
                await update.message.reply_text(f"❌ Failed to close: {result.get('reason', 'unknown')}")

        except Exception as e:
            logger.error(f"Error in /close command: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")

    async def cmd_closeall(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Close all open positions at current market prices."""
        if not self.is_authorized(update):
            await update.message.reply_text("⛔ Unauthorized")
            return

        try:
            positions = self.bot.trading_engine.position_manager.get_all_positions()

            if not positions:
                await update.message.reply_text("📭 No open positions to close")
                return

            await update.message.reply_text(f"🔄 Closing {len(positions)} position(s)...\n"
                                           f"This may take a moment...")

            closed_count = 0
            total_pnl = 0
            results = []

            for pos in positions:
                try:
                    # Fetch CURRENT price for each position
                    dex_profile = await self.bot.dexscreener.get_token_profile(pos.token_address)
                    current_price = dex_profile['price_usd'] if dex_profile else None

                    # If DexScreener fails, try Jupiter
                    if not current_price or current_price == 0:
                        jupiter_data = await self.bot.jupiter.get_token_price_data(pos.token_address)
                        current_price = jupiter_data['price_usd'] if jupiter_data else None

                    # Fallback to cached price if all sources fail
                    if not current_price or current_price == 0:
                        current_price = pos.current_price

                    # Close the position
                    result = await self.bot.trading_engine.execute_sell(
                        pos.token_address,
                        current_price,
                        reason='manual_closeall'
                    )

                    if result['status'] == 'success':
                        closed_count += 1
                        total_pnl += result['pnl']
                        pnl_pct = result['pnl_percent']
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
            logger.info(f"Closed all positions via /closeall: {closed_count} positions, ${total_pnl:.2f} PnL")

        except Exception as e:
            logger.error(f"Error in /closeall command: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")

    async def cmd_export(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Export trade history to CSV file."""
        if not self.is_authorized(update):
            await update.message.reply_text("⛔ Unauthorized")
            return

        try:
            from datetime import datetime

            # Export trades to CSV
            filepath = 'data/trade_history.csv'
            trade_count = self.bot.trading_engine.position_manager.export_to_csv(filepath)

            if trade_count == 0:
                await update.message.reply_text("📭 No trades to export yet")
                return

            # Send file to user
            await update.message.reply_text(
                f"📊 Exporting {trade_count} trades...\n\n"
                f"Columns:\n"
                f"• Date & Time\n"
                f"• Token & Symbol\n"
                f"• Entry/Exit Prices\n"
                f"• Position Size\n"
                f"• PnL ($ and %)\n"
                f"• Win/Loss\n"
                f"• Duration\n"
                f"• Close Reason (Trailing Stop, Rug, Manual, etc.)\n\n"
                f"Opening in Excel..."
            )

            # Send CSV file
            with open(filepath, 'rb') as f:
                await update.message.reply_document(
                    document=f,
                    filename=f"trade_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    caption=f"✅ {trade_count} trades exported"
                )

            logger.info(f"Exported {trade_count} trades via /export command")

        except Exception as e:
            logger.error(f"Error in /export command: {e}")
            await update.message.reply_text(f"❌ Error exporting trades: {str(e)}")

    async def cmd_pause(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Pause trading (monitoring continues)."""
        if not self.is_authorized(update):
            await update.message.reply_text("⛔ Unauthorized")
            return

        try:
            self.bot.trading_paused = True
            await update.message.reply_text("⏸️ Trading paused. Monitoring continues.")
            logger.info("Trading paused via Telegram")
        except Exception as e:
            logger.error(f"Error in /pause command: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")

    async def cmd_resume(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Resume trading."""
        if not self.is_authorized(update):
            await update.message.reply_text("⛔ Unauthorized")
            return

        try:
            self.bot.trading_paused = False
            await update.message.reply_text("▶️ Trading resumed.")
            logger.info("Trading resumed via Telegram")
        except Exception as e:
            logger.error(f"Error in /resume command: {e}")
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
/settings - View current settings
/export - Export trade history to CSV (Excel)

*Controls*
/pause - Pause trading
/resume - Resume trading
/close <token> - Close a position
/closeall - Close ALL positions at current prices

*Settings*
/stop_loss <pct> - Set stop loss %
/take_profit <pct> - Set take profit %

*Examples*
/stop_loss 15
/take_profit 40
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
        self.application.add_handler(CommandHandler("settings", self.cmd_settings))
        self.application.add_handler(CommandHandler("stop_loss", self.cmd_stop_loss))
        self.application.add_handler(CommandHandler("take_profit", self.cmd_take_profit))
        self.application.add_handler(CommandHandler("close", self.cmd_close))
        self.application.add_handler(CommandHandler("closeall", self.cmd_closeall))
        self.application.add_handler(CommandHandler("export", self.cmd_export))
        self.application.add_handler(CommandHandler("pause", self.cmd_pause))
        self.application.add_handler(CommandHandler("resume", self.cmd_resume))
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
