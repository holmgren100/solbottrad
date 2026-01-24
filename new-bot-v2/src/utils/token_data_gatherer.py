"""
Token Data Gatherer - Comprehensive Data Collection

Gathers complete token data from all sources:
- Alchemy: Token metadata, safety checks
- Jupiter: Current price, liquidity
- DexScreener: Candles, volume, buy/sell pressure

Returns unified data dict for all bot modules.
"""

import logging
from typing import Dict, List, Optional

from src.api.alchemy_client import AlchemyClient
from src.api.jupiter_client import JupiterClient
from src.api.dexscreener_client import DexScreenerClient
from src.api.birdeye_client import BirdeyeClient
from src.indicators.macd import MACDCalculator
from src.indicators.rsi import RSICalculator
from src.indicators.volume import VolumeAnalyzer

logger = logging.getLogger(__name__)


class TokenDataGatherer:
    """
    Gathers comprehensive token data from all sources.

    Handles API failures gracefully - returns partial data if needed.
    """

    def __init__(self):
        """Initialize data gatherer with all API clients."""
        self.alchemy_client = AlchemyClient()
        self.jupiter_client = JupiterClient()
        self.dexscreener_client = DexScreenerClient()
        self.birdeye_client = BirdeyeClient()

        self.macd_calculator = MACDCalculator()
        self.rsi_calculator = RSICalculator()
        self.volume_analyzer = VolumeAnalyzer()

        logger.info("Token Data Gatherer initialized")

    def gather_complete_data(self, token_address: str) -> Optional[Dict]:
        """
        Gather comprehensive token data from all sources.

        Args:
            token_address: Token mint address

        Returns:
            Complete token data dict or None if critical data missing
        """
        try:
            logger.debug(f"Gathering data for {token_address[:8]}...")

            data = {
                "address": token_address,
                "symbol": "UNKNOWN",
                "name": "UNKNOWN",
                "price": 0,
                "liquidity": 0,
                "volume_5m": 0,
                "volume_1h": 0,
                "volume_24h": 0,
                "prices": [],
                "volumes": [],
                "candles": [],
                "lp_burned": False,
                "mint_revoked": False,
                "buys": 0,
                "sells": 0,
                "rsi": 0,
                "macd": {},
                "volume_velocity": 0
            }

            # 1. Get basic token info from DexScreener (has most data)
            dex_data = self.dexscreener_client.get_token_data(token_address)

            if not dex_data:
                logger.warning(f"No DexScreener data for {token_address[:8]}")
                return None  # Critical failure

            # Extract basic info
            data["symbol"] = dex_data.get("symbol", "UNKNOWN")
            data["name"] = dex_data.get("name", "UNKNOWN")
            data["price"] = dex_data.get("price", 0)
            data["liquidity"] = dex_data.get("liquidity", 0)
            data["volume_5m"] = dex_data.get("volume_5m", 0)
            data["volume_1h"] = dex_data.get("volume_1h", 0)
            data["volume_24h"] = dex_data.get("volume_24h", 0)
            data["price_change_5m"] = dex_data.get("price_change_5m", 0)
            data["price_change_1h"] = dex_data.get("price_change_1h", 0)
            data["buys_5m"] = dex_data.get("buys", 0)
            data["sells_5m"] = dex_data.get("sells", 0)
            data["market_cap_usd"] = dex_data.get("market_cap_usd", 0)

            # Get candles for technical analysis from DexScreener (works reliably!)
            logger.debug(f"Generating candles from DexScreener price changes for {token_address[:8]}...")
            candles = self.dexscreener_client.get_price_history(token_address, timeframe="15m", limit=50)

            if candles and len(candles) > 0:
                data["candles"] = candles
                data["prices"] = [c.get("close", 0) for c in candles]
                data["volumes"] = [c.get("volume", 0) for c in candles]
                logger.debug(f"Generated {len(candles)} approximate candles from DexScreener")
            else:
                logger.warning(f"Failed to generate candles - indicators will fail")
                data["candles"] = []
                data["prices"] = []
                data["volumes"] = []

            # 2. Get safety checks from Alchemy
            try:
                lp_burned = self.alchemy_client.check_lp_burned(token_address)
                mint_revoked = self.alchemy_client.check_mint_authority(token_address)

                data["lp_burned"] = lp_burned
                data["mint_revoked"] = mint_revoked

                logger.debug(f"Safety: LP={lp_burned}, Mint={mint_revoked}")

            except Exception as e:
                logger.warning(f"Alchemy safety check failed: {e}")
                # Continue with partial data

            # 3. Get buy/sell pressure
            try:
                pressure_data = self.dexscreener_client.get_buy_sell_pressure(token_address)

                if pressure_data:
                    data["buys"] = pressure_data.get("buys", 0)
                    data["sells"] = pressure_data.get("sells", 0)

                logger.debug(f"Pressure: Buys={data['buys']}, Sells={data['sells']}")

            except Exception as e:
                logger.warning(f"Buy/sell pressure failed: {e}")
                # Continue with partial data

            # 4. Calculate technical indicators (if enough price data)
            if len(data["prices"]) >= 14:  # Minimum for RSI
                try:
                    # RSI
                    rsi_result = self.rsi_calculator.calculate(data["prices"])
                    if rsi_result:
                        data["rsi"] = rsi_result.get("rsi", 0)

                    # MACD (need 30 candles)
                    if len(data["prices"]) >= 30:
                        macd_result = self.macd_calculator.calculate(data["prices"])
                        if macd_result:
                            data["macd"] = macd_result

                    logger.debug(f"Indicators: RSI={data['rsi']:.1f}")

                except Exception as e:
                    logger.warning(f"Indicator calculation failed: {e}")
                    # Continue with partial data

            # 5. Calculate volume velocity
            if data["volume_5m"] > 0 and data["volume_1h"] > 0:
                try:
                    vol_1m = data["volume_5m"] / 5  # Approximate 1m volume
                    vol_5m = data["volume_1h"] / 12  # Approximate 5m average

                    velocity = self.volume_analyzer.calculate_velocity(vol_1m, vol_5m)
                    data["volume_velocity"] = velocity

                    logger.debug(f"Volume velocity: {velocity:.1f}x")

                except Exception as e:
                    logger.warning(f"Volume velocity calculation failed: {e}")

            logger.info(
                f"✅ Gathered data for {data['symbol']}: "
                f"${data['price']:.8f}, Liq=${data['liquidity']:.0f}"
            )

            return data

        except Exception as e:
            logger.error(f"Error gathering token data: {e}")
            return None

    def gather_price_update(self, token_address: str) -> Optional[Dict]:
        """
        Quick price update for existing position (lighter call).

        Args:
            token_address: Token mint address

        Returns:
            Price update dict or None
        """
        try:
            # Just get current price from DexScreener
            dex_data = self.dexscreener_client.get_token_data(token_address)

            if not dex_data:
                return None

            return {
                "address": token_address,
                "price": dex_data.get("price", 0),
                "volume_5m": dex_data.get("volume_5m", 0),
                "volume_1h": dex_data.get("volume_1h", 0),
                "timestamp": dex_data.get("timestamp")
            }

        except Exception as e:
            logger.error(f"Error getting price update: {e}")
            return None

    def verify_safety(self, token_address: str) -> Dict:
        """
        Quick safety verification (LP + Mint).

        Args:
            token_address: Token mint address

        Returns:
            {"passed": bool, "lp_burned": bool, "mint_revoked": bool}
        """
        try:
            lp_burned = self.alchemy_client.check_lp_burned(token_address)
            mint_revoked = self.alchemy_client.check_mint_authority(token_address)

            passed = lp_burned and mint_revoked

            logger.debug(
                f"Safety check: LP={lp_burned}, Mint={mint_revoked}, Pass={passed}"
            )

            return {
                "passed": passed,
                "lp_burned": lp_burned,
                "mint_revoked": mint_revoked
            }

        except Exception as e:
            logger.error(f"Safety verification failed: {e}")
            return {
                "passed": False,
                "lp_burned": False,
                "mint_revoked": False
            }


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    gatherer = TokenDataGatherer()

    # Test with BONK token
    token_address = "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263"

    print("\n" + "=" * 60)
    print("Test 1: Gather Complete Data")
    print("=" * 60)

    data = gatherer.gather_complete_data(token_address)

    if data:
        print(f"\nSymbol: {data['symbol']}")
        print(f"Price: ${data['price']:.8f}")
        print(f"Liquidity: ${data['liquidity']:,.0f}")
        print(f"Volume 24h: ${data['volume_24h']:,.0f}")
        print(f"RSI: {data['rsi']:.1f}")
        print(f"Safety: LP={data['lp_burned']}, Mint={data['mint_revoked']}")
        print(f"Pressure: Buys={data['buys']}, Sells={data['sells']}")
        print(f"Candles loaded: {len(data['candles'])}")
    else:
        print("Failed to gather data")

    print("\n" + "=" * 60)
    print("Test 2: Quick Safety Check")
    print("=" * 60)

    safety = gatherer.verify_safety(token_address)
    print(f"\nPassed: {safety['passed']}")
    print(f"LP Burned: {safety['lp_burned']}")
    print(f"Mint Revoked: {safety['mint_revoked']}")

    print("\n" + "=" * 60)
    print("Test 3: Price Update")
    print("=" * 60)

    update = gatherer.gather_price_update(token_address)
    if update:
        print(f"\nPrice: ${update['price']:.8f}")
        print(f"Volume 5m: ${update['volume_5m']:,.0f}")
    else:
        print("Failed to get price update")
