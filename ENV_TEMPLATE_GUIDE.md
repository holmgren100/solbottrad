# Complete .env Template - All Settings + Feature Flags

## ✅ What This Is

A **COMPLETE** `.env` template with:
- ✅ All Nov 30 working settings (proven 97% good trades)
- ✅ All new feature flags (9 on/off switches)
- ✅ All API keys organized by category
- ✅ All hardcoded defaults documented
- ✅ Clear comments explaining each setting

---

## 🎯 How to Use

### Step 1: Copy Template to .env

```bash
# Backup your current .env first!
cp .env .env.backup.$(date +%Y%m%d_%H%M%S)

# Use template as reference
cat .env.template
```

### Step 2: Set Feature Flags (Start Safe!)

**Golden Baseline (Start Here):**
```bash
ENABLE_JUPITER=true              # ✅ Keep true
ENABLE_DEXSCREENER=false         # ⏸️ Test later
ENABLE_BIRDEYE=false             # ⏸️ Test later
ENABLE_AGE_BASED_STRATEGIES=false    # ⏸️ Test later
ENABLE_VOLUME_ANALYZER=false         # ⏸️ Test later
ENABLE_RUGCHECK_API=false            # ⏸️ Test later
ENABLE_WHALE_TRACKING=false          # ⏸️ Test later
ENABLE_MOVEMENT_DETECTION=false      # ⏸️ Test later
ENABLE_TWITTER_SENTIMENT=false       # ⏸️ Test later
```

### Step 3: Fill In Your API Keys

Replace `YOUR_KEY_HERE` with actual keys:
- ✅ ALCHEMY_API_KEY (required)
- ✅ BIRDEYE_API_KEY (if using Birdeye)
- ✅ TELEGRAM_BOT_TOKEN (for notifications)
- ✅ TELEGRAM_CHAT_ID (for notifications)
- ✅ SOLANA_PRIVATE_KEY (for live trading)

### Step 4: Verify Settings

```bash
# Check no syntax errors
python3 -m py_compile src/main.py

# Check .env loads
python3 -c "import os; from dotenv import load_dotenv; load_dotenv(); print('OK')"
```

### Step 5: Test

```bash
# Restart bot
sudo systemctl restart solana-trading-bot

# Watch logs
tail -f bot.log
```

---

## 📊 Key Settings Explained

### Position Management (Highest Priority!)

```bash
DEFAULT_POSITION_SIZE=65        # Average $65 per trade
MAX_POSITION_SIZE=100           # Hard cap $100
MAX_OPEN_POSITIONS=5            # Max 5 concurrent

TRAILING_STOP_PERCENT=10        # Exit 10% below peak
MIN_POSITION_LIQUIDITY=5000     # Close if liquidity < $5k
STALE_PRICE_MINUTES=2           # Close if no movement 2 min
```

**Why Important:**
- Positions are the BACKBONE to make money
- Proper monitoring prevents losses
- Auto-closes rugs and dead tokens quickly

### Entry Filters (Finding Opportunities - Second Priority!)

```bash
MIN_ENTRY_LIQUIDITY=30000       # $30k minimum liquidity
MIN_24H_VOLUME=15000            # $15k daily volume
MIN_ENTRY_PRICE=0.10            # $0.10 minimum price
MAX_TOKENS_PER_DOLLAR=10000     # Max 10k tokens per $
```

**Why Important:**
- Quality filters = better trades
- Block scams, honeypots, dead tokens
- Only trade tokens with real volume/liquidity

### Exit Strategy (Don't Get Robbed!)

```bash
MIN_EXIT_LIQUIDITY=15000        # Need $15k to exit
SELL_SLIPPAGE_PERCENT=1.0       # Expect 1% slippage on sells
```

**Why Important:**
- Don't try to sell low liquidity (slippage eats profit)
- Better take small loss than get robbed on exit
- Check liquidity before AND after entering

### Rug Protection (Triple Control!)

```bash
RUG_DETECTION_ENABLED=true      # Auto-close rugs
FORCE_CLOSE_ON_RUG=true         # Don't wait, close immediately
RUGCHECK_API_KEY=...            # If ENABLE_RUGCHECK_API=true
```

**Triple Control:**
1. Entry: RugCheck scans before buying (if enabled)
2. Monitoring: Watch price movement (STALE_PRICE_MINUTES)
3. Exit: Force close on rug signals (FORCE_CLOSE_ON_RUG)

---

## 🔧 Feature Flags - When to Enable

### Start: Golden Baseline
```
ENABLE_JUPITER=true
Everything else=false
```

**Test for 6-12 hours:**
- Finding tokens?
- Good entry prices?
- Win rate 50%+?

### Add Sources (One at a Time)

**After baseline confirmed, test DexScreener:**
```
ENABLE_DEXSCREENER=true
```

**Test 2-4 hours:**
- More tokens found?
- Still quality?
- Win rate same or better?

**If good, add Birdeye:**
```
ENABLE_BIRDEYE=true
```

### Add Protection (One at a Time)

**RugCheck first:**
```
ENABLE_RUGCHECK_API=true
```

**Test 2-4 hours:**
- Blocks scams?
- Still finding good tokens?

