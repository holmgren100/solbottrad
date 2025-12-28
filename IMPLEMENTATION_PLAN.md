# ML Bot Exit/Entry Timing - Implementation Summary & Plan

**Date:** 2025-12-28
**Status:** Phase 1 COMPLETE - Data Collection in Progress
**Session:** claude/setup-new-session-NrKhE

---

## 🎯 GOAL: Improve Exit Timing (ML Bot 2 Style)

**Problem Identified:**
- Current win rate: 42.9% (Goal: 71.7%+ like ML Bot 2)
- Exiting winners too early due to liquidity fluctuations
- Not holding winners long enough (need 25-35 min minimum)
- Rug detection too aggressive (30% liquidity drop = instant exit)

**Core Insight from Analysis:**
ML Bot 2 achieved 71.7% win rate by:
1. **Drawdown as primary exit signal** (not liquidity)
2. **Winner hold pattern**: <5% drawdown = hold 25-35 min
3. **Loser pattern**: >30% drawdown = exit immediately
4. **Relaxed liquidity monitoring**: Only exit if >70% drop + price frozen

---

## ✅ PHASE 1: FIXES IMPLEMENTED (COMPLETED)

### Fix 1: Exit/Entry Timing Logic (Commit: 05da36a)

**File:** `ml_bot_core/exit/position_manager.py`

**Changes:**
1. Added `entry_liquidity` field to Position dataclass
2. Added drawdown tracking methods:
   - `get_drawdown_percent()` - Calculate % drop from peak price
   - `is_winner_pattern()` - <5% drawdown after 15+ min
   - `is_loser_pattern()` - >30% drawdown
3. Relaxed `is_liquidity_dead()`:
   - OLD: 30% liquidity drop = rug
   - NEW: 70% drop + price frozen 10 min = rug (combination signal)

**File:** `trading_bot/main.py`

**Changes:**
1. NEW Exit Priority Order (lines 477-568):
   ```
   Priority 1: DRAWDOWN (Loser pattern >30%)
   Priority 2: Stop Loss (Safety net)
   Priority 3: Rug Detection (Severe only: 70% liq + frozen)
   Priority 4: Trailing Stop (After winners develop)
   Priority 5: Winner Hold Logic (Don't exit <25 min!)
   ```

2. Winner Hold Logic:
   - If drawdown <5% and duration <25 min → SKIP EXIT, keep holding
   - Optimal window: 25-35 min for winners
   - After 35 min: Allow exit

3. Pass `entry_liquidity` when opening positions

### Fix 2: State Persistence Crash (Commit: 735da68)

**Problem:** Bot crashed on restart - `entry_liquidity` field missing from save/load

**Files Fixed:**
- `ml_bot_core/exit/state_persistence.py` - Added field to save method
- `ml_bot_core/exit/position_manager.py` - Added field to load method with default 0.0

### Fix 3: Partial Profit Crash (Commit: 2a99352)

**Problem:** Bot crashed when miharu hit +200% trying to sell partial profit

**File:** `trading_bot/main.py` line 466

**Fix:** Changed `self.executor.available_balance` → `self.executor.current_capital`

---

## 📊 CURRENT HARDCODED VALUES

**Drawdown Thresholds:**
- `LOSER_DRAWDOWN = 30%` - Exit if exceeds
- `WINNER_DRAWDOWN = 5%` - Hold if below

**Winner Hold Timing:**
- `WINNER_HOLD_MIN = 25 min` - Don't exit before this
- `WINNER_HOLD_OPTIMAL = 35 min` - Optimal exit window

**Liquidity Monitoring:**
- `LIQ_DROP_THRESHOLD = 70%` - Only flag if exceeds (was 30%)
- `FROZEN_MINUTES = 10 min` - Combination signal for rug

**Stop Loss:**
- `STOP_LOSS_PERCENT = 30%` - Hard stop (unchanged)

**Trailing Stop:**
- Currently active but after drawdown/rug checks
- Will add activation threshold later

---

