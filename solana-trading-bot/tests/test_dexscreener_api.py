import asyncio
from api.dexscreener_api import DexScreenerAPI

async def test_dexscreener():
    dex_api = DexScreenerAPI()
    # Use a known valid Solana token address
    token_address = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"  # USDC
    try:
        token_data = await dex_api.get_token_data(token_address)
        logger.info(f"Retrieved token data: {token_data}")
        return True
    except Exception as e:
        logger.error(f"Error in DexScreener test: {str(e)}")
        return False

    
    print(f"Token data for {token_address}: {token_data}")

    # Test fetching market data
    market_data = await dex_api.get_market_data()
    print(f"Market data: {market_data}")

if __name__ == "__main__":
    asyncio.run(test_dexscreener())