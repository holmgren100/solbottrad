#!/usr/bin/env python3
"""
Withdraw SOL from Trading Bot Wallet
Safely send SOL from your bot wallet to another address.
"""

import os
import sys
import asyncio
import aiohttp
from dotenv import load_dotenv

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from src.blockchain.wallet_manager import WalletManager

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
                        return lamports / 1e9
        return 0.0
    except Exception as e:
        print(f"Error getting balance: {e}")
        return 0.0

async def get_latest_blockhash(rpc_url: str) -> tuple:
    """Get latest blockhash for transaction."""
    try:
        payload = {
            'jsonrpc': '2.0',
            'id': 1,
            'method': 'getLatestBlockhash',
            'params': [{'commitment': 'confirmed'}]
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
                        blockhash = data['result']['value']['blockhash']
                        last_valid_height = data['result']['value']['lastValidBlockHeight']
                        return blockhash, last_valid_height
        return None, None
    except Exception as e:
        print(f"Error getting blockhash: {e}")
        return None, None

async def send_transaction(rpc_url: str, signed_tx_base64: str) -> str:
    """Send signed transaction to network."""
    try:
        payload = {
            'jsonrpc': '2.0',
            'id': 1,
            'method': 'sendTransaction',
            'params': [
                signed_tx_base64,
                {
                    'skipPreflight': False,
                    'encoding': 'base64',
                    'maxRetries': 3
                }
            ]
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                rpc_url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    if 'result' in data:
                        return data['result']
                    elif 'error' in data:
                        raise Exception(f"RPC error: {data['error']}")
        return None
    except Exception as e:
        raise Exception(f"Error sending transaction: {e}")

async def withdraw_sol(
    wallet: WalletManager,
    destination: str,
    amount_sol: float,
    rpc_url: str
) -> str:
    """
    Withdraw SOL from bot wallet to destination address.

    Args:
        wallet: WalletManager instance
        destination: Destination wallet address
        amount_sol: Amount of SOL to send
        rpc_url: Solana RPC URL

    Returns:
        Transaction signature
    """
    try:
        from solders.pubkey import Pubkey
        from solders.system_program import transfer, TransferParams
        from solders.transaction import Transaction
        from solders.message import Message
        from solders.hash import Hash as Blockhash

        # Convert amount to lamports
        amount_lamports = int(amount_sol * 1e9)

        # Get latest blockhash
        print("🔍 Getting latest blockhash...")
        blockhash_str, last_valid_height = await get_latest_blockhash(rpc_url)
        if not blockhash_str:
            raise Exception("Failed to get blockhash")

        blockhash = Blockhash.from_string(blockhash_str)
        print(f"✅ Blockhash: {blockhash_str[:8]}...")

        # Create transfer instruction
        print(f"💸 Creating transfer: ◎{amount_sol} to {destination[:8]}...")
        transfer_ix = transfer(
            TransferParams(
                from_pubkey=wallet.keypair.pubkey(),
                to_pubkey=Pubkey.from_string(destination),
                lamports=amount_lamports
            )
        )

        # Build and sign transaction
        print("✍️  Signing transaction...")
        message = Message.new_with_blockhash([transfer_ix], wallet.keypair.pubkey(), blockhash)
        transaction = Transaction([wallet.keypair], message, blockhash)

        # Serialize transaction
        import base64
        signed_tx_bytes = bytes(transaction)
        signed_tx_base64 = base64.b64encode(signed_tx_bytes).decode('utf-8')

        # Send transaction
        print("📤 Sending transaction...")
        signature = await send_transaction(rpc_url, signed_tx_base64)

        if signature:
            print(f"✅ Transaction sent: {signature}")
            return signature
        else:
            raise Exception("Failed to send transaction")

    except Exception as e:
        raise Exception(f"Withdrawal failed: {e}")

async def main():
    # Load environment variables
    load_dotenv()

    encryption_key = os.getenv('WALLET_ENCRYPTION_KEY')
    encrypted_key = os.getenv('SOLANA_PRIVATE_KEY_ENCRYPTED')
    rpc_url = os.getenv('SOLANA_RPC_URL', 'https://api.mainnet-beta.solana.com')

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
    print("💸 SOL WITHDRAWAL TOOL")
    print("=" * 70)
    print(f"\n📍 From Wallet: {public_key}\n")

    # Check balance
    print("💰 Checking balance...")
    balance = await get_balance(rpc_url, public_key)
    print(f"   Available: ◎{balance:.6f} SOL\n")

    if balance == 0:
        print("❌ Error: Wallet has no SOL to withdraw")
        return

    # Get destination address
    print("📥 Destination address (where to send SOL):")
    destination = input("   Enter address: ").strip()

    if not destination or len(destination) < 32:
        print("❌ Error: Invalid destination address")
        return

    # Get amount
    print(f"\n💵 Amount to withdraw (available: ◎{balance:.6f}):")
    print("   TIP: Leave ~0.001 SOL for future fees")
    amount_str = input(f"   Enter amount (or 'max' for all): ").strip()

    if amount_str.lower() == 'max':
        # Leave small amount for fees
        amount_sol = max(0, balance - 0.001)
        print(f"   Withdrawing ◎{amount_sol:.6f} (leaving ◎0.001 for fees)")
    else:
        try:
            amount_sol = float(amount_str)
            if amount_sol <= 0 or amount_sol > balance:
                print("❌ Error: Invalid amount")
                return
        except ValueError:
            print("❌ Error: Invalid amount")
            return

    # Confirm
    print("\n" + "=" * 70)
    print("⚠️  CONFIRMATION REQUIRED")
    print("=" * 70)
    print(f"From:   {public_key}")
    print(f"To:     {destination}")
    print(f"Amount: ◎{amount_sol:.6f} SOL")
    print(f"Fee:    ~◎0.000005 SOL")
    print("=" * 70)

    confirm = input("\nType 'CONFIRM' to proceed: ").strip()

    if confirm.upper() != 'CONFIRM':
        print("\n❌ Withdrawal cancelled")
        return

    # Execute withdrawal
    print("\n🚀 Processing withdrawal...\n")

    try:
        signature = await withdraw_sol(wallet, destination, amount_sol, rpc_url)

        print("\n" + "=" * 70)
        print("✅ WITHDRAWAL SUCCESSFUL!")
        print("=" * 70)
        print(f"Transaction: {signature}")
        print(f"View on Solscan: https://solscan.io/tx/{signature}")
        print("\n💡 Transaction will confirm in ~10-30 seconds")
        print("=" * 70)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("Transaction failed - your funds are safe")

if __name__ == "__main__":
    asyncio.run(main())
