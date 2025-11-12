import asyncio
from main import TradingBot

async def test_bot_initialization():
    bot = TradingBot()

    # Test initialization
    success = await bot.initialize()
    if success:
        print("Bot initialized successfully")
    else:
        print("Bot initialization failed")

if __name__ == "__main__":
    asyncio.run(test_bot_initialization())