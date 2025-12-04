# 🔍 COMPREHENSIVE RESEARCH - All Data Sources for Finding GAINERS

**Date:** 2025-12-04
**Status:** ✅ COMPLETE - Ready for Decision
**Focus:** Find the BEST way to get Solana token data (gainers, movers, new listings)

---

## 📋 EXECUTIVE SUMMARY

I researched **ALL available options** for getting Solana token data to find GAINERS:

**Categories Researched:**
1. ✅ **Paid APIs** (Apify, Birdeye, Helius, Shyft)
2. ✅ **Free APIs** (Jupiter, DexScreener, GeckoTerminal)
3. ✅ **Web Scrapers** (GitHub open-source, Apify scrapers)
4. ✅ **Social Signals** (Twitter bots, Telegram channels)
5. ✅ **Alternative Platforms** (GMGN, Photon, Step Finance)

**Key Finding:** There's a **middle ground** between expensive paid APIs and limited free APIs!

---

## 🎯 THE BIG PICTURE - Option Matrix

| Approach | Cost | Quality | Difficulty | Recommendation |
|----------|------|---------|------------|----------------|
| **Current (Jupiter + DexScreener + Birdeye Free)** | $0 | ⭐⭐⭐ Medium | ✅ Easy | Good baseline |
| **Apify DexScreener Scraper** | $5-39/mo | ⭐⭐⭐⭐ High | ✅ Easy | **BEST VALUE** |
| **GitHub Open-Source Scrapers** | $0 | ⭐⭐⭐ Medium | ⚠️ Medium | Good if technical |
| **Birdeye Paid (Starter)** | $99/mo | ⭐⭐⭐⭐⭐ Best | ✅ Easy | Best but expensive |
| **Helius/Shyft APIs** | $49-99/mo | ⭐⭐⭐⭐ High | ⚠️ Medium | For real-time data |
| **Twitter/Telegram Signals** | $0-100/mo | ⭐⭐ Low-Med | ⚠️ Risky | Supplement only |
| **Alternative Platforms** | $0 | ⭐⭐⭐ Medium | ✅ Easy | Good additions |

---

## 💡 RECOMMENDED SOLUTION: The Middle Ground

### **Option 1: Apify DexScreener Scraper (BEST VALUE)**

**What It Does:**
- Scrapes DexScreener for trending tokens, gainers, price changes
- Sorts by liquidity, volume, price change (24h, 6h, 1h)
- Real-time WebSocket data or HTTP requests
- Returns clean JSON with all token data

**Pricing:**
- **Free Tier:** $5 worth of credits/month (good for testing)
- **Starter Plan:** $39/month + usage (~$10-20 extra for your volume)
- **Total Cost:** ~$49-59/month for unlimited scraping

**How It Works:**
```python
# Call Apify API to run the scraper
response = requests.post(
    "https://api.apify.com/v2/acts/crypto-scraper~dexscreener-tokens-scraper/runs",
    json={
        "chain": "solana",
        "sortBy": "priceChange24h",  # GAINERS!
        "timeFrame": "6h",
        "minVolume": 50000,
        "limit": 30
    }
)
```

**Pros:**
- ✅ Get DexScreener's FULL data (not limited API)
- ✅ Sort by price change % (GAINERS!)
- ✅ Filter by any criteria (volume, liquidity, age)
- ✅ No website anti-bot issues (Apify handles it)
- ✅ Reliable, maintained by professionals
- ✅ Cheaper than Birdeye paid ($49 vs $99)

**Cons:**
- ❌ Costs $49-59/month (not free)
- ❌ Requires API integration
- ❌ Usage-based pricing (more calls = more cost)

**Best For:** **YOUR USE CASE!** You need sorted, filtered gainers data without huge costs.

---

### **Option 2: GitHub Open-Source Scrapers (FREE)**

**Top Projects:**

**1. nicHamsa/dexscreener-parser**
- **FREE and open-source**
- Scrapes DexScreener with Selenium (stealth browser)
- Sends Telegram alerts for new tokens
- Custom filters: liquidity, volume, market cap, age
- **No API costs**

