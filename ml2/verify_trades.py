import json

# Load trades
trades = []
with open('data/ml_training/ml_trades.jsonl', 'r') as f:
    for line in f:
        trades.append(json.loads(line))

# Calculate totals
total_trades = len(trades)
wins = sum(1 for t in trades if t['win'])
losses = total_trades - wins
total_pnl = sum(t['pnl_usd'] for t in trades)
win_rate = (wins / total_trades * 100) if total_trades > 0 else 0

print(f"📊 Trade Verification:")
print(f"Total Trades: {total_trades}")
print(f"Wins: {wins} ({win_rate:.1f}%)")
print(f"Losses: {losses}")
print(f"Total P&L: ${total_pnl:.2f}")
print(f"\n🔝 Top 5 Wins:")
for trade in sorted(trades, key=lambda x: x['pnl_usd'], reverse=True)[:5]:
    print(f"  {trade['token_symbol']}: ${trade['pnl_usd']:.2f} ({trade['pnl_percent']:.1f}%)")
print(f"\n💀 Top 5 Losses:")
for trade in sorted(trades, key=lambda x: x['pnl_usd'])[:5]:
    print(f"  {trade['token_symbol']}: ${trade['pnl_usd']:.2f} ({trade['pnl_percent']:.1f}%)")