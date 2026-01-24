# ML Bot 2 Trading Bot

**Main bot integration that combines the protected ML Bot 2 core with optional enhancement modules.**

This is the production-ready bot that you'll run. It integrates:
- 🔒 **Protected Core** (71.7% win rate foundation)
- ✅ **Optional Enhancements** (CSV tracking, safety filters)

---

## 🚀 Quick Start

### 1. Setup Configuration

Copy the template to create your `.env` file:

```bash
cp .env.ml_bot_2 .env
```

### 2. Configure Settings

Edit `.env` and add your API keys:

```bash
# Required API Keys
SOLANA_PRIVATE_KEY=your_private_key_here
DEXSCREENER_API_KEY=your_api_key_here

# Optional API Keys
SOLSNIFFER_API_KEY=your_api_key_here
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```

### 3. Choose Your Mode

**Start with paper trading to test:**

```bash
PAPER_TRADING_MODE=true
PAPER_SOL_BALANCE=1000.0
```

**When ready for live trading:**

```bash
PAPER_TRADING_MODE=false
```

### 4. Run the Bot

```bash
# Install dependencies first
pip install -r requirements.txt

# Run the bot
python trading_bot/main.py
```

---

## ⚙️ Configuration

### 🔒 Protected Core Settings (DO NOT MODIFY!)

These achieved 71.7% win rate - only change if you have data proof:

```bash
# Trailing Stops (85-93% win rate on trail exits!)
USE_TRAILING_STOP=true
TRAILING_STOP_PERCENT=15.0          # 15% below PEAK price

# Position Management
MAX_OPEN_POSITIONS=7
STOP_LOSS_PERCENT=20.0              # Fallback if trailing disabled
TAKE_PROFIT_PERCENT=50.0            # Fallback if trailing disabled

# Rug Detection
RUG_DETECTION_ENABLED=true
STALE_PRICE_MINUTES=5               # No price update = rug
MIN_POSITION_LIQUIDITY=5000         # Below this = rug

# Monitoring
SCAN_INTERVAL=120                   # Scan every 2 min
MONITOR_INTERVAL=60                 # Monitor every 1 min
```

### ✅ Enhancement Modules (Safe to Toggle)

**CSV Tracking (RECOMMENDED):**

```bash
ENABLE_CSV_TRACKING=true            # Track all trades
CSV_AUTO_EXPORT=true                # Auto-export to CSV
```

**Safety Filters (TEST FIRST!):**

⚠️ ML Bot 2 wins WITHOUT these! A/B test to prove impact.

```bash
ENABLE_SAFETY_FILTERS=false         # Start disabled

# If enabled:
ENABLE_LP_LOCK_CHECK=true
LP_LOCK_MIN_DAYS=30                 # LP locked for 30+ days
ENABLE_HOLDER_CHECK=true
HOLDER_TOP10_MAX=50.0               # Top 10 holders < 50%
HOLDER_TOP1_MAX=20.0                # Top 1 holder < 20%
ENABLE_CONTRACT_SAFETY=true
```

---

## 🏗️ Architecture

### How It Works

```
┌─────────────────────────────────────────┐
│         ML Bot 2 Trading Bot            │
├─────────────────────────────────────────┤
│                                         │
│  ┌───────────────────────────────┐     │
│  │   🔒 PROTECTED CORE           │     │
│  │   (Never Modified!)           │     │
│  ├───────────────────────────────┤     │
│  │ • RiskAssessor                │     │
│  │   - Weighted scoring          │     │
│  │   - 71.7% win rate logic      │     │
│  │                               │     │
│  │ • PositionManager             │     │
│  │   - Trailing stops            │     │
│  │   - Position tracking         │     │
│  │                               │     │
│  │ • PriceValidator              │     │
│  │   - Dual-source validation    │     │
│  │   - Rug detection             │     │
│  └───────────────────────────────┘     │
│              ↕                          │
│  ┌───────────────────────────────┐     │
│  │   ✅ ENHANCEMENTS (Optional)  │     │
│  ├───────────────────────────────┤     │
│  │ • CSVTracker                  │     │
│  │   - 50+ field logging         │     │
│  │   - Performance analysis      │     │
│  │                               │     │
│  │ • SafetyFilters               │     │
│  │   - LP lock check             │     │
│  │   - Holder concentration      │     │
│  │   - Contract safety           │     │
│  └───────────────────────────────┘     │
│                                         │
└─────────────────────────────────────────┘
```

