"""
Volume breakout and smart money tracking analyzer.
Detects significant volume spikes that indicate smart money accumulation.
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict
from ..monitoring.logger import get_logger

logger = get_logger(__name__)


class VolumeAnalyzer:
    """Analyzes volume patterns to detect smart money and breakouts."""

    def __init__(self):
        """Initialize volume analyzer with historical tracking."""
        # Track volume history for each token: {token_address: [(timestamp, volume), ...]}
        self.volume_history: Dict[str, List[tuple]] = defaultdict(list)

        # Volume spike thresholds
        self.spike_threshold_multiplier = 3.0  # 3x average = spike
        self.strong_spike_multiplier = 5.0     # 5x average = strong spike
        self.extreme_spike_multiplier = 10.0   # 10x average = extreme spike

        # Historical window
        self.history_window_hours = 24
        self.max_history_points = 100  # Limit memory usage

    def record_volume(self, token_address: str, volume_24h: float):
        """
        Record volume observation for a token.

        Args:
            token_address: Token contract address
            volume_24h: 24-hour trading volume in USD
        """
        timestamp = datetime.now()

        # Add new observation
        self.volume_history[token_address].append((timestamp, volume_24h))

        # Clean old data (keep only recent history)
        self._cleanup_old_data(token_address)

    def _cleanup_old_data(self, token_address: str):
        """Remove old volume data beyond history window."""
        if token_address not in self.volume_history:
            return

        cutoff_time = datetime.now() - timedelta(hours=self.history_window_hours)

        # Keep only recent data
        self.volume_history[token_address] = [
            (ts, vol) for ts, vol in self.volume_history[token_address]
            if ts > cutoff_time
        ]

        # Limit total data points
        if len(self.volume_history[token_address]) > self.max_history_points:
            self.volume_history[token_address] = self.volume_history[token_address][-self.max_history_points:]

    def calculate_average_volume(self, token_address: str) -> float:
        """
        Calculate average volume over history window.

        Args:
            token_address: Token contract address

        Returns:
            Average volume in USD
        """
        if token_address not in self.volume_history or not self.volume_history[token_address]:
            return 0.0

        volumes = [vol for _, vol in self.volume_history[token_address]]
        return sum(volumes) / len(volumes) if volumes else 0.0

    def detect_volume_spike(self, token_address: str, current_volume: float) -> Dict:
        """
        Detect if current volume represents a significant spike.

        Args:
            token_address: Token contract address
            current_volume: Current 24h volume in USD

        Returns:
            Dictionary with spike analysis
        """
        # Record this volume
        self.record_volume(token_address, current_volume)

        # Calculate average
        avg_volume = self.calculate_average_volume(token_address)

        # Need at least 5 data points for reliable average
        min_data_points = 5
        if len(self.volume_history.get(token_address, [])) < min_data_points:
            return {
                'is_spike': False,
                'spike_level': 'insufficient_data',
                'multiplier': 0.0,
                'current_volume': current_volume,
                'average_volume': avg_volume,
                'data_points': len(self.volume_history.get(token_address, [])),
                'confidence': 0.0
            }

        # Calculate spike multiplier
        if avg_volume > 0:
            multiplier = current_volume / avg_volume
        else:
            multiplier = 0.0

        # Classify spike level
        is_spike = False
        spike_level = 'normal'
        confidence = 0.0

        if multiplier >= self.extreme_spike_multiplier:
            is_spike = True
            spike_level = 'extreme'  # 10x+ = extreme smart money
            confidence = 0.95
        elif multiplier >= self.strong_spike_multiplier:
            is_spike = True
            spike_level = 'strong'   # 5-10x = strong buying
            confidence = 0.85
        elif multiplier >= self.spike_threshold_multiplier:
            is_spike = True
            spike_level = 'moderate'  # 3-5x = moderate interest
            confidence = 0.70
        else:
            spike_level = 'normal'
            confidence = 0.50

        return {
            'is_spike': is_spike,
            'spike_level': spike_level,
            'multiplier': multiplier,
            'current_volume': current_volume,
            'average_volume': avg_volume,
            'data_points': len(self.volume_history[token_address]),
            'confidence': confidence,
            'timestamp': datetime.now().isoformat()
        }

    def analyze_volume_trend(self, token_address: str) -> Dict:
        """
        Analyze volume trend over time (increasing/decreasing).

        Args:
            token_address: Token contract address

        Returns:
            Trend analysis dictionary
        """
        if token_address not in self.volume_history or len(self.volume_history[token_address]) < 3:
            return {
                'trend': 'unknown',
                'trend_strength': 0.0,
                'recent_volumes': []
            }

        # Get recent volumes (last 10 observations)
        recent_data = self.volume_history[token_address][-10:]
        volumes = [vol for _, vol in recent_data]

        # Calculate trend using simple linear regression
        n = len(volumes)
        x_values = list(range(n))

        # Calculate slope
        x_mean = sum(x_values) / n
        y_mean = sum(volumes) / n

        numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, volumes))
        denominator = sum((x - x_mean) ** 2 for x in x_values)

        if denominator == 0:
            slope = 0
        else:
            slope = numerator / denominator

        # Classify trend
        if slope > y_mean * 0.1:  # Increasing by >10% per observation
            trend = 'increasing'
            trend_strength = min(abs(slope) / y_mean, 1.0)
        elif slope < -y_mean * 0.1:  # Decreasing by >10%
            trend = 'decreasing'
            trend_strength = min(abs(slope) / y_mean, 1.0)
        else:
            trend = 'stable'
            trend_strength = 0.5

        return {
            'trend': trend,
            'trend_strength': trend_strength,
            'recent_volumes': volumes,
            'slope': slope
        }

    def detect_smart_money_accumulation(
        self,
        token_address: str,
        current_volume: float,
        liquidity_usd: float
    ) -> Dict:
        """
        Detect smart money accumulation patterns.

        Args:
            token_address: Token contract address
            current_volume: Current 24h volume
            liquidity_usd: Current liquidity in USD

        Returns:
            Smart money analysis
        """
        # Get volume spike analysis
        spike_analysis = self.detect_volume_spike(token_address, current_volume)

        # Get trend analysis
        trend_analysis = self.analyze_volume_trend(token_address)

        # Calculate volume-to-liquidity ratio (high ratio = heavy trading)
        if liquidity_usd > 0:
            vol_liq_ratio = current_volume / liquidity_usd
        else:
            vol_liq_ratio = 0.0

        # Smart money indicators
        indicators = []
        smart_money_score = 0.0

        # Indicator 1: Volume spike (most important)
        if spike_analysis['is_spike']:
            if spike_analysis['spike_level'] == 'extreme':
                indicators.append('EXTREME_VOLUME_SPIKE')
                smart_money_score += 0.4
            elif spike_analysis['spike_level'] == 'strong':
                indicators.append('STRONG_VOLUME_SPIKE')
                smart_money_score += 0.3
            else:
                indicators.append('VOLUME_SPIKE')
                smart_money_score += 0.2

        # Indicator 2: Increasing volume trend
        if trend_analysis['trend'] == 'increasing':
            indicators.append('INCREASING_VOLUME_TREND')
            smart_money_score += 0.2 * trend_analysis['trend_strength']

        # Indicator 3: High volume-to-liquidity ratio (>2.0 = very active)
        if vol_liq_ratio > 5.0:
            indicators.append('VERY_HIGH_TRADING_ACTIVITY')
            smart_money_score += 0.2
        elif vol_liq_ratio > 2.0:
            indicators.append('HIGH_TRADING_ACTIVITY')
            smart_money_score += 0.1

        # Indicator 4: Sustained high volume (multiple spikes)
        if spike_analysis['data_points'] >= 10:
            recent_spikes = sum(
                1 for _, vol in self.volume_history[token_address][-10:]
                if vol > spike_analysis['average_volume'] * 2
            )
            if recent_spikes >= 5:
                indicators.append('SUSTAINED_HIGH_VOLUME')
                smart_money_score += 0.1

        # Classify overall signal
        if smart_money_score >= 0.7:
            signal = 'strong_accumulation'
            recommendation = 'BUY'
        elif smart_money_score >= 0.4:
            signal = 'moderate_accumulation'
            recommendation = 'WATCH'
        else:
            signal = 'normal'
            recommendation = 'NEUTRAL'

        return {
            'signal': signal,
            'recommendation': recommendation,
            'smart_money_score': smart_money_score,
            'indicators': indicators,
            'volume_spike': spike_analysis,
            'volume_trend': trend_analysis,
            'vol_liq_ratio': vol_liq_ratio,
            'timestamp': datetime.now().isoformat()
        }

    def get_statistics(self) -> Dict:
        """
        Get analyzer statistics.

        Returns:
            Statistics dictionary
        """
        return {
            'tracked_tokens': len(self.volume_history),
            'total_data_points': sum(len(v) for v in self.volume_history.values()),
            'avg_data_points_per_token': (
                sum(len(v) for v in self.volume_history.values()) / len(self.volume_history)
                if self.volume_history else 0
            )
        }
