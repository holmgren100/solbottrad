# Troubleshooting Guide

## Bot Hangs After 2-4 Hours

### Symptoms
- Bot appears to be running but no new trades
- Buy orders fail with "Position already exists"
- Console shows "searching for positions" but nothing happens
- Bot becomes unresponsive

### Causes
1. **Bad price data from DexScreener** - API returning prices like `$6.9e-10` or `-100%` drops
2. **Stuck waiting for API response** - Network timeout without proper error handling
3. **Too many positions** - Hitting the position limit and trying to open more

### Solutions

#### 1. Check Logs for Bad Price Data
```bash
grep "Price too small\|SUSPICIOUS\|outside valid range" trading_bot.log
```

The bot now automatically:
- Rejects unrealistic prices (<1e-12 or >1e10)
- Detects suspicious price changes (>90%)
- Falls back to cached prices when API returns bad data

#### 2. Check for Timeout Errors
```bash
grep "Timeout\|took >" trading_bot.log | tail -20
```

The bot now has:
- 30 second timeout per token analysis
- 60 second timeout for position checks
- Automatic skip and continue on timeout

#### 3. Check Position Limit
```bash
python diagnose_positions.py
```

Configure max positions in `.env`:
```env
MAX_OPEN_POSITIONS=3  # Reduce from 7 to prevent accumulation
```

#### 4. Restart Bot Safely
The bot now saves state automatically, so restarting won't lose your portfolio:

```bash
# Stop bot (Ctrl+C)
# Check state is saved
python check_state.py
# Restart
python src/main.py
```

---

## Capital Resets Every Day

### Symptoms
- Portfolio value goes back to $1000 after restart
- All positions disappear
- Trade history is lost

### Root Cause
The state file `paper_trading_state.json` is not being saved or loaded correctly.

### Diagnosis

#### Step 1: Check if state file exists
```bash
python check_state.py
```

This shows:
- ✅ If state file exists and location
- 💰 Current portfolio state
- 📊 All open positions
- 📈 Recent trade history

#### Step 2: Check logs for state save/load
```bash
grep "State saved\|State loaded\|state file" trading_bot.log | tail -20
```

You should see:
```
INFO - State file location: /path/to/solbottrad/paper_trading_state.json
INFO - 📝 No previous state file found at ..., starting fresh  (first run)
INFO - 💾 State saved: $950.00 cash, 2 positions → /path/to/paper_trading_state.json
INFO - 📂 Loading state from /path/to/paper_trading_state.json...
INFO - ✅ State loaded successfully: $950.00 cash, 2 positions, 5 trades
```

#### Step 3: Verify you're running from the same directory
The state file is saved in the **current working directory** where you run the bot.

**Problem**: Running bot from different locations
```bash
# First time - saves to C:\Users\fiske\solbottrad\paper_trading_state.json
C:\Users\fiske\solbottrad> python src\main.py

# Second time - looks for C:\paper_trading_state.json (doesn't exist!)
C:\> python C:\Users\fiske\solbottrad\src\main.py
```

**Solution**: Always run from the project root
```bash
cd C:\Users\fiske\solbottrad
python src\main.py
```

### Fixes Implemented

1. **Absolute path for state file** - Bot now uses full path in current directory
2. **State saved after every trade** - Buy and sell operations auto-save
3. **Periodic state saves** - Every 10 scan cycles (10 minutes)
4. **Better logging** - Shows exactly where state is saved/loaded
5. **Error recovery** - If load fails, starts fresh instead of crashing

### Manual Backup

To manually backup your state:
```bash
# Backup
copy paper_trading_state.json paper_trading_state_backup.json

# Restore
copy paper_trading_state_backup.json paper_trading_state.json
```

---

## Position Won't Close at Take Profit

### Symptoms
- Position shows +11% profit but doesn't sell
- Position shows +20% profit but doesn't sell
- Stop loss also not triggering

### Check Your Settings

Your `.env` file has:
```env
TAKE_PROFIT_PERCENT=20
STOP_LOSS_PERCENT=10
```

