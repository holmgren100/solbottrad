# Solana Trading Bot (Taskmaster)

An advanced automated trading bot for meme coins and small-cap tokens on the Solana blockchain. The bot leverages AI models, real-time market data, and social sentiment analysis to make informed trading decisions with minimal human intervention.

## Features

### Blockchain Data Integration
- Real-time monitoring via Alchemy API
- WebSocket connections for transaction updates
- Wallet activity tracking for "smart money" analysis
- Token discovery through SolSniffer API

### Market Monitoring
- Price and volume tracking via DexScreener API
- Liquidity assessment for safe trading
- Multi-DEX support on Solana
- Market volatility analysis

### Social Sentiment Analysis
- Twitter API integration for social media monitoring
- Sentiment scoring of cryptocurrency discussions
- Trend identification and buzz detection
- Detection of coordinated pump schemes

### AI-Powered Decision Making
- Sentiment analysis model for scoring social signals
- Price prediction using technical indicators
- Comprehensive risk assessment system
- Adaptive learning from trading performance

### Trading Execution
- Integration with GMGN bot via Telegram
- Support for buy/sell operations
- Intelligent position sizing
- Stop loss and take profit automation

### Monitoring & Alerts
- Real-time status updates via Telegram
- Comprehensive logging system
- Component health checks
- Error alerting for critical issues

### Paper Trading Mode
- Risk-free strategy testing
- Simulated portfolio tracking
- Performance evaluation and reporting
- Full trade history

## Installation

### Prerequisites
- Python 3.9 or higher
- Telegram account
- API keys (see Configuration section)

### Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd solbottrad
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your API keys and configuration
```

## Configuration

### Required API Keys

1. **Alchemy API Key** (Required)
   - Sign up at [alchemy.com](https://www.alchemy.com/)
   - Create a Solana Mainnet app
   - Copy the API key to `.env`

2. **Telegram Bot Token** (Required)
   - Message [@BotFather](https://t.me/BotFather) on Telegram
   - Create a new bot with `/newbot`
   - Copy the token to `.env`

3. **Telegram Chat ID** (Required)
   - Message [@userinfobot](https://t.me/userinfobot) on Telegram
   - Copy your chat ID to `.env`

### Optional API Keys

4. **Twitter Bearer Token** (Recommended)
   - Apply for developer access at [developer.twitter.com](https://developer.twitter.com/)
   - Create a project and app
   - Generate Bearer Token

5. **SolSniffer API Key** (Optional)
   - Visit [solsniffer.com](https://solsniffer.com/)
   - Sign up for an API key

6. **DexScreener API Key** (Optional)
   - Free tier available at [dexscreener.com](https://dexscreener.com/)

### Trading Configuration

Edit `.env` to configure trading parameters:

```env
# Paper trading mode (recommended for testing)
PAPER_TRADING_MODE=true

# Position sizing
MAX_POSITION_SIZE=100          # Maximum $100 per trade
MIN_LIQUIDITY_USD=10000        # Minimum $10k liquidity

# Risk management
STOP_LOSS_PERCENT=20           # 20% stop loss
TAKE_PROFIT_PERCENT=50         # 50% take profit
MAX_OPEN_POSITIONS=5           # Maximum 5 simultaneous positions

