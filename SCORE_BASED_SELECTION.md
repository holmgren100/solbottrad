# 🎯 Score-Based Token Selection - How It Works

## Problem Solved

**Before:** Bot analyzed tokens in source order and bought immediately:
```
Jupiter tokens → Analyze → Buy immediately (takes slot)
DexScreener tokens → Analyze → Buy if slots left
CoinGecko GAINERS → Analyze → Buy if slots left (often no slots!)
```

**Issue:** If Jupiter found 5 okay tokens, CoinGecko's +50% gainer never got considered!

---

## New Solution: Two-Phase Selection

### Phase 1: Analyze and Score ALL Tokens
```python
# Analyze all 47 tokens first
for token in all_tokens:
    analysis = analyze_token(token)
    if good:
        score = calculate_score(token)
        opportunities.append({token, score})
```

### Phase 2: Buy BEST Opportunities
```python
# Sort by score (highest first)
opportunities.sort(by='score', descending=True)

# Buy top 5 (regardless of source)
for i in range(5):
    buy(opportunities[i])
```

**Result:** CoinGecko's +50% gainer with 80 score beats Jupiter's +5% token with 55 score!

---

## Scoring System (0-100 scale)

### Factor 1: Price Change (Up to +30 points) - HIGHEST PRIORITY
```
+10% gain  → +5 points
+50% gain  → +25 points
+100% gain → +30 points (max)
```

**Why Important:** CoinGecko and Apify provide sorted GAINERS with actual price changes. Jupiter tokens don't have this data, so CoinGecko's gainers automatically get 20-30 bonus points!

### Factor 2: Liquidity (Up to +10 points)
```
>$100k liquidity → +10 points
>$50k liquidity  → +5 points
>$30k liquidity  → +2 points
<$30k liquidity  → -5 points (penalty)
```

**Why Important:** Need liquidity to exit without slippage.

### Factor 3: Volume (Up to +8 points)
```
>$500k volume → +8 points
>$100k volume → +5 points
>$50k volume  → +2 points
```

**Why Important:** High volume = active trading = easier exits.

### Factor 4: Source Quality (Up to +10 points)
```
Apify      → +10 points (BEST - sorted DexScreener data)
CoinGecko  → +8 points  (sorted top gainers)
Birdeye    → +6 points  (GAINERS focus)
DexScreener→ +3 points  (organic, not sorted)
Jupiter    → +2 points  (reliable, not GAINERS-focused)
```

**Why Important:** Sources that provide sorted GAINERS data get higher scores.

### Factor 5: Market Cap (Up to +12 points)
```
<$500k mcap  → +12 points (micro-cap moonshot)
$500k-$1M    → +8 points
$1M-$5M      → +5 points
$5M-$10M     → +2 points
>$10M        → 0 points (harder to 10x)
```

**Why Important:** Lower market cap = more room to grow.

### Factor 6: Market Cap Rank (Up to +5 points)
```
Rank >500 (unranked/low cap) → +5 points
Rank >200                     → +3 points
Rank <200 (established)       → 0 points
```

**Why Important:** Lower rank = more speculative = more moonshot potential.

### Factor 7: Volume/Liquidity Ratio (Up to +8 points)
```
Ratio 0.5-3.0 (healthy)   → +5 points
Ratio >3.0 (high momentum)→ +8 points
```

**Why Important:** High volume relative to liquidity = strong momentum.

---

## Example Scores

### CoinGecko Gainer (High Score)
```
Token: PUMP
Source: CoinGecko
Price Change 24h: +85%
Liquidity: $120k
Volume: $600k
Market Cap: $800k

SCORE BREAKDOWN:
Base score:           50
Price change +85%:   +30 (max)
Liquidity >100k:     +10
Volume >500k:        +8
Source (CoinGecko):  +8
Market cap $800k:    +8
Rank >500:           +5
Vol/liq ratio 5.0:   +8
------------------------
TOTAL SCORE:         100 (PERFECT!)
```

### Jupiter Token (Medium Score)
```
Token: RANDOM
Source: Jupiter
Price Change 24h: N/A (not available)
Liquidity: $80k
Volume: $120k
Market Cap: $15M

SCORE BREAKDOWN:
Base score:           50
Price change:         +0 (no data)
Liquidity >50k:       +5
Volume >100k:         +5
Source (Jupiter):     +2
Market cap >10M:      +0
Rank unknown:         +0
Vol/liq ratio 1.5:    +5
------------------------
TOTAL SCORE:          67
```

