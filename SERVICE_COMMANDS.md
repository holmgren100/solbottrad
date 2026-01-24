# 🤖 Solana Trading Bot - Systemd Service Commands

## 🚀 Initial Setup (One-time)

```bash
cd /root/solbottrad
./setup_service.sh
```

---

## 📋 Daily Commands

### Check Status
```bash
sudo systemctl status solana-trading-bot
```

### View Live Logs
```bash
# Main bot log
tail -f /root/solbottrad/bot.log

# System journal logs
journalctl -u solana-trading-bot -f
```

### Restart Bot (After .env changes)
```bash
sudo systemctl restart solana-trading-bot
```

### Stop Bot
```bash
sudo systemctl stop solana-trading-bot
```

### Start Bot
```bash
sudo systemctl start solana-trading-bot
```

---

## 🔍 Troubleshooting

### View Last 50 Log Lines
```bash
journalctl -u solana-trading-bot -n 50 --no-pager
```

### View Errors Only
```bash
journalctl -u solana-trading-bot -p err --no-pager
```

### Check if Bot is Running
```bash
sudo systemctl is-active solana-trading-bot
```

### Check if Bot Auto-starts on Boot
```bash
sudo systemctl is-enabled solana-trading-bot
```

---

## 🔄 Update Bot (When pulling new code)

```bash
cd /root/solbottrad

# Pull latest changes
git pull origin claude/merge-solana-bots-01J6Zki9Vv7DrwZ9jKBX6y4F

# Install any new dependencies
pip3 install --ignore-installed -r requirements.txt

# Restart service
sudo systemctl restart solana-trading-bot

# Check it started OK
sudo systemctl status solana-trading-bot
```

---

## ⚙️ Configuration Changes

After editing `.env`:
```bash
# Reload systemd (if service file changed)
sudo systemctl daemon-reload

# Restart bot to pick up new config
sudo systemctl restart solana-trading-bot

# Verify it restarted
sudo systemctl status solana-trading-bot
```

---

## 🛑 Disable Auto-start (If needed)

```bash
# Stop and disable
sudo systemctl stop solana-trading-bot
sudo systemctl disable solana-trading-bot
```

---

## 🔧 Advanced: Edit Service File

```bash
# Edit service configuration
sudo nano /etc/systemd/system/solana-trading-bot.service

# After editing, reload and restart
sudo systemctl daemon-reload
sudo systemctl restart solana-trading-bot
```

---

## 📊 Monitoring

### Real-time Performance
```bash
# Watch logs for TIER2 decisions
tail -f /root/solbottrad/bot.log | grep "TIER2"

# Watch for buy signals
tail -f /root/solbottrad/bot.log | grep "BUY SIGNAL"

# Watch for positions
tail -f /root/solbottrad/bot.log | grep -E "Position|profit"
```

### Check System Resources
```bash
# Memory usage
systemctl status solana-trading-bot | grep Memory

# Process info
ps aux | grep "python3 -m src.main"
```

---

## 🚨 Emergency Stop

```bash
# Stop immediately
sudo systemctl stop solana-trading-bot

# Kill if not responding
sudo pkill -f "python3 -m src.main"
```

---

## ✅ Health Check Script

Create a daily health check:
```bash
cat > /root/check_bot.sh << 'EOF'
#!/bin/bash
echo "=== Bot Health Check ==="
echo ""
echo "Service Status:"
sudo systemctl is-active solana-trading-bot
echo ""
echo "Last 5 Log Lines:"
tail -5 /root/solbottrad/bot.log
echo ""
echo "Uptime:"
systemctl show solana-trading-bot --property=ActiveEnterTimestamp --no-pager
EOF

chmod +x /root/check_bot.sh
```

Run with: `./check_bot.sh`

---

## 📱 Telegram Commands

While bot is running, use these in Telegram:
- `/status` - Check bot status
- `/positions` - View open positions
- `/export` - Export trading data
- `/pause` - Pause trading
- `/resume` - Resume trading
- `/close <address>` - Close specific position
- `/closeall` - Close all positions

---

## 🎯 Quick Reference

| What You Want | Command |
|---------------|---------|
| Is it running? | `sudo systemctl status solana-trading-bot` |
| See logs now | `tail -f /root/solbottrad/bot.log` |
| Restart it | `sudo systemctl restart solana-trading-bot` |
| Stop it | `sudo systemctl stop solana-trading-bot` |
| Start it | `sudo systemctl start solana-trading-bot` |
| Check errors | `journalctl -u solana-trading-bot -p err` |

---

**Tip**: Bookmark this file! 📌
