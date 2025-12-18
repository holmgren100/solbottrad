"""
Secure Solana Wallet Manager
Handles wallet creation, private key encryption, and transaction signing.
"""

import os
import base58
from typing import Optional, Dict
from cryptography.fernet import Fernet
import logging

logger = logging.getLogger(__name__)


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

            # Get private key in base58 format
            private_key_bytes = bytes(self.keypair)
            private_key_base58 = base58.b58encode(private_key_bytes).decode()

            # Encrypt private key
            encrypted_private_key = self.fernet.encrypt(private_key_base58.encode()).decode()

            logger.info(f"✅ New wallet generated: {self.public_key}")

            return {
                'public_key': self.public_key,
                'encrypted_private_key': encrypted_private_key,
                'private_key_base58': private_key_base58
            }

        except ImportError:
            logger.error("❌ solders library not installed! Run: pip install -r requirements.txt")
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

    def get_public_key(self) -> Optional[str]:
        """Get the wallet's public key (address)."""
        return self.public_key

    def is_loaded(self) -> bool:
        """Check if a wallet is currently loaded."""
        return self.keypair is not None and self.public_key is not None
