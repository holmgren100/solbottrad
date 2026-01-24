"""
Alchemy API client for Solana blockchain data.
Monitors transactions, wallet activities, and token transfers.
"""

import asyncio
import aiohttp
from typing import Dict, List, Optional, Callable, Awaitable
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)


class AlchemyClient:
    """Client for interacting with Alchemy API for Solana data."""

    def __init__(self, api_key: str):
        """
        Initialize Alchemy client.

        Args:
            api_key: Alchemy API key
        """
        self.api_key = api_key
        self.base_url = f"https://solana-mainnet.g.alchemy.com/v2/{api_key}"
        self.ws_url = f"wss://solana-mainnet.g.alchemy.com/v2/{api_key}"
        self.session: Optional[aiohttp.ClientSession] = None
        self._ws_connection = None
        self._running = False

    async def _ensure_session(self):
        """Ensure aiohttp session exists."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()

    async def close(self):
        """Close the client session."""
        if self.session and not self.session.closed:
            await self.session.close()

    async def get_token_info(self, token_address: str) -> Optional[Dict]:
        """
        Get token information from Alchemy.

        Args:
            token_address: Token contract address

        Returns:
            Token information dictionary or None if failed
        """
        await self._ensure_session()

        try:
            payload = {
                "id": 1,
                "jsonrpc": "2.0",
                "method": "getAccountInfo",
                "params": [
                    token_address,
                    {"encoding": "jsonParsed"}
                ]
            }

            async with self.session.post(self.base_url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    if 'result' in data and data['result']:
                        logger.debug(f"Retrieved token info for {token_address}")
                        return data['result']
                    else:
                        logger.warning(f"No token info found for {token_address}")
                        return None
                else:
                    logger.error(f"Alchemy API error: {response.status}")
                    return None

        except Exception as e:
            logger.error(f"Error fetching token info: {e}")
            return None

    async def get_recent_transactions(
        self,
        address: str,
        limit: int = 10
    ) -> List[Dict]:
        """
        Get recent transactions for an address.

        Args:
            address: Wallet or token address
            limit: Maximum number of transactions to retrieve

        Returns:
            List of transaction dictionaries
        """
        await self._ensure_session()

        try:
            payload = {
                "id": 1,
                "jsonrpc": "2.0",
                "method": "getSignaturesForAddress",
                "params": [
                    address,
                    {"limit": limit}
                ]
            }

            async with self.session.post(self.base_url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    if 'result' in data:
                        logger.debug(f"Retrieved {len(data['result'])} transactions for {address}")
                        return data['result']

            return []

        except Exception as e:
            logger.error(f"Error fetching transactions: {e}")
            return []

    async def health_check(self) -> bool:
        """
        Check if Alchemy API is accessible.

        Returns:
            True if healthy, False otherwise
        """
        await self._ensure_session()

        try:
            payload = {
                "id": 1,
                "jsonrpc": "2.0",
                "method": "getHealth"
            }

            async with self.session.post(self.base_url, json=payload, timeout=aiohttp.ClientTimeout(total=5)) as response:
                return response.status == 200

        except Exception as e:
            logger.error(f"Alchemy health check failed: {e}")
            return False
