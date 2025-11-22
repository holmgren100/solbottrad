import aiohttp
import logging
from typing import Optional, Dict, List

class AlchemyClient:
    """Client for Alchemy API - Solana blockchain data"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = f"https://solana-mainnet.g.alchemy.com/v2/{api_key}"
        self.logger = logging.getLogger('trading_bot.alchemy')

    async def get_token_balance(self, wallet_address: str, token_address: str) -> Optional[float]:
        """Get token balance for a wallet"""
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "getTokenAccountsByOwner",
                    "params": [
                        wallet_address,
                        {"mint": token_address},
                        {"encoding": "jsonParsed"}
                    ]
                }

                async with session.post(self.base_url, json=payload) as response:
                    data = await response.json()

                    if 'result' in data and data['result']['value']:
                        token_amount = data['result']['value'][0]['account']['data']['parsed']['info']['tokenAmount']
                        return float(token_amount['uiAmount'])

            return 0.0
        except Exception as e:
            self.logger.error(f"Error fetching token balance: {e}")
            return None

    async def get_recent_transactions(self, address: str, limit: int = 10) -> List[Dict]:
        """Get recent transactions for an address"""
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "getSignaturesForAddress",
                    "params": [address, {"limit": limit}]
                }

                async with session.post(self.base_url, json=payload) as response:
                    data = await response.json()

                    if 'result' in data:
                        return data['result']

            return []
        except Exception as e:
            self.logger.error(f"Error fetching transactions: {e}")
            return []

    async def is_connected(self) -> bool:
        """Check if API is accessible"""
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "getHealth"
                }

                async with session.post(self.base_url, json=payload, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    return response.status == 200
        except Exception as e:
            self.logger.error(f"Alchemy connection check failed: {e}")
            return False
