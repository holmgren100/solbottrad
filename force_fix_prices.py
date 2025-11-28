#!/usr/bin/env python3
"""
Force-fix the two positions with obviously bad data.
"""

import json
import os
import sys
import asyncio
from datetime import datetime
from dotenv import load_dotenv

project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from src.market.dexscreener_client import DexScreenerClient
from src.market.jupiter_client import JupiterClient


async def get_fresh_price(token_mint: str):
    """Get current price from APIs."""
    dex_api = DexScreenerClient()
    jupiter_api = JupiterClient()

    # Try DexScreener first
    try:
        token_data = await dex_api.get_token_profile(token_mint)
        if token_data and token_data.get('price_usd'):
            return token_data['price_usd'], 'DexScreener'
    except:
        pass

    # Try Jupiter
    try:
        token_data = await jupiter_api.get_token_price_data(token_mint)
        if token_data and token_data.get('price_usd'):
            return token_data['price_usd'], 'Jupiter'
    except:
        pass

    return None, None


async def main():
    load_dotenv()

    state_file = "live_trading_state.json"

    if not os.path.exists(state_file):
        print(f"❌ State file not found: {state_file}")
        return

    print("🔍 Force-fixing positions with suspicious values...")
    print()

    with open(state_file, 'r') as f:
        state = json.load(f)

    positions = state.get('positions', {})

    # Backup
    backup_file = f"{state_file}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    with open(backup_file, 'w') as f:
        json.dump(state, f, indent=2)
    print(f"💾 Backup created: {backup_file}")
    print()

    suspicious_tokens = []

    # Find all positions with value > $1000 (clearly wrong given 0.0156 SOL balance)
    for token_addr, pos in positions.items():
        amount_usd = pos.get('amount_usd', 0)
        if amount_usd > 1000:
            suspicious_tokens.append({
                'address': token_addr,
                'amount_usd': amount_usd,
                'current_price': pos.get('current_price'),
                'quantity': pos.get('quantity'),
                'position': pos
            })

    if not suspicious_tokens:
        print("✅ No suspicious positions found!")
        return

    print(f"⚠️  Found {len(suspicious_tokens)} positions with suspicious values:")
    print()

    for token in suspicious_tokens:
        print(f"  {token['address'][:8]}...")
        print(f"    Position value: ${token['amount_usd']:,.2f}")
        print(f"    Current price: ${token['current_price']}")
        print(f"    Quantity: {token['quantity']:,.2f}")
        print()

    print("🔄 Fetching fresh prices and recalculating...")
    print()

    fixed_count = 0
    removed_count = 0

    for token in suspicious_tokens:
        token_addr = token['address']
        pos = token['position']

        print(f"  Fixing {token_addr[:8]}...")

        # Get fresh price
        new_price, source = await get_fresh_price(token_addr)

        if new_price is None:
            print(f"    ❌ Could not get price - REMOVING position")
            del positions[token_addr]
            removed_count += 1
            continue

        # Check if new price is also suspicious
        if new_price > 1000:
            print(f"    ⚠️  New price ${new_price:,.2f} also looks wrong")
            print(f"    🔄 Trying with adjusted decimals...")

            # Try dividing by powers of 10
            for divisor in [10, 100, 1000, 10000, 100000, 1000000]:
                adjusted_price = new_price / divisor
                position_value = adjusted_price * token['quantity']

                if 0.01 < position_value < 100:  # Reasonable range
                    print(f"    ✅ Found reasonable price: ${adjusted_price:.8f}")
                    print(f"       Position value: ${position_value:.2f}")
                    new_price = adjusted_price
                    break

        # Update position
        old_value = pos['amount_usd']
        new_value = new_price * token['quantity']

        pos['current_price'] = new_price
        pos['entry_price'] = new_price  # Reset entry price
        pos['amount_usd'] = new_value
        pos['highest_price'] = new_price
        pos['stop_loss'] = new_price * 0.80
        pos['take_profit'] = new_price * 1.50
        pos['trailing_stop_price'] = new_price * 0.80

        print(f"    ✅ Fixed!")
        print(f"       Old value: ${old_value:,.2f}")
        print(f"       New price: ${new_price:.8f} ({source})")
        print(f"       New value: ${new_value:.2f}")
        print()

        positions[token_addr] = pos
        fixed_count += 1

    # Save
    state['positions'] = positions

    with open(state_file, 'w') as f:
        json.dump(state, f, indent=2)

    new_portfolio = sum(p['amount_usd'] for p in positions.values())

    print("="*60)
    print(f"✅ Force-fix complete!")
    print(f"   Positions fixed: {fixed_count}")
    print(f"   Positions removed: {removed_count}")
    print(f"   New portfolio value: ${new_portfolio:.2f}")
    print()
    print("🔄 Restart your bot:")
    print("   pkill -9 python3 && python -m src.main > bot.log 2>&1 &")
    print("="*60)


if __name__ == '__main__':
    asyncio.run(main())
