import asyncio
import logging
from config.settings import settings
from api.dexscreener_api import DexScreenerAPI
from monitoring.volume_monitor import VolumeMonitor
from utils.logger import setup_logger

# Set up logger
logger = setup_logger(__name__)

# BONK Token address on Solana
VALID_TOKEN_ADDRESS = "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263"  # BONK token


async def test_dexscreener():
    logger.info("Starting DexScreener API test")
    api = DexScreenerAPI()
    try:
        logger.info(f"Testing with BONK token address: {VALID_TOKEN_ADDRESS}")
        logger.info(f"Using DexScreener API URL: {settings.DEXSCREENER_API_URL}")

        result = await api.get_market_data(VALID_TOKEN_ADDRESS)

        if result:
            logger.info("DexScreener API Test Result:")
            logger.info(f"Token Address: {VALID_TOKEN_ADDRESS}")
            logger.info(f"Price: ${result.get('price', 'N/A')}")
            logger.info(f"24h Volume: ${result.get('volume_24h', 'N/A')}")
            logger.info(f"Liquidity: ${result.get('liquidity_usd', 'N/A')}")
            logger.info(f"Price Change 24h: {result.get('price_change_24h', 'N/A')}%")
        else:
            logger.warning("No data returned from DexScreener API")

        return result
    except Exception as e:
        logger.error(f"Error in DexScreener test: {str(e)}")
        raise
    finally:
        # Prefer close() if present, else cleanup()
        close_coro = getattr(api, "close", None) or getattr(api, "cleanup", None)
        if close_coro:
            if asyncio.iscoroutinefunction(close_coro):
                await close_coro()
            elif callable(close_coro):
                close_coro()


async def test_volume_monitor():
    logger.info("Starting Volume Monitor test")
    monitor = VolumeMonitor()
    try:
        logger.info(f"Testing with BONK token address: {VALID_TOKEN_ADDRESS}")
        logger.info(f"Min Volume Threshold: ${settings.MIN_VOLUME}")
        logger.info(f"Min Liquidity Threshold: ${settings.MIN_LIQUIDITY}")

        result = await monitor.check_volume(VALID_TOKEN_ADDRESS)

        if result:
            logger.info("Volume Monitor Test Result:")
            logger.info(f"Raw Result: {result}")

            vol = float(result.get("volume_24h", 0) or 0)
            liq = float(result.get("liquidity_usd", 0) or 0)

            volume_ok = vol >= float(settings.MIN_VOLUME)
            liquidity_ok = liq >= float(settings.MIN_LIQUIDITY)

            logger.info(f"Volume Sufficient: {volume_ok} (vol={vol}, min={settings.MIN_VOLUME})")
            logger.info(f"Liquidity Sufficient: {liquidity_ok} (liq={liq}, min={settings.MIN_LIQUIDITY})")

        trend = await monitor.analyze_volume_trend(VALID_TOKEN_ADDRESS)
        if trend:
            logger.info("Volume Trend Analysis:")
            logger.info(f"Trend Analysis: {trend}")

        return result, trend
    except Exception as e:
        logger.error(f"Error in Volume Monitor test: {str(e)}")
        raise
    finally:
        # Prefer close() if present
        close_coro = getattr(monitor, "close", None) or getattr(monitor, "cleanup", None)
        if close_coro:
            if asyncio.iscoroutinefunction(close_coro):
                await close_coro()
            elif callable(close_coro):
                close_coro()


async def test_settings():
    logger.info("Testing Settings Configuration")
    try:
        logger.info("Current Settings:")
        logger.info(f"MIN_VOLUME: ${settings.MIN_VOLUME}")
        logger.info(f"MIN_LIQUIDITY: ${settings.MIN_LIQUIDITY}")
        logger.info(f"MIN_SENTIMENT_SCORE: {settings.MIN_SENTIMENT_SCORE}")
        logger.info(f"PRICE_CHANGE_THRESHOLD: {settings.PRICE_CHANGE_THRESHOLD}")
        logger.info(f"TRACKED_WALLETS: {settings.TRACKED_WALLETS}")
        logger.info(f"RATE_LIMIT_CALLS: {settings.RATE_LIMIT_CALLS}")
        logger.info(f"RATE_LIMIT_PERIOD: {settings.RATE_LIMIT_PERIOD}")
        return True
    except Exception as e:
        logger.error(f"Error in settings test: {str(e)}")
        raise


async def main():
    try:
        logger.info("=== Starting Component Tests ===")

        logger.info("\n1. Testing Settings Configuration...")
        await test_settings()

        logger.info("\n2. Testing DexScreener API...")
        await test_dexscreener()

        logger.info("\n3. Testing Volume Monitor...")
        await test_volume_monitor()

        logger.info("\n=== All Tests Completed Successfully ===")

    except Exception as e:
        logger.error(f"Test execution failed: {str(e)}")
        raise
    finally:
        logger.info("=== Test Session Ended ===")


if __name__ == "__main__":
    try:
        # Clean up any existing handlers to avoid duplicate logging
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)

        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Tests interrupted by user")
    except Exception as e:
        logger.error(f"Tests failed with error: {str(e)}")