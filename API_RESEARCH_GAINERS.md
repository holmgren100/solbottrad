# 🚀 DEEP API RESEARCH - Finding GAINERS on Solana

**Date:** 2025-12-04
**Status:** ✅ COMPLETE
**Focus:** Find APIs that identify tokens with 10x-100x potential (GAINERS)

---

## 📋 Executive Summary

**Goal:** Find the best API endpoints to discover Solana tokens with high gain potential (movers, new listings, trending, high volume growth).

**Key Findings:**
1. **Birdeye** - Best for trending/gainers but hitting FREE TIER LIMITS (30K CUs/month)
2. **Jupiter** - Good cycling strategies, already integrated and working
3. **DexScreener** - Limited API but has organic filter, already integrated
4. **Helius** - Premium option with real-time streaming (paid only)
5. **Raydium/Pump.fun** - Direct on-chain monitoring for NEW listings (requires WebSocket)

---

## 🔥 PRIORITY 1: Fix Birdeye (Currently Failing)

### Problem:
```
Birdeye trending tokens error 400: {"success":false,"message":"Compute units usage limit exceeded"}
```

### Root Cause:
- **Free Tier:** 30,000 CUs/month
- **Rate Limit:** 1 request/second
- **Current Usage:** Bot is hitting limits very quickly

### Solutions (Pick One):

#### **Option A: Optimize Birdeye Usage (FREE)**
1. **Reduce frequency** - Only call Birdeye every 5th scan (not every scan)
2. **Reduce limits** - Use `limit=5` instead of `limit=12` (save CUs)
3. **Use cheaper endpoints** - Token Trending is cheaper than Token List
4. **Track CU usage** - Monitor how many CUs we're using per day

**Estimated CU Usage:**
- Token Trending: ~10-20 CUs per call
- At current frequency: ~2,000-4,000 CUs per day
- Monthly: ~60,000-120,000 CUs (WAY over 30K limit!)

**Implementation:**
```python
# Only call Birdeye every 5th scan
if scan_count % 5 == 0:
    birdeye_tokens = await self.birdeye.get_trending_tokens(limit=5)
```

#### **Option B: Upgrade to Paid Tier (RECOMMENDED)**
- **Starter Plan:** $99/month → 3,000,000 CUs (100x more)
- **Rate Limit:** 15 RPS (15x faster)
- **Benefits:** Can use all endpoints freely, no more failures

#### **Option C: Disable Birdeye, Use Alternatives (CURRENT)**
- Already disabled in code
- Use Jupiter + DexScreener only
- Add Helius or Raydium monitoring for new listings

---

## 📊 API COMPARISON TABLE

| API | Focus | Free Tier | Best For | Status |
|-----|-------|-----------|----------|--------|
| **Jupiter** | Trending, traded, organic | ✅ Unlimited | Cycling strategies, variety | ✅ Working |
| **DexScreener** | Organic tokens, profiles | ✅ Unlimited | Filtering scams/boosted | ✅ Working |
| **Birdeye** | Gainers, trending, volume | ❌ 30K CUs/mo | Price change, gainers | ❌ DISABLED (hitting limits) |
| **Helius** | Real-time streaming | ❌ Paid only | New listings, swaps | ⚠️ Not integrated |
| **Raydium WebSocket** | New pairs | ✅ Free | Instant new listings | ⚠️ Not integrated |
| **Pump.fun Monitor** | New launches | ✅ Free | Brand new tokens | ⚠️ Not integrated |

---

## 🎯 DETAILED API ANALYSIS

### **1. Birdeye API (CURRENTLY DISABLED)**

**Official Docs:** https://docs.birdeye.so/docs/trending-tokens

#### **Best Endpoints for GAINERS:**

**A. Token Trending (Best for Gainers)**
```
GET https://public-api.birdeye.so/defi/token_trending
```

**Sort Options (Use These!):**
- `sort_by=priceChange24h` - **24h GAINERS** (tokens moving up fast)
- `sort_by=priceChange1h` - **1h GAINERS** (movers right now)
- `sort_by=volume24hUSD` - High volume (interest)
- `sort_by=liquidity` - Liquid tokens (can sell)
- `sort_by=rank` - Trending rank

**Parameters:**
```
sort_by: rank | liquidity | volume24hUSD | priceChange24h | priceChange1h
sort_type: asc | desc
offset: 0
limit: 1-50
```

