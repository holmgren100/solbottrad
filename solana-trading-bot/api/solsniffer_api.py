import requests
import aiohttp
import time
from typing import Dict, Any, Optional
from utils.logger import setup_logger
from config.settings import settings
from exceptions.custom_exceptions import APIError, RateLimitExceededError
from utils.rate_limiter import RateLimiter

class SolSnifferAPI:
    """
    API client for SolSniffer with both async and sync capabilities.
    Includes rate limiting and comprehensive error handling.
    """

    def __init__(self):
        self.logger = setup_logger(__name__)
        self.api_key = settings.SOLSNIFFER_API_KEY
        self.base_url = "https://api.solsniffer.com/v1"  # Replace with actual URL
        self.rate_limiter = RateLimiter(calls_per_second=2)
        
        # Headers for API requests
        self.headers = {
            "api-key": self.api_key,
            "Content-Type": "application/json",
            "User-Agent": "SolanaBot/1.0"
        }
        
        # Rate limiting for sync methods
        self.rate_limit = {
            "calls": 0,
            "reset_time": time.time() + 60  # Reset every 60 seconds
        }
        
        self.logger.info("SolSnifferAPI initialized")

    # ASYNC METHODS
    async def get_token_info(self, token_address: str) -> Dict[str, Any]:
        """
        Get token information using async HTTP.
        
        Args:
            token_address: The token address to query
            
        Returns:
            Dict containing token information
            
        Raises:
            APIError: If the request fails
        """
        try:
            await self.rate_limiter.wait_if_needed()
            url = f"{self.base_url}/token/{token_address}"
            self.logger.debug(f"Request URL: {url}")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers) as response:
                    response_text = await response.text()
                    self.logger.debug(f"Response: {response_text}")
                    
                    if response.status == 200:
                        data = await response.json()
                        self.logger.debug(f"Successfully fetched token info for {token_address}")
                        return data
                    else:
                        error_msg = f"Error fetching token info: Status {response.status}"
                        self.logger.error(error_msg)
                        raise APIError(error_msg)
                        
        except aiohttp.ClientError as e:
            error_msg = f"Network error fetching token info: {str(e)}"
            self.logger.error(error_msg)
            raise APIError(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error fetching token info: {str(e)}"
            self.logger.error(error_msg)
            raise APIError(error_msg)

    async def get_market_data(self, token_address: str) -> Dict[str, Any]:
        """Get market data for a token using async HTTP."""
        try:
            await self.rate_limiter.wait_if_needed()
            url = f"{self.base_url}/market/{token_address}"
            self.logger.debug(f"Fetching market data from: {url}")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        self.logger.debug(f"Successfully fetched market data for {token_address}")
                        return data
                    else:
                        error_msg = f"Error fetching market data: Status {response.status}"
                        self.logger.error(error_msg)
                        raise APIError(error_msg)
                        
        except aiohttp.ClientError as e:
            error_msg = f"Network error fetching market data: {str(e)}"
            self.logger.error(error_msg)
            raise APIError(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error fetching market data: {str(e)}"
            self.logger.error(error_msg)
            raise APIError(error_msg)

    async def get_new_tokens(self) -> Dict[str, Any]:
        """Get newly listed tokens using async HTTP."""
        try:
            await self.rate_limiter.wait_if_needed()
            url = f"{self.base_url}/tokens/new"
            self.logger.debug(f"Fetching new tokens from: {url}")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        self.logger.debug("Successfully fetched new tokens")
                        return data
                    else:
                        error_msg = f"Error fetching new tokens: Status {response.status}"
                        self.logger.error(error_msg)
                        raise APIError(error_msg)
                        
        except aiohttp.ClientError as e:
            error_msg = f"Network error fetching new tokens: {str(e)}"
            self.logger.error(error_msg)
            raise APIError(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error fetching new tokens: {str(e)}"
            self.logger.error(error_msg)
            raise APIError(error_msg)

    async def get_token_holders(self, token_address: str) -> Dict[str, Any]:
        """Get token holders using async HTTP."""
        try:
            await self.rate_limiter.wait_if_needed()
            url = f"{self.base_url}/token/{token_address}/holders"
            self.logger.debug(f"Fetching token holders from: {url}")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        self.logger.debug(f"Successfully fetched holders for {token_address}")
                        return data
                    else:
                        error_msg = f"Error fetching token holders: Status {response.status}"
                        self.logger.error(error_msg)
                        raise APIError(error_msg)
                        
        except aiohttp.ClientError as e:
            error_msg = f"Network error fetching token holders: {str(e)}"
            self.logger.error(error_msg)
            raise APIError(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error fetching token holders: {str(e)}"
            self.logger.error(error_msg)
            raise APIError(error_msg)

    async def get_recent_transactions(self, token_address: str) -> Dict[str, Any]:
        """Get recent transactions using async HTTP."""
        try:
            await self.rate_limiter.wait_if_needed()
            url = f"{self.base_url}/transactions/{token_address}"
            self.logger.debug(f"Fetching recent transactions from: {url}")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        self.logger.debug(f"Successfully fetched transactions for {token_address}")
                        return data
                    else:
                        error_msg = f"Error fetching transactions: Status {response.status}"
                        self.logger.error(error_msg)
                        raise APIError(error_msg)
                        
        except aiohttp.ClientError as e:
            error_msg = f"Network error fetching transactions: {str(e)}"
            self.logger.error(error_msg)
            raise APIError(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error fetching transactions: {str(e)}"
            self.logger.error(error_msg)
            raise APIError(error_msg)

    async def search_tokens(self, query: str) -> Dict[str, Any]:
        """Search for tokens using async HTTP."""
        try:
            await self.rate_limiter.wait_if_needed()
            url = f"{self.base_url}/search"
            params = {"q": query}
            self.logger.debug(f"Searching tokens with query: {query}")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        self.logger.debug(f"Successfully searched tokens for: {query}")
                        return data
                    else:
                        error_msg = f"Error searching tokens: Status {response.status}"
                        self.logger.error(error_msg)
                        raise APIError(error_msg)
                        
        except aiohttp.ClientError as e:
            error_msg = f"Network error searching tokens: {str(e)}"
            self.logger.error(error_msg)
            raise APIError(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error searching tokens: {str(e)}"
            self.logger.error(error_msg)
            raise APIError(error_msg)

    # SYNC METHODS
    def _check_rate_limit(self):
        """Check and update rate limit for sync methods"""
        current_time = time.time()
        if current_time > self.rate_limit["reset_time"]:
            self.rate_limit = {
                "calls": 0,
                "reset_time": current_time + 60
            }

        if self.rate_limit["calls"] >= 30:  # 30 calls per minute
            raise RateLimitExceededError("SolSniffer API rate limit exceeded")

        self.rate_limit["calls"] += 1

    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make API request with rate limiting for sync methods"""
        self._check_rate_limit()

        try:
            url = f"{self.base_url}/{endpoint}"
            self.logger.debug(f"Making sync request to: {url}")
            
            response = requests.get(url, headers=self.headers, params=params, timeout=30)

            if response.status_code == 429:
                raise RateLimitExceededError("SolSniffer API rate limit exceeded")
            elif response.status_code == 200:
                data = response.json()
                self.logger.debug(f"Successfully made sync request to: {endpoint}")
                return data
            else:
                error_msg = f"SolSniffer API error: {response.status_code}"
                self.logger.error(error_msg)
                raise APIError(error_msg)

        except requests.RequestException as e:
            error_msg = f"Network error in sync request: {str(e)}"
            self.logger.error(error_msg)
            raise APIError(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error in sync request: {str(e)}"
            self.logger.error(error_msg)
            raise APIError(error_msg)

    def get_token_data(self, token_address: str) -> Dict[str, Any]:
        """
        Fetch token data from SolSniffer API (sync version).
        This is an alias for get_token_info for backward compatibility.
        """
        try:
            return self._make_request(f"token/{token_address}")
        except Exception as e:
            self.logger.error(f"Error fetching token data: {str(e)}")
            raise

    def get_token_info_sync(self, token_address: str) -> Dict[str, Any]:
        """Get token information (sync version)"""
        return self._make_request(f"token/{token_address}")

    def get_market_data_sync(self, token_address: str) -> Dict[str, Any]:
        """Get market data for token (sync version)"""
        return self._make_request(f"market/{token_address}")

    def get_recent_transactions_sync(self, token_address: str) -> Dict[str, Any]:
        """Get recent transactions for token (sync version)"""
        return self._make_request(f"transactions/{token_address}")

    def search_tokens_sync(self, query: str) -> Dict[str, Any]:
        """Search for tokens (sync version)"""
        return self._make_request("search", {"q": query})

# Test function
async def test_solsniffer():
    """Test function for SolSniffer API"""
    # Test token address (replace with a valid one)
    test_token = "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263"

    api = SolSnifferAPI()
    try:
        # Test async methods
        token_info = await api.get_token_info(test_token)
        print(f"Token info: {token_info}")
        
        market_data = await api.get_market_data(test_token)
        print(f"Market data: {market_data}")
        
        # Test sync methods
        token_data = api.get_token_data(test_token)
        print(f"Token data (sync): {token_data}")
        
        return token_info, market_data
    except Exception as e:
        print(f"Test failed: {e}")
        return None, None

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_solsniffer())