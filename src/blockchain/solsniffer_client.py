"""
SolSniffer API client for token discovery and analysis.
"""

import aiohttp
from typing import Dict, List, Optional
from datetime import datetime
from ..monitoring.logger import get_logger

logger = get_logger(__name__)


class SolSnifferClient:
    """Client for SolSniffer API to discover and analyze tokens."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize SolSniffer client.

        Args:
            api_key: SolSniffer API key (optional)
        """
        self.api_key = api_key
        self.base_url = "https://solsniffer.com/api/v2"
        self.session: Optional[aiohttp.ClientSession] = None

    async def _ensure_session(self):
        """Ensure aiohttp session exists."""
        if self.session is None or self.session.closed:
            headers = {}
            if self.api_key:
                # Use X-API-KEY header (common pattern for API authentication)
                headers['X-API-KEY'] = self.api_key
            self.session = aiohttp.ClientSession(headers=headers)

    async def close(self):
        """Close the client session."""
        if self.session and not self.session.closed:
            await self.session.close()

    async def get_new_tokens(self, limit: int = 50) -> List[Dict]:
        """
        Get recently created tokens.

        Args:
            limit: Maximum number of tokens to retrieve

        Returns:
            List of token dictionaries
        """
        await self._ensure_session()

        try:
            url = f"{self.base_url}/tokens/new"
            params = {'limit': limit}

            async with self.session.get(url, params=params) as response:
                response_text = await response.text()
                logger.info(f"SolSniffer /tokens/new response: status={response.status}, body={response_text[:200]}")

                if response.status == 200:
                    try:
                        import json
                        data = json.loads(response_text)
                        tokens = data.get('tokens', [])
                        logger.info(f"Retrieved {len(tokens)} new tokens from SolSniffer")
                        return tokens
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse JSON response: {e}")
                        return []
                else:
                    logger.error(f"SolSniffer API error: {response.status} - {response_text[:500]}")
                    return []

        except Exception as e:
            logger.error(f"Error fetching new tokens: {e}")
            return []

    async def get_token_security(self, token_address: str) -> Optional[Dict]:
        """
        Get security analysis for a token.

        Args:
            token_address: Token contract address

        Returns:
            Security analysis dictionary or None
        """
        await self._ensure_session()

        try:
            url = f"{self.base_url}/token/{token_address}/security"

            async with self.session.get(url) as response:
                response_text = await response.text()

                if response.status == 200:
                    try:
                        import json
                        data = json.loads(response_text)
                        logger.debug(f"Retrieved security info for {token_address}")
                        return data
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse security JSON: {e}")
                        return None
                else:
                    logger.warning(
                        f"Security info not available for {token_address[:8]}... "
                        f"(status={response.status}, response={response_text[:200]})"
                    )
                    return None

        except Exception as e:
            logger.error(f"Error fetching token security: {e}")
            return None

    async def get_token_metrics(self, token_address: str) -> Optional[Dict]:
        """
        Get metrics for a token.

        Args:
            token_address: Token contract address

        Returns:
            Metrics dictionary or None
        """
        await self._ensure_session()

        try:
            url = f"{self.base_url}/token/{token_address}/metrics"

            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.debug(f"Retrieved metrics for {token_address}")
                    return data
                else:
                    logger.warning(f"Metrics not available for {token_address}")
                    return None

        except Exception as e:
            logger.error(f"Error fetching token metrics: {e}")
            return None

    async def analyze_token(self, token_address: str) -> Dict:
        """
        Get comprehensive analysis of a token.

        Args:
            token_address: Token contract address

        Returns:
            Dictionary with security, metrics, and risk assessment
        """
        security = await self.get_token_security(token_address)
        metrics = await self.get_token_metrics(token_address)

        analysis = {
            'address': token_address,
            'timestamp': datetime.now().isoformat(),
            'security': security or {},
            'metrics': metrics or {},
            'risk_level': self._calculate_risk_level(security, metrics)
        }

        return analysis

    def _calculate_risk_level(
        self,
        security: Optional[Dict],
        metrics: Optional[Dict]
    ) -> str:
        """
        Calculate overall risk level based on security and metrics.

        Args:
            security: Security analysis data
            metrics: Token metrics data

        Returns:
            Risk level: 'low', 'medium', 'high', or 'unknown'
        """
        if not security:
            return 'unknown'

        risk_factors = 0

        # Check for common security issues
        if security.get('is_mintable'):
            risk_factors += 1
        if security.get('has_freeze_authority'):
            risk_factors += 1
        if not security.get('is_verified'):
            risk_factors += 1
        if security.get('ownership_renounced') is False:
            risk_factors += 1

        # Assess based on risk factors
        if risk_factors == 0:
            return 'low'
        elif risk_factors <= 2:
            return 'medium'
        else:
            return 'high'

    async def health_check(self) -> bool:
        """
        Check if SolSniffer API is accessible.

        Returns:
            True if healthy, False otherwise
        """
        await self._ensure_session()

        try:
            url = f"{self.base_url}/health"
            async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                return response.status == 200
        except Exception as e:
            logger.error(f"SolSniffer health check failed: {e}")
            return False
