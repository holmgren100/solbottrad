#!/usr/bin/env python3
"""
Check paper trading state file location and contents
"""

import json
import os
from datetime import datetime

def check_state():
    """Check if state file exists and show its contents"""
    state_file = 'paper_trading_state.json'

    # Check current working directory
    cwd = os.getcwd()
    state_path = os.path.join(cwd, state_file)

    print("🔍 Paper Trading State Check")
    print("=" * 60)
    print(f"\nCurrent working directory: {cwd}")
    print(f"Expected state file path: {state_path}\n")

    if not os.path.exists(state_path):
        print(f"❌ State file NOT found at {state_path}")
        print("\nThis means:")
        print("  • The bot hasn't saved any state yet, OR")
        print("  • You're running from a different directory than where the bot runs\n")
        print("Try running this script from the same directory where you run the bot")
        return

    print(f"✅ State file found!\n")

    try:
        with open(state_path, 'r') as f:
            state = json.load(f)

        # Show file info
        file_size = os.path.getsize(state_path)
        file_mtime = datetime.fromtimestamp(os.path.getmtime(state_path))

        print(f"📄 File Details:")
        print(f"   Size: {file_size:,} bytes")
        print(f"   Last modified: {file_mtime.strftime('%Y-%m-%d %H:%M:%S')}")
        print()

        # Show state contents
        cash = state.get('current_capital', 0)
        initial_capital = state.get('initial_capital', 1000)
        positions = state.get('positions', {})
        trades = state.get('trades', [])

        total_pnl = cash - initial_capital
        pnl_percent = (total_pnl / initial_capital) * 100 if initial_capital > 0 else 0

        print(f"💰 Portfolio State:")
        print(f"   Initial Capital: ${initial_capital:.2f}")
        print(f"   Current Cash: ${cash:.2f}")
        print(f"   Total P&L: ${total_pnl:.2f} ({pnl_percent:+.2f}%)")
        print()

        print(f"📊 Open Positions: {len(positions)}")
        if positions:
            for token_addr, pos in positions.items():
                entry_price = pos.get('entry_price', 0)
                current_price = pos.get('current_price', 0)
                amount = pos.get('amount_usd', 0)

                pnl_pct = ((current_price - entry_price) / entry_price * 100) if entry_price > 0 else 0

                print(f"\n   🔹 {token_addr[:12]}...")
                print(f"      Entry: ${entry_price:.8f}")
                print(f"      Current: ${current_price:.8f}")
                print(f"      P&L: {pnl_pct:+.2f}%")
                print(f"      Size: ${amount:.2f}")

        print(f"\n📈 Trade History: {len(trades)} trades")
        if trades:
            print("\n   Recent trades (last 5):")
            for trade in trades[-5:]:
                timestamp = trade.get('timestamp', 'Unknown')[:19]
                action = trade.get('action', 'unknown')
                token = trade.get('token_address', 'Unknown')[:12]
                pnl = trade.get('pnl', 0)

                emoji = "🟢" if action == "buy" else ("🔴" if pnl >= 0 else "💔")
                print(f"   {emoji} {timestamp} - {action.upper()} {token}... (P&L: ${pnl:.2f})")

        print("\n" + "=" * 60)
        print("✅ State file is working correctly!")
        print("   Your positions and capital should persist across restarts.\n")

    except json.JSONDecodeError as e:
        print(f"❌ Error: State file is corrupted (invalid JSON)")
        print(f"   {e}\n")
        print("You may need to delete the file and let the bot create a new one.")
    except Exception as e:
        print(f"❌ Error reading state file: {e}")

if __name__ == "__main__":
    check_state()
