#!/usr/bin/env python3
"""
Check trading bot performance and statistics
"""

import os
import sys

def check_logs():
    """Check if log file exists and show recent trades"""
    log_file = "trading_bot.log"

    if not os.path.exists(log_file):
        print(f"❌ Log file '{log_file}' not found")
        return

    print(f"📄 Reading {log_file}...\n")

    # Read log file
    with open(log_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    if not lines:
        print("⚠️  Log file is empty")
        return

    print(f"Total log lines: {len(lines)}\n")

    # Count trades
    buy_count = sum(1 for line in lines if "PAPER BUY" in line or "TRADE EXECUTED: BUY" in line)
    sell_count = sum(1 for line in lines if "PAPER SELL" in line or "TRADE EXECUTED: SELL" in line)

    print(f"📊 Trading Statistics:")
    print(f"   Total Buys: {buy_count}")
    print(f"   Total Sells: {sell_count}")
    print(f"   Total Trades: {buy_count + sell_count}\n")

    # Show recent trades
    trade_lines = [line for line in lines if "TRADE EXECUTED" in line or "PAPER BUY" in line or "PAPER SELL" in line]

    if trade_lines:
        print(f"📝 Recent Trades (last 10):")
        for line in trade_lines[-10:]:
            print(f"   {line.strip()}")
    else:
        print("⚠️  No trades found in logs")

    # Show any errors
    error_lines = [line for line in lines if "ERROR" in line]
    if error_lines:
        print(f"\n❌ Recent Errors (last 5):")
        for line in error_lines[-5:]:
            print(f"   {line.strip()}")

if __name__ == "__main__":
    check_logs()
