# Feature Flags Guide - Test Bot Features One by One

## ✅ Overview

All new features now have **on/off switches** via `.env` flags. This allows you to:
- Test each feature individually
- Compare performance with/without features
- Keep golden working strategy as baseline
- Disable features that cause issues

---

## 🎯 Feature Flags Available

### 1. Token Discovery Sources

```bash
# Jupiter API (proven working - v1.0-batch6-breakthrough baseline)
ENABLE_JUPITER=true          # DEFAULT: true (keep golden working)

# DexScreener boosted tokens (better data quality)
ENABLE_DEXSCREENER=false     # DEFAULT: false (test when ready)

# Birdeye Solana-native trending + new listings
ENABLE_BIRDEYE=false         # DEFAULT: false (test when ready)
```

**How It Works:**
- `true` = All 3 sources work TOGETHER (combined + deduplicated)
- Bot shows in logs: `🔧 Token sources: Jupiter=True, DexScreener=False, Birdeye=False`
- Start with Jupiter only (proven), then add others one by one

---

### 2. Age-Based Profit Strategies

```bash
# Four profit profiles based on token age:
# - New tokens (0-6h): Aggressive 15% trailing stop
# - Established (6h-3d): Balanced 15% trailing
# - Mature (3-7d): Conservative 8% trailing  
# - Stable (7+d): Very tight 5% trailing
ENABLE_AGE_BASED_STRATEGIES=false  # DEFAULT: false (uses golden settings)
```

**How It Works:**
- `false` = Uses golden settings from .env (10% trailing stop for all)
- `true` = Selects strategy based on token age (4 profiles)
- Bot shows: `✅ Age-based profit strategies ENABLED` or `🔒 DISABLED - using golden settings`

---

### 3. RugCheck API (Rug Detection)

```bash
# Scans tokens for rug pull risks before entry
# Checks: mint authority, liquidity locks, top holders, etc.
ENABLE_RUGCHECK_API=false    # DEFAULT: false
```

**How It Works:**
- `false` = Skips RugCheck entirely (faster, less API calls)
- `true` = Checks every token before buying
- Bot shows: `✅ RugCheck API ENABLED` or `🔒 DISABLED`
- Blocks tokens with critical/high risk if enabled

---

### 4. Whale Tracking

```bash
# Analyzes whale concentration and top holder risks
# Warns if top 10 holders own >70% supply
ENABLE_WHALE_TRACKING=false  # DEFAULT: false
```

**How It Works:**
- `false` = Skips whale analysis (faster)
- `true` = Checks whale concentration via Solscan
- Bot shows: `✅ Whale tracking ENABLED` or `🔒 DISABLED`
- Logs warnings if whales detected

---

### 5. Movement Detection

```bash
# Detects unusual trading patterns (pump/dump signals)
# Monitors: volume spikes, sell walls, liquidity drains
ENABLE_MOVEMENT_DETECTION=false  # DEFAULT: false
```

**How It Works:**
- `false` = Skips movement analysis
- `true` = Analyzes trading patterns for rug signals
- Bot shows: `✅ Movement detection ENABLED` or `🔒 DISABLED`
- Blocks tokens with critical rug signals

---

### 6. Twitter Sentiment

```bash
# Analyzes Twitter mentions and sentiment for tokens
# Checks: tweet volume, sentiment, coordinated activity
ENABLE_TWITTER_SENTIMENT=false  # DEFAULT: false
```

**How It Works:**
- `false` = Uses neutral sentiment scores (0.5)
- `true` = Fetches real Twitter data
- Bot shows: `✅ Twitter sentiment analysis ENABLED` or `🔒 DISABLED`
- When disabled, confidence still calculated with neutral defaults

---

### 7. Volume Analyzer

```bash
# Detects smart money accumulation via volume breakouts
# Analyzes: volume spikes, liquidity ratios, accumulation patterns
ENABLE_VOLUME_ANALYZER=false  # DEFAULT: false
```

**How It Works:**
- `false` = Skips volume breakout detection
- `true` = Analyzes volume for smart money signals
- Bot shows: `✅ Volume analyzer ENABLED` or `🔒 DISABLED`
- Logs smart money scores when enabled

---

## 📊 Testing Strategy

### Phase 1: Baseline (Golden Settings)
```bash
# Test with proven working settings ONLY
ENABLE_JUPITER=true
ENABLE_DEXSCREENER=false
ENABLE_BIRDEYE=false
ENABLE_AGE_BASED_STRATEGIES=false
ENABLE_RUGCHECK_API=false
ENABLE_WHALE_TRACKING=false
ENABLE_MOVEMENT_DETECTION=false
ENABLE_TWITTER_SENTIMENT=false
ENABLE_VOLUME_ANALYZER=false
```

**Expected:** Bot works like v1.0-batch6-breakthrough (60% win rate baseline)

---

### Phase 2: Add Token Sources (One at a Time)

**Test 2A: Add DexScreener**
```bash
ENABLE_JUPITER=true
ENABLE_DEXSCREENER=true  # NEW
# ... rest false
```

**Expected:** More tokens discovered, still quality trades

**Test 2B: Add Birdeye** (after DexScreener confirmed)
```bash
ENABLE_JUPITER=true
ENABLE_DEXSCREENER=true
ENABLE_BIRDEYE=true  # NEW
# ... rest false
```

**Expected:** Maximum token discovery, combined quality

