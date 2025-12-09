#!/bin/bash
echo "=== Checking Birdeye API Fix ==="
echo ""

cd /root/solbottrad

echo "1. Current git commit:"
git log -1 --oneline

echo ""
echo "2. Checking birdeye_client.py for correct endpoint:"
grep -n "defi/token_trending" src/market/birdeye_client.py && echo "✅ FOUND correct endpoint" || echo "❌ MISSING correct endpoint"

echo ""
echo "3. Checking for x-chain header:"
grep -n '"x-chain": "solana"' src/market/birdeye_client.py && echo "✅ FOUND x-chain header" || echo "❌ MISSING x-chain header"

echo ""
echo "4. Checking for volume24hUSD (correct field):"
grep -n "volume24hUSD" src/market/birdeye_client.py && echo "✅ FOUND correct field" || echo "❌ MISSING correct field"

echo ""
echo "5. Latest git commits:"
git log --oneline -5

echo ""
echo "6. Git status:"
git status

echo ""
echo "7. Python cache cleared:"
find . -type d -name "__pycache__" | wc -l
echo "   (should be 0 after clearing)"
