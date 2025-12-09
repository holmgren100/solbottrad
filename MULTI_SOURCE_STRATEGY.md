# 🎯 MULTI-SOURCE STRATEGY - Best of Each Platform

**Date:** 2025-12-04
**Status:** ✅ RECOMMENDED APPROACH
**Cost:** ~$50/month (only Apify DexScreener)

---

## 📋 THE STRATEGY: Use Each Source for What It's Best At

**Your Smart Approach:**
1. **Jupiter** - Trading execution + organic score data
2. **Apify DexScreener** - Main data for GAINERS (price change sorting) ← **PAY FOR THIS**
3. **Birdeye** - Additional gainer validation (free tier)
4. **GeckoTerminal** - FREE fallback if others break

---

## 🆓 WHAT GECKOTERMINAL DOES (FREE!)

### **What It Is:**
- CoinGecko's DEX aggregator (like DexScreener but from CoinGecko)
- Real-time DEX data across 90+ chains, 500+ DEXs
- **100% FREE API** with good rate limits

### **What Data It Provides:**

**1. Trending Pools** (GAINERS!)
```
GET https://api.geckoterminal.com/api/v2/networks/solana/trending_pools
```

**Returns:**
- Pool address, token addresses
- **Price change** (1h, 24h, 5m, 6h)
- Volume (24h, 5m, 1h, 6h)
- Liquidity in USD
- Buy/sell transaction counts
- Pool creation time

**Example Response:**
```json
{
  "data": {
    "attributes": {
      "name": "TOKEN/SOL",
      "price_change_percentage": {
        "h1": 45.2,    // Up 45% in 1 hour!
        "h24": 125.6   // Up 125% in 24 hours!
      },
      "volume_usd": {
        "h24": 1500000
      },
      "reserve_in_usd": 450000,
      "fdv_usd": 2000000
    }
  }
}
```

**2. New Pools** (NEW LISTINGS!)
```
GET https://api.geckoterminal.com/api/v2/networks/solana/new_pools
```

**Returns:**
- Newly created pools on Solana
- Same data as trending pools
- Good for catching early listings

**3. Specific Pool Data**
```
GET https://api.geckoterminal.com/api/v2/networks/solana/pools/{address}
```

**Returns:**
- Detailed pool information
- Historical data
- OHLC (candlestick) data

### **Pricing & Limits:**

| Tier | Cost | Rate Limit | Best For |
|------|------|------------|----------|
| **Free (Public)** | $0 | 30 calls/min | ✅ **Perfect for you!** |
| **Paid (CoinGecko API)** | $129-2499/mo | 500 calls/min | Overkill |

**30 calls/min = 1,800 calls/hour = plenty for a trading bot!**

### **Why Use GeckoTerminal:**

**Pros:**
- ✅ **100% FREE** (no API key even needed!)
- ✅ Price change data (h1, h24, h6, 5m)
- ✅ Trending pools (find movers)
- ✅ New pools (early listings)
- ✅ Good rate limits (30/min)
- ✅ **Perfect fallback** if Apify/Birdeye fail
- ✅ Different data source = more coverage

**Cons:**
- ⚠️ No custom sorting beyond trending
- ⚠️ Lower limits than paid APIs (but 30/min is fine)
- ⚠️ Beta (subject to changes)

**Best Used For:**
- ✅ **Fallback data source** (if Apify breaks)
- ✅ **Trending pools** (supplement to Apify gainers)
- ✅ **New pools** (catch fresh listings)
- ✅ **Validation** (cross-check data from other sources)

---

## 🔥 APIFY DEXSCREENER SCRAPERS - WHICH IS BEST?

I found **4 different scrapers** on Apify. Here's the comparison:

### **Scraper #1: crypto-scraper/dexscreener-tokens-scraper**

**Stats:**
- ❌ **Success Rate: 32.3%** (TERRIBLE!)
- Users: 761 total, 52 monthly
- Support: 2.1 days response time
- Known Issue: Can't retrieve contract addresses directly

**Verdict:** ❌ **AVOID** - Too unreliable!

