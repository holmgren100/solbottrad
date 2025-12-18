# 🚀 Quick Start Guide

## ✅ **Your Bot is Ready!**

You have a fully functional Solana trading bot with multiple ways to monitor and control it.

---

## 📱 **1. Telegram Commands (Recommended)**

The easiest way to control your bot - works from anywhere, including your phone!

### Start the Bot:
```bash
cd C:\Users\fiske\solbottrad
venv\Scripts\activate
python -m src.main
```

### Use These Commands in Telegram:

| Command | What It Does |
|---------|-------------|
| `/status` | View portfolio, positions, and P&L |
| `/settings` | Show all bot settings |
| `/stop_loss 15` | Change stop loss to 15% |
| `/take_profit 40` | Change take profit to 40% |
| `/pause` | Pause new trades (monitoring continues) |
| `/resume` | Resume trading |
| `/close So111111` | Close a specific position |
| `/help` | Show all commands |

**Example:**
```
You send: /status

Bot replies:
📊 Trading Bot Status

💰 Portfolio
Total Value: $1,045.20
Cash: $819.72
Invested: $180.28
P&L: $45.20 (+4.52%)

📈 Open Positions (3)
🟢 So111111...
   Entry: $139.98
   Current: $142.50
   P&L: +1.80%
```

---

## 🖥️ **2. Terminal Monitor**

Visual monitoring in your terminal with colors and auto-refresh.

### Open a New Terminal:
```bash
cd C:\Users\fiske\solbottrad
venv\Scripts\activate
python monitor.py
```

### What You'll See:
```
======================================================================
          🤖 SOLANA TRADING BOT - LIVE MONITOR
======================================================================
Last updated: 2025-11-19 15:30:45

📊 BOT STATUS
──────────────────────────────────────────────────────────────────────
Mode: 📄 Paper Trading
Stop Loss: 20%
Take Profit: 50%
Max Position: $100.0

💰 PORTFOLIO
──────────────────────────────────────────────────────────────────────
Initial Capital: $1000.00
Cash Available:  $819.72
Invested:        $180.28
Total Value:     $1000.00

📈 OPEN POSITIONS (3)
──────────────────────────────────────────────────────────────────────
⚪ So111111...
   Entry: $139.98 | Size: $60.96
   Current: $139.98 | P&L: +0.00%
```

**Features:**
- ✅ Color-coded (green profits, red losses)
- ✅ Auto-refreshes every 10 seconds
- ✅ Shows recent trades
- ✅ Press Ctrl+C to exit

---

## 🌐 **3. HTML Dashboard**

Simple web page you can open in your browser.

### How to Use:
1. **Navigate to the folder:**
   ```bash
   cd C:\Users\fiske\solbottrad
   ```

2. **Double-click `dashboard.html`** or right-click and "Open with Chrome/Firefox/Edge"

### What You'll See:
- Beautiful web interface
- Portfolio stats with cards
- Instructions for getting live data

**Note:** This is a static HTML file. It will be fully functional when we add Flask later. For now, use Telegram or the Terminal Monitor for live data.

---

## 📊 **4. Check Performance**

See your trading statistics:

```bash
python check_performance.py
```

Shows:
- Total trades (buys and sells)
- Win/loss ratio
- Average P&L
- Current positions

---

## 📁 **5. View Logs**

All activity is logged to `trading_bot.log`:

```bash
# View entire log
type trading_bot.log

# View last 20 lines
powershell "Get-Content trading_bot.log -Tail 20"

# Watch live
powershell "Get-Content trading_bot.log -Wait -Tail 10"
```

---

## 🎯 **Typical Workflow**

### Daily Operation:

1. **Start the bot** (morning):
   ```bash
   python -m src.main
   ```

2. **Open terminal monitor** (optional, for visual monitoring):
   ```bash
   python monitor.py
   ```

3. **Check status from your phone** throughout the day:
   - Send `/status` in Telegram
   - Get notifications when trades happen

4. **Adjust settings** if needed:
   - `/stop_loss 18` to change stop loss
   - `/pause` if you want to stop trading temporarily

5. **Let it run!** The bot will:
   - Scan for opportunities every 5 minutes
   - Monitor positions every 1 minute
   - Auto-sell on stop loss or take profit
   - Notify you of all actions

---

## 🔧 **Common Tasks**

### Change Stop Loss:
```
Telegram: /stop_loss 15
```

### Change Take Profit:
```
Telegram: /take_profit 40
```

### Pause Trading (keep monitoring):
```
Telegram: /pause
```

### Close a Position Manually:
```
Telegram: /close So111111
```

### Check if Bot is Running:
- Look for the terminal window running `python -m src.main`
- Or check log file: `type trading_bot.log`
- Or send `/status` in Telegram

---

## ⚠️ **Important Notes**

1. **Keep Computer On:** The bot needs to run continuously. If computer sleeps, bot stops.

2. **Paper Trading:** Currently in paper trading mode ($1000 virtual). No real money at risk!

3. **Log File:** All activity saved to `trading_bot.log` - check it if something seems wrong

4. **Telegram is Your Friend:** Most convenient way to monitor and control the bot

5. **API Limitations:**
   - SolSniffer is down → Using test tokens (SOL, USDC, Bonk, Jupiter)
   - Twitter disabled → Trading on market signals only
   - This is fine for testing!

---

## 🆘 **Troubleshooting**

### Bot Not Starting?
1. Make sure you're in the right directory: `cd C:\Users\fiske\solbottrad`
2. Activate venv: `venv\Scripts\activate`
3. Check .env file has required keys

### Telegram Commands Not Working?
1. Make sure bot is running (`python -m src.main`)
2. Check your chat ID in .env matches your Telegram

### No Positions Opening?
- Bot scans every 5 minutes - be patient!
- Check if trading is paused: `/settings` in Telegram
- Positions may already be open - check `/status`

### Monitor Not Showing Data?
- Make sure bot has been running and made trades
- Data comes from `trading_bot.log` file
- Use Telegram `/status` for real-time data

---

## 🎉 **You're All Set!**

**Recommended Setup:**
1. ✅ Start bot: `python -m src.main`
2. ✅ Keep Telegram open for notifications
3. ✅ Check `/status` whenever you want
4. ✅ Let it trade!

**Everything Else is Optional:**
- Terminal monitor for visual
- HTML dashboard (will enhance later with Flask)
- Log file for detailed history

**The bot is now trading automatically! 🤖📈**
