"""
Dynamic token scoring system with adaptive thresholds.
NO HARD SETTINGS - learns from recent trade performance.
"""

import os
import json
from typing import Dict, Optional
from datetime import datetime
from ..monitoring.logger import get_logger

logger = get_logger(__name__)


class DynamicTokenScorer:
    """
    Score tokens 0-100 based on multiple factors.
    Thresholds adapt based on recent winner/loser analysis.
    """

    def __init__(self, trades_file: str = "data/ml_training/ml_trades.jsonl"):
        """
        Initialize dynamic scorer.

        Args:
            trades_file: Path to trade history for learning
        """
        self.trades_file = trades_file

        # Default thresholds (will be updated from recent trades)
        self.thresholds = {
            'min_liquidity': 50000,
            'good_liquidity': 100000,
            'excellent_liquidity': 150000,
            'min_volume': 100000,
            'good_volume': 200000,
            'excellent_volume': 500000,
            'min_score': 50,
            'medium_score': 60,
            'high_score': 70
        }

        # Load adaptive thresholds from recent trades
        self._update_thresholds_from_history()

    def _update_thresholds_from_history(self):
        """Update thresholds based on last 200 trades."""
        if not os.path.exists(self.trades_file):
            logger.warning(f"Trade file not found: {self.trades_file}, using defaults")
            return

        try:
            # Load last 200 trades
            trades = []
            with open(self.trades_file, 'r') as f:
                lines = f.readlines()
                for line in lines[-200:]:  # Last 200
                    trades.append(json.loads(line))

            if len(trades) < 20:
                logger.info(f"Only {len(trades)} trades, using default thresholds")
                return

            # Separate winners and losers
            winners = [t for t in trades if t.get('win', False)]
            losers = [t for t in trades if not t.get('win', False)]

            if len(winners) < 10:
                logger.info(f"Only {len(winners)} winners, using default thresholds")
                return

            # Calculate median values for winners (25th percentile = minimum bar)
            winner_liquidity = sorted([t['entry_liquidity_usd'] for t in winners if 'entry_liquidity_usd' in t])
            winner_volume = sorted([t.get('entry_volume_24h', 0) for t in winners])

            if winner_liquidity:
                # Use 25th percentile (bottom 25% of winners)
                idx_25 = len(winner_liquidity) // 4
                idx_50 = len(winner_liquidity) // 2
                idx_75 = len(winner_liquidity) * 3 // 4

                self.thresholds['min_liquidity'] = max(winner_liquidity[idx_25], 30000)  # Floor at $30k
                self.thresholds['good_liquidity'] = winner_liquidity[idx_50]
                self.thresholds['excellent_liquidity'] = winner_liquidity[idx_75]

            if winner_volume:
                idx_25 = len(winner_volume) // 4
                idx_50 = len(winner_volume) // 2
                idx_75 = len(winner_volume) * 3 // 4

                self.thresholds['min_volume'] = max(winner_volume[idx_25], 10000)  # Floor at $10k
                self.thresholds['good_volume'] = winner_volume[idx_50]
                self.thresholds['excellent_volume'] = winner_volume[idx_75]

            logger.info(
                f"📊 Updated thresholds from {len(trades)} trades ({len(winners)} winners): "
                f"Liq ${self.thresholds['min_liquidity']:,.0f}/"
                f"${self.thresholds['good_liquidity']:,.0f}/"
                f"${self.thresholds['excellent_liquidity']:,.0f}, "
                f"Vol ${self.thresholds['min_volume']:,.0f}/"
                f"${self.thresholds['good_volume']:,.0f}/"
                f"${self.thresholds['excellent_volume']:,.0f}"
            )

        except Exception as e:
            logger.error(f"Error updating thresholds: {e}")

    def score_token(
        self,
        token_data: Dict,
        rugcheck_data: Optional[Dict] = None,
        market_data: Optional[Dict] = None
    ) -> Dict:
        """
        Score token 0-100 based on all available data.

        Args:
            token_data: Data from multi-source aggregator
            rugcheck_data: Holder analysis from RugCheck (optional)
            market_data: Market conditions (optional)

        Returns:
            Scoring result with breakdown and recommendation
        """
        score = 0
        breakdown = {}
        warnings = []

        # FACTOR 1: LIQUIDITY (50 points max) - MOST IMPORTANT
        liquidity = token_data.get('liquidity', 0)

        if liquidity >= self.thresholds['excellent_liquidity']:
            liq_score = 50
        elif liquidity >= self.thresholds['good_liquidity']:
            liq_score = 40
        elif liquidity >= self.thresholds['min_liquidity']:
            liq_score = 25
        else:
            liq_score = 0
            warnings.append(f"Liquidity ${liquidity:,.0f} below minimum ${self.thresholds['min_liquidity']:,.0f}")

        score += liq_score
        breakdown['liquidity'] = liq_score

        # FACTOR 2: DATA CONFIDENCE (15 points) - NEW!
        confidence = token_data.get('confidence', 'none')

        if confidence == 'high':  # 2+ sources agree
            conf_score = 15
        elif confidence == 'medium':  # 2+ sources but disagree
            conf_score = 10
        elif confidence == 'low':  # Single source
            conf_score = 5
            warnings.append("Only single data source available")
        else:
            conf_score = 0
            warnings.append("No reliable data sources")

        score += conf_score
        breakdown['confidence'] = conf_score

        # FACTOR 3: VOLUME (15 points)
        volume = token_data.get('volume_24h', 0)

        if volume >= self.thresholds['excellent_volume']:
            vol_score = 15
        elif volume >= self.thresholds['good_volume']:
            vol_score = 12
        elif volume >= self.thresholds['min_volume']:
            vol_score = 8
        else:
            vol_score = 3

        score += vol_score
        breakdown['volume'] = vol_score

        # FACTOR 4: RUGCHECK SAFETY (20 points if available)
        if rugcheck_data:
            safety_score = rugcheck_data.get('safety_score', 0)

            if safety_score >= 80:
                rug_score = 20
            elif safety_score >= 60:
                rug_score = 15
            elif safety_score >= 40:
                rug_score = 10
                warnings.append(f"RugCheck safety only {safety_score}/100")
            else:
                rug_score = 0
                warnings.append(f"RugCheck safety critically low: {safety_score}/100")

            # CRITICAL: Auto-fail on critical risks
            if not rugcheck_data.get('can_enter', True):
                score = 0
                warnings.insert(0, "CRITICAL: " + rugcheck_data.get('warnings', ['Unknown risk'])[0])
                return self._build_result(score, breakdown, warnings, token_data, rugcheck_data, market_data)

            score += rug_score
            breakdown['rugcheck'] = rug_score

            # Add holder risk warnings
            if rugcheck_data.get('risk_level') == 'high':
                warnings.append(f"High holder risk: Top 10 own {rugcheck_data.get('top_10_percentage', 0):.0f}%")

        # FACTOR 5: MARKET CONDITIONS (10 points if available)
        if market_data:
            market_state = market_data.get('market_state', 'normal')
            sol_health = market_data.get('sol_health', {})

            if market_state == 'crash':
                market_score = 0
                warnings.append("MARKET CRASH - do not trade!")
                score = 0  # Force fail
                return self._build_result(score, breakdown, warnings, token_data, rugcheck_data, market_data)
            elif market_state == 'warning':
                market_score = 5
                warnings.append("Market warning - reduce position size")
            elif sol_health.get('is_healthy', True):
                market_score = 10
            else:
                market_score = 7
                warnings.append("SOL dumping - liquidity may dry up")

            score += market_score
            breakdown['market'] = market_score

        # Build final result
        return self._build_result(score, breakdown, warnings, token_data, rugcheck_data, market_data)

    def _build_result(
        self,
        score: int,
        breakdown: Dict,
        warnings: List,
        token_data: Dict,
        rugcheck_data: Optional[Dict],
        market_data: Optional[Dict]
    ) -> Dict:
        """Build comprehensive scoring result."""

        # Determine if pump.fun token
        token_address = token_data.get('token_address', '')
        is_pumpfun = token_address.endswith('pump')

        # Get position size recommendation
        position_size, confidence = self._get_position_recommendation(
            score,
            is_pumpfun,
            rugcheck_data,
            market_data
        )

        # Determine action
        if score < self.thresholds['min_score']:
            action = 'skip'
            reason = f"Score {score} below minimum {self.thresholds['min_score']}"
        elif score < self.thresholds['medium_score']:
            action = 'enter'
            confidence = 'low'
            reason = f"Low confidence entry: score {score}"
        elif score < self.thresholds['high_score']:
            action = 'enter'
            confidence = 'medium'
            reason = f"Medium confidence entry: score {score}"
        else:
            action = 'enter'
            confidence = 'high'
            reason = f"High confidence entry: score {score}"

        return {
            'score': score,
            'breakdown': breakdown,
            'action': action,
            'confidence': confidence,
            'position_size': position_size,
            'warnings': warnings,
            'is_pumpfun': is_pumpfun,
            'reason': reason,
            'timestamp': datetime.now().isoformat()
        }

    def _get_position_recommendation(
        self,
        score: int,
        is_pumpfun: bool,
        rugcheck_data: Optional[Dict],
        market_data: Optional[Dict]
    ) -> tuple[float, str]:
        """
        Get recommended position size based on score and risk factors.

        Returns:
            Tuple of (position_size_usd, confidence_level)
        """
        # Base position size from score
        if score >= 70:
            base_size = 40
            confidence = 'high'
        elif score >= 60:
            base_size = 30
            confidence = 'medium'
        elif score >= 50:
            base_size = 20
            confidence = 'low'
        else:
            base_size = 0
            confidence = 'none'

        if base_size == 0:
            return 0, confidence

        # Adjust for pump.fun
        if is_pumpfun:
            base_size *= 0.65  # 35% reduction for pump.fun risk

        # Adjust for holder risk
        if rugcheck_data:
            risk_level = rugcheck_data.get('risk_level', 'medium')
            if risk_level == 'high':
                base_size *= 0.7  # 30% reduction for high holder risk
            elif risk_level == 'critical':
                base_size = 0  # Don't enter

        # Adjust for market conditions
        if market_data:
            market_multiplier = market_data.get('position_size_multiplier', 1.0)
            base_size *= market_multiplier

        return round(base_size, 2), confidence
