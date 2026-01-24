#!/bin/bash
# Städa upp gamla loggfiler

echo "🧹 Städar upp gamla loggfiler..."

cd /root/solbottrad || exit 1

# Skapa backup-mapp
mkdir -p old_logs

# Flytta gamla loggar
if [ -f "bot.log" ]; then
    mv bot.log old_logs/
    echo "✅ Flyttade bot.log → old_logs/"
fi

if [ -f "bot_output.log" ]; then
    mv bot_output.log old_logs/
    echo "✅ Flyttade bot_output.log → old_logs/"
fi

echo ""
echo "📝 Aktiv loggfil: /root/solbottrad/trading_bot.log"
echo ""
echo "🎯 Använd detta kommando för live logs:"
echo "   tail -f /root/solbottrad/trading_bot.log"
echo ""
echo "✅ Klart!"
