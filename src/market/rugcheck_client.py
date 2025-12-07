"""
RugCheck API client for token security analysis and holder tracking.
Monitors dev wallets and top holders to avoid dump risks.
"""

import aiohttp
from typing import Dict, List, Optional
from datetime import datetime
from ..monitoring.logger import get_logger

logger = get_logger(__name__)


class RugCheckClient:
    """Client for RugCheck API - token security and holder analysis."""

    def __init__(self):
        """Initialize RugCheck client (no API key needed for basic endpoints)."""
        self.base_url = "https://api.rugcheck.xyz/v1"
        self.session: Optional[aiohttp.ClientSession] = None

    async def _ensure_session(self):
        """Ensure aiohttp session exists."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()

    async def close(self):
        """Close the client session."""
        if self.session and not self.session.closed:
            await self.session.close()

    async def get_token_report(self, token_address: str) -> Optional[Dict]:
        """
        Get comprehensive security report for a token.

        Args:
            token_address: Token mint address

        Returns:
            Security report with risks, holder data, and safety score
        """
        await self._ensure_session()

        try:
            url = f"{self.base_url}/tokens/{token_address}/report"

            async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    data = await response.json()

                    # Calculate safety score
                    safety_score = self._calculate_safety_score(data)

                    # Extract key information
                    report = {
                        'token_address': token_address,
                        'safety_score': safety_score,  # 0-100
                        'risks': data.get('risks', []),
                        'mint_authority': data.get('tokenMeta', {}).get('mintAuthority'),
                        'freeze_authority': data.get('tokenMeta', {}).get('freezeAuthority'),
                        'top_holders': self._parse_holders(data.get('topHolders', [])),
                        'liquidity_locked': data.get('markets', [{}])[0].get('lp', {}).get('lpLockedPct', 0) > 50,
                        'total_supply': data.get('tokenMeta', {}).get('totalSupply', 0),
                        'decimals': data.get('tokenMeta', {}).get('decimals', 0),
                        'timestamp': datetime.now().isoformat()
                    }

                    logger.info(
                        f"RugCheck: {token_address[:8]}... "
                        f"Safety: {safety_score}/100, "
                        f"Risks: {len(report['risks'])}"
                    )

                    return report

                elif response.status == 404:
                    logger.warning(f"RugCheck: Token {token_address[:8]}... not found")
                    return None
                else:
                    logger.error(f"RugCheck API error: {response.status}")
                    return None

        except asyncio.TimeoutError:
            logger.warning(f"RugCheck timeout for {token_address[:8]}...")
            return None
        except Exception as e:
            logger.error(f"Error fetching RugCheck report: {e}")
            return None

    def _calculate_safety_score(self, report_data: Dict) -> int:
        """
        Calculate safety score 0-100 from RugCheck data.

        Higher score = safer token
        Lower score = more risks

        Args:
            report_data: Raw RugCheck report

        Returns:
            Safety score 0-100
        """
        score = 100

        # Check mint authority (can create more tokens)
        token_meta = report_data.get('tokenMeta', {})
        if token_meta.get('mintAuthority'):
            score -= 30
            logger.debug("  -30: Mint authority present")

        # Check freeze authority (can freeze accounts)
        if token_meta.get('freezeAuthority'):
            score -= 30
            logger.debug("  -30: Freeze authority present")

        # Check liquidity lock
        markets = report_data.get('markets', [])
        if markets:
            lp_locked_pct = markets[0].get('lp', {}).get('lpLockedPct', 0)
            if lp_locked_pct < 50:
                score -= 20
                logger.debug(f"  -20: Liquidity not locked ({lp_locked_pct}%)")
            elif lp_locked_pct < 80:
                score -= 10
                logger.debug(f"  -10: Liquidity partially locked ({lp_locked_pct}%)")

        # Check top holder concentration
        top_holders = report_data.get('topHolders', [])
        if top_holders:
            # Calculate top 10 holders percentage
            top_10_pct = sum(float(h.get('pct', 0)) for h in top_holders[:10])

            if top_10_pct > 70:
                score -= 20
                logger.debug(f"  -20: Top 10 holders own {top_10_pct:.1f}%")
            elif top_10_pct > 50:
                score -= 10
                logger.debug(f"  -10: Top 10 holders own {top_10_pct:.1f}%")

        # Check for known risk flags
        risks = report_data.get('risks', [])
        high_risk_count = len([r for r in risks if r.get('level') == 'danger'])
        medium_risk_count = len([r for r in risks if r.get('level') == 'warn'])

        score -= high_risk_count * 10
        score -= medium_risk_count * 5

        if high_risk_count > 0:
            logger.debug(f"  -{high_risk_count * 10}: {high_risk_count} high risks")
        if medium_risk_count > 0:
            logger.debug(f"  -{medium_risk_count * 5}: {medium_risk_count} medium risks")

        return max(score, 0)

    def _parse_holders(self, holders_data: List[Dict]) -> List[Dict]:
        """
        Parse and enrich holder data.

        Args:
            holders_data: Raw holder data from RugCheck

        Returns:
            List of holder dictionaries with useful info
        """
        parsed = []

        for idx, holder in enumerate(holders_data[:10]):  # Top 10
            parsed.append({
                'rank': idx + 1,
                'address': holder.get('address', ''),
                'percentage': float(holder.get('pct', 0)),
                'amount': float(holder.get('amount', 0)),
                'is_dev': holder.get('isDev', False),
                'is_locked': holder.get('isLocked', False),
                'is_suspicious': self._is_suspicious_holder(holder)
            })

        return parsed

    def _is_suspicious_holder(self, holder: Dict) -> bool:
        """
        Check if holder looks suspicious.

        Args:
            holder: Holder data

        Returns:
            True if suspicious patterns detected
        """
        # High percentage holder that's not locked
        if float(holder.get('pct', 0)) > 10 and not holder.get('isLocked', False):
            return True

        # Dev wallet with high percentage
        if holder.get('isDev', False) and float(holder.get('pct', 0)) > 5:
            return True

        return False

    async def analyze_holder_risk(self, token_address: str) -> Dict:
        """
        Analyze holder distribution for dump risk.

        This is the CRITICAL function to avoid getting dumped on.

        Args:
            token_address: Token mint address

        Returns:
            Risk analysis with actionable insights
        """
        report = await self.get_token_report(token_address)

        if not report:
            return {
                'risk_level': 'unknown',
                'can_enter': False,
                'reason': 'No RugCheck data available'
            }

        holders = report['top_holders']
        safety_score = report['safety_score']

        # Calculate metrics
        top_5_pct = sum(h['percentage'] for h in holders[:5]) if holders else 0
        top_10_pct = sum(h['percentage'] for h in holders[:10]) if holders else 0

        dev_holders = [h for h in holders if h['is_dev']]
        suspicious_holders = [h for h in holders if h['is_suspicious']]

        dev_total_pct = sum(h['percentage'] for h in dev_holders)

        # Risk assessment
        risk_level = 'low'
        can_enter = True
        warnings = []

        # Critical risks - DO NOT ENTER
        if safety_score < 30:
            risk_level = 'critical'
            can_enter = False
            warnings.append(f"Safety score too low: {safety_score}/100")

        if report['mint_authority']:
            risk_level = 'critical'
            can_enter = False
            warnings.append("Mint authority active - can print tokens!")

        if report['freeze_authority']:
            risk_level = 'critical'
            can_enter = False
            warnings.append("Freeze authority active - can lock your funds!")

        if top_5_pct > 80:
            risk_level = 'critical'
            can_enter = False
            warnings.append(f"Top 5 holders own {top_5_pct:.1f}% - extreme concentration!")

        # High risks - Enter with caution (small position)
        if risk_level != 'critical':
            if top_10_pct > 60:
                risk_level = 'high'
                warnings.append(f"Top 10 holders own {top_10_pct:.1f}%")

            if dev_total_pct > 15:
                risk_level = 'high'
                warnings.append(f"Dev wallets own {dev_total_pct:.1f}%")

            if len(suspicious_holders) > 2:
                risk_level = 'high'
                warnings.append(f"{len(suspicious_holders)} suspicious large holders")

            if not report['liquidity_locked']:
                risk_level = 'high'
                warnings.append("Liquidity not locked - rug risk!")

        # Medium risks
        if risk_level not in ['critical', 'high']:
            if top_10_pct > 40:
                risk_level = 'medium'
                warnings.append(f"Top 10 holders own {top_10_pct:.1f}%")

            if safety_score < 60:
                risk_level = 'medium'
                warnings.append(f"Safety score: {safety_score}/100")

        # Log analysis
        logger.info(
            f"📊 Holder Analysis {token_address[:8]}...: "
            f"Risk={risk_level}, "
            f"Safety={safety_score}/100, "
            f"Top5={top_5_pct:.1f}%, "
            f"Dev={dev_total_pct:.1f}%"
        )

        return {
            'risk_level': risk_level,  # critical/high/medium/low
            'can_enter': can_enter,
            'safety_score': safety_score,
            'top_5_percentage': top_5_pct,
            'top_10_percentage': top_10_pct,
            'dev_percentage': dev_total_pct,
            'suspicious_holder_count': len(suspicious_holders),
            'warnings': warnings,
            'liquidity_locked': report['liquidity_locked'],
            'recommended_position_size': self._get_recommended_position(risk_level)
        }

    def _get_recommended_position(self, risk_level: str) -> str:
        """Get recommended position size based on risk."""
        if risk_level == 'critical':
            return 'SKIP'
        elif risk_level == 'high':
            return '$15-20 (high risk)'
        elif risk_level == 'medium':
            return '$25-30 (medium risk)'
        else:
            return '$35-40 (normal)'
