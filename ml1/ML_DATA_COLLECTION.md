# 📊 ML Data Collection System

## Overview

Your bot now **automatically collects comprehensive trade data** for future machine learning training. Every trade is logged with 60+ data points capturing market conditions, risk scores, predictions, and outcomes.

**Strategy**: **COLLECT NOW, TRAIN LATER** when you have 100+ trades.

---

## 🎯 What's Being Collected

### Every Completed Trade Captures:

#### 📈 **Basic Trade Info**
- Entry/exit prices and times
- Hold duration
- Position size
- P&L (USD and %)
- Win/loss outcome
- Exit reason (trailing_stop, stop_loss, manual, rugged, partial_profit)

#### 🌊 **Market Conditions (Entry & Exit)**
- Liquidity (USD)
- 24h volume
- 24h price change
- Market cap
- Holder count
- Token age

#### ⚠️ **Risk Assessment Scores** (0-1)
- Overall risk score
- Liquidity risk
- Security risk
- Volatility risk
- Sentiment risk
- Age risk

#### 🎯 **Signals & Predictions**
- Sentiment score & confidence
- Coordination risk
- Price prediction direction
- Prediction confidence
- Predicted change %

#### 🔒 **Token Security**
- Is mintable?
- Has freeze authority?
- Is verified?
- Ownership renounced?

#### 💰 **Execution & Performance**
- Highest price reached during hold
- Max drawdown from peak
- Trailing stop settings
- Partial profit milestones hit
- Execution method (Jupiter/Jito)
- Fees paid

#### 🎲 **Portfolio Context**
- Portfolio value at entry
- Number of open positions
- Daily trades before this one

---

## 📂 Where Data is Stored

### **data/ml_training/**
```
data/ml_training/
├── ml_trades.jsonl       # JSON Lines format (one trade per line)
├── ml_trades.csv         # CSV format (Excel-friendly)
└── ml_ready.json         # Formatted for ML frameworks (export)
```

### **JSON Lines Format** (ml_trades.jsonl)
- One JSON object per line
- Easy to stream and process
- Compatible with most ML libraries (TensorFlow, PyTorch, scikit-learn)
- Efficient for large datasets

### **CSV Format** (ml_trades.csv)
- All fields in columns
- Easy to analyze in Excel/Google Sheets
- Good for manual inspection

---

## 🔍 Data Schema

### **MLTradeRecord** (60+ fields)

```python
{
  # === IDENTIFIERS ===
  "trade_id": "uuid",
  "token_address": "solana_address",
  "token_symbol": "TOKEN",

  # === TRADE BASICS ===
  "action": "completed",
  "entry_time": "2025-11-25T10:30:00",
  "exit_time": "2025-11-25T12:45:00",
  "hold_duration_minutes": 135.0,

  # === PRICES ===
  "entry_price": 0.00001234,
  "exit_price": 0.00002468,
  "highest_price_reached": 0.00003000,
  "lowest_price_reached": 0.00001000,

  # === POSITION ===
  "amount_usd": 15.50,
  "quantity": 1255555.0,
  "position_size_percent_of_portfolio": 1.55,

  # === OUTCOME ===
  "pnl_usd": 15.50,
  "pnl_percent": 100.0,
  "win": true,
  "exit_reason": "trailing_stop",

  # === MARKET @ ENTRY ===
  "entry_liquidity_usd": 25000.0,
  "entry_volume_24h": 150000.0,
  "entry_price_change_24h": 45.5,
  "entry_holder_count": 1250,
  "entry_market_cap": 500000.0,

  # === MARKET @ EXIT ===
  "exit_liquidity_usd": 30000.0,

  # === TOKEN CHARACTERISTICS ===
  "token_age_hours": 12.5,
  "is_mintable": false,
  "has_freeze_authority": false,
  "is_verified": true,
  "ownership_renounced": true,

  # === RISK SCORES (0-1) ===
  "overall_risk_score": 0.45,
  "liquidity_risk": 0.3,
  "security_risk": 0.2,
  "volatility_risk": 0.6,
  "sentiment_risk": 0.4,
  "age_risk": 0.7,

  # === SIGNALS ===
  "sentiment_score": 0.75,
  "sentiment_confidence": 0.68,
  "coordination_risk": 0.2,
  "price_prediction_direction": "up",
  "price_prediction_confidence": 0.72,
  "predicted_change_percent": 35.5,

  # === PERFORMANCE ===
  "max_drawdown_from_peak_percent": 10.5,
  "used_trailing_stop": true,
  "trailing_stop_percent": 15.0,
  "milestones_hit": [100, 200],
  "partial_sell_count": 2,

  # === CONTEXT ===
  "portfolio_value_at_entry": 1000.0,
  "open_positions_count": 3,
  "daily_trades_before_this": 5,
  "execution_method": "jupiter",
  "paper_trading": true
}
```

---

## 📊 Checking Your Data

### **In Python** (after running bot):

```python
from src.data import MLDataCollector

collector = MLDataCollector()
stats = collector.get_statistics()

print(stats)
# Output:
# {
#   'total_trades': 47,
#   'winning_trades': 25,
#   'losing_trades': 22,
#   'win_rate': 0.532,
#   'avg_hold_duration_hours': 4.5,
#   'ready_for_ml': False,  # Need 100+ trades
#   'message': 'Need 53 more trades for ML training (current: 47)',
#   'data_quality_score': 0.87  # 0-1, higher is better
# }
```