**2. vincentkoc/dexscraper**
- WebSocket-based (real-time)
- Supports Solana
- CLI interface + Python library
- Cloudflare bypass built-in

**3. doffn/Dexscreen-scraper**
- WebSocket scraping
- Flask API for easy integration
- Real-time trending data

**How It Works:**
```python
# Example from nicHamsa/dexscreener-parser
# 1. Clone repo
git clone https://github.com/nicHamsa/dexscreener-parser
cd dexscreener-parser

# 2. Configure filters
# filters.json: { "minVolume": 50000, "minLiquidity": 10000 }

# 3. Run scraper
python scraper.py

# 4. Gets data + sends Telegram alerts
```

**Pros:**
- ✅ **100% FREE**
- ✅ Full control over logic
- ✅ Can customize any filter
- ✅ Community-maintained
- ✅ Telegram integration built-in

**Cons:**
- ❌ Requires technical setup
- ❌ DexScreener may block IPs (Cloudflare)
- ❌ Maintenance burden (if site changes)
- ❌ May break with website updates

**Best For:** If you're technical and want FREE solution with full control.

---

## 🔥 DETAILED OPTIONS BREAKDOWN

### **A. PAID API SERVICES**

#### **1. Birdeye Paid Tier**

**Pricing:**
- Free: 30,000 CUs/month (hitting limits)
- **Starter: $99/month** - 3M CUs, 15 RPS
- Premium Plus: $250/month - 15M CUs, 50 RPS

**Features:**
- ✅ **BEST price change sorting** (priceChange24h, priceChange1h)
- ✅ Official API (most reliable)
- ✅ Real-time data
- ✅ Comprehensive token data

**Verdict:** Best quality but expensive ($99/mo vs $49 for Apify).

---

#### **2. Helius**

**Pricing:**
- Free: 1M credits/month, 10 RPS
- **Developer: $49/month** - 10M credits, 50 RPS
- Business: $499/month - 100M credits, 200 RPS

**Features:**
- ✅ Real-time WebSocket streaming
- ✅ New listings instantly (monitor Raydium)
- ✅ Webhooks for events
- ✅ Staked connections (better tx inclusion)

**Use Case:** **Real-time new listings** (Pump.fun graduates, Raydium new pairs)

**Verdict:** Good for real-time monitoring, but requires WebSocket integration.

---

#### **3. Shyft**

**Pricing:**
- Free tier available (limits unclear)
- Paid tiers available (check shyft.to/dashboard/pricing)

**Features:**
- ✅ RESTful APIs (simpler than raw RPC)
- ✅ NFT, DeFi, transaction APIs
- ✅ No rate limits on gRPC subscriptions

**Verdict:** Good for general Solana data, less focused on token discovery.

---

### **B. FREE API SERVICES**

#### **4. Jupiter (Current)**

**Pricing:** FREE ✅

**Features:**
- Cycles: toporganicscore, toptraded, toptrending
- Filters bots (organic score)
- No rate limits

**Limitation:** ❌ No price change sorting

**Verdict:** Keep using, but supplement with others.

---

#### **5. DexScreener Official API (Current)**

**Pricing:** FREE ✅

**Features:**
- `/token-profiles/latest/v1` endpoint
- Organic tokens (filters boosted)

**Limitation:** ❌ **NO SORTING** (can't sort by price change, volume, etc.)

**Verdict:** Limited API - this is why web scraping is better.

---

#### **6. GeckoTerminal**

**Pricing:** FREE ✅

**Features:**
- Real-time DEX analytics
- TradingView charts
- Tracks pools, volume, liquidity
- **FREE Public API**

**Example:**
```
GET https://api.geckoterminal.com/api/v2/networks/solana/trending_pools
GET https://api.geckoterminal.com/api/v2/networks/solana/new_pools
```

**Verdict:** **GREAT FREE ALTERNATIVE** to DexScreener API!

---

### **C. WEB SCRAPING SOLUTIONS**

#### **7. Apify DexScreener Scrapers**

**Multiple scrapers available:**

**a) crypto-scraper/dexscreener-tokens-scraper**
- Extracts token prices, liquidity, volumes, transactions
- Sorts by liquidity, volume, price change
- Supports 18+ chains including Solana

