# 🚀 LIVE TRADING DEPLOYMENT GUIDE

## ⚠️ CRITICAL: READ BEFORE DEPLOYING

This guide will help you deploy the trading bot to Digital Ocean for **Phase 0 live testing** with **$1-4 positions**.

---

## 📋 PRE-DEPLOYMENT CHECKLIST

Before you start, ensure you have:

- [ ] **~$100 in SOL** in your trading wallet
- [ ] **Wallet private key** ready (keep secure!)
- [ ] **Digital Ocean droplet** running Ubuntu
- [ ] **Telegram bot configured** and working
- [ ] **All API keys** from paper trading setup
- [ ] **Backup** of paper trading version saved

---

## 🎯 PHASE 0 CONFIGURATION

**Ultra-Conservative Settings for Initial Testing:**

```env
PAPER_TRADING_MODE=false          # LIVE MODE
DEFAULT_POSITION_SIZE=2.0         # $2 average
MAX_POSITION_SIZE=4.0             # $4 hard cap
MAX_OPEN_POSITIONS=5              # Only 5 positions
```

**Expected Phase 0 Results:**
- Duration: 1-2 hours
- Trades: 5-10 trades
- Capital at risk: $20 max (5 positions × $4)
- Expected profit: $1-3 if matches paper trading

---

## 📦 DEPLOYMENT STEPS

### Step 1: Connect to Digital Ocean

```bash
ssh root@your-droplet-ip
```

### Step 2: Backup Existing Bot (if any)

```bash
# Check if old bot exists
ls -la | grep sol

# Backup old version
mv solbottrad solbottrad-backup-$(date +%Y%m%d) 2>/dev/null || echo "No existing bot"
```

### Step 3: Clone Live Trading Version

```bash
# Clone repository
git clone https://github.com/holmgren100/solbottrad.git
cd solbottrad

# Checkout live trading branch
git checkout live-trading-v1.0-micro
git pull origin live-trading-v1.0-micro
```

### Step 4: Configure Environment

```bash
# Copy .env template
cp .env.example .env

# Edit .env file
nano .env
```

**CRITICAL CHANGES TO MAKE IN .ENV:**

```env
# Change from paper to live
PAPER_TRADING_MODE=false

# Phase 0 position sizing
DEFAULT_POSITION_SIZE=2.0
MAX_POSITION_SIZE=4.0
MAX_OPEN_POSITIONS=5

# Add your wallet private key
SOLANA_PRIVATE_KEY=your_actual_private_key_here

# Verify RPC URL
SOLANA_RPC_URL=https://solana-mainnet.g.alchemy.com/v2/YOUR_KEY

# Keep all protection systems enabled (already configured)
AUTO_CLEANUP_ENABLED=true
FORCE_CLOSE_ON_RUG=true
MIN_ENTRY_LIQUIDITY=30000
MIN_EXIT_LIQUIDITY=15000
MIN_ENTRY_PRICE=0.10
MAX_TOKENS_PER_DOLLAR=10000
```

**Save file:**
- Press `CTRL+X`
- Press `Y`
- Press `ENTER`

### Step 5: Install Dependencies

```bash
# Update system
apt update
apt install python3-pip python3-venv -y

# Create virtual environment
python3 -m venv venv

# Activate venv
source venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

### Step 6: Test Configuration

```bash
# Quick test run
python -m src.main &
sleep 10

# Check logs
tail -50 bot_output.log

# Look for:
# ✅ "PAPER_TRADING_MODE=false" or "Live mode"
# ✅ "Position size: $1-4"
# ✅ "All protection systems enabled"
# ❌ No critical errors

# Stop test
pkill -f "python.*main"
```

### Step 7: Start Bot as Service (Recommended)

```bash
# Create systemd service
nano /etc/systemd/system/solana-bot.service
```

**Paste this configuration:**

```ini
[Unit]
Description=Solana Trading Bot - Live Phase 0
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/solbottrad
Environment="PATH=/root/solbottrad/venv/bin"
ExecStart=/root/solbottrad/venv/bin/python -m src.main
Restart=always
RestartSec=10
StandardOutput=append:/root/solbottrad/bot_output.log
StandardError=append:/root/solbottrad/bot_output.log

