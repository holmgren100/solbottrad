# 🚀 CoinGecko & Apify Integration - Setup Guide

## Overview

I've successfully integrated **CoinGecko** and **Apify DexScreener** into your Solana trading bot!

### What Was Added:

1. **CoinGecko Client** - Top gainers/losers discovery (FREE)
2. **Apify DexScreener Client** - SORTED price change data (BEST for GAINERS, ~$50/mo)
3. **Multi-Source Strategy** - All 5 sources working together

---

## 📋 What You Need to Do

### 1. Install New Dependencies

```bash
pip install apify-client==1.7.1
```

Or install all requirements:
```bash
pip install -r requirements.txt
```

### 2. Update Your `.env` File

Add these lines to your `.env` file (NOT .env.example):

```bash
# CoinGecko API (FREE - already have the key!)
COINGECKO_API_KEY=CG-Mj7ZxXQgmzFK1ryHWB4EowdQ
ENABLE_COINGECKO=true

# Apify API (Demo/Free tier access confirmed)
APIFY_API_TOKEN=your_apify_token_here
ENABLE_APIFY=true
```

**Note:** I've added your CoinGecko API key above. For Apify, you need to get your API token from:
- Go to: https://console.apify.com/account/integrations
- Copy your API token
- Replace `your_apify_token_here` with the actual token

### 3. Restart the Bot

After updating `.env`, restart the bot:
```bash
python -m src.main
```

---

## 🎯 How It Works

### Multi-Source Token Discovery (5 Sources!)

The bot now scans tokens from **5 different sources**, each with cycling strategies:

#### **Source 1: Jupiter** (FREE)
- **Cycles:** toporganicscore → toptraded → toptrending
- **What it finds:** Organic growth tokens, high trading volume
- **Status:** Already enabled ✅

#### **Source 2: DexScreener** (FREE)
- **What it finds:** Organic tokens (no paid promotions)
- **Status:** Available, optional

#### **Source 3: Birdeye** (FREE tier)
- **Cycles:** priceChange24h → priceChange1h → volume → liquidity → rank
- **What it finds:** 24h/1h GAINERS with price movement
- **Status:** Already enabled ✅

#### **Source 4: CoinGecko** (FREE) **NEW!**
- **Cycles:** top_gainers → trending → top_losers
- **What it finds:** Top gainers across ALL chains (filtered for Solana)
- **Rate limit:** 30 calls/min (1,800/hour)
- **Cost:** FREE
- **Status:** Ready to enable ✅

#### **Source 5: Apify DexScreener** (~$50/mo) **NEW! BEST FOR GAINERS**
- **Cycles:** priceChange24h → priceChange6h → priceChange1h → volume → liquidity
- **What it finds:** SORTED DexScreener data by price change
- **Rate limit:** Depends on your plan (demo tier available)
- **Cost:** ~$50/month (pay-per-use)
- **Status:** Ready to enable ✅

---

## 💰 Cost Breakdown

| Source | Cost | Notes |
|--------|------|-------|
| Jupiter | FREE | Already using |
| DexScreener | FREE | Optional |
| Birdeye | FREE | Already using (30K CUs/month) |
| **CoinGecko** | **FREE** | **30 calls/min, unlimited** |
| **Apify** | **~$50/mo** | **BEST for GAINERS** |

**Total New Cost:** ~$50/month (only Apify paid)

---

## 🔥 Expected Improvements

With CoinGecko + Apify added:

### Before (Jupiter + Birdeye only):
- Limited price change sorting
- No cross-chain gainer discovery
- DexScreener API doesn't support sorting

### After (Jupiter + Birdeye + CoinGecko + Apify):
- ✅ **CoinGecko:** Top gainers from ALL chains (Solana filtered)
- ✅ **Apify:** SORTED DexScreener by priceChange24h/6h/1h
- ✅ **5 different discovery strategies** cycling together
- ✅ **Free fallback** (CoinGecko) if Apify fails
- ✅ **Best value** (~$50/mo for actual GAINERS)

---

## 🧪 Testing Recommendations

### Phase 1: Test CoinGecko First (FREE)

1. Update `.env` with CoinGecko key (already provided above)
2. Set `ENABLE_COINGECKO=true`
3. Restart bot and watch for:
   - `📡 Fetching tokens from CoinGecko (Top Gainers)...`
   - `✅ CoinGecko: Found X GAINERS`
4. Monitor for 1-2 hours to verify it's finding tokens

