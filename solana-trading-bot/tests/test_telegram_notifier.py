import asyncio
import pytest
from utils.telegram_notifier import TelegramNotifier
from utils.logger import setup_logger

# Set up logging
logger = setup_logger(__name__)

class TestTelegramNotifier:
    def setup_method(self):
        """Setup method called before each test"""
        self.notifier = TelegramNotifier()
        logger.info("TelegramNotifier test instance created")

    @pytest.mark.asyncio
    async def test_basic_notification(self):
        """Test basic notification functionality"""
        try:
            await self.notifier.send_notification("Testing Telegram notifications!")
            logger.info("Basic notification sent successfully")
            assert True  # Test passed
        except Exception as e:
            logger.error(f"Error sending basic notification: {str(e)}")
            pytest.fail(f"Basic notification failed: {str(e)}")

    @pytest.mark.asyncio
    async def test_trade_notification(self):
        """Test trade notification functionality"""
        try:
            await self.notifier.send_trade_notification(
                trade_type="BUY",
                token="SOL",
                amount=1.0,
                price=100.50
            )
            logger.info("Trade notification sent successfully")
            assert True  # Test passed
        except Exception as e:
            logger.error(f"Error sending trade notification: {str(e)}")
            pytest.fail(f"Trade notification failed: {str(e)}")

    @pytest.mark.asyncio
    async def test_error_notification(self):
        """Test error notification functionality"""
        try:
            await self.notifier.send_error_notification(
                "API connection failed",
                severity="ERROR"
            )
            logger.info("Error notification sent successfully")
            assert True  # Test passed
        except Exception as e:
            logger.error(f"Error sending error notification: {str(e)}")
            pytest.fail(f"Error notification failed: {str(e)}")

    @pytest.mark.asyncio
    async def test_volume_alert(self):
        """Test volume alert functionality"""
        try:
            await self.notifier.send_volume_alert(
                token="SOL",
                volume=1000000,
                price=100.50,
                change=5.25
            )
            logger.info("Volume alert sent successfully")
            assert True  # Test passed
        except Exception as e:
            logger.error(f"Error sending volume alert: {str(e)}")
            pytest.fail(f"Volume alert failed: {str(e)}")

    @pytest.mark.asyncio
    async def test_all_notifications_with_delays(self):
        """Test all notifications with proper delays to avoid rate limiting"""
        logger.info("Starting comprehensive Telegram notification test...")

        # Test basic notification
        await self.notifier.send_notification("Testing Telegram notifications!")
        logger.info("Basic notification sent")
        await asyncio.sleep(1)

        # Test trade notification
        await self.notifier.send_trade_notification(
            trade_type="BUY",
            token="SOL",
            amount=1.0,
            price=100.50
        )
        logger.info("Trade notification sent")
        await asyncio.sleep(1)

        # Test error notification
        await self.notifier.send_error_notification(
            "API connection failed",
            severity="ERROR"
        )
        logger.info("Error notification sent")
        await asyncio.sleep(1)

        # Test volume alert
        await self.notifier.send_volume_alert(
            token="SOL",
            volume=1000000,
            price=100.50,
            change=5.25
        )
        logger.info("Volume alert sent")

        logger.info("All notifications sent successfully!")
        assert True  # Test passed

# Standalone test runner (for manual testing)
async def run_manual_tests():
    """Manual test runner - use this if you want to run tests outside pytest"""
    logger.info("Starting manual Telegram notification tests...")
    
    notifier = TelegramNotifier()
    
    try:
        # Test basic notification
        await notifier.send_notification("Manual test: Basic notification")
        logger.info("✅ Basic notification sent")
        await asyncio.sleep(1)

        # Test trade notification
        await notifier.send_trade_notification(
            trade_type="SELL",
            token="BONK",
            amount=1000000,
            price=0.000015
        )
        logger.info("✅ Trade notification sent")
        await asyncio.sleep(1)

        # Test error notification
        await notifier.send_error_notification(
            "Manual test error",
            severity="WARNING"
        )
        logger.info("✅ Error notification sent")
        await asyncio.sleep(1)

        # Test volume alert
        await notifier.send_volume_alert(
            token="PEPE",
            volume=5000000,
            price=0.00001,
            change=-2.5
        )
        logger.info("✅ Volume alert sent")

        logger.info("🎉 All manual tests completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Manual test failed: {str(e)}")
        raise

def main():
    """Main function for manual testing"""
    try:
        asyncio.run(run_manual_tests())
    except Exception as e:
        logger.error(f"Error running manual tests: {str(e)}")
        raise

if __name__ == "__main__":
    main()