#!/usr/bin/env python3
"""Test Birdeye API directly to see exact error."""

import asyncio
import aiohttp
import os
from dotenv import load_dotenv

load_dotenv()

async def test_birdeye():
    api_key = os.getenv('BIRDEYE_API_KEY', '3d8ad892a2e24dfe9ace09e7c2010cfe')

    print("=" * 60)
    print("Testing Birdeye API")
    print("=" * 60)
    print(f"API Key: {api_key[:10]}...{api_key[-10:]}")
    print()

    url = "https://public-api.birdeye.so/defi/token_trending"
    params = {
        "sort_by": "volume",
        "sort_type": "desc",
        "offset": 0,
        "limit": 10
    }
    headers = {
        "X-API-KEY": api_key,
        "x-chain": "solana",
        "accept": "application/json"
    }

    print(f"URL: {url}")
    print(f"Params: {params}")
    print(f"Headers: {headers}")
    print()

    async with aiohttp.ClientSession() as session:
        print("Sending request...")
        try:
            async with session.get(url, params=params, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as response:
                print(f"Status: {response.status}")
                print(f"Headers: {dict(response.headers)}")
                print()

                text = await response.text()
                print(f"Response body:")
                print(text[:1000])

                if response.status == 200:
                    print("\n✅ SUCCESS!")
                    data = await response.json()
                    if data.get('success'):
                        tokens = data.get('data', {}).get('tokens', [])
                        print(f"✅ Got {len(tokens)} tokens")
                        if tokens:
                            print(f"First token: {tokens[0]}")
                    else:
                        print(f"❌ API returned success=false")
                elif response.status == 400:
                    print("\n❌ 400 Bad Request - Check parameters or API key")
                elif response.status == 429:
                    print("\n❌ 429 Rate Limit - Too many requests")
                elif response.status == 401:
                    print("\n❌ 401 Unauthorized - Invalid API key")
                else:
                    print(f"\n❌ Error {response.status}")

        except Exception as e:
            print(f"❌ Exception: {e}")

if __name__ == "__main__":
    asyncio.run(test_birdeye())
