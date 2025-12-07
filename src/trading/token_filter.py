"""
Token Blacklist/Whitelist System - Filter tokens based on manual lists.

IMPORTANT: This is INFRASTRUCTURE ONLY - disabled by default.
Enable via .env when ready to use filtering.
"""

from typing import Set, List
import json
import os
from ..monitoring.logger import get_logger

logger = get_logger(__name__)


class TokenFilter:
    """
    Manage blacklist and whitelist for token filtering.

    Blacklist: Tokens to NEVER trade (known scams, rugs, etc.)
    Whitelist: Tokens to ALWAYS allow (overrides other filters)

    Usage:
        filter = TokenFilter()
        if filter.is_blacklisted(token_address):
            reject_token()
        if filter.is_whitelisted(token_address):
            allow_token()
    """

    def __init__(
        self,
        blacklist_file: str = 'data/token_blacklist.json',
        whitelist_file: str = 'data/token_whitelist.json'
    ):
        """
        Initialize token filter.

        Args:
            blacklist_file: Path to blacklist JSON file
            whitelist_file: Path to whitelist JSON file
        """
        self.blacklist_file = blacklist_file
        self.whitelist_file = whitelist_file

        self.blacklist: Set[str] = set()
        self.whitelist: Set[str] = set()

        # Load existing lists
        self.load_lists()

        logger.info(
            f"🚫 Token Filter initialized: "
            f"{len(self.blacklist)} blacklisted, {len(self.whitelist)} whitelisted"
        )

    def is_blacklisted(self, token_address: str) -> bool:
        """
        Check if token is blacklisted.

        Args:
            token_address: Token contract address

        Returns:
            True if token is blacklisted
        """
        return token_address in self.blacklist

    def is_whitelisted(self, token_address: str) -> bool:
        """
        Check if token is whitelisted.

        Args:
            token_address: Token contract address

        Returns:
            True if token is whitelisted
        """
        return token_address in self.whitelist

    def add_to_blacklist(self, token_address: str, reason: str = ''):
        """
        Add token to blacklist.

        Args:
            token_address: Token contract address
            reason: Reason for blacklisting (optional)
        """
        self.blacklist.add(token_address)
        self.save_lists()

        logger.warning(
            f"🚫 Added to BLACKLIST: {token_address[:8]}... "
            f"{f'({reason})' if reason else ''}"
        )

    def add_to_whitelist(self, token_address: str, reason: str = ''):
        """
        Add token to whitelist.

        Args:
            token_address: Token contract address
            reason: Reason for whitelisting (optional)
        """
        self.whitelist.add(token_address)
        self.save_lists()

        logger.info(
            f"✅ Added to WHITELIST: {token_address[:8]}... "
            f"{f'({reason})' if reason else ''}"
        )

    def remove_from_blacklist(self, token_address: str):
        """Remove token from blacklist."""
        if token_address in self.blacklist:
            self.blacklist.remove(token_address)
            self.save_lists()
            logger.info(f"Removed from blacklist: {token_address[:8]}...")

    def remove_from_whitelist(self, token_address: str):
        """Remove token from whitelist."""
        if token_address in self.whitelist:
            self.whitelist.remove(token_address)
            self.save_lists()
            logger.info(f"Removed from whitelist: {token_address[:8]}...")

    def clear_blacklist(self):
        """Clear all blacklisted tokens."""
        count = len(self.blacklist)
        self.blacklist.clear()
        self.save_lists()
        logger.info(f"Cleared blacklist: {count} tokens removed")

    def clear_whitelist(self):
        """Clear all whitelisted tokens."""
        count = len(self.whitelist)
        self.whitelist.clear()
        self.save_lists()
        logger.info(f"Cleared whitelist: {count} tokens removed")

    def get_blacklist(self) -> List[str]:
        """Get list of blacklisted tokens."""
        return list(self.blacklist)

    def get_whitelist(self) -> List[str]:
        """Get list of whitelisted tokens."""
        return list(self.whitelist)

    def save_lists(self):
        """Save blacklist and whitelist to JSON files."""
        try:
            # Create data directory if needed
            os.makedirs(os.path.dirname(self.blacklist_file), exist_ok=True)

            # Save blacklist
            with open(self.blacklist_file, 'w') as f:
                json.dump(list(self.blacklist), f, indent=2)

            # Save whitelist
            with open(self.whitelist_file, 'w') as f:
                json.dump(list(self.whitelist), f, indent=2)

            logger.debug(
                f"💾 Token filter lists saved: "
                f"{len(self.blacklist)} blacklisted, {len(self.whitelist)} whitelisted"
            )

        except Exception as e:
            logger.error(f"❌ Error saving token filter lists: {e}", exc_info=True)

    def load_lists(self):
        """Load blacklist and whitelist from JSON files."""
        try:
            # Load blacklist
            if os.path.exists(self.blacklist_file):
                with open(self.blacklist_file, 'r') as f:
                    self.blacklist = set(json.load(f))
                logger.info(f"✅ Loaded blacklist: {len(self.blacklist)} tokens")
            else:
                logger.info(f"📝 No existing blacklist at {self.blacklist_file}")

            # Load whitelist
            if os.path.exists(self.whitelist_file):
                with open(self.whitelist_file, 'r') as f:
                    self.whitelist = set(json.load(f))
                logger.info(f"✅ Loaded whitelist: {len(self.whitelist)} tokens")
            else:
                logger.info(f"📝 No existing whitelist at {self.whitelist_file}")

        except Exception as e:
            logger.error(f"❌ Error loading token filter lists: {e}", exc_info=True)
            logger.warning("⚠️  Starting with empty filter lists")