## 📈 DATA TO COLLECT (2-3 HOURS)

**Current Baseline (Before Timing Fixes):**
- Total trades: 175
- Win rate: 42.9%
- Open positions: 13
- Total PnL: -$243.38
- Unrealized PnL: $93.57

**Metrics to Track:**

1. **Win Rate Impact:**
   - Does win rate improve from 42.9%?
   - Target: Move toward 71.7%

2. **Hold Time Analysis:**
   - Are losers exiting faster? (Goal: <30 min)
   - Are winners holding longer? (Goal: 25-35+ min)
   - Average hold time for winners vs losers

3. **Runner Detection:**
   - Do any positions reach +25%? +50%? +100%?
   - How long are they held?
   - Are they exiting in optimal 25-35 min window?

4. **Rug Detection:**
   - Are we avoiding false positives? (Not exiting on normal liquidity fluctuations)
   - Are we still catching real rugs? (70% drop + frozen price)

5. **Drawdown Patterns:**
   - How many exit via loser pattern (>30% drawdown)?
   - How many winners are held via winner pattern?
   - Is drawdown a better signal than liquidity?

**Commands to Check:**
```bash
# After 2-3 hours in Telegram:
/status  # Win rate, positions, PnL
/export  # Full trade history with hold times

# On server:
grep "WINNER HOLD" trading_bot.log | wc -l  # Count winner holds
grep "LOSER PATTERN" trading_bot.log | wc -l  # Count loser exits
grep "WINNER OPTIMAL" trading_bot.log  # Check optimal exits
```

---

## 🔧 PHASE 2: PLANNED CHANGES (AFTER DATA COLLECTION)

### Change 1: Move Hardcoded Values → ENV Variables

**Reason:** Allow tuning without code changes

**New ENV Variables:**
```bash
# Drawdown thresholds
LOSER_DRAWDOWN_PERCENT=30
WINNER_DRAWDOWN_PERCENT=5

# Winner hold timing
WINNER_HOLD_MIN_MINUTES=25
WINNER_HOLD_OPTIMAL_MINUTES=35

# Liquidity monitoring
LIQ_DROP_THRESHOLD_PERCENT=70
FROZEN_PRICE_MINUTES=10

# Stop loss
STOP_LOSS_PERCENT=30

# Trailing stop activation
TRAIL_ACTIVATION_PERCENT=35  # NEW: Only activate trail after 35% gain
```

**Files to Update:**
- `trading_bot/main.py` - Load from ENV with defaults
- `.env.example` - Document new variables
- `README.md` - Update configuration docs

### Change 2: Trail Stop Activation Threshold

**Current:** Trail stop always active (competes with winner hold logic)

**Problem:** May exit winners too early before they reach optimal 25-35 min

**Solution:** Only activate trail after position gains 35%+

**Logic:**
```python
# Only apply trailing stop if:
if gain_percent > TRAIL_ACTIVATION_PERCENT:  # 35%
    # Apply trailing stop logic
    if price dropped from peak by trail_percent:
        exit_position()
```

**Reason:** Let small winners develop without trail interference, only trail on big winners

### Change 3: Dynamic Stop Loss Based on Pattern

**Current:** Fixed 30% stop loss for all positions

**Idea:** Adjust stop loss based on winner/loser pattern

**Proposed Logic:**
```python
# Losers: Tight stop (20-25%)
if is_loser_pattern():
    stop_loss = 25%

# Winners: Allow more room (30-35%)
if is_winner_pattern():
    stop_loss = 35%
```

**Reason:** Protect losers faster, give winners more room to breathe

### Change 4: Time-Based Position Limits

**Current:** Max 15 positions at any time

**Observation:** Many positions held <30 min (quick losers)

**Idea:** Track "position slots" with time decay

