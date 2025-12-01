"""
RugCheck API client for Solana token security analysis.
Official API docs: https://rugcheck.xyz/
"""

import asyncio
import aiohttp
from typing import Dict, Optional
from datetime import datetime
from ..monitoring.logger import get_logger

logger = get_logger(__name__)


class RugCheckClient:
    """Client for RugCheck API to assess token security risks."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize RugCheck client.

        Args:
            api_key: RugCheck API key
        """
        self.api_key = api_key
        self.base_url = "https://api.rugcheck.xyz/v1"
        self.session: Optional[aiohttp.ClientSession] = None
        self._enabled = api_key is not None and api_key != "your_actual_key_here"

    async def _ensure_session(self):
        """Ensure aiohttp session exists."""
        if not self._enabled:
            return

        if self.session is None or self.session.closed:
            headers = {
                'X-API-KEY': self.api_key,
                'Content-Type': 'application/json'
            }
            self.session = aiohttp.ClientSession(headers=headers)

    async def close(self):
        """Close the client session."""
        if self.session and not self.session.closed:
            await self.session.close()

    async def get_token_report(self, token_address: str) -> Optional[Dict]:
        """
        Get detailed security report for a token.

        Args:
            token_address: Token mint address

        Returns:
            Token report dictionary or None if failed
        """
        if not self._enabled:
            logger.debug("RugCheck client not enabled (no API key)")
            return None

        await self._ensure_session()

        try:
            url = f"{self.base_url}/tokens/{token_address}/report"

            async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.debug(f"Retrieved RugCheck report for {token_address[:8]}...")
                    return data
                elif response.status == 404:
                    logger.debug(f"Token {token_address[:8]}... not found in RugCheck")
                    return None
                elif response.status == 429:
                    logger.warning("RugCheck API rate limit reached")
                    return None
                else:
                    logger.error(f"RugCheck API error: {response.status}")
                    return None

        except asyncio.TimeoutError:
            logger.warning(f"RugCheck API timeout for {token_address[:8]}...")
            return None
        except Exception as e:
            logger.error(f"Error fetching RugCheck report: {e}")
            return None

    async def get_token_summary(self, token_address: str) -> Optional[Dict]:
        """
        Get summary security report for a token (faster).

        Args:
            token_address: Token mint address

        Returns:
            Token summary dictionary or None if failed
        """
        if not self._enabled:
            logger.debug("RugCheck client not enabled (no API key)")
            return None

        await self._ensure_session()

        try:
            url = f"{self.base_url}/tokens/{token_address}/report/summary"

            async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.debug(f"Retrieved RugCheck summary for {token_address[:8]}...")
                    return data
                elif response.status == 404:
                    logger.debug(f"Token {token_address[:8]}... not found in RugCheck")
                    return None
                elif response.status == 429:
                    logger.warning("RugCheck API rate limit reached")
                    return None
                else:
                    logger.error(f"RugCheck API error: {response.status}")
                    return None

        except asyncio.TimeoutError:
            logger.warning(f"RugCheck API timeout for {token_address[:8]}...")
            return None
        except Exception as e:
            logger.error(f"Error fetching RugCheck summary: {e}")
            return None

    def analyze_risk(self, report: Dict) -> Dict:
        """
        Analyze risk level from RugCheck report.

        Args:
            report: RugCheck report data

        Returns:
            Risk analysis dictionary
        """
        if not report:
            return {
                'risk_level': 'unknown',
                'risk_score': 0.0,
                'is_safe': False,
                'risks': [],
                'warnings': []
            }

        # Extract risk data from report
        risks = report.get('risks', [])
        score = report.get('score', 0)

        # Additional risk indicators
        token_meta = report.get('tokenMeta', {})
        markets = report.get('markets', [])
        top_holders = report.get('topHolders', [])

        warnings = []
        risk_factors = []

        # Analyze RugCheck score (0-100, higher is safer)
        if score < 30:
            risk_level = 'critical'
            risk_factors.append('Very low RugCheck score')
        elif score < 50:
            risk_level = 'high'
            risk_factors.append('Low RugCheck score')
        elif score < 70:
            risk_level = 'medium'
        else:
            risk_level = 'low'

        # Check for specific risk flags
        for risk in risks:
            risk_name = risk.get('name', '')
            risk_level_flag = risk.get('level', '')
            risk_description = risk.get('description', '')

            if risk_level_flag in ['danger', 'critical']:
                risk_factors.append(f"CRITICAL: {risk_name}")
            elif risk_level_flag == 'warning':
                warnings.append(f"WARNING: {risk_name}")

        # Check token metadata
        if token_meta:
            if not token_meta.get('updateAuthority'):
                warnings.append("No update authority (immutable metadata)")

            if token_meta.get('freezeAuthority'):
                risk_factors.append("Freeze authority exists (can freeze tokens)")

        # Check liquidity and holder concentration
        if markets:
            total_liquidity = sum(m.get('liquidity', {}).get('usd', 0) for m in markets)
            if total_liquidity < 10000:
                warnings.append(f"Low liquidity (${total_liquidity:,.0f})")

        if top_holders:
            # Check if top holder owns > 50% (excluding known exchanges)
            top_holder = top_holders[0] if top_holders else {}
            top_holder_pct = top_holder.get('pct', 0) * 100
            if top_holder_pct > 50:
                risk_factors.append(f"Top holder owns {top_holder_pct:.1f}% of supply")

        # Determine if safe to trade
        is_safe = (
            risk_level in ['low', 'medium'] and
            len(risk_factors) == 0 and
            score >= 50
        )

        return {
            'risk_level': risk_level,
            'risk_score': score,
            'is_safe': is_safe,
            'risks': risk_factors,
            'warnings': warnings,
            'raw_report': report
        }

    async def quick_check(self, token_address: str) -> Dict:
        """
        Quick risk check for a token (optimized for speed).

        Args:
            token_address: Token mint address

        Returns:
            Quick risk assessment
        """
        # Use summary endpoint for speed
        summary = await self.get_token_summary(token_address)

        if not summary:
            # If RugCheck not available, return neutral result
            return {
                'token_address': token_address,
                'risk_level': 'unknown',
                'risk_score': 50.0,  # Neutral score
                'is_safe': True,  # Don't block if service unavailable
                'risks': [],
                'warnings': ['RugCheck data unavailable'],
                'checked_at': datetime.now().isoformat()
            }

        risk_analysis = self.analyze_risk(summary)

        return {
            'token_address': token_address,
            'risk_level': risk_analysis['risk_level'],
            'risk_score': risk_analysis['risk_score'],
            'is_safe': risk_analysis['is_safe'],
            'risks': risk_analysis['risks'],
            'warnings': risk_analysis['warnings'],
            'checked_at': datetime.now().isoformat()
        }

    async def get_trending_tokens(self) -> list:
        """
        Get trending tokens from RugCheck.

        Returns:
            List of trending token addresses
        """
        if not self._enabled:
            return []

        await self._ensure_session()

        try:
            url = f"{self.base_url}/stats/trending"

            async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                if response.status == 200:
                    data = await response.json()
                    tokens = data.get('tokens', [])
                    logger.debug(f"Retrieved {len(tokens)} trending tokens from RugCheck")
                    return tokens
                else:
                    logger.error(f"RugCheck trending API error: {response.status}")
                    return []

        except Exception as e:
            logger.error(f"Error fetching trending tokens: {e}")
            return []

    async def get_new_tokens(self) -> list:
        """
        Get newly detected tokens from RugCheck.

        Returns:
            List of new token addresses
        """
        if not self._enabled:
            return []

        await self._ensure_session()

        try:
            url = f"{self.base_url}/stats/new_tokens"

            async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                if response.status == 200:
                    data = await response.json()
                    tokens = data.get('tokens', [])
                    logger.debug(f"Retrieved {len(tokens)} new tokens from RugCheck")
                    return tokens
                else:
                    logger.error(f"RugCheck new tokens API error: {response.status}")
                    return []

        except Exception as e:
            logger.error(f"Error fetching new tokens: {e}")
            return []

    async def health_check(self) -> bool:
        """
        Check if RugCheck API is accessible.

        Returns:
            True if healthy, False otherwise
        """
        if not self._enabled:
            return True  # Consider it healthy if not configured

        await self._ensure_session()

        try:
            # Try to get trending tokens as health check
            url = f"{self.base_url}/stats/trending"

            async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                return response.status in [200, 429]  # 429 means rate limited but API is working

        except Exception as e:
            logger.error(f"RugCheck health check failed: {e}")
            return False
