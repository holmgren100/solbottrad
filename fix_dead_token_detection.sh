#!/bin/bash
# Fix aggressive dead token detection

echo "=== Fixing Aggressive Dead Token Detection ==="
cd /root/solbottrad

# Backup
cp .env .env.backup.deadtoken_fix.$(date +%Y%m%d_%H%M%S)

# Stop bot
echo "Stopping bot..."
sudo systemctl stop solana-trading-bot

# Update dead token detection settings
cat > /tmp/deadtoken_fix.env << 'EOF'

# === LESS AGGRESSIVE DEAD TOKEN DETECTION ===
# Applied to stop premature exits

# Wait LONGER before calling a token dead
STALE_PRICE_MINUTES=15           # Was 3, now 15 minutes

# Lower the liquidity threshold (don't exit just because liquidity dropped)
MIN_POSITION_LIQUIDITY=20000     # Was 10000, now 20000 (still protected)

# Increase stuck time threshold
STUCK_TIME_HOURS=3               # Was 2, now 3 hours

# Keep max position age reasonable
MAX_POSITION_AGE_HOURS=24        # Was 12, now 24 hours

# Keep force close on rug (this is good)
FORCE_CLOSE_ON_RUG=true

EOF

# Remove old dead token settings from .env
sed -i '/^STALE_PRICE_MINUTES=/d' .env
sed -i '/^MIN_POSITION_LIQUIDITY=/d' .env
sed -i '/^STUCK_TIME_HOURS=/d' .env
sed -i '/^MAX_POSITION_AGE_HOURS=/d' .env

# Append new settings
cat /tmp/deadtoken_fix.env >> .env

echo ""
echo "✅ Dead token detection updated!"
echo ""
echo "New settings:"
echo "- Wait 15 minutes before calling token dead (was 3)"
echo "- Lower liquidity threshold: $20k (was $10k)"
echo "- Stuck time: 3 hours (was 2)"
echo "- Max age: 24 hours (was 12)"
echo ""
echo "With your new $100k liquidity + $50k volume filters,"
echo "tokens should have time to pump before being called dead!"
echo ""
echo "Restart bot: sudo systemctl restart solana-trading-bot"
