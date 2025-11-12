import logging
from typing import Dict, Optional, List, Any
from datetime import datetime, timezone, timedelta
from exceptions.custom_exceptions import VolumeMonitorError
from config.settings import settings
from utils.logger import setup_logger
from api.dexscreener_api import DexScreenerAPI
from utils.rate_limiter import RateLimiter

logger = setup_logger(__name__)

class VolumeMonitor:
    """
    Monitor trading volume and liquidity for tokens.
    Includes historical tracking and trend analysis.
    """

    def __init__(self):
        # Initialize logger
        self.logger = setup_logger(__name__)

        # Load settings
        self.min_volume = settings.MIN_VOLUME
        self.min_liquidity = settings.MIN_LIQUIDITY
        self.volume_threshold = settings.PRICE_CHANGE_THRESHOLD

        self.logger.info(
            f"Initialized VolumeMonitor with settings: "
            f"min_volume=${self.min_volume:,.2f}, "
            f"min_liquidity=${self.min_liquidity:,.2f}"
        )

        # Initialize components
        self.dex_api = DexScreenerAPI()
        self.rate_limiter = RateLimiter(calls_per_second=2)

        # Initialize volume history storage
        self.volume_history: Dict[str, List[Dict[str, Any]]] = {}

    async def check_volume(self, token_address: str) -> Dict[str, Any]:
        """
        Check the trading volume and other metrics for a given token.

        Args:
            token_address (str): The token address to check.

        Returns:
            Dict[str, Any]: Volume information including 24h volume, current price, liquidity, etc.

        Raises:
            VolumeMonitorError: If there's an error checking the volume.
        """
        try:
            self.logger.debug(f"Checking volume for token: {token_address}")

            # Get market data from DexScreener
            market_data = await self.dex_api.get_market_data(token_address)

            if not market_data:
                self.logger.warning(f"No market data available for token {token_address}")
                return self._create_empty_volume_data(token_address)

            # Create volume data dictionary
            volume_data = self._create_volume_data(token_address, market_data)

            # Update volume history
            self._update_volume_history(token_address, volume_data)

            # Log results
            self._log_volume_check(token_address, volume_data)

            return volume_data

        except Exception as e:
            error_msg = f"Error checking volume for token {token_address}: {str(e)}"
            self.logger.error(error_msg)
            raise VolumeMonitorError(error_msg)

    def check_volume_threshold(self, volume_data: dict) -> bool:
        """
        Check if volume and liquidity meet minimum thresholds.
        Supports both old format (volume, liquidity) and new format (volume_24h, liquidity_usd).
        """
        # Support both key formats for backward compatibility
        volume = volume_data.get("volume_24h") or volume_data.get("volume", 0)
        liquidity = volume_data.get("liquidity_usd") or volume_data.get("liquidity", 0)

        if volume >= self.min_volume and liquidity >= self.min_liquidity:
            self.logger.info(f"Volume threshold met: ${volume:,.2f} >= ${self.min_volume:,.2f}")
            return True

        self.logger.debug(f"Volume threshold not met: ${volume:,.2f} < ${self.min_volume:,.2f}")
        return False

    def update_volumes(self, volume_data: dict) -> None:
        """
        Public method for updating volume history (for tests and external use).
        
        Args:
            volume_data (dict): Volume data containing token_address and other metrics.
        
        Raises:
            ValueError: If volume_data doesn't contain token_address.
        """
        token_address = volume_data.get("token_address")
        if not token_address:
            raise ValueError("volume_data must include 'token_address'")
        
        self._update_volume_history(token_address, volume_data)
        self.logger.debug(f"Updated volume history for token: {token_address}")

    def _create_empty_volume_data(self, token_address: str) -> Dict[str, Any]:
        """Create empty volume data structure for tokens with no market data."""
        return {
            "token_address": token_address,
            "volume_24h": 0.0,
            "price": 0.0,
            "liquidity_usd": 0.0,
            "price_change_24h": 0.0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "no_data"
        }

    def _create_volume_data(self, token_address: str, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create volume data structure from market data."""
        return {
            "token_address": token_address,
            "volume_24h": market_data["volume_24h"],
            "price": market_data["price"],
            "liquidity_usd": market_data["liquidity_usd"],
            "price_change_24h": market_data["price_change_24h"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "active",
            "dex_id": market_data["dex_id"],
            "pair_address": market_data["pair_address"],
            "volume_sufficient": self.is_volume_sufficient(market_data["volume_24h"]),
            "liquidity_sufficient": self.is_liquidity_sufficient(market_data["liquidity_usd"])
        }

    def _update_volume_history(self, token_address: str, volume_data: Dict[str, Any]) -> None:
        """Update volume history for a token."""
        if token_address not in self.volume_history:
            self.volume_history[token_address] = []

        self.volume_history[token_address].append(volume_data)

        # Keep only last 24 entries (assuming hourly checks)
        if len(self.volume_history[token_address]) > 24:
            self.volume_history[token_address] = self.volume_history[token_address][-24:]

    def _log_volume_check(self, token_address: str, volume_data: Dict[str, Any]) -> None:
        """Log volume check results."""
        self.logger.info(
            f"Volume check for {token_address}: "
            f"Volume=${volume_data['volume_24h']:,.2f} "
            f"({'sufficient' if volume_data['volume_sufficient'] else 'insufficient'}), "
            f"Price=${volume_data['price']:.8f}, "
            f"Liquidity=${volume_data['liquidity_usd']:,.2f} "
            f"({'sufficient' if volume_data['liquidity_sufficient'] else 'insufficient'})"
        )

    def is_volume_sufficient(self, volume: float) -> bool:
        """Check if volume meets minimum threshold."""
        return volume >= self.min_volume

    def is_liquidity_sufficient(self, liquidity: float) -> bool:
        """Check if liquidity meets minimum threshold."""
        return liquidity >= self.min_liquidity

    async def analyze_volume_trend(self, token_address: str) -> Dict[str, Any]:
        """
        Analyze volume trend for a token over the stored history.

        Args:
            token_address (str): The token address to analyze.

        Returns:
            Dict[str, Any]: Analysis results including volume trend and statistics.

        Raises:
            VolumeMonitorError: If analysis fails.
        """
        try:
            if token_address not in self.volume_history or not self.volume_history[token_address]:
                return {"status": "no_history", "token_address": token_address}

            history = self.volume_history[token_address]
            volumes = [entry["volume_24h"] for entry in history]
            prices = [entry["price"] for entry in history]

            analysis = self._calculate_trend_metrics(token_address, volumes, prices)
            self._log_trend_analysis(token_address, analysis)

            return analysis

        except Exception as e:
            error_msg = f"Error analyzing volume trend for {token_address}: {str(e)}"
            self.logger.error(error_msg)
            raise VolumeMonitorError(error_msg)

    def _calculate_trend_metrics(self, token_address: str, volumes: List[float], prices: List[float]) -> Dict[str, Any]:
        """Calculate trend metrics from historical data."""
        return {
            "token_address": token_address,
            "current_volume": volumes[-1],
            "average_volume": sum(volumes) / len(volumes),
            "volume_change": ((volumes[-1] - volumes[0]) / volumes[0] * 100) if volumes[0] != 0 else 0,
            "price_change": ((prices[-1] - prices[0]) / prices[0] * 100) if prices[0] != 0 else 0,
            "max_volume": max(volumes),
            "min_volume": min(volumes),
            "volume_volatility": (max(volumes) - min(volumes)) / sum(volumes) / len(volumes) if volumes else 0,
            "data_points": len(volumes),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "analyzed"
        }

    def _log_trend_analysis(self, token_address: str, analysis: Dict[str, Any]) -> None:
        """Log trend analysis results."""
        self.logger.info(
            f"Volume trend analysis for {token_address}: "
            f"Current=${analysis['current_volume']:,.2f}, "
            f"Avg=${analysis['average_volume']:,.2f}, "
            f"Change={analysis['volume_change']:+.2f}%, "
            f"Price Change={analysis['price_change']:+.2f}%"
        )

    async def close(self) -> None:
        """Clean up resources."""
        await self.dex_api.close()
        self.logger.info("VolumeMonitor resources cleaned up")

async def test_volume_monitor():
    """Test function for VolumeMonitor"""
    # BONK token address
    test_token = "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263"

    monitor = VolumeMonitor()
    try:
        # Check volume
        volume_data = await monitor.check_volume(test_token)
        print("\nVolume Check Results:")
        print(f"Volume: ${volume_data['volume_24h']:,.2f}")
        print(f"Price: ${volume_data['price']:.8f}")
        print(f"Liquidity: ${volume_data['liquidity_usd']:,.2f}")

        # Check trend after a delay
        await asyncio.sleep(60)  # Wait 1 minute
        volume_data = await monitor.check_volume(test_token)

        # Analyze trend
        trend = await monitor.analyze_volume_trend(test_token)
        print("\nTrend Analysis:")
        print(f"Volume Change: {trend['volume_change']:+.2f}%")
        print(f"Price Change: {trend['price_change']:+.2f}%")

        return volume_data, trend
    finally:
        await monitor.close()

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_volume_monitor())