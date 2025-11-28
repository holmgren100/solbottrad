#!/usr/bin/env python3
"""
Fix incorrect prices in position state file.
This script checks all positions and corrects bad price data.
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from src.blockchain.wallet_manager import WalletManager
from src.market.dexscreener_client import DexScreenerClient
from src.market.jupiter_client import JupiterClient
from src.monitoring.logger import get_logger

logger = get_logger(__name__)


async def get_token_accounts(wallet_pubkey: str, rpc_url: str):
    """Get all token accounts for a wallet."""
    import aiohttp

    payload = {
        'jsonrpc': '2.0',
        'id': 1,
        'method': 'getTokenAccountsByOwner',
        'params': [
            wallet_pubkey,
            {'programId': 'TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA'},
            {'encoding': 'jsonParsed'}
        ]
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                rpc_url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get('result', {}).get('value', [])
    except Exception as e:
        print(f"Error getting token accounts: {e}")

    return []


async def validate_price(price: float, token_mint: str, token_amount: float) -> dict:
    """Validate if a price makes sense based on multiple checks."""
    issues = []

    # Check 1: Price should be positive and reasonable
    if price <= 0:
        issues.append(f"Invalid price: {price}")
    elif price > 1000000:
        issues.append(f"Suspiciously high price: ${price:,.2f}")

    # Check 2: Position value check (position > $10M is suspicious for small holdings)
    position_value = price * token_amount
    if position_value > 10000000:
        issues.append(f"Huge position value: ${position_value:,.2f} ({token_amount:,.2f} tokens @ ${price})")

    # Check 3: Check if price has too many decimal places (often indicates wrong units)
    if price > 10 and '.' in str(price):
        decimal_places = len(str(price).split('.')[1])
        if decimal_places > 2:
            issues.append(f"Too many decimals for high price: ${price}")

    return {
        'price': price,
        'is_valid': len(issues) == 0,
        'issues': issues,
        'position_value': position_value
    }


async def get_verified_price(token_mint: str, dex_api, jupiter_api):
    """Get price from multiple sources and cross-validate."""
    prices = []
    sources = []

    # Try DexScreener
    try:
        token_data = await dex_api.get_token_profile(token_mint)
        if token_data and token_data.get('price_usd'):
            prices.append(token_data['price_usd'])
            sources.append('DexScreener')
    except Exception as e:
        logger.debug(f"DexScreener failed: {e}")

    # Try Jupiter
    try:
        token_data = await jupiter_api.get_token_price_data(token_mint)
        if token_data and token_data.get('price_usd'):
            prices.append(token_data['price_usd'])
            sources.append('Jupiter')
    except Exception as e:
        logger.debug(f"Jupiter failed: {e}")

    if not prices:
        return None, None, None

    # If we have multiple prices, check if they're consistent
    if len(prices) > 1:
        price_diff_pct = abs(prices[0] - prices[1]) / max(prices[0], prices[1]) * 100
        if price_diff_pct > 50:
            print(f"  ⚠️  Price mismatch: {sources[0]}=${prices[0]:.8f}, {sources[1]}=${prices[1]:.8f} ({price_diff_pct:.1f}% diff)")
            # Use the lower price to be conservative
            return min(prices), sources[prices.index(min(prices))], True

    # Return the first valid price
    return prices[0], sources[0], False


async def main():
    load_dotenv()

    state_file = "live_trading_state.json"

    if not os.path.exists(state_file):
        print(f"❌ State file not found: {state_file}")
        print("   This script needs to run where your bot is actually running.")
        return

    print("🔍 Loading position state file...")
    print()

    with open(state_file, 'r') as f:
        state = json.load(f)

    positions = state.get('positions', {})

    if not positions:
        print("❌ No positions found in state file")
        return

    print(f"📊 Found {len(positions)} positions")
    print(f"   Portfolio value: ${sum(p.get('amount_usd', 0) for p in positions.values()):,.2f}")
    print()

    # Initialize APIs
    dex_api = DexScreenerClient()
    jupiter_api = JupiterClient()

    # Load wallet to get actual balances
    encryption_key = os.getenv('WALLET_ENCRYPTION_KEY')
    encrypted_key = os.getenv('SOLANA_PRIVATE_KEY_ENCRYPTED')
    rpc_url = os.getenv('SOLANA_RPC_URL', 'https://api.mainnet-beta.solana.com')

    wallet_balances = {}
    if encryption_key and encrypted_key:
        wallet = WalletManager(encryption_key)
        wallet.load_wallet_from_encrypted_key(encrypted_key)
        wallet_pubkey = str(wallet.get_public_key())

        print(f"👛 Wallet: {wallet_pubkey[:8]}...")
        token_accounts = await get_token_accounts(wallet_pubkey, rpc_url)

        for account in token_accounts:
            try:
                parsed_info = account['account']['data']['parsed']['info']
                token_mint = parsed_info['mint']
                token_amount = float(parsed_info['tokenAmount']['uiAmountString'] or 0)
                wallet_balances[token_mint] = token_amount
            except:
                pass

        print(f"   Found {len(wallet_balances)} tokens in wallet")
        print()

    fixes_needed = 0
    removed_count = 0
    updated_count = 0

    new_positions = {}

    for token_addr, pos in positions.items():
        print(f"  🔎 Checking {token_addr[:8]}...")

        current_price = pos.get('current_price', 0)
        entry_price = pos.get('entry_price', 0)
        quantity = pos.get('quantity', 0)
        amount_usd = pos.get('amount_usd', 0)

        # Check if token still exists in wallet
        actual_balance = wallet_balances.get(token_addr, 0)
        if actual_balance == 0:
            print(f"     ❌ Token no longer in wallet - removing position")
            removed_count += 1
            continue

        # Validate current price
        validation = await validate_price(current_price, token_addr, quantity)

        if not validation['is_valid']:
            print(f"     ⚠️  Price issues detected:")
            for issue in validation['issues']:
                print(f"        - {issue}")

            # Get fresh price
            new_price, source, had_mismatch = await get_verified_price(token_addr, dex_api, jupiter_api)

            if new_price:
                print(f"     🔄 Updating price: ${current_price:,.8f} → ${new_price:,.8f} ({source})")
                pos['current_price'] = new_price
                pos['entry_price'] = new_price  # Update entry to current (we don't know original)
                pos['amount_usd'] = new_price * actual_balance
                pos['quantity'] = actual_balance

                # Recalculate stop loss and take profit
                pos['stop_loss'] = new_price * 0.80  # -20%
                pos['take_profit'] = new_price * 1.50  # +50%
                pos['highest_price'] = new_price
                pos['trailing_stop_price'] = new_price * 0.80

                print(f"     ✅ Fixed: ${pos['amount_usd']:.2f} ({actual_balance:.2f} tokens)")
                updated_count += 1
                fixes_needed += 1
            else:
                print(f"     ❌ Could not get price - removing position")
                removed_count += 1
                continue
        else:
            # Price looks ok, but update quantity if different from wallet
            if actual_balance != quantity:
                print(f"     🔄 Updating quantity: {quantity:.2f} → {actual_balance:.2f}")
                pos['quantity'] = actual_balance
                pos['amount_usd'] = current_price * actual_balance
                updated_count += 1

        new_positions[token_addr] = pos

    # Save updated state
    if fixes_needed > 0 or removed_count > 0:
        state['positions'] = new_positions

        # Backup original
        backup_file = f"{state_file}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        with open(backup_file, 'w') as f:
            json.dump(positions, f, indent=2)
        print()
        print(f"💾 Backed up original to: {backup_file}")

        # Save fixed version
        with open(state_file, 'w') as f:
            json.dump(state, f, indent=2)

        new_portfolio_value = sum(p['amount_usd'] for p in new_positions.values())

        print(f"💾 Saved fixed state to: {state_file}")
        print()
        print("="*60)
        print(f"✅ Fixes complete!")
        print(f"   Positions updated: {updated_count}")
        print(f"   Positions removed: {removed_count} (no longer in wallet)")
        print(f"   Total positions: {len(new_positions)}")
        print(f"   New portfolio value: ${new_portfolio_value:,.2f}")
        print()
        print("🔄 Restart your bot to apply changes:")
        print("   pkill -9 python3 && python -m src.main > bot.log 2>&1 &")
        print()
    else:
        print()
        print("="*60)
        print("✅ All positions look good! No fixes needed.")
        print()


if __name__ == '__main__':
    asyncio.run(main())
