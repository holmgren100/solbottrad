# 🎛️ Dashboard & Control Guide

This guide explains how to use the **Telegram Commands** and **Streamlit Dashboard** to control and monitor your trading bot.

---

## 📱 Telegram Commands

The bot now responds to commands in Telegram, allowing you to control it from anywhere!

### Available Commands

#### 📊 Status & Information

- **`/status`** - View portfolio value, open positions, and P&L
- **`/settings`** - Display current bot settings
- **`/help`** - Show all available commands

#### ⚙️ Settings Control

- **`/stop_loss <percentage>`** - Change stop loss percentage
  - Example: `/stop_loss 15` (sets stop loss to 15%)
  - Range: 0-50%

- **`/take_profit <percentage>`** - Change take profit percentage
  - Example: `/take_profit 40` (sets take profit to 40%)
  - Range: 0-200%

#### 🎮 Trading Controls

- **`/pause`** - Pause new trades (monitoring continues)
- **`/resume`** - Resume trading
- **`/close <token_address>`** - Manually close a position
  - Example: `/close So111111` (closes SOL position)
  - You can use just the first 8 characters of the token address

### Usage Examples

```
You: /status

Bot:
📊 Trading Bot Status

💰 Portfolio
Total Value: $1,045.20
Cash: $819.72
Invested: $180.28
P&L: $45.20 (+4.52%)

📈 Open Positions (3)
🟢 So111111...
   Entry: $139.98000000
   Current: $142.50000000
   P&L: +1.80%
   Size: $60.96
...
```

```
You: /stop_loss 18

Bot: ✅ Stop loss updated to 18%
```

```
You: /pause

Bot: ⏸️ Trading paused. Monitoring continues.
```

---

## 🖥️ Streamlit Dashboard

A web-based dashboard for visual monitoring and analytics.

### Starting the Dashboard

1. **Open a new terminal/command prompt**
2. **Navigate to the bot directory:**
   ```bash
   cd C:\Users\fiske\solbottrad
   ```

3. **Activate virtual environment:**
   ```bash
   venv\Scripts\activate
   ```

4. **Install dashboard dependencies (first time only):**
   ```bash
   pip install streamlit plotly
   ```

5. **Start the dashboard:**
   ```bash
   streamlit run dashboard.py
   ```

6. **Open your browser** - Streamlit will automatically open at `http://localhost:8501`

### Dashboard Features

#### 📊 Portfolio Tab
- Real-time portfolio value
- Cash vs invested breakdown
- Total P&L and returns
- Portfolio composition pie chart

#### 📈 Positions Tab
- List of all open positions
- Color-coded P&L (green = profit, red = loss)
- Entry/current prices
- Stop loss and take profit levels
- Position details with expandable cards

#### 📜 Activity Log Tab
- Recent buy/sell trades
- Color-coded by type (buy, sell, stop loss, take profit)
- Full log file viewer (expandable)

#### 📉 Performance Tab
- Total trades and win rate
- Average win/loss amounts
- Portfolio value chart over time
- Trade distribution statistics

### Dashboard Controls

- **🔄 Refresh Data** - Reload latest data from bot
- Auto-refreshes every 30 seconds
- View current settings in sidebar
- Link to Telegram commands for modifications

---

## 🔄 Workflow: Using Both Together

**Recommended setup:**

1. **Keep the bot running** in one terminal
   ```bash
   python -m src.main
   ```

2. **Open the dashboard** in another terminal
   ```bash
   streamlit run dashboard.py
   ```

3. **Use Telegram** for:
   - Quick status checks (from your phone)
   - Changing settings on the fly
   - Pausing/resuming trading
   - Closing positions manually

4. **Use the Dashboard** for:
   - Deep-dive analytics
   - Visual monitoring
   - Performance tracking
   - Full activity history

---

## 🔒 Security Notes

- Only **your authorized Telegram chat ID** can send commands
- Commands from other users will be rejected with "⛔ Unauthorized"
- The dashboard runs locally on your machine
- No external access unless you configure port forwarding

---

## 🆘 Troubleshooting

### Telegram Commands Not Working

1. **Check bot is running** - The main bot must be running for commands to work
2. **Verify chat ID** - Make sure your .env has the correct `TELEGRAM_CHAT_ID`
3. **Check logs** - Look for "Telegram command handler started" in logs

### Dashboard Shows No Data

1. **Bot must be running** - Dashboard reads from log file created by bot
2. **Check log file exists** - Look for `trading_bot.log` in bot directory
3. **Refresh data** - Click the refresh button in sidebar
4. **Wait for trades** - Some data only appears after trades are executed

### Dashboard Won't Start

1. **Install dependencies:**
   ```bash
   pip install streamlit plotly
   ```

2. **Check port 8501** - Make sure nothing else is using this port
3. **Try a different port:**
   ```bash
   streamlit run dashboard.py --server.port 8502
   ```

---

## 📱 Quick Reference Card

| Task | Command | Example |
|------|---------|---------|
| Check status | `/status` | - |
| View settings | `/settings` | - |
| Change stop loss | `/stop_loss <pct>` | `/stop_loss 15` |
| Change take profit | `/take_profit <pct>` | `/take_profit 40` |
| Pause trading | `/pause` | - |
| Resume trading | `/resume` | - |
| Close position | `/close <token>` | `/close So111111` |
| Open dashboard | `streamlit run dashboard.py` | - |
| Refresh dashboard | Click 🔄 button | - |

---

**💡 Pro Tip:** Keep the dashboard open on a second monitor while watching Telegram notifications on your phone for the ultimate trading bot experience!
