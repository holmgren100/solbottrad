# Restoration Plan - Combine Working Bot + New Features

## Current Situation Analysis

### Two Working Versions Found:
1. **golden-working-60pct-winrate** branch
   - Jupiter token source
   - 60% win rate
   - Good PnL
   - Proven working

2. **Nov 30 backup** (.env you provided)
   - 97% good trades
   - Settings documented

### New Features Added (Current Branch):
1. ✅ Birdeye API integration
2. ✅ DexScreener integration
3. ✅ Age-based strategies (Phase 1)
4. ✅ RugCheck API (Phase 2)
5. ✅ Multi-layer screening (Phase 3)
6. ✅ Enhanced monitoring

### Problem:
- New features not properly integrated with old winning strategy
- Settings got corrupted with rapid changes
- Lost the winning formula

---

## Restoration Strategy

### Step 1: Create Safe Restoration Branch
```bash
git checkout -b restore-working-plus-upgrades
```

### Step 2: Get Core Working Strategy
From `golden-working-60pct-winrate`:
- Core trading logic
- Proven filters
- Win rate formula

### Step 3: Layer in New Features (ONE AT A TIME)
1. First: DexScreener + Birdeye token sources
2. Test: Verify still finding good tokens
3. Then: Enhanced filters (liquidity, volume monitoring)
4. Test: Verify not blocking good trades
5. Finally: Tune settings to match old win rate

### Step 4: Key Settings to Restore
```bash
# From working versions:
MIN_CONFIDENCE_SCORE=0.25        # Balanced (not 0.0, not 0.4)
MIN_SENTIMENT_SCORE=0.25         # Some filter
TRAILING_STOP_PERCENT=10         # Proven working
STALE_PRICE_MINUTES=2            # Fast exit for memes
MIN_ENTRY_LIQUIDITY=30000        # $30k (not $100k!)
MIN_24H_VOLUME=15000             # $15k (not $50k!)
DEFAULT_POSITION_SIZE=65         # Working size
MAX_POSITION_SIZE=100            # Working max
```

---

## What NOT to Do:
- ❌ Make multiple changes at once
- ❌ Modify .env with scripts
- ❌ Change core strategy logic
- ❌ Rush without testing

## What TO Do:
- ✅ One change at a time
- ✅ Test after each change
- ✅ Keep working strategy intact
- ✅ Only ADD features, don't REPLACE

---

## Next Steps (Need Your Approval):

1. Should I create restore branch from golden-working-60pct-winrate?
2. Or use current code + restore Nov 30 settings carefully?
3. Which version do you want as BASE: golden branch or Nov 30 backup?

Tell me which approach and I'll execute carefully.
