#!/bin/bash
# Fix systemd service to load .env file

echo "=== Fixing Systemd Service to Load .env File ==="

cd /root/solbottrad

# Stop bot
echo "Stopping bot..."
sudo systemctl stop solana-trading-bot

# Copy fixed service file
echo "Copying fixed service file..."
sudo cp solana-trading-bot.service /etc/systemd/system/

# Reload systemd
echo "Reloading systemd..."
sudo systemctl daemon-reload

# Verify the service file
echo ""
echo "Verifying service file contains EnvironmentFile..."
grep "EnvironmentFile" /etc/systemd/system/solana-trading-bot.service && echo "✅ Found!" || echo "❌ Missing!"

# Show current .env setting
echo ""
echo "Current .env STALE_PRICE_MINUTES setting:"
grep "^STALE_PRICE_MINUTES" .env

echo ""
echo "✅ Service file updated!"
echo ""
echo "NOW RESTART: sudo systemctl restart solana-trading-bot"
echo ""
echo "The bot will now load .env and use STALE_PRICE_MINUTES=30"
