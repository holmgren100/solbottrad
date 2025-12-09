# Bot Architecture Map
**Generated:** November 28, 2025
**Branch:** claude/restore-solana-bot-013YagNNs2FiAmTvNscyLeqq
**Analysis:** Complete codebase mapping

---

## 🎯 CRITICAL FINDINGS

### ✅ What's Already Implemented (GOOD NEWS!)
1. **SolSniffer/Honeypot Detection** - Already integrated!
   - File: `src/blockchain/solsniffer_client.py`
   - Used in: `src/main.py:219` - `analyze_token()`
   - Status: ✅ Working

2. **Position Tracking Features** - All exist!
   - File: `src/trading/position_manager.py:16-99`
   - ✅ Trailing stop logic (lines 66-75)
   - ✅ Peak price tracking (line 30, 68-69)
   - ✅ Milestone checking (lines 77-91)
   - ✅ Frozen price detection (lines 43-58)
   - ✅ Liquidity tracking (line 59)
   - Status: ✅ Code exists but NOT being called!

3. **Rug Detection Fields** - Built-in
   - Lines 33-38 in Position class
   - Tracks price freezes, liquidity drops
   - Status: ✅ Working

### ❌ What's Broken (INTEGRATION ISSUES!)

#### 1. **SLOW MONITORING** - Main Issue!
- **File:** `src/main.py:766-767`
- **Current:**
  ```python
  monitor_interval = 60  # 1 minute
  ```
- **Problem:** Too slow to catch rugs
- **Fix:** Change to 20 seconds
- **Priority:** 🔴 HIGH

#### 2. **NO LIQUIDITY CHECK BEFORE SELLS**
- **File:** `src/trading/live_trading.py:201-204`
- **Current:** Directly calls Jupiter without checking liquidity
  ```python
  swap_result = await self.jupiter_executor.sell_token(
      token_mint=token_address,
      amount_tokens=position.quantity,
      slippage_percent=5.0  # Fixed!
  )
  ```
- **Problem:**
  - No check if liquidity exists
  - Fixed 5% slippage regardless of market conditions
  - Will fail on low-liquidity tokens
- **Fix:** Add liquidity check + dynamic slippage
- **Priority:** 🔴 HIGH

#### 3. **MILESTONE LOGIC NOT CALLED**
- **File:** `src/trading/live_trading.py:259-299` (update_prices method)
- **Current:** Has stop_loss and trailing_stop checks
- **Missing:** Doesn't call `position.check_profit_milestone()`
- **Problem:** Milestones (100%, 200%, etc.) never trigger
- **Fix:** Add milestone checking to monitoring loop
- **Priority:** 🟡 MEDIUM

#### 4. **NO PARTIAL SELLS**
- **File:** `src/trading/live_trading.py:203`
- **Current:** Always sells full position
  ```python
  amount_tokens=position.quantity,  # Full position!
  ```
- **Problem:** Can't take partial profits at milestones
- **Fix:** Support partial sells
- **Priority:** 🟡 MEDIUM

---

## 📁 Key Files & Locations

### Main Entry Point
- **File:** `src/main.py`
- **Main Loop:** Lines 762-791
  - Scan interval: 120s (line 766)
  - Monitor interval: 60s (line 767) ← **NEEDS FIX**
  - Loop sleep: 10s (line 787)

### Trading Execution
- **Live Trading:** `src/trading/live_trading.py`
  - `execute_buy()`: Lines 78-165
  - `execute_sell()`: Lines 171-257 ← **NEEDS INTEGRATION**
  - `update_prices()`: Lines 259-299 ← **NEEDS MILESTONE LOGIC**

- **Jupiter Executor:** `src/blockchain/jupiter_executor.py`
  - `buy_token()`: Lines 371-422
  - `sell_token()`: Lines 424-460
  - Fixed 5% slippage ← **NEEDS DYNAMIC**

### Position Management
- **Position Class:** `src/trading/position_manager.py:16-99`
  - Has all features we need!
  - Just needs integration

### Safety Features (Already Exist!)
- **SolSniffer:** `src/blockchain/solsniffer_client.py`
- **Market Analysis:** `src/market/market_analyzer.py`
  - Honeypot detection: Line 100-122
  - Volume checks built-in

---

## 🔧 Integration Plan

### Phase 1: Quick Wins (30 minutes)
1. **INT-001:** Speed up monitoring (60s → 20s)
   - File: `src/main.py:767`
   - Change: `monitor_interval = 20`
   - Risk: LOW

2. **INT-002:** Add liquidity safety check function
   - Create: `src/safety/liquidity_checker.py`
   - New module, no breaking changes
   - Risk: ZERO

### Phase 2: Integration (1 hour)
3. **INT-003:** Integrate liquidity check into sells
   - File: `src/trading/live_trading.py:188-197`
   - Add check before line 201
   - Risk: MEDIUM (test carefully!)

4. **INT-004:** Verify honeypot detection is active
   - File: `src/main.py:219`
   - Already exists, verify it's blocking bad tokens
   - Risk: LOW

### Phase 3: Profit Protection (1 hour)
5. **PROFIT-001:** Add milestone checking to monitoring
   - File: `src/trading/live_trading.py:259-299`
   - Call `position.check_profit_milestone()`
   - Risk: MEDIUM

6. **PROFIT-002:** Implement partial sells
   - File: `src/trading/live_trading.py:171-257`
   - Add partial sell support
   - Risk: MEDIUM

---

## 🚫 DO NOT MODIFY

These components are working perfectly:
- ✅ Token discovery logic
- ✅ Buy execution
- ✅ Risk assessment (`src/ai/risk_assessor.py`)
- ✅ ML data collection (`src/data/ml_data_collector.py`)
- ✅ Position class structure
- ✅ SolSniffer integration

---

## 📊 Current State Summary

**Working:**
- Buy logic: ✅
- Risk assessment: ✅
- Honeypot detection: ✅
- Position tracking: ✅

**Needs Integration:**
- Monitoring speed: ❌ Too slow
- Liquidity checks: ❌ Not integrated
- Milestone profits: ❌ Not called
- Partial sells: ❌ Not implemented

**Root Cause:** The bot has all the features coded, but they're not integrated into the execution flow!

---

## Next Steps
1. Speed up monitoring (INT-001)
2. Create safety module (INT-002)
3. Integrate safety checks (INT-003)
4. Add milestone logic (PROFIT-001)
5. Implement partial sells (PROFIT-002)
6. Test in paper trading mode
7. Deploy with small capital
