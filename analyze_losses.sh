#!/bin/bash
# Analyze why the bot is losing money

echo "=== LOSS ANALYSIS ==="
cd /root/solbottrad

echo ""
echo "1. Recent SELL transactions (last 50):"
echo "======================================="
grep "SELL" bot.log | tail -50 | grep -E "PnL:|proceeds:" | tail -20

echo ""
echo "2. Dead token auto-closes:"
echo "=========================="
grep "AUTO-CLOSING DEAD TOKEN" bot.log | tail -10

echo ""
echo "3. Trailing stop triggers:"
echo "========================="
grep "Trailing stop triggered" bot.log | tail -10

echo ""
echo "4. Buy signal analysis (last 10 buys):"
echo "======================================"
grep "BOUGHT:" bot.log | tail -10

echo ""
echo "5. Current paper trading state:"
echo "=============================="
if [ -f "paper_trading_state.json" ]; then
    python3 - <<'PYTHON'
import json
with open('paper_trading_state.json', 'r') as f:
    state = json.load(f)
    print(f"Capital: ${state['capital']:.2f}")
    print(f"Starting capital: ${state.get('starting_capital', 1000):.2f}")
    print(f"Open positions: {len(state['positions'])}")
    print(f"Total trades: {state['total_trades']}")
    print(f"Wins: {state['wins']}")
    print(f"Losses: {state['losses']}")
    print(f"Win rate: {state['wins']/state['total_trades']*100:.1f}%")

    print("\nLast 10 closed positions:")
    for trade in state.get('trade_history', [])[-10:]:
        print(f"  {trade['symbol']}: ${trade['pnl']:.2f} ({trade['pnl_percent']:.1f}%) - {trade['exit_reason']}")
PYTHON
fi

echo ""
echo "6. Slippage/Fee analysis:"
echo "========================"
echo "Buy fee: 0.3% + 0.5% slippage = 0.8% cost"
echo "Sell fee: 0.3% + 1.0% slippage = 1.3% cost"
echo "Total round trip cost: ~2.1%"
echo "→ Need >2.1% profit just to break even!"

echo ""
echo "7. Check for honeypots:"
echo "======================"
grep -i "honeypot\|unsellable\|can't sell" bot.log | tail -5
