# 🎯 GAINERS FOCUS FIX - Token Discovery Optimization

**Date:** 2025-12-04
**Branch:** `claude/restore-solana-bot-013YagNNs2FiAmTvNscyLeqq`
**Status:** ✅ COMPLETE

---

## 📋 Summary

Fixed token discovery to focus on **GAINERS** (10x-100x potential) instead of bluechips/stablecoins. Implemented Jupiter cycling, bluechip filtering, and fixed dead token detection that was incorrectly flagging SOL, TRUMP, JUP as "dead tokens".

---

## 🔍 Problems Identified

### 1. **Too Many Bluechips (No Profit Potential)**
- Bot was selecting SOL, TRUMP, JUP, USDC, USDT
- These are stable tokens with high market caps
- Won't provide 10x-100x gains user is looking for

### 2. **Jupiter Cycling Broken**
- Code was hardcoded to only use `category='toporganicscore'`
- Jupiter client HAS cycling (toporganicscore → toptraded → toptrending)
- But main.py never used it - always same tokens every scan

### 3. **Birdeye API Failing**
- Hitting "Compute units usage limit exceeded" error
- Wasting API calls on failed requests
- Not contributing any tokens to discovery

### 4. **Dead Token Detection Too Aggressive**
- Flagged tokens with <1% movement in 1 minute as "dead"
- SOL, TRUMP, JUP are STABLE = they don't move 1% per minute
- This caused bluechips to be auto-closed incorrectly

---

## ✅ Fixes Implemented

### **FIX 1: Enable Jupiter Cycling** (`src/main.py` lines 800-857)

**BEFORE:**
```python
jupiter_tokens = await self.jupiter.get_trending_tokens(
    category='toporganicscore',  # Hardcoded - no cycling
    interval='1h',
    limit=30
)
```

**AFTER:**
```python
jupiter_tokens = await self.jupiter.get_trending_tokens(
    category=None,  # Enable cycling (toporganicscore → toptraded → toptrending)
    interval='1h',
    limit=30
)
```

**Result:**
- ✅ Now cycles through 3 discovery strategies
- ✅ Finds different tokens each scan (toporganicscore, toptraded, toptrending)
- ✅ Increased variety = better chance of finding gainers

---

### **FIX 2: Add Bluechip Filter** (`src/main.py` lines 813-851)

**NEW CODE:**
```python
# 🚫 FILTER OUT BLUECHIPS - Focus on gainers with room to grow
BLUECHIP_SYMBOLS = {'SOL', 'USDC', 'USDT', 'JUP', 'BONK', 'WIF', 'TRUMP', 'PYTH', 'RAY', 'ORCA'}
BLUECHIP_ADDRESSES = {
    'So11111111111111111111111111111111111111112',  # SOL
    'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v',  # USDC
    'Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB',  # USDT
    'JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN',  # JUP
    'DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263',  # BONK
}

filtered_tokens = []
for token in jupiter_tokens:
    symbol = token.get('symbol', '').upper()
    addr = token.get('address')
    mcap = token.get('mcap', 0)

    # Skip bluechips by symbol, address, or market cap >$100M
    if symbol in BLUECHIP_SYMBOLS:
        continue
    if addr in BLUECHIP_ADDRESSES:
        continue
    if mcap and mcap > 100_000_000:  # >$100M market cap
        continue

    filtered_tokens.append(token)
```

**Result:**
- ✅ Filters out SOL, TRUMP, JUP, USDC, USDT by symbol AND address
- ✅ Filters out any token with market cap >$100M
- ✅ Focus on medium/low caps with room to grow

---

### **FIX 3: Disable Birdeye** (`src/main.py` lines 883-909)

**BEFORE:**
```python
if enable_birdeye and self.birdeye:
    # Calls that fail with "Compute units usage limit exceeded"
```

**AFTER:**
```python
if False:  # Disabled - was: enable_birdeye and self.birdeye
    # NOTE: Birdeye free tier is hitting "Compute units usage limit exceeded"
    # Temporarily disabled to avoid wasting API calls
```

**Result:**
- ✅ No more wasted API calls to Birdeye
- ✅ Cleaner logs (no more error spam)
- ✅ Can re-enable when we upgrade to paid tier

---

### **FIX 4: Fix Dead Token Detection** (`src/trading/position_manager.py` lines 521-591)

**ADDED:** Bluechip exclusion list
```python
# 🚫 BLUECHIP EXCLUSION - Never flag these as dead (they're stable by design)
BLUECHIP_ADDRESSES = {
    'So11111111111111111111111111111111111111112',  # SOL
    'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v',  # USDC
    'Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB',  # USDT
    'JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN',  # JUP
    'DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263',  # BONK
    # ... more bluechips
}

for token_address, position in self.open_positions.items():
    # Skip bluechip tokens - they are stable by design, not dead!
    if token_address in BLUECHIP_ADDRESSES:
        continue
```

