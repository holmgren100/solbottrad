# Deep Research: API Endpoints & Token Discovery for Quality Data

**Research Date:** December 4, 2025
**Purpose:** Find best API endpoints/categories for discovering tokens with quality data
**Status:** RESEARCH ONLY - NO CHANGES MADE

---

## 🔍 Current Problem

User reports:
- "no buying position, no good data at all"
- "Jupiter fetch tokens but with nearly no data"
- Bot analyzing 100 tokens but not taking any positions
- Data quality appears poor

---

## 📊 Current Implementation (as of commit bf03613)

### Jupiter API
```python
category='toporganicscore'  # Changed from 'toptraded'
interval='1h'
limit=100
```
**Endpoint:** `https://lite-api.jup.ag/tokens/v2/toporganicscore/1h?limit=100`

**Cycling:** Yes (3 cycles)
- Cycle 1: toporganicscore
- Cycle 2: toptraded
- Cycle 3: toptrending

### Birdeye API
```python
sort_by = 'rank'  # Cycles through 5 options
limit=30 (15 trending + 15 new listings)
rate_limit=30/min
```
**Endpoint:** `https://public-api.birdeye.so/defi/token_trending?sort_by=rank`

**Cycling:** Yes (5 cycles)
- Cycle 1: rank
- Cycle 2: liquidity
- Cycle 3: volume24hUSD
- Cycle 4: priceChange24h
- Cycle 5: priceChange1h

### DexScreener API
```python
endpoint='/token-profiles/latest/v1'
limit=30
filtering: boosts.active === 0 (no paid promotions)
```
**Endpoint:** `https://api.dexscreener.com/token-profiles/latest/v1`

