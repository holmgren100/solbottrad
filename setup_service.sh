#!/bin/bash
# ============================================================================
# Systemd Service Setup for Hybrid Solana Trading Bot
# ============================================================================

echo "🚀 Setting up Solana Trading Bot as systemd service..."

# Stop existing service if running
echo "⏸️  Stopping any existing service..."
sudo systemctl stop solana-trading-bot 2>/dev/null || true

# Copy service file to systemd directory
echo "📄 Installing service file..."
sudo cp /root/solbottrad/solana-trading-bot.service /etc/systemd/system/

# Reload systemd to recognize new/updated service
echo "🔄 Reloading systemd daemon..."
sudo systemctl daemon-reload

# Enable service to start on boot
echo "✅ Enabling service to start on boot..."
sudo systemctl enable solana-trading-bot

# Start the service
echo "▶️  Starting bot service..."
sudo systemctl start solana-trading-bot

# Wait a moment for startup
sleep 2

# Show status
echo ""
echo "============================================================================"
echo "📊 SERVICE STATUS"
echo "============================================================================"
sudo systemctl status solana-trading-bot --no-pager

echo ""
echo "============================================================================"
echo "✅ SETUP COMPLETE!"
echo "============================================================================"
echo ""
echo "📝 Useful Commands:"
echo ""
echo "  # Check status"
echo "  sudo systemctl status solana-trading-bot"
echo ""
echo "  # View logs (live)"
echo "  tail -f /root/solbottrad/bot.log"
echo ""
echo "  # Stop the bot"
echo "  sudo systemctl stop solana-trading-bot"
echo ""
echo "  # Restart the bot"
echo "  sudo systemctl restart solana-trading-bot"
echo ""
echo "  # View recent logs"
echo "  journalctl -u solana-trading-bot -n 50 --no-pager"
echo ""
echo "  # Disable auto-start on boot"
echo "  sudo systemctl disable solana-trading-bot"
echo ""
echo "============================================================================"
