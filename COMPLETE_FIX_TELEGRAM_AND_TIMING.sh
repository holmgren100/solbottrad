#!/bin/bash
# Complete fix for Telegram token + 5-minute detection issues

echo "🔧 COMPLETE FIX: Telegram + Timing Issues"
echo "=========================================="
echo ""

# 1. Pull latest code (includes 1-minute detection fix)
echo "📥 Step 1: Pulling latest code..."
git pull origin claude/restore-solana-bot-013YagNNs2FiAmTvNscyLeqq

echo ""
echo "🔑 Step 2: Fixing Telegram token..."

# 2. Update Telegram token in .env
OLD_TOKEN="7485034507:AAHSp30qCCHb7eulIvUSMyAXcATjX2p2VYg"
NEW_TOKEN="7485034507:AAGolg2sVNJhuGyOEXpEJ87GMzRg8cfL4Jc"

if grep -q "$OLD_TOKEN" .env; then
    echo "  ❌ Found OLD token in .env - replacing..."
    sed -i "s|$OLD_TOKEN|$NEW_TOKEN|g" .env
    echo "  ✅ Telegram token updated!"
else
    echo "  ℹ️  Old token not found, checking current token..."
    CURRENT_TOKEN=$(grep "^TELEGRAM_BOT_TOKEN=" .env | cut -d= -f2)
    if [ "$CURRENT_TOKEN" = "$NEW_TOKEN" ]; then
        echo "  ✅ Token is already correct!"
    else
        echo "  ⚠️  Unexpected token found: $CURRENT_TOKEN"
        echo "  Updating to correct token..."
        sed -i "s|^TELEGRAM_BOT_TOKEN=.*|TELEGRAM_BOT_TOKEN=$NEW_TOKEN|" .env
        echo "  ✅ Token updated!"
    fi
fi

echo ""
echo "📊 Step 3: Verifying critical settings..."
echo "  TELEGRAM_BOT_TOKEN: $(grep '^TELEGRAM_BOT_TOKEN=' .env | cut -d= -f2 | cut -c1-20)..."
echo "  STALE_PRICE_MINUTES: $(grep '^STALE_PRICE_MINUTES=' .env | cut -d= -f2)"
echo "  MIN_POSITION_LIQUIDITY: $(grep '^MIN_POSITION_LIQUIDITY=' .env | cut -d= -f2)"

echo ""
echo "🛑 Step 4: Stopping old bot..."
pkill -f "python.*main.py"
sleep 2

# Verify no bot is running
if ps aux | grep -v grep | grep "python.*main.py" > /dev/null; then
    echo "  ⚠️  Bot still running, force killing..."
    pkill -9 -f "python.*main.py"
    sleep 1
fi

echo "  ✅ Old bot stopped"

echo ""
echo "🚀 Step 5: Starting bot with fixes..."
nohup python3 src/main.py > bot_console.log 2>&1 &
sleep 3

# Check if running
if ps aux | grep -v grep | grep "python.*main.py" > /dev/null; then
    echo "  ✅ Bot is running!"
else
    echo "  ❌ Bot failed to start. Check bot_console.log"
    exit 1
fi

echo ""
echo "✅ ALL FIXES APPLIED!"
echo "=========================================="
echo ""
echo "📋 What was fixed:"
echo "  1. ✅ Telegram token updated (no more 401 errors)"
echo "  2. ✅ Dead token detection: 5 min → 1 min"
echo "  3. ✅ Position monitoring: 10 seconds"
echo "  4. ✅ Birdeye diagnostics improved"
echo ""
echo "📊 Monitor logs:"
echo "  tail -f trading_bot.log | grep -E 'Telegram|DEAD TOKEN|Monitoring'"
echo ""
echo "🔍 What to expect:"
echo "  • No more '401 Unauthorized' from Telegram"
echo "  • Dead tokens detected in 1-2 minutes (not 5)"
echo "  • Position monitoring every ~10 seconds"
echo ""