---

### Phase 3: Add Protection Features (One at a Time)

**Test 3A: Add RugCheck**
```bash
# Keep sources enabled
ENABLE_RUGCHECK_API=true  # NEW
# ... rest false
```

**Expected:** Blocks high-risk tokens, slightly fewer trades but safer

**Test 3B: Add Whale Tracking**
```bash
ENABLE_RUGCHECK_API=true
ENABLE_WHALE_TRACKING=true  # NEW
# ... rest false
```

**Expected:** Warns about whale concentration, blocks dangerous distributions

**Test 3C: Add Movement Detection**
```bash
ENABLE_RUGCHECK_API=true
ENABLE_WHALE_TRACKING=true
ENABLE_MOVEMENT_DETECTION=true  # NEW
# ... rest false
```

**Expected:** Blocks pump/dump patterns, exit before rugs

---

### Phase 4: Add Smart Features (One at a Time)

**Test 4A: Add Volume Analyzer**
```bash
# Keep protection features
ENABLE_VOLUME_ANALYZER=true  # NEW
# ... sentiment/age still false
```

**Expected:** Prioritizes tokens with smart money accumulation

**Test 4B: Add Age-Based Strategies**
```bash
ENABLE_VOLUME_ANALYZER=true
ENABLE_AGE_BASED_STRATEGIES=true  # NEW
# ... sentiment still false
```

**Expected:** Different trailing stops based on token age

**Test 4C: Add Twitter Sentiment** (optional - rate limited)
```bash
ENABLE_VOLUME_ANALYZER=true
ENABLE_AGE_BASED_STRATEGIES=true
ENABLE_TWITTER_SENTIMENT=true  # NEW
```

**Expected:** Better confidence scoring with social data

---

## 🔍 Monitoring Flags in Logs

### Startup Logs
```
✅ Age-based profit strategies ENABLED
🔒 RugCheck API DISABLED
🔒 Whale tracking DISABLED
🔒 Movement detection DISABLED
✅ Volume analyzer ENABLED
🔒 Twitter sentiment DISABLED
```

### Token Scanning
```
🔍 Starting token scan...
  🔧 Token sources: Jupiter=True, DexScreener=True, Birdeye=False
  📡 Fetching tokens from Jupiter (proven working)...
  ✅ Jupiter: Found 50 tokens
  📡 Fetching tokens from DexScreener...
  ✅ DexScreener: Found 20 boosted tokens
  ✅ Combined: 65 unique tokens from 2 sources
```

### Token Analysis
```
Analyzing token: DezXAZ8...
RugCheck API disabled - skipping risk assessment
Whale tracking disabled - skipping analysis
Movement detection disabled - skipping patterns
Twitter sentiment disabled - using neutral scores
📊 Using golden settings (age-based strategies disabled)
```

---

## ⚠️ Important Notes

### Default = Safe
- All new features default to `false` (disabled)
- Only Jupiter enabled by default (proven working)
- Must explicitly enable each feature to test

### API Rate Limits
- Twitter: 180 requests/15 min (enable carefully)
- RugCheck: No hard limit but can be slow
- Whale/Movement: Solscan 100 requests/min

### Performance Impact
- More features = slower scanning
- RugCheck adds ~500ms per token
- Whale tracking adds ~300ms per token
- Movement adds ~400ms per token
- Twitter adds ~1-2s per token

### Fallback Behavior
- If feature enabled but API fails → Uses neutral defaults
- Bot continues trading, just without that feature
- Errors logged but don't stop bot

---

## 🚨 Troubleshooting

**Problem:** Feature shows ENABLED but not working
**Solution:** Check API keys in .env, verify no errors in logs

**Problem:** Bot not finding any tokens
**Solution:** Verify `ENABLE_JUPITER=true` (must have at least one source)

**Problem:** All features enabled, bot very slow
**Solution:** Disable optional features, test one at a time

**Problem:** Bot rejecting all tokens
**Solution:** Check if RugCheck strict mode blocking too much, disable features to test

---

## 📝 .env Template

Add these to your `.env` file:

```bash
# === TOKEN DISCOVERY SOURCES (Test One at a Time) ===
ENABLE_JUPITER=true              # Proven working (keep true)
ENABLE_DEXSCREENER=false         # Better data (test when ready)
ENABLE_BIRDEYE=false             # Solana-native (test when ready)

# === ADVANCED FEATURES (Test One at a Time) ===
ENABLE_AGE_BASED_STRATEGIES=false  # 4 profit profiles by age
ENABLE_RUGCHECK_API=false          # Rug detection scanning
ENABLE_WHALE_TRACKING=false        # Whale concentration analysis
ENABLE_MOVEMENT_DETECTION=false    # Pump/dump pattern detection
ENABLE_TWITTER_SENTIMENT=false     # Social sentiment analysis
ENABLE_VOLUME_ANALYZER=false       # Smart money detection
```

---

## ✅ Summary

**Golden Rule:** Start with all features `false` except `ENABLE_JUPITER=true`

**Test Order:**
1. Baseline (Jupiter only)
2. Add sources (DexScreener, Birdeye)
3. Add protection (RugCheck, Whale, Movement)
4. Add intelligence (Volume, Age strategies, Twitter)

**Monitor:** Watch logs for enabled/disabled messages, compare performance with/without each feature

**Goal:** Find best combination that maximizes win rate without breaking golden strategy