**Proposed:**
- If position exits <15 min → Penalize slot for 5 min (don't immediately replace)
- If position exits 25-35 min (optimal) → Allow immediate replacement
- Encourages quality over quantity

**Goal:** Reduce churn, focus on better setups

### Change 5: Enhanced Logging for Analysis

**Add Detailed Exit Logs:**
```python
logger.info(
    f"📊 EXIT ANALYSIS: {symbol}\n"
    f"  Pattern: {'WINNER' if is_winner else 'LOSER'}\n"
    f"  Drawdown: {drawdown}%\n"
    f"  Hold Time: {duration}min\n"
    f"  Liq Drop: {liq_drop}%\n"
    f"  Exit Reason: {reason}\n"
    f"  P&L: ${pnl} ({pnl_pct}%)"
)
```

**Reason:** Better data for tuning thresholds

### Change 6: Winner/Loser Statistics Tracking

**Add to PositionManager:**
```python
self.winner_exits = 0  # Exits with <5% drawdown
self.loser_exits = 0   # Exits with >30% drawdown
self.avg_winner_hold_time = 0
self.avg_loser_hold_time = 0
self.optimal_exits = 0  # Exits in 25-35 min window
```

**Display in /status:**
```
Pattern Stats:
├─ Winners: 45 (avg hold: 32min)
├─ Losers: 30 (avg hold: 12min)
└─ Optimal Exits: 28 (62%)
```

**Reason:** Validate if patterns are working as designed

---

## 🧪 PHASE 3: POTENTIAL EXPERIMENTS (FUTURE)

### Experiment 1: Drawdown Threshold Optimization

**Test Different Values:**
- Loser threshold: 25%, 30%, 35%
- Winner threshold: 3%, 5%, 7%

**Method:** A/B test or sequential testing

### Experiment 2: Hold Time Windows

**Test Different Windows:**
- Conservative: 30-40 min
- Aggressive: 20-30 min
- Current: 25-35 min

### Experiment 3: Liquidity Drop Combinations

**Test Signal Combinations:**
1. 70% drop + 10 min frozen (current)
2. 80% drop + 5 min frozen (stricter)
3. 60% drop + 15 min frozen (looser)

### Experiment 4: Multi-Tier Exit Strategy

**Concept:** Different rules for different gain levels

```python
if gain > 100%:
    # Tier 3: Very profitable - use tight trail (5%)
elif gain > 50%:
    # Tier 2: Profitable - use medium trail (10%)
elif gain > 25%:
    # Tier 1: Developing - use winner hold logic
else:
    # Tier 0: Early - use drawdown logic
```

---

## 📋 IMMEDIATE NEXT STEPS

### Step 1: Data Collection (NOW - Next 2-3 Hours)
- ✅ Bot running with new timing fixes
- ✅ No code changes
- 🔄 Collecting trade data
- 🔄 Monitoring Telegram notifications

### Step 2: Analysis Session (After 2-3 Hours)
1. Run `/status` in Telegram
2. Run `/export` for detailed trade history
3. Analyze:
   - Win rate change
   - Hold time distribution
   - Runner performance
   - Exit reason breakdown

4. Check logs for pattern confirmations:
   ```bash
   grep "WINNER HOLD" trading_bot.log
   grep "LOSER PATTERN" trading_bot.log
   grep "Rug detected" trading_bot.log
   ```

### Step 3: Tune or Proceed (Based on Results)

**If Win Rate Improves (>45%):**
- ✅ Timing fixes working!
- → Proceed to Phase 2: Move to ENV variables
- → Add trail activation threshold

**If Win Rate Unchanged (42-44%):**
- ⚠️ Need to investigate
- → Check if winner hold logic is activating
- → Check if drawdown thresholds are right
- → May need to adjust thresholds

**If Win Rate Decreases (<42%):**
- ❌ Timing fixes may be too conservative
- → Review exit logs to see why
- → May need to tighten thresholds
- → Consider reverting some changes

### Step 4: Implement Phase 2 (If Validated)
1. Create ENV variables for all thresholds
2. Add trail activation threshold (35%)
3. Enhanced logging
4. Winner/loser stats tracking

### Step 5: Run Next Test Cycle
- Another 2-3 hours with ENV-based config
- A/B test different threshold values
- Continue iterating toward 71.7% target

---

## 🎯 SUCCESS CRITERIA

**Minimum Viable (Phase 1):**
- ✅ Bot runs without crashes
- ✅ Winner hold logic activates
- ✅ Loser pattern exits work
- ⏳ Win rate improves to 45%+

**Target (Phase 2):**
- Win rate: 50%+ (halfway to 71.7%)
- Average winner hold: 25-35 min
- Average loser hold: <20 min
- At least 1 runner per day reaching 50%+

**Stretch Goal (Phase 3):**
- Win rate: 60%+
- Consistent runners reaching 100%+
- Optimal exit rate: 70%+ of winners in 25-35 min window
- Trail stop only on big winners (35%+)

---

## 🔍 KEY METRICS TO WATCH

### Primary Metrics:
1. **Win Rate** (most important)
   - Current: 42.9%
   - Target: 71.7%
   - Milestone: 45% → 50% → 60%

2. **Average Hold Time for Winners**
   - Target: 25-35 min
   - Compare to losers (<20 min)

3. **Runner Frequency**
   - How many reach 50%+?
   - How many reach 100%+?
   - Are they held long enough?

### Secondary Metrics:
4. **Exit Reason Distribution**
   - How many: Drawdown vs Rug vs Trail vs Stop Loss
   - Optimal: More drawdown exits (good signal)

5. **False Positive Rate**
   - Are we exiting winners as rugs? (bad)
   - Should be near zero with 70% threshold

6. **Pattern Activation Rate**
   - % of trades that trigger winner hold logic
   - % of trades that trigger loser pattern
   - Target: 40-50% winners, 30-40% losers

---

## 📝 NOTES & OBSERVATIONS

### From Pre-Crash Analysis:

**User Insights:**
1. "Golden och ML fann de token ändå hela tiden" - ML bots found runners without complex filters
2. Security (stop loss, rug detection) important BUT must not block runners
3. Focus on EXIT timing, not complex entry filters
4. Simple is better - let patterns emerge from data

**Design Philosophy:**
- Drawdown > Liquidity (primary exit signal)
- Time-based patterns (25-35 min optimal window)
- Combination signals (not single indicators)
- Let winners run, cut losers fast

### Technical Debt:
- Partial profit logic exists but needs ENV config
- Trailing stop needs activation threshold
- Need better analytics/logging
- State persistence works but could be more robust

### Future Considerations:
- Live trading mode (not implemented yet)
- Multi-token liquidity tracking
- ML model for drawdown prediction
- Auto-tuning thresholds based on performance

---

## ⚠️ RISKS & MITIGATION

**Risk 1: Winner Hold Too Long**
- Risk: Hold winners past peak, give back gains
- Mitigation: 35 min upper limit, trail activation at 35%

**Risk 2: Loser Exit Too Late**
- Risk: 30% drawdown = -30% loss already
- Mitigation: Consider tightening to 25% if needed

**Risk 3: Rug Detection Misses**
- Risk: 70% threshold too high, miss some rugs
- Mitigation: Combination signal (liq + frozen), stop loss backup

**Risk 4: ENV Config Errors**
- Risk: Invalid values crash bot
- Mitigation: Validate ENV vars on startup, use safe defaults

---

## 📚 REFERENCES

**ML Bot 2 Baseline:**
- Win rate: 71.7%
- Pattern: Winner/loser detection via drawdown
- Exit priority: Drawdown first, not liquidity

**Current Codebase:**
- Entry logic: `ml_bot_core/entry/` (not modified)
- Exit logic: `ml_bot_core/exit/position_manager.py` (modified)
- Main loop: `trading_bot/main.py` (modified)
- State: `ml_bot_core/exit/state_persistence.py` (fixed)

**Commits This Session:**
1. `05da36a` - Exit/Entry timing fixes
2. `735da68` - State persistence fix
3. `2a99352` - Partial profit crash fix

---

**END OF PLAN**

*Next update after 2-3 hours of data collection.*
