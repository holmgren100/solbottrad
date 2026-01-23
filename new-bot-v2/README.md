# Fearless Momentum Runner v2.0

**Catch 500-1700% Solana runners while preserving capital**

A momentum-based Solana trading bot that identifies explosive price movements using technical indicators and filters. Built with FREE APIs only - zero monthly costs!

## Strategy Overview

### Goal
- **Win Rate Target**: 50-60% Month 1
- **Target Gains**: Catch runners with 500-1700% potential
- **Capital Preservation**: -25% hard stop, breakeven at +50%

### Entry Logic (80-Point Scorer)

**Momentum Pattern** (need 80/100 points):
- **MACD** (40 points max): Histogram positive + growing
- **Volume** (30 points max): 400%+ spike (velocity >= 4.0x)
- **RSI** (20 points max): Sweet spot (40-70) + rising
- **Pullback** (10 points max): 1-2 red candles before entry

**Additional Checks**:
- **Trend Confirmation**: Uptrend, higher highs/lows
- **Anti-FOMO**: Block if RSI >80, 4+ green candles, or 15%+ pump
- **Safety**: LP burned + Mint revoked (BINARY - both must pass!)

### Position Management

**Entry**:
- Size: 0.1 SOL per trade (40% of capital - fearless!)
- Stop: -25% hard stop (broad - give room!)

**Breakeven** (at +50% profit):
- Sell 40% of position (recover initial investment)
- Move stop to entry +2%
- Position now RISK-FREE!

**Pyramiding**:
- At +150%: Add 30% more (if momentum still strong)
- At +300%: Add 20% more (if accelerating)

**Partial Profits**:
- At +500%: Sell 30%
- At +1000%: Sell 30%
- Moon bag: 40% rides to 1700%+ with trailing stop

## APIs Used (ALL FREE!)

| API | Use Case | Cost | Limit |
|-----|----------|------|-------|
| **Alchemy** | LP/Mint checks | FREE | 300M compute units/month |
| **Jupiter** | Prices, discovery | FREE | Unlimited |
| **DexScreener** | Market data, candles | FREE | Rate limited |
| **TOTAL** | - | **$0/month** | - |

## Project Structure

```
new-bot-v2/
├── config/
│   ├── parameters.py          # All trading parameters
│   └── apis.py                # API configurations
│
├── src/
│   ├── api/                   # API Clients
│   │   ├── alchemy_client.py  # LP/Mint checks
│   │   ├── jupiter_client.py  # Discovery, prices, swaps
│   │   └── dexscreener_client.py # Market data, candles
│   │
│   ├── indicators/            # Technical Indicators
│   │   ├── macd.py           # MACD calculator (40 points)
│   │   ├── rsi.py            # RSI calculator (20 points)
│   │   └── volume.py         # Volume analyzer (30 points)
│   │
│   ├── strategies/            # Entry Strategies
│   │   ├── momentum_entry.py  # 80-point scorer
│   │   ├── trend_confirmation.py
│   │   └── anti_fomo.py      # FOMO blocker
│   │
│   ├── filters/
│   │   └── safety_check.py   # LP + Mint (BINARY)
│   │
│   └── data/
│       └── logger.py         # CSV export for ML
│
├── data/                      # CSV outputs
│   ├── ml_trades.csv
│   └── rejected_trades.csv
│
├── tests/                     # Unit tests
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## Installation

### Prerequisites
- Python 3.9+
- pip

### Setup

1. **Clone repository**
   ```bash
   git clone https://github.com/holmgren100/solbottrad.git
   cd solbottrad/new-bot-v2
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env and add your Alchemy API key
   ```

5. **Get FREE Alchemy API Key**
   - Visit: https://www.alchemy.com/
   - Sign up for FREE account
   - Create new Solana app
   - Copy API key to `.env` file

## Configuration

### Parameters

All parameters are in `config/parameters.py`. Parameters marked with `# ADJUSTABLE` can be optimized.

