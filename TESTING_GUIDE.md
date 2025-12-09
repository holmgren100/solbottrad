# 🧪 Testing Guide - CoinGecko & Apify Integration
## Step-by-Step Commands to Verify Before Going Live

**Goal:** Hit batch 5-6 performance numbers before switching to live mode

---

## ✅ Pre-Flight Checklist

```bash
# 1. Verify you're in the right directory
cd /home/user/solbottrad

# 2. Check .env configuration
grep -E "PAPER_TRADING_MODE|ENABLE_JUPITER|ENABLE_BIRDEYE|ENABLE_COINGECKO|ENABLE_APIFY" .env

# Expected output:
# PAPER_TRADING_MODE=true
# ENABLE_JUPITER=true
# ENABLE_BIRDEYE=true
# ENABLE_COINGECKO=true
# ENABLE_APIFY=false

# 3. Verify API keys are set
grep -E "BIRDEYE_API_KEY|COINGECKO_API_KEY" .env | grep -v "your_"

# Expected: Both keys should show actual values (not placeholders)
```

---

## 🚀 STEP 1: Start Bot in Paper Trading Mode

### Option A: Foreground (See Logs Directly)

```bash
# Start bot and watch output
python3 -m src.main
```

**What to look for:**
```
✅ CoinGecko client initialized
✅ Apify DexScreener client initialized (or warning if disabled)
📄 Paper trading mode enabled
Bot initialization complete

🔧 Token sources: Jupiter=True, Birdeye=True, CoinGecko=True, Apify=False

📡 Fetching tokens from Jupiter (CYCLING discovery)...
Jupiter Cycle 1/3: Using 'toporganicscore' discovery
✅ Jupiter: Found XX tokens

📡 Fetching tokens from Birdeye (GAINERS focus)...
Birdeye Cycle 1/5: Using 'priceChange24h' discovery
✅ Birdeye: Found XX GAINERS

📡 Fetching tokens from CoinGecko (Top Gainers)...
CoinGecko Cycle 1/3: Using 'top_gainers' discovery
✅ CoinGecko: Found XX GAINERS

Combined: XX unique tokens from all sources
```

**Stop with:** `Ctrl+C`

---

### Option B: Background (Production Mode)

```bash
# Start in background
nohup python3 -m src.main > bot_output.log 2>&1 &

# Get process ID
echo $!

# Save PID for later
echo $! > bot.pid
```

---

## 📊 STEP 2: Monitor Bot Performance

### A. Watch Live Logs (Real-time)

```bash
# Follow main log file
tail -f trading_bot.log

# Filter for important events only
tail -f trading_bot.log | grep -E "(Token sources|Found.*tokens|Found.*GAINERS|Cycle|Entry|Exit|profit|loss|WIN|LOSS)"
```

### B. Check Token Discovery Stats

```bash
# Count tokens found per source (last 100 lines)
tail -100 trading_bot.log | grep -E "Jupiter: Found|Birdeye: Found|CoinGecko: Found"

# Example output:
# ✅ Jupiter: Found 28 tokens (3 bluechips filtered)
# ✅ Birdeye: Found 5 GAINERS (0 bluechips filtered)
# ✅ CoinGecko: Found 12 GAINERS (4 bluechips filtered)
```

### C. Monitor Cycling Strategies

```bash
# See which discovery methods are being used
tail -200 trading_bot.log | grep -E "Cycle [0-9]/[0-9]:"

# Expected (rotating each scan):
# Jupiter Cycle 1/3: Using 'toporganicscore' discovery
# Birdeye Cycle 1/5: Using 'priceChange24h' discovery
# CoinGecko Cycle 1/3: Using 'top_gainers' discovery
# Jupiter Cycle 2/3: Using 'toptraded' discovery
# Birdeye Cycle 2/5: Using 'priceChange1h' discovery
# CoinGecko Cycle 2/3: Using 'trending' discovery
```

### D. Check Trade Performance (After 2-4 Hours)

```bash
# Count wins vs losses
grep -E "WIN|LOSS" trading_bot.log | tail -20

# Calculate win rate
echo "Wins: $(grep -c 'WIN' trading_bot.log)"
echo "Losses: $(grep -c 'LOSS' trading_bot.log)"

# See profit/loss amounts
grep -E "profit.*%" trading_bot.log | tail -20
```

---

## 🎯 STEP 3: Verify GAINERS Discovery

### Test: Are We Finding Actual GAINERS?

```bash
# Check for price change mentions (GAINERS indicator)
tail -500 trading_bot.log | grep -i "price.*change"

# Check for high percentage moves
tail -500 trading_bot.log | grep -E "[+][0-9]{2,}%|profit.*[5-9][0-9]%"

# See token symbols being discovered
tail -200 trading_bot.log | grep -E "symbol.*:" | head -20
```

