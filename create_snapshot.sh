#!/bin/bash
# Tar senaste rader från bot.log och sparar med timestamp för Claude Code analys

OUTPUT_DIR="/home/user/solbottrad/analysis/live"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BOT_DIR="/home/user/solbottrad"

# Find most recent log file
if [ -f "$BOT_DIR/bot_new.log" ] && [ "$BOT_DIR/bot_new.log" -nt "$BOT_DIR/bot.log" ]; then
    LOG_FILE="$BOT_DIR/bot_new.log"
else
    LOG_FILE="$BOT_DIR/bot.log"
fi

# Senaste errors/warnings/critical
echo "=== RECENT ERRORS/WARNINGS ===" > "$OUTPUT_DIR/latest_snapshot.txt"
echo "Log file: $LOG_FILE" >> "$OUTPUT_DIR/latest_snapshot.txt"
echo "" >> "$OUTPUT_DIR/latest_snapshot.txt"
tail -2000 "$LOG_FILE" | grep -E "ERROR|WARNING|CRITICAL" | tail -100 >> "$OUTPUT_DIR/latest_snapshot.txt"

# Senaste trades
echo -e "\n=== RECENT TRADES ===" >> "$OUTPUT_DIR/latest_snapshot.txt"
tail -2000 "$LOG_FILE" | grep -E "Position opened|Position closed|NUCLEAR|MOONSHOT EXCEPTION|INCUBATOR" | tail -50 >> "$OUTPUT_DIR/latest_snapshot.txt"
if [ $(tail -2000 "$LOG_FILE" | grep -E "Position opened|Position closed" | wc -l) -eq 0 ]; then
    echo "No trading activity yet" >> "$OUTPUT_DIR/latest_snapshot.txt"
fi

# Stats
echo -e "\n=== LATEST STATS ===" >> "$OUTPUT_DIR/latest_snapshot.txt"
tail -500 "$LOG_FILE" | grep -A 6 "TRADING STATISTICS" | tail -10 >> "$OUTPUT_DIR/latest_snapshot.txt"

# Nuclear stops
echo -e "\n=== NUCLEAR STOPS ===" >> "$OUTPUT_DIR/latest_snapshot.txt"
tail -2000 "$LOG_FILE" | grep "NUCLEAR STOP" | tail -10 >> "$OUTPUT_DIR/latest_snapshot.txt"
if [ $(tail -2000 "$LOG_FILE" | grep "NUCLEAR STOP" | wc -l) -eq 0 ]; then
    echo "None yet" >> "$OUTPUT_DIR/latest_snapshot.txt"
fi

# Step-up tiers
echo -e "\n=== STEP-UP TIERS ===" >> "$OUTPUT_DIR/latest_snapshot.txt"
tail -2000 "$LOG_FILE" | grep "Step-up tier" | tail -10 >> "$OUTPUT_DIR/latest_snapshot.txt"
if [ $(tail -2000 "$LOG_FILE" | grep "Step-up tier" | wc -l) -eq 0 ]; then
    echo "None yet" >> "$OUTPUT_DIR/latest_snapshot.txt"
fi

# Moonshot exceptions
echo -e "\n=== MOONSHOT EXCEPTIONS (APPROVED) ===" >> "$OUTPUT_DIR/latest_snapshot.txt"
tail -2000 "$LOG_FILE" | grep "MOONSHOT EXCEPTION!" | grep -v "No moonshot" | tail -10 >> "$OUTPUT_DIR/latest_snapshot.txt"
if [ $(tail -2000 "$LOG_FILE" | grep "MOONSHOT EXCEPTION!" | grep -v "No moonshot" | wc -l) -eq 0 ]; then
    echo "None yet (waiting for token with LP burned 100%)" >> "$OUTPUT_DIR/latest_snapshot.txt"
fi

# Moonshot rejections
echo -e "\n=== MOONSHOT REJECTIONS (LP 0%) ===" >> "$OUTPUT_DIR/latest_snapshot.txt"
tail -2000 "$LOG_FILE" | grep "No moonshot exception (LP 0%" | tail -10 >> "$OUTPUT_DIR/latest_snapshot.txt"

# Incubator
echo -e "\n=== INCUBATOR ADDED ===" >> "$OUTPUT_DIR/latest_snapshot.txt"
tail -2000 "$LOG_FILE" | grep "INCUBATOR: Added" | tail -10 >> "$OUTPUT_DIR/latest_snapshot.txt"
if [ $(tail -2000 "$LOG_FILE" | grep "INCUBATOR: Added" | wc -l) -eq 0 ]; then
    echo "None yet (criteria may be too strict)" >> "$OUTPUT_DIR/latest_snapshot.txt"
fi

echo -e "\n=== INCUBATOR TRIGGERS ===" >> "$OUTPUT_DIR/latest_snapshot.txt"
tail -2000 "$LOG_FILE" | grep "INCUBATOR.*TRIGGER" | tail -10 >> "$OUTPUT_DIR/latest_snapshot.txt"
if [ $(tail -2000 "$LOG_FILE" | grep "INCUBATOR.*TRIGGER" | wc -l) -eq 0 ]; then
    echo "None yet (no tokens in incubator to trigger)" >> "$OUTPUT_DIR/latest_snapshot.txt"
fi

echo "✅ Snapshot saved to $OUTPUT_DIR/latest_snapshot.txt"
