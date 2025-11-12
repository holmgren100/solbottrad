import unittest
import asyncio
from monitoring.volume_monitor import VolumeMonitor
from unittest.mock import patch
from utils.logger import setup_logger

logger = setup_logger(__name__)

class TestMonitoring(unittest.TestCase):
    def setUp(self):
        self.volume_monitor = VolumeMonitor()
        logger.info("VolumeMonitor initialized for testing")
        self.test_token = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"  # USDC

    def test_volume_monitoring(self):
        # Test synchronous volume checking
        volume_data = {
            "token_address": self.test_token,
            "volume": 2000.0,
            "liquidity": 10000.0
        }
        result = self.volume_monitor.check_volume_threshold(volume_data)
        self.assertTrue(result)
        logger.info("Synchronous volume check passed")

    async def test_async_volume_monitoring(self):
        # Test asynchronous volume checking
        try:
            volume_data = await self.volume_monitor.check_volume(self.test_token)
            self.assertIsNotNone(volume_data)
            self.assertTrue(volume_data.get('volume_sufficient', False))
            logger.info("Asynchronous volume check passed")
        except Exception as e:
            logger.error(f"Async volume check failed: {str(e)}")
            raise

    def test_async_wrapper(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self.test_async_volume_monitoring())
        finally:
            loop.close()

if __name__ == '__main__':
    unittest.main()