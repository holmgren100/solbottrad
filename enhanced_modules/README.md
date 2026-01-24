# Enhanced Modules

**Optional enhancements for the ML Bot 2 protected core**

These modules add functionality WITHOUT modifying the proven core logic that achieved 71.7% win rate.

---

## 📋 What's Included

### 1. **CSVTracker** (`csv_tracker.py`)

Comprehensive trade logging with 50+ fields for deep analysis.

**Fields tracked:**
- Core trade data (price, PnL, duration, exit reason)
- Liquidity tracking (entry vs exit, % change)
- Volume data (24h, 1h)
- Selection scoring (opportunity score, risk score)
- Source tracking (API, DEX platform)
- Peak tracking (max gain, drawdown from peak)
- Configuration used (stop loss %, trailing %, etc.)
- Transaction activity (buys, sells, ratio)
- Position sizing data (multipliers, bonuses)
- LP lock status (locked, burned, days)
- Holder concentration (top 10%, top 1%)
- Contract safety (mint, freeze, ownership)
- Momentum indicators (price changes, volume spikes)

**Why use it:**
✅ Essential for performance analysis
✅ A/B testing different strategies
✅ Pattern discovery
✅ Optimization decisions based on data

**Usage:**
```python
from enhanced_modules import CSVTracker

tracker = CSVTracker(enabled=True, auto_export=True)

# Log trade on exit
tracker.log_trade(position, exit_reason='trailing_stop', exit_price=0.50)

# Export manually
tracker.export_csv('data/trades.csv')

# Get statistics
stats = tracker.get_statistics()
print(f"Win rate: {stats['win_rate']:.1f}%")
```

### 2. **SafetyFilters** (`safety_filters.py`)

Optional pre-filters for common rug pull indicators.

**Checks available:**
- **LP Lock:** Is LP locked or burned? For how long?
- **Holder Concentration:** Top 10 holders < 50%? Top 1 < 20%?
- **Contract Safety:** Mint/freeze authority? Ownership renounced?

**Why optional:**
⚠️  ML Bot 2 achieves 71.7% win rate WITHOUT these!
⚠️  They may block good opportunities
⚠️  Need A/B testing to prove they IMPROVE performance

**Usage:**
```python
from enhanced_modules import SafetyFilters, SafetyConfig

config = SafetyConfig(
    enable_lp_lock_check=True,
    lp_lock_min_days=30,
    enable_holder_check=True,
    holder_top10_max_percent=50.0,
    enable_contract_safety=True,
)

filters = SafetyFilters(enabled=True, config=config)

# Check token before core RiskAssessor
passed, reason = filters.check_all(token_data)

if not passed:
    logger.info(f"Blocked by safety filter: {reason}")
    # Skip this token
else:
    # Continue to core RiskAssessor
    should_trade, risk = risk_assessor.assess_risk(token_data)
```

---

## 🎯 Integration with Protected Core

These modules wrap around the protected core WITHOUT modifying it:

```python
from ml_bot_core import RiskAssessor, PositionManager, PriceValidator, DEFAULT_CONFIG
from enhanced_modules import CSVTracker, SafetyFilters

class TradingBot:
    def __init__(self, config):
        # 🔒 PROTECTED CORE (never modified!)
        self.risk_assessor = RiskAssessor(DEFAULT_CONFIG)
        self.position_manager = PositionManager(DEFAULT_CONFIG)
        self.price_validator = PriceValidator(dex_client, jup_client)

        # ✅ OPTIONAL ENHANCEMENTS
        self.csv_tracker = CSVTracker(enabled=config.enable_csv)
        self.safety_filters = SafetyFilters(enabled=config.enable_safety)

    def analyze_token(self, token_address):
        """Analyze token with optional pre-filters."""

        # Get token data
        token_data = self.get_token_data(token_address)

        # OPTIONAL: Safety pre-filter
        if self.safety_filters and self.safety_filters.enabled:
            passed, reason = self.safety_filters.check_all(token_data)
            if not passed:
                logger.info(f"Safety filter blocked: {reason}")
                if self.csv_tracker:
                    self.csv_tracker.log_rejection(token_address, reason)
                return False, reason

        # 🔒 PROTECTED CORE SELECTION (never bypassed!)
        should_trade, risk = self.risk_assessor.assess_risk(
            token_address,
            market_data,
            security_data,
            sentiment_score,
            price_prediction
        )

        # OPTIONAL: Track analysis for later review
        if self.csv_tracker:
            self.csv_tracker.log_analysis(token_address, should_trade, risk)

        return should_trade, risk

    def close_position(self, token_address, exit_price, reason):
        """Close position with optional tracking."""

        # 🔒 CORE: Close position
        position = self.position_manager.get_position(token_address)
        trade = self.position_manager.close_position(token_address, exit_price, reason)

        # OPTIONAL: Track comprehensive data
        if self.csv_tracker and position:
            self.csv_tracker.log_trade(position, reason, exit_price)

        return trade
```

