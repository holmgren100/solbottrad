#!/bin/bash
# Skapar perfekt formaterad data för Gemini analys

BOT_DIR="/home/user/solbottrad"
OUTPUT="$BOT_DIR/analysis/gemini_input.txt"

# Find most recent log file
if [ -f "$BOT_DIR/bot_new.log" ] && [ "$BOT_DIR/bot_new.log" -nt "$BOT_DIR/bot.log" ]; then
    LOG_FILE="$BOT_DIR/bot_new.log"
else
    LOG_FILE="$BOT_DIR/bot.log"
fi

echo "=== DATA FOR GEMINI ANALYSIS ===" > "$OUTPUT"
echo "Generated: $(date)" >> "$OUTPUT"
echo "Log file: $LOG_FILE" >> "$OUTPUT"
echo "" >> "$OUTPUT"

# Bot status check
echo "=== BOT STATUS ===" >> "$OUTPUT"
if [ $(find "$LOG_FILE" -mmin -5 2>/dev/null | wc -l) -gt 0 ]; then
    echo "✅ Bot is ACTIVE (log updated within 5 min)" >> "$OUTPUT"
else
    echo "⚠️  Bot appears STOPPED (log >5 min old)" >> "$OUTPUT"
fi

NETWORK_ERRORS=$(tail -100 "$LOG_FILE" 2>/dev/null | grep -c "Cannot connect to host")
if [ $NETWORK_ERRORS -gt 0 ]; then
    echo "❌ Network issues detected ($NETWORK_ERRORS errors)" >> "$OUTPUT"
    echo "   Bot cannot reach trading APIs - no trades possible" >> "$OUTPUT"
fi
echo "" >> "$OUTPUT"

# Latest trades
echo "=== TRADES DATA (Last 100) ===" >> "$OUTPUT"
if [ -f "$BOT_DIR/data/ml_trades.csv" ]; then
    TRADE_COUNT=$(wc -l < "$BOT_DIR/data/ml_trades.csv")
    echo "Total trades in CSV: $((TRADE_COUNT - 1))" >> "$OUTPUT"
    echo "" >> "$OUTPUT"
    tail -101 "$BOT_DIR/data/ml_trades.csv" >> "$OUTPUT"
else
    echo "⚠️  No trades yet - ml_trades.csv not found" >> "$OUTPUT"
    echo "   This means the bot hasn't completed any trades yet" >> "$OUTPUT"
fi

# Rejected tokens
echo -e "\n\n=== REJECTED TOKENS (Last 50) ===" >> "$OUTPUT"
if [ -f "$BOT_DIR/data/export_rejected.csv" ]; then
    tail -51 "$BOT_DIR/data/export_rejected.csv" >> "$OUTPUT"
else
    echo "No rejected data yet" >> "$OUTPUT"
fi

# Current stats from logs
echo -e "\n\n=== CURRENT BOT STATUS FROM LOGS ===" >> "$OUTPUT"
tail -500 "$LOG_FILE" | grep -A 6 "TRADING STATISTICS" | tail -10 >> "$OUTPUT"

echo ""
echo "✅ Gemini input ready: $OUTPUT"
echo ""
echo "📋 To use:"
echo "1. cat $OUTPUT"
echo "2. Copy output to Gemini"
echo "3. Ask Gemini to analyze and suggest optimizations"
echo "4. Give me (Claude) Gemini's output for implementation"
