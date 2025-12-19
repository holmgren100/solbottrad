"""
Telegram bot command handler for controlling the trading bot.
Allows users to check status, modify settings, and control the bot via Telegram.
"""

import asyncio
import os
from datetime import datetime
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
            # Works for both paper and live trading
            engine = self.bot.trading_engine
            positions = engine.position_manager.get_all_positions()
            stats = engine.get_performance_summary()

            mode_emoji = "📄" if self.bot.settings.is_paper_trading() else "💰"
            mode_text = "Paper" if self.bot.settings.is_paper_trading() else "LIVE"

            message = f"📊 *Trading Bot Status* ({mode_emoji} {mode_text})\n\n"
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

    async def cmd_cleanup(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Cleanup stuck positions (zero liquidity, frozen, too old).
        Frees up position slots for new trades.
        """
        if not self.is_authorized(update):
            await update.message.reply_text("⛔ Unauthorized")
            return

        try:
            # Get stuck position management settings
            stuck_liquidity = self.bot.trading_engine.stuck_liquidity_threshold
            stuck_hours = self.bot.trading_engine.stuck_time_hours
            max_age_hours = self.bot.trading_engine.max_position_age_hours

            # Find stuck positions
            stuck_positions = self.bot.trading_engine.position_manager.get_stuck_positions(
                min_liquidity=stuck_liquidity,
                stuck_hours=stuck_hours
            )

            # Find old positions
            old_positions = []
            for token_address, position in self.bot.trading_engine.position_manager.open_positions.items():
                age_hours = (datetime.now() - position.entry_time).total_seconds() / 3600
                if age_hours > max_age_hours:
                    old_positions.append(token_address)

            # Combine unique positions to cleanup
            to_cleanup = list(set(stuck_positions + old_positions))

            if not to_cleanup:
                await update.message.reply_text("✅ No stuck positions found!\n"
                                              "All positions are healthy.")
                return

            await update.message.reply_text(
                f"🗑️  Found {len(to_cleanup)} stuck position(s):\n"
                f"   Stuck (low liquidity): {len(stuck_positions)}\n"
                f"   Too old (>{max_age_hours:.0f}h): {len(old_positions)}\n\n"
                f"Forcing cleanup..."
            )

            # Force close all stuck positions
            cleaned = 0
            total_loss = 0.0
            results = []

            for token_address in to_cleanup:
                position = self.bot.trading_engine.position_manager.get_position(token_address)
                if not position:
                    continue

                # Determine reason
                age_hours = (datetime.now() - position.entry_time).total_seconds() / 3600
                is_stuck = token_address in stuck_positions
                is_old = token_address in old_positions

                if is_stuck and is_old:
                    reason = f"stuck+old ({age_hours:.1f}h)"
                elif is_stuck:
                    reason = f"stuck (liq: ${position.current_liquidity:.0f})"
                else:
                    reason = f"too old ({age_hours:.1f}h)"

                # Force close
                trade = self.bot.trading_engine.position_manager.force_close_position(
                    token_address,
                    reason='manual_cleanup'
                )

                if trade:
                    cleaned += 1
                    total_loss += abs(trade.pnl)
                    results.append(f"🗑️  {token_address[:8]}: {reason}")

            # Send summary
            open_slots = self.bot.trading_engine.position_manager.max_open_positions - len(self.bot.trading_engine.position_manager.open_positions)
            message = f"✅ Cleanup Complete!\n\n"
            message += f"Positions cleaned: {cleaned}\n"
            message += f"Total write-off: ${total_loss:.2f}\n"
            message += f"Slots freed: {cleaned}\n"
            message += f"Available slots: {open_slots}\n\n"
            message += "Cleaned:\n" + "\n".join(results[:10])  # Show first 10
            if len(results) > 10:
                message += f"\n... and {len(results) - 10} more"

            await update.message.reply_text(message)
            logger.info(f"Manual cleanup via /cleanup: {cleaned} positions, ${total_loss:.2f} write-off")

        except Exception as e:
            logger.error(f"Error in /cleanup command: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")

    async def cmd_export(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Export trade history to CSV file with optional filters.

        Usage:
            /export - Export all trades
            /export 100 - Export latest 100 trades
            /export daily - Export last 24 hours
            /export weekly - Export last 7 days
            /export monthly - Export last 30 days
        """
        if not self.is_authorized(update):
            await update.message.reply_text("⛔ Unauthorized")
            return

        try:
            from datetime import datetime

            # Parse arguments
            timeframe = 'all'
            limit = None

            if context.args and len(context.args) > 0:
                arg = context.args[0].lower()

                # Check if it's a number (limit)
                if arg.isdigit():
                    limit = int(arg)
                    timeframe = 'all'
                # Check if it's a timeframe
                elif arg in ['daily', 'weekly', 'monthly']:
                    timeframe = arg
                    limit = None
                else:
                    await update.message.reply_text(
                        "❌ Invalid argument\n\n"
                        "Usage:\n"
                        "/export - All trades\n"
                        "/export 100 - Latest 100 trades\n"
                        "/export daily - Last 24 hours\n"
                        "/export weekly - Last 7 days\n"
                        "/export monthly - Last 30 days"
                    )
                    return

            # Export trades to CSV
            filepath = f'data/trade_history_{timeframe}.csv'
            trade_count = self.bot.trading_engine.position_manager.export_to_csv(
                filepath=filepath,
                timeframe=timeframe,
                limit=limit
            )

            if trade_count == 0:
                await update.message.reply_text("📭 No trades to export for this timeframe")
                return

            # Build description
            if limit:
                description = f"Latest {limit} trades"
            elif timeframe == 'daily':
                description = "Last 24 hours"
            elif timeframe == 'weekly':
                description = "Last 7 days"
            elif timeframe == 'monthly':
                description = "Last 30 days"
            else:
                description = "All trades"

            # Send file info
            await update.message.reply_text(
                f"📊 Exporting {trade_count} trades ({description})...\n\n"
                f"✅ *Enhanced Columns:*\n"
                f"• Date, Time, Day of Week, Hour\n"
                f"• Token Address & Symbol\n"
                f"• Entry/Exit Prices\n"
                f"• Price Change ($ and %)\n"
                f"• Position Size & Quantity\n"
                f"• Tokens per Dollar\n"
                f"• Entry/Exit Liquidity\n"
                f"• Liquidity Change (%)\n"
                f"• Volume 24h & Volume 1h\n"
                f"• Opportunity Score (0-100)\n"
                f"• Token Source (Jupiter/DexScreener)\n"
                f"• DEX Platform (Raydium/Orca/etc.)\n"
                f"• PnL ($ and %)\n"
                f"• Win/Loss\n"
                f"• Duration (hours & minutes)\n"
                f"• Close Reason\n"
                f"• Volume Fallback\n"
                f"• Strategy Used\n"
                f"• Token Age at Entry\n\n"
                f"📈 Ready for Excel analysis!",
                parse_mode='Markdown'
            )

            # Send CSV file
            with open(filepath, 'rb') as f:
                filename = f"trades_{timeframe}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                await update.message.reply_document(
                    document=f,
                    filename=filename,
                    caption=f"✅ {trade_count} trades ({description})"
                )

            logger.info(f"Exported {trade_count} trades via /export command (timeframe: {timeframe}, limit: {limit})")

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

    async def cmd_daily(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show daily trade summary."""
        if not self.is_authorized(update):
            await update.message.reply_text("⛔ Unauthorized")
            return

        try:
            from datetime import datetime, timedelta
            import csv

            # Load trades from last 24 hours from CSV
            trades_file = "data/ml_trades.csv"
            if not os.path.exists(trades_file):
                await update.message.reply_text("📭 No trade history found")
                return

            now = datetime.now()
            yesterday = now - timedelta(hours=24)
            daily_trades = []

            with open(trades_file, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        # Parse date and time from CSV
                        trade_date = row.get('Date', '')
                        trade_time = row.get('Time', '')
                        if trade_date and trade_time:
                            trade_datetime = datetime.strptime(f"{trade_date} {trade_time}", "%Y-%m-%d %H:%M:%S")
                            if trade_datetime >= yesterday:
                                # Convert CSV row to trade dict
                                pnl = float(row.get('PnL ($)', 0))
                                trade = {
                                    'pnl': pnl,
                                    'win': row.get('Win/Loss', '').lower() == 'win',
                                    'exit_reason': row.get('Exit Reason', 'unknown'),
                                    'symbol': row.get('Symbol', ''),
                                    'pnl_percent': float(row.get('PnL (%)', 0))
                                }
                                daily_trades.append(trade)
                    except Exception as e:
                        logger.debug(f"Skipping row in /daily: {e}")
                        continue

            if not daily_trades:
                await update.message.reply_text("📭 No trades in the last 24 hours")
                return

            # Calculate stats
            wins = [t for t in daily_trades if t.get('win', False)]
            losses = [t for t in daily_trades if not t.get('win', False)]
            total_pnl = sum(t.get('pnl', 0) for t in daily_trades)
            win_rate = len(wins) / len(daily_trades) * 100 if daily_trades else 0

            # Exit reason breakdown
            exit_reasons = {}
            for t in daily_trades:
                reason = t.get('exit_reason', 'unknown')
                exit_reasons[reason] = exit_reasons.get(reason, 0) + 1

            # Build message
            message = f"📊 *Daily Summary* (24h)\n"
            message += f"━━━━━━━━━━━━━━━━\n\n"
            message += f"💰 *Performance*\n"
            message += f"Total P&L: ${total_pnl:+.2f}\n"
            message += f"Total Trades: {len(daily_trades)}\n"
            message += f"Win Rate: {win_rate:.1f}%\n"
            message += f"Wins/Losses: {len(wins)}/{len(losses)}\n\n"

            if wins:
                avg_win = sum(t.get('pnl', 0) for t in wins) / len(wins)
                message += f"🟢 Average Win: ${avg_win:.2f}\n"
            if losses:
                avg_loss = sum(t.get('pnl', 0) for t in losses) / len(losses)
                message += f"🔴 Average Loss: ${avg_loss:.2f}\n"

            message += f"\n📝 *Exit Reasons*\n"
            for reason, count in sorted(exit_reasons.items(), key=lambda x: x[1], reverse=True):
                message += f"  • {reason.replace('_', ' ').title()}: {count}\n"

            # Current status
            engine = self.bot.trading_engine
            positions = engine.position_manager.get_all_positions()
            message += f"\n📈 *Current*\n"
            message += f"Open Positions: {len(positions)}\n"
            message += f"Available Slots: {engine.position_manager.max_open_positions - len(positions)}\n"

            await update.message.reply_text(message, parse_mode='Markdown')

        except Exception as e:
            logger.error(f"Error in /daily command: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")

    async def cmd_weekly(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show weekly trade analysis."""
        if not self.is_authorized(update):
            await update.message.reply_text("⛔ Unauthorized")
            return

        try:
            from datetime import datetime, timedelta
            import csv

            # Load trades from last 7 days from CSV
            trades_file = "data/ml_trades.csv"
            if not os.path.exists(trades_file):
                await update.message.reply_text("📭 No trade history found")
                return

            now = datetime.now()
            week_ago = now - timedelta(days=7)
            weekly_trades = []

            with open(trades_file, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        # Parse date and time from CSV
                        trade_date = row.get('Date', '')
                        trade_time = row.get('Time', '')
                        if trade_date and trade_time:
                            trade_datetime = datetime.strptime(f"{trade_date} {trade_time}", "%Y-%m-%d %H:%M:%S")
                            if trade_datetime >= week_ago:
                                # Convert CSV row to trade dict
                                pnl = float(row.get('PnL ($)', 0))
                                trade = {
                                    'pnl': pnl,
                                    'win': row.get('Win/Loss', '').lower() == 'win',
                                    'exit_reason': row.get('Exit Reason', 'unknown'),
                                    'symbol': row.get('Symbol', ''),
                                    'pnl_percent': float(row.get('PnL (%)', 0)),
                                    'exit_time': trade_datetime
                                }
                                weekly_trades.append(trade)
                    except Exception as e:
                        logger.debug(f"Skipping row in /weekly: {e}")
                        continue

            if not weekly_trades:
                await update.message.reply_text("📭 No trades in the last 7 days")
                return

            # Calculate stats
            wins = [t for t in weekly_trades if t.get('win', False)]
            losses = [t for t in weekly_trades if not t.get('win', False)]
            total_pnl = sum(t.get('pnl', 0) for t in weekly_trades)
            win_rate = len(wins) / len(weekly_trades) * 100 if weekly_trades else 0

            # Daily breakdown
            daily_pnl = {}
            for t in weekly_trades:
                day = t['exit_time'].strftime('%Y-%m-%d')
                daily_pnl[day] = daily_pnl.get(day, 0) + t.get('pnl', 0)

            # Best/worst trades
            sorted_trades = sorted(weekly_trades, key=lambda x: x.get('pnl_percent', 0), reverse=True)
            best_trade = sorted_trades[0] if sorted_trades else None
            worst_trade = sorted_trades[-1] if sorted_trades else None

            # Build message
            message = f"📊 *Weekly Summary* (7 days)\n"
            message += f"━━━━━━━━━━━━━━━━\n\n"
            message += f"💰 *Performance*\n"
            message += f"Total P&L: ${total_pnl:+.2f}\n"
            message += f"Total Trades: {len(weekly_trades)}\n"
            message += f"Win Rate: {win_rate:.1f}%\n"
            message += f"Wins/Losses: {len(wins)}/{len(losses)}\n\n"

            if best_trade:
                message += f"🏆 *Best Trade*\n"
                message += f"  {best_trade.get('symbol', 'Unknown')}: {best_trade.get('pnl_percent', 0):+.1f}% (${best_trade.get('pnl', 0):+.2f})\n\n"

            if worst_trade:
                message += f"💔 *Worst Trade*\n"
                message += f"  {worst_trade.get('symbol', 'Unknown')}: {worst_trade.get('pnl_percent', 0):+.1f}% (${worst_trade.get('pnl', 0):+.2f})\n\n"

            message += f"📅 *Daily Breakdown*\n"
            for day in sorted(daily_pnl.keys(), reverse=True)[:7]:
                pnl = daily_pnl[day]
                emoji = "🟢" if pnl > 0 else "🔴" if pnl < 0 else "⚪"
                message += f"  {emoji} {day}: ${pnl:+.2f}\n"

            await update.message.reply_text(message, parse_mode='Markdown')

        except Exception as e:
            logger.error(f"Error in /weekly command: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")

    async def cmd_apis(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Test all API connections."""
        if not self.is_authorized(update):
            await update.message.reply_text("⛔ Unauthorized")
            return

        try:
            await update.message.reply_text("🔄 Testing all APIs...\n"
                                           "This may take a moment...")

            results = []
            total_tests = 0
            passed = 0

            # Test Jupiter API
            total_tests += 1
            try:
                test_token = "So11111111111111111111111111111111111111112"  # SOL
                data = await self.bot.jupiter.get_token_price_data(test_token)
                if data and data.get('price_usd', 0) > 0:
                    results.append("🟢 Jupiter: Online")
                    passed += 1
                else:
                    results.append("🔴 Jupiter: No data")
            except Exception as e:
                results.append(f"🔴 Jupiter: {str(e)[:50]}")

            # Test DexScreener API
            total_tests += 1
            try:
                test_token = "So11111111111111111111111111111111111111112"
                data = await self.bot.dexscreener.get_token_profile(test_token)
                if data and data.get('price_usd', 0) > 0:
                    results.append("🟢 DexScreener: Online")
                    passed += 1
                else:
                    results.append("🔴 DexScreener: No data")
            except Exception as e:
                results.append(f"🔴 DexScreener: {str(e)[:50]}")

            # Test Birdeye API (if enabled)
            if hasattr(self.bot, 'birdeye') and self.bot.birdeye:
                total_tests += 1
                try:
                    # Test Birdeye health check
                    is_healthy = await self.bot.birdeye.health_check()
                    if is_healthy:
                        results.append("🟢 Birdeye: Online")
                        passed += 1
                    else:
                        results.append("🔴 Birdeye: Health check failed")
                except Exception as e:
                    error_msg = str(e)[:50]
                    # Check if it's the CU limit error
                    if "Compute units" in str(e) or "limit exceeded" in str(e):
                        results.append("🟡 Birdeye: CU limit hit (resets monthly)")
                    else:
                        results.append(f"🔴 Birdeye: {error_msg}")

            # Test RugCheck API (if enabled)
            if hasattr(self.bot, 'enhanced_bot') and self.bot.enhanced_bot:
                total_tests += 1
                try:
                    test_token = "So11111111111111111111111111111111111111112"
                    data = await self.bot.enhanced_bot.rugcheck.get_token_report(test_token)
                    if data:
                        results.append("🟢 RugCheck: Online")
                        passed += 1
                    else:
                        results.append("🟡 RugCheck: No data (may not exist)")
                        passed += 1  # Not an error
                except Exception as e:
                    results.append(f"🔴 RugCheck: {str(e)[:50]}")

            # Test CoinGecko API (Top Gainers source)
            if hasattr(self.bot, 'coingecko') and self.bot.coingecko:
                total_tests += 1
                try:
                    # Test CoinGecko health check (ping endpoint)
                    is_healthy = await self.bot.coingecko.health_check()
                    if is_healthy:
                        results.append("🟢 CoinGecko: Online")
                        passed += 1
                    else:
                        results.append("🔴 CoinGecko: Health check failed")
                except Exception as e:
                    results.append(f"🔴 CoinGecko: {str(e)[:50]}")

            # Test Apify API (if enabled)
            if hasattr(self.bot, 'apify') and self.bot.apify:
                total_tests += 1
                try:
                    # Test Apify health check
                    is_healthy = await self.bot.apify.health_check()
                    if is_healthy:
                        results.append("🟢 Apify: Online")
                        passed += 1
                    else:
                        results.append("🔴 Apify: Health check failed")
                except Exception as e:
                    results.append(f"🔴 Apify: {str(e)[:50]}")

            # Build summary
            message = f"🔧 *API Status Report*\n"
            message += f"━━━━━━━━━━━━━━━━\n\n"
            message += f"✅ Passed: {passed}/{total_tests}\n\n"
            message += "\n".join(results)
            message += f"\n\n💡 If APIs are down, bot will use fallback sources"

            await update.message.reply_text(message, parse_mode='Markdown')

        except Exception as e:
            logger.error(f"Error in /apis command: {e}")
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
/daily - Daily trade summary (24h)
/weekly - Weekly trade analysis (7 days)
/apis - Test all API connections

*Export Data*
/export - Export ALL trades to CSV
/export 100 - Export latest 100 trades
/export daily - Export last 24 hours
/export weekly - Export last 7 days
/export monthly - Export last 30 days

*Controls*
/pause - Pause trading
/resume - Resume trading
/close <token> - Close a position
/closeall - Close ALL positions at current prices
/cleanup - Force cleanup stuck positions (zero liquidity)

*Settings*
/stop\\_loss <pct> - Set stop loss %
/take\\_profit <pct> - Set take profit %

*Examples*
/stop\\_loss 10
/export 100
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
        self.application.add_handler(CommandHandler("daily", self.cmd_daily))
        self.application.add_handler(CommandHandler("weekly", self.cmd_weekly))
        self.application.add_handler(CommandHandler("apis", self.cmd_apis))
        self.application.add_handler(CommandHandler("stop_loss", self.cmd_stop_loss))
        self.application.add_handler(CommandHandler("take_profit", self.cmd_take_profit))
        self.application.add_handler(CommandHandler("close", self.cmd_close))
        self.application.add_handler(CommandHandler("closeall", self.cmd_closeall))
        self.application.add_handler(CommandHandler("cleanup", self.cmd_cleanup))
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