**Example Request:**
```bash
curl --request GET \
  --url 'https://public-api.birdeye.so/defi/token_trending?sort_by=priceChange24h&sort_type=desc&limit=20' \
  --header 'X-API-KEY: YOUR_KEY' \
  --header 'x-chain: solana'
```

**Response Fields:**
- `address` - Token mint address
- `symbol` - Token symbol
- `liquidity` - Liquidity in USD
- `volume24hUSD` - 24h volume
- `priceChange24hPercent` - 24h price change %
- `priceChange1hPercent` - 1h price change %
- `rank` - Trending rank

**CU Cost:** ~10-20 CUs per call

**Our Implementation:**
- ✅ Already has cycling (rank → liquidity → volume24h → priceChange24h → priceChange1h)
- ✅ Rotates through 5 strategies
- ❌ Currently disabled due to CU limits

**Recommendation:**
1. **Short-term:** Keep disabled OR use Option A (reduce frequency)
2. **Long-term:** Upgrade to Starter plan ($99/mo) for 3M CUs

---

**B. Token List V3 API (NEW in 2025)**
```
GET https://public-api.birdeye.so/defi/v3/token/list
```

**Features:**
- Sort by price change % (1h, 2h, 4h, 8h, 24h)
- Sort by volume change %
- Sort by market cap, FDV, liquidity
- Sort by recent listing time

**Best for:**
- Finding new listings
- Tracking volume spikes
- Multi-timeframe analysis

**CU Cost:** Higher than Token Trending (~50-100 CUs)

**Recommendation:** Use Token Trending instead (cheaper)

---

### **2. Jupiter API (WORKING WELL)**

**Current Status:** ✅ Working, cycling enabled

**Endpoints:**
```
GET https://lite-api.jup.ag/tokens/v2/{category}/{interval}
```

**Categories:**
- `toporganicscore` - Organic activity (filters bots)
- `toptraded` - Highest volume
- `toptrending` - Trending tokens

**Intervals:**
- `5m`, `1h`, `6h`, `24h`

**Our Implementation:**
- ✅ Cycling through 3 categories
- ✅ Bluechip filter enabled
- ✅ Limit: 30 tokens per scan

**Strengths:**
- Free, unlimited
- No rate limits issues
- Good quality tokens
- Organic score filters bots

**Weaknesses:**
- Doesn't sort by price change %
- No direct "gainers" endpoint
- Misses very new tokens

**Recommendation:** Keep using as primary source ✅

---

### **3. DexScreener API (WORKING WELL)**

**Current Status:** ✅ Working, organic filter enabled

**Endpoint:**
```
GET https://api.dexscreener.com/token-profiles/latest/v1
```

**Our Implementation:**
- ✅ Gets organic (non-boosted) tokens
- ✅ Bluechip filter enabled
- ✅ Limit: 25 tokens per scan

**Strengths:**
- Free, unlimited
- Filters paid promotions (scams)
- Reliable data

**Weaknesses:**
- NO SORTING/FILTERING in API (major limitation!)
- Can't sort by price change, volume, or gainers
- Just returns "latest token profiles"
- Website has sorting but API doesn't expose it

**Recommendation:** Keep using, but limited value for finding gainers ⚠️

---

### **4. Helius (PREMIUM - NOT INTEGRATED)**

**Website:** https://www.helius.dev

**What They Offer:**
- Real-time WebSocket streams (LaserStream)
- Ultra-low latency on-chain events
- Webhooks for swaps, sales, listings
- Token metadata and balances
- Transaction streaming

**Best For:**
- **New Listings:** Monitor Raydium pool creation in real-time
- **Swaps:** Track buy/sell activity instantly
- **Volume Spikes:** Detect sudden trading activity

**Pricing:**
- **Free Tier:** Basic RPC only
- **Starter:** $50/month - 1M requests
- **Business:** $250/month - 5M requests
- **Enterprise:** Custom pricing

**Implementation Complexity:** Medium
- Need WebSocket integration
- Need to parse Raydium program logs
- Need to filter pool creation events

**Recommendation:**
- **Not urgent** - Jupiter + DexScreener cover most cases
- **Consider later** if we want real-time new listings

---

