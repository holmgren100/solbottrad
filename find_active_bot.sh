#!/bin/bash
# Hittar var den aktiva boten körs och vilken loggfil som används

BOT_DIR="/home/user/solbottrad"

# Kolla båda loggfilerna och använd den senaste
if [ -f "$BOT_DIR/bot_new.log" ] && [ -f "$BOT_DIR/bot.log" ]; then
    # Jämför modification times
    if [ "$BOT_DIR/bot_new.log" -nt "$BOT_DIR/bot.log" ]; then
        echo "$BOT_DIR" "bot_new.log"
    else
        echo "$BOT_DIR" "bot.log"
    fi
elif [ -f "$BOT_DIR/bot_new.log" ]; then
    echo "$BOT_DIR" "bot_new.log"
elif [ -f "$BOT_DIR/bot.log" ]; then
    echo "$BOT_DIR" "bot.log"
else
    echo "$BOT_DIR" "bot.log"  # Default
fi