### **Export for ML Frameworks**:

```python
collector.export_for_ml_framework('data/ml_ready.json')
# Creates structured file ready for scikit-learn, TensorFlow, PyTorch
```

---

## 🤖 Future ML Applications

Once you have 100+ trades, this data can train models to:

### **1. Trade Quality Prediction**
- **Input**: Market conditions, risk scores, predictions
- **Output**: Probability this trade will be profitable
- **Use**: Skip low-probability setups

### **2. Optimal Position Sizing**
- **Input**: Token characteristics, portfolio state
- **Output**: Recommended position size
- **Use**: Dynamic position sizing based on confidence

### **3. Exit Timing Optimization**
- **Input**: Current profit %, hold duration, market conditions
- **Output**: Hold or exit?
- **Use**: Better exit timing than fixed rules

### **4. Risk Calibration**
- **Input**: Your actual win rates per risk category
- **Output**: Adjusted risk thresholds
- **Use**: Personalized risk assessment

### **5. Pattern Recognition**
- **Input**: All features
- **Output**: Identify profitable vs unprofitable patterns
- **Use**: Discover which market conditions work best for YOU

---

## 📈 Data Quality

### **What Makes Good ML Training Data:**

✅ **100+ trades minimum** (200+ better, 500+ ideal)
✅ **Mix of wins and losses** (not just cherry-picked wins)
✅ **Diverse market conditions** (different liquidity levels, ages, etc.)
✅ **Complete fields** (all risk scores, predictions filled in)
✅ **Honest outcomes** (include rugs, stop losses, etc.)

### **Your Current Quality Score:**

The bot calculates a data quality score (0-1) based on:
- How many critical fields are filled
- Completeness of risk assessments
- Availability of predictions

**Target: 0.8+** for good ML training

---

## 🔧 Technical Details

### **Automatic Collection**

Data is collected **automatically** when:
1. You buy a token → Analysis context stored
2. You sell a token → Complete MLTradeRecord created
3. Exit reason captured → (trailing_stop, manual, rugged, etc.)
4. Saved to disk → Both JSONL and CSV

### **No Performance Impact**

- Async I/O (non-blocking)
- Small file sizes (~2KB per trade)
- Minimal memory footprint
- Errors don't crash bot

### **Data Privacy**

- All data stored **locally** in `data/ml_training/`
- No data sent to external servers
- You control the data completely
- Can delete anytime

---

## 🎯 Recommended Workflow

### **Phase 1: Collection** (NOW - Next 2-4 weeks)
1. ✅ Run bot in paper trading mode
2. ✅ Let it collect 100-200 trades naturally
3. ✅ Check data quality score weekly
4. ✅ Don't modify strategy yet - need clean baseline

### **Phase 2: Analysis** (After 100+ trades)
1. Export data: `collector.export_for_ml_framework()`
2. Analyze in Jupyter Notebook or Excel
3. Look for patterns manually first
4. Identify which conditions led to best trades

### **Phase 3: ML Training** (After 200+ trades)
1. Build simple ML models (Random Forest, XGBoost)
2. Test predictions on held-out data
3. Validate before using in live trading
4. Iterate and improve

### **Phase 4: Integration** (After successful ML tests)
1. Add ML predictions to decision making
2. Start with conservative confidence thresholds
3. Monitor performance
4. Tune based on results

---

## 📝 Example Analysis Questions

With 100+ trades, you can answer:

- **"Which token age range has highest win rate?"**
  - Filter by `token_age_hours`, calculate win rates

- **"Does high coordination risk correlate with losses?"**
  - Plot `coordination_risk` vs `pnl_percent`

- **"What's optimal hold duration?"**
  - Analyze `hold_duration_minutes` for winning trades

- **"Are my risk scores accurate?"**
  - Compare `overall_risk_score` to actual outcomes

- **"Should I trust sentiment predictions?"**
  - Measure `sentiment_score` prediction accuracy

- **"What's my real edge?"**
  - Find feature combinations that predict wins

---

## 🚀 Getting Started

### **1. Just Run the Bot**
```bash
python -m src.main
```

Data collection happens automatically!

### **2. Check Progress Periodically**
```bash
ls -lh data/ml_training/
# Shows file sizes, number of records
```

### **3. Export for Analysis** (when ready)
```python
from src.data import MLDataCollector
collector = MLDataCollector()
collector.export_for_ml_framework()
```

### **4. Analyze in Excel/Python**
```bash
# Excel: Open data/ml_training/ml_trades.csv
# Python: Load data/ml_training/ml_ready.json
```

---

## ✅ Current Status

- ✅ **ML data collection:** ENABLED
- ✅ **Auto-logging:** Every trade
- ✅ **60+ data points:** Comprehensive capture
- ✅ **Dual formats:** JSONL + CSV
- ✅ **Zero config needed:** Works out of the box

**Next:** Let bot run and accumulate trades. Check back after 100 trades!

---

## 🎓 ML Resources (For Later)

When you're ready to build ML models:

- **scikit-learn** - Simple, great for beginners
- **XGBoost** - Powerful, good for tabular data
- **TensorFlow/PyTorch** - Advanced deep learning
- **pandas** - Data analysis and manipulation
- **matplotlib/seaborn** - Visualization

**Recommended starting point:** scikit-learn Random Forest for trade classification.

---

**Bottom Line:** Your bot is now a learning machine. Every trade makes it smarter (once you train the models). Just let it run and collect quality data! 🚀
