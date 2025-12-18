"""
Terminal-based monitoring dashboard for the Solana Trading Bot.
Shows real-time portfolio status, positions, and recent activity.

Run with: python monitor.py
"""

import os
import sys
import time
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from src.config import settings
except:
    pass

# Terminal colors
class Colors:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GRAY = '\033[90m'

def clear_screen():
    """Clear terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')

def parse_log_for_positions():
    """Parse log file to find current positions."""
    log_file = 'trading_bot.log'
    positions = {}

    if not os.path.exists(log_file):
        return positions

    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        for line in lines:
            # Look for buy trades
            if '[PAPER] BUY' in line:
                parts = line.split()
                for i, part in enumerate(parts):
                    if part == 'BUY' and i+1 < len(parts):
                        token = parts[i+1]
                        # Extract price
                        for j in range(i, min(i+10, len(parts))):
                            if parts[j].startswith('$') and '.' in parts[j]:
                                try:
                                    price = float(parts[j].replace('$', '').replace(',', ''))
                                    # Extract size
                                    for k in range(j, min(j+5, len(parts))):
                                        if parts[k].startswith('$') and parts[k] != parts[j]:
                                            try:
                                                size = float(parts[k].replace('$', '').replace(',', ''))
                                                positions[token] = {
                                                    'entry_price': price,
                                                    'size': size,
                                                    'current_price': price
                                                }
                                                break
                                            except:
                                                pass
                                    break
                                except:
                                    pass
                        break

            # Look for sell trades (remove from positions)
            elif '[PAPER] SELL' in line:
                parts = line.split()
                for i, part in enumerate(parts):
                    if part == 'SELL' and i+1 < len(parts):
                        token = parts[i+1]
                        if token in positions:
                            del positions[token]
                        break

        return positions
    except Exception as e:
        return {}

def get_recent_trades(limit=10):
    """Get recent trades from log file."""
    log_file = 'trading_bot.log'
    trades = []

    if not os.path.exists(log_file):
        return trades

    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        for line in reversed(lines):
            if '[PAPER] BUY' in line or '[PAPER] SELL' in line:
                # Extract timestamp
                timestamp = line.split(' - ')[0] if ' - ' in line else ''
                trades.append({
                    'timestamp': timestamp,
                    'action': 'BUY' if 'BUY' in line else 'SELL',
                    'line': line.strip()
                })
                if len(trades) >= limit:
                    break

        return trades
    except Exception as e:
        return []

def display_dashboard():
    """Display the monitoring dashboard."""
    clear_screen()

    # Header
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'🤖 SOLANA TRADING BOT - LIVE MONITOR':^70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*70}{Colors.RESET}")
    print(f"{Colors.GRAY}Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Colors.RESET}\n")

    # Bot status
    print(f"{Colors.BOLD}📊 BOT STATUS{Colors.RESET}")
    print(f"{'─'*70}")

    try:
        mode = "📄 Paper Trading" if settings.is_paper_trading() else "💰 Live Trading"
        print(f"Mode: {Colors.YELLOW}{mode}{Colors.RESET}")
        print(f"Stop Loss: {Colors.RED}{settings.risk.stop_loss_percent}%{Colors.RESET}")
        print(f"Take Profit: {Colors.GREEN}{settings.risk.take_profit_percent}%{Colors.RESET}")
        print(f"Max Position: ${settings.trading.max_position_size}")
    except:
        print(f"{Colors.GRAY}(Settings not available - bot may not be running){Colors.RESET}")

    print()

    # Portfolio summary
    positions = parse_log_for_positions()
    total_invested = sum(pos['size'] for pos in positions.values())
    initial_capital = 1000.0
    cash = initial_capital - total_invested

    print(f"{Colors.BOLD}💰 PORTFOLIO{Colors.RESET}")
    print(f"{'─'*70}")
    print(f"Initial Capital: ${initial_capital:.2f}")
    print(f"Cash Available:  {Colors.GREEN}${cash:.2f}{Colors.RESET}")
    print(f"Invested:        {Colors.YELLOW}${total_invested:.2f}{Colors.RESET}")
    print(f"Total Value:     {Colors.CYAN}${initial_capital:.2f}{Colors.RESET}")
    print()

    # Open positions
    print(f"{Colors.BOLD}📈 OPEN POSITIONS ({len(positions)}){Colors.RESET}")
    print(f"{'─'*70}")

    if positions:
        for token, pos in positions.items():
            entry = pos['entry_price']
            current = pos['current_price']
            size = pos['size']
            pnl_pct = 0.0  # We don't have current price, so 0%

            pnl_color = Colors.GRAY
            symbol = "⚪"

            print(f"{symbol} {Colors.BOLD}{token[:12]}...{Colors.RESET}")
            print(f"   Entry: ${entry:.8f} | Size: ${size:.2f}")
            print(f"   Current: ${current:.8f} | P&L: {pnl_color}{pnl_pct:+.2f}%{Colors.RESET}")
            print()
    else:
        print(f"{Colors.GRAY}No open positions{Colors.RESET}")
        print()

    # Recent activity
    trades = get_recent_trades(5)
    print(f"{Colors.BOLD}📜 RECENT ACTIVITY (Last 5 trades){Colors.RESET}")
    print(f"{'─'*70}")

    if trades:
        for trade in trades:
            if trade['action'] == 'BUY':
                icon = f"{Colors.GREEN}🟢 BUY{Colors.RESET}"
            else:
                icon = f"{Colors.RED}🔴 SELL{Colors.RESET}"

            timestamp = trade['timestamp'][-8:] if len(trade['timestamp']) >= 8 else trade['timestamp']
            print(f"{timestamp} {icon}")
    else:
        print(f"{Colors.GRAY}No trades yet{Colors.RESET}")

    print()

    # Footer
    print(f"{'─'*70}")
    print(f"{Colors.GRAY}💡 Use Telegram commands to control the bot{Colors.RESET}")
    print(f"{Colors.GRAY}   /status - Portfolio | /pause - Pause trading{Colors.RESET}")
    print(f"{Colors.GRAY}   Press Ctrl+C to exit this monitor{Colors.RESET}")
    print(f"{Colors.CYAN}{'='*70}{Colors.RESET}")

def main():
    """Main monitoring loop."""
    print(f"{Colors.CYAN}Starting Trading Bot Monitor...{Colors.RESET}")
    print(f"{Colors.GRAY}Refreshing every 10 seconds...{Colors.RESET}\n")
    time.sleep(2)

    try:
        while True:
            display_dashboard()
            time.sleep(10)  # Refresh every 10 seconds
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Monitor stopped.{Colors.RESET}")
        print(f"{Colors.GRAY}Bot is still running in the background.{Colors.RESET}\n")

if __name__ == "__main__":
    main()