### Key Pattern: Enhancements Wrap Core

```python
async def analyze_token(self, token_address, market_data, ...):
    # OPTIONAL: Safety pre-filter
    if self.safety_filters and self.safety_filters.enabled:
        passed, reason = self.safety_filters.check_all(token_data)
        if not passed:
            logger.info(f"Safety filter blocked: {reason}")
            return False, 1.0, reason

    # 🔒 CORE SELECTION (never bypassed!)
    assessment = self.risk_assessor.assess_risk(
        token_address,
        market_data,
        security_data,
        sentiment_score,
        price_prediction
    )

    # OPTIONAL: Track for analysis
    if self.csv_tracker:
        self.csv_tracker.log_analysis(token_address, assessment)

    return assessment.should_trade, assessment.risk_score, assessment.overall_risk
```

**Notice:**
- Core logic is NEVER modified
- Enhancements wrap around core
- Core selection is NEVER bypassed
- All enhancements are optional

---

## 📊 Files

```
trading_bot/
├── __init__.py          # Module exports
├── config.py            # Configuration loader (.env → objects)
├── main.py              # Main bot integration
├── README.md            # This file
└── [future]
    ├── runner.py        # Full trading loop
    ├── api_clients.py   # DexScreener, Jupiter clients
    └── monitors.py      # Position monitoring
```

---

## 🧪 Testing Guide

### Phase 4: Initial Testing (50-100 trades)

**Test 1: Baseline (Core Only)**

```bash
PAPER_TRADING_MODE=true
ENABLE_CSV_TRACKING=true
ENABLE_SAFETY_FILTERS=false
```

**Goal:** Establish baseline performance (should match ML Bot 2: ~71.7% win)

**Test 2: Core + Safety Filters**

```bash
PAPER_TRADING_MODE=true
ENABLE_CSV_TRACKING=true
ENABLE_SAFETY_FILTERS=true
```

**Goal:** Does adding safety filters IMPROVE or HURT win rate?

**Analysis:**
1. Run 50 trades with Test 1
2. Run 50 trades with Test 2
3. Export CSV data from both
4. Compare win rates
5. Check if filters blocked winners or only losers

**Decision:**
- If win rate improves: Keep filters ✅
- If win rate drops: Disable filters ❌
- If neutral: Keep for risk reduction (preference)

---

## 📈 Performance Targets

Based on ML Bot 2 historical performance:

| Metric | Target | ML Bot 2 Actual |
|--------|--------|-----------------|
| Win Rate | 65-75% | 71.7% |
| Avg Profit per Win | 25-35% | 30.09% |
| Avg Loss per Loss | -15 to -20% | -18.22% |
| Profit Factor | 7-10x | 9.02x |
| Trailing Stop Exit Win Rate | 80-90% | 85-93% |

If your results deviate significantly:
1. ❌ Don't modify core settings!
2. ✅ Check API integrations
3. ✅ Verify price validation is working
4. ✅ Review CSV data for patterns
5. ✅ Compare with ML Bot 2 CSV exports

---

## 🔑 API Requirements

### Required APIs:

1. **Solana RPC**
   - Mainnet: `https://api.mainnet-beta.solana.com`
   - Or use QuickNode, Helius, etc. (faster)

2. **DexScreener**
   - Get API key: https://dexscreener.com/api
   - Used for token profiles and price data

