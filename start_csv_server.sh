#!/bin/bash
# Start HTTP server för CSV-filer
# Claude Code kan då använda WebFetch för att läsa live data!

PORT=8765
DATA_DIR="/home/user/solbottrad/data"

echo "🌐 Starting HTTP server on port $PORT..."
echo "📂 Serving files from: $DATA_DIR"
echo ""
echo "🔗 Access URLs:"
echo "   http://$(curl -s ifconfig.me):$PORT/ml_trades.csv"
echo "   http://$(curl -s ifconfig.me):$PORT/rejected_trades.csv"
echo ""
echo "⚠️  WARNING: This exposes your data publicly!"
echo "💡 For production, add nginx with basic auth or IP whitelist"
echo ""

cd "$DATA_DIR"
python3 -m http.server $PORT
