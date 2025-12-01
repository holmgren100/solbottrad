# Systemd Service Fix - ImportError Resolution

## Problem

You're seeing this error when running the bot as a systemd service:

```
ImportError: attempted relative import with no known parent package
```

**Root Cause**: The systemd service is running `python src/main.py` directly, but `src/main.py` uses relative imports (`from .config import settings`) which only work when running as a Python module.

## Solution

The bot MUST be run as: `python3 -m src.main` (not `python3 src/main.py`)

---

## Fix Your Existing Systemd Service

### Step 1: Find your service file

```bash
# Try these locations:
ls -la /etc/systemd/system/solana-trading-bot.service
ls -la /lib/systemd/system/solana-trading-bot.service
ls -la /usr/lib/systemd/system/solana-trading-bot.service

# Or search for it:
sudo find /etc /lib /usr/lib -name "*solana*" -o -name "*trading*" 2>/dev/null
```

### Step 2: Edit the service file

```bash
# Once you find it, edit it:
sudo nano /etc/systemd/system/solana-trading-bot.service
```

### Step 3: Fix the ExecStart line

**WRONG (causes ImportError):**
```ini
ExecStart=/usr/bin/python3 src/main.py
ExecStart=/usr/bin/python3 /root/solbottrad/src/main.py
ExecStart=python3 src/main.py
```

**CORRECT:**
```ini
ExecStart=/usr/bin/python3 -m src.main
```

**Complete working service file:**
```ini
[Unit]
Description=Solana Trading Bot with Multi-Layer Screening
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/solbottrad

# CRITICAL: Must use -m flag to run as module
ExecStart=/usr/bin/python3 -m src.main

Restart=always
RestartSec=10

StandardOutput=append:/root/solbottrad/bot_output.log
StandardError=append:/root/solbottrad/bot_error.log

[Install]
WantedBy=multi-user.target
```

### Step 4: Reload and restart

```bash
sudo systemctl daemon-reload
sudo systemctl restart solana-trading-bot
sudo systemctl status solana-trading-bot
```

### Step 5: Check logs

```bash
# Watch for successful startup:
tail -f /root/solbottrad/bot_output.log

# Check for errors:
tail -f /root/solbottrad/bot_error.log
```

---

## Alternative: Install Fresh Service File

If you can't find your existing service file, install the template provided:

```bash
# Copy template to systemd directory
sudo cp /root/solbottrad/solana-trading-bot.service /etc/systemd/system/

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable solana-trading-bot
sudo systemctl start solana-trading-bot

# Check status
sudo systemctl status solana-trading-bot
```

---

## Quick Test (Without Systemd)

To verify the bot works with correct import syntax:

```bash
cd /root/solbottrad

# WRONG (will fail with ImportError):
# python3 src/main.py

# CORRECT (will work):
python3 -m src.main
```

Or use the startup script:

```bash
cd /root/solbottrad
./start_bot.sh
```

---

## Troubleshooting

### "command not found: python3"

Try `python` instead:
```bash
ExecStart=/usr/bin/python -m src.main
```

### "No module named src"

Ensure `WorkingDirectory` is set correctly:
```ini
WorkingDirectory=/root/solbottrad
```

### "Permission denied"

Ensure correct ownership:
```bash
sudo chown -R root:root /root/solbottrad
sudo chmod +x /root/solbottrad/start_bot.sh
```

### Virtual environment issues

If using venv, activate it in the service:
```ini
ExecStart=/bin/bash -c 'cd /root/solbottrad && source venv/bin/activate && python -m src.main'
```

---

## Expected Output (Successful Start)

When correctly configured, you should see:

```
✅ Solana Trading Bot Starting...
✅ Configuration loaded from .env
✅ Monitoring system initialized
✅ RugCheck client initialized
✅ Whale analyzer initialized
✅ Movement detector initialized
✅ Volume analyzer initialized
✅ All systems ready
🤖 Bot is now monitoring Jupiter for opportunities...
```

---

## Service Management Commands

```bash
# Start bot
sudo systemctl start solana-trading-bot

# Stop bot
sudo systemctl stop solana-trading-bot

# Restart bot
sudo systemctl restart solana-trading-bot

# Check status
sudo systemctl status solana-trading-bot

# View logs in real-time
journalctl -u solana-trading-bot -f

# Enable auto-start on boot
sudo systemctl enable solana-trading-bot

# Disable auto-start
sudo systemctl disable solana-trading-bot
```