**b) muhammetakkurtt/dexscreener-scraper**
- Trending API
- Real-time data
- Custom time frames (5m, 1h, 6h, 24h)

**Pricing:**
- Free: $5 credits/month
- Starter: $39/month + usage
- **Total:** ~$49-59/month

**Verdict:** **BEST VALUE** for sorted DexScreener data.

---

#### **8. GitHub Open-Source Scrapers**

See **Option 2** above for details.

**Top Picks:**
- **nicHamsa/dexscreener-parser** - Most complete, Telegram alerts
- **vincentkoc/dexscraper** - WebSocket-based, real-time
- **doffn/Dexscreen-scraper** - Flask API, easy integration

**Verdict:** FREE but requires technical work.

---

### **D. SOCIAL MEDIA SIGNALS**

#### **9. Twitter/X Token Snipers**

**GitHub: solanabots/Solana-Twitter-Bot**
- Monitors specific Twitter accounts for token addresses
- Auto-buys new tokens mentioned
- Uses multiple wallets

**Limitations:**
- ❌ Risky (often scams/pumps)
- ❌ Requires Twitter API ($100/month for API access)
- ❌ Late entry (by the time it's on Twitter, often too late)

**Verdict:** NOT RECOMMENDED as primary source.

---

#### **10. Telegram Signal Channels**

**Popular Channels:**
- Trojan Bot (largest, 1.7M users)
- SolTradingBot (Solana-specific)
- Maestro (Copy Trade & Signals)
- DegenPump (13.7K subscribers, claims 98% success)

**Features:**
- Some bots have "Signals" feature
- Auto-buy on signal received
- Copy trade from successful wallets

**Limitations:**
- ❌ **Many are pump-and-dump schemes**
- ❌ High risk of scams
- ❌ Insider manipulation
- ❌ Late entry (by the time signal is sent)

**Verdict:** **RISKY** - Use with extreme caution, NOT as primary source.

---

### **E. ALTERNATIVE PLATFORMS**

#### **11. GMGN.AI**

**Pricing:** FREE with premium features

**Features:**
- ✅ Meme token focus
- ✅ Smart money tracking (copy top traders)
- ✅ Contract security checks
- ✅ Insider trader monitoring
- ✅ Honeypot detection

**Verdict:** **EXCELLENT supplement** for security + smart money tracking!

---

#### **12. Photon**

**Pricing:** FREE

**Features:**
- One-click trading on Solana
- Recent pairs (last 5m, 30m, 1h)
- Trending pairs

**Verdict:** Good for manual discovery, not for automated bots.

---

#### **13. Step Finance**

**Pricing:** FREE

**Features:**
- Portfolio dashboard
- Visual insights for Solana positions
- Performance tracking

**Verdict:** For portfolio management, not token discovery.

---

## 🎯 RECOMMENDED IMPLEMENTATION PLAN

### **Phase 1: Quick Win (FREE - This Week)**

**Option A: Enable Birdeye + Add GeckoTerminal**
```python
# 1. Birdeye (already enabled, just restart bot)
#    - Get priceChange24h, priceChange1h sorting
#    - Limit=5 to stay within free tier

# 2. Add GeckoTerminal API (FREE!)
#    - GET /networks/solana/trending_pools
#    - GET /networks/solana/new_pools
#    - Supplement Jupiter + DexScreener
```

**Cost:** $0
**Effort:** 1-2 hours
**Impact:** Medium - adds trending + new pools data

---

**Option B: Deploy GitHub Scraper**
```bash
# 1. Clone nicHamsa/dexscreener-parser
git clone https://github.com/nicHamsa/dexscreener-parser

# 2. Configure filters
# Set: minVolume=50K, minLiquidity=10K, minPriceChange=20%

# 3. Run scraper + Telegram alerts
python scraper.py
```

**Cost:** $0
**Effort:** 2-4 hours setup
**Impact:** High - get sorted/filtered DexScreener data for FREE

---

### **Phase 2: Paid Upgrade (Best Value - Next Week)**

**Deploy Apify DexScreener Scraper**
```python
# 1. Sign up for Apify Starter ($39/mo)
# 2. Integrate API:

import requests

def get_gainers_from_dex():
    response = requests.post(
        "https://api.apify.com/v2/acts/crypto-scraper~dexscreener-tokens-scraper/runs",
        headers={"Authorization": f"Bearer {APIFY_API_TOKEN}"},
        json={
            "chain": "solana",
            "sortBy": "priceChange24h",  # GAINERS!
            "sortOrder": "desc",
            "timeFrame": "6h",
            "minVolume": 50000,
            "minLiquidity": 10000,
            "limit": 30
        }
    )

    # Get tokens sorted by 24h price change
    tokens = response.json()["data"]
    return [t for t in tokens if t["priceChange24h"] > 20]  # Only +20%+ gainers
```

**Cost:** ~$49-59/month
**Effort:** 4-6 hours integration
**Impact:** **HIGH** - get DexScreener's FULL sorted data

---

**Alternative: Upgrade Birdeye to Starter**

**Cost:** $99/month
**Impact:** **HIGHEST** quality data, but more expensive

---

### **Phase 3: Advanced (Optional - Long-term)**

**Add Real-Time New Listings**

**Option 1: Helius WebSocket** ($49/mo)
- Monitor Raydium program for new pairs
- Catch tokens within seconds of launch

**Option 2: Pump.fun Monitoring** (FREE)
- Monitor migration account
- Catch tokens graduating to Raydium

**Cost:** $0-49/month
**Effort:** 8-12 hours integration
**Impact:** **VERY HIGH** - catch tokens at launch

---

## 💰 COST COMPARISON

| Solution | Monthly Cost | Data Quality | Maintenance | RECOMMENDED? |
|----------|--------------|--------------|-------------|--------------|
| **Current (Jupiter + DexScreener + Birdeye Free)** | $0 | ⭐⭐⭐ | Low | ✅ Baseline |
| **+ GeckoTerminal API** | $0 | ⭐⭐⭐ | Low | ✅ Easy add |
| **+ GitHub Scraper** | $0 | ⭐⭐⭐⭐ | Medium | ✅ If technical |
| **Apify Scraper** | $49-59 | ⭐⭐⭐⭐ | Low | ✅✅ **BEST VALUE** |
| **Birdeye Starter** | $99 | ⭐⭐⭐⭐⭐ | Low | ⚠️ Expensive |
| **Helius Developer** | $49 | ⭐⭐⭐⭐ | Medium | ⚠️ For real-time |
| **Twitter/Telegram Signals** | $0-100 | ⭐⭐ | High (risky) | ❌ NOT recommended |
| **GMGN.AI** | $0 | ⭐⭐⭐ | Low | ✅ Supplement |

---

## 🎯 MY FINAL RECOMMENDATION

### **Best Approach: 3-Tier Strategy**

**Tier 1: FREE (Do Now - 0-2 hours)**
1. ✅ Restart bot (enable Birdeye)
2. ✅ Add GeckoTerminal API (trending + new pools)
3. ✅ Add GMGN.AI for smart money tracking

**Tier 2: Low-Cost Value (Next Week - ~$50/mo)**
4. ✅ **Deploy Apify DexScreener scraper** ($49-59/mo)
   - Get sorted data by price change
   - Filter by volume, liquidity, age
   - No maintenance, reliable

**Tier 3: Advanced (Optional - Long-term)**
5. ⚠️ Add Helius for real-time new listings ($49/mo)
6. ⚠️ OR deploy Pump.fun monitoring (FREE)

**Total Cost:**
- **Phase 1 (Free):** $0/month ← Start here!
- **Phase 2 (Value):** ~$50/month ← Best bang for buck
- **Phase 3 (Advanced):** ~$100/month ← If you need real-time

---

## ⚠️ WHAT TO AVOID

**DON'T USE (High Risk):**
1. ❌ Telegram pump groups (scams, pump-and-dumps)
2. ❌ Twitter snipers (late entry, often scams)
3. ❌ "Guaranteed moonshot" channels
4. ❌ Paid signal groups without track record

**WHY:** These are risky, manipulated, and you'll lose money.

---

## 📊 EXPECTED OUTCOMES

### **If You Add GeckoTerminal (FREE):**
- ✅ Get trending pools data
- ✅ See new pools immediately
- ✅ Supplement Jupiter + DexScreener
- ✅ No cost, easy integration

### **If You Deploy GitHub Scraper (FREE):**
- ✅ Get sorted DexScreener data (by price change!)
- ✅ Custom filters (volume, liquidity, age)
- ✅ Telegram alerts for new tokens
- ✅ Full control, no API costs
- ⚠️ Requires technical setup + maintenance

### **If You Use Apify Scraper ($49/mo):**
- ✅ **Get DexScreener's FULL data with sorting**
- ✅ Sort by priceChange24h (ACTUAL GAINERS!)
- ✅ Professional, reliable, maintained
- ✅ No website blocking issues
- ✅ Clean JSON output
- ✅ **BEST value for money**

### **If You Upgrade Birdeye ($99/mo):**
- ✅ **BEST data quality**
- ✅ Official API (most reliable)
- ✅ Multiple sorting options
- ✅ Real-time updates
- ❌ Most expensive option

---

## 🔄 NEXT STEPS

**Decision Time:**

**Option 1: FREE Approach**
- Add GeckoTerminal API
- Deploy GitHub scraper
- Total cost: $0

**Option 2: Value Approach (RECOMMENDED)**
- Add GeckoTerminal API (free)
- Deploy Apify scraper ($49/mo)
- Total cost: ~$50/month

**Option 3: Premium Approach**
- Upgrade Birdeye to Starter ($99/mo)
- Add Helius for real-time ($49/mo)
- Total cost: ~$150/month

**Which do you prefer?** I can implement any of these!

---

## 📚 SOURCES

**Apify & Scraping:**
- [DexScreener Token Scraper | Apify](https://apify.com/crypto-scraper/dexscreener-tokens-scraper)
- [Apify Pricing](https://apify.com/pricing)
- [GitHub: nicHamsa/dexscreener-parser](https://github.com/nicHamsa/dexscreener-parser)
- [GitHub: vincentkoc/dexscraper](https://github.com/vincentkoc/dexscraper)
- [GitHub: doffn/Dexscreen-scraper](https://github.com/doffn/Dexscreen-scraper)

**APIs & Platforms:**
- [Helius - Solana's Leading RPC](https://www.helius.dev)
- [Helius Pricing](https://www.helius.dev/pricing)
- [Shyft - Solana APIs](https://shyft.to/)
- [GeckoTerminal](https://www.geckoterminal.com)
- [GMGN.AI](https://gmgn.ai)

**Social & Signals:**
- [GitHub: Solana-Twitter-Bot](https://github.com/solanabots/Solana-Twitter-Bot)
- [21 Best Crypto Trading Signal Providers](https://nftplazas.com/best-crypto-signals/)
- [Top 5 Telegram Trading Bots | CoinGecko](https://www.coingecko.com/learn/top-telegram-trading-bots)
- [130+ Best Crypto Telegram Channels](https://coingape.com/best-telegram-crypto-channels-list/)

**Comparisons:**
- [Best DEX Screener Alternatives](https://solanabox.tools/alternatives/dex-screener)
- [Birdeye vs Other Analytics Tools](https://magicsquare.io/blog/birdeyeso-vs-other-crypto-analytics-tools)
- [Helius vs Shyft vs QuickNode](https://coincodecap.com/solana-grpc-helius-vs-bitquery-vs-quicknode-vs-shyft-which-one-should-you-choose)

---

**Status:** Research complete! Ready to implement based on your decision. 🚀
