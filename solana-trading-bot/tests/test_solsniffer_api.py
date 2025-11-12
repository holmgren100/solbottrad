import asyncio
import logging
from api.solsniffer_api import SolSnifferAPI
from utils.logger import setup_logger

logger = setup_logger(__name__)

class TestSolSnifferAPI:
    def __init__(self):
        self.solsniffer_api = SolSnifferAPI()
        logger.info("SolSnifferAPI test instance created")

    async def test_get_token_info(self):
        try:
            # Test getting token information
            token_address = "your_test_token_address"  # Replace with a valid token address
            token_info = await self.solsniffer_api.get_token_info(token_address)

            logger.info(f"Retrieved token info: {token_info}")
            return True
        except Exception as e:
            logger.error(f"Error getting token info: {str(e)}")
            return False

    async def test_get_market_data(self):
        try:
            # Test getting market data
            market_data = await self.solsniffer_api.get_market_data()

            logger.info(f"Retrieved market data with {len(market_data)} entries")
            for entry in list(market_data.items())[:3]:  # Log first 3 entries
                logger.info(f"Market data entry: {entry}")

            return True
        except Exception as e:
            logger.error(f"Error getting market data: {str(e)}")
            return False

    async def test_get_new_tokens(self):
        try:
            # Test getting new tokens
            new_tokens = await self.solsniffer_api.get_new_tokens()

            logger.info(f"Retrieved {len(new_tokens)} new tokens")
            for token in new_tokens[:3]:  # Log first 3 new tokens
                logger.info(f"New token: {token}")

            return True
        except Exception as e:
            logger.error(f"Error getting new tokens: {str(e)}")
            return False

    async def test_get_token_holders(self):
        try:
            # Test getting token holders
            token_address = "your_test_token_address"  # Replace with a valid token address
            holders = await self.solsniffer_api.get_token_holders(token_address)

            logger.info(f"Retrieved {len(holders)} token holders")
            for holder in holders[:3]:  # Log first 3 holders
                logger.info(f"Holder info: {holder}")

            return True
        except Exception as e:
            logger.error(f"Error getting token holders: {str(e)}")
            return False

    async def run_all_tests(self):
        logger.info("Starting SolSniffer API tests...")

        # Test token info
        token_info_result = await self.test_get_token_info()
        logger.info(f"Token info test: {'Success' if token_info_result else 'Failed'}")

        await asyncio.sleep(1)  # Rate limiting pause

        # Test market data
        market_data_result = await self.test_get_market_data()
        logger.info(f"Market data test: {'Success' if market_data_result else 'Failed'}")

        await asyncio.sleep(1)  # Rate limiting pause

        # Test new tokens
        new_tokens_result = await self.test_get_new_tokens()
        logger.info(f"New tokens test: {'Success' if new_tokens_result else 'Failed'}")

        await asyncio.sleep(1)  # Rate limiting pause

        # Test token holders
        holders_result = await self.test_get_token_holders()
        logger.info(f"Token holders test: {'Success' if holders_result else 'Failed'}")

        return all([token_info_result, market_data_result, new_tokens_result, holders_result])

def main():
    test_suite = TestSolSnifferAPI()

    try:
        success = asyncio.run(test_suite.run_all_tests())

        if success:
            logger.info("All SolSniffer API tests completed successfully!")
        else:
            logger.error("Some SolSniffer API tests failed. Check the logs for details.")

    except Exception as e:
        logger.error(f"Error running SolSniffer API tests: {str(e)}")
        raise

if __name__ == "__main__":
    main()