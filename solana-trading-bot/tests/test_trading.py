import unittest
import asyncio
from trading.gmgn_trader import GMGNTrader
from unittest.mock import patch
from utils.logger import setup_logger

class TestTrading(unittest.TestCase):
    def setUp(self):
        self.trader = GMGNTrader()
        self.test_token = "TEST_TOKEN"

    @patch('trading.gmgn_trader.GMGNTrader.buy_token')
    def test_buy_token(self, mock_buy):
        async def run_test():
            try:
                # Mock successful response
                mock_buy.return_value = {'success': True, 'transaction_id': 'test_tx'}
                result = await self.trader.buy_token(self.test_token, 100)
                self.assertIsNotNone(result)
                self.assertTrue(result['success'])
            except Exception as e:
                self.fail(f"Buy token test failed: {str(e)}")

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(run_test())
        loop.close()

    @patch('trading.gmgn_trader.GMGNTrader.sell_token')
    def test_sell_token(self, mock_sell):
        async def run_test():
            try:
                # Mock successful response
                mock_sell.return_value = {'success': True, 'transaction_id': 'test_tx'}
                result = await self.trader.sell_token(self.test_token, 50)
                self.assertIsNotNone(result)
                self.assertTrue(result['success'])
            except Exception as e:
                self.fail(f"Sell token test failed: {str(e)}")

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(run_test())
        loop.close()

if __name__ == '__main__':
    unittest.main()