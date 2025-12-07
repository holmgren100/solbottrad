# Token Tracker & Filter - .env Parameters

## Overview
These parameters control the Token Performance Tracker and Blacklist/Whitelist Filter.
**ALL DISABLED BY DEFAULT** - Infrastructure is ready but not activated.

Add these to your `.env` file when ready to use them.

---

## Token Performance Tracker

**Purpose**: Learn from historical token performance to avoid repeat losers.

```bash
# Enable/disable token performance tracking
ENABLE_TOKEN_TRACKER=false  # Set to 'true' to activate

# Auto-blacklist settings (requires tracker + filter enabled)
AUTO_BLACKLIST_LOSERS=false  # Auto-add consistent losers to blacklist
AUTO_BLACKLIST_MIN_TRADES=3  # Minimum trades before auto-blacklist
AUTO_BLACKLIST_MAX_WINRATE=0.0  # Max win rate % for auto-blacklist (0 = 100% losers only)
```

**How it works**:
- Tracks every token you trade (wins/losses, avg PnL, win rate)
- Stores data in `data/token_performance.json`
- Detects "consistent losers" (3+ trades, 0% win rate)
- Detects "repeat winners" (3+ trades, 60%+ win rate)
- Logs warnings when you encounter known losers
- Can auto-blacklist repeat losers if enabled

**Example usage** (when enabled):
```
✅ REPEAT WINNER: 9AvytnUK... - 5 trades, 80% win rate!  (logs info)
❌ REJECTED 2HtgZvJm... - REPEAT LOSER: 4 trades, 0% win rate, avg -12.5% PnL
🚫 Added to BLACKLIST: 2HtgZvJm... (4 trades, 0% win)  (if auto-blacklist enabled)
```

---

## Blacklist/Whitelist Filter

**Purpose**: Manually filter known good/bad tokens.

```bash
# Enable/disable blacklist/whitelist filtering
ENABLE_TOKEN_FILTER=false  # Set to 'true' to activate
```

**How it works**:
- **Blacklist**: Tokens to NEVER trade (stored in `data/token_blacklist.json`)
- **Whitelist**: Tokens to ALWAYS allow - bypasses ALL filters (stored in `data/token_whitelist.json`)
- Manual control via JSON files or auto-populated by tracker

**Priority order**:
1. Whitelist (highest) - always allow
2. Blacklist - always reject
3. Other filters - normal processing

**Example usage** (when enabled):
```
✅ WHITELISTED token JUPyiwrY... - bypassing other filters
❌ REJECTED 2HtgZvJm... - Token is BLACKLISTED
```

---

## Integration with Existing System

**Execution flow when both enabled**:
1. Token discovered
2. Check whitelist → **ALLOW** (bypass all filters)
3. Check blacklist → **REJECT**
4. Check performance tracker → **REJECT if repeat loser**
5. Check opportunity score, liquidity, etc. (normal filters)
6. Execute trade
7. On close → **Record to tracker**
8. If consistent loser detected → **Auto-blacklist** (if enabled)

---

## Recommended Settings for Testing

### Phase 1: Data Collection (CURRENT - Recommended)
```bash
ENABLE_TOKEN_TRACKER=false  # Not yet - collect more data first
ENABLE_TOKEN_FILTER=false   # Not yet - no manual lists
```
**Why**: Need 200-300 trades with proper scoring before enabling filters

### Phase 2: Analysis (After 200-300 trades)
```bash
ENABLE_TOKEN_TRACKER=true   # Start tracking
ENABLE_TOKEN_FILTER=false   # Still no filtering
AUTO_BLACKLIST_LOSERS=false # Just track, don't filter yet
```
**Why**: Build performance database without affecting trading

### Phase 3: Filtering (When patterns confirmed)
```bash
ENABLE_TOKEN_TRACKER=true
ENABLE_TOKEN_FILTER=true
AUTO_BLACKLIST_LOSERS=true
AUTO_BLACKLIST_MIN_TRADES=5  # Conservative (5+ trades needed)
AUTO_BLACKLIST_MAX_WINRATE=20.0  # Reject if <20% win rate
```
**Why**: Only filter after proven patterns (e.g., "token X lost 10 times in a row")

---

## Data Files Created

When enabled, these files are auto-created in `data/`:

```
data/token_performance.json   # Token win/loss history
data/token_blacklist.json     # Manual + auto blacklist
data/token_whitelist.json     # Manual whitelist
```

**Format examples**:

`token_performance.json`:
```json
{
  "9AvytnUKGJvKhBR2znJ6MzGe2iZbZMHC9mZPUBfBpump": {
    "total_trades": 21,
    "winning_trades": 0,
    "losing_trades": 21,
    "win_rate": 0.0,
    "avg_pnl_percent": -8.5,
    "symbol": "UNKNOWN"
  }
}
```

`token_blacklist.json`:
```json
[
  "9AvytnUKGJvKhBR2znJ6MzGe2iZbZMHC9mZPUBfBpump",
  "2HtgZvJmHfQdTiVuBa6cJ9xYMb5XqP9WNkFrK8Sspump"
]
```

---

## Summary

**CURRENT STATUS**: ✅ Infrastructure ready, ⏸️ Disabled by default

**Add to .env** (keep disabled for now):
```bash
# === TOKEN PERFORMANCE TRACKER (INFRASTRUCTURE - DISABLED) ===
ENABLE_TOKEN_TRACKER=false
AUTO_BLACKLIST_LOSERS=false
AUTO_BLACKLIST_MIN_TRADES=3
AUTO_BLACKLIST_MAX_WINRATE=0.0

# === BLACKLIST/WHITELIST FILTER (INFRASTRUCTURE - DISABLED) ===
ENABLE_TOKEN_FILTER=false
```

**Enable when ready**: After collecting 200-300 trades with new CSV tracking, analyze the data and decide if patterns are strong enough to activate filtering.
