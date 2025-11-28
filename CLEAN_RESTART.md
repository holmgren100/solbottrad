# Clean Restart Guide - After Bug Fixes

All critical bugs are fixed. Follow this guide for a clean restart.

---

## ⚠️ Before You Start

**Your current state:**
- Portfolio: $2.19 (only SOL, tokens are dust)
- 22 tokens in wallet (total value ~$0)
- Bot has 16 "positions" but most are worthless
- All critical bugs fixed ✅

**Decision point:**

### Option 1: Fresh Start (Recommended)
- Clear all old positions
- Start clean with new capital
- No baggage from bugged sessions

### Option 2: Continue with Old Positions
- Keep tracking the 22 tokens
- Risk: Most are probably rugs/dead
- Will monitor them with fixed bot

---

## 🎯 Clean Start Procedure (Recommended)

### Step 1: Stop Everything

```bash
# Stop the bot
pkill -9 python3

# Verify it's stopped
ps aux | grep python
```

### Step 2: Clean State

```bash
# Backup old state (if it exists)
if [ -f live_trading_state.json ]; then
    mv live_trading_state.json live_trading_state.json.backup.old
    echo "✅ Backed up old state"
fi

# You're starting fresh - no state file
```

### Step 3: Run Preflight Check

```bash
python3 preflight_check.py
```

**You should see:**
```
✅ PASS  Imports
✅ PASS  Network
✅ PASS  Wallet
✅ PASS  Persistence
✅ PASS  Monitoring
✅ PASS  Config

🎉 ALL CHECKS PASSED!
```

**If anything fails, fix it before continuing.**

### Step 4: Review Configuration

```bash
nano .env  # or vim, code, etc.
```

**Recommended conservative settings for fresh start:**

```bash
# Trading Mode
PAPER_TRADING_MODE=false  # Live trading

# Position Limits (CONSERVATIVE)
MAX_OPEN_POSITIONS=5      # Down from 12 - focus on quality
MAX_DAILY_TRADES=20       # Down from 250 - avoid overtrading
DEFAULT_BUY_AMOUNT=0.02   # ◎0.02 per position

# Quality Filters (STRICT)
MIN_LIQUIDITY_USD=10000   # Up from 5000 - avoid low liquidity rugs
MIN_CONFIDENCE_SCORE=0.6  # Up from 0.4 - better token selection
MIN_SENTIMENT_SCORE=0.5   # Keep at 0.5
MIN_SOCIAL_SCORE=0.6      # Keep at 0.6

# Risk Management (TIGHT)
STOP_LOSS_PERCENT=15      # Tighter than 10% (optional)
TAKE_PROFIT_PERCENT=30    # Take profits sooner
USE_TRAILING_STOP=true    # Keep this
TRAILING_STOP_PERCENT=15  # Up from 10 - lock in gains

# Rug Protection (STRICT)
RUG_DETECTION_ENABLED=true
MIN_POSITION_LIQUIDITY=10000  # Up from 8000
STALE_PRICE_MINUTES=2         # Down from 3 - faster detection
```

**Why these settings?**
- Fewer positions = better focus
- Higher liquidity = less likely to rug
- Tighter stops = limit losses
- Conservative approach until proven

### Step 5: Deposit SOL

**Recommended starting amount:** ◎0.5 ($100)

```
Address: 6c9spbhr6NN1btpk84QCyyHeM1BmAEHJxrNyzGcqgspM

Why ◎0.5?
- Enough for 5 positions @ ◎0.02 = ◎0.1
- ◎0.4 left for fees (~80-200 transactions)
- Not too much if issues remain
- Enough to be meaningful
```

**Wait for deposit to confirm:**
```bash
python3 check_wallet_balance.py
# Should show ◎0.5+
```

### Step 6: Start Bot

```bash
# Start in background with logging
python -m src.main > bot.log 2>&1 &

# Get the process ID
echo $!  # Note this number

# Or use screen for easier management
screen -S trading_bot
python -m src.main
# Ctrl+A then D to detach
# screen -r trading_bot to reattach
```

### Step 7: Monitor Startup

```bash
# Watch the logs
tail -f bot.log

# You should see:
# - "Initializing Solana Trading Bot..."
# - "Live trading mode enabled"  (NOT paper trading)
# - "Position monitoring enabled"
# - "Starting main trading loop..."
# - "Scanning for tokens..."
```

### Step 8: Verify Bot is Working

**In Telegram:**
```
/status
```

**You should see:**
```
📊 Trading Bot Status (💰 Live)  ← Must say "Live"

💰 Portfolio
Total Value: $100.00    ← Your starting capital
Cash: $100.00
Invested: $0.00
P&L: $0.00 (+0.00%)

📈 Open Positions (0)  ← Starts at 0
```

**In logs:**
```bash
tail -f bot.log
```

**Watch for:**
- ✅ "Analyzing token: [address]"
- ✅ "Token passed all checks"
- ✅ "BUY CONFIRMED" (when it finds good token)
- ✅ "Monitoring X positions"
- ✅ Position saved to state

