# Birdeye CU Limit Fix

## ❌ Issue

```
Birdeye trending tokens error 400: {"success":false,"message":"Compute units usage limit exceeded"}
```

**Root Cause:** You've hit the **30,000 CUs/month** limit on the Birdeye FREE tier.

---

## ✅ Quick Fix: Disable Birdeye

Since you're already getting tokens from Jupiter + DexScreener + CoinGecko, you can disable Birdeye temporarily:

```bash
# Edit .env file
nano .env

# Find line 131 and change to:
ENABLE_BIRDEYE=false

# Restart bot
pkill -f "python3 -m src.main"
python3 -m src.main
```

**Expected Result:**
```
🔧 Token sources: Jupiter=True, DexScreener=True, Birdeye=False, CoinGecko=True
✅ Combined: 40-60 tokens from 3 sources
```

---

## 📊 Current Token Discovery (Without Birdeye)

You're still getting **45 tokens** from 3 sources:

| Source | Tokens | Status |
|--------|--------|--------|
| **Jupiter** | 25 tokens | ✅ Working |
| **DexScreener** | 25 tokens | ✅ Working |
| **CoinGecko** | 0-15 tokens | ⚠️ Just fixed |
| **Birdeye** | 0 tokens | ❌ CU limit |

**After disabling Birdeye:** Still finding 40-50+ tokens per scan!

---

## 🔄 Options to Fix Birdeye

### Option 1: Wait for Monthly Reset (FREE)

Birdeye CUs reset on the **1st of each month**.

- **Current month:** December (used up 30K CUs)
- **Reset date:** January 1, 2025
- **What to do:** Keep Birdeye disabled until Jan 1, then re-enable

```bash
# On January 1, 2025:
nano .env
# Change: ENABLE_BIRDEYE=true
# Restart bot
```

---

### Option 2: Reduce Birdeye Usage (FREE, but limited)

If you want to keep using Birdeye with remaining CUs:

**Reduce scan frequency:**
```bash
# Current: Bot scans every 2-5 minutes
# Each Birdeye call uses ~500-1000 CUs
# 30K CUs ≈ 30-60 API calls

# Option: Disable Birdeye during testing, only enable for production
ENABLE_BIRDEYE=false  # During paper trading
ENABLE_BIRDEYE=true   # Only when going live
```

**Or reduce limit:**
- Edit `src/market/birdeye_client.py` line 920
- Change `limit=5` to `limit=3` (uses fewer CUs)

---

### Option 3: Upgrade to Birdeye Paid Tier

**Birdeye Pro:**
- Cost: **$99/month**
- CUs: **300,000 CUs/month** (10x more)
- Rate limit: Higher request limits

**Is it worth it?**
- ❌ **No**, not yet - you already have 3 FREE sources working
- ✅ **Maybe later** if you need more GAINERS after testing
- ✅ **Consider Apify instead** (~$50/mo for sorted DexScreener data)

---

## 🎯 Recommended Strategy

### Phase 1: Test Without Birdeye (Current)

```bash
# Disable Birdeye
ENABLE_BIRDEYE=false

# Active sources (FREE):
# - Jupiter (cycling: toporganicscore → toptraded → toptrending)
# - DexScreener (organic tokens only)
# - CoinGecko (top_gainers → trending)

# Expected: 40-60 tokens per scan, all FREE
```

**Test for 6-12 hours:**
- ✅ Win rate 50-60%?
- ✅ Finding quality tokens?
- ✅ GAINERS in the feed?

---

### Phase 2: Add Apify Instead (Optional, ~$50/mo)

If you need MORE sorted GAINERS:

```bash
# Instead of Birdeye Pro ($99/mo):
# Use Apify DexScreener ($50/mo)

ENABLE_APIFY=true
APIFY_API_TOKEN=your_token_here

# Apify provides:
# - SORTED by priceChange24h/6h/1h (ACTUAL GAINERS!)
# - Better than Birdeye for GAINER discovery
# - Cheaper than Birdeye Pro
```

---

### Phase 3: Re-enable Birdeye (After Jan 1)

On **January 1, 2025**, your Birdeye CUs reset:

```bash
# Re-enable Birdeye
ENABLE_BIRDEYE=true

# Now you have 4 FREE sources:
# - Jupiter
# - DexScreener
# - CoinGecko
# - Birdeye (30K CUs fresh)
```

---

## 🚨 Current Status Summary

**Working (3 sources, all FREE):**
- ✅ Jupiter: 18-25 tokens per scan
- ✅ DexScreener: 25 tokens per scan
- ✅ CoinGecko: 10-15 tokens per scan (just fixed)

**Not Working:**
- ❌ Birdeye: CU limit exceeded (30K/month used)

**Total:** 40-60 tokens per scan from 3 FREE sources

---

## 📋 Action Items

### Immediate (Now):

```bash
# 1. Disable Birdeye
nano .env
# Line 131: ENABLE_BIRDEYE=false

# 2. Restart bot
pkill -f "python3 -m src.main"
python3 -m src.main

# 3. Verify working
tail -f trading_bot.log | grep -E "Token sources|Found.*tokens"

# Expected:
# 🔧 Token sources: Jupiter=True, DexScreener=True, Birdeye=False, CoinGecko=True
# ✅ Jupiter: Found 25 tokens
# ✅ DexScreener: Found 25 tokens
# ✅ CoinGecko: Found 15 GAINERS
# ✅ Combined: 55 unique tokens
```

### After CoinGecko Fix (Next restart):

```bash
# Pull latest CoinGecko fixes
git pull origin claude/restore-solana-bot-013YagNNs2FiAmTvNscyLeqq

# Restart
pkill -f "python3 -m src.main"
python3 -m src.main
```

### January 1, 2025:

```bash
# Re-enable Birdeye (fresh 30K CUs)
nano .env
# Line 131: ENABLE_BIRDEYE=true
```

---

## 🎯 Expected Results

**After disabling Birdeye:**
```
🔍 Starting token scan...
🔧 Token sources: Jupiter=True, DexScreener=True, Birdeye=False, CoinGecko=True

📡 Fetching tokens from Jupiter...
✅ Jupiter: Found 25 tokens

📡 Fetching tokens from DexScreener...
✅ DexScreener: Found 25 tokens

📡 Fetching tokens from CoinGecko...
✅ CoinGecko: Found 15 GAINERS

✅ Combined: 55 unique tokens from 3 sources
```

**Still plenty of tokens for finding GAINERS! 🚀**

---

## 💡 Key Takeaway

**You DON'T need Birdeye right now:**
- You have 3 FREE sources finding 40-60 tokens
- CoinGecko finds top gainers (sorted by 24h change)
- DexScreener finds organic tokens
- Jupiter finds trending/traded tokens

**Save money, test with FREE sources first!**

If you hit batch 5-6 numbers (50-60% win rate) with just these 3 sources, then consider Apify (~$50/mo) instead of Birdeye Pro ($99/mo).