# Confidence threshold
MIN_CONFIDENCE_SCORE=0.7       # Minimum 70% confidence to trade
```

## Usage

### Start the Bot

```bash
python -m src.main
```

### Paper Trading Mode (Recommended)

Start with paper trading to test strategies without risk:

```env
PAPER_TRADING_MODE=true
```

The bot will:
- Simulate all trades
- Track virtual portfolio performance
- Log all decisions and outcomes
- Send Telegram notifications

### Live Trading Mode (Use with Caution)

When ready for live trading:

```env
PAPER_TRADING_MODE=false
```

**Important Notes:**
- Start with small position sizes
- Monitor the bot closely
- The bot will send trade signals via Telegram
- Manual execution required through GMGN bot
- Review all trades before executing

## Architecture

```
src/
├── blockchain/          # Blockchain data integration
│   ├── alchemy_client.py
│   ├── solsniffer_client.py
│   └── wallet_tracker.py
├── market/              # Market data and analysis
│   ├── dexscreener_client.py
│   └── market_analyzer.py
├── social/              # Social sentiment analysis
│   ├── twitter_client.py
│   └── sentiment_analyzer.py
├── ai/                  # AI decision models
│   ├── sentiment_model.py
│   ├── price_predictor.py
│   └── risk_assessor.py
├── trading/             # Trade execution
│   ├── telegram_executor.py
│   ├── position_manager.py
│   └── paper_trading.py
├── monitoring/          # Monitoring and alerts
│   ├── logger.py
│   ├── telegram_notifier.py
│   └── health_checker.py
├── config/              # Configuration management
│   └── settings.py
└── main.py             # Main orchestrator
```

## How It Works

1. **Token Discovery**: Monitors new token launches via SolSniffer
2. **Data Collection**: Gathers market data, social sentiment, and security info
3. **Analysis**: AI models analyze all data points
4. **Risk Assessment**: Comprehensive risk evaluation
5. **Decision Making**: Determines if trade meets criteria
6. **Execution**: Executes trade (paper or live)
7. **Monitoring**: Tracks positions for stop loss/take profit
8. **Reporting**: Sends updates via Telegram

## Trading Strategy

The bot uses a multi-factor approach:

### Market Analysis (30%)
- Price action and volume
- Liquidity depth
- Volatility assessment

### Sentiment Analysis (30%)
- Social media buzz
- Sentiment polarity
- Influential user activity

### Technical Prediction (20%)
- Price trend analysis
- Volume patterns
- Historical performance

### Risk Assessment (20%)
- Security audit results
- Token age and history
- Coordination detection

## Safety Features

- **Paper Trading**: Test strategies without risk
- **Position Limits**: Maximum position and exposure caps
- **Risk Assessment**: Every trade evaluated for risk
- **Stop Loss**: Automatic loss protection
- **Confidence Threshold**: Only high-confidence trades
- **Manual Execution**: Final approval for live trades
- **Health Monitoring**: Component status tracking
- **Error Handling**: Graceful failure recovery

## Monitoring

### Telegram Notifications

The bot sends:
- Startup/shutdown messages
- Trade signals with analysis
- Execution confirmations
- Stop loss/take profit triggers
- Error alerts
- Performance summaries

### Logs

Check `trading_bot.log` for:
- Detailed operation logs
- Error traces
- Trading decisions
- Analysis results

## Performance Metrics

View performance with:
```python
# Paper trading performance
performance = bot.trading_engine.get_performance_summary()
```

Metrics include:
- Total P&L
- Win rate
- Average win/loss
- Portfolio value
- Trade statistics

## Troubleshooting

### Common Issues

1. **API Key Errors**
   - Verify all required keys in `.env`
   - Check key validity with providers

2. **No Trades Executing**
   - Check `MIN_CONFIDENCE_SCORE` setting
   - Review `MIN_LIQUIDITY_USD` threshold
   - Verify `PAPER_TRADING_MODE` setting

3. **Telegram Not Working**
   - Verify bot token and chat ID
   - Test with `/start` command to bot
   - Check bot permissions

4. **Rate Limiting**
   - Reduce scan frequency
   - Upgrade API tier if needed
   - Monitor API usage

## Disclaimer

**IMPORTANT: Use at your own risk!**

- Cryptocurrency trading is highly risky
- Past performance doesn't guarantee future results
- Only invest what you can afford to lose
- This bot is for educational purposes
- Test thoroughly in paper trading mode
- Monitor all trades closely
- No guarantee of profits

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

This project is provided as-is for educational purposes.

## Support

For issues and questions:
- Check the documentation
- Review logs for errors
- Test in paper trading mode first
- Consult the codebase comments

## Roadmap

Future enhancements:
- [ ] Advanced backtesting framework
- [ ] Enhanced ML models
- [ ] Additional data sources
- [ ] Mobile app for monitoring
- [ ] Multi-chain support
- [ ] Performance visualization dashboard

---

**Happy Trading! Remember: Always test in paper trading mode first!**
