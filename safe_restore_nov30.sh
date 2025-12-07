#!/bin/bash
# SAFE restoration of Nov 30 working settings
# With verification at each step

set -e  # Exit on any error

echo "=========================================="
echo "SAFE Nov 30 Settings Restoration"
echo "=========================================="
echo ""

cd /root/solbottrad

# Step 1: Verify we're in the right directory
echo "1. Verifying location..."
if [ ! -f ".env" ]; then
    echo "❌ ERROR: .env file not found!"
    exit 1
fi
echo "✅ Found .env file"
echo ""

# Step 2: Create timestamped backup
echo "2. Creating backup..."
BACKUP_FILE=".env.backup.$(date +%Y%m%d_%H%M%S)"
cp .env "$BACKUP_FILE"
echo "✅ Backup created: $BACKUP_FILE"
echo ""

# Step 3: Stop bot safely
echo "3. Stopping bot..."
sudo systemctl stop solana-trading-bot
sleep 2
echo "✅ Bot stopped"
echo ""

# Step 4: Clear Python cache
echo "4. Clearing Python cache..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
echo "✅ Cache cleared"
echo ""

# Step 5: Remove conflicting settings (one by one, safely)
echo "5. Removing old settings..."
sed -i.bak '/^MIN_CONFIDENCE_SCORE=/d' .env
sed -i.bak '/^MIN_SENTIMENT_SCORE=/d' .env
sed -i.bak '/^MIN_ENTRY_LIQUIDITY=/d' .env
sed -i.bak '/^MIN_EXIT_LIQUIDITY=/d' .env
sed -i.bak '/^MIN_24H_VOLUME=/d' .env
sed -i.bak '/^MIN_ENTRY_PRICE=/d' .env
sed -i.bak '/^MAX_TOKENS_PER_DOLLAR=/d' .env
sed -i.bak '/^STALE_PRICE_MINUTES=/d' .env
sed -i.bak '/^MIN_POSITION_LIQUIDITY=/d' .env
sed -i.bak '/^MAX_POSITION_AGE_HOURS=/d' .env
sed -i.bak '/^STUCK_TIME_HOURS=/d' .env
sed -i.bak '/^STUCK_LIQUIDITY_THRESHOLD=/d' .env
sed -i.bak '/^TRAILING_STOP_PERCENT=/d' .env
sed -i.bak '/^DEFAULT_POSITION_SIZE=/d' .env
sed -i.bak '/^MAX_POSITION_SIZE=/d' .env
echo "✅ Old settings removed"
echo ""

# Step 6: Add Nov 30 working settings
echo "6. Adding Nov 30 working settings..."
cat >> .env << 'EOF'

# === NOV 30 WORKING SETTINGS (Restored) ===
# These settings produced 97% good trades
MIN_CONFIDENCE_SCORE=0.0
MIN_SENTIMENT_SCORE=0.25
MIN_SOCIAL_SCORE=0.0
DEFAULT_POSITION_SIZE=65
MAX_POSITION_SIZE=100
TRAILING_STOP_PERCENT=10
MIN_ENTRY_LIQUIDITY=30000
MIN_EXIT_LIQUIDITY=15000
MIN_24H_VOLUME=15000
MAX_POSITION_VS_LIQUIDITY=0.005
MIN_ENTRY_PRICE=0.10
MAX_TOKENS_PER_DOLLAR=10000
ALLOW_VOLUME_FALLBACK=true
MIN_VOLUME_FOR_FALLBACK=50000
VOLUME_FALLBACK_POSITION_MULTIPLIER=0.5
AUTO_CLEANUP_ENABLED=true
MAX_POSITION_AGE_HOURS=48
STUCK_LIQUIDITY_THRESHOLD=1000
STUCK_TIME_HOURS=6
FORCE_CLOSE_ON_RUG=true
RUG_DETECTION_ENABLED=true
STALE_PRICE_MINUTES=2
MIN_POSITION_LIQUIDITY=5000.0
EOF
echo "✅ Settings added"
echo ""

# Step 7: Verify critical settings
echo "7. Verifying settings were added correctly..."
echo ""
echo "Checking key values:"
grep "^MIN_CONFIDENCE_SCORE=" .env && echo "  ✅ MIN_CONFIDENCE_SCORE found" || echo "  ❌ Missing"
grep "^MIN_ENTRY_LIQUIDITY=" .env && echo "  ✅ MIN_ENTRY_LIQUIDITY found" || echo "  ❌ Missing"
grep "^MIN_24H_VOLUME=" .env && echo "  ✅ MIN_24H_VOLUME found" || echo "  ❌ Missing"
grep "^STALE_PRICE_MINUTES=" .env && echo "  ✅ STALE_PRICE_MINUTES found" || echo "  ❌ Missing"
grep "^TRAILING_STOP_PERCENT=" .env && echo "  ✅ TRAILING_STOP_PERCENT found" || echo "  ❌ Missing"
echo ""

# Step 8: Update systemd service file
echo "8. Ensuring systemd loads .env file..."
sudo cp solana-trading-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
echo "✅ Systemd updated"
echo ""

# Step 9: Show final settings
echo "9. Final Nov 30 settings:"
echo "=========================================="
echo "MIN_CONFIDENCE_SCORE: $(grep '^MIN_CONFIDENCE_SCORE=' .env | cut -d= -f2)"
echo "MIN_SENTIMENT_SCORE: $(grep '^MIN_SENTIMENT_SCORE=' .env | cut -d= -f2)"
echo "MIN_ENTRY_LIQUIDITY: $(grep '^MIN_ENTRY_LIQUIDITY=' .env | cut -d= -f2)"
echo "MIN_24H_VOLUME: $(grep '^MIN_24H_VOLUME=' .env | cut -d= -f2)"
echo "STALE_PRICE_MINUTES: $(grep '^STALE_PRICE_MINUTES=' .env | cut -d= -f2)"
echo "TRAILING_STOP_PERCENT: $(grep '^TRAILING_STOP_PERCENT=' .env | cut -d= -f2)"
echo "DEFAULT_POSITION_SIZE: $(grep '^DEFAULT_POSITION_SIZE=' .env | cut -d= -f2)"
echo "=========================================="
echo ""

echo "✅ All settings restored successfully!"
echo ""
echo "To start bot: sudo systemctl restart solana-trading-bot"
echo "To check logs: tail -f /root/solbottrad/bot.log"
echo ""
echo "If something goes wrong, restore from: $BACKUP_FILE"