**Red flags:**
- ❌ "Paper trading mode enabled" (should be live)
- ❌ "Live trading not yet implemented"
- ❌ KeyError or exceptions
- ❌ "0 positions already open" after buying

### Step 9: First Trade Check

**When bot makes first trade:**

1. **Check logs:**
   ```bash
   grep -i "BUY CONFIRMED" bot.log | tail -1
   ```

2. **Check /status in Telegram:**
   - Should show 1 position
   - Entry price, current price
   - Stop loss set correctly

3. **Verify state saved:**
   ```bash
   cat live_trading_state.json | grep -A 5 positions
   # Should show the position data
   ```

4. **Check Solscan:**
   ```
   https://solscan.io/account/6c9spbhr6NN1btpk84QCyyHeM1BmAEHJxrNyzGcqgspM
   # Verify transaction executed
   ```

**If ALL these work, the bot is functioning correctly!**

### Step 10: Monitor Closely (First 24 Hours)

**Every 2 hours:**
```bash
# Check logs for errors
grep -i "error\|fail" bot.log | tail -20

# Check /status in Telegram
# Verify positions are being monitored

# Check if stop losses trigger correctly
grep -i "stop loss\|take profit" bot.log | tail -10
```

**After 24 hours:**
- If profitable: Continue
- If breaking even: Keep monitoring
- If losing: Review what tokens it bought (may need tighter filters)

---

## 🔄 Continue with Old Positions (Not Recommended)

If you want to keep the existing 22 tokens:

### Step 1: Clean the Data

```bash
# Force fix any bad prices
python3 force_fix_prices.py

# Should show:
# "Found 0 positions with suspicious values"
# (Already fixed in previous session)
```

### Step 2: Remove Worthless Tokens

Most of the 22 tokens are probably worth $0. Remove them:

```bash
python3 force_fix_prices.py
# Will auto-remove tokens not in wallet or worth <$0.10
```

### Step 3: Deposit SOL (Still Needed)

You still need more SOL for fees:
```
Deposit: ◎0.1-0.2 to cover monitoring and exits
```

### Step 4: Start Bot

```bash
python -m src.main > bot.log 2>&1 &
```

**Bot will:**
- Load existing positions from state file
- Monitor them every 60 seconds
- Trigger stop losses if prices drop
- Take profit if prices rise

**Problem:** Most tokens are likely dead, so you'll just be monitoring dust. Fresh start is better.

---

## 📊 What to Expect (Fresh Start)

**First few hours:**
- Bot scans trending tokens every 2 minutes
- Filters out low liquidity, low score tokens
- May take 30-60 min to find first good token
- Will start slow (this is GOOD)

**First position:**
- ◎0.02 buy (~$4)
- Stop loss at -15% (~$3.40)
- Take profit at +30% (~$5.20)
- Trailing stop will follow if it pumps

**First day:**
- Expect 3-10 trades (depending on market)
- Win rate: 30-50% is normal for small caps
- Goal: Don't lose money (break even is success)

**First week:**
- Should have clearer picture of token selection quality
- Can adjust MIN_CONFIDENCE_SCORE if too strict/loose
- Can adjust position size if working well

---

## 🚨 Emergency Procedures

### If Bot Crashes

```bash
# Check the error
tail -50 bot.log

# Restart
python -m src.main > bot.log 2>&1 &

# Verify positions loaded
grep "Loaded.*positions" bot.log
```

### If /status Shows Wrong Data

```bash
# Stop bot
pkill -9 python3

# Fix state file
python3 fix_position_prices.py

# Restart
python -m src.main > bot.log 2>&1 &
```

### If Running Out of SOL Again

```bash
# Check balance
python3 check_wallet_balance.py

# If < ◎0.01, deposit more
# Then restart to resume monitoring
```

### If Positions Not Being Monitored

```bash
# Check if monitoring is running
grep "Monitoring.*position" bot.log | tail -5

# Should see every 60 seconds
# If not, check src/main.py for paper trading check
```

---

## ✅ Success Criteria

**After 1 week, you should have:**
- ✅ No crashes or errors
- ✅ Positions showing in /status correctly
- ✅ Stop losses triggering when needed
- ✅ Take profits triggering when in profit
- ✅ State file persisting across restarts
- ✅ Portfolio value realistic (not $4M)

**If all these work: Bot is fixed and functional.**

Then it's just about tuning the strategy for profitability.

---

## 📞 Support

If you encounter issues:

1. **Run diagnostics:**
   ```bash
   python3 preflight_check.py
   python3 diagnose_network.py
   ```

2. **Check logs for specific error:**
   ```bash
   grep -i "error" bot.log | tail -20
   ```

3. **Share the specific error** (not just "it's broken")

4. **Include:**
   - What step you're on
   - Exact error message
   - Output of preflight_check.py
   - Last 20 lines of bot.log

---

**Good luck! The bot is now ready to use properly.**
