#!/usr/bin/env python3
"""
Quick test script to verify API connectivity
"""

import asyncio
from src.market.dexscreener_client import DexScreenerClient

async def test_dexscreener():
    """Test DexScreener API"""
    print("Testing DexScreener API...")

    client = DexScreenerClient()

    # Test with SOL address
    sol_address = "So11111111111111111111111111111111111111112"
    print(f"\nFetching data for SOL ({sol_address})...")

    data = await client.get_token_data(sol_address)

    if data:
        print("✅ Success! Token data retrieved:")
        print(f"  Symbol: {data.get('baseToken', {}).get('symbol')}")
        print(f"  Price: ${float(data.get('priceUsd', 0)):.2f}")
        print(f"  24h Volume: ${float(data.get('volume', {}).get('h24', 0)):,.2f}")
        print(f"  Liquidity: ${float(data.get('liquidity', {}).get('usd', 0)):,.2f}")
    else:
        print("❌ Failed to retrieve token data")

if __name__ == "__main__":
    asyncio.run(test_dexscreener())
