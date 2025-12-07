"""
Market monitor for tracking BTC, ETH, SOL and overall market conditions.
Helps detect market-wide crashes that affect all tokens.
"""

import asyncio
import aiohttp
from typing import Dict, Optional
from datetime import datetime, timedelta
from ..monitoring.logger import get_logger

logger = get_logger(__name__)


class MarketMonitor:
    """
    Monitor major crypto markets (BTC, ETH, SOL) to detect market-wide conditions.

    When BTC/ETH dump, all alts follow. When SOL dumps, liquidity dries up.
    This helps us avoid trading during market crashes.
    """

    def __init__(self):
        """Initialize market monitor."""
        self.session: Optional[aiohttp.ClientSession] = None

        # Track market data
        self.btc_data = {}
        self.eth_data = {}
        self.sol_data = {}

        # Market state
        self.market_state = 'normal'  # normal/warning/crash
        self.last_update = 0

        # Thresholds
        self.crash_threshold = -10  # 10% drop in 1 hour = crash
        self.warning_threshold = -5  # 5% drop in 1 hour = warning

    async def _ensure_session(self):
        """Ensure aiohttp session exists."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()

    async def close(self):
        """Close the client session."""
        if self.session and not self.session.closed:
            await self.session.close()

    async def get_market_data(self) -> Dict:
        """
        Get current market data for BTC, ETH, SOL from CoinGecko.

        Returns:
            Dictionary with price and change data
        """
        await self._ensure_session()

        try:
            # CoinGecko free API - get BTC, ETH, SOL data
            url = "https://api.coingecko.com/api/v3/simple/price"
            params = {
                'ids': 'bitcoin,ethereum,solana',
                'vs_currencies': 'usd',
                'include_24hr_change': 'true',
                'include_1h_change': 'true'
            }

            async with self.session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    data = await response.json()

                    self.btc_data = {
                        'price': data.get('bitcoin', {}).get('usd', 0),
                        'change_1h': data.get('bitcoin', {}).get('usd_1h_change', 0),
                        'change_24h': data.get('bitcoin', {}).get('usd_24h_change', 0)
                    }

                    self.eth_data = {
                        'price': data.get('ethereum', {}).get('usd', 0),
                        'change_1h': data.get('ethereum', {}).get('usd_1h_change', 0),
                        'change_24h': data.get('ethereum', {}).get('usd_24h_change', 0)
                    }

                    self.sol_data = {
                        'price': data.get('solana', {}).get('usd', 0),
                        'change_1h': data.get('solana', {}).get('usd_1h_change', 0),
                        'change_24h': data.get('solana', {}).get('usd_24h_change', 0)
                    }

                    self.last_update = datetime.now().timestamp()

                    # Determine market state
                    self._update_market_state()

                    return {
                        'btc': self.btc_data,
                        'eth': self.eth_data,
                        'sol': self.sol_data,
                        'market_state': self.market_state,
                        'timestamp': self.last_update
                    }

                else:
                    logger.error(f"CoinGecko API error: {response.status}")
                    return {}

        except Exception as e:
            logger.error(f"Error fetching market data: {e}")
            return {}

    def _update_market_state(self):
        """Update market state based on recent price changes."""
        btc_1h = self.btc_data.get('change_1h', 0)
        eth_1h = self.eth_data.get('change_1h', 0)
        sol_1h = self.sol_data.get('change_1h', 0)

        # Check for crash conditions
        if (btc_1h < self.crash_threshold or
            eth_1h < self.crash_threshold or
            sol_1h < self.crash_threshold):
            self.market_state = 'crash'
            logger.error(
                f"🚨 MARKET CRASH DETECTED: "
                f"BTC {btc_1h:+.1f}%, ETH {eth_1h:+.1f}%, SOL {sol_1h:+.1f}%"
            )

        # Check for warning conditions
        elif (btc_1h < self.warning_threshold or
              eth_1h < self.warning_threshold or
              sol_1h < self.warning_threshold):
            self.market_state = 'warning'
            logger.warning(
                f"⚠️ MARKET WARNING: "
                f"BTC {btc_1h:+.1f}%, ETH {eth_1h:+.1f}%, SOL {sol_1h:+.1f}%"
            )

        # Market looks good
        else:
            if self.market_state != 'normal':
                logger.info(
                    f"✅ Market returned to normal: "
                    f"BTC {btc_1h:+.1f}%, ETH {eth_1h:+.1f}%, SOL {sol_1h:+.1f}%"
                )
            self.market_state = 'normal'

    async def monitor_continuous(self, check_interval: int = 60):
        """
        Continuously monitor market conditions.

        Args:
            check_interval: Seconds between checks (default 60)
        """
        logger.info("📊 Starting continuous market monitoring...")

        while True:
            try:
                await self.get_market_data()

                # Log current state
                logger.info(
                    f"📈 Market: {self.market_state.upper()} | "
                    f"BTC ${self.btc_data.get('price', 0):,.0f} ({self.btc_data.get('change_1h', 0):+.1f}%), "
                    f"ETH ${self.eth_data.get('price', 0):,.0f} ({self.eth_data.get('change_1h', 0):+.1f}%), "
                    f"SOL ${self.sol_data.get('price', 0):,.2f} ({self.sol_data.get('change_1h', 0):+.1f}%)"
                )

            except Exception as e:
                logger.error(f"Error in market monitoring: {e}")

            await asyncio.sleep(check_interval)

    def should_trade(self) -> tuple[bool, str]:
        """
        Check if conditions are good for trading.

        Returns:
            Tuple of (should_trade, reason)
        """
        if self.market_state == 'crash':
            return False, "Market crash in progress - high risk"

        if self.market_state == 'warning':
            # Can still trade but with caution
            return True, "Market warning - trade with reduced position sizes"

        return True, "Market conditions normal"

    def get_sol_health(self) -> Dict:
        """
        Get SOL-specific health metrics.

        SOL is critical for Solana token trading:
        - If SOL dumps, all token liquidity dries up
        - If SOL pumps, more liquidity flows in

        Returns:
            SOL health assessment
        """
        sol_1h = self.sol_data.get('change_1h', 0)
        sol_24h = self.sol_data.get('change_24h', 0)
        sol_price = self.sol_data.get('price', 0)

        # Determine SOL trend
        if sol_1h < -5:
            trend = 'bearish'
            liquidity_outlook = 'Expect liquidity to dry up'
        elif sol_1h > 5:
            trend = 'bullish'
            liquidity_outlook = 'Expect increased liquidity'
        else:
            trend = 'neutral'
            liquidity_outlook = 'Normal liquidity conditions'

        return {
            'price': sol_price,
            'change_1h': sol_1h,
            'change_24h': sol_24h,
            'trend': trend,
            'liquidity_outlook': liquidity_outlook,
            'is_healthy': sol_1h > -5  # SOL not dumping
        }

    def get_position_size_multiplier(self) -> float:
        """
        Get position size multiplier based on market conditions.

        Returns:
            Multiplier (0.5 = half size, 1.0 = normal, 1.5 = larger)
        """
        if self.market_state == 'crash':
            return 0  # Don't trade during crash

        if self.market_state == 'warning':
            return 0.7  # Reduce position size by 30%

        # Check SOL specifically (most important for Solana tokens)
        sol_1h = self.sol_data.get('change_1h', 0)

        if sol_1h < -3:
            return 0.7  # SOL dumping, reduce size

        if sol_1h > 5:
            return 1.2  # SOL pumping, can increase size slightly

        return 1.0  # Normal
