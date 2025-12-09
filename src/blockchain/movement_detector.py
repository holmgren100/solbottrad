"""
Blockchain unusual movement detector.
Detects suspicious patterns like rapid transfers, coordinated activity, and rug signals.
"""

import aiohttp
import asyncio
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict
from ..monitoring.logger import get_logger

logger = get_logger(__name__)


class MovementDetector:
    """Detects unusual blockchain movements and suspicious patterns."""

    def __init__(self, solscan_api_key: Optional[str] = None):
        """
        Initialize movement detector.

        Args:
            solscan_api_key: Solscan Pro API key (v2.0)
        """
        self.solscan_api_key = solscan_api_key
        self.base_url = "https://pro-api.solscan.io/v2.0"  # Official v2.0 API
        self.session: Optional[aiohttp.ClientSession] = None
        self._enabled = solscan_api_key is not None  # v2.0 requires API key

        # Pattern detection thresholds
        self.rapid_transfer_threshold = 10  # 10+ transfers in 5 min = suspicious
        self.rapid_transfer_window_minutes = 5

        # Track recent activity
        self.recent_activity: Dict[str, List[datetime]] = defaultdict(list)

    async def _ensure_session(self):
        """Ensure aiohttp session exists."""
        if self.session is None or self.session.closed:
            headers = {
                'Accept': 'application/json'
            }
            # Solscan Pro API v2.0 requires API key via 'token' header
            if self.solscan_api_key:
                headers['token'] = self.solscan_api_key
            self.session = aiohttp.ClientSession(headers=headers)

    async def close(self):
        """Close the client session."""
        if self.session and not self.session.closed:
            await self.session.close()

    async def get_recent_transfers(
        self,
        token_address: str,
        limit: int = 50
    ) -> Optional[List[Dict]]:
        """
        Get recent token transfers from Solscan v2.0 API.
        Official endpoint: GET /v2.0/token/transfer

        Args:
            token_address: Token mint address
            limit: Number of transfers to fetch

        Returns:
            List of transfer dictionaries or None if failed
        """
        if not self._enabled:
            logger.debug("Movement detector disabled (no Solscan API key)")
            return None

        await self._ensure_session()

        try:
            # Official Solscan v2.0 endpoint
            url = f"{self.base_url}/token/transfer"
            params = {
                'address': token_address,
                'page': 1,
                'page_size': min(limit, 50)  # v2.0 uses page_size
            }

            async with self.session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    data = await response.json()
                    transfers = data.get('data', [])
                    logger.debug(f"Retrieved {len(transfers)} transfers for {token_address[:8]}...")
                    return transfers
                elif response.status == 429:
                    logger.warning("Solscan API rate limit reached")
                    return None
                elif response.status == 401:
                    logger.error("Solscan API authentication failed (check API key)")
                    return None
                else:
                    logger.debug(f"Solscan transfer API returned {response.status}")
                    return None

        except asyncio.TimeoutError:
            logger.warning(f"Solscan API timeout for transfers {token_address[:8]}...")
            return None
        except Exception as e:
            logger.debug(f"Error fetching transfers: {e}")
            return None

    def analyze_transfer_pattern(self, transfers: List[Dict]) -> Dict:
        """
        Analyze transfer patterns for suspicious activity.

        Args:
            transfers: List of transfer data

        Returns:
            Pattern analysis dictionary
        """
        if not transfers:
            return {
                'pattern': 'unknown',
                'is_suspicious': False,
                'flags': []
            }

        flags = []
        is_suspicious = False

        # Group transfers by time windows
        now = datetime.now()
        window_5min = now - timedelta(minutes=5)
        window_15min = now - timedelta(minutes=15)
        window_1hour = now - timedelta(hours=1)

        transfers_5min = []
        transfers_15min = []
        transfers_1hour = []

        for transfer in transfers:
            # Parse timestamp (assuming Unix timestamp in seconds)
            timestamp = transfer.get('blockTime', 0)
            if timestamp:
                transfer_time = datetime.fromtimestamp(timestamp)

                if transfer_time > window_5min:
                    transfers_5min.append(transfer)
                if transfer_time > window_15min:
                    transfers_15min.append(transfer)
                if transfer_time > window_1hour:
                    transfers_1hour.append(transfer)

        # Flag 1: Rapid transfers (>10 in 5 minutes)
        if len(transfers_5min) >= self.rapid_transfer_threshold:
            flags.append(f'RAPID_TRANSFERS ({len(transfers_5min)} in 5min)')
            is_suspicious = True

        # Flag 2: Burst activity (3x more in recent 15min vs previous hour)
        if len(transfers_1hour) > 0:
            transfers_prev_45min = len(transfers_1hour) - len(transfers_15min)
            if transfers_prev_45min > 0:
                recent_rate = len(transfers_15min) / 15  # per minute
                prev_rate = transfers_prev_45min / 45    # per minute
                if recent_rate > prev_rate * 3:
                    flags.append('BURST_ACTIVITY')
                    is_suspicious = True

        # Flag 3: Check for coordinated wallets (same wallets appearing multiple times)
        if len(transfers) >= 10:
            from_wallets = [t.get('from', '') for t in transfers[:20]]
            to_wallets = [t.get('to', '') for t in transfers[:20]]

            # Count wallet occurrences
            from_counts = defaultdict(int)
            to_counts = defaultdict(int)

            for wallet in from_wallets:
                if wallet:
                    from_counts[wallet] += 1
            for wallet in to_wallets:
                if wallet:
                    to_counts[wallet] += 1

            # Check for wallets appearing >3 times (coordinated activity)
            frequent_senders = [w for w, c in from_counts.items() if c > 3]
            frequent_receivers = [w for w, c in to_counts.items() if c > 3]

            if frequent_senders:
                flags.append(f'COORDINATED_SENDERS ({len(frequent_senders)} wallets)')
                is_suspicious = True
            if frequent_receivers:
                flags.append(f'COORDINATED_RECEIVERS ({len(frequent_receivers)} wallets)')

        # Flag 4: Large transfer concentration (one wallet receiving >50% of recent volume)
        if len(transfers_15min) >= 5:
            amounts_by_receiver = defaultdict(float)
            total_amount = 0.0

            for transfer in transfers_15min:
                to_wallet = transfer.get('to', '')
                amount = float(transfer.get('amount', 0))
                if to_wallet and amount > 0:
                    amounts_by_receiver[to_wallet] += amount
                    total_amount += amount

            if total_amount > 0:
                max_receiver_amount = max(amounts_by_receiver.values()) if amounts_by_receiver else 0
                concentration = (max_receiver_amount / total_amount) * 100

                if concentration > 50:
                    flags.append(f'HIGH_CONCENTRATION ({concentration:.1f}% to one wallet)')
                    is_suspicious = True

        # Classify pattern
        if len(flags) >= 3:
            pattern = 'highly_suspicious'
        elif len(flags) >= 2:
            pattern = 'suspicious'
        elif len(flags) >= 1:
            pattern = 'unusual'
        else:
            pattern = 'normal'

        return {
            'pattern': pattern,
            'is_suspicious': is_suspicious,
            'flags': flags,
            'transfers_5min': len(transfers_5min),
            'transfers_15min': len(transfers_15min),
            'transfers_1hour': len(transfers_1hour)
        }

    def detect_rug_signals(self, transfers: List[Dict], holder_data: Optional[List[Dict]] = None) -> Dict:
        """
        Detect rug pull signals from transfer patterns.

        Args:
            transfers: Recent transfer data
            holder_data: Optional holder concentration data

        Returns:
            Rug signal analysis
        """
        if not transfers:
            return {
                'rug_risk': 'unknown',
                'signals': [],
                'risk_score': 0.0
            }

        signals = []
        risk_score = 0.0

        # Signal 1: Mass exodus (many sells, few buys)
        recent_transfers = transfers[:20]  # Last 20 transfers
        sells = sum(1 for t in recent_transfers if t.get('type') == 'sell' or t.get('from') != t.get('mint'))
        buys = len(recent_transfers) - sells

        if sells > buys * 3:  # 3x more sells than buys
            signals.append('MASS_EXODUS')
            risk_score += 0.3

        # Signal 2: Wallet draining (top holders moving large amounts)
        if holder_data:
            # Check if top holders are in recent transfers
            top_holder_addresses = {h.get('address', '') for h in holder_data[:10]}
            transfers_from_whales = [
                t for t in transfers[:20]
                if t.get('from', '') in top_holder_addresses
            ]

            if len(transfers_from_whales) >= 3:
                signals.append('WHALE_DUMPING')
                risk_score += 0.4

        # Signal 3: Liquidity pool drainage
        lp_keywords = ['raydium', 'orca', 'liquidity', 'pool']
        lp_transfers = [
            t for t in transfers[:30]
            if any(keyword in str(t.get('from', '')).lower() for keyword in lp_keywords)
        ]

        if len(lp_transfers) >= 2:
            signals.append('LIQUIDITY_REMOVAL')
            risk_score += 0.5  # Very serious signal

        # Classify rug risk
        if risk_score >= 0.7:
            rug_risk = 'critical'
        elif risk_score >= 0.4:
            rug_risk = 'high'
        elif risk_score >= 0.2:
            rug_risk = 'medium'
        else:
            rug_risk = 'low'

        return {
            'rug_risk': rug_risk,
            'signals': signals,
            'risk_score': risk_score,
            'timestamp': datetime.now().isoformat()
        }

    async def quick_movement_check(self, token_address: str) -> Dict:
        """
        Quick check for unusual movements.

        Args:
            token_address: Token mint address

        Returns:
            Movement analysis dictionary
        """
        # Get recent transfers
        transfers = await self.get_recent_transfers(token_address, limit=50)

        if not transfers:
            return {
                'movement_risk': 'unknown',
                'pattern': 'unknown',
                'is_safe': True,  # Don't block if data unavailable
                'warnings': ['Movement data unavailable'],
                'checked_at': datetime.now().isoformat()
            }

        # Analyze patterns
        pattern_analysis = self.analyze_transfer_pattern(transfers)

        # Detect rug signals
        rug_analysis = self.detect_rug_signals(transfers)

        # Combine analyses
        warnings = []
        is_safe = True

        if pattern_analysis['is_suspicious']:
            warnings.extend(pattern_analysis['flags'])
            is_safe = False

        if rug_analysis['rug_risk'] in ['critical', 'high']:
            warnings.extend(rug_analysis['signals'])
            is_safe = False

        # Overall movement risk
        if not is_safe:
            if rug_analysis['rug_risk'] == 'critical':
                movement_risk = 'critical'
            elif pattern_analysis['pattern'] == 'highly_suspicious':
                movement_risk = 'high'
            else:
                movement_risk = 'medium'
        else:
            movement_risk = 'low'

        return {
            'movement_risk': movement_risk,
            'pattern': pattern_analysis['pattern'],
            'rug_risk': rug_analysis['rug_risk'],
            'is_safe': is_safe,
            'warnings': warnings,
            'flags': pattern_analysis['flags'],
            'rug_signals': rug_analysis['signals'],
            'checked_at': datetime.now().isoformat()
        }

    async def health_check(self) -> bool:
        """
        Check if Solscan API is accessible.

        Returns:
            True if healthy, False otherwise
        """
        if not self._enabled:
            return True  # Consider healthy if not configured

        await self._ensure_session()

        try:
            url = f"{self.base_url}/chaininfo"

            async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                return response.status in [200, 429]  # 429 = rate limited but working

        except Exception as e:
            logger.error(f"Movement detector health check failed: {e}")
            return False