**Key Pattern:** Core logic is protected. Enhancements wrap around it but never modify it!

---

## ⚙️ Configuration (.env)

```bash
# === ENHANCED MODULES CONFIGURATION ===

# CSV Tracking (RECOMMENDED: true)
ENABLE_CSV_TRACKING=true
CSV_AUTO_EXPORT=true
CSV_EXPORT_PATH=data/ml_trades.csv

# Safety Filters (TEST IMPACT!)
ENABLE_SAFETY_FILTERS=true  # A/B test this!

# LP Lock Check
ENABLE_LP_LOCK_CHECK=true
LP_LOCK_MIN_DAYS=30
LP_LOCK_ACCEPT_BURNED=true

# Holder Concentration Check
ENABLE_HOLDER_CHECK=true
HOLDER_TOP10_MAX=50.0  # Top 10 holders < 50%
HOLDER_TOP1_MAX=20.0   # Top 1 holder < 20%

# Contract Safety Check
ENABLE_CONTRACT_SAFETY=true
REJECT_MINT_AUTHORITY=true
REJECT_FREEZE_AUTHORITY=true
REQUIRE_OWNERSHIP_RENOUNCED=true
```

---

## 🧪 A/B Testing Recommendations

### Test 1: Core Only (Baseline)
```bash
ENABLE_CSV_TRACKING=true  # Track data
ENABLE_SAFETY_FILTERS=false  # No filters
```
**Goal:** Establish baseline performance (should match ML Bot 2: ~71.7% win)

### Test 2: Core + Safety Filters
```bash
ENABLE_CSV_TRACKING=true
ENABLE_SAFETY_FILTERS=true
```
**Goal:** Does adding safety filters IMPROVE or HURT win rate?

**Analysis:**
- Compare win rates (Test 1 vs Test 2)
- Check if filters blocked winners or only losers
- Look at safety_score correlation with PnL

**Decision:**
- If win rate improves: Keep filters ✅
- If win rate drops: Disable filters ❌
- If neutral: Keep for risk reduction (preference)

### Test 3: Tune Filter Thresholds
If Test 2 shows promise, tune:
- LP lock days (7, 14, 30, 90)
- Holder concentration (top10: 40%, 50%, 60%)
- Contract safety (selective vs strict)

---

## 📊 Expected CSV Output

```csv
Date,Time,Symbol,Entry Price,Exit Price,PnL ($),PnL (%),Win/Loss,Exit Reason,Duration (min),Entry Liquidity,Exit Liquidity,LP Locked,LP Burned,Top 10 Concentration (%),Contract Safe,...
2025-12-18,14:30:15,BONK,$0.00001234,$0.00001850,$25.67,49.92%,WIN,trailing_stop,28.5,$45000,$42000,Yes,No,35.2%,Yes,...
```

**Analysis possibilities:**
- Filter `Exit Reason` by `trailing_stop` → Check win rate on trail exits
- Group by `LP Locked` → Does LP lock correlate with wins?
- Plot `Max Gain (%)` vs `Peak to Exit Drop (%)` → Optimize trail distance
- Check `Top 10 Concentration (%)` for winners vs losers → Useful filter?

---

## 📁 File Structure

```
enhanced_modules/
├── __init__.py              # Module exports
├── README.md                # This file
├── csv_tracker.py           # 50+ field CSV tracking
└── safety_filters.py        # LP lock, holder, contract checks
```

---

## ⚠️ Important Notes

### DO:
1. ✅ **Always use CSV tracking** - Essential for analysis
2. ✅ **A/B test safety filters** - Prove they help before keeping
3. ✅ **Review CSV data regularly** - Find patterns, optimize
4. ✅ **Keep enhancements optional** - Easy to toggle on/off

### DON'T:
1. ❌ **Don't modify core logic** - Enhancements wrap, never modify
2. ❌ **Don't assume filters help** - Test with data
3. ❌ **Don't ignore the CSV** - It's your optimization compass
4. ❌ **Don't add complexity without proof** - Simple > complex

---

## 🎯 Success Metrics

**CSV Tracking:**
- ✅ Captures all 50+ fields correctly
- ✅ Exports to readable CSV format
- ✅ Enables pattern analysis and optimization

**Safety Filters:**
- ✅ Can toggle on/off easily
- ✅ Logs reason for each rejection
- ✅ Impact on win rate is measurable (via CSV)

**Integration:**
- ✅ Works with protected core without modification
- ✅ All features configurable via .env
- ✅ No performance degradation

---

*Enhanced Modules v1.0.0 - Optional enhancements for ML Bot 2 core*
*DO NOT modify protected core - Enhancements wrap around it!*
