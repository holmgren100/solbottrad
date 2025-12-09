#!/bin/bash
# Remove inline comments from .env file for systemd compatibility

echo "=== Cleaning .env File (Remove Inline Comments) ==="

cd /root/solbottrad

# Backup
cp .env .env.backup.clean.$(date +%Y%m%d_%H%M%S)

# Remove inline comments (everything after # on lines with =)
# Keep full comment lines (lines starting with #)
sed -i 's/\([^#]*\)#.*/\1/' .env

# Remove trailing whitespace
sed -i 's/[[:space:]]*$//' .env

# Remove empty lines at the end
sed -i -e :a -e '/^\n*$/{$d;N;ba' -e '}' .env

echo "✅ .env file cleaned!"
echo ""
echo "Verification - checking key settings:"
echo "MIN_ENTRY_LIQUIDITY: $(grep '^MIN_ENTRY_LIQUIDITY=' .env)"
echo "STALE_PRICE_MINUTES: $(grep '^STALE_PRICE_MINUTES=' .env)"
echo "MIN_CONFIDENCE_SCORE: $(grep '^MIN_CONFIDENCE_SCORE=' .env)"

echo ""
echo "NOW RESTART: sudo systemctl restart solana-trading-bot"