**Key Parameters**:
- `MOMENTUM_SCORE_THRESHOLD = 80`: Min score to enter (0-100)
- `MACD_GROWING_STREAK_MIN = 3`: Candles for growing histogram
- `VOLUME_VELOCITY_THRESHOLD = 4.0`: 400% volume spike
- `RSI_MIN_SWEET_SPOT = 40`: RSI lower bound
- `RSI_MAX_SWEET_SPOT = 70`: RSI upper bound
- `FOMO_RSI_OVERBOUGHT = 80`: Block if RSI > this
- `ENTRY_AMOUNT_SOL = 0.1`: SOL per trade
- `HARD_STOP_LOSS_PERCENT = -25`: Stop loss

### API Configuration

Edit `config/apis.py` for API settings:
- Timeouts
- Retry logic
- Rate limits

## Usage

### Test Individual Modules

```python
# Test MACD Calculator
python -m src.indicators.macd

# Test Volume Analyzer
python -m src.indicators.volume

# Test Momentum Entry
python -m src.strategies.momentum_entry

# Test Safety Check
python -m src.filters.safety_check
```

### Run Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src tests/

# Run specific test
pytest tests/test_indicators.py -v
```

## Development

### Code Quality

```bash
# Format code
black src/ tests/

# Lint code
flake8 src/ tests/

# Type checking
mypy src/
```

### Adding New Indicators

1. Create file in `src/indicators/`
2. Implement calculation method
3. Add scoring method
4. Write tests
5. Update `MomentumEntry` to use it

## Data Logging

All trades and rejections are logged to CSV for ML analysis:

- **`data/ml_trades.csv`**: Successful trades with full details
- **`data/rejected_trades.csv`**: Rejected tokens with reasons

Use this data to:
- Train AI models
- Optimize parameters
- Analyze performance
- Identify patterns

## Phase 1 Complete ✅

**Implemented**:
- ✅ Project structure
- ✅ Config (parameters, APIs)
- ✅ API clients (Alchemy, Jupiter, DexScreener)
- ✅ Indicators (MACD, RSI, Volume)
- ✅ Strategies (Momentum, Trend, AntiFOMO)
- ✅ Safety filter (LP + Mint)
- ✅ Data logger (CSV exports)
- ✅ Requirements, env, gitignore
- ✅ Comprehensive documentation

**Next Phase**:
- Position management
- Exit logic (weakness detector, stops)
- Main orchestrator
- Live trading integration
- Backtesting framework

## Key Features

### ✅ What Makes This Bot Different

1. **FREE APIs Only**: $0/month operating cost
2. **Simple Scoring**: Binary pass/fail, no complex systems
3. **Capital Preservation**: Breakeven at +50%, hard stop at -25%
4. **Momentum Focus**: Catches big runners (500-1700%+)
5. **Anti-FOMO**: Waits for pullbacks, doesn't buy tops
6. **Data Driven**: Logs everything for ML optimization
7. **Clean Code**: Well-documented, testable, maintainable

### ❌ What We Removed

- Age-based strategies (conflicted with filters)
- Complex scoring systems (0-100 points per token)
- Multiple decision layers (simplified to 80-point threshold)
- Premium APIs (GMGN, RugCheck, etc.)

## Performance Expectations

**Month 1 Target**:
- Win rate: 50-60%
- Average win: 100-500% (with some 1000%+ runners)
- Average loss: -15% (stopped before -25%)
- Risk/Reward: Asymmetric upside

## Safety & Disclaimers

⚠️ **IMPORTANT**:
- This bot is for educational purposes
- Cryptocurrency trading involves significant risk
- Never invest more than you can afford to lose
- Past performance doesn't guarantee future results
- Always do your own research (DYOR)
- Start with small position sizes
- Test thoroughly before live trading

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/new-indicator`)
3. Write tests for new functionality
4. Ensure all tests pass (`pytest`)
5. Submit pull request

## License

MIT License - See LICENSE file

## Support

- **GitHub Issues**: https://github.com/holmgren100/solbottrad/issues
- **Documentation**: See this README and code comments
- **Strategy**: See STRATEGY.md in parent directory

## Acknowledgments

Built with:
- Alchemy Solana API
- Jupiter Aggregator
- DexScreener API
- Python ecosystem

---

**Let's catch those momentum runners! 🚀**
