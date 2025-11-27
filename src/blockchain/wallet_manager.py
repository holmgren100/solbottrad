"""
Secure Solana Wallet Manager
Handles wallet creation, private key encryption, and transaction signing.
"""

import os
import base58
from typing import Optional, Dict
from cryptography.fernet import Fernet
from ..monitoring.logger import get_logger

logger = get_logger(__name__)


class WalletManager:
    """
    Manages Solana wallet for automated trading with secure key storage.
    """

    def __init__(self, encryption_key: Optional[str] = None):
        """
        Initialize wallet manager.

        Args:
            encryption_key: Optional encryption key (generated if not provided)
        """
        self.encryption_key = encryption_key or self._generate_encryption_key()
        self.fernet = Fernet(self.encryption_key.encode() if isinstance(self.encryption_key, str) else self.encryption_key)
        self.keypair = None
        self.public_key = None

        logger.info("WalletManager initialized")

    def _generate_encryption_key(self) -> bytes:
        """Generate a new Fernet encryption key."""
        key = Fernet.generate_key()
        logger.warning(
            "⚠️  Generated new encryption key - save this securely!\n"
            f"   Add to .env: WALLET_ENCRYPTION_KEY={key.decode()}"
        )
        return key

    def generate_new_wallet(self) -> Dict[str, str]:
        """
        Generate a new Solana wallet keypair.

        Returns:
            Dictionary with public key and encrypted private key
        """
        try:
            from solders.keypair import Keypair

            # Generate new keypair
            self.keypair = Keypair()
            self.public_key = str(self.keypair.pubkey())

            # Get private key in base58 format (Phantom-compatible)
            private_key_bytes = bytes(self.keypair)
            private_key_base58 = base58.b58encode(private_key_bytes).decode()

            # Encrypt private key
            encrypted_private_key = self.fernet.encrypt(private_key_base58.encode()).decode()

            logger.info(f"✅ New wallet generated: {self.public_key}")
            logger.warning(
                "⚠️  IMPORTANT: Save these securely!\n"
                f"   Public Key (Wallet Address): {self.public_key}\n"
                f"   Add to .env: SOLANA_WALLET_ADDRESS={self.public_key}\n"
                f"   Add to .env: SOLANA_PRIVATE_KEY_ENCRYPTED={encrypted_private_key}"
            )

            return {
                'public_key': self.public_key,
                'encrypted_private_key': encrypted_private_key,
                'private_key_base58': private_key_base58  # Return once for backup, never log again
            }

        except ImportError:
            logger.error(
                "❌ solders library not installed!\n"
                "   Run: pip install -r requirements.txt"
            )
            return None
        except Exception as e:
            logger.error(f"Error generating wallet: {e}")
            return None

    def load_wallet_from_encrypted_key(self, encrypted_private_key: str) -> bool:
        """
        Load wallet from encrypted private key.

        Args:
            encrypted_private_key: Encrypted private key string

        Returns:
            True if successful
        """
        try:
            from solders.keypair import Keypair

            # Decrypt private key
            decrypted_key = self.fernet.decrypt(encrypted_private_key.encode()).decode()

            # Decode base58 private key
            private_key_bytes = base58.b58decode(decrypted_key)

            # Create keypair from bytes
            self.keypair = Keypair.from_bytes(private_key_bytes)
            self.public_key = str(self.keypair.pubkey())

            logger.info(f"✅ Wallet loaded: {self.public_key}")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to load wallet: {e}")
            return False

    def load_wallet_from_private_key(self, private_key_base58: str) -> bool:
        """
        Load wallet from unencrypted private key (e.g., from Phantom export).

        Args:
            private_key_base58: Base58-encoded private key

        Returns:
            True if successful
        """
        try:
            from solders.keypair import Keypair

            # Decode base58 private key
            private_key_bytes = base58.b58decode(private_key_base58)

            # Create keypair from bytes
            self.keypair = Keypair.from_bytes(private_key_bytes)
            self.public_key = str(self.keypair.pubkey())

            logger.info(f"✅ Wallet loaded from private key: {self.public_key}")

            # Encrypt and save for future use
            encrypted_key = self.fernet.encrypt(private_key_base58.encode()).decode()
            logger.info(
                f"💡 To use this wallet in future, add to .env:\n"
                f"   SOLANA_PRIVATE_KEY_ENCRYPTED={encrypted_key}"
            )

            return True

        except Exception as e:
            logger.error(f"❌ Failed to load wallet from private key: {e}")
            return False

    def get_public_key(self) -> Optional[str]:
        """Get the wallet's public key (address)."""
        return self.public_key

    def sign_transaction(self, transaction_data: bytes) -> Optional[bytes]:
        """
        Sign a transaction with the wallet's private key.

        Args:
            transaction_data: Transaction bytes to sign

        Returns:
            Signed transaction bytes or None if failed
        """
        if not self.keypair:
            logger.error("❌ No wallet loaded - cannot sign transaction")
            return None

        try:
            from solders.transaction import VersionedTransaction
            from solders.hash import Hash

            logger.info(f"✍️  Signing transaction with wallet {self.public_key[:8]}...")

            # Deserialize the transaction
            tx = VersionedTransaction.from_bytes(transaction_data)

            # Try creating a new signed transaction by passing the keypair directly
            # This ensures the signature is computed correctly for the message
            try:
                # Method 1: Use VersionedTransaction constructor with keypair
                signed_tx = VersionedTransaction(tx.message, [self.keypair])
                return bytes(signed_tx)
            except Exception as e:
                logger.debug(f"Method 1 failed: {e}, trying method 2...")

                # Method 2: Manual signing with proper message serialization
                # Serialize message to get the exact bytes that need to be signed
                message_bytes = bytes(tx.message)

                # Sign the message bytes
                signature = self.keypair.sign_message(message_bytes)

                # Create signed transaction
                signed_tx = VersionedTransaction.populate(tx.message, [signature])
                return bytes(signed_tx)

        except Exception as e:
            logger.error(f"Error signing transaction: {e}")
            return None

    def is_loaded(self) -> bool:
        """Check if a wallet is currently loaded."""
        return self.keypair is not None and self.public_key is not None