### **5. Raydium WebSocket Monitoring (FREE - NOT INTEGRATED)**

**Concept:** Monitor Raydium program directly via WebSocket

**Program ID:** `675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8`

**What It Does:**
- Catches NEW liquidity pools the moment they're created
- Faster than any API (instant)
- No API key needed (use public RPC)

**Implementation:**
```python
# Subscribe to Raydium program account changes
ws.programSubscribe(
    program_id="675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8",
    filter="pool_creation"
)
```

**Challenges:**
- Need to parse Solana logs
- High data volume (Raydium is busy)
- Need to filter out junk tokens
- Recommended to use Geyser plugin for production

**Best For:**
- **Brand new tokens** - Catch them within seconds
- **Pump.fun graduates** - Tokens migrating to Raydium
- **New pairs** - First to trade

**Recommendation:**
- **High value** but **high complexity**
- Worth considering after fixing Birdeye

---

### **6. Pump.fun Monitoring (FREE - NOT INTEGRATED)**

**Concept:** Monitor Pump.fun bonding curve completions

**Migration Account:** `39azUYFWPz3VHgKCf3VChUwbpURdCHRxjWVowf5jUJjg`

**What It Does:**
- Tracks tokens that "graduate" from Pump.fun to Raydium
- These often have strong momentum (completed bonding curve)
- Can catch early before they 10x on Raydium

**Implementation:**
```python
# Subscribe to Pump.fun migration account
ws.accountSubscribe(
    account="39azUYFWPz3VHgKCf3VChUwbpURdCHRxjWVowf5jUJjg"
)
```

**Identification:**
- Check token metadata for `createdOn: "pump.fun"`
- Or check if creator is Pump.fun program

**Best For:**
- **Early movers** - Get in right after Raydium launch
- **Community tokens** - Pump.fun requires community buying
- **Momentum plays** - Completed bonding curve = strong interest

**Recommendation:**
- **Very high value** for finding gainers
- **Medium complexity** - easier than full Raydium monitoring
- Should implement this!

---

## 🎯 RECOMMENDATIONS (Priority Order)

### **IMMEDIATE (This Week):**

**1. Fix Birdeye or Replace It**
   - **Option A (Free):** Reduce Birdeye frequency to every 5th scan, limit=5
   - **Option B (Paid):** Upgrade to Starter plan ($99/mo) for 3M CUs
   - **Option C (Alternative):** Add Pump.fun monitoring instead

**Why:** Birdeye has the BEST gainers data (priceChange24h, priceChange1h) but we're locked out due to CU limits.

### **SHORT-TERM (Next 2 Weeks):**

**2. Add Pump.fun Monitoring**
   - Monitor migration account for tokens graduating to Raydium
   - Catch early movers with strong community support
   - Free, no API key needed
   - **Expected impact:** Find tokens within seconds of Raydium launch

**3. Add Price Change Sorting**
   - Currently we use rank, volume, organic score
   - We need to track which tokens are MOVING (price change %)
   - Can calculate this ourselves from DexScreener/Jupiter data

### **LONG-TERM (Next Month):**

**4. Consider Helius LaserStream**
   - Real-time WebSocket for all Raydium events
   - Most comprehensive new listing detection
   - $50-$250/month depending on volume
   - **Expected impact:** Never miss a new listing

