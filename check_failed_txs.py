#!/usr/bin/env python3
"""
Check why transactions are failing.
"""

import asyncio
import aiohttp
import os
from dotenv import load_dotenv


async def check_transaction(tx_sig: str, rpc_url: str):
    """Check transaction details."""
    payload = {
        'jsonrpc': '2.0',
        'id': 1,
        'method': 'getTransaction',
        'params': [
            tx_sig,
            {
                'encoding': 'jsonParsed',
                'maxSupportedTransactionVersion': 0
            }
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
                    return result.get('result')
    except Exception as e:
        print(f"Error: {e}")

    return None


async def get_balance(wallet_pubkey: str, rpc_url: str):
    """Get wallet SOL balance."""
    payload = {
        'jsonrpc': '2.0',
        'id': 1,
        'method': 'getBalance',
        'params': [wallet_pubkey]
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
                    lamports = result['result']['value']
                    return lamports / 1e9
    except Exception as e:
        print(f"Error: {e}")

    return 0


async def main():
    load_dotenv()

    # Failed transactions from user's message
    failed_txs = [
        "2TzvcR2AQghbYg9xL7oCwW9xgpPuEUphS6UFggpFu4ySv6C38XSqubrZLTcg",
        "zu9cF3eX21STbX1azBGZ1T9nXcut6ZC4A5CNDgcwMWr7EsQfDbg5BRD5q8E5",
        "jndkjjzkWPhtS6uD5FbUQjYYEZ514avWc4P79gCuxFMruYJ8EDERHHV734xh",
        "3pnFms7ZRSgnri2Fm3dC5vJXw4P5batXrHhHrjbnwykBvxeN5e2X2R3SX33L",
        "531PikuxBgDKgkymcV7WNGC9HDr4hjxF5K6jrLMEdTRw9tYoqUZCZSTQmfht",
        "5tYEVseUw7s9Z9TXz61C6UKLHsWfUrCUMMNXZa5MsaxEMg26vb5CKUv4jLTD",
        "ZQm4a7Fqm929AwdLTixZdXKZJtVa6nA1JyuPCLC2chDuHfPJ7EqxBaYKDinK",
    ]

    # Successful transaction
    success_tx = "2oAAVJEnvkCN3h3LMfDZ8VoC1n8ZKmaoPMZ3rpBipPJVnPfTQunqQNLWFjUo"

    rpc_url = os.getenv('SOLANA_RPC_URL', 'https://api.mainnet-beta.solana.com')

    print("🔍 Analyzing recent transactions...")
    print()

    # Check successful transaction first
    print("✅ SUCCESSFUL TRANSACTION:")
    print(f"   https://solscan.io/tx/{success_tx}")
    tx_data = await check_transaction(success_tx, rpc_url)
    if tx_data:
        if tx_data.get('meta', {}).get('err') is None:
            print("   Status: Confirmed")
            fee = tx_data['meta']['fee'] / 1e9
            print(f"   Fee paid: ◎{fee:.6f}")
        else:
            print(f"   Error: {tx_data['meta']['err']}")
    print()

    print("❌ FAILED TRANSACTIONS:")
    print()

    failure_reasons = {}

    for i, tx_sig in enumerate(failed_txs, 1):
        print(f"{i}. Checking {tx_sig[:8]}...")
        print(f"   https://solscan.io/tx/{tx_sig}")

        tx_data = await check_transaction(tx_sig, rpc_url)

        if tx_data is None:
            print("   ⚠️  Transaction not found (may have been dropped)")
            reason = "dropped_not_confirmed"
        elif tx_data.get('meta', {}).get('err'):
            error = tx_data['meta']['err']
            print(f"   ❌ Error: {error}")

            # Categorize error
            error_str = str(error)
            if 'InsufficientFunds' in error_str:
                reason = "insufficient_funds"
            elif 'Slippage' in error_str or 'slippage' in error_str:
                reason = "slippage_exceeded"
            elif 'timeout' in error_str.lower():
                reason = "timeout"
            else:
                reason = error_str
        else:
            print("   Status: Actually succeeded?")
            reason = "unknown"

        failure_reasons[reason] = failure_reasons.get(reason, 0) + 1
        print()

    # Summary
    print("="*60)
    print("FAILURE SUMMARY:")
    print()
    for reason, count in failure_reasons.items():
        print(f"  {reason}: {count} transactions")
    print()

    # Check current balance
    from src.blockchain.wallet_manager import WalletManager

    encryption_key = os.getenv('WALLET_ENCRYPTION_KEY')
    encrypted_key = os.getenv('SOLANA_PRIVATE_KEY_ENCRYPTED')

    if encryption_key and encrypted_key:
        wallet = WalletManager(encryption_key)
        wallet.load_wallet_from_encrypted_key(encrypted_key)
        wallet_pubkey = str(wallet.get_public_key())

        balance = await get_balance(wallet_pubkey, rpc_url)

        print(f"💰 Current Wallet Balance: ◎{balance:.6f} (~${balance*200:.2f})")
        print()

        if balance < 0.01:
            print("⚠️  CRITICAL: Balance too low!")
            print("   Minimum recommended: ◎0.05 ($10)")
            print("   Each transaction costs ◎0.001-0.005 in fees")
            print()
            print("   🚨 YOU NEED TO DEPOSIT MORE SOL! 🚨")
            print()
        elif balance < 0.05:
            print("⚠️  WARNING: Balance is low")
            print("   Recommended: ◎0.1+ for reliable trading")

    print("="*60)


if __name__ == '__main__':
    asyncio.run(main())
