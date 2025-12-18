# 🔒 Protected ML Bot Core

**Based on ML Bot 2 - 71.7% win rate, 9.02x profit factor**

This package contains the **protected core** components from ML Bot 2, extracted and isolated to prevent accidental modifications. These components achieved proven results over 276 trades and should **NOT be modified** without extensive testing.

---

## 📊 Proven Performance

ML Bot 2's results with these exact components:

| Metric | Value | vs ML Bot 1 |
|--------|-------|-------------|
| **Trades** | 276 | -865 trades |
| **Win Rate** | **71.7%** | **+8.4%** 🔥 |
| **Avg Profit** | **$30.09** | **+133%** 🔥 |
| **Profit Factor** | **9.02x** | **+152%** 🔥 |
| **Stop Loss Rate** | **8.3%** | **-63%** 🔥 |
| **Trail Win Rate** | **85-93%** | Similar |
| **Low Liq Exit Win** | **73.7%** | Similar |

**Key Finding:** ML Bot 2 is SIMPLER but MORE EFFECTIVE than ML Bot 1!

---

## 🎯 Core Components

### 1. **RiskAssessor** (`selection/risk_assessor.py`)

**The secret to 71.7% win rate!**

Weighted risk scoring that finds real opportunities:

```python
risk_weights = {
    'liquidity': 0.35,      # Can't sell without it
    'security': 0.35,       # Rug pull protection
    'volatility': 0.05,     # Volatility = opportunity!
    'sentiment': 0.15,      # Coordination risk
    'prediction': 0.05,     # Less important
    'age': 0.05            # New tokens can moon
}
```

