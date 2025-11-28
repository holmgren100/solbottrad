#!/usr/bin/env python3
"""
Network connectivity diagnostic tool.
Tests access to all required APIs and shows which are blocked.
"""

import asyncio
import aiohttp
import sys


async def test_endpoint(name: str, url: str):
    """Test if an endpoint is accessible."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                status = response.status
                headers = dict(response.headers)

                if status == 403 and 'x-deny-reason' in headers:
                    return {
                        'name': name,
                        'status': '❌ BLOCKED',
                        'reason': headers['x-deny-reason'],
                        'code': status
                    }
                elif status < 500:
                    return {
                        'name': name,
                        'status': '✅ ACCESSIBLE',
                        'reason': f'HTTP {status}',
                        'code': status
                    }
                else:
                    return {
                        'name': name,
                        'status': '⚠️  ERROR',
                        'reason': f'HTTP {status}',
                        'code': status
                    }
    except aiohttp.ClientConnectorError as e:
        return {
            'name': name,
            'status': '❌ FAILED',
            'reason': 'Cannot connect (DNS/Network)',
            'code': 0
        }
    except asyncio.TimeoutError:
        return {
            'name': name,
            'status': '❌ TIMEOUT',
            'reason': 'Connection timeout',
            'code': 0
        }
    except Exception as e:
        return {
            'name': name,
            'status': '❌ ERROR',
            'reason': str(e)[:50],
            'code': 0
        }


async def main():
    print("🔍 Testing network connectivity to required APIs...")
    print()

    endpoints = [
        ("Jupiter API", "https://lite-api.jup.ag/"),
        ("DexScreener API", "https://api.dexscreener.com/latest/dex/search?q=SOL"),
        ("CoinGecko API", "https://api.coingecko.com/api/v3/ping"),
        ("Solana Mainnet RPC", "https://api.mainnet-beta.solana.com"),
        ("Alchemy Solana RPC", "https://solana-mainnet.g.alchemy.com/v2/demo"),
        ("Helius RPC", "https://mainnet.helius-rpc.com/?api-key=demo"),
    ]

    tasks = [test_endpoint(name, url) for name, url in endpoints]
    results = await asyncio.gather(*tasks)

    # Print results
    print("API Connectivity Status:")
    print("=" * 70)

    blocked_count = 0
    accessible_count = 0

    for result in results:
        print(f"{result['status']:20} {result['name']:25} {result['reason']}")

        if 'BLOCKED' in result['status'] or 'FAILED' in result['status']:
            blocked_count += 1
        elif 'ACCESSIBLE' in result['status']:
            accessible_count += 1

    print("=" * 70)
    print()

    # Diagnosis
    if blocked_count == 0 and accessible_count > 0:
        print("✅ Network is OK - All APIs accessible")
        print()
        print("If you're still having issues, check:")
        print("  1. RPC rate limits")
        print("  2. API keys in .env file")
        print("  3. Bot logs for other errors")
    elif blocked_count > 0:
        print(f"❌ Network RESTRICTED - {blocked_count} APIs blocked")
        print()
        print("Your environment is blocking cryptocurrency APIs.")
        print()
        print("Solutions:")
        print("  1. Run the bot on a different server/machine")
        print("  2. Use a VPN to bypass restrictions")
        print("  3. Configure proxy settings")
        print("  4. Contact your hosting provider")
        print()
        print("The bot CANNOT function in a restricted network environment.")
    else:
        print("⚠️  Network issues detected")
        print()
        print("Check:")
        print("  1. Internet connection")
        print("  2. DNS resolution")
        print("  3. Firewall settings")

    print()


if __name__ == '__main__':
    asyncio.run(main())
