#!/usr/bin/env python3
"""Check paper trading state and show what happened."""

import json
from pathlib import Path

state_file = Path("/root/solbottrad/paper_trading_state.json")

if not state_file.exists():
    print("❌ paper_trading_state.json not found!")
    exit(1)

with open(state_file, 'r') as f:
    state = json.load(f)

print("=" * 60)
print("PAPER TRADING STATE ANALYSIS")
print("=" * 60)

# Show keys
print("\nAvailable keys in state:")
print(list(state.keys()))

# Try to show capital/balance
if 'capital' in state:
    capital = state['capital']
elif 'balance' in state:
    capital = state['balance']
elif 'cash' in state:
    capital = state['cash']
else:
    print("\n⚠️  No capital/balance/cash field found!")
    print("State structure:")
    print(json.dumps(state, indent=2)[:1000])
    exit(0)

print(f"\nCurrent capital: ${capital:.2f}")

# Positions
positions = state.get('positions', {})
print(f"Open positions: {len(positions)}")

# Trade stats
total = state.get('total_trades', 0)
wins = state.get('wins', 0)
losses = state.get('losses', 0)

print(f"\nTotal trades: {total}")
print(f"Wins: {wins}")
print(f"Losses: {losses}")
if total > 0:
    print(f"Win rate: {wins/total*100:.1f}%")

# Starting capital
start = state.get('starting_capital', state.get('initial_capital', 1000))
print(f"\nStarting capital: ${start:.2f}")
print(f"Current capital: ${capital:.2f}")
print(f"Total P&L: ${capital - start:.2f} ({(capital/start - 1)*100:.1f}%)")

# Last 20 trades
history = state.get('trade_history', [])
print(f"\n\nLast 20 Closed Trades:")
print("=" * 60)

for trade in history[-20:]:
    symbol = trade.get('symbol', 'UNKNOWN')
    pnl = trade.get('pnl', 0)
    pnl_pct = trade.get('pnl_percent', 0)
    reason = trade.get('exit_reason', 'unknown')
    
    emoji = "🟢" if pnl > 0 else "🔴"
    print(f"{emoji} {symbol:10s} ${pnl:7.2f} ({pnl_pct:+6.1f}%) - {reason}")

# Summary by exit reason
print(f"\n\nExit Reasons Summary:")
print("=" * 60)
reasons = {}
for trade in history:
    reason = trade.get('exit_reason', 'unknown')
    pnl = trade.get('pnl', 0)
    if reason not in reasons:
        reasons[reason] = {'count': 0, 'total_pnl': 0}
    reasons[reason]['count'] += 1
    reasons[reason]['total_pnl'] += pnl

for reason, data in sorted(reasons.items(), key=lambda x: x[1]['count'], reverse=True):
    print(f"{reason:20s}: {data['count']:3d} trades, ${data['total_pnl']:8.2f} total P&L")