---

### **Scraper #2: muhammetakkurtt/dexscreener-scraper** ⭐

**Stats:**
- ✅ **Success Rate: >99%** (EXCELLENT!)
- Users: 484 total, 22 monthly active
- Rating: **5.0/5** (7 reviews)
- Support: **0.63 hours** response time
- Bookmarks: 28

**Features:**
- Supports **80+ chains** including Solana
- **Default limit: 150 records** (good for bulk data)
- DEX-specific filtering (filter by Raydium, Orca, etc.)
- Real-time trending data
- **Price change filtering**
- **Volume/liquidity filtering**

**Input Parameters:**
```json
{
  "chain": "solana",
  "sortBy": "priceChange24h",  // Sort by 24h gainers!
  "sortOrder": "desc",
  "timeFrame": "6h",
  "minVolume": 50000,
  "minLiquidity": 10000,
  "limit": 30,
  "dexIdsSolana": ["raydium", "orca"]  // Filter by DEX
}
```

**What It Returns:**
```json
{
  "tokenAddress": "...",
  "symbol": "TOKEN",
  "priceUSD": 0.00045,
  "priceChange24h": 156.7,  // Up 156%!
  "priceChange1h": 23.4,
  "priceChange6h": 89.2,
  "volume24h": 1250000,
  "liquidity": 450000,
  "fdv": 2500000,
  "holders": 1234,
  "poolCreatedAt": "2025-12-04T10:30:00Z"
}
```

**Verdict:** ✅✅ **BEST CHOICE!** - This is the one you want!

---

### **Scraper #3: crypto-scraper/dexscreener-pair-scraper**

**Purpose:** Scrapes specific trading pairs
**Use Case:** If you know exact pairs to monitor
**Verdict:** ⚠️ Not for token discovery (too specific)

---

### **Scraper #4: crypto-scraper/dexscreener-top-traders-scraper**

**Purpose:** Extract top traders with PnL data
**Use Case:** Copy trading / smart money tracking
**Verdict:** ⚠️ Different use case (not for token discovery)

---

## 🎯 RECOMMENDED: muhammetakkurtt/dexscreener-scraper

**Why This One:**
1. ✅ **>99% success rate** (most reliable)
2. ✅ **5.0 rating** (users love it)
3. ✅ **Fast support** (0.63 hours)
4. ✅ **Price change sorting** (find GAINERS!)
5. ✅ **Custom filters** (volume, liquidity, DEX)
6. ✅ **150 token limit** (get more data)
7. ✅ **80+ chains** (future-proof)

**Cost:** ~$49-59/month (Apify Starter $39 + usage ~$10-20)

---

## 🏗️ THE COMPLETE MULTI-SOURCE ARCHITECTURE

### **Source #1: Jupiter (Already Working)**

**What It Does:**
- Trading execution (swap tokens)
- Token discovery (toporganicscore, toptraded, toptrending)
- Filters bot activity (organic score)

**Used For:**
- ✅ Executing trades
- ✅ Organic token discovery (supplement)
- ✅ Variety (cycling through 3 strategies)

**Cost:** FREE ✅
**Keep Using:** YES ✅

---

### **Source #2: Apify DexScreener (NEW - Main Source)** ⭐

**What It Does:**
- Scrapes DexScreener with **price change sorting**
- Returns tokens sorted by 24h gains (50-200%+)
- Filters by volume, liquidity, DEX, age

**Used For:**
- ✅ **PRIMARY source for GAINERS** (sorted by price change!)
- ✅ **Main data provider** (most important source)
- ✅ **Entry selection** (pick which tokens to trade)

**Implementation:**
```python
# Every scan, get top 30 gainers from DexScreener
async def get_dexscreener_gainers():
    response = await apify_client.call_actor(
        actor_id="muhammetakkurtt/dexscreener-scraper",
        run_input={
            "chain": "solana",
            "sortBy": "priceChange24h",  # 24h GAINERS!
            "sortOrder": "desc",
            "timeFrame": "6h",
            "minVolume": 50000,
            "minLiquidity": 10000,
            "limit": 30
        }
    )

    tokens = response["data"]
    # Returns 30 tokens sorted by highest 24h price change
    return tokens
```

