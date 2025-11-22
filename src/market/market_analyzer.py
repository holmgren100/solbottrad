import logging
from typing import Dict, Optional
from dataclasses import dataclass
import numpy as np

@dataclass
class MarketSignal:
    signal_type: str  # 'buy', 'sell', 'hold'
    confidence: float
    price: float
    volume_24h: float
    price_change_24h: float
    liquidity: float
    market_cap: Optional[float]

class MarketAnalyzer:
    """Analyze market data and generate trading signals"""

    def __init__(self):
        self.logger = logging.getLogger('trading_bot.market_analyzer')

    def analyze(self, token_data: Dict) -> MarketSignal:
        """Analyze token data and generate signal"""
        try:
            # Extract market data
            price = float(token_data.get('priceUsd', 0))
            volume_24h = float(token_data.get('volume', {}).get('h24', 0))
            price_change_24h = float(token_data.get('priceChange', {}).get('h24', 0))
            liquidity_usd = float(token_data.get('liquidity', {}).get('usd', 0))
            market_cap = token_data.get('fdv')
            if market_cap:
                market_cap = float(market_cap)

            # Calculate technical indicators
            signal_type = 'hold'
            confidence = 0.5

            # Bullish signals
            bullish_score = 0.0

            # Price momentum (positive price change)
            if price_change_24h > 5:
                bullish_score += 0.3
            elif price_change_24h > 0:
                bullish_score += 0.1

            # Volume (high volume relative to liquidity)
            if liquidity_usd > 0:
                volume_to_liquidity = volume_24h / liquidity_usd
                if volume_to_liquidity > 2:  # High volume
                    bullish_score += 0.2
                elif volume_to_liquidity > 0.5:
                    bullish_score += 0.1

            # Liquidity (sufficient liquidity)
            if liquidity_usd > 50000:
                bullish_score += 0.2
            elif liquidity_usd > 10000:
                bullish_score += 0.1

            # Volume trend (high 24h volume)
            if volume_24h > 100000:
                bullish_score += 0.2
            elif volume_24h > 10000:
                bullish_score += 0.1

            # Determine signal
            if bullish_score >= 0.6:
                signal_type = 'buy'
                confidence = min(bullish_score, 0.95)
            elif bullish_score <= 0.3:
                signal_type = 'sell'
                confidence = min(1 - bullish_score, 0.95)
            else:
                signal_type = 'hold'
                confidence = 0.5

            return MarketSignal(
                signal_type=signal_type,
                confidence=confidence,
                price=price,
                volume_24h=volume_24h,
                price_change_24h=price_change_24h,
                liquidity=liquidity_usd,
                market_cap=market_cap
            )

        except Exception as e:
            self.logger.error(f"Error analyzing market data: {e}")
            # Return neutral signal on error
            return MarketSignal(
                signal_type='hold',
                confidence=0.0,
                price=0.0,
                volume_24h=0.0,
                price_change_24h=0.0,
                liquidity=0.0,
                market_cap=None
            )

    def calculate_rsi(self, prices: list, period: int = 14) -> float:
        """Calculate Relative Strength Index"""
        if len(prices) < period + 1:
            return 50.0  # Neutral RSI

        deltas = np.diff(prices)
        gains = deltas.copy()
        losses = deltas.copy()
        gains[gains < 0] = 0
        losses[losses > 0] = 0
        losses = abs(losses)

        avg_gain = np.mean(gains[:period])
        avg_loss = np.mean(losses[:period])

        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return rsi
