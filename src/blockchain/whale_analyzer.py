"""
Whale wallet analyzer - detects large holder movements and concentration risks.
Uses blockchain data to identify whale activity and token concentration.
"""

import aiohttp
import asyncio
from typing import Dict, List, Optional
from datetime import datetime
from ..monitoring.logger import get_logger

logger = get_logger(__name__)


class WhaleAnalyzer:
    """Analyzes whale wallets and holder concentration for tokens."""

    def __init__(self, solscan_api_key: Optional[str] = None):
        """
        Initialize whale analyzer.

        Args:
            solscan_api_key: Optional Solscan API key for enhanced limits
        """
        self.solscan_api_key = solscan_api_key
        self.base_url = "https://public-api.solscan.io"
        self.session: Optional[aiohttp.ClientSession] = None

        # Whale thresholds
        self.whale_threshold_percent = 5.0  # >5% of supply = whale
        self.concentration_risk_percent = 50.0  # Top 10 holders >50% = risky

    async def _ensure_session(self):
        """Ensure aiohttp session exists."""
        if self.session is None or self.session.closed:
            headers = {}
            if self.solscan_api_key:
                headers['token'] = self.solscan_api_key
            self.session = aiohttp.ClientSession(headers=headers)

    async def close(self):
        """Close the client session."""
        if self.session and not self.session.closed:
            await self.session.close()

    async def get_token_holders(self, token_address: str, limit: int = 20) -> Optional[List[Dict]]:
        """
        Get top token holders from Solscan.

        Args:
            token_address: Token mint address
            limit: Number of top holders to fetch

        Returns:
            List of holder dictionaries or None if failed
        """
        await self._ensure_session()

        try:
            url = f"{self.base_url}/token/holders"
            params = {
                'tokenAddress': token_address,
                'offset': 0,
                'limit': min(limit, 50)  # API max is usually 50
            }

            async with self.session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    data = await response.json()
                    holders = data.get('data', [])
                    logger.debug(f"Retrieved {len(holders)} holders for {token_address[:8]}...")
                    return holders
                elif response.status == 429:
                    logger.warning("Solscan API rate limit reached")
                    return None
                else:
                    logger.error(f"Solscan API error: {response.status}")
                    return None

        except asyncio.TimeoutError:
            logger.warning(f"Solscan API timeout for {token_address[:8]}...")
            return None
        except Exception as e:
            logger.error(f"Error fetching token holders: {e}")
            return None

    def analyze_holder_concentration(self, holders: List[Dict], total_supply: float) -> Dict:
        """
        Analyze holder concentration and whale presence.

        Args:
            holders: List of holder data from API
            total_supply: Total token supply

        Returns:
            Concentration analysis dictionary
        """
        if not holders or total_supply <= 0:
            return {
                'concentration_risk': 'unknown',
                'top_holder_percent': 0.0,
                'top_10_percent': 0.0,
                'whale_count': 0,
                'is_risky': False,
                'warnings': ['Insufficient holder data']
            }

        # Calculate holder percentages
        holder_percentages = []
        whale_count = 0

        for holder in holders[:10]:  # Analyze top 10
            amount = float(holder.get('amount', 0))
            percentage = (amount / total_supply) * 100 if total_supply > 0 else 0

            holder_percentages.append(percentage)

            if percentage >= self.whale_threshold_percent:
                whale_count += 1

        # Calculate metrics
        top_holder_percent = holder_percentages[0] if holder_percentages else 0.0
        top_10_percent = sum(holder_percentages[:10])

        # Assess concentration risk
        warnings = []
        is_risky = False

        if top_holder_percent > 20:
            warnings.append(f"Top holder owns {top_holder_percent:.1f}% (centralization risk)")
            is_risky = True

        if top_10_percent > self.concentration_risk_percent:
            warnings.append(f"Top 10 holders own {top_10_percent:.1f}% (concentration risk)")
            is_risky = True

        if whale_count >= 5:
            warnings.append(f"{whale_count} whales detected (>5% holders)")

        # Classify concentration risk
        if top_10_percent > 80:
            concentration_risk = 'critical'
        elif top_10_percent > 60:
            concentration_risk = 'high'
        elif top_10_percent > 40:
            concentration_risk = 'medium'
        else:
            concentration_risk = 'low'

        return {
            'concentration_risk': concentration_risk,
            'top_holder_percent': top_holder_percent,
            'top_10_percent': top_10_percent,
            'whale_count': whale_count,
            'is_risky': is_risky,
            'warnings': warnings,
            'holder_count': len(holders)
        }

    def detect_whale_movement(
        self,
        old_holders: List[Dict],
        new_holders: List[Dict],
        total_supply: float
    ) -> Dict:
        """
        Detect whale wallet movements between two snapshots.

        Args:
            old_holders: Previous holder snapshot
            new_holders: Current holder snapshot
            total_supply: Total token supply

        Returns:
            Movement analysis dictionary
        """
        if not old_holders or not new_holders:
            return {
                'movement_detected': False,
                'whale_buys': 0,
                'whale_sells': 0,
                'net_change': 0.0
            }

        # Create holder maps
        old_map = {h['address']: float(h.get('amount', 0)) for h in old_holders}
        new_map = {h['address']: float(h.get('amount', 0)) for h in new_holders}

        whale_buys = 0
        whale_sells = 0
        net_change = 0.0

        # Check for significant changes
        for address in set(list(old_map.keys()) + list(new_map.keys())):
            old_amount = old_map.get(address, 0)
            new_amount = new_map.get(address, 0)

            change = new_amount - old_amount
            change_percent = (change / total_supply) * 100 if total_supply > 0 else 0

            # Only track significant whale movements (>1% of supply)
            if abs(change_percent) > 1.0:
                if change > 0:
                    whale_buys += 1
                    net_change += change_percent
                elif change < 0:
                    whale_sells += 1
                    net_change += change_percent

        movement_detected = whale_buys > 0 or whale_sells > 0

        return {
            'movement_detected': movement_detected,
            'whale_buys': whale_buys,
            'whale_sells': whale_sells,
            'net_change': net_change,
            'signal': 'accumulation' if net_change > 2 else 'distribution' if net_change < -2 else 'neutral'
        }

    async def quick_whale_check(self, token_address: str, token_supply: Optional[float] = None) -> Dict:
        """
        Quick whale analysis for a token.

        Args:
            token_address: Token mint address
            token_supply: Optional total supply (if known)

        Returns:
            Whale analysis dictionary
        """
        # Get top holders
        holders = await self.get_token_holders(token_address, limit=20)

        if not holders:
            return {
                'whale_risk': 'unknown',
                'concentration_risk': 'unknown',
                'is_safe': True,  # Don't block if data unavailable
                'warnings': ['Whale data unavailable'],
                'checked_at': datetime.now().isoformat()
            }

        # If supply not provided, try to calculate from holders
        if not token_supply:
            # Estimate supply from first holder's percentage (if provided by API)
            first_holder = holders[0]
            if 'amount' in first_holder and 'percentage' in first_holder:
                amount = float(first_holder['amount'])
                percentage = float(first_holder['percentage'])
                if percentage > 0:
                    token_supply = (amount / percentage) * 100

        if not token_supply or token_supply <= 0:
            # Can't analyze without supply
            return {
                'whale_risk': 'unknown',
                'concentration_risk': 'unknown',
                'is_safe': True,
                'warnings': ['Token supply unknown'],
                'checked_at': datetime.now().isoformat()
            }

        # Analyze concentration
        analysis = self.analyze_holder_concentration(holders, token_supply)

        # Determine overall whale risk
        if analysis['concentration_risk'] in ['critical', 'high']:
            whale_risk = 'high'
            is_safe = False
        elif analysis['concentration_risk'] == 'medium':
            whale_risk = 'medium'
            is_safe = True  # Medium risk is acceptable
        else:
            whale_risk = 'low'
            is_safe = True

        return {
            'whale_risk': whale_risk,
            'concentration_risk': analysis['concentration_risk'],
            'top_holder_percent': analysis['top_holder_percent'],
            'top_10_percent': analysis['top_10_percent'],
            'whale_count': analysis['whale_count'],
            'is_safe': is_safe,
            'warnings': analysis['warnings'],
            'checked_at': datetime.now().isoformat()
        }

    async def analyze_token_distribution(self, token_address: str) -> Dict:
        """
        Comprehensive token distribution analysis.

        Args:
            token_address: Token mint address

        Returns:
            Distribution analysis dictionary
        """
        holders = await self.get_token_holders(token_address, limit=50)

        if not holders:
            return {
                'distribution_quality': 'unknown',
                'holder_count': 0,
                'recommendation': 'SKIP'
            }

        # Analyze holder distribution
        holder_count = len(holders)

        # Healthy distribution indicators
        healthy_indicators = []
        unhealthy_indicators = []

        if holder_count >= 100:
            healthy_indicators.append('Large holder base (100+)')
        elif holder_count < 20:
            unhealthy_indicators.append('Very small holder base (<20)')

        # Check for even distribution
        if holder_count >= 10:
            top_5_amounts = [float(h.get('amount', 0)) for h in holders[:5]]
            next_5_amounts = [float(h.get('amount', 0)) for h in holders[5:10]]

            if top_5_amounts and next_5_amounts:
                top_5_avg = sum(top_5_amounts) / len(top_5_amounts)
                next_5_avg = sum(next_5_amounts) / len(next_5_amounts)

                if top_5_avg / next_5_avg < 3:  # Not too concentrated
                    healthy_indicators.append('Even distribution among top holders')
                else:
                    unhealthy_indicators.append('Very uneven distribution')

        # Overall quality assessment
        if len(healthy_indicators) >= 2 and len(unhealthy_indicators) == 0:
            distribution_quality = 'excellent'
            recommendation = 'BUY'
        elif len(healthy_indicators) > len(unhealthy_indicators):
            distribution_quality = 'good'
            recommendation = 'WATCH'
        elif len(unhealthy_indicators) > 0:
            distribution_quality = 'poor'
            recommendation = 'SKIP'
        else:
            distribution_quality = 'fair'
            recommendation = 'WATCH'

        return {
            'distribution_quality': distribution_quality,
            'holder_count': holder_count,
            'healthy_indicators': healthy_indicators,
            'unhealthy_indicators': unhealthy_indicators,
            'recommendation': recommendation,
            'timestamp': datetime.now().isoformat()
        }

    async def health_check(self) -> bool:
        """
        Check if Solscan API is accessible.

        Returns:
            True if healthy, False otherwise
        """
        await self._ensure_session()

        try:
            # Try a simple API call
            url = f"{self.base_url}/chaininfo"

            async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                return response.status in [200, 429]  # 429 means rate limited but API is working

        except Exception as e:
            logger.error(f"Whale analyzer health check failed: {e}")
            return False