[Install]
WantedBy=multi-user.target
```

**Save and start service:**

```bash
# Reload systemd
systemctl daemon-reload

# Enable service
systemctl enable solana-bot

# Start bot
systemctl start solana-bot

# Check status
systemctl status solana-bot
```

---

## 📊 MONITORING PHASE 0

### Via Logs

```bash
# Follow logs in real-time
tail -f /root/solbottrad/bot_output.log

# View recent errors
grep -i error /root/solbottrad/bot_output.log | tail -20

# Check bot status
systemctl status solana-bot
```

### Via Telegram

Use these commands to monitor:

- `/status` - Current positions and portfolio
- `/settings` - Bot configuration
- `/cleanup` - Force cleanup stuck positions
- `/closeall` - Emergency: close all positions

---

## 🎯 WHAT TO MONITOR

### First 1-2 Hours (Phase 0):

**Watch for:**
- ✅ Successful buy transactions
- ✅ Successful sell transactions
- ✅ Position sizes $1-4 (not higher!)
- ✅ Max 5 positions open
- ✅ Telegram notifications working
- ✅ Stop loss/take profit triggering
- ⚠️ Any errors in logs
- ⚠️ Stuck positions (should auto-cleanup)

**Expected Results:**
- Small profits: $0.50-$2 per winning trade
- Small losses: $0.10-$0.50 per losing trade
- Overall: Should be profitable (if matches paper trading)

---

## 🚨 EMERGENCY PROCEDURES

### Stop Bot Immediately

```bash
# Stop service
systemctl stop solana-bot

# Or kill process
pkill -9 -f "python.*main"
```

### Close All Positions

```bash
# Via Telegram
/closeall

# Or via logs - find token addresses and manually close
```

### Check Wallet Balance

Visit Solana Explorer with your wallet address:
https://solscan.io/account/YOUR_WALLET_ADDRESS

---

## 📈 PHASE 0 → PHASE 1 TRANSITION

### After 1-2 Hours, If Phase 0 is Successful:

**Success Criteria:**
- ✅ No critical errors
- ✅ Real ROI >15% (target: 20-35%)
- ✅ Trades executing successfully
- ✅ Telegram monitoring working
- ✅ Unsellable rate <15%

**Scale to Phase 1:**

```bash
# Edit .env
nano /root/solbottrad/.env
```

**Update these values:**

```env
DEFAULT_POSITION_SIZE=5.0    # Increase to $5
MAX_POSITION_SIZE=8.0        # Increase to $8
MAX_OPEN_POSITIONS=10        # Increase to 10
```

**Restart bot:**

```bash
systemctl restart solana-bot
tail -f /root/solbottrad/bot_output.log
```

---

## 🔧 USEFUL COMMANDS

```bash
# View logs
journalctl -u solana-bot -f
tail -f /root/solbottrad/bot_output.log

# Restart bot
systemctl restart solana-bot

# Stop bot
systemctl stop solana-bot

# Check status
systemctl status solana-bot

# Update code
cd /root/solbottrad
git pull origin live-trading-v1.0-micro
systemctl restart solana-bot

# View recent trades
grep "TRADE" /root/solbottrad/bot_output.log | tail -20
```

---

## ⚠️ SECURITY REMINDERS

1. **Never share your SOLANA_PRIVATE_KEY**
2. **Never commit .env to git** (already in .gitignore)
3. **Use SSH keys for Digital Ocean** (not passwords)
4. **Keep Telegram bot token secure**
5. **Monitor wallet balance regularly**
6. **Set up alerts for large losses**

---

## 📞 SUPPORT

If you encounter issues:

1. Check logs: `tail -100 /root/solbottrad/bot_output.log`
2. Check wallet balance on Solscan
3. Stop bot if needed: `systemctl stop solana-bot`
4. Review error messages
5. Check network connectivity
6. Verify API keys are correct

---

## 🎉 GOOD LUCK!

You're deploying a bot with **33.78% proven ROI** in paper trading!

Phase 0 will validate that real execution matches expectations.

Stay conservative, monitor closely, and scale gradually! 🚀
