# Solana Trading Bot

Automated trading bot for Solana meme coins and small-cap tokens using AI-driven analysis.

## Features

- 🤖 **Automated Trading**: AI-driven decision making based on market data and sentiment
- 📊 **Market Analysis**: Real-time market data from DexScreener
- 💭 **Sentiment Analysis**: Social sentiment tracking from Twitter
- 🧠 **AI Models**: Price prediction and risk assessment
- 📄 **Paper Trading**: Safe testing mode with virtual capital
- 📱 **Telegram Notifications**: Real-time trade alerts
- ⚖️ **Risk Management**: Automated stop loss and take profit

## Setup

### 1. Install Dependencies

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` and fill in your API keys:

```bash
cp .env.example .env
```

Required configuration:
- `TELEGRAM_BOT_TOKEN`: Your Telegram bot token
- `TELEGRAM_CHAT_ID`: Your Telegram chat ID
- `PAPER_TRADING_MODE=true`: Enable paper trading mode

Optional (for full functionality):
- `ALCHEMY_API_KEY`: Solana blockchain data
- `TWITTER_BEARER_TOKEN`: Social sentiment analysis
- `SOLSNIFFER_API_KEY`: Token discovery

### 3. Run the Bot

```bash
python src/main.py
```

## Paper Trading Mode

The bot starts in **paper trading mode** by default for safe testing:

- Initial virtual capital: $1,000
- Simulated trades with real market data
- No real money at risk
- Full trade logging and P&L tracking

## Configuration

Key settings in `.env`:

```env
# Trading Configuration
PAPER_TRADING_MODE=true
INITIAL_CAPITAL=1000
MAX_POSITION_SIZE=100
MIN_CONFIDENCE_SCORE=0.0

# Risk Management
STOP_LOSS_PERCENT=5
TAKE_PROFIT_PERCENT=10
SCAN_INTERVAL=60
```

## Monitoring

### Check Performance

```bash
python check_performance.py
```

### View Logs

```bash
tail -f trading_bot.log
```

### Test API Connectivity

```bash
python test_bot.py
```

## How It Works

1. **Token Discovery**: Scans for new tokens via SolSniffer or uses test tokens
2. **Market Analysis**: Fetches real-time data from DexScreener
3. **Sentiment Analysis**: Analyzes social sentiment from Twitter (if configured)
4. **AI Decision**: Price prediction and risk assessment
5. **Risk Check**: Validates trade against risk parameters
6. **Execution**: Executes trade in paper trading mode
7. **Position Management**: Monitors positions for stop loss / take profit

## Trading Logic

### Buy Signal
- Positive market signal (price momentum, volume, liquidity)
- Neutral or positive sentiment (or no sentiment data)
- Passes risk assessment
- Recommended position size > $0.05

### Sell Signal
- Stop loss triggered (default: -5%)
- Take profit triggered (default: +10%)
- Negative sentiment or market signals

## Troubleshooting

### Empty Log File

The bot writes detailed logs to `trading_bot.log`. If the file is empty:

1. Check file permissions
2. Ensure the bot is running long enough (wait 1-2 scan cycles)
3. Check console output for errors
4. Verify configuration with `python -c "from src.config.settings import validate_config; validate_config()"`

### No Trades Executing

Common reasons:
- Risk assessment too strict (adjust `MIN_CONFIDENCE_SCORE`)
- Position size too small (check `MAX_POSITION_SIZE`)
- Market conditions don't meet criteria (check logs for warnings)
- Already have positions open (bot doesn't open duplicate positions)

### API Connection Issues

If SolSniffer is down, the bot automatically falls back to test tokens:
- SOL (Wrapped Solana)
- USDC
- Bonk
- Jupiter (JUP)

## Architecture

```
src/
├── main.py                  # Main orchestrator
├── config/
│   └── settings.py          # Configuration management
├── blockchain/
│   ├── alchemy_client.py    # Solana blockchain data
│   ├── solsniffer_client.py # Token discovery
│   └── wallet_tracker.py    # Smart money tracking
├── market/
│   ├── dexscreener_client.py # Market data API
│   └── market_analyzer.py    # Technical analysis
├── social/
│   ├── twitter_client.py     # Twitter API
│   └── sentiment_analyzer.py # Sentiment analysis
├── ai/
│   ├── sentiment_model.py    # AI sentiment model
│   ├── price_predictor.py    # Price prediction
│   └── risk_assessor.py      # Risk assessment
├── trading/
│   ├── paper_trading.py      # Paper trading engine
│   ├── position_manager.py   # Position tracking
│   └── telegram_executor.py  # Live trading (future)
└── monitoring/
    ├── logger.py             # Logging system
    ├── telegram_notifier.py  # Telegram notifications
    └── health_checker.py     # Health monitoring
```

## Development

### Debug Mode

Enhanced debug output is enabled by default. Check `trading_bot.log` for detailed execution traces:

```bash
grep "EXECUTING TRADE" trading_bot.log
grep "Trade result" trading_bot.log
```

### Testing Changes

Always test in paper trading mode before enabling live trading:

```env
PAPER_TRADING_MODE=true
```

## Safety

- ⚠️ **Never share your .env file** - it contains sensitive API keys
- ⚠️ **Test in paper trading mode first** before enabling live trading
- ⚠️ **Start with small position sizes** when going live
- ⚠️ **Monitor the bot regularly** - automated trading carries risk

## License

MIT License - Use at your own risk. This bot is for educational purposes.

## Disclaimer

**Cryptocurrency trading carries significant risk. This bot is provided as-is with no guarantees. Always test thoroughly in paper trading mode and never invest more than you can afford to lose.**
