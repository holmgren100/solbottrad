import aiohttp
import logging
from typing import List, Dict, Optional

class SolSnifferClient:
    """Client for SolSniffer API - Token discovery"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.base_url = "https://api.solsniffer.com"
        self.logger = logging.getLogger('trading_bot.solsniffer')

    async def get_new_tokens(self, limit: int = 20) -> List[Dict]:
        """Get newly listed tokens"""
        try:
            headers = {}
            if self.api_key:
                headers['Authorization'] = f'Bearer {self.api_key}'

            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/api/v1/tokens/new"
                params = {'limit': limit}

                async with session.get(url, headers=headers, params=params, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get('tokens', [])
                    else:
                        self.logger.warning(f"SolSniffer API returned status {response.status}")
                        return []
        except aiohttp.ClientConnectorError as e:
            self.logger.warning(f"Cannot connect to SolSniffer: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Error fetching new tokens from SolSniffer: {e}")
            return []

    async def get_token_info(self, token_address: str) -> Optional[Dict]:
        """Get detailed token information"""
        try:
            headers = {}
            if self.api_key:
                headers['Authorization'] = f'Bearer {self.api_key}'

            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/api/v1/tokens/{token_address}"

                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        return await response.json()
                    return None
        except Exception as e:
            self.logger.error(f"Error fetching token info: {e}")
            return None

    async def is_connected(self) -> bool:
        """Check if API is accessible"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/health", timeout=aiohttp.ClientTimeout(total=5)) as response:
                    return response.status == 200
        except:
            return False
