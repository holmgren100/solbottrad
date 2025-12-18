#!/usr/bin/env python3
"""
Decrypt Wallet Private Key for Phantom Import
⚠️  WARNING: This reveals your private key. Keep it PRIVATE!
Anyone with this key can steal all your funds!
"""

import os
from dotenv import load_dotenv
from cryptography.fernet import Fernet

def main():
    # Load environment variables
    load_dotenv()

    encryption_key = os.getenv('WALLET_ENCRYPTION_KEY')
    encrypted_key = os.getenv('SOLANA_PRIVATE_KEY_ENCRYPTED')

    if not encryption_key or not encrypted_key:
        print("❌ Error: Wallet credentials not found in .env")
        return

    try:
        # Decrypt the private key
        fernet = Fernet(encryption_key.encode())
        private_key_bytes = fernet.decrypt(encrypted_key.encode())
        private_key = private_key_bytes.decode()

        # Display with strong warnings
        print("\n" + "=" * 70)
        print("🚨 CRITICAL SECURITY WARNING 🚨")
        print("=" * 70)
        print("⚠️  The private key below controls ALL funds in your wallet!")
        print("⚠️  NEVER share this with anyone!")
        print("⚠️  NEVER post this online, screenshot it, or send in chat!")
        print("⚠️  Anyone with this key can STEAL all your SOL and tokens!")
        print("=" * 70)
        print()

        # Confirm user wants to proceed
        confirm = input("Type 'SHOW' to display private key (or anything else to cancel): ")

        if confirm.strip().upper() != 'SHOW':
            print("\n✅ Cancelled. Private key NOT displayed.")
            return

        print("\n" + "=" * 70)
        print("🔐 YOUR PRIVATE KEY (Keep this SECRET!):")
        print("=" * 70)
        print(private_key)
        print("=" * 70)
        print()
        print("📱 To import into Phantom wallet:")
        print()
        print("1. Open Phantom browser extension or mobile app")
        print("2. Click on your wallet name (top)")
        print("3. Click 'Add / Connect Wallet'")
        print("4. Select 'Import Private Key'")
        print("5. Paste the private key above")
        print("6. Give it a name (e.g., 'Trading Bot')")
        print("7. ✅ Done! You can now send/receive from this wallet in Phantom")
        print()
        print("💡 TIP: After importing, you can:")
        print("   - View your balance")
        print("   - Send SOL to another wallet")
        print("   - Withdraw profits from trading")
        print()
        print("🔒 SECURITY REMINDER:")
        print("   - Delete this private key from your screen/clipboard after use")
        print("   - Don't leave it visible on your screen")
        print("   - The encrypted version in .env is still safe")
        print("=" * 70)
        print()

    except Exception as e:
        print(f"\n❌ Error decrypting wallet: {e}")
        print("Make sure your WALLET_ENCRYPTION_KEY and SOLANA_PRIVATE_KEY_ENCRYPTED are correct")

if __name__ == "__main__":
    main()
