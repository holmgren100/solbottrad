#!/bin/bash
# EMERGENCY FIX: Ultra-strict filters to stop losses

echo "=== APPLYING ULTRA-STRICT FILTERS ==="
cd /root/solbottrad

# Backup current .env
cp .env .env.backup.emergency.$(date +%Y%m%d_%H%M%S)

# Stop bot
echo "Stopping bot..."
sudo systemctl stop solana-trading-bot

# Apply STRICT filters
cat >> .env << 'FILTERS'

# === EMERGENCY STRICT FILTERS ===
# Applied to stop 77% capital loss

# DISABLE AUTO-TRADING (manual mode only)
AUTO_TRADE_ENABLED=false

# MUCH STRICTER LIQUIDITY (prevent honeypots)
MIN_ENTRY_LIQUIDITY=200000      # $200k minimum (was $30k)
MIN_EXIT_LIQUIDITY=100000        # $100k minimum (was $15k)
MIN_24H_VOLUME=100000            # $100k volume (was $15k)

# BIGGER POSITIONS (reduce trade frequency)
DEFAULT_POSITION_SIZE=50.0       # $50 per trade (was $2)
MAX_POSITION_SIZE=100.0          # $100 max (was $4)

# STRICTER PRICE FILTERS
MIN_ENTRY_PRICE=0.0001           # Allow pump.fun tokens
MAX_TOKENS_PER_DOLLAR=100000     # Block ultra-cheap scams

# DISABLE VOLUME FALLBACK (too risky)
ALLOW_VOLUME_FALLBACK=false

# STRICTER RUG PROTECTION
MIN_POSITION_LIQUIDITY=50000     # Close if liquidity drops below $50k
STUCK_LIQUIDITY_THRESHOLD=50000  # $50k minimum

# LONGER DEAD TOKEN DETECTION (stop premature closes)
STALE_PRICE_MINUTES=10           # Wait 10min before calling it dead

FILTERS

echo ""
echo "✅ Strict filters applied!"
echo ""
echo "Current settings:"
grep -E "AUTO_TRADE_ENABLED|MIN_ENTRY_LIQUIDITY|MIN_24H_VOLUME|DEFAULT_POSITION_SIZE" .env | tail -10

echo ""
echo "⚠️  AUTO-TRADING DISABLED"
echo "Bot will scan but NOT make trades automatically"
echo "Use Telegram commands to manually trade if you want"