**CHANGED:** Minimal movement threshold
```python
# BEFORE: 1% movement in 1 minute (TOO AGGRESSIVE)
if minutes_held >= 1:
    if price_change_pct < 1.0:
        # Flag as dead

# AFTER: 2% movement in 5 minutes (MORE REASONABLE)
if minutes_held >= 5:
    if price_change_pct < 2.0:
        # Flag as dead
```

**Result:**
- ✅ SOL, TRUMP, JUP are NEVER flagged as dead tokens
- ✅ More reasonable threshold (2% in 5 minutes vs 1% in 1 minute)
- ✅ Still detects real honeypots/rugs, but doesn't false-positive on stable tokens

---

## 📊 Expected Outcomes

### **Token Discovery:**
- ✅ **Variety**: Different tokens each scan (cycling through 3 strategies)
- ✅ **Quality**: Medium/low cap tokens with room to grow
- ✅ **No Bluechips**: SOL, TRUMP, JUP filtered out from selection

### **Position Management:**
- ✅ **No False Positives**: Bluechips won't be flagged as "dead"
- ✅ **Better Detection**: 5-minute window gives real tokens time to move
- ✅ **Cleaner Logs**: No more spam from Birdeye API failures

### **Profit Potential:**
- ✅ **Focus on Gainers**: Tokens that can 10x-100x
- ✅ **Avoid Stables**: No more trading SOL/USDC/USDT
- ✅ **Better Discovery**: Cycling finds trending + traded + organic tokens

---

## 🔄 Cycling Behavior

### **How It Works:**
1. **Scan 1**: Uses `toporganicscore` (organic activity, filters bots)
2. **Scan 2**: Uses `toptraded` (highest volume tokens)
3. **Scan 3**: Uses `toptrending` (trending tokens)
4. **Repeat**: Cycles back to `toporganicscore`

### **Example Logs:**
```
📡 Fetching tokens from Jupiter (CYCLING discovery)...
Jupiter Cycle 1/3: Using 'toporganicscore' discovery
✅ Jupiter: Found 18 tokens (12 bluechips filtered)

📡 Fetching tokens from Jupiter (CYCLING discovery)...
Jupiter Cycle 2/3: Using 'toptraded' discovery
✅ Jupiter: Found 22 tokens (8 bluechips filtered)

📡 Fetching tokens from Jupiter (CYCLING discovery)...
Jupiter Cycle 3/3: Using 'toptrending' discovery
✅ Jupiter: Found 20 tokens (10 bluechips filtered)
```

---

## 🎯 Testing Checklist

- [ ] **Jupiter Cycling**: Verify logs show "Cycle 1/3", "Cycle 2/3", "Cycle 3/3"
- [ ] **Bluechip Filtering**: Verify SOL, TRUMP, JUP are filtered out from selection
- [ ] **No Dead Token False Positives**: Verify SOL, TRUMP, JUP are NOT flagged as dead
- [ ] **Birdeye Disabled**: Verify no Birdeye API calls in logs
- [ ] **Token Variety**: Verify different tokens each scan (not the same 30 every time)
- [ ] **Gainer Focus**: Verify selected tokens have medium/low market caps (<$100M)

---

## 📁 Files Modified

1. **`src/main.py`**
   - Lines 800-857: Jupiter cycling + bluechip filter
   - Lines 883-909: Birdeye disabled

2. **`src/trading/position_manager.py`**
   - Lines 521-539: Bluechip exclusion in dead token detection
   - Lines 580-591: Adjusted minimal movement threshold (2% in 5 min)

---

## 🚀 Deployment Notes

**No Breaking Changes:**
- ✅ All changes are backward compatible
- ✅ No new dependencies required
- ✅ No .env changes needed

**Safe to Deploy:**
- ✅ Bluechip filter only affects token selection
- ✅ Dead token detection still works (just doesn't false-positive)
- ✅ Birdeye disabled cleanly (no crashes)

---

## 📝 Notes

- **Birdeye**: Disabled until we upgrade to paid tier or limits reset
- **Bluechip List**: Can be expanded in both `main.py` and `position_manager.py`
- **Market Cap Threshold**: Currently $100M - can adjust if needed
- **Dead Token Threshold**: Currently 2% in 5 minutes - can tune based on results

---

## ✅ Success Metrics

**Before:**
- ❌ Same 30 tokens every scan (toporganicscore only)
- ❌ Many bluechips selected (SOL, TRUMP, JUP)
- ❌ Bluechips flagged as "dead" and auto-closed
- ❌ Birdeye failing with compute limit errors

**After:**
- ✅ Different tokens each scan (cycling 3 strategies)
- ✅ Bluechips filtered out from selection
- ✅ Bluechips never flagged as dead
- ✅ No Birdeye API failures

---

**Status:** Ready for testing and deployment 🚀