### Phase 2: Add Apify (Paid, but BEST)

1. Get Apify API token from https://console.apify.com/account/integrations
2. Update `.env` with token
3. Set `ENABLE_APIFY=true`
4. Restart bot and watch for:
   - `📡 Fetching tokens from Apify DexScreener (SORTED BY GAINERS)...`
   - `Starting Apify scraper (this may take 10-30 seconds)...`
   - `✅ Apify: Found X SORTED GAINERS`
5. **Note:** Apify runs take 10-30 seconds per scan (it's web scraping)

---

## 🎮 Cycling Strategy Explained

Each source rotates through different discovery methods on each scan:

**Example Scan Sequence:**

| Scan # | Jupiter | Birdeye | CoinGecko | Apify |
|--------|---------|---------|-----------|-------|
| 1 | toporganicscore | priceChange24h | top_gainers | priceChange24h |
| 2 | toptraded | priceChange1h | trending | priceChange6h |
| 3 | toptrending | volume | top_losers | priceChange1h |
| 4 | toporganicscore | liquidity | top_gainers | volume |
| 5 | toptraded | rank | trending | liquidity |

This ensures the bot discovers tokens using **different strategies** each scan, maximizing GAINER discovery!

---

## 📊 Monitoring Logs

After enabling, you'll see these logs:

### Startup:
```
✅ CoinGecko client initialized
✅ Apify DexScreener client initialized
🔧 Token sources: Jupiter=True, DexScreener=False, Birdeye=True, CoinGecko=True, Apify=True
```

### During Scan:
```
🔍 Starting token scan...
📡 Fetching tokens from Jupiter (CYCLING discovery)...
✅ Jupiter: Found 25 tokens (3 bluechips filtered)

📡 Fetching tokens from Birdeye (GAINERS focus)...
Birdeye Cycle 1/5: Using 'priceChange24h' discovery
✅ Birdeye: Found 5 GAINERS (0 bluechips filtered)

📡 Fetching tokens from CoinGecko (Top Gainers)...
CoinGecko Cycle 1/3: Using 'top_gainers' discovery
✅ CoinGecko: Found 8 GAINERS (2 bluechips filtered)

📡 Fetching tokens from Apify DexScreener (SORTED BY GAINERS)...
Apify Cycle 1/5: Using 'priceChange24h' discovery
Starting Apify scraper (this may take 10-30 seconds)...
✅ Apify: Found 18 SORTED GAINERS (2 bluechips filtered)

Combined: 56 unique tokens from all sources
```

---

## ⚠️ Important Notes

1. **Apify is SLOW** - Scraping takes 10-30 seconds per scan
2. **CoinGecko is FREE** - No cost, but rate limited to 30 calls/min
3. **Demo Tier** - You mentioned having Apify demo/free tier access
4. **Bluechip Filtering** - All sources filter out SOL, USDC, JUP, etc.
5. **Deduplication** - Bot tracks seen addresses to avoid duplicates

---

## 🚀 Quick Start Commands

```bash
# 1. Install dependencies
pip install apify-client==1.7.1

# 2. Edit .env file
nano .env
# Add:
# COINGECKO_API_KEY=CG-Mj7ZxXQgmzFK1ryHWB4EowdQ
# ENABLE_COINGECKO=true
# APIFY_API_TOKEN=your_token_here
# ENABLE_APIFY=true

# 3. Restart bot
python -m src.main

# 4. Watch logs for confirmation
# Should see: "✅ CoinGecko: Found X GAINERS"
# Should see: "✅ Apify: Found X SORTED GAINERS"
```

---

## 📚 Related Documentation

- **MULTI_SOURCE_STRATEGY.md** - Full implementation details
- **COMPREHENSIVE_DATA_SOURCES_RESEARCH.md** - Research on all options
- **BIRDEYE_ENABLED.md** - Previous Birdeye fix

---

## 🎯 Summary

**What's Ready:**
- ✅ CoinGecko client implemented
- ✅ Apify client implemented
- ✅ Both integrated into token scan flow
- ✅ Cycling strategies configured
- ✅ Bluechip filtering applied
- ✅ Health checks registered

**What You Need:**
1. Install `apify-client` package
2. Add API keys to `.env`
3. Restart bot
4. Monitor logs to confirm working

**Expected Result:**
Bot will find ACTUAL GAINERS using sorted price change data from Apify + top gainers from CoinGecko!

---

Good luck! Let me know if you need any adjustments or have questions. 🚀