**Cost:** ~$50/month ← **ONLY PAID SERVICE**
**Priority:** HIGHEST (main data source)

---

### **Source #3: Birdeye (Already Enabled)**

**What It Does:**
- Token trending by price change (priceChange24h, priceChange1h)
- Token security data
- Official Solana-native API

**Used For:**
- ✅ **Validation** (cross-check Apify data)
- ✅ **Additional gainers** (supplement Apify)
- ✅ **Security checks** (rug detection)

**Limitation:** Free tier 30K CUs/month (optimized to limit=5)

**Cost:** FREE (within limits) ✅
**Priority:** MEDIUM (supplement + validation)

---

### **Source #4: GeckoTerminal (NEW - Fallback)** 🆓

**What It Does:**
- Trending pools on Solana
- New pools (fresh listings)
- Price change data (h1, h24, h6)

**Used For:**
- ✅ **Fallback** if Apify fails
- ✅ **Trending pools** (supplement)
- ✅ **New listings** (early detection)
- ✅ **Validation** (third data source)

**Implementation:**
```python
# Fallback if Apify is down
async def get_geckoterminal_trending():
    response = requests.get(
        "https://api.geckoterminal.com/api/v2/networks/solana/trending_pools",
        params={"page": 1}
    )

    pools = response.json()["data"]
    # Extract tokens with high price change
    gainers = [
        p for p in pools
        if p["attributes"]["price_change_percentage"]["h24"] > 20
    ]
    return gainers
```

**Cost:** FREE ✅
**Priority:** LOW (fallback + supplement)

---

## 🔄 HOW IT WORKS TOGETHER

### **Every Token Scan:**

```
1. PRIMARY: Apify DexScreener (muhammetakkurtt)
   ↓
   Get 30 tokens sorted by priceChange24h
   Filter: volume >$50K, liquidity >$10K
   ↓
   Result: 30 ACTUAL GAINERS (tokens up 50-200%!)

2. SUPPLEMENT: Birdeye (if within CU limits)
   ↓
   Get 5 tokens using priceChange24h sorting
   ↓
   Result: 5 additional gainers

3. SUPPLEMENT: Jupiter (already running)
   ↓
   Get 30 tokens via cycling (organic/traded/trending)
   ↓
   Result: 30 quality tokens (may not be movers)

4. FALLBACK: GeckoTerminal (if Apify fails)
   ↓
   Get trending pools from Solana
   ↓
   Result: Trending tokens as backup

5. COMBINE & DEDUPLICATE
   ↓
   Total: ~60-90 unique tokens
   Prioritize: Apify tokens first (sorted by gains)
   ↓
   Analyze top 40-50 tokens
   Enter positions on best movers
```

---

## 💰 TOTAL COST BREAKDOWN

| Source | Monthly Cost | Purpose | Required? |
|--------|--------------|---------|-----------|
| **Jupiter** | $0 | Trading + organic discovery | ✅ YES |
| **Apify DexScreener** | ~$50 | MAIN gainers source | ✅ **YES** |
| **Birdeye Free** | $0 | Validation + supplement | ⚠️ Optional |
| **GeckoTerminal** | $0 | Fallback + trending | ⚠️ Optional |
| **TOTAL** | **~$50/month** | Complete system | - |

**You only pay for Apify DexScreener - everything else is FREE!**

---

## 🎯 EXPECTED OUTCOMES

### **With This Multi-Source Strategy:**

**Data Quality:**
- ✅ Get tokens **sorted by actual price gains** (Apify)
- ✅ Find tokens up 50-200% in 24h (GAINERS!)
- ✅ Cross-validate with 3 sources (reduce false positives)
- ✅ Fallback if primary fails (GeckoTerminal)

**Token Selection:**
- ✅ Prioritize tokens with **proven momentum** (already moving up)
- ✅ Filter out low-volume/low-liquidity tokens
- ✅ Get tokens from multiple DEXs (Raydium, Orca, etc.)
- ✅ Catch new listings (GeckoTerminal new pools)

