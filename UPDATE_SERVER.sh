#!/bin/bash
# Run this script on your Digital Ocean server to update the bot

echo "🔄 Updating Solana Trading Bot..."

# 1. Pull latest code
echo "📥 Pulling latest code from GitHub..."
git pull origin claude/restore-solana-bot-013YagNNs2FiAmTvNscyLeqq

# 2. Kill old bot process
echo "🛑 Stopping old bot..."
pkill -f "python.*main.py"
sleep 2

# 3. Add missing feature flags to .env if not present
echo "⚙️  Checking .env feature flags..."
if ! grep -q "ENABLE_AGE_BASED_STRATEGIES" .env; then
    echo "Adding missing feature flags to .env..."
    cat >> .env << 'EOF'

# === FEATURE FLAGS (Phase 3 - Test One by One) ===
ENABLE_AGE_BASED_STRATEGIES=false
ENABLE_VOLUME_ANALYZER=false
ENABLE_RUGCHECK_API=false
ENABLE_WHALE_TRACKING=false
ENABLE_MOVEMENT_DETECTION=false
ENABLE_TWITTER_SENTIMENT=false
EOF
    echo "✅ Feature flags added"
else
    echo "✅ Feature flags already exist"
fi

# 4. Verify critical settings
echo ""
echo "📋 Current Settings:"
echo "  STALE_PRICE_MINUTES: $(grep '^STALE_PRICE_MINUTES=' .env | cut -d= -f2)"
echo "  MIN_POSITION_LIQUIDITY: $(grep '^MIN_POSITION_LIQUIDITY=' .env | cut -d= -f2)"
echo "  TELEGRAM_BOT_TOKEN: $(grep '^TELEGRAM_BOT_TOKEN=' .env | cut -d= -f2 | cut -c1-20)..."
echo "  ENABLE_AGE_BASED_STRATEGIES: $(grep '^ENABLE_AGE_BASED_STRATEGIES=' .env | cut -d= -f2)"
echo ""

# 5. Start bot in background
echo "🚀 Starting bot..."
nohup python3 src/main.py > bot_console.log 2>&1 &
sleep 3

# 6. Check if running
if ps aux | grep -v grep | grep "python.*main.py" > /dev/null; then
    echo "✅ Bot is running!"
    echo "📊 Monitor logs: tail -f trading_bot.log"
else
    echo "❌ Bot failed to start. Check bot_console.log"
fi
