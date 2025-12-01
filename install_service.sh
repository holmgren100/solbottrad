#!/bin/bash
# Quick service installation script
# Fixes the systemd service and installs dependencies

set -e  # Exit on error

echo "🔧 Solana Trading Bot - Service Installation & Fix"
echo "=================================================="
echo ""

# Change to bot directory
cd /root/solbottrad

echo "📥 Step 1/6: Pulling latest code..."
git pull origin claude/restore-solana-bot-013YagNNs2FiAmTvNscyLeqq || {
    echo "⚠️  Git pull failed - continuing anyway..."
}
echo ""

echo "📦 Step 2/6: Installing Python dependencies..."
pip3 install -r requirements.txt
echo ""

echo "🗑️  Step 3/6: Removing old/broken service file..."
sudo rm -f /etc/systemd/system/solana-trading-bot.service
echo ""

echo "📄 Step 4/6: Installing clean service file..."
sudo cp /root/solbottrad/solana-trading-bot.service /etc/systemd/system/
echo ""

echo "🔄 Step 5/6: Reloading systemd daemon..."
sudo systemctl daemon-reload
echo ""

echo "✅ Step 6/6: Enabling and starting service..."
sudo systemctl enable solana-trading-bot
sudo systemctl start solana-trading-bot
echo ""

echo "=================================================="
echo "✅ Installation complete!"
echo ""
echo "📊 Service status:"
sudo systemctl status solana-trading-bot --no-pager || true
echo ""
echo "📝 To view live logs, run:"
echo "   tail -f /root/solbottrad/bot_output.log"
echo ""
echo "🛑 To stop the bot:"
echo "   sudo systemctl stop solana-trading-bot"
echo ""
echo "🔄 To restart the bot:"
echo "   sudo systemctl restart solana-trading-bot"
echo ""
