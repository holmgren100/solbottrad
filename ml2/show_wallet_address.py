#!/usr/bin/env python3
"""
Show Wallet Public Address
Quick script to display your bot's wallet address for funding/checking balance.
"""

import os
import sys
from dotenv import load_dotenv

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from src.blockchain.wallet_manager import WalletManager

def main():
    # Load environment variables
    load_dotenv()

    encryption_key = os.getenv('WALLET_ENCRYPTION_KEY')
    encrypted_key = os.getenv('SOLANA_PRIVATE_KEY_ENCRYPTED')

    if not encryption_key or not encrypted_key:
        print("❌ Error: Wallet credentials not found in .env")
        print("Required: WALLET_ENCRYPTION_KEY and SOLANA_PRIVATE_KEY_ENCRYPTED")
        return

    # Load wallet
    wallet = WalletManager(encryption_key=encryption_key)
    success = wallet.load_wallet_from_encrypted_key(encrypted_key)

    if not success:
        print("❌ Error: Failed to load wallet")
        return

    public_key = wallet.get_public_key()

    # Display info
    print("=" * 70)
    print("🔑 YOUR TRADING BOT WALLET")
    print("=" * 70)
    print(f"\n📍 Public Address:")
    print(f"   {public_key}")
    print()
    print("🔗 View on Solscan:")
    print(f"   Mainnet: https://solscan.io/account/{public_key}")
    print(f"   Devnet:  https://solscan.io/account/{public_key}?cluster=devnet")
    print()
    print("💰 To fund this wallet:")
    print(f"   1. Copy address: {public_key}")
    print("   2. Send SOL from Phantom/exchange to this address")
    print("   3. Check balance on Solscan (links above)")
    print()
    print("⚠️  IMPORTANT:")
    print("   - NEVER share your private key (encrypted or decrypted)")
    print("   - This public address is SAFE to share")
    print("   - Works on both mainnet and devnet (different balances)")
    print("=" * 70)

if __name__ == "__main__":
    main()