**Good Signs:**
- Seeing tokens with +20%, +50%, +100%+ price changes
- Birdeye finds tokens sorted by priceChange24h
- CoinGecko finds top_gainers
- Variety of tokens (not just bluechips)

**Bad Signs:**
- Only finding SOL, USDC, JUP (bluechips)
- No price change data
- All tokens have 0% or negative moves

---

## 📈 STEP 4: Performance Targets (Batch 5-6 Numbers)

### What to Measure After 4-6 Hours:

```bash
# 1. Win Rate (Target: 50-60%+)
python3 << 'EOF'
import re

with open('trading_bot.log', 'r') as f:
    content = f.read()
    wins = len(re.findall(r'WIN', content))
    losses = len(re.findall(r'LOSS', content))

    if wins + losses > 0:
        win_rate = (wins / (wins + losses)) * 100
        print(f"Win Rate: {win_rate:.1f}% ({wins} wins, {losses} losses)")
        print(f"Target: 50-60%+ (Batch 5-6 standard)")
    else:
        print("No completed trades yet")
EOF

# 2. Average Profit per Win (Target: +15-25%)
grep -oP 'profit.*?\+\K[0-9.]+' trading_bot.log | awk '{sum+=$1; n++} END {if(n>0) print "Avg Profit: +"sum/n"%"}'

# 3. Average Loss (Target: -5 to -10%)
grep -oP 'loss.*?-\K[0-9.]+' trading_bot.log | awk '{sum+=$1; n++} END {if(n>0) print "Avg Loss: -"sum/n"%"}'

# 4. Number of Tokens Found per Scan (Target: 40-80)
tail -500 trading_bot.log | grep "Combined.*unique tokens" | tail -10
```

**Batch 5-6 Target Numbers:**
- ✅ Win Rate: **50-60%+**
- ✅ Avg Profit: **+15-25%** per win
- ✅ Avg Loss: **-5 to -10%** per loss
- ✅ Tokens per scan: **40-80** unique tokens
- ✅ GAINERS in feed: **20-40%** of discovered tokens

---

## 🔍 STEP 5: Health Checks

### Every 1-2 Hours, Verify:

```bash
# 1. All APIs healthy
tail -50 trading_bot.log | grep -E "health"

# Expected:
# ✅ alchemy is healthy
# ✅ jupiter is healthy
# ✅ birdeye is healthy
# ✅ coingecko is healthy

# 2. No repeated errors
tail -100 trading_bot.log | grep -c "ERROR"
# Should be 0 or very low (<5)

# 3. Bot still running
ps aux | grep "python3 -m src.main" | grep -v grep

# 4. Memory usage reasonable
ps aux | grep "python3 -m src.main" | grep -v grep | awk '{print "Memory: " $4"%"}'
```

---

## 🚨 STEP 6: Troubleshooting Common Issues

### Issue 1: No Tokens Found

```bash
# Check API connectivity
tail -100 trading_bot.log | grep -E "Cannot connect|Temporary failure|403|401"

# Verify API keys
grep -E "BIRDEYE_API_KEY|COINGECKO_API_KEY" .env

# Test manually (should show keys)
python3 << 'EOF'
import os
from dotenv import load_dotenv
load_dotenv()
print(f"Birdeye: {os.getenv('BIRDEYE_API_KEY', 'NOT SET')[:10]}...")
print(f"CoinGecko: {os.getenv('COINGECKO_API_KEY', 'NOT SET')[:10]}...")
EOF
```

### Issue 2: Only Finding Bluechips

```bash
# Check bluechip filter is working
tail -200 trading_bot.log | grep -i "filtered out bluechip"

# Should see:
# [JUP] Filtered out bluechip: SOL
# [DEX] Filtered out bluechip: USDC
# [BIRDEYE] Filtered out bluechip: JUP
```

### Issue 3: CoinGecko Rate Limit

```bash
# Check for rate limit errors
tail -100 trading_bot.log | grep "429\|rate limit"

# If hit, CoinGecko has 30 calls/min limit
# Solution: Bot will automatically skip and retry next scan
```

---

## ✅ STEP 7: When to Enable Apify (Optional)

### Only after 6-12 hours of testing shows:

- ✅ Win rate 50%+
- ✅ Finding 40+ tokens per scan
- ✅ CoinGecko working (finding GAINERS)
- ✅ No repeated errors

### Enable Apify:

