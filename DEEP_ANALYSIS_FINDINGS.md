# Deep Analysis Findings - Demo vs Live Issues

## Current Status (User's /status)
```
Portfolio: $13,309.82
Invested: $28.12
P&L: $13,309.82 (+100%)
Win Rate: 25.6% (11/30 trades)
```

**This is mathematically impossible:**
- 25.6% win rate with 11 wins, 30 losses = NET NEGATIVE expected
- Can't have $13k profit on $28 invested
- P&L calculation is clearly broken

---

## Bugs Found So Far

### 1. ✅ Fee Calculation Bug (FIXED - df7e712)
**Location:** src/blockchain/jupiter_executor.py:308
**Problem:** Using token quantity instead of USD value
```python
# BEFORE:
fees = self._calculate_fees(amount_in, use_jito)
# amount_in = 526,082 tokens → calculated as $526,082 USD!
# Result: $1,315 fee on $5 trade

# AFTER:
trade_value_usd = output_amount * sol_price_usd  # Convert to USD first
fees = self._calculate_fees(trade_value_usd, use_jito)
# Result: Correct ~$15 fee
```

### 2. ✅ P&L Portfolio Calculation Bug (FIXED - df7e712)
**Location:** src/trading/live_trading.py:552
**Problem:** Using hardcoded $200 wallet balance
```python
# BEFORE:
wallet_balance_usd = 200.0  # Hardcoded fake!
return wallet_balance_usd + positions_value_usd

# AFTER:
total_pnl = stats['total_realized_pnl'] + stats['total_unrealized_pnl']
portfolio_value = self.starting_balance + total_pnl
```

**BUT**: User still shows $13k P&L, so either:
- Fix not deployed yet
- State file has corrupted data
- starting_balance is wrong

### 3. ❓ Potential State File Corruption
**Hypothesis:** Old state file from demo mode or previous session has inflated numbers

**Need to check:**
- What's in live_trading_state.json?
- Is starting_balance correctly set?
- Are old trades from demo mode being loaded?

---

## Golden Branch vs Current Branch

### Settings Comparison

**Golden Branch (golden-working-60pct-winrate):**
```env
MIN_CONFIDENCE_SCORE=0.4  # .env.example default
MIN_SOCIAL_SCORE=0.6
MIN_ENTRY_LIQUIDITY=30000  # From 974-trade analysis
```

**User's Actual Demo Settings (122 trades, 33.8% ROI):**
```env
MIN_CONFIDENCE_SCORE=0.0  # User confirmed
MIN_SOCIAL_SCORE=0.0
MIN_ENTRY_LIQUIDITY=40000  # User confirmed
```

**Current Live Settings:**
```env
MIN_CONFIDENCE_SCORE=0.0  # Same as demo
MIN_SOCIAL_SCORE=0.0      # Same as demo
MIN_ENTRY_LIQUIDITY=30000 # DIFFERENT! (was 40k in demo)
```

**Finding:** Live is using 30k liquidity threshold, but demo used 40k!

### Code Changes

**Added in current branch (vs golden):**
1. Position persistence (absolute paths)
2. Force-close on dead tokens
3. Failed sell attempt tracking
4. Catastrophic fee protection
5. /cleanup command
6. Entry price validation
7. Volume fallback tracking

**Potential Issues:**
- Force-close logic might be too aggressive?
- State persistence might load corrupted data?
- Fee calculation bug (now fixed but was calculating wrong before)

---

## Key Questions to Answer

### 1. State File Investigation
- What's in live_trading_state.json?
- Is it loading old corrupted data?
- Should we delete it and start fresh?

### 2. Liquidity Threshold Mismatch
- Demo: 40k entry liquidity
- Live: 30k entry liquidity
- **Is this why live gets worse tokens?**

### 3. Token Source
- Both use: `jupiter.get_trending_tokens('toptraded', limit=50)`
- Should be same tokens
- Need to log actual tokens being analyzed

### 4. Timing/Market Conditions
- Demo: Specific time period?
- Live: Running 24/7, catching bad hours?
- Solana has quiet hours (low liquidity)?

### 5. Force-Close Behavior
- How many positions being force-closed?
- Is force-close being too aggressive?
- Are force-closes calculated correctly in P&L?

---

## Demo Mode Sellability Analysis

User verified with ChatGPT/Claude that 96.7% of 122 demo trades were ACTUALLY sellable.

**This rules out:**
- ❌ Demo bug (liquidity not passed to execute_sell)
- ❌ Demo not checking liquidity

**This confirms:**
- ✅ Demo tokens HAD good liquidity
- ✅ Demo results are REAL
- ✅ Something is different in live mode

---

## Next Investigation Steps

1. **Check live_trading_state.json**
   - See if corrupted data
   - Check starting_balance value
   - Verify trade history makes sense

2. **Compare Settings Exactly**
   - User's demo .env vs current live .env
   - MIN_ENTRY_LIQUIDITY: 40k (demo) vs 30k (live)

3. **Log Token Analysis**
   - What tokens is live mode analyzing?
   - Are they same quality as demo?
   - Liquidity levels?

4. **Check Force-Close Stats**
   - How many force-closes happened?
   - Are they calculated correctly?
   - Do they match user's 25.6% win rate?

5. **Verify Fee Fix Deployment**
   - Is df7e712 deployed on Digital Ocean?
   - Are fees now calculated correctly?
   - Check actual transaction logs

---

## Hypothesis: Liquidity Threshold Mismatch

**Demo (successful):**
- MIN_ENTRY_LIQUIDITY=40000
- Gets tokens with $40k+ liquidity
- 96.7% sellable rate
- 33.8% ROI

**Live (failing):**
- MIN_ENTRY_LIQUIDITY=30000
- Gets tokens with $30k+ liquidity (lower quality!)
- ~30% sellable rate
- Tokens dying faster

**Action:** Update live .env to match demo exactly:
```env
MIN_ENTRY_LIQUIDITY=40000  # Match demo
MIN_EXIT_LIQUIDITY=20000   # Match demo
MIN_CONFIDENCE_SCORE=0.0   # Already matches
MIN_SOCIAL_SCORE=0.0       # Already matches
```

---

## Summary

**Bugs Fixed:**
1. ✅ Fee calculation (token quantity → USD)
2. ✅ P&L calculation (fake $200 → real balance)

**Still Investigating:**
1. ❓ Why P&L shows $13k on $28 invested (state corruption?)
2. ❓ Liquidity threshold mismatch (40k demo vs 30k live)
3. ❓ Are force-closes working correctly?
4. ❓ Token quality difference demo vs live?

**User's Request:**
- Take time
- Deep analysis
- No changes until approved
- Find root cause of demo vs live difference
