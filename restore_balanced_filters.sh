#!/bin/bash
# Restore balanced confidence filters (not too strict, not too loose)

echo "=== Restoring Balanced Confidence Filters ==="
cd /root/solbottrad

# Backup
cp .env .env.backup.restore_balance.$(date +%Y%m%d_%H%M%S)

# Stop bot
echo "Stopping bot..."
sudo systemctl stop solana-trading-bot

# Remove current settings
sed -i '/^MIN_CONFIDENCE_SCORE=/d' .env
sed -i '/^MIN_SENTIMENT_SCORE=/d' .env
sed -i '/^MIN_SOCIAL_SCORE=/d' .env

# Add BALANCED settings (between too strict and too loose)
cat >> .env << 'EOF'

# Confidence filters - BALANCED (not 0.0, not 0.1, but middle ground)
MIN_CONFIDENCE_SCORE=0.05
MIN_SENTIMENT_SCORE=0.2
MIN_SOCIAL_SCORE=0.0
EOF

echo ""
echo "✅ Balanced filters restored!"
echo ""
echo "New settings:"
echo "- MIN_CONFIDENCE_SCORE: 0.05 (was 0.0 - too loose)"
echo "- MIN_SENTIMENT_SCORE: 0.2 (was 0.0 - too loose)"
echo "- MIN_SOCIAL_SCORE: 0.0 (unchanged)"
echo ""
echo "This will:"
echo "- Block blue chips (WBTC, WETH, SOL) ✅"
echo "- Block already-pumped tokens ✅"
echo "- Allow early-stage pumps with sentiment ✅"
echo "- Find tokens like the +218%, +281%, +337% winners ✅"
echo ""
echo "Restart: sudo systemctl restart solana-trading-bot"
