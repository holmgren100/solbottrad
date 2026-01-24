# Data Cleanup Guide

## Overview
This guide shows you how to clean up old trade data and start fresh with new data collection using the improved multi-source monitoring system.

## Why Clean Up?

You mentioned:
> "I need doo a refresh on all trades and data collection soo have new data soo dont is a mess from all old shitty trades"

**Good reasons to clean up:**
- Old trades were from before the multi-source aggregator (Jupiter + DexScreener + Birdeye)
- Old trades didn't have RugCheck holder analysis
- Old trades didn't have dynamic scoring (used hard settings that failed)
- Old trades didn't have market crash detection
- Want to measure performance of NEW system only
- Start with clean slate for analysis

## What Data Will Be Deleted

1. **Trade History** (`data/ml_training/ml_trades.jsonl`)
   - All historical trade records
   - This is used for ML training and analysis

2. **Position State** (`data/position_state.json`)
   - Current position tracking (if any)

3. **CSV Exports** (`data/trade_history*.csv`)
   - Previously exported CSV files

4. **Logs** (optional) (`logs/`)
   - Bot operation logs

## ⚠️ IMPORTANT: Backup First!

Before deleting anything, **BACKUP YOUR DATA**:

```bash
# SSH into your Digital Ocean droplet
ssh root@your-droplet-ip

# Navigate to bot directory
cd /root/solbottrad  # or wherever your bot is

# Create backup directory with timestamp
mkdir -p backups/backup_$(date +%Y%m%d_%H%M%S)

# Backup trade data
cp -r data/ backups/backup_$(date +%Y%m%d_%H%M%S)/
cp -r logs/ backups/backup_$(date +%Y%m%d_%H%M%S)/ 2>/dev/null || true

# Verify backup
ls -lh backups/
```

## How to Clean Up (Digital Ocean Terminal)

### Option 1: Clean Everything (Fresh Start)

```bash
# Stop the bot first
pm2 stop solbot

# Delete all trade data
rm -f data/ml_training/ml_trades.jsonl
rm -f data/position_state.json
rm -f data/trade_history*.csv
rm -f data/trades.db  # If you have SQLite database

# Optionally delete logs
rm -rf logs/*

# Verify deletion
ls -lh data/
ls -lh data/ml_training/

# Start bot with clean slate
pm2 start solbot
pm2 logs solbot
```

### Option 2: Archive Old Data (Safer)

```bash
# Stop the bot first
pm2 stop solbot

# Create archive directory
mkdir -p data/archive/$(date +%Y%m%d)

# Move old data to archive
mv data/ml_training/ml_trades.jsonl data/archive/$(date +%Y%m%d)/ 2>/dev/null || true
mv data/position_state.json data/archive/$(date +%Y%m%d)/ 2>/dev/null || true
mv data/trade_history*.csv data/archive/$(date +%Y%m%d)/ 2>/dev/null || true

# Verify
ls -lh data/
ls -lh data/archive/$(date +%Y%m%d)/

# Start bot
pm2 start solbot
pm2 logs solbot
```

### Option 3: Keep Last N Trades Only

If you want to keep some recent trades for comparison:

```bash
# Stop the bot
pm2 stop solbot

# Keep last 100 trades in ml_trades.jsonl
tail -n 100 data/ml_training/ml_trades.jsonl > data/ml_training/ml_trades_temp.jsonl
mv data/ml_training/ml_trades_temp.jsonl data/ml_training/ml_trades.jsonl

# Start bot
pm2 start solbot
```

## Step-by-Step: Complete Fresh Start

Here's the full process for a clean restart:

```bash
# 1. SSH into Digital Ocean
ssh root@your-droplet-ip

# 2. Navigate to bot directory
cd /root/solbottrad

# 3. Create backup (IMPORTANT!)
mkdir -p backups/backup_$(date +%Y%m%d_%H%M%S)
cp -r data/ backups/backup_$(date +%Y%m%d_%H%M%S)/
echo "Backup created in: backups/backup_$(date +%Y%m%d_%H%M%S)"

# 4. Stop the bot
pm2 stop solbot
pm2 logs solbot  # Verify it stopped

# 5. Delete old trade data
rm -f data/ml_training/ml_trades.jsonl
rm -f data/position_state.json
rm -f data/trade_history*.csv

# 6. Verify deletion
echo "=== Data directory after cleanup ==="
ls -lh data/
ls -lh data/ml_training/

# 7. Make sure enhanced systems are enabled in .env
cat .env | grep -E "ENABLE_MULTI_SOURCE|ENABLE_RUGCHECK|ENABLE_MARKET|ENABLE_DYNAMIC"

# 8. Start bot fresh
pm2 start solbot

# 9. Monitor startup
pm2 logs solbot --lines 50

# 10. Verify bot is working
# Wait 1-2 minutes, then check Telegram for startup message
```

## Verify Clean Start

After cleanup and restart, verify the bot is working correctly:

```bash
# Check bot status
pm2 status

# Check recent logs
pm2 logs solbot --lines 100

# Check if new data files are being created
ls -lh data/ml_training/

# Check Telegram
# You should receive:
# 🤖 Trading Bot Started
# The Solana trading bot is now running and monitoring markets.
```

## What Happens After Cleanup?

1. **Bot starts with NO trade history**
   - `/status` will show 0 total trades
   - `/daily` and `/weekly` will show "No trades"
   - `/export` will show "No trades to export"

