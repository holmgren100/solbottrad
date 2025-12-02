#!/bin/bash
# Restore settings from when bot had +70% wins

echo "=== Restoring Working Settings from Successful Trades ==="
cd /root/solbottrad

# Backup
cp .env .env.backup.restore_working.$(date +%Y%m%d_%H%M%S)

# Stop bot
echo "Stopping bot..."
sudo systemctl stop solana-trading-bot

# Remove ALL problematic settings
sed -i '/^MIN_CONFIDENCE_SCORE=/d' .env
sed -i '/^MIN_SENTIMENT_SCORE=/d' .env
sed -i '/^MIN_ENTRY_LIQUIDITY=/d' .env
sed -i '/^MIN_24H_VOLUME=/d' .env
sed -i '/^MIN_ENTRY_PRICE=/d' .env
sed -i '/^STALE_PRICE_MINUTES=/d' .env
sed -i '/^MIN_POSITION_LIQUIDITY=/d' .env
sed -i '/^MAX_POSITION_AGE_HOURS=/d' .env
sed -i '/^STUCK_TIME_HOURS=/d' .env

# Add WORKING settings (from when bot had +70% wins)
cat >> .env << 'EOF'

# === WORKING SETTINGS (from +70% win period) ===
# These settings produced NEX Ai +70%, Gemini 3 +76%, KalShe entry

# Liquidity & Volume (WORKING VALUES)
MIN_ENTRY_LIQUIDITY=50000
MIN_EXIT_LIQUIDITY=20000
MIN_24H_VOLUME=30000

# Price filters (allow meme tokens)
MIN_ENTRY_PRICE=0.0001
MAX_TOKENS_PER_DOLLAR=100000

# Confidence (was working with DexScreener)
MIN_CONFIDENCE_SCORE=0.25
MIN_SENTIMENT_SCORE=0.25
MIN_SOCIAL_SCORE=0.0

# Dead token detection (PATIENT - 30 min minimum)
STALE_PRICE_MINUTES=30
MIN_POSITION_LIQUIDITY=20000
MAX_POSITION_AGE_HOURS=48
STUCK_TIME_HOURS=6

EOF

echo ""
echo "✅ Working settings restored!"
echo ""
echo "Settings from +70% win period:"
echo "- MIN_ENTRY_LIQUIDITY: 50000 ($50k - allows quality meme tokens)"
echo "- MIN_24H_VOLUME: 30000 ($30k - real trading activity)"
echo "- MIN_CONFIDENCE_SCORE: 0.25 (balanced)"
echo "- STALE_PRICE_MINUTES: 30 (patient - lets pumps develop)"
echo ""
echo "Restart: sudo systemctl restart solana-trading-bot"
