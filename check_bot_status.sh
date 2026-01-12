#!/bin/bash
# Diagnostisk check av botens status

echo "=== BOT STATUS DIAGNOSTIC ==="
echo ""

# Find active log file
BOT_DIR="/home/user/solbottrad"
if [ -f "$BOT_DIR/bot_new.log" ] && [ "$BOT_DIR/bot_new.log" -nt "$BOT_DIR/bot.log" ]; then
    LOG_FILE="$BOT_DIR/bot_new.log"
else
    LOG_FILE="$BOT_DIR/bot.log"
fi

echo "📂 Log file: $LOG_FILE"
echo "📅 Last modified: $(stat -c %y "$LOG_FILE" 2>/dev/null | cut -d. -f1)"
echo ""

# Check if bot is running
if [ $(find "$LOG_FILE" -mmin -5 2>/dev/null | wc -l) -gt 0 ]; then
    echo "✅ Bot appears to be ACTIVE (log updated within 5 min)"
else
    echo "⚠️  Bot appears to be STOPPED (log not updated in >5 min)"
fi
echo ""

# Check for network errors
NETWORK_ERRORS=$(tail -100 "$LOG_FILE" 2>/dev/null | grep -c "Cannot connect to host")
if [ $NETWORK_ERRORS -gt 0 ]; then
    echo "❌ NETWORK ISSUES DETECTED ($NETWORK_ERRORS errors in last 100 lines)"
    echo "   Bot cannot connect to trading APIs (Jupiter, DexScreener, CoinGecko)"
    echo "   This prevents the bot from finding tokens to trade"
    echo ""
    echo "   Recent errors:"
    tail -100 "$LOG_FILE" 2>/dev/null | grep "Cannot connect" | head -3
    echo ""
else
    echo "✅ No network errors detected"
fi
echo ""

# Check for recent trades
RECENT_TRADES=$(tail -500 "$LOG_FILE" 2>/dev/null | grep -c "Position opened")
RECENT_EXITS=$(tail -500 "$LOG_FILE" 2>/dev/null | grep -c "Position closed")

echo "📊 RECENT ACTIVITY (last 500 log lines):"
echo "   Position opens: $RECENT_TRADES"
echo "   Position closes: $RECENT_EXITS"
echo ""

# Check CSV files
echo "📁 DATA FILES:"
if [ -f "$BOT_DIR/data/ml_trades.csv" ]; then
    TRADE_COUNT=$(wc -l < "$BOT_DIR/data/ml_trades.csv")
    echo "   ✅ ml_trades.csv: $((TRADE_COUNT - 1)) trades"
    echo "   Last modified: $(stat -c %y "$BOT_DIR/data/ml_trades.csv" 2>/dev/null | cut -d. -f1)"
else
    echo "   ⚠️  ml_trades.csv: NOT FOUND (no trades completed yet)"
fi

if [ -f "$BOT_DIR/data/rejected_trades.csv" ]; then
    REJECT_COUNT=$(wc -l < "$BOT_DIR/data/rejected_trades.csv")
    echo "   ✅ rejected_trades.csv: $((REJECT_COUNT - 1)) rejections"
else
    echo "   ⚠️  rejected_trades.csv: NOT FOUND"
fi
echo ""

# Analysis system status
echo "🔧 ANALYSIS SYSTEM:"
if [ -f "$BOT_DIR/data/ml_trades.csv" ]; then
    echo "   ✅ Ready to analyze - run: ./analysis_pipeline.sh"
else
    echo "   ⏳ Waiting for trading data"
    echo "   Analysis scripts are set up but need completed trades to analyze"
fi
echo ""

# Summary
echo "=== SUMMARY ==="
if [ $NETWORK_ERRORS -gt 0 ]; then
    echo "🔴 Bot has NETWORK CONNECTIVITY ISSUES"
    echo "   → Fix network/DNS issues on the server"
    echo "   → Once fixed, bot will start finding and trading tokens"
elif [ $RECENT_TRADES -eq 0 ]; then
    echo "🟡 Bot is running but NO TRADING ACTIVITY"
    echo "   → Check if APIs are returning tokens"
    echo "   → Check if filters are too strict"
else
    echo "🟢 Bot is TRADING NORMALLY"
    echo "   → Analysis pipeline is ready to use"
fi
echo ""