**5. Add Multi-Timeframe Analysis**
   - Track 1h, 6h, 24h price changes
   - Identify tokens in EARLY momentum (1h gainers that aren't 24h gainers yet)
   - This finds tokens BEFORE they trend

---

## 💰 COST ANALYSIS

| Solution | Monthly Cost | Value | Recommendation |
|----------|--------------|-------|----------------|
| **Keep Current (Jupiter + DexScreener)** | $0 | Medium | ⚠️ Missing gainers data |
| **Fix Birdeye - Reduce Frequency** | $0 | Medium-High | ✅ Good short-term fix |
| **Birdeye Starter Plan** | $99 | High | ✅ Best for gainers |
| **Add Pump.fun Monitoring** | $0 | Very High | ✅ Must implement! |
| **Add Helius LaserStream** | $50-$250 | Very High | ⚠️ Consider later |
| **Raydium WebSocket** | $0 | Very High | ⚠️ High complexity |

---

## 🔧 IMPLEMENTATION PLAN

### **Phase 1: Quick Wins (This Week)**

**A. Optimize Birdeye (Free Option)**
```python
# In src/main.py - only call Birdeye every 5th scan
if self.scan_count % 5 == 0 and enable_birdeye:
    birdeye_tokens = await self.birdeye.get_trending_tokens(limit=5)
```

**B. Add Price Change Tracking**
```python
# Track price changes ourselves from Jupiter/DexScreener data
# Sort tokens by price_change_24h and prioritize movers
```

### **Phase 2: High-Value Addition (Next Week)**

**C. Add Pump.fun Monitoring**
```python
# New file: src/market/pumpfun_monitor.py
class PumpfunMonitor:
    async def monitor_migrations(self):
        # Subscribe to migration account
        # Return tokens graduating to Raydium
```

### **Phase 3: Premium Features (Next Month)**

**D. Upgrade Birdeye to Paid**
- Get Starter plan ($99/mo)
- Re-enable all Birdeye endpoints
- Use full cycling (5 strategies)

**E. Consider Helius Integration**
- Evaluate Helius LaserStream
- Implement real-time new listing detection
- Compare results vs. Pump.fun monitoring

---

## 📝 TECHNICAL DETAILS

### **Birdeye Trending Tokens API**

**Endpoint:**
```
GET https://public-api.birdeye.so/defi/token_trending
```

**Headers:**
```
X-API-KEY: <your_api_key>
x-chain: solana
accept: application/json
```

**Parameters:**
```
sort_by: rank | liquidity | volume24hUSD | priceChange24h | priceChange1h
sort_type: asc | desc
offset: 0
limit: 1-50
```

**Response Structure:**
```json
{
  "success": true,
  "data": {
    "tokens": [
      {
        "address": "TokenMintAddress...",
        "symbol": "TOKEN",
        "name": "Token Name",
        "liquidity": 1500000,
        "volume24hUSD": 5000000,
        "priceChange24hPercent": 150.5,
        "priceChange1hPercent": 25.3,
        "rank": 1
      }
    ]
  }
}
```

**Our Implementation:**
- File: `src/market/birdeye_client.py`
- Method: `get_trending_tokens()`
- Cycling: 5 strategies (rank, liquidity, volume24h, priceChange24h, priceChange1h)
- Status: Disabled due to CU limits

---

## 🎯 EXPECTED OUTCOMES

### **If We Fix Birdeye:**
- ✅ Find tokens with 24h price change >100% (real gainers)
- ✅ Find tokens with 1h price change >20% (movers right now)
- ✅ Prioritize high-volume movers (liquid gainers)
- ✅ Cycle through 5 discovery strategies

### **If We Add Pump.fun Monitoring:**
- ✅ Catch tokens within SECONDS of Raydium launch
- ✅ Get tokens with proven community (completed bonding curve)
- ✅ Early entry before they trend elsewhere
- ✅ High-quality new listings only

### **If We Add Price Change Tracking:**
- ✅ Sort current tokens by price movement
- ✅ Prioritize movers over stagnant tokens
- ✅ Multi-timeframe analysis (1h, 6h, 24h)

---

## 📚 SOURCES

- [Birdeye Trending Tokens Documentation](https://docs.birdeye.so/docs/trending-tokens)
- [Birdeye Rate Limiting](https://docs.birdeye.so/docs/rate-limiting)
- [Birdeye Compute Unit Cost](https://docs.birdeye.so/docs/compute-unit-cost)
- [Birdeye Pricing](https://docs.birdeye.so/docs/pricing)
- [Jupiter Token API V2](https://dev.jup.ag/docs/tokens/v2)
- [DexScreener API Reference](https://docs.dexscreener.com/api/reference)
- [Helius Solana APIs](https://www.helius.dev/solana-token-apis)
- [Solana Raydium Monitoring](https://docs.chainstack.com/docs/solana-listening-to-pumpfun-migrations-to-raydium)
- [Pump.fun to Raydium Tracking](https://blogs.shyft.to/how-to-track-token-transfers-from-pump-fun-to-raydium-5ada83c2ac58)
- [Top 10 APIs for Solana Trading Bots](https://coincodecap.com/top-10-apis-to-get-real-time-data-for-solana-trading-bots)

---

**Status:** Ready for implementation 🚀
**Next Steps:** Choose Phase 1 option (A or B) and implement
