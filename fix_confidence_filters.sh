#!/bin/bash
# Fix confidence filter blocking good tokens

echo "=== Fixing Strict Confidence Filter ==="
cd /root/solbottrad

# Backup
cp .env .env.backup.confidence_fix.$(date +%Y%m%d_%H%M%S)

# Stop bot
echo "Stopping bot..."
sudo systemctl stop solana-trading-bot

# Lower confidence requirements
# When APIs fail/return "unknown", allow trades based on liquidity/volume alone
cat >> .env << 'EOF'

# === RELAXED CONFIDENCE FILTERS ===
# Allow trades when sentiment APIs fail/return unknown
# Trust liquidity + volume filters instead

# Set to 0.0 to allow trades when sentiment confidence is unknown
MIN_CONFIDENCE_SCORE=0.0

# Lower sentiment requirement (many tokens have no Twitter)
MIN_SENTIMENT_SCORE=0.0

# Social score already at 0 (good)
MIN_SOCIAL_SCORE=0.0

EOF

# Remove old settings
sed -i '/^MIN_CONFIDENCE_SCORE=/d' .env
sed -i '/^MIN_SENTIMENT_SCORE=/d' .env
sed -i '/^MIN_SOCIAL_SCORE=/d' .env

# Add new relaxed settings
echo "" >> .env
echo "# Confidence filters - Relaxed to allow trades when APIs fail" >> .env
echo "MIN_CONFIDENCE_SCORE=0.0    # Allow unknown sentiment" >> .env
echo "MIN_SENTIMENT_SCORE=0.0     # Don't require Twitter sentiment" >> .env
echo "MIN_SOCIAL_SCORE=0.0        # Don't require social signals" >> .env

echo ""
echo "✅ Confidence filters relaxed!"
echo ""
echo "New settings:"
echo "- MIN_CONFIDENCE_SCORE: 0.1 → 0.0 (allow unknown sentiment)"
echo "- MIN_SENTIMENT_SCORE: 0.3 → 0.0 (don't require Twitter)"
echo "- MIN_SOCIAL_SCORE: Already 0.0 ✅"
echo ""
echo "Bot will now trust:"
echo "- Liquidity filters ($100k minimum)"
echo "- Volume filters ($50k minimum)"
echo "- Market buy signals (0.90 confidence)"
echo "- RugCheck scores"
echo ""
echo "Restart: sudo systemctl restart solana-trading-bot"
