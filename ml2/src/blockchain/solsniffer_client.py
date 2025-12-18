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

        NOTE: SolSniffer API v2 does not have a "new tokens" endpoint.
        SolSniffer is for security analysis of known tokens, not token discovery.
        This method returns an empty list - use other sources for token discovery.

        Args:
            limit: Maximum number of tokens to retrieve (unused)

        Returns:
            Empty list (SolSniffer doesn't support token discovery)
        """
        logger.info("SolSniffer does not support token discovery - use DexScreener or other sources")
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
            # SolSniffer API v2 endpoint: /token/{address}
            url = f"{self.base_url}/token/{token_address}"

            async with self.session.get(url) as response:
                response_text = await response.text()

                if response.status == 200:
                    try:
                        import json
                        data = json.loads(response_text)
                        logger.debug(f"Retrieved token data for {token_address[:8]}...")
                        return data
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse token JSON: {e}")
                        return None
                else:
                    # Use debug for rate limits (429) to reduce log noise
                    log_level = logger.debug if response.status == 429 else logger.warning
                    log_level(
                        f"Token data not available for {token_address[:8]}... "
                        f"(status={response.status})"
                    )
                    return None

        except Exception as e:
            logger.error(f"Error fetching token data: {e}")
            return None

    async def get_token_metrics(self, token_address: str) -> Optional[Dict]:
        """
        Get metrics for a token.

        NOTE: In API v2, metrics are included in the main /token/{address} endpoint.
        This method calls get_token_security() which gets all token data.

        Args:
            token_address: Token contract address

        Returns:
            Metrics dictionary or None
        """
        # In v2, all token data (security + metrics) comes from /token/{address}
        # Just call get_token_security which now uses the correct endpoint
        return await self.get_token_security(token_address)

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
