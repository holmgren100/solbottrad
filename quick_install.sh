#!/bin/bash
# Quick install bypassing blinker distutils issue

set -e

echo "🔧 Quick Install - Bypassing distutils conflicts"
echo "================================================"
echo ""

cd /root/solbottrad

echo "📦 Installing critical dependencies only..."
pip3 install --upgrade python-telegram-bot==20.7 || {
    echo "⚠️  Trying with --ignore-installed flag..."
    pip3 install --ignore-installed python-telegram-bot==20.7
}

echo ""
echo "🗑️  Removing old service file..."
sudo rm -f /etc/systemd/system/solana-trading-bot.service

echo ""
echo "📄 Installing clean service file..."
sudo cp /root/solbottrad/solana-trading-bot.service /etc/systemd/system/

echo ""
echo "🔄 Reloading systemd..."
sudo systemctl daemon-reload

echo ""
echo "✅ Starting service..."
sudo systemctl enable solana-trading-bot
sudo systemctl start solana-trading-bot

echo ""
echo "================================================"
echo "✅ Installation complete!"
echo ""
sudo systemctl status solana-trading-bot --no-pager || true