**Whale tracking:**
```
ENABLE_WHALE_TRACKING=true
```

**Movement detection:**
```
ENABLE_MOVEMENT_DETECTION=true
```

### Add Intelligence (Last)

**Volume analyzer:**
```
ENABLE_VOLUME_ANALYZER=true
```

**Age-based strategies:**
```
ENABLE_AGE_BASED_STRATEGIES=true
```

**Twitter sentiment (optional - rate limited):**
```
ENABLE_TWITTER_SENTIMENT=true
```

---

## ⚠️ Critical Settings - Don't Change

These are proven Nov 30 settings that work:

```bash
# KEEP THESE VALUES
MIN_ENTRY_LIQUIDITY=30000       # Don't go lower
MIN_EXIT_LIQUIDITY=15000        # Don't go lower
MIN_24H_VOLUME=15000            # Don't go lower
TRAILING_STOP_PERCENT=10        # Proven optimal
STALE_PRICE_MINUTES=2           # Fast rug detection
MIN_POSITION_LIQUIDITY=5000     # Safety threshold
```

**You can change:**
- Position sizes (DEFAULT_POSITION_SIZE, MAX_POSITION_SIZE)
- Max positions (MAX_OPEN_POSITIONS)
- Feature flags (ENABLE_*)

**Don't change unless testing:**
- Liquidity/volume minimums
- Trailing stop percent
- Rug detection thresholds

---

## 🚨 Common Mistakes

### Mistake 1: Enabling Everything at Once
```bash
# ❌ DON'T DO THIS
ENABLE_JUPITER=true
ENABLE_DEXSCREENER=true
ENABLE_BIRDEYE=true
ENABLE_RUGCHECK_API=true
ENABLE_WHALE_TRACKING=true
ENABLE_MOVEMENT_DETECTION=true
# ... all true
```

**Problem:** If something breaks, you don't know which feature caused it

**Solution:** Enable one at a time, test 2-4 hours each

### Mistake 2: Lowering Liquidity Filters
```bash
# ❌ DON'T DO THIS
MIN_ENTRY_LIQUIDITY=5000        # Too low!
MIN_EXIT_LIQUIDITY=1000         # Way too low!
```

**Problem:** You'll enter tokens you can't exit (slippage kills profit)

**Solution:** Keep Nov 30 values (30k entry, 15k exit)

### Mistake 3: No API Keys
```bash
# ❌ THIS WON'T WORK
ENABLE_BIRDEYE=true
BIRDEYE_API_KEY=YOUR_KEY_HERE   # Not filled in!
```

**Problem:** Feature enabled but API key missing = errors

**Solution:** Fill in API keys OR keep feature disabled

### Mistake 4: Inline Comments
```bash
# ❌ SYSTEMD WON'T PARSE THIS
MIN_ENTRY_LIQUIDITY=30000  # My comment
```

**Problem:** Systemd's EnvironmentFile doesn't strip comments

**Solution:** Comments on separate lines only

---

## 📝 Checklist Before Starting

- [ ] Backed up current .env
- [ ] Filled in all API keys
- [ ] All feature flags set (start with false except Jupiter)
- [ ] Nov 30 working values unchanged
- [ ] No inline comments in .env
- [ ] Syntax check passed
- [ ] Service file has EnvironmentFile directive

---

## 🎯 Success Criteria

**Baseline (Jupiter only):**
- Finding 20-50 tokens per scan
- Win rate 50-60%
- No rugs/dead tokens losing >10%
- Positions monitored every 20s
- Auto-closes work correctly

**With DexScreener:**
- Finding 50-80 tokens per scan
- Win rate stays 50-60%+
- No duplicate tokens

**With Birdeye:**
- Finding 80-100 tokens per scan
- More Solana-native tokens
- Win rate stays or improves

**With Protection Features:**
- Blocks 80%+ scams
- Win rate improves to 70%+
- Fewer rug losses

**Final Goal:**
- 70-80% win rate
- Average +15% profit per winner
- Maximum -10% loss per loser
- Ready for live trading

---

## 📚 Related Files

- `.env` - Your actual configuration (not in git)
- `.env.template` - This complete template
- `FEATURE_FLAGS_GUIDE.md` - Detailed feature explanations
- `TOKEN_SOURCE_UPGRADE.md` - Token source combination guide
- `GOLDEN_BRANCH_ANALYSIS.md` - Working bot structure

---

## ✅ Summary

**What You Have:**
- Complete .env template with ALL settings
- Nov 30 proven working baseline
- 9 feature flags for incremental testing
- Clear testing strategy
- All API keys organized
- No hardcoded values

**What You Do:**
1. Copy template
2. Fill in API keys
3. Start with golden baseline (Jupiter only)
4. Test 6-12 hours
5. Add features one by one
6. Find optimal combination
7. Go to live mode when ready

**Most Important:**
- Monitor positions = #1 priority (backbone to make money)
- Find opportunities = #2 priority (feed the pipeline)
- Test one feature at a time = don't break what works
- Use real data = triple-check rugs/dead tokens
- Exit strategy = don't get robbed on low liquidity

🚀 **Now you have stable ground to build on!**