**Risk Management:**
- ✅ **Better entries** (tokens already trending up)
- ✅ **Fewer "dead tokens"** (better quality data)
- ✅ **More winners** like Franinu (+168%), KABUTOPS (+118%)
- ✅ **Fewer losers** (avoid stagnant tokens)

---

## 🔧 IMPLEMENTATION PLAN

### **Phase 1: Add GeckoTerminal (FREE - 1 hour)**

```python
# File: src/market/geckoterminal_client.py
async def get_trending_pools(limit=20):
    url = "https://api.geckoterminal.com/api/v2/networks/solana/trending_pools"
    response = requests.get(url, params={"page": 1})
    pools = response.json()["data"][:limit]

    # Extract token addresses and price change data
    tokens = []
    for pool in pools:
        attrs = pool["attributes"]
        if attrs["price_change_percentage"]["h24"] > 20:  # Only +20%+ gainers
            tokens.append({
                "address": attrs["base_token_address"],
                "symbol": attrs["name"].split("/")[0],
                "price_change_24h": attrs["price_change_percentage"]["h24"],
                "volume_24h": attrs["volume_usd"]["h24"],
                "liquidity": attrs["reserve_in_usd"]
            })
    return tokens
```

**Time:** 1 hour
**Cost:** $0

---

### **Phase 2: Deploy Apify DexScreener (PAID - 4 hours)**

```python
# File: src/market/apify_dexscreener.py
from apify_client import ApifyClient

client = ApifyClient(os.getenv('APIFY_API_TOKEN'))

async def get_dexscreener_gainers(limit=30):
    # Run the muhammetakkurtt/dexscreener-scraper actor
    run = client.actor("muhammetakkurtt/dexscreener-scraper").call(
        run_input={
            "chain": "solana",
            "sortBy": "priceChange24h",  # Sort by 24h gainers!
            "sortOrder": "desc",
            "timeFrame": "6h",
            "minVolume": 50000,        # Min $50K volume
            "minLiquidity": 10000,     # Min $10K liquidity
            "limit": limit,
            "dexIdsSolana": ["raydium", "orca", "meteora"]  # Major DEXs
        }
    )

    # Get results
    tokens = []
    for item in client.dataset(run["defaultDatasetId"]).iterate_items():
        tokens.append({
            "address": item["tokenAddress"],
            "symbol": item["symbol"],
            "price_change_24h": item["priceChange24h"],
            "price_change_6h": item["priceChange6h"],
            "volume_24h": item["volume24h"],
            "liquidity": item["liquidity"],
            "fdv": item.get("fdv"),
            "holders": item.get("holders")
        })

    return tokens
```

**Time:** 4 hours
**Cost:** ~$50/month

---

### **Phase 3: Integrate Into Main Bot (2 hours)**

```python
# File: src/main.py
async def scan_for_tokens(self):
    all_tokens = []

    # 1. PRIORITY: Apify DexScreener (GAINERS!)
    try:
        apify_tokens = await self.apify_dex.get_dexscreener_gainers(limit=30)
        print(f"✅ Apify: Found {len(apify_tokens)} GAINERS")
        all_tokens.extend(apify_tokens)
    except Exception as e:
        print(f"⚠️ Apify failed, using GeckoTerminal fallback")

        # FALLBACK: GeckoTerminal
        gecko_tokens = await self.geckoterminal.get_trending_pools(limit=20)
        print(f"✅ GeckoTerminal: Found {len(gecko_tokens)} trending")
        all_tokens.extend(gecko_tokens)

    # 2. SUPPLEMENT: Birdeye (if available)
    if self.birdeye and scan_count % 2 == 0:  # Every 2nd scan
        birdeye_tokens = await self.birdeye.get_trending_tokens(limit=5)
        print(f"✅ Birdeye: Found {len(birdeye_tokens)} gainers")
        all_tokens.extend(birdeye_tokens)

    # 3. SUPPLEMENT: Jupiter (already running)
    jupiter_tokens = await self.jupiter.get_trending_tokens(limit=30)
    print(f"✅ Jupiter: Found {len(jupiter_tokens)} organic")
    all_tokens.extend(jupiter_tokens)

    # 4. DEDUPLICATE & FILTER BLUECHIPS
    unique_tokens = deduplicate(all_tokens)
    filtered_tokens = filter_bluechips(unique_tokens)

    # 5. PRIORITIZE by price change (Apify tokens first)
    sorted_tokens = sorted(
        filtered_tokens,
        key=lambda x: x.get("price_change_24h", 0),
        reverse=True
    )

    print(f"✅ Combined: {len(sorted_tokens)} unique tokens (sorted by gains)")
    return sorted_tokens[:50]  # Top 50 gainers
```

