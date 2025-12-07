# Telegram Notification Improvements

## Summary
Enhanced Telegram notification system to stop signal flooding and provide only vital information with comprehensive entry/exit details.

## Changes Made

### 1. Stop Buy Signal Flooding ✅

**Before**: Bot sent notifications for every token scanned (500-4000/day)
**After**: Only sends notifications for actual position entries/exits (10-40/day)

- Deprecated `send_trade_signal()` method - no longer sends scanning signals
- Created new methods that only trigger on actual trades:
  - `send_entry_notification()` - Only when entering a position
  - `send_exit_notification()` - Only when exiting a position

### 2. Priority Levels ✅

Added comprehensive priority system with emojis:

- 🔵 **DEBUG** - Debug information (disabled by default)
- 🟢 **INFO** - Normal information (entries, daily summaries)
- 🟡 **WARNING** - Warning conditions (market warnings, API issues)
- 🔴 **ERROR** - Error conditions (API failures)
- 🚨 **CRITICAL** - Critical alerts (force exits, market crashes, major losses)

### 3. Enhanced Entry Notifications ✅

New comprehensive entry messages include:
- 💰 Position size and entry price
- 📊 Token score (0-100) and confidence level
- 📍 Data source (Jupiter/DexScreener/Birdeye)
- 💧 Liquidity and volume data
- ⏰ Token age
- 🔗 Number of data sources used
- ✅ Score breakdown by factor
- 🛡️ RugCheck analysis (if available)
  - Safety score
  - Risk level
  - Top holder concentration
- 📈 Market conditions
  - Market state (normal/warning/crash)
  - SOL price and trend
- ⚠️ Warnings (up to 3 most important)

### 4. Enhanced Exit Notifications ✅

New comprehensive exit messages include:
- 💰 P&L in USD and percentage
- 📊 Outcome (WIN/LOSS/BREAKEVEN)
- 💲 Entry and exit prices
- 💼 Position size
- ⏱️ Hold time in hours
- 📝 Exit reason with emoji
  - 📈 Trailing Stop
  - 🛑 Stop Loss
  - 🎯 Take Profit
  - 🚨 Force Exit
  - 👤 Manual
  - ⏰ Max Age
  - 💧 Low Liquidity
- 💧 Liquidity changes during hold
  - Entry liquidity
  - Exit liquidity
  - Change percentage

### 5. Vital Warnings ✅

Added critical alert methods:

**Market Crash Alerts** (`send_market_crash_alert`)
- Triggers when BTC/ETH/SOL dump >10% (crash) or >5% (warning)
- Shows all three market changes
- Indicates action taken (trading stopped/reduced)
- Priority: CRITICAL or WARNING

**API Status Alerts** (`send_api_status_alert`)
- Triggers when API goes down or recovers
- Shows which API affected
- Shows error message if available
- Indicates fallback behavior
- Priority: ERROR or INFO

**Force Exit Alerts** (`send_force_exit_alert`)
- Triggers on emergency position closure
- Shows reason for force exit
- Shows liquidity drop details
  - Entry liquidity
  - Current liquidity
  - Drop percentage
- Priority: CRITICAL

### 6. New Commands ✅

**`/daily` - Daily Trade Summary (24h)**
- Total P&L for last 24 hours
- Number of trades
- Win rate
- Wins/Losses count
- Average win/loss amounts
- Exit reason breakdown
- Current open positions and available slots

**`/weekly` - Weekly Trade Analysis (7 days)**
- Total P&L for last 7 days
- Number of trades
- Win rate
- Wins/Losses count
- Best trade (highest %)
- Worst trade (lowest %)
- Daily breakdown of P&L

**`/apis` - Test All API Connections**
- Tests Jupiter API
- Tests DexScreener API
- Tests Birdeye API (if enabled)
- Tests RugCheck API (if enabled)
- Tests CoinGecko API (Market Monitor)
- Shows passed/total count
- Shows status for each API

## Files Modified

1. **src/monitoring/telegram_notifier.py**
   - Updated priority levels (added DEBUG 🔵)
   - Deprecated `send_trade_signal()` to prevent flooding
   - Added `send_entry_notification()` - comprehensive entry messages
   - Added `send_exit_notification()` - comprehensive exit messages
   - Added `send_market_crash_alert()` - market crash warnings
   - Added `send_api_status_alert()` - API status notifications
   - Added `send_force_exit_alert()` - force exit alerts

2. **src/monitoring/telegram_commands.py**
   - Added `cmd_daily()` - daily summary command
   - Added `cmd_weekly()` - weekly analysis command
   - Added `cmd_apis()` - API test command
   - Updated `cmd_help()` - added new commands
   - Registered new command handlers

## Expected Results

### Before
- 500-4000 Telegram messages per day (mostly scanning signals)
- Minimal information in entry/exit messages
- No market crash warnings
- No API status monitoring
- Manual calculation needed for daily/weekly summaries

### After
- 10-40 Telegram messages per day (only actual trades + vital alerts)
- Comprehensive entry/exit messages with all relevant data
- Automatic market crash detection and alerts
- API status monitoring with alerts
- Commands for daily/weekly summaries on demand