This means:
- **Take profit** triggers at **+20%** (not +10%)
- **Stop loss** triggers at **-10%** (not -5%)

A position at +11% will **NOT** sell because it hasn't reached +20% yet.

### Diagnosis
```bash
python diagnose_positions.py
```

This shows for each position:
- Current price vs entry price
- Actual P&L percentage
- Distance to stop loss
- Distance to take profit
- Why SL/TP hasn't triggered

Example output:
```
🔹 JUP
   Entry Price: $0.00016890
   Live Price: $0.00018760
   Live P&L: +11.07%

   ⚖️  Trigger Check:
   ✅ No triggers
      Stop Loss: +121.07% away (needs to drop to -10%)
      Take Profit: +8.93% away (needs to reach +20%)
```

### Solutions

#### Option 1: Lower take profit threshold
Edit `.env`:
```env
TAKE_PROFIT_PERCENT=10  # Change from 20 to 10
```

Restart bot. Now positions will sell at +10% instead of +20%.

#### Option 2: Manually close position
```bash
python close_positions.py
```

Choose which position to close or close all.

---

## Bot Shows "Position Already Exists" But Can't Find It

### Symptom
```
Position already exists for XYZ
❌ No position found for XYZ
```

### Cause
The bot's in-memory positions don't match the market data being scanned.

### Diagnosis
```bash
# Check what positions exist
python diagnose_positions.py

# Check logs
grep "Position already exists" trading_bot.log | tail -10
```

### Solution
```bash
# Close all positions to reset
python close_positions.py --all

# Or restart bot (state will load correctly)
```

---

## General Debugging

### Enable Debug Logging
Edit `src/monitoring/logger.py`:
```python
logger.setLevel(logging.DEBUG)  # Change from INFO
```

### Check Bot Health
```bash
# Check logs for errors
grep "ERROR\|❌" trading_bot.log | tail -20

# Check for warnings
grep "WARNING\|⚠️" trading_bot.log | tail -20

# Check last 100 lines
tail -100 trading_bot.log
```

### Performance Check
```bash
python check_performance.py
```

Shows:
- Total trades
- Recent trades
- Errors

### Clean Restart
```bash
# Stop bot
# Backup state
copy paper_trading_state.json backup.json
# Delete state to start fresh
del paper_trading_state.json
# Restart bot
python src\main.py
```

---

## Common Error Messages

### "Price too small: $6.9e-10"
**Fixed** - Bot now rejects invalid prices and uses cached values.

### "SUSPICIOUS: Price dropped -100.0%"
**Fixed** - Bot detects unrealistic price changes and ignores them.

### "Timeout analyzing token (took >30s)"
**Normal** - Bot skips slow tokens and continues. No action needed.

### "Max positions (3) reached"
**Normal** - Bot won't open new positions until some close. Adjust `MAX_OPEN_POSITIONS` in `.env` if needed.

### "State file NOT found"
**Action**: You're running from wrong directory. Always run from project root:
```bash
cd C:\Users\fiske\solbottrad
python src\main.py
```

---

## Getting Help

If issues persist:

1. **Collect logs**:
   ```bash
   # Last 200 lines
   tail -200 trading_bot.log > debug.log
   ```

2. **Check state**:
   ```bash
   python check_state.py > state_info.txt
   ```

3. **Check positions**:
   ```bash
   python diagnose_positions.py > positions.txt
   ```

4. **Share these files** for debugging

---

## Quick Reference

| Problem | Command | Fix |
|---------|---------|-----|
| Bot hanging | `grep "Timeout" trading_bot.log` | Timeouts now auto-skip |
| Capital resets | `python check_state.py` | State persistence enabled |
| Position stuck | `python diagnose_positions.py` | Shows why SL/TP not triggered |
| Close positions | `python close_positions.py` | Manual position closer |
| Bad prices | `grep "SUSPICIOUS" trading_bot.log` | Price validation enabled |
| Check trades | `python check_performance.py` | Shows trade statistics |