**Time:** 2 hours
**Total Implementation:** 7 hours

---

## ✅ SUCCESS CRITERIA

**You'll know it's working when:**

1. **Logs show all 4 sources:**
```
✅ Apify: Found 30 GAINERS (sorted by price change)
✅ Birdeye: Found 5 gainers
✅ Jupiter: Found 30 organic tokens
✅ GeckoTerminal: Available as fallback
✅ Combined: 65 unique tokens (sorted by gains)
```

2. **Token quality improves:**
- More entries on tokens already moving up (+20-50%)
- Fewer "dead token" closures
- Higher win rate (more like Franinu +168%, KABUTOPS +118%)

3. **Telegram shows better entries:**
- Entry notifications for tokens with momentum
- Price change % in notification
- Fewer stagnant token picks

---

## 📊 COMPARISON: Before vs After

### **BEFORE (Current):**
```
Sources: Jupiter + DexScreener API + Birdeye (disabled)
Sorting: organic, traded, trending (NO price change)
Data: Random tokens, not sorted by gains
Result: Many losses (tokens not moving)
Cost: $0
```

### **AFTER (Multi-Source):**
```
Sources: Apify DexScreener + Jupiter + Birdeye + GeckoTerminal
Sorting: priceChange24h (ACTUAL GAINERS!)
Data: 30 tokens sorted by highest gains + supplements
Result: Better entries on tokens with momentum
Cost: ~$50/month (only Apify)
```

---

## 🎯 FINAL RECOMMENDATION

**Deploy This Strategy:**

1. ✅ **Week 1:** Add GeckoTerminal (FREE, 1 hour)
2. ✅ **Week 2:** Deploy Apify DexScreener (~$50/mo, 4 hours)
3. ✅ **Week 3:** Monitor results, tune filters

**Total Investment:**
- **Time:** 7 hours total
- **Cost:** ~$50/month (only Apify, everything else FREE)
- **Impact:** HIGH - get actual GAINERS sorted by price change!

**Best Value:** You get 4 data sources but only pay for 1 (Apify)!

---

## 📚 SOURCES

**GeckoTerminal:**
- [GeckoTerminal API Documentation](https://apiguide.geckoterminal.com/)
- [GeckoTerminal API Docs](https://api.geckoterminal.com/docs/index.html)
- [GeckoTerminal FAQ](https://apiguide.geckoterminal.com/faq)
- [DEX API for DeFi Developers](https://www.geckoterminal.com/dex-api)

**Apify DexScreener Scrapers:**
- [DexScreener Token Scraper (crypto-scraper)](https://apify.com/crypto-scraper/dexscreener-tokens-scraper)
- [DexScreener Trending API (muhammetakkurtt)](https://apify.com/muhammetakkurtt/dexscreener-scraper) ⭐ **BEST**
- [Apify Pricing](https://apify.com/pricing)

**Supporting Documentation:**
- [GitHub: geckoterminal-api Python wrapper](https://github.com/dineshpinto/geckoterminal-api)
- [CoinGecko API Pricing](https://www.coingecko.com/en/api/pricing)

---

**Status:** Ready to implement! 🚀
**Next Step:** Choose which phase to start with (I recommend Week 1: add GeckoTerminal for FREE first)
