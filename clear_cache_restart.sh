#!/bin/bash
# Force clear all Python cache and restart bot

echo "=== Clearing Python Cache Completely ==="
cd /root/solbottrad

# Stop bot first
echo "Stopping bot..."
sudo systemctl stop solana-trading-bot

# Clear all __pycache__ directories
echo "Clearing __pycache__ directories..."
find . -type d -name "__pycache__" -print -exec rm -rf {} + 2>/dev/null || true

# Clear all .pyc files
echo "Clearing .pyc files..."
find . -type f -name "*.pyc" -print -delete

# Clear all .pyo files
echo "Clearing .pyo files..."
find . -type f -name "*.pyo" -print -delete

# Verify cache is cleared
remaining=$(find . -type d -name "__pycache__" 2>/dev/null | wc -l)
echo "Remaining __pycache__ directories: $remaining"

if [ "$remaining" -eq 0 ]; then
    echo "✅ Python cache fully cleared!"
else
    echo "⚠️  Warning: $remaining cache directories still exist"
    echo "Attempting force removal with sudo..."
    sudo find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
fi

# Restart bot
echo ""
echo "Restarting bot..."
sudo systemctl restart solana-trading-bot

echo ""
echo "✅ Done! Check logs with: tail -f /root/solbottrad/bot.log"
