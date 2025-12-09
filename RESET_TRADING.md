# Reset Trading Data - Simple Command for Digital Ocean

## Single Command to Reset All Trading Data

Copy and paste this ONE command on your Digital Ocean server:

```bash
cd ~/solbottrad && rm -f paper_trading_state.json && rm -f data/*.csv && rm -f data/ml_training/*.jsonl && echo "✅ Trading data reset! Restart bot for fresh start with \$1000 capital."
```

## What This Does:

1. **Removes paper trading state** - Clears your current capital/positions
2. **Removes CSV exports** - Clears trade history files
3. **Removes ML training data** - Clears analysis data

## After Running This Command:

1. **Restart your bot** (systemctl restart solbottrad or however you run it)
2. Bot will start with **fresh $1000 capital** (or whatever is in .env)
3. **All new trades will have correct liquidity data** (no more zeros!)

## That's It!

Simple, clean, fresh start. Your .env settings stay the same.
