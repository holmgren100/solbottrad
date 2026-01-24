#!/bin/bash
# Update .env with new API keys

cd /root/solbottrad

# Backup current .env
cp .env .env.backup.$(date +%Y%m%d_%H%M%S)

# Add Birdeye API key
if grep -q "^BIRDEYE_API_KEY=" .env; then
    sed -i 's/^BIRDEYE_API_KEY=.*/BIRDEYE_API_KEY=3d8ad892a2e24dfe9ace09e7c2010cfe/' .env
else
    echo "BIRDEYE_API_KEY=3d8ad892a2e24dfe9ace09e7c2010cfe" >> .env
fi

# Update Solscan API key (refresh)
if grep -q "^SOLSCAN_API_KEY=" .env; then
    sed -i 's|^SOLSCAN_API_KEY=.*|SOLSCAN_API_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJjcmVhdGVkQXQiOjE3NjQ2MzQwMTg0MzYsImVtYWlsIjoiaG9sbWdyZW4xMDBAZ21haWwuY29tIiwiYWN0aW9uIjoidG9rZW4tYXBpIiwiYXBpVmVyc2lvbiI6InYyIiwiaWF0IjoxNzY0NjM0MDE4fQ.q0ppkK2lGNHqFu3X_UzNq6rcfwl7eNz4pbMnzCThXXs|' .env
else
    echo 'SOLSCAN_API_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJjcmVhdGVkQXQiOjE3NjQ2MzQwMTg0MzYsImVtYWlsIjoiaG9sbWdyZW4xMDBAZ21haWwuY29tIiwiYWN0aW9uIjoidG9rZW4tYXBpIiwiYXBpVmVyc2lvbiI6InYyIiwiaWF0IjoxNzY0NjM0MDE4fQ.q0ppkK2lGNHqFu3X_UzNq6rcfwl7eNz4pbMnzCThXXs' >> .env
fi

# Ensure MIN_ENTRY_PRICE is set correctly
if grep -q "^MIN_ENTRY_PRICE=" .env; then
    sed -i 's/^MIN_ENTRY_PRICE=.*/MIN_ENTRY_PRICE=0.0001/' .env
else
    echo "MIN_ENTRY_PRICE=0.0001" >> .env
fi

echo "✅ API keys updated in .env"
echo "📝 Backup saved to .env.backup.*"