2. **Bot starts collecting NEW data**
   - Every trade uses multi-source aggregator
   - Every trade has RugCheck analysis
   - Every trade has dynamic scoring
   - Every trade has market conditions tracked
   - Data saved to `data/ml_training/ml_trades.jsonl`

3. **You can analyze improvement**
   - Compare old backup data vs new data
   - See if win rate improves
   - See if low liquidity exits decrease (73% → target 15-20%)
   - See if dynamic scoring performs better than hard settings

## Enhanced Data Collection (After Cleanup)

Your NEW trades will include:

### In ml_trades.jsonl:
```json
{
  "token_address": "...",
  "symbol": "...",
  "entry_price": 0.00001234,
  "exit_price": 0.00001567,
  "pnl": 12.50,
  "pnl_percent": 35.7,
  "win": true,
  "exit_reason": "trailing_stop",

  // NEW - Multi-source data
  "data_sources": ["jupiter", "dexscreener", "birdeye"],
  "data_confidence": "high",
  "entry_liquidity": 125000,
  "exit_liquidity": 138500,
  "liquidity_change_pct": 10.8,

  // NEW - RugCheck
  "rugcheck_safety_score": 85,
  "rugcheck_risk_level": "low",
  "top_10_holder_pct": 35.2,

  // NEW - Market conditions
  "market_state": "normal",
  "sol_price": 102.34,
  "sol_change_1h": 2.3,

  // NEW - Dynamic scoring
  "token_score": 75,
  "score_breakdown": {
    "liquidity": 50,
    "confidence": 15,
    "volume": 15,
    "rugcheck": 20,
    "market": 10
  },

  "duration_hours": 3.2,
  "token_age_hours": 2.3,
  "is_pumpfun": false
}
```

### In CSV exports (via /export):
All the enhanced columns:
- Date, Time, Day of Week, Hour
- Entry/Exit Prices, Price Change
- Entry/Exit Liquidity, Liquidity Change
- Duration (hours & minutes)
- Token Age at Entry
- Strategy Used
- Win/Loss Analysis

## Monitoring New Performance

After cleanup, track these metrics:

```bash
# Check trade count (should start at 0)
pm2 logs solbot | grep "Total trades"

# Monitor win rate over time
# Use /daily command in Telegram

# Export data weekly for analysis
# Use /export weekly command in Telegram
```

## Rollback (If Needed)

If you need to restore old data:

```bash
# Stop bot
pm2 stop solbot

# Find your backup
ls -lh backups/

# Restore from backup
cp -r backups/backup_YYYYMMDD_HHMMSS/data/* data/

# Start bot
pm2 start solbot
```

## Common Commands Reference

```bash
# Bot management
pm2 status              # Check if bot is running
pm2 start solbot        # Start bot
pm2 stop solbot         # Stop bot
pm2 restart solbot      # Restart bot
pm2 logs solbot         # View live logs
pm2 logs solbot --lines 100  # View last 100 log lines

# File management
ls -lh data/            # List data files
du -sh data/            # Check data directory size
cat .env | grep ENABLE  # Check feature flags

# Backup management
ls -lh backups/         # List backups
du -sh backups/         # Check backup size
```

## Troubleshooting

### Bot won't start after cleanup

```bash
# Check logs
pm2 logs solbot --lines 50

# Check if data directory exists
ls -lh data/
ls -lh data/ml_training/

# Recreate directories if needed
mkdir -p data/ml_training
mkdir -p data/positions

# Restart
pm2 restart solbot
```

### No trades being recorded

```bash
# Check if enhanced systems are enabled
cat .env | grep ENABLE_MULTI_SOURCE_AGGREGATOR
cat .env | grep ENABLE_DYNAMIC_SCORER

# Should show:
# ENABLE_MULTI_SOURCE_AGGREGATOR=true
# ENABLE_DYNAMIC_SCORER=true

# If false, enable them and restart
pm2 restart solbot
```

### Want to verify data is clean

```bash
# Check trade file
cat data/ml_training/ml_trades.jsonl | wc -l
# Should show 0 after fresh cleanup

# Check position state
cat data/position_state.json
# Should be empty {} or not exist

# Monitor for first trade
pm2 logs solbot | grep "Position entered"
```

## Best Practice Workflow

1. **Before cleanup:**
   - Export current data: `/export` in Telegram
   - Backup files: `cp -r data/ backups/`
   - Verify enhanced systems enabled in `.env`

2. **During cleanup:**
   - Stop bot: `pm2 stop solbot`
   - Move or delete old data
   - Verify deletion

3. **After cleanup:**
   - Start bot: `pm2 start solbot`
   - Monitor startup: `pm2 logs solbot`
   - Wait for first trade
   - Verify new data format

4. **Ongoing:**
   - Use `/daily` to monitor performance
   - Use `/export daily` to analyze daily results
   - Compare vs old backup data
   - Adjust settings based on results

## Summary

**To start fresh with clean data:**

```bash
# Quick version
cd /root/solbottrad
cp -r data/ backups/backup_$(date +%Y%m%d)/
pm2 stop solbot
rm -f data/ml_training/ml_trades.jsonl data/position_state.json data/trade_history*.csv
pm2 start solbot
pm2 logs solbot
```

Now your bot will collect data with all the new enhanced features! 🚀
