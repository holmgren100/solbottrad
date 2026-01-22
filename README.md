# Solana Trading Bot v2.0

A simple, effective Solana trading bot using binary pass/fail filters. Based on analysis of 774 historical trades achieving **71.4% win rate** (November 2024 version).

## Strategy Overview

### Goal
60%+ win rate through simple, clear decision logic

### What We Learned (From 774 Trades)
- ✅ TIER 2 filters work: `MIN_PRICE=0.10`, `MAX_TOKENS_PER_DOLLAR=10000`
- ✅ Binary pass/fail is better than complex scoring
- ❌ Age-based logic conflicts with filters → **REMOVED**
- ❌ 100-point scoring system too complex → **REMOVED**

## Decision Logic

```
if Safety_Checks_Pass AND Performance_Checks_Pass:
    TRADE
else:
    REJECT (with logged reason)
```

**No age-based strategies. No scoring systems. Simple binary decisions.**

## Filters

### TIER 1: Safety Checks (All Must Pass)
- **Token price**: 0.10 to 1.0 SOL
- **Liquidity**: Minimum $50,000
- **Security score**: Minimum 80/100
- **Contract verified**: YES

### TIER 2: Performance Checks (All Must Pass)
- **Volume/Liquidity ratio**: 0.3 to 0.8 (optimal range from data)
- **Max tokens per dollar**: 10,000
- **Top holder concentration**: Maximum 20%

## Position Management

- **Entry size**: 0.1 SOL per trade
- **Take profit**: +15%
- **Stop loss**: -8%
- **Max hold time**: 4 hours

## Project Structure

```
solbottrad/
├── src/
│   ├── filters/
│   │   ├── tier1_safety.py       # TIER 1 safety filters
│   │   └── tier2_performance.py  # TIER 2 performance filters
│   ├── decision_engine.py        # Simple pass/fail decision logic
│   └── main.py                   # Bot entry point
├── tests/
│   └── test_filters.py           # Comprehensive filter tests
├── config/
│   └── settings.yaml             # Configuration parameters
├── logs/                         # Bot logs (created at runtime)
├── requirements.txt              # Python dependencies
├── setup.py                      # Package setup
├── STRATEGY.md                   # Strategy documentation
└── README.md                     # This file
```

## Installation

### Prerequisites
- Python 3.9 or higher
- pip package manager

### Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/holmgren100/solbottrad.git
   cd solbottrad
   ```

2. **Create virtual environment** (recommended)
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Install package in development mode**
   ```bash
   pip install -e .
   ```

## Configuration

Edit `config/settings.yaml` to customize filter parameters:

```yaml
tier1:
  min_price: 0.10
  max_price: 1.0
  min_liquidity: 50000
  min_security_score: 80

tier2:
  min_volume_liquidity_ratio: 0.3
  max_volume_liquidity_ratio: 0.8
  max_tokens_per_dollar: 10000
  max_top_holder_percent: 20

position:
  entry_size: 0.1
  take_profit_percent: 15
  stop_loss_percent: 8
  max_hold_hours: 4
```

## Usage

### Run the bot
```bash
python -m src.main
```

### Run tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src tests/

# Run specific test file
pytest tests/test_filters.py -v
```

## Logging

The bot provides comprehensive logging:

- **Console output**: Real-time decisions and statistics
- **Log files**: Stored in `logs/` directory with timestamps
- **Decision tracking**: Why each token was accepted or rejected

Example log output:
```
============================================================
Running TIER 1 Safety Checks for TEST1
============================================================
✅ Price check passed: 0.1500 SOL
✅ Liquidity check passed: $75,000
✅ Security check passed: 85/100
✅ Contract verification passed
✅ TEST1 PASSED all TIER 1 safety checks

============================================================
Running TIER 2 Performance Checks for TEST1
============================================================
✅ V/L ratio check passed: 0.533
✅ Tokens per dollar check passed: 66
✅ Top holder check passed: 15.0%
✅ TEST1 PASSED all TIER 2 performance checks

============================================================
✅ DECISION: TRADE TEST1
   Entry Size: 0.1 SOL
   Entry Price: 0.150000 SOL
   Take Profit: +15%
   Stop Loss: -8%
   Max Hold: 4 hours
============================================================
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

### Adding New Filters

1. Add filter function to `tier1_safety.py` or `tier2_performance.py`
2. Follow the pattern: return `Tuple[bool, str]` (passed, reason)
3. Add to `run_all_checks()` method
4. Write tests in `tests/test_filters.py`

Example:
```python
def check_new_metric(self, token_data: Dict) -> Tuple[bool, str]:
    """Check new metric."""
    value = token_data.get('new_metric', 0)

    if value < self.threshold:
        reason = f"New metric too low: {value}"
        logger.info(f"❌ REJECTED - {reason}")
        return False, reason

    logger.debug(f"✅ New metric check passed: {value}")
    return True, f"New metric OK: {value}"
```

## What Was Removed

This v2.0 removes complexity from previous versions:

- ❌ **Age-based strategies**: Created conflicts with filters
- ❌ **Scoring systems**: 0-100 point systems were too complex
- ❌ **Multiple decision layers**: Simplified to single binary decision

## Performance Metrics

Based on historical analysis (774 trades):

- **Win Rate**: 71.4% (November 2024 version)
- **Target Win Rate**: 60%+
- **Key Success Factors**:
  - MIN_PRICE filter (0.10 SOL)
  - MAX_TOKENS_PER_DOLLAR filter (10,000)
  - Volume/Liquidity ratio in optimal range

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/new-filter`)
3. Write tests for new functionality
4. Ensure all tests pass (`pytest`)
5. Submit a pull request

## License

MIT License - See LICENSE file for details

## Disclaimer

**This bot is for educational purposes only.** Cryptocurrency trading involves significant risk. Past performance (71.4% win rate) does not guarantee future results. Always do your own research and never invest more than you can afford to lose.

## Support

For issues and questions:
- GitHub Issues: https://github.com/holmgren100/solbottrad/issues
- Strategy Documentation: See `STRATEGY.md`

## Version History

### v2.0.0 (Current)
- Simplified to binary pass/fail filters
- Removed age-based logic
- Removed scoring systems
- Added comprehensive logging
- Based on 71.4% win rate strategy

### v1.0.0 (November 2024)
- Initial version with 71.4% win rate
- Complex scoring system
- Age-based strategies