```bash
# 1. Get token from https://console.apify.com/account/integrations

# 2. Add to .env
nano .env
# Change line 102:
# APIFY_API_TOKEN=your_actual_token_here
# Change line 133:
# ENABLE_APIFY=true

# 3. Restart bot
pkill -f "python3 -m src.main"
nohup python3 -m src.main > bot_output.log 2>&1 &

# 4. Verify Apify working
tail -f trading_bot.log | grep -E "Apify|SORTED GAINERS"

# Expected:
# 📡 Fetching tokens from Apify DexScreener (SORTED BY GAINERS)...
# Apify Cycle 1/5: Using 'priceChange24h' discovery
# Starting Apify scraper (this may take 10-30 seconds)...
# ✅ Apify: Found 18 SORTED GAINERS
```

**Note:** Apify scraping takes 10-30 seconds per scan (slower but BEST data)

---

## 🎯 STEP 8: Final Go-Live Checklist

### Before switching to PAPER_TRADING_MODE=false:

```bash
# Run this checklist:
echo "=== GO-LIVE CHECKLIST ==="
echo ""

# 1. Performance targets met
echo "1. Performance (last 20 trades):"
python3 << 'EOF'
import re
with open('trading_bot.log', 'r') as f:
    content = f.read()
    wins = len(re.findall(r'WIN', content))
    losses = len(re.findall(r'LOSS', content))
    if wins + losses >= 20:
        win_rate = (wins / (wins + losses)) * 100
        status = "✅ READY" if win_rate >= 50 else "❌ NOT READY"
        print(f"   Win Rate: {win_rate:.1f}% {status}")
    else:
        print(f"   ❌ Only {wins + losses} trades, need 20+")
EOF

# 2. All APIs healthy
echo "2. API Health:"
tail -50 trading_bot.log | grep -c "is healthy" | xargs -I {} echo "   {} APIs healthy (need 4+)"

# 3. Token discovery working
echo "3. Token Discovery:"
tail -100 trading_bot.log | grep "Combined.*unique tokens" | tail -1

# 4. GAINERS being found
echo "4. GAINERS Found:"
tail -200 trading_bot.log | grep -c "GAINERS" | xargs -I {} echo "   {} GAINER mentions"

# 5. Wallet funded (for live trading)
echo "5. Wallet (will check when going live):"
echo "   Needs: ~$100 SOL for Phase 0 testing"

echo ""
echo "=== If all ✅, you're ready for live mode! ==="
```

---

## 🔴 STEP 9: Going Live (When Ready)

### Only after hitting batch 5-6 numbers!

```bash
# 1. Backup current state
cp .env .env.backup.$(date +%Y%m%d_%H%M%S)
cp trading_bot.log trading_bot_paper.log.$(date +%Y%m%d_%H%M%S)

# 2. Stop paper trading bot
pkill -f "python3 -m src.main"

# 3. Add wallet credentials to .env
nano .env
# Find lines 122-125:
# SOLANA_PRIVATE_KEY=YOUR_WALLET_PRIVATE_KEY_HERE
# Replace with your actual key

# 4. Switch to live mode
sed -i 's/PAPER_TRADING_MODE=true/PAPER_TRADING_MODE=false/' .env

# 5. Verify settings
grep "PAPER_TRADING_MODE" .env
# Should show: PAPER_TRADING_MODE=false

# 6. Start in live mode (SMALL POSITIONS!)
nohup python3 -m src.main > bot_live.log 2>&1 &

# 7. Watch VERY CAREFULLY
tail -f trading_bot.log | grep -E "LIVE TRADING|Entry|Exit|profit|loss"
```

**⚠️ WARNING:** Live mode uses REAL money!
- Start with $2-4 positions (already set in .env)
- Watch first 5-10 trades VERY closely
- Stop immediately if something looks wrong

---

## 📊 Quick Reference Commands

```bash
# Start bot (paper mode)
python3 -m src.main

# Start bot (background)
nohup python3 -m src.main > bot_output.log 2>&1 &

# Watch logs
tail -f trading_bot.log

# Check performance
grep -E "WIN|LOSS" trading_bot.log | tail -20

# Check token discovery
tail -100 trading_bot.log | grep -E "Found.*tokens|Found.*GAINERS"

# Stop bot
pkill -f "python3 -m src.main"

# Check if running
ps aux | grep "python3 -m src.main" | grep -v grep
```

---

## 🎯 Success Criteria Summary

**Test for 6-12 hours, verify:**
- ✅ Win rate: 50-60%+
- ✅ Avg profit: +15-25%
- ✅ Avg loss: -5 to -10%
- ✅ Tokens/scan: 40-80
- ✅ GAINERS found: 20-40% of tokens
- ✅ No repeated API errors
- ✅ All health checks passing

**If all ✅, you hit batch 5-6 numbers = READY FOR LIVE! 🚀**