## Usage Examples

### Entry Notification
```
🟢 ENTERED: BONK 📈
━━━━━━━━━━━━━━━━
💰 Position: $35.00
💲 Entry: $0.00001234
📊 Score: 75/100 (high)

📍 Source: JUPITER
💧 Liquidity: $125,000 (high)
📈 Volume 24h: $450,000
⏰ Age: 2.3h
🔗 Data: 3 sources

✅ Score Breakdown:
  • liquidity: 50 pts
  • confidence: 15 pts
  • volume: 15 pts
  • rugcheck: 20 pts
  • market: 10 pts

🛡️ RugCheck:
  • Safety: 85/100
  • Risk: low
  • Top 10: 35.2%

📈 Market: NORMAL
  • SOL: $102.34 (+2.3%)

🔗 jG8r3K2...9xLm
```

### Exit Notification
```
🟢 EXITED: BONK 📈
━━━━━━━━━━━━━━━━
💰 P&L: +$12.50 (+35.71%)
📊 Outcome: WIN

💲 Entry: $0.00001234
💲 Exit: $0.00001674
💼 Size: $35.00
⏱️ Hold: 3.2h
📝 Reason: Trailing Stop

💧 Liquidity:
  • Entry: $125,000
  • Exit: $138,500
  • Change: +10.8%

🔗 jG8r3K2...9xLm
```

### Force Exit Alert
```
🚨 FORCE EXIT: BONK

Position force closed due to:
Critical liquidity drop

💧 Liquidity:
  • Entry: $125,000
  • Current: $28,000
  • Drop: 78%

🔗 jG8r3K2...9xLm
```

### Market Crash Alert
```
🚨 MARKET CRASH DETECTED

Major crypto markets dumping:
  • BTC: -12.3%
  • ETH: -14.1%
  • SOL: -18.7%

🛡️ Action: Trading STOPPED
💡 All positions being monitored closely
```

### Daily Summary (`/daily`)
```
📊 Daily Summary (24h)
━━━━━━━━━━━━━━━━

💰 Performance
Total P&L: +$45.20
Total Trades: 12
Win Rate: 58.3%
Wins/Losses: 7/5

🟢 Average Win: $15.30
🔴 Average Loss: -$8.50

📝 Exit Reasons
  • Trailing Stop: 7
  • Low Liquidity: 3
  • Stop Loss: 2

📈 Current
Open Positions: 3
Available Slots: 2
```

### API Test (`/apis`)
```
🔧 API Status Report
━━━━━━━━━━━━━━━━

✅ Passed: 5/5

🟢 Jupiter: Online
🟢 DexScreener: Online
🟢 RugCheck: Online
🟢 CoinGecko: Online
🟢 Birdeye: Online

💡 If APIs are down, bot will use fallback sources
```

## Integration Notes

To use the new notification methods in your bot:

```python
# Entry notification (instead of send_trade_signal)
await notifier.send_entry_notification(
    token_address=token_address,
    symbol=symbol,
    entry_price=entry_price,
    position_size=position_size,
    score=score_result['score'],
    confidence=score_result['confidence'],
    token_data=token_data,
    rugcheck_data=rugcheck_data,
    market_data=market_data,
    score_breakdown=score_result['breakdown'],
    warnings=score_result['warnings'],
    is_pumpfun=score_result['is_pumpfun']
)

# Exit notification
await notifier.send_exit_notification(
    token_address=token_address,
    symbol=symbol,
    entry_price=entry_price,
    exit_price=exit_price,
    position_size=position_size,
    pnl=pnl,
    pnl_percent=pnl_percent,
    hold_time_hours=hold_time_hours,
    exit_reason=exit_reason,
    liquidity_change={
        'entry': entry_liquidity,
        'exit': exit_liquidity,
        'change_percent': change_percent
    }
)

# Market crash alert
await notifier.send_market_crash_alert(
    btc_change=btc_1h_change,
    eth_change=eth_1h_change,
    sol_change=sol_1h_change,
    market_state='crash'  # or 'warning'
)

# API status alert
await notifier.send_api_status_alert(
    api_name='Jupiter',
    status='down',  # or 'recovered'
    error_message='Connection timeout'
)

# Force exit alert
await notifier.send_force_exit_alert(
    token_address=token_address,
    symbol=symbol,
    reason='Critical liquidity drop',
    entry_liquidity=entry_liquidity,
    current_liquidity=current_liquidity,
    drop_percent=drop_percent
)
```

## Testing Checklist

- [ ] Test `/daily` command with real trade data
- [ ] Test `/weekly` command with real trade data
- [ ] Test `/apis` command to verify all APIs
- [ ] Verify entry notifications only send on actual entries
- [ ] Verify exit notifications show correct P&L and liquidity changes
- [ ] Test market crash alert triggers correctly
- [ ] Test API down/recovered alerts
- [ ] Test force exit alerts
- [ ] Verify old `send_trade_signal` no longer floods
- [ ] Confirm message count reduced from 500-4000/day to 10-40/day
