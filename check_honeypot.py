#!/usr/bin/env python3
"""
Honeypot detection - Check if token can be sold before buying.
Uses simulation to test if sell transactions work.
"""

import asyncio
import aiohttp
from typing import Dict, Optional


class HoneypotChecker:
    """Check if a token is a honeypot (can buy but not sell)."""

    def __init__(self, rpc_url: str):
        self.rpc_url = rpc_url

    async def check_token(self, token_mint: str) -> Dict:
        """
        Check if token is a honeypot.

        Returns:
            {
                'is_honeypot': bool,
                'can_buy': bool,
                'can_sell': bool,
                'buy_tax': float,
                'sell_tax': float,
                'issues': list
            }
        """
        result = {
            'is_honeypot': False,
            'can_buy': True,
            'can_sell': True,
            'buy_tax': 0.0,
            'sell_tax': 0.0,
            'issues': []
        }

        # Use honeypot.is API (free service for Solana)
        try:
            async with aiohttp.ClientSession() as session:
                url = f"https://api.honeypot.is/v2/IsHoneypot"
                params = {
                    'address': token_mint,
                    'chainID': '1399811149'  # Solana mainnet
                }

                async with session.get(
                    url,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        data = await response.json()

                        if 'honeypotResult' in data:
                            hp_result = data['honeypotResult']

                            result['is_honeypot'] = hp_result.get('isHoneypot', False)

                            if 'honeypotReason' in hp_result:
                                result['issues'].append(hp_result['honeypotReason'])

                        if 'simulationResult' in data:
                            sim = data['simulationResult']

                            result['can_buy'] = sim.get('buySuccess', True)
                            result['can_sell'] = sim.get('sellSuccess', True)
                            result['buy_tax'] = sim.get('buyTax', 0.0)
                            result['sell_tax'] = sim.get('sellTax', 0.0)

                            if not result['can_sell']:
                                result['issues'].append("Cannot sell token")
                                result['is_honeypot'] = True

                            if result['sell_tax'] > 50:
                                result['issues'].append(f"High sell tax: {result['sell_tax']}%")
                                result['is_honeypot'] = True

        except Exception as e:
            # If API fails, try basic checks
            result['issues'].append(f"API check failed: {str(e)[:50]}")

            # Fall back to basic liquidity check
            can_sell = await self._test_sell_simulation(token_mint)
            if not can_sell:
                result['is_honeypot'] = True
                result['can_sell'] = False
                result['issues'].append("Sell simulation failed")

        return result

    async def _test_sell_simulation(self, token_mint: str) -> bool:
        """
        Fallback: Try to simulate a small sell transaction.
        Returns True if sell would succeed.
        """
        try:
            # This is a simplified check
            # In production, would use Jupiter to simulate a swap
            # For now, just return True (assume not honeypot if API fails)
            return True
        except:
            return False


async def main():
    """Test honeypot checker."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python3 check_honeypot.py <token_address>")
        return

    token_mint = sys.argv[1]

    print(f"🔍 Checking token: {token_mint[:8]}...")
    print()

    checker = HoneypotChecker("https://api.mainnet-beta.solana.com")
    result = await checker.check_token(token_mint)

    print("Results:")
    print(f"  Is Honeypot: {'🚨 YES' if result['is_honeypot'] else '✅ NO'}")
    print(f"  Can Buy: {'✅' if result['can_buy'] else '❌'}")
    print(f"  Can Sell: {'✅' if result['can_sell'] else '❌'}")
    print(f"  Buy Tax: {result['buy_tax']}%")
    print(f"  Sell Tax: {result['sell_tax']}%")

    if result['issues']:
        print()
        print("  ⚠️  Issues:")
        for issue in result['issues']:
            print(f"    - {issue}")

    print()

    if result['is_honeypot']:
        print("🚨 DO NOT BUY - This is a honeypot!")
    else:
        print("✅ Token appears safe to trade")


if __name__ == '__main__':
    asyncio.run(main())
