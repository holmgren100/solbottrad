#!/usr/bin/env python3
"""
Close all positions and clean state for fresh start.
WARNING: This will attempt to sell ALL tokens and clear state file.
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)


async def sell_all_tokens_to_sol(wallet_manager, jupiter_executor):
    """Sell all tokens back to SOL."""
    import aiohttp

    wallet_pubkey = str(wallet_manager.get_public_key())
    rpc_url = os.getenv('SOLANA_RPC_URL', 'https://api.mainnet-beta.solana.com')

    # Get all token accounts
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

    print("📊 Getting all token accounts...")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                rpc_url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    token_accounts = result.get('result', {}).get('value', [])
    except Exception as e:
        print(f"❌ Error getting token accounts: {e}")
        return

    if not token_accounts:
        print("✅ No tokens to sell")
        return

    print(f"Found {len(token_accounts)} token accounts")
    print()

    sol_mint = "So11111111111111111111111111111111111111112"
    sold_count = 0
    skipped_count = 0
    failed_count = 0

    for account in token_accounts:
        try:
            parsed_info = account['account']['data']['parsed']['info']
            token_mint = parsed_info['mint']
            token_amount = float(parsed_info['tokenAmount']['uiAmountString'] or 0)

            if token_amount == 0:
                skipped_count += 1
                continue

            print(f"  Selling {token_mint[:8]}...")
            print(f"    Amount: {token_amount:,.2f}")

            # Try to sell to SOL
            try:
                result = await jupiter_executor._execute_real_swap(
                    input_mint=token_mint,
                    output_mint=sol_mint,
                    amount_in=token_amount,
                    slippage_bps=1000  # 10% slippage (high to ensure it goes through)
                )

                if result['success']:
                    sol_received = result.get('output_amount', 0)
                    print(f"    ✅ Sold for ◎{sol_received:.6f}")
                    sold_count += 1
                else:
                    error = result.get('error', 'Unknown error')
                    print(f"    ❌ Failed: {error}")
                    failed_count += 1

            except Exception as e:
                print(f"    ❌ Error: {str(e)[:100]}")
                failed_count += 1

            print()

            # Small delay between swaps
            await asyncio.sleep(2)

        except Exception as e:
            print(f"  ❌ Error processing account: {e}")
            failed_count += 1

    print()
    print("="*60)
    print(f"✅ Sold: {sold_count}")
    print(f"❌ Failed: {failed_count}")
    print(f"⏭️  Skipped (empty): {skipped_count}")
    print("="*60)


async def main():
    load_dotenv()

    print("="*70)
    print("🧹 CLOSE ALL POSITIONS - Fresh Start Tool")
    print("="*70)
    print()
    print("⚠️  WARNING: This will:")
    print("   1. Attempt to sell ALL tokens to SOL")
    print("   2. Clear the position state file")
    print("   3. Give you a clean slate")
    print()

    # Ask for confirmation
    response = input("Are you sure you want to continue? (yes/no): ")
    if response.lower() != 'yes':
        print("❌ Cancelled")
        return

    print()
    print("Starting cleanup...")
    print()

    # Load wallet
    from src.blockchain.wallet_manager import WalletManager
    from src.blockchain.jupiter_executor import JupiterSwapExecutor

    encryption_key = os.getenv('WALLET_ENCRYPTION_KEY')
    encrypted_key = os.getenv('SOLANA_PRIVATE_KEY_ENCRYPTED')
    rpc_url = os.getenv('SOLANA_RPC_URL', 'https://api.mainnet-beta.solana.com')

    if not encryption_key or not encrypted_key:
        print("❌ Wallet keys not found in .env")
        return

    print("1️⃣  Loading wallet...")
    wallet = WalletManager(encryption_key)
    wallet.load_wallet_from_encrypted_key(encrypted_key)
    print(f"   ✅ Wallet: {str(wallet.get_public_key())[:8]}...")
    print()

    print("2️⃣  Setting up Jupiter executor...")
    executor = JupiterSwapExecutor(rpc_url, use_jito=False, paper_trading=False)
    executor.set_wallet(wallet)
    print("   ✅ Ready")
    print()

    print("3️⃣  Selling all tokens to SOL...")
    print()
    await sell_all_tokens_to_sol(wallet, executor)
    print()

    print("4️⃣  Clearing state file...")
    state_file = "live_trading_state.json"

    if os.path.exists(state_file):
        # Backup
        backup_file = f"{state_file}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        import shutil
        shutil.copy(state_file, backup_file)
        print(f"   💾 Backed up to: {backup_file}")

        # Remove
        os.remove(state_file)
        print(f"   🗑️  Removed: {state_file}")
    else:
        print("   ℹ️  No state file to remove")

    print()
    print("="*70)
    print("✅ CLEANUP COMPLETE!")
    print()
    print("Next steps:")
    print("1. Check your SOL balance:")
    print("   python3 check_wallet_balance.py")
    print()
    print("2. If you want to continue trading:")
    print("   - Deposit more SOL (◎0.5+ recommended)")
    print("   - Review settings in .env")
    print("   - Run: python3 preflight_check.py")
    print("   - Start bot: python -m src.main > bot.log 2>&1 &")
    print()
    print("3. Or take a break - the fixes will be here when ready.")
    print("="*70)


if __name__ == '__main__':
    asyncio.run(main())
