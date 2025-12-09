#!/bin/bash
# Restore EXACT working settings from Nov 30 backup

echo "=== Restoring Nov 30 Working Settings (97% good trades) ==="
cd /root/solbottrad

# Backup current
cp .env .env.backup.before_nov30_restore.$(date +%Y%m%d_%H%M%S)

# Stop bot
echo "Stopping bot..."
sudo systemctl stop solana-trading-bot

# Remove conflicting settings
sed -i '/^MIN_CONFIDENCE_SCORE=/d' .env
sed -i '/^MIN_SENTIMENT_SCORE=/d' .env
sed -i '/^MIN_ENTRY_LIQUIDITY=/d' .env
sed -i '/^MIN_EXIT_LIQUIDITY=/d' .env
sed -i '/^MIN_24H_VOLUME=/d' .env
sed -i '/^MIN_ENTRY_PRICE=/d' .env
sed -i '/^MAX_TOKENS_PER_DOLLAR=/d' .env
sed -i '/^STALE_PRICE_MINUTES=/d' .env
sed -i '/^MIN_POSITION_LIQUIDITY=/d' .env
sed -i '/^MAX_POSITION_AGE_HOURS=/d' .env
sed -i '/^STUCK_TIME_HOURS=/d' .env
sed -i '/^STUCK_LIQUIDITY_THRESHOLD=/d' .env
sed -i '/^TRAILING_STOP_PERCENT=/d' .env
sed -i '/^DEFAULT_POSITION_SIZE=/d' .env
sed -i '/^MAX_POSITION_SIZE=/d' .env

# Add EXACT Nov 30 working settings
cat >> .env << 'EOF'

# === NOV 30 WORKING SETTINGS (97% good trades) ===
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

echo ""
echo "✅ Nov 30 working settings restored!"
echo ""
echo "Key settings:"
echo "- MIN_CONFIDENCE_SCORE: 0.0"
echo "- MIN_SENTIMENT_SCORE: 0.25"
echo "- MIN_ENTRY_LIQUIDITY: 30000 ($30k)"
echo "- MIN_24H_VOLUME: 15000 ($15k)"
echo "- STALE_PRICE_MINUTES: 2"
echo "- TRAILING_STOP_PERCENT: 10"
echo "- POSITION_SIZE: $65-100"
echo ""
echo "Restart: sudo systemctl restart solana-trading-bot"
