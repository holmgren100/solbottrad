#!/usr/bin/env python3
"""
Check Wallet Balance on Mainnet and Devnet
Shows SOL balance and value in USD for both networks.
"""

import os
import sys
import asyncio
import aiohttp
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from blockchain.wallet_manager import WalletManager

async def get_balance(rpc_url: str, public_key: str) -> float:
    """Get SOL balance from RPC."""
    try:
        payload = {
            'jsonrpc': '2.0',
            'id': 1,
            'method': 'getBalance',
            'params': [public_key]
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                rpc_url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    if 'result' in data:
                        lamports = data['result']['value']
                        return lamports / 1e9  # Convert to SOL
        return 0.0
    except Exception as e:
        print(f"Error getting balance: {e}")
        return 0.0

async def get_sol_price() -> float:
    """Get current SOL price from CoinGecko."""
    try:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                if response.status == 200:
                    data = await response.json()
                    return data['solana']['usd']
        return 200.0  # Fallback price
    except:
        return 200.0  # Fallback price

async def main():
    # Load environment variables
    load_dotenv()

    encryption_key = os.getenv('WALLET_ENCRYPTION_KEY')
    encrypted_key = os.getenv('SOLANA_PRIVATE_KEY_ENCRYPTED')

    if not encryption_key or not encrypted_key:
        print("❌ Error: Wallet credentials not found in .env")
        return

    # Load wallet
    wallet = WalletManager(encryption_key=encryption_key)
    success = wallet.load_wallet_from_encrypted_key(encrypted_key)

    if not success:
        print("❌ Error: Failed to load wallet")
        return

    public_key = wallet.get_public_key()

    print("=" * 70)
    print("💰 WALLET BALANCE CHECK")
    print("=" * 70)
    print(f"\n📍 Wallet: {public_key}\n")

    # Get SOL price
    print("💵 Fetching SOL price...")
    sol_price = await get_sol_price()
    print(f"   Current SOL price: ${sol_price:,.2f}\n")

    # RPC endpoints
    mainnet_rpc = os.getenv('SOLANA_RPC_URL', 'https://api.mainnet-beta.solana.com')
    devnet_rpc = 'https://api.devnet.solana.com'

    # Check mainnet balance
    print("🌐 Checking MAINNET balance...")
    mainnet_balance = await get_balance(mainnet_rpc, public_key)
    mainnet_usd = mainnet_balance * sol_price

    print(f"   SOL:  ◎{mainnet_balance:.6f}")
    print(f"   USD:  ${mainnet_usd:,.2f}")
    print(f"   Link: https://solscan.io/account/{public_key}")
    print()

    # Check devnet balance
    print("🧪 Checking DEVNET balance...")
    devnet_balance = await get_balance(devnet_rpc, public_key)

    print(f"   SOL:  ◎{devnet_balance:.6f} (test SOL, no real value)")
    print(f"   Link: https://solscan.io/account/{public_key}?cluster=devnet")
    print()

    # Summary
    print("=" * 70)
    print("📊 SUMMARY")
    print("=" * 70)

    if mainnet_balance > 0:
        print(f"✅ Mainnet funded: ◎{mainnet_balance:.6f} (${mainnet_usd:,.2f})")
        print("   Ready for live trading!")
    else:
        print("⚠️  Mainnet balance is ZERO")
        print(f"   Send SOL to: {public_key}")
        print("   From Phantom, exchange, or another wallet")

    if devnet_balance > 0:
        print(f"\n✅ Devnet funded: ◎{devnet_balance:.6f} (test SOL)")
    else:
        print("\n💧 Devnet unfunded - get free SOL from:")
        print("   https://faucet.solana.com/")

    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(main())