# Utility functions for wallet setup

def setup_trading_wallet(
    private_key: Optional[str] = None,
    encryption_key: Optional[str] = None
) -> Optional[WalletManager]:
    """
    Set up a trading wallet for the bot.

    Args:
        private_key: Optional private key (base58). If not provided, generates new wallet.
        encryption_key: Optional encryption key from .env

    Returns:
        Configured WalletManager or None if failed
    """
    try:
        wallet_manager = WalletManager(encryption_key=encryption_key)

        if private_key:
            # Check if it's encrypted or plain
            if private_key.startswith('gAAAAA'):  # Fernet encrypted format
                success = wallet_manager.load_wallet_from_encrypted_key(private_key)
            else:
                success = wallet_manager.load_wallet_from_private_key(private_key)

            if success:
                return wallet_manager
            else:
                logger.error("Failed to load wallet from provided key")
                return None
        else:
            # Generate new wallet
            wallet_info = wallet_manager.generate_new_wallet()
            if wallet_info:
                logger.warning(
                    "\n"
                    "=" * 80 + "\n"
                    "🔐 NEW TRADING WALLET CREATED\n"
                    "=" * 80 + "\n"
                    f"📍 Wallet Address: {wallet_info['public_key']}\n"
                    f"🔑 Private Key (SAVE THIS ONCE): {wallet_info['private_key_base58'][:20]}...\n"
                    "\n"
                    "⚠️  IMPORTANT SECURITY STEPS:\n"
                    "1. Copy the private key above and save it in a secure password manager\n"
                    "2. Add to .env file (NEVER commit this file!):\n"
                    f"   SOLANA_WALLET_ADDRESS={wallet_info['public_key']}\n"
                    f"   SOLANA_PRIVATE_KEY_ENCRYPTED={wallet_info['encrypted_private_key']}\n"
                    f"   WALLET_ENCRYPTION_KEY=<your_encryption_key_from_logs>\n"
                    "3. Fund this wallet with SMALL amount for testing (0.5-1 SOL)\n"
                    "4. Send SOL to: {wallet_info['public_key']}\n"
                    "\n"
                    "=" * 80 + "\n"
                )
                return wallet_manager
            else:
                logger.error("Failed to generate new wallet")
                return None

    except Exception as e:
        logger.error(f"Error setting up trading wallet: {e}")
        return None