**Why it works:**
- 70% weight on essentials (liquidity + security)
- Only 10% on volatility/age (they're opportunities, not risks!)
- Finds REAL opportunities, not just "safe" tokens
- Proven: 71.7% win rate over 276 trades

**Liquidity Thresholds:**
```python
>= $100k: 0.1 risk (very safe)
>= $50k:  0.2 risk (safe)
>= $20k:  0.3 risk (moderate)
>= $10k:  0.5 risk (risky)
>= $5k:   0.7 risk (high risk)
< $5k:    1.0 risk (too risky - reject)
```

**Security Penalties:**
```python
Mintable: +0.25 risk
Freeze authority: +0.25 risk
Not verified: +0.20 risk
Ownership not renounced: +0.20 risk
Has blacklist: +0.10 risk
```

### 2. **PositionManager** (`exit/position_manager.py`)

**Trailing stops - 85-93% win rate!**

Exits positions using trailing stops that let winners run:

```python
TRAILING_STOP_PERCENT = 15  # 15% below PEAK (not entry!)

# Example:
# Entry: $0.10
# Peak: $0.50 (400% gain!)
# Trailing stop: $0.425 (15% below peak)
# Exit: $0.425 = 325% profit locked in!
```

**Why it works:**
- Not capped at fixed take profit (20%)
- Follows price up, locks in gains on pullback
- Lets winners run to 100%+ instead of exiting at 20%
- Proven: 85-93% win rate on trail exits

**Also tracks:**
- Drawdown from peak (monitors health)
- Position age (for rug detection)
- Price update failures (bad data detection)

### 3. **PriceValidator** (`monitoring/price_validator.py`)

**Dual-source validation prevents bad data losses**

Validates prices from multiple sources and rejects suspicious data:

```python
# Get prices from both sources
dex_price = await dexscreener.get_price(token)
jup_price = await jupiter.get_price(token)

# Cross-validate
if abs(dex_price - jup_price) / dex_price < 0.10:
    # Agree within 10% - use average
    price = (dex_price + jup_price) / 2
else:
    # Divergence - flag suspicious
    price = dex_price  # Use DexScreener (more reliable)

# Reject suspicious drops
if (price - entry_price) / entry_price < -0.80:
    # >80% drop = bad data!
    reject_price_update()
```

**Why it works:**
- Prevents 100% losses from bad API data
- Cross-validates from 2 independent sources
- Rejects None, NaN, Infinity, zero, negative prices
- Rejects suspicious drops >80% (likely bad data)
- Saved countless trades from fake losses

**Validation checks:**
1. ✅ None check
2. ✅ NaN (not a number) check
3. ✅ Infinity check
4. ✅ Zero/negative check
5. ✅ Extremely small (<$0.000000001) check
6. ✅ Suspicious drop (>80%) check

### 4. **MLBot2Config** (`config/ml_bot_2_config.py`)

**Exact settings that achieved 71.7% win rate**

All configuration values from ML Bot 2:

```python
# Risk scoring
risk_weights = {liquidity: 0.35, security: 0.35, ...}

# Trailing stops
use_trailing_stop = True
trailing_stop_percent = 15.0

# Rug detection
stale_price_minutes = 5
min_position_liquidity = 5000.0

# Monitoring
scan_interval = 120  # 2 minutes
monitor_interval = 60  # 1 minute

# What ML Bot 2 DOESN'T have:
simulate_fees = False  # No fee simulation
enable_tier2_filters = False  # No extra filters
allow_volume_fallback = False  # No volume fallback
auto_cleanup_enabled = False  # No stuck cleanup
```

**Why it works:**
- Simpler than ML Bot 1 (fewer features)
- Trusts core risk scoring
- No over-optimization
- LESS IS MORE!

---

## 🔒 Protection System

The core is protected to prevent accidental modifications:

1. **Protected marker:** `__protected__ = True` in `__init__.py`
2. **Version tracking:** `__version__ = "2.0.0"`
3. **Performance baseline:** Tracks ML Bot 2's proven metrics
4. **Validation function:** `validate_core()` checks integrity (placeholder for future hash validation)

**Future enhancements:**
- File hash validation
- Signature verification
- Automatic rollback on modification

---

## 📖 Usage

### Import Protected Components

```python
from ml_bot_core import RiskAssessor, PositionManager, PriceValidator, DEFAULT_CONFIG

# Use exact ML Bot 2 settings
config = DEFAULT_CONFIG

# Initialize core components (DO NOT MODIFY!)
risk_assessor = RiskAssessor(config)
position_manager = PositionManager(config)
price_validator = PriceValidator(dexscreener_client, jupiter_client)
```

### Token Analysis

```python
# Analyze token with core RiskAssessor
should_trade, risk_score = risk_assessor.assess_risk(
    token_address=token_address,
    market_data=market_data,
    security_data=security_data,
    sentiment_score=sentiment,
    price_prediction=prediction
)

if should_trade:
    print(f"✅ Trade approved! Risk: {risk_score:.2f}")
else:
    print(f"❌ Trade rejected. Risk: {risk_score:.2f}")
```

### Position Management

```python
# Create position with trailing stop
position = position_manager.create_position(
    token_address=token_address,
    entry_price=price,
    quantity=quantity,
    use_trailing_stop=True,
    trailing_stop_percent=15.0
)

# Update price (triggers trailing stop logic)
position_manager.update_position_price(token_address, current_price, liquidity)

# Check if should exit
should_exit, reason = position_manager.check_exit(token_address)

if should_exit:
    print(f"🚪 Exit signal: {reason}")
```

### Price Validation

```python
# Get validated price from dual sources
price, liquidity, source = await price_validator.get_validated_price(
    token_address=token_address,
    entry_price=entry_price
)

if price:
    print(f"✅ Valid price: ${price:.8f} from {source}")
else:
    print(f"❌ Invalid price data - skipping update")
```

---

## ⚠️ CRITICAL RULES

### DO:
1. ✅ **Use as-is** - Import and use the components
2. ✅ **Trust the core** - It's proven to work (71.7% win)
3. ✅ **Add enhancements AROUND the core** - Wrap, don't modify
4. ✅ **Test with data** - Validate any changes with 100+ trades

### DON'T:
1. ❌ **DON'T modify the core** - It finds winners, don't break it!
2. ❌ **DON'T add filters** - ML Bot 1 tried this, lost 8.4% win rate
3. ❌ **DON'T over-optimize** - Simple beats complex
4. ❌ **DON'T skip validation** - Test everything before deploying

---

## 🎯 The Winning Formula

```
GREAT SELECTION (RiskAssessor with 70% weight on essentials)
+ LET WINNERS RUN (trailing stops at 15% below peak)
+ CUT LOSERS FAST (rug detection at 5 min, $5k)
+ VALIDATE EVERYTHING (dual-source price validation)
= 71.7% WIN RATE, 9.02X PROFIT FACTOR 🔥
```

---

## 📚 File Structure

```
ml_bot_core/
├── __init__.py                    # Protection, validation, exports
├── README.md                      # This file
│
├── selection/
│   ├── __init__.py
│   └── risk_assessor.py          # 🔒 Weighted risk scoring
│
├── exit/
│   ├── __init__.py
│   └── position_manager.py       # 🔒 Trailing stops, position tracking
│
├── monitoring/
│   ├── __init__.py
│   └── price_validator.py        # 🔒 Dual-source validation
│
└── config/
    ├── __init__.py
    └── ml_bot_2_config.py        # 🔒 Exact ML Bot 2 settings
```

---

## 💡 Key Insights

### Why ML Bot 2 Wins:

1. **Simplicity** - Fewer filters = less over-optimization
2. **Balanced Risk Weights** - 70% on essentials (liquidity + security)
3. **Trailing Stops** - Lets winners run to 100%+ (not capped at 20%)
4. **Dual-Source Validation** - Prevents bad data losses
5. **Fast Monitoring** - Detects rugs in 5 minutes

### Why ML Bot 1 Lost 8.4% Win Rate:

1. **Too Many Filters** - Tier 2 filters blocked winners
2. **Over-Optimization** - Tried to prevent every loss
3. **Defensive Mindset** - Focused on avoiding losses instead of finding winners
4. **Complex = More Failure Points** - More code = more bugs

**Lesson:** LESS IS MORE! Trust the core, don't over-filter.

---

## 🔥 The Secret to 73.7% Low Liq Exit Success

ML Bot 2 achieves 73.7% win rate on low liquidity exits. The secret is **NOT** special exit logic - it's **SUPERIOR SELECTION**!

**Winners (73.7%):**
- Hold time: 26-34 minutes
- Drawdown: 0.8-1.3% (almost straight up!)
- ROI: 143-155% average
- Pattern: Token pumps cleanly

**Losers (26.3%):**
- Hold time: 14-15 minutes
- Drawdown: 30-34% (dumped hard)
- ROI: -20 to -24%
- Pattern: Pump then rug

**The Real Secret:**
1. RiskAssessor picks better tokens (they don't rug)
2. Patient holding (25-33 min for winners to develop)
3. Fast cutting (14-15 min to exit losers)
4. Drawdown tracking (can tell winners from losers early)

---

## 📞 Support

If you need to modify the core:

1. **Read ML_BOTS_ANALYSIS.md** - Understand why it works
2. **Test with data** - Run 100+ trades to validate
3. **A/B test** - Compare before/after performance
4. **Keep if better** - Only keep changes that improve win rate

**Remember:** The core is proven. It achieved 71.7% win rate. Modifications require proof, not assumptions!

---

*Protected Core v2.0.0 - Based on ML Bot 2 (276 trades, 71.7% win, 9.02x PF)*
*DO NOT MODIFY - Import and use only!*