**Cycling:** NO (API doesn't support sorting/filtering - only latest profiles)

---

## 📚 Historical Analysis: What Worked Before

### Nov 30, 2025 - "97% Good Trades" Period (Commit 82fc688)

**Working Settings:**
```env
MIN_ENTRY_LIQUIDITY=30000  # $30k minimum
MIN_24H_VOLUME=15000       # $15k minimum
MIN_SENTIMENT_SCORE=0.25
STALE_PRICE_MINUTES=2
```

**Token Source at that time:**
According to commit history and JOURNAL.md:
- Used `toptraded` category for Jupiter
- Fallback to `recent` if trending failed
- DexScreener: boosted tokens endpoint (later changed)
- No Birdeye (added later)

### July 2024 - Data Quality Fix (Commit 5579d90)

**Problem Identified:**
- 90% of tokens had $0 liquidity (from `/recent` endpoint)
- 95% of DexScreener tokens were paid scam promotions
- Birdeye rate limit exceeded constantly

**Solution Implemented:**
```python
# Jupiter: Changed to organic score
category='toporganicscore'  # FROM: '/recent' fallback
interval='1h'
limit=100

# DexScreener: Filter out boosted
get_organic_tokens()  # FROM: get_boosted_tokens()

# Birdeye: Reduce rate limit
calls_per_minute=50  # FROM: 100/min
```

**Results After Fix:**
- 85% tokens with real liquidity (up from 10%)
- 0% paid promotions (down from 95%)
- Birdeye API working (was 100% failing)

---

## 🌐 Web Research Findings

### Jupiter API Official Documentation

**Source:** [Jupiter Developers - Tokens API V2](https://dev.jup.ag/docs/tokens/v2)

**Available Categories:**
1. **toporganicscore** - Filters artificial/bot activity, genuine user participation only
2. **toptraded** - Highest volume tokens (can be manipulated)
3. **toptrending** - Trending tokens (new opportunities)

**Intervals Available:** 5m, 1h, 6h, 24h

**Key Quote from Docs:**
> "The result filters out generic top tokens like SOL, USDC, etc (since those tokens are likely always top of the categories)"

**Endpoint Format:**
```
https://lite-api.jup.ag/tokens/v2/{category}/{interval}?limit={number}
```

**Default Limit:** 50 tokens (can increase/decrease)

### Birdeye API Official Documentation

**Source:** [Birdeye Docs - Trending Tokens](https://docs.birdeye.so/docs/trending-tokens)

**Available sort_by Parameters:**
- `rank` (default) - Trending rank, tokens with major popularity growth
- `liquidity` - Sufficient liquidity for smooth trading
- `volume24hUSD` - Highest trading activity and market interest
- `priceChange24h` - 24h gainers
- `priceChange1h` - 1h gainers

**Newer Token List V3 API Additions:**
- Market Cap, FDV (Fully Diluted Valuation)
- Recent listing time
- Volume change percentage
- Trade count by timeframes (1h, 2h, 4h, 8h, 24h)
- Most Viewed / Most Watched

**Free Tier Limits:**
- 30,000 Compute Units/month
- 1 RPS (60 requests/min theoretical)
- **BUT:** Compute units consumed FASTER than request rate on complex queries

**Best Practices Found:**
- Use `volume24hUSD` for tokens with high trading activity
- Use `liquidity` for tokens with adequate liquidity (smooth trades)
- Use `rank` for discovering trending tokens with popularity growth

### DexScreener API Research

**Source:** [DexScreener API Reference](https://docs.dexscreener.com/api/reference)

**Available Endpoints:**
1. `/token-pairs/v1/{chainId}/{tokenAddress}` - Individual token pairs
2. `/tokens/v1/{chainId}/{tokenAddresses}` - Up to 30 comma-separated addresses
3. `/token-profiles/latest/v1` - Latest token profiles (FREE, no API key)

**CRITICAL FINDING:**
> "There currently isn't a direct API endpoint to fetch trending tokens from DexScreener"

**NO ENDPOINTS FOR:**
- `/dex/pairs/solana` (doesn't exist - returns 404)
- Sorting by price change, volume, transactions
- Filtering by liquidity thresholds

**Scam Warning from Docs:**
> "DEXScreener tracks all on-chain activity including scams, showing tokens with zero liquidity or rug-pull potential, so users should always double-check contract details and liquidity locks before trusting a token."

---

## 🎯 Community & Best Practices (Web Search)

### Solana Bot Token Discovery Best Practices

**Source:** [Bitquery Solana API](https://bitquery.io/blockchains/solana-blockchain-api)

**Recommended Filters:**
```
AmountInUSD gt: "10"         # Minimum trade $10
PriceAsymmetry lt: 0.01      # Price stability <1%
liquidityUsd                 # Filter by liquidity in USD
volume                       # Total trading volume
lpBurn eq: 100               # LP tokens 100% burned
holders                      # Number of token holders
```

### Alternative Data Sources Found

**Solana Tracker API:**
- Searches by symbol, name, or address
- Advanced filtering by liquidity, market cap, volume, age
- Better for discovery than DexScreener API

**Pump.fun Integration:**
- Track newly created liquidity pools
- Monitor token migrations from Pump.fun to Raydium
- Real-time WebSocket connections

---

## 🔬 Analysis: Current vs Historical vs Recommended

### What Changed That May Affect Data Quality

| Aspect | Nov 30 "97% Good" | Current Implementation | Impact |
|--------|-------------------|------------------------|---------|
| **Jupiter Category** | toptraded | toporganicscore (cycling) | Unknown - both should work |
| **Jupiter Limit** | 50 | 100 | More tokens = potentially lower quality? |
| **DexScreener** | Boosted (paid) | Latest profiles (organic) | ✅ Better now |
| **Birdeye** | Not enabled | Enabled (cycling, 30/min) | ✅ Better now |
| **Liquidity Filter** | $30k | $30k | Same |
| **Volume Filter** | $15k | $15k | Same |

### Key Differences Identified

**1. Jupiter Limit: 50 → 100 tokens**
- Nov 30: Fetched 50 tokens
- Current: Fetching 100 tokens
- **Hypothesis:** Jupiter may return top 50 highest quality, then 51-100 lower quality?

**2. Cycling vs Static Categories**
- Nov 30: Always used same category (toptraded)
- Current: Rotates through 3 categories (toporganicscore, toptraded, toptrending)
- **Hypothesis:** Some cycles may return lower quality tokens?

**3. Birdeye Added**
- Nov 30: No Birdeye
- Current: Birdeye cycling through 5 sort methods
- **Hypothesis:** Birdeye may be adding low-quality tokens to the mix?

---

## 🔍 Data Quality Investigation

### From JOURNAL.md - The "/recent" Disaster

**User's Original Problem (Nov 24, 2024):**
```
Retrieved 30 recent tokens from Jupiter
→ Analyzing 8eN451Ka...
WARNING - No market data from either source for 8eN451Ka...
```

**Root Cause:**
> "/ endpoint returns BRAND NEW tokens (literally just created their first pool)
> Too new = DexScreener doesn't have them indexed yet
> Too new = Jupiter search API doesn't return price data yet
> Bot can't analyze tokens without price/liquidity data → skips all of them"

**Solution That Worked (Commit 61e8653):**
```python
# Try trending tokens FIRST (they have market data!)
new_tokens = await self.jupiter.get_trending_tokens(category='toptraded', limit=50)

# Fallback to recent if trending fails
if not new_tokens:
    new_tokens = await self.jupiter.get_recent_tokens(limit=50)
```

### From API_DATA_QUALITY_FIXES.md

**Quality Metrics Before/After Fix:**

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Tokens with liquidity | 10% | 85% | **+750%** |
| Paid promotion exposure | 95% | 0% | **-100%** |
| Birdeye API success | 0% | 95% | **+∞** |

**Key Recommendations from Doc:**
1. ✅ Jupiter: `/toporganicscore/1h` (no more $0 liquidity)
2. ✅ DexScreener: Filter out boosted tokens (no more scams)
3. ✅ Birdeye: Reduce rate limit (no more errors)
4. ❌ AVOID: `/recent` endpoint (90% $0 liquidity)
5. ❌ AVOID: `/token-boosts/top/v1` (95% paid scams)

---

## 💡 Key Findings & Hypotheses

### Finding 1: Cycling May Reduce Quality

**Evidence:**
- Nov 30 "97% good trades" used STATIC category (toptraded)
- Current uses CYCLING (toporganicscore → toptraded → toptrending)
- `toptrending` may include very new tokens with incomplete data

**Hypothesis:**
> Cycling through `toptrending` may fetch newer tokens that don't have complete market data yet, similar to the old `/recent` problem

### Finding 2: Limit Too High?

**Evidence:**
- Nov 30 likely used 50 token limit (standard)
- Current uses 100 token limit
- Jupiter docs default to 50

**Hypothesis:**
> Jupiter may rank tokens by quality. Top 50 = best data, tokens 51-100 = lower quality/newer/less data

### Finding 3: Birdeye Rate Limit Still Issues

**Evidence:**
- User logs still show: "Birdeye trending tokens error 400: Compute units usage limit exceeded"
- Reduced from 50/min to 40/min to 30/min
- Still failing

**Hypothesis:**
> Birdeye free tier may be insufficient for bot's usage pattern. Cycling through 5 different sort methods may consume more compute units than expected.

### Finding 4: DexScreener Limited Value

**Evidence:**
- API only has `/token-profiles/latest/v1` for discovery
- No sorting, filtering, or quality ranking
- Just returns latest profiles
- Web research confirms: "There currently isn't a direct API endpoint to fetch trending tokens"

**Hypothesis:**
> DexScreener is not useful for token DISCOVERY, only good for enriching data on tokens found elsewhere

### Finding 5: Data Completeness Issue

**User said:** "Jupiter fetch tokens but with nearly no data"

**Possible Causes:**
1. Tokens from `toptrending` cycle are too new
2. 100 token limit includes lower-quality tokens (51-100)
3. Cycling hitting APIs too frequently → incomplete responses
4. Birdeye failures reducing overall data quality

---

## 🎯 Recommended Research Actions (NO CHANGES)

### 1. Log Analysis Needed

**Check what data is actually being returned:**
```python
# In token analysis loop, log:
- Which API source provided the token
- Which cycle/category was active
- What data fields are present/missing
- Liquidity and volume values
- Why analysis is being skipped
```

### 2. Category Performance Comparison

**Test each category individually:**
- toporganicscore only (1 day)
- toptraded only (1 day)
- toptrending only (1 day)
- Compare: data completeness, position entries, quality

### 3. Limit Optimization

**Test different limits:**
- 50 tokens (original default)
- 75 tokens (middle ground)
- 100 tokens (current)
- Log which tokens 1-50 vs 51-100 have complete data

### 4. Source Priority Testing

**Disable sources one at a time:**
- Jupiter only
- Jupiter + DexScreener
- Jupiter + Birdeye
- All three
- Compare data quality and position entries

### 5. Birdeye Investigation

**Check Birdeye usage:**
- How many Birdeye calls per scan?
- Which sort_by methods consume most compute units?
- Is cycling worth the compute unit cost?
- Try static `volume24hUSD` instead of cycling?

---

## 📋 Comparison Table: API Endpoints

| Source | Endpoint | Current Use | Data Quality (Research) | Recommendation |
|--------|----------|-------------|------------------------|----------------|
| **Jupiter toporganicscore** | `/toporganicscore/1h` | ✅ Yes (Cycle 1) | 🟢 Excellent - filters bots | Keep, consider as primary |
| **Jupiter toptraded** | `/toptraded/1h` | ✅ Yes (Cycle 2) | 🟡 Good - high volume but manipulatable | Keep for validation |
| **Jupiter toptrending** | `/toptrending/1h` | ✅ Yes (Cycle 3) | 🟠 Risky - may include new tokens | TEST - may have incomplete data |
| **Jupiter recent** | `/recent` | ❌ No | 🔴 Poor - 90% $0 liquidity | AVOID |
| **Birdeye rank** | `/token_trending?sort_by=rank` | ✅ Yes (Cycle 1) | 🟡 Good - trending tokens | TEST compute unit cost |
| **Birdeye liquidity** | `/token_trending?sort_by=liquidity` | ✅ Yes (Cycle 2) | 🟢 Excellent - ensures tradability | Keep if compute units OK |
| **Birdeye volume24hUSD** | `/token_trending?sort_by=volume24hUSD` | ✅ Yes (Cycle 3) | 🟢 Excellent - high activity | Keep if compute units OK |
| **Birdeye priceChange24h** | `/token_trending?sort_by=priceChange24h` | ✅ Yes (Cycle 4) | 🟡 Good - gainers | TEST quality |
| **Birdeye priceChange1h** | `/token_trending?sort_by=priceChange1h` | ✅ Yes (Cycle 5) | 🟠 Risky - volatile new movers | TEST - may be pumps |
| **DexScreener latest** | `/token-profiles/latest/v1` | ✅ Yes | 🟠 Limited - just latest, no ranking | Consider removing |
| **DexScreener boosted** | `/token-boosts/top/v1` | ❌ No | 🔴 Terrible - 95% scams | NEVER use |

---

## 🏆 Best Practice Recommendations (From All Research)

### Tier 1: High Quality, Complete Data
1. **Jupiter toporganicscore/1h** - Filters bots, genuine trading
2. **Birdeye volume24hUSD** - High activity, proven liquidity
3. **Birdeye liquidity** - Ensures smooth trading

### Tier 2: Good Quality, Some Risk
4. **Jupiter toptraded/1h** - High volume (watch for manipulation)
5. **Birdeye rank** - Trending but validate liquidity
6. **Birdeye priceChange24h** - Sustained gainers

### Tier 3: Risky, May Have Incomplete Data
7. **Jupiter toptrending/1h** - New opportunities but may be too new
8. **Birdeye priceChange1h** - Fast movers but often pumps
9. **DexScreener latest** - Just latest profiles, no quality filter

### Tier 4: AVOID
10. **Jupiter recent** - 90% garbage, no market data
11. **DexScreener boosted** - 95% paid scam promotions

---

## 🔧 Potential Issues with Current Implementation

### Issue 1: Too Many Cycles = Diluted Quality

**Current:** 8 different discovery methods rotating
- 3 Jupiter cycles
- 5 Birdeye cycles
- 1 DexScreener (static)

**Problem:** Some cycles (toptrending, priceChange1h) may fetch lower-quality tokens

**Historical:** Nov 30 "97% good trades" used simpler approach with fewer cycles

### Issue 2: 100 Token Limit May Be Too High

**Current:** Fetching 100 tokens from Jupiter

**Jupiter Docs Default:** 50 tokens

**Problem:** Tokens 51-100 may be lower quality than top 50

### Issue 3: Birdeye Free Tier Limits

**Current:** 30 requests/min with 5 cycling sort methods

**Problem:** Still hitting compute unit limits despite low request rate

**Free Tier:** 30,000 compute units/month (may already be exhausted)

### Issue 4: DexScreener Adds Little Value

**Current:** Fetching latest profiles from DexScreener

**Problem:**
- No quality ranking
- Just "latest" = could be anything
- API can't sort/filter
- May be adding noise

---

## 📝 Specific Endpoint Recommendations

### For Maximum Data Quality (Conservative)

**Primary Source:**
```python
# Jupiter: ONLY toporganicscore (no cycling)
jupiter.get_trending_tokens(
    category='toporganicscore',
    interval='1h',
    limit=50  # Reduce from 100
)
```

**Secondary Validation:**
```python
# Birdeye: ONLY volume24hUSD (no cycling)
birdeye.get_trending_tokens(
    sort_by='volume24hUSD',
    limit=20
)
```

**Skip:** DexScreener (limited value for discovery)

### For Balanced Quality & Diversity

**Primary Source:**
```python
# Jupiter: Cycle ONLY between best 2 categories
categories = ['toporganicscore', 'toptraded']  # Remove toptrending
limit=75  # Middle ground between 50-100
```

**Secondary Source:**
```python
# Birdeye: Cycle between best 3
sort_methods = ['volume24hUSD', 'liquidity', 'rank']  # Remove priceChange
limit=15
```

**Tertiary:** DexScreener for enrichment only (not discovery)

### For Aggressive Discovery (Current)

Keep current implementation but:
- Monitor which cycles produce quality positions
- Track success rate by source/category
- Reduce limit from 100 to 75 on Jupiter

---

## 🎓 Learning from Git History

### Commits That Improved Quality

**5579d90** - "FIX: Critical data quality issues"
- Changed from `/recent` → `/toporganicscore`
- Results: 10% → 85% tokens with liquidity

**82fc688** - "Restore EXACT Nov 30 working settings (97% good trades)"
- MIN_ENTRY_LIQUIDITY=30000
- MIN_24H_VOLUME=15000
- Used simpler token discovery (likely toptraded, no cycling)

**dec89f3** - "Combine all token sources instead of cascading fallback"
- Switched from fallback chain to parallel fetching
- May have introduced lower-quality tokens?

### Commits That May Have Reduced Quality

**9719548** - "Add cycling discovery strategies for all data sources"
- Added toptrending cycle (may include incomplete data tokens)
- Added 5 Birdeye cycles (some risky like priceChange1h)
- Increased complexity without proven benefit

---

## 🌐 Sources & References

### Official Documentation
- [Jupiter Tokens API V2 (Beta)](https://dev.jup.ag/docs/tokens/v2) - Official Jupiter API docs
- [Birdeye Trending Tokens](https://docs.birdeye.so/docs/trending-tokens) - Official Birdeye docs
- [DexScreener API Reference](https://docs.dexscreener.com/api/reference) - Official DexScreener docs

### Community Resources
- [Bitquery Solana API](https://bitquery.io/blockchains/solana-blockchain-api) - Advanced filtering best practices
- [Solana Stack Exchange](https://solana.stackexchange.com/questions/13812/) - Community discussion on DexScreener/Birdeye APIs
- [Birdeye Token List V3 API](https://medium.com/@birdeye-data/new-api-token-list-v3-api-2bf5f24b8e75) - New sorting options

### Internal Documentation
- `JOURNAL.md` - Historical context on API changes
- `API_DATA_QUALITY_FIXES.md` - Previous quality improvements
- `DEEP_ANALYSIS_FINDINGS.md` - Demo vs Live analysis

---

## 🎯 Next Steps for User

### Immediate Investigation (NO CODE CHANGES)

1. **Check Current Logs:**
   - Which Jupiter cycle is currently active?
   - How many tokens are being analyzed?
   - How many have complete data (price, liquidity, volume)?
   - Which tokens are being skipped and why?

2. **Monitor By Source:**
   - Track which source provides tokens that become positions
   - Track which cycles/categories produce best quality
   - Identify if any source is adding only garbage

3. **Compare to Historical:**
   - What was working on Nov 30?
   - What changed since then?
   - Can we identify the specific change that reduced quality?

### Testing Recommendations

**Test 1: Reduce Complexity**
- Disable cycling, use static toporganicscore only
- Reduce Jupiter limit from 100 → 50
- Run for 6 hours, compare quality

**Test 2: Remove Risky Cycles**
- Keep toporganicscore and toptraded only
- Remove toptrending from Jupiter
- Remove priceChange1h and priceChange24h from Birdeye
- Run for 6 hours, compare quality

**Test 3: Disable Sources One by One**
- Run with Jupiter only (no DexScreener/Birdeye)
- Run with Jupiter + Birdeye (no DexScreener)
- Compare data quality and position entries

**Test 4: API Response Analysis**
- Add detailed logging of API responses
- Check what data fields are present/missing
- Identify which endpoints return incomplete data

---

## ⚠️ Critical Questions to Answer

1. **Is toptrending causing the "no data" issue?**
   - Does it return tokens too new to have market data?
   - Compare to toporganicscore data completeness

2. **Is 100 token limit too high?**
   - Are tokens 51-100 lower quality?
   - Would 50 token limit improve quality?

3. **Is Birdeye adding value or noise?**
   - Does Birdeye provide tokens that become positions?
   - Is it worth the compute unit cost?
   - Would static volume24hUSD be better than cycling?

4. **Is DexScreener discovery useful?**
   - Does it find tokens Jupiter/Birdeye miss?
   - Or is it just adding random latest profiles?
   - Would it be better for enrichment only?

5. **What actually changed since Nov 30?**
   - Nov 30 had "97% good trades"
   - Current has "no good data"
   - What specific code/config change caused this?

---

## 📊 Summary Matrix

### Current State
- Jupiter: toporganicscore/toptraded/toptrending cycling, 100 tokens
- Birdeye: 5-method cycling, 30 tokens, hitting compute limits
- DexScreener: Latest profiles, 30 tokens, no quality filter
- **Result:** "No good data", no positions being taken

### Historical Working State (Nov 30)
- Jupiter: toptraded (likely), 50 tokens, simpler approach
- Birdeye: Not enabled
- DexScreener: Likely simpler approach
- **Result:** "97% good trades", positions being taken

### Recommended Test State
- Jupiter: toporganicscore ONLY, 50 tokens, no cycling
- Birdeye: volume24hUSD ONLY, 20 tokens, no cycling (or disable)
- DexScreener: Disable for discovery, use for enrichment only
- **Expected:** Better data quality, more positions

---

## 🏁 Conclusion

**Main Hypothesis:**
The cycling strategy implementation, while theoretically providing diversity, may have **reduced data quality** by:
1. Including riskier categories (toptrending, priceChange1h)
2. Fetching too many tokens (100 vs 50)
3. Adding Birdeye tokens that may not be ready
4. Adding DexScreener latest profiles with no quality filter

**Historical Evidence:**
- Nov 30 "97% good trades" used simpler approach
- After cycling added, user reports "no good data"
- Previous data quality fixes showed simpler = better

**Recommendation:**
Test with simpler, more conservative approach:
- Single best category per source
- Lower token limits
- Focus on proven quality endpoints
- Monitor what actually produces positions

**Critical Next Step:**
ADD DETAILED LOGGING to understand:
- What data is actually being returned
- Which tokens have complete data vs incomplete
- Which sources/cycles produce positions
- Why tokens are being skipped

---

**NO CHANGES MADE - THIS IS RESEARCH ONLY**

All findings compiled from:
- Official API documentation
- Web research and community forums
- Internal git history and documentation
- Historical commit analysis
