#!/usr/bin/env python3
"""
Analysis Script for Hybrid Bot Performance
Run this after 200-300 trades to analyze TIER 2 filter effectiveness
"""

import json
from datetime import datetime
from collections import defaultdict

def analyze_hybrid_bot_performance():
    """Analyze hybrid bot's trading performance"""

    print("=" * 80)
    print("🤖 HYBRID BOT PERFORMANCE ANALYSIS (TIER 2 BINARY FILTERS)")
    print("=" * 80)
    print()

    # Load state file
    try:
        with open('paper_trading_state.json', 'r') as f:
            state = json.load(f)
    except FileNotFoundError:
        print("❌ State file not found. Make sure bot has been running.")
        return

    # Extract data
    total_trades = len(state.get('trades', []))
    balance = state.get('balance', 1000)
    starting_balance = state.get('starting_balance', 1000)

    if total_trades == 0:
        print("❌ No trades found. Let the bot run longer.")
        return

    print(f"📊 OVERVIEW")
    print(f"{'─' * 80}")
    print(f"Total Trades: {total_trades}")
    print(f"Starting Balance: ${starting_balance:,.2f}")
    print(f"Current Balance: ${balance:,.2f}")
    print(f"Total P&L: ${balance - starting_balance:+,.2f} ({(balance/starting_balance - 1)*100:+.2f}%)")
    print()

    # Analyze trades
    trades = state.get('trades', [])
    wins = [t for t in trades if t.get('pnl', 0) > 0]
    losses = [t for t in trades if t.get('pnl', 0) <= 0]

    win_rate = len(wins) / total_trades * 100 if total_trades > 0 else 0

    print(f"🎯 WIN RATE")
    print(f"{'─' * 80}")
    print(f"Winners: {len(wins)} ({len(wins)/total_trades*100:.1f}%)")
    print(f"Losers: {len(losses)} ({len(losses)/total_trades*100:.1f}%)")
    print(f"Win Rate: {win_rate:.2f}%")
    print()

    # P&L Analysis
    if wins:
        avg_win = sum(t['pnl'] for t in wins) / len(wins)
        max_win = max(t['pnl'] for t in wins)
        total_wins = sum(t['pnl'] for t in wins)
        print(f"💰 WINNING TRADES")
        print(f"{'─' * 80}")
        print(f"Average Win: ${avg_win:.2f}")
        print(f"Largest Win: ${max_win:.2f}")
        print(f"Total Profit from Wins: ${total_wins:,.2f}")
        print()

    if losses:
        avg_loss = sum(t['pnl'] for t in losses) / len(losses)
        max_loss = min(t['pnl'] for t in losses)
        total_losses = sum(t['pnl'] for t in losses)
        print(f"📉 LOSING TRADES")
        print(f"{'─' * 80}")
        print(f"Average Loss: ${avg_loss:.2f}")
        print(f"Largest Loss: ${max_loss:.2f}")
        print(f"Total Loss from Losers: ${total_losses:,.2f}")
        print()

    # Profit Factor
    if losses and wins:
        profit_factor = abs(sum(t['pnl'] for t in wins) / sum(t['pnl'] for t in losses))
        print(f"📊 PROFIT FACTOR")
        print(f"{'─' * 80}")
        print(f"Profit Factor: {profit_factor:.2f}")
        print(f"(>1.0 = profitable, >2.0 = excellent)")
        print()

    # Exit Reason Analysis
    exit_reasons = defaultdict(int)
    for trade in trades:
        reason = trade.get('reason', 'unknown')
        exit_reasons[reason] += 1

    print(f"🚪 EXIT REASONS")
    print(f"{'─' * 80}")
    for reason, count in sorted(exit_reasons.items(), key=lambda x: -x[1]):
        percentage = count / total_trades * 100
        print(f"{reason:30s}: {count:4d} ({percentage:5.1f}%)")
    print()

    # Token Source Analysis (where good tokens come from)
    source_performance = defaultdict(lambda: {'wins': 0, 'losses': 0, 'total_pnl': 0})
    for trade in trades:
        source = trade.get('token_source', 'unknown')
        is_win = trade.get('pnl', 0) > 0
        pnl = trade.get('pnl', 0)

        if is_win:
            source_performance[source]['wins'] += 1
        else:
            source_performance[source]['losses'] += 1
        source_performance[source]['total_pnl'] += pnl

    print(f"📡 TOKEN SOURCE PERFORMANCE")
    print(f"{'─' * 80}")
    print(f"{'Source':<15} {'Trades':>8} {'Win Rate':>10} {'Total P&L':>12}")
    print(f"{'─' * 15} {'─' * 8} {'─' * 10} {'─' * 12}")
    for source, stats in sorted(source_performance.items(), key=lambda x: -x[1]['total_pnl']):
        total = stats['wins'] + stats['losses']
        win_rate = stats['wins'] / total * 100 if total > 0 else 0
        pnl = stats['total_pnl']
        print(f"{source:<15} {total:8d} {win_rate:9.1f}% ${pnl:11.2f}")
    print()

    # Entry Metrics
    entry_prices = [t.get('entry_price', 0) for t in trades if t.get('entry_price', 0) > 0]
    entry_liquidity = [t.get('entry_liquidity', 0) for t in trades if t.get('entry_liquidity', 0) > 0]
    entry_volume = [t.get('entry_volume_24h', 0) for t in trades if t.get('entry_volume_24h', 0) > 0]

    if entry_prices:
        print(f"📍 ENTRY METRICS")
        print(f"{'─' * 80}")
        print(f"Avg Entry Price: ${sum(entry_prices)/len(entry_prices):.6f}")
        print(f"Min Entry Price: ${min(entry_prices):.6f}")
        print(f"Max Entry Price: ${max(entry_prices):.6f}")
        if entry_liquidity:
            print(f"Avg Entry Liquidity: ${sum(entry_liquidity)/len(entry_liquidity):,.0f}")
        if entry_volume:
            print(f"Avg Entry Volume: ${sum(entry_volume)/len(entry_volume):,.0f}")
        print()

    # Recommendations
    print(f"💡 RECOMMENDATIONS")
    print(f"{'─' * 80}")

    if win_rate < 30:
        print("⚠️  Win rate is low (<30%). Consider:")
        print("   • Increasing MIN_ENTRY_LIQUIDITY")
        print("   • Increasing MIN_24H_VOLUME")
        print("   • Tightening MIN_VOLUME_LIQUIDITY_RATIO")
    elif win_rate > 50:
        print("✅ Excellent win rate (>50%)! TIER 2 filters working well!")
    else:
        print("✅ Good win rate (30-50%). Filters are effective.")

    if wins and losses:
        if profit_factor > 2.0:
            print("✅ Excellent profit factor (>2.0)! Big winners covering small losses.")
        elif profit_factor > 1.0:
            print("✅ Profitable (profit factor >1.0) but could be better.")
        else:
            print("⚠️  Profit factor <1.0. Losses outweigh wins. Tighten filters!")

    print()
    print("=" * 80)
    print("Analysis complete! Compare this to old bot's 21.4% win rate.")
    print("=" * 80)

if __name__ == '__main__':
    analyze_hybrid_bot_performance()
