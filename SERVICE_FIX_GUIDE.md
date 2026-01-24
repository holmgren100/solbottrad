# URGENT: Service Fix Guide

Your systemd service has 2 issues that need fixing:

## Issue 1: Malformed Service File ⚠️

Error: `Assignment outside of section. Ignoring.`

**Problem**: Your service file at `/etc/systemd/system/solana-trading-bot.service` has corrupted syntax.

**Fix**:

```bash
# 1. Remove the broken service file
sudo rm /etc/systemd/system/solana-trading-bot.service

# 2. Copy the clean template from this repo
sudo cp /root/solbottrad/solana-trading-bot.service /etc/systemd/system/

# 3. Reload systemd
sudo systemctl daemon-reload

# 4. Enable the service
sudo systemctl enable solana-trading-bot
```

---

## Issue 2: Missing telegram Module ❌

Error: `ModuleNotFoundError: No module named 'telegram'`

**Problem**: Python telegram library not installed on the system.

**Fix**:

```bash
# Install all required dependencies
cd /root/solbottrad
pip3 install -r requirements.txt

# OR install just telegram if other deps are already installed
pip3 install python-telegram-bot==20.7
```

---

## Complete Fix Steps (Do This)

```bash
# 1. Pull latest code (includes fixes)
cd /root/solbottrad
git pull origin claude/restore-solana-bot-013YagNNs2FiAmTvNscyLeqq

# 2. Install missing Python dependencies
pip3 install -r requirements.txt

# 3. Remove broken service file
sudo rm /etc/systemd/system/solana-trading-bot.service

# 4. Install clean service file from repo
sudo cp /root/solbottrad/solana-trading-bot.service /etc/systemd/system/

# 5. Reload systemd daemon
sudo systemctl daemon-reload

# 6. Enable auto-start on boot
sudo systemctl enable solana-trading-bot

# 7. Start the service
sudo systemctl start solana-trading-bot

# 8. Check status (should show "active (running)")
sudo systemctl status solana-trading-bot

# 9. Watch logs in real-time
tail -f /root/solbottrad/bot_output.log
```

---

## Expected Output

When working correctly, you'll see:

```
● solana-trading-bot.service
     Loaded: loaded (/etc/systemd/system/solana-trading-bot.service; enabled)
     Active: active (running) since Mon 2025-12-01 21:20:00 UTC; 5s ago
   Main PID: 12345 (python3)
```

And in the logs:
```
✅ Solana Trading Bot Starting...
✅ Monitoring system initialized
✅ All systems ready
🤖 Bot is now monitoring Jupiter for opportunities...
```

---

## Alternative: Run Without Systemd

If you just want to test without systemd:

```bash
cd /root/solbottrad
./start_bot.sh
```

Or:
```bash
cd /root/solbottrad
python3 -m src.main
```

Press Ctrl+C to stop.

---

## Troubleshooting

### "pip3: command not found"
```bash
sudo apt update
sudo apt install python3-pip
```

### "Permission denied: requirements.txt"
```bash
sudo pip3 install -r requirements.txt
```

### Service still failing
```bash
# Check logs for detailed error
journalctl -u solana-trading-bot -n 50 --no-pager

# Or check bot error log
tail -50 /root/solbottrad/bot_error.log
```

### Want to see live logs
```bash
# Method 1: Service logs
journalctl -u solana-trading-bot -f

# Method 2: Bot logs
tail -f /root/solbottrad/bot_output.log

# Method 3: Error logs
tail -f /root/solbottrad/bot_error.log
```

---

## What Happened?

1. **Service file got corrupted** when you edited it with nano
   - Likely missing `[Unit]`, `[Service]`, `[Install]` section headers
   - systemd requires strict formatting

2. **telegram module never installed** on the server
   - Bot was running from terminal before (different Python environment)
   - systemd uses system Python which doesn't have the module

Both are now fixed with the steps above! 🎉
