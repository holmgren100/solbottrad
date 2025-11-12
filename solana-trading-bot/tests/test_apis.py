import unittest
import asyncio
from api.dexscreener_api import DexScreenerAPI
from unittest.mock import patch
from utils.logger import setup_logger

class TestAPIs(unittest.TestCase):
    def setUp(self):
        self.dex_api = DexScreenerAPI()
        self.test_token = "TEST_TOKEN_ADDRESS"

    @patch('api.dexscreener_api.DexScreenerAPI.get_token_data')
    def test_get_token_data(self, mock_get_data):
        async def run_test():
            try:
                # Mock successful response
                mock_data = {
                    'price': 1.0,
                    'volume': 1000,
                    'liquidity': 10000
                }
                mock_get_data.return_value = mock_data

                result = await self.dex_api.get_token_data(self.test_token)
                self.assertIsNotNone(result)
                self.assertEqual(result['price'], 1.0)
            except Exception as e:
                self.fail(f"API test failed: {str(e)}")

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(run_test())
        loop.close()

if __name__ == '__main__':
    unittest.main()