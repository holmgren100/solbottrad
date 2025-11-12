import aiohttp
import requests
import logging
from typing import Optional, Dict, Any, List
from config.settings import settings
from utils.logger import setup_logger
from exceptions.custom_exceptions import APIError
from utils.rate_limiter import RateLimiter

class DexScreenerAPI:
    """
    API client for DexScreener with both async and sync capabilities.
    Includes rate limiting and comprehensive error handling.
    """

    def __init__(self):
        # Initialize logger
        self.logger = setup_logger(__name__)

        # Initialize configuration from settings
        self.base_url = settings.DEXSCREENER_API_URL
        self.rate_limit_calls = settings.RATE_LIMIT_CALLS
        self.rate_limit_period = settings.RATE_LIMIT_PERIOD

        # Initialize rate limiter with settings
        self.rate_limiter = RateLimiter(
            calls_per_second=self.rate_limit_calls / self.rate_limit_period
        )

        # Initialize session as None
        self.session: Optional[aiohttp.ClientSession] = None

        # Headers for requests
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json'
        }

        self.logger.info(f"Initialized DexScreenerAPI with URL: {self.base_url}")

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30)
            )
        return self.session

    async def close(self) -> None:
        """Close the aiohttp session"""
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None
            self.logger.debug("Closed aiohttp session")

    async def get_token_data(self, token_address: str) -> Dict[str, Any]:
        """
        Fetch token data for a specific token using async HTTP.

        Args:
            token_address: The address of the token

        Returns:
            Dict containing token data

        Raises:
            APIError: If the request fails
        """
        try:
            await self.rate_limiter.wait_if_needed()
            session = await self._get_session()
            url = f"{self.base_url}/tokens/{token_address}"
            
            self.logger.debug(f"Request URL: {url}")

            async with session.get(url, headers=self.headers) as response:
                response_text = await response.text()
                self.logger.debug(f"Response: {response_text}")
                
                if response.status == 200:
                    data = await response.json()
                    self.logger.debug(f"Successfully fetched token data for {token_address}")
                    return data
                else:
                    error_msg = f"Error fetching token data: Status {response.status}"
                    self.logger.error(error_msg)
                    raise APIError(error_msg)

        except aiohttp.ClientError as e:
            error_msg = f"Network error fetching token data: {str(e)}"
            self.logger.error(error_msg)
            raise APIError(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error fetching token data: {str(e)}"
            self.logger.error(error_msg)
            raise APIError(error_msg)

    async def get_token_pairs(self, token_address: str) -> List[Dict[str, Any]]:
        """
        Get trading pairs for a token.

        Args:
            token_address: The address of the token

        Returns:
            List of trading pairs

        Raises:
            APIError: If the request fails
        """
        try:
            await self.rate_limiter.wait_if_needed()
            session = await self._get_session()
            url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
            
            self.logger.debug(f"Fetching pairs from: {url}")

            async with session.get(url, headers=self.headers) as response:
                if response.status == 200:
                    data = await response.json()
                    pairs = data.get('pairs', [])
                    self.logger.debug(f"Found {len(pairs)} pairs for token {token_address}")
                    return pairs
                else:
                    error_msg = f"Error fetching token pairs: Status {response.status}"
                    self.logger.error(error_msg)
                    raise APIError(error_msg)

        except aiohttp.ClientError as e:
            error_msg = f"Network error fetching token pairs: {str(e)}"
            self.logger.error(error_msg)
            raise APIError(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error fetching token pairs: {str(e)}"
            self.logger.error(error_msg)
            raise APIError(error_msg)

    async def get_market_data(self, token_address: str) -> Optional[Dict[str, Any]]:
        """
        Get market data for a token using async HTTP.

        Args:
            token_address: The address of the token

        Returns:
            Dictionary containing market data or None if no pairs found

        Raises:
            APIError: If the request fails
        """
        try:
            pairs = await self.get_token_pairs(token_address)
            if not pairs:
                self.logger.warning(f"No pairs found for token {token_address}")
                return None

            # Get the most liquid pair
            main_pair = max(pairs, key=lambda x: float(x.get('volume', {}).get('h24', 0)))

            market_data = {
                'price': float(main_pair.get('priceUsd', 0)),
                'volume_24h': float(main_pair.get('volume', {}).get('h24', 0)),
                'price_change_24h': float(main_pair.get('priceChange', {}).get('h24', 0)),
                'liquidity_usd': float(main_pair.get('liquidity', {}).get('usd', 0)),
                'pair_address': main_pair.get('pairAddress'),
                'dex_id': main_pair.get('dexId'),
                'timestamp': main_pair.get('timestamp'),
                'updated_at': main_pair.get('updatedAt')
            }

            self.logger.info(
                f"Market data for {token_address}: "
                f"Price=${market_data['price']:.6f}, "
                f"24h Volume=${market_data['volume_24h']:,.2f}, "
                f"24h Change={market_data['price_change_24h']}%"
            )

            return market_data

        except Exception as e:
            error_msg = f"Failed to get market data: {str(e)}"
            self.logger.error(error_msg)
            raise APIError(error_msg)

    def get_token_pairs_sync(self, token_address: str) -> List[Dict[str, Any]]:
        """
        Synchronous version of get_token_pairs with rate limiting
        """
        try:
            self.rate_limiter.wait_if_needed_sync()
            url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
            
            self.logger.debug(f"Fetching pairs (sync) from: {url}")
            
            response = requests.get(url, headers=self.headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                pairs = data.get('pairs', [])
                self.logger.debug(f"Found {len(pairs)} pairs for token {token_address} (sync)")
                return pairs
            else:
                error_msg = f"Error fetching token pairs (sync): Status {response.status_code}"
                self.logger.error(error_msg)
                raise APIError(error_msg)

        except requests.RequestException as e:
            error_msg = f"Network error fetching token pairs (sync): {str(e)}"
            self.logger.error(error_msg)
            raise APIError(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error fetching token pairs (sync): {str(e)}"
            self.logger.error(error_msg)
            raise APIError(error_msg)

    def get_market_data_sync(self, token_address: str) -> Optional[Dict[str, Any]]:
        """
        Synchronous version of get_market_data with rate limiting
        """
        try:
            pairs = self.get_token_pairs_sync(token_address)

            if not pairs:
                self.logger.warning(f"No pairs found for token {token_address}")
                return None

            main_pair = max(pairs, key=lambda x: float(x.get('volume', {}).get('h24', 0)))
            market_data = {
                'price': float(main_pair.get('priceUsd', 0)),
                'volume_24h': float(main_pair.get('volume', {}).get('h24', 0)),
                'price_change_24h': float(main_pair.get('priceChange', {}).get('h24', 0)),
                'liquidity_usd': float(main_pair.get('liquidity', {}).get('usd', 0)),
                'pair_address': main_pair.get('pairAddress'),
                'dex_id': main_pair.get('dexId'),
                'timestamp': main_pair.get('timestamp'),
                'updated_at': main_pair.get('updatedAt')
            }

            self.logger.info(
                f"Market data for {token_address} (sync): "
                f"Price=${market_data['price']:.6f}, "
                f"24h Volume=${market_data['volume_24h']:,.2f}"
            )

            return market_data

        except Exception as e:
            error_msg = f"Failed to get market data (sync): {str(e)}"
            self.logger.error(error_msg)
            raise APIError(error_msg)

async def test_dexscreener():
    """Test function for DexScreener API"""
    # BONK token address on Solana
    test_token = "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263"

    api = DexScreenerAPI()
    try:
        market_data = await api.get_market_data(test_token)
        if market_data:
            print(f"Successfully fetched market data for BONK token:")
            print(f"Price: ${market_data['price']:.6f}")
            print(f"24h Volume: ${market_data['volume_24h']:,.2f}")
            print(f"24h Change: {market_data['price_change_24h']}%")
        else:
            print("No market data found for token")
        return market_data
    finally:
        await api.close()

