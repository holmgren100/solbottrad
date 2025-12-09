#!/bin/bash
# FORCE FIX: Set dead token detection to 30 minutes

echo "=== EMERGENCY: Setting Dead Token Detection to 30 Minutes ==="
cd /root/solbottrad

# Stop bot
echo "Stopping bot..."
sudo systemctl stop solana-trading-bot

# Backup
cp .env .env.backup.emergency30min.$(date +%Y%m%d_%H%M%S)

# FORCE REMOVE all old settings (use proper sed syntax)
sed -i '/^STALE_PRICE_MINUTES/d' .env
sed -i '/^MIN_POSITION_LIQUIDITY/d' .env
sed -i '/^STUCK_TIME_HOURS/d' .env
sed -i '/^MAX_POSITION_AGE_HOURS/d' .env

# Add new settings AT THE END (guaranteed to be read)
cat >> .env << 'EOF'

# === DEAD TOKEN DETECTION - FIXED ===
# Set to 30 minutes to give tokens time to pump
STALE_PRICE_MINUTES=30
MIN_POSITION_LIQUIDITY=20000
STUCK_TIME_HOURS=6
MAX_POSITION_AGE_HOURS=48
EOF

echo ""
echo "✅ Settings updated!"
echo ""
echo "Verification:"
grep "STALE_PRICE_MINUTES" .env
grep "MIN_POSITION_LIQUIDITY" .env
grep "STUCK_TIME_HOURS" .env
grep "MAX_POSITION_AGE_HOURS" .env

echo ""
echo "NOW RESTART: sudo systemctl restart solana-trading-bot"