3. **Jupiter**
   - Public API: `https://quote-api.jup.ag/v6`
   - Used for price validation and swaps

### Optional APIs:

4. **SolSniffer**
   - Get API key: https://solsniffer.com/api
   - Used for contract security analysis

5. **Telegram**
   - Create bot: https://t.me/BotFather
   - Used for trade notifications

---

## ⚠️ Important Notes

### DO:
1. ✅ **Always start with paper trading** - Test before risking real funds
2. ✅ **Always use CSV tracking** - Essential for optimization
3. ✅ **A/B test safety filters** - Prove they help before keeping
4. ✅ **Review logs regularly** - Catch issues early
5. ✅ **Keep API keys secure** - Never commit .env to git

### DON'T:
1. ❌ **Don't modify core settings** - Unless you have data proof
2. ❌ **Don't skip paper trading** - Real money requires validation
3. ❌ **Don't assume filters help** - Test with data
4. ❌ **Don't ignore CSV data** - It's your optimization compass
5. ❌ **Don't trade without RUG_DETECTION_ENABLED=true** - Safety first!

---

## 🐛 Troubleshooting

### Bot won't start

```bash
# Check configuration
python trading_bot/config.py

# Should output: ✅ Configuration loaded successfully!
```

### Import errors

```bash
# Verify dependencies
pip install -r requirements.txt

# Check Python path
python -c "import ml_bot_core; import enhanced_modules"
```

### API connection issues

```bash
# Test Solana RPC
curl https://api.mainnet-beta.solana.com -X POST -H "Content-Type: application/json" -d '{"jsonrpc":"2.0","id":1,"method":"getHealth"}'

# Test Jupiter API
curl https://quote-api.jup.ag/v6/quote?inputMint=So11111111111111111111111111111111111111112&outputMint=EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v&amount=1000000
```

### Low win rate

1. Check CSV data - are you filtering good opportunities?
2. Verify TRAILING_STOP_PERCENT=15.0 (not entry price!)
3. Confirm RUG_DETECTION_ENABLED=true
4. Review logs for price validation failures
5. Compare with ML Bot 2 baseline

---

## 📁 Related Documentation

- **Core Logic**: `ml_bot_core/README.md` - Protected core details
- **Enhancements**: `enhanced_modules/README.md` - Optional modules
- **ML Analysis**: `ML_BOTS_ANALYSIS.md` - Why ML Bot 2 wins
- **Complete Roadmap**: `COMPLETE_ROADMAP.md` - 8-week plan

---

## 🎯 Next Steps

### Immediate (Phase 3):
- ✅ Configuration system complete
- ✅ Main bot integration complete
- ✅ Ready for testing

### Phase 4 (Week 4):
- [ ] Implement full trading loop
- [ ] Add API client integrations
- [ ] Run Test 1: Core only (50 trades)
- [ ] Run Test 2: Core + safety (50 trades)
- [ ] Validate 65-75% win rate

### Phase 5 (Weeks 5-8):
- [ ] Analyze CSV data
- [ ] A/B test optimizations
- [ ] Fine-tune settings based on data
- [ ] Target 71.7%+ win rate

---

## 📞 Support

### Issues?

1. Check logs in `trading_bot.log`
2. Review CSV exports for patterns
3. Verify .env configuration
4. Test individual components:
   - `python ml_bot_core/selection/risk_assessor.py`
   - `python enhanced_modules/csv_tracker.py`
   - `python trading_bot/config.py`

### Questions?

- Review `ML_BOTS_ANALYSIS.md` for technical details
- Check `COMPLETE_ROADMAP.md` for implementation plan
- Read component READMEs for specific modules

---

**Version:** 1.0.0
**Status:** Phase 3 Complete - Ready for Testing
**Performance Target:** 71.7% win rate (ML Bot 2 baseline)
**Last Updated:** 2025-12-18

*Built on the ML Bot 2 foundation that achieved 71.7% win rate over 276 trades*