**Result:** CoinGecko PUMP (score 100) gets bought first, Jupiter RANDOM (score 67) waits for next slot!

---

## What You'll See in Logs

### Old Logs (Before Fix)
```
🔍 Starting token scan...
✅ Jupiter: Found 18 tokens
✅ DexScreener: Found 25 tokens
✅ CoinGecko: Found 10 GAINERS
✅ Combined: 47 unique tokens

→ Analyzing token 1 (Jupiter)... ✅ Buying!
→ Analyzing token 2 (Jupiter)... ✅ Buying!
→ Analyzing token 3 (Jupiter)... ✅ Buying!
→ Analyzing token 4 (Jupiter)... ✅ Buying!
→ Analyzing token 5 (Jupiter)... ✅ Buying!
⏭️  No slots left (CoinGecko gainers never considered!)
```

### New Logs (After Fix)
```
🔍 Starting token scan...
✅ Jupiter: Found 18 tokens
✅ DexScreener: Found 25 tokens
✅ CoinGecko: Found 10 GAINERS
✅ Combined: 47 unique tokens

📊 PHASE 1: Analyzing all 47 tokens...
→ Analyzing token 1... ✅ Opportunity found (score: 67.2)
→ Analyzing token 2... ✅ Opportunity found (score: 89.5)
→ Analyzing token 3... ✅ Opportunity found (score: 55.4)
...
→ Analyzing token 47... ✅ Opportunity found (score: 72.1)

🎯 Found 15 opportunities, buying best ones...
🎯 #1 BEST OPPORTUNITY (score 89.5): PUMP from coingecko ✨
🎯 #2 BEST OPPORTUNITY (score 78.3): MOON from coingecko ✨
🎯 #3 BEST OPPORTUNITY (score 72.1): GAIN from dexscreener
🎯 #4 BEST OPPORTUNITY (score 67.2): TOKEN from jupiter
🎯 #5 BEST OPPORTUNITY (score 65.8): COIN from jupiter
⏭️  Skipped 10 lower-scored opportunities (no slots)
```

**See the difference?** CoinGecko's GAINERS now get priority!

---

## Benefits

1. **GAINERS Get Priority** ✅
   - CoinGecko +50% gainer beats Jupiter +5% token
   - Apify sorted data gets highest scores
   - Best opportunities bought first

2. **Fair Source Evaluation** ✅
   - All 47 tokens analyzed before buying
   - Source doesn't determine order
   - Quality determines order

3. **Data-Driven Selection** ✅
   - Price change data = huge score boost
   - Liquidity/volume metrics considered
   - Market cap for moonshot potential

4. **Better Win Rate Expected** ✅
   - Buying tokens with actual momentum
   - Not just "first 5 tokens found"
   - Higher quality opportunities

---

## Testing Strategy

1. **Watch First Scan Cycle**
   - Check if scores make sense
   - Verify GAINERS get high scores (80-100)
   - Verify random tokens get medium scores (50-70)

2. **Monitor Which Tokens Get Bought**
   - Should see CoinGecko/Apify tokens bought first
   - Should see "score: XX.X" in logs
   - Should see "BEST OPPORTUNITY" messages

3. **Track Performance**
   - Compare win rate before/after
   - Target: 50-60% or higher
   - Should see more profitable trades

---

## Expected Score Ranges

```
90-100: PERFECT opportunities (CoinGecko +50%+ gainers with high liquidity)
80-89:  EXCELLENT opportunities (strong gainers with good metrics)
70-79:  GOOD opportunities (moderate gains or high momentum)
60-69:  DECENT opportunities (some positive factors)
50-59:  MARGINAL opportunities (few positive factors)
<50:    WEAK opportunities (low liquidity or no momentum)
```

**Buy Threshold:** Bot will buy ANY opportunity that passes `make_trading_decision()`, but now buys BEST ones first!

---

## Summary

**What Changed:**
- Added `_calculate_opportunity_score()` method (103 lines)
- Modified scan flow to use two-phase selection
- No changes to entry/exit filters (still safe)

**What Improved:**
- CoinGecko GAINERS now get fair consideration
- Best opportunities bought first (not first found)
- Data-driven selection (price change matters!)

**What Stayed Same:**
- Same 3 sources (Jupiter + DexScreener + CoinGecko)
- Same liquidity/volume filters
- Same stop loss / take profit settings
- Still paper trading mode

🚀 **Now testing to hit batch 5-6 numbers (50-60% win rate)!**
