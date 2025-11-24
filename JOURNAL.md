# Bot Development Journal

Track all changes, what worked, what broke, and how to revert.

---

## 2025-11-24 - Partial Profit-Taking Strategy

### Commit: `18b451e`
**Status: ✅ IMPLEMENTED - TESTING**

### What Changed:
- Added partial profit-taking at +100%, +200%, +300%, +500% milestones
- Sell 25%, 15%, 10%, 10% respectively at each milestone
- Remaining 40% continues with 10% trailing stop

### Why:
Theros position went from +743% to +67% in a flash crash before trailing stop could trigger. Lost ~$100 in unrealized gains. Need to lock profits incrementally.

### Files Modified:
- `src/trading/position_manager.py` - Added `initial_quantity` and `milestones_hit` tracking
- `src/trading/paper_trading.py` - Added milestone checking and partial sell logic

### Configuration:
```env
PARTIAL_PROFIT_ENABLED=true
PROFIT_MILESTONE_100=25
PROFIT_MILESTONE_200=15
PROFIT_MILESTONE_300=10
PROFIT_MILESTONE_500=10
```

### Expected Result:
- On big winners, lock 60% of gains incrementally
- Prevent total loss from flash crashes
- Let 40% ride with trailing stop for moon shots

### How to Revert:
```bash
git revert 18b451e
# Or set PARTIAL_PROFIT_ENABLED=false in .env
```

---

## 2025-11-24 - Fix Jupiter Categories Endpoint

### Commit: `afc6377`
**Status: ✅ WORKING**

### What Changed:
Fixed typo in Jupiter API endpoint: `/categories/` → `/category/` (singular)

### Why:
All Jupiter token discovery was broken, returning 400 errors. Bot was falling back to 4 hardcoded tokens (SOL, USDC, BONK, JUP). No real trading happening.

### Files Modified:
- `src/market/jupiter_client.py` line 109

### Result:
- ✅ Token discovery works again
- ✅ Bot gets fresh token lists
- ✅ No more 400 errors

### Research:
Jupiter V2 API docs at https://dev.jup.ag/docs/tokens/v2 - endpoint is `/category/` not `/categories/`

### How to Revert:
```bash
git revert afc6377
```

---

## 2025-11-24 - Revert to Simple Token Discovery

### Commit: `3710886`
**Status: ✅ WORKING**

### What Changed:
Reverted from complex token discovery attempts (category rotation, SolSniffer, fallbacks) back to simple `jupiter.get_recent_tokens(limit=50)`

### Why:
Was overcomplicating things trying to fix what was actually a simple typo bug. Complex attempts were all broken:
- Jupiter category rotation → endpoint didn't exist (typo)
- SolSniffer get_new_tokens → returns empty
- DexScreener trending → requires premium

### Files Modified:
- `src/main.py` - Simplified token discovery back to working state

### Result:
- ✅ Clean, simple code that works
- ✅ Gets 50 recent tokens from Jupiter
- ✅ No broken fallbacks

### Lesson:
Research APIs properly BEFORE making changes. Don't break working code.

### How to Revert:
```bash
git revert 3710886
```

---

## 2025-11-24 - Use Trending Tokens Instead of Recent

### Commit: `165334c`
**Status: ⚠️ DIDN'T WORK - REVERTED**

### What Changed:
Switched from `get_recent_tokens()` to `get_trending_tokens()` for token discovery

### Why:
Thought trending tokens might have better quality/momentum

### Result:
- ❌ Broke token discovery
- ❌ Jupiter endpoint returned 400 errors
- **Root cause was typo, not the endpoint choice**

### Reverted By:
Commit `3710886` reverted back to `get_recent_tokens()`

---

## 2025-11-24 - Fix Jupiter get_recent_tokens

### Commit: `3c6eca7`
**Status: ⚠️ COMPLEX ATTEMPT - REVERTED**

### What Changed:
Tried to fix token discovery by using SolSniffer instead of Jupiter

### Why:
Jupiter endpoints weren't working (due to typo bug)

### Result:
- ❌ SolSniffer `get_new_tokens()` returns empty data
- ❌ Didn't solve the problem
- **Real issue was the `/categories/` vs `/category/` typo**

### Reverted By:
Commit `3710886` reverted back to simple approach

---

## Known Working Configuration (as of 2025-11-24)

### Trading Parameters:
```env
INITIAL_CAPITAL=100.0
BUY_AMOUNT_USD=25.0
TRAILING_STOP_PERCENT=10
MIN_CONFIDENCE_SCORE=0.0  # Disabled to allow trades
BUY_SIGNAL_THRESHOLD=0.50  # Aggressive
```

### Token Discovery:
- Jupiter `get_recent_tokens(limit=50)` - ✅ Working
- Scan interval: 300 seconds (5 minutes)

### Risk Management:
- Rug detection: 3 minutes stale price, $8000 min liquidity
- Partial profit-taking: ✅ Enabled (25/15/10/10% at 100/200/300/500%)
- Trailing stop: 10% below peak on remaining position

### Performance History:
- **Before conservative changes**: 85-95% win rate with 20% take profit
- **After conservative changes**: 62.5% win rate, too selective
- **Current (aggressive)**: Testing partial profit-taking strategy

---

## How to Use This Journal

### If Bot Breaks:
1. Check recent commits in journal
2. Find last known working state
3. Revert using provided git commands
4. Document what broke in journal

### Before Making Changes:
1. Document current working state
2. Research APIs/endpoints properly
3. Make changes
4. Test thoroughly
5. Document results in journal

### Rolling Back:
```bash
# Revert specific commit
git revert <commit-hash>

# Or reset to specific commit (nuclear option)
git reset --hard <commit-hash>

# See commit history
git log --oneline -10
```

---

## Quick Reference: Git Commits

```bash
18b451e - Add partial profit-taking at milestones (TESTING)
afc6377 - Fix Jupiter categories endpoint (WORKING ✅)
3710886 - REVERT: Back to simple token discovery (WORKING ✅)
165334c - Use trending tokens (BROKEN - REVERTED)
3c6eca7 - Try SolSniffer for tokens (BROKEN - REVERTED)
```

---

## Lessons Learned

1. **Research APIs First**: Always check official docs before changing endpoints
2. **Don't Break Working Code**: If it works, be very careful changing it
3. **Simple > Complex**: The simple solution is usually the right one
4. **Lock Profits Early**: Trailing stops alone can't catch flash crashes
5. **Document Everything**: This journal prevents repeating mistakes

---

## TODO: Future Improvements

- [ ] Test partial profit-taking on real trades
- [ ] Monitor if 60% partial + 40% trailing is optimal ratio
- [ ] Consider faster price monitoring for better crash detection
- [ ] Track which tokens rug vs which moon
- [ ] Optimize buy signal threshold based on win rate data
