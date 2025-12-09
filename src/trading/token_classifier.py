#!/usr/bin/env python3
"""
Token Type Classifier - Identify meme vs blue chip vs alt vs shit
"""

from typing import Dict, Literal

TokenType = Literal["meme", "blue_chip", "alt_coin", "shit_coin"]


class TokenClassifier:
    """Classify tokens by type to apply appropriate strategies."""

    # Known blue chip addresses (skip these)
    BLUE_CHIPS = {
        "So11111111111111111111111111111111111111112",  # SOL
        "7vfCXTUXGyQdSz6HEo3gaPqWcP6JbhFvjg3wB8KgNq6V",  # WETH
        "3NZ9JMVBmGAqocybic2c7LQCJScmgsAZ6vQqTDzcqmJh",  # WBTC
        "J1toso1uCk3RLmjorhTtrVwY9HJ7X8V9yYac6Y7kGCPn",  # JitoSOL
        "jupSoLaHXQiZZTSfEWMTRRgpnyFm8f6sZdosWBjx93v",   # JupSOL
        "mSoLzYCxHdYgdzU16g5QSh3i5K3z3KZK7ytfqcJm7So",   # mSOL
        "bSo13r4TkiE4KumL71LsHTPpL2euBYLFx6h9HP3piy1",   # bSOL
    }

    # Meme token indicators
    MEME_KEYWORDS = [
        "pump", "moon", "doge", "pepe", "shib", "inu", "wojak",
        "chad", "giga", "based", "frog", "cat", "dog", "elon",
        "safe", "baby", "mini", "floki", "shiba", "bonk", "samo"
    ]

    @classmethod
    def classify_token(cls,
                      address: str,
                      symbol: str,
                      name: str,
                      price: float,
                      liquidity: float,
                      volume_24h: float,
                      market_cap: float = 0) -> Dict:
        """
        Classify token and return type + strategy params.

        Returns:
            {
                "type": "meme" | "blue_chip" | "alt_coin" | "shit_coin",
                "should_trade": bool,
                "strategy": {
                    "trailing_stop_percent": float,
                    "max_hold_minutes": int,
                    "position_multiplier": float
                },
                "reason": str
            }
        """

        # Check if blue chip (skip)
        if address in cls.BLUE_CHIPS:
            return {
                "type": "blue_chip",
                "should_trade": False,
                "strategy": None,
                "reason": f"Blue chip token ({symbol}) - not suitable for meme pump strategy"
            }

        # Check price-based classification
        if price > 100:
            return {
                "type": "blue_chip",
                "should_trade": False,
                "strategy": None,
                "reason": f"High price (${price:.2f}) suggests blue chip - skipping"
            }

        # Check for shit coin (very low liquidity)
        if liquidity < 10000:
            return {
                "type": "shit_coin",
                "should_trade": False,
                "strategy": None,
                "reason": f"Very low liquidity (${liquidity:.0f}) - high rug risk"
            }

        # Check for meme indicators
        symbol_lower = symbol.lower()
        name_lower = name.lower()

        is_meme = any(keyword in symbol_lower or keyword in name_lower
                     for keyword in cls.MEME_KEYWORDS)

        # Price-based meme detection
        is_cheap = 0.00001 <= price <= 10  # Typical meme price range

        if is_meme or (is_cheap and volume_24h > 100000):
            # MEME TOKEN - This is what we want!
            return {
                "type": "meme",
                "should_trade": True,
                "strategy": {
                    "trailing_stop_percent": 15.0,  # Aggressive
                    "max_hold_minutes": 60,          # 1 hour max
                    "position_multiplier": 1.0       # Full position
                },
                "reason": f"Meme token detected - price ${price:.6f}, suitable for pump strategy"
            }

        # Alt coin (mid-range)
        if 1 <= price <= 100 and liquidity > 50000:
            return {
                "type": "alt_coin",
                "should_trade": True,
                "strategy": {
                    "trailing_stop_percent": 10.0,  # Moderate
                    "max_hold_minutes": 120,         # 2 hours max
                    "position_multiplier": 0.5       # Half position (riskier)
                },
                "reason": f"Alt coin - moderate risk, reduced position size"
            }

        # Default: treat as meme if has volume
        if volume_24h > 50000:
            return {
                "type": "meme",
                "should_trade": True,
                "strategy": {
                    "trailing_stop_percent": 15.0,
                    "max_hold_minutes": 60,
                    "position_multiplier": 1.0
                },
                "reason": f"High volume token - treating as meme candidate"
            }

        # Unknown/suspicious
        return {
            "type": "shit_coin",
            "should_trade": False,
            "strategy": None,
            "reason": "Doesn't match any known pattern - skipping for safety"
        }


# Example usage
if __name__ == "__main__":
    classifier = TokenClassifier()

    # Test cases
    tests = [
        {
            "address": "So11111111111111111111111111111111111111112",
            "symbol": "SOL",
            "name": "Solana",
            "price": 138.50,
            "liquidity": 2000000,
            "volume_24h": 5000000
        },
        {
            "address": "pump123456789",
            "symbol": "PEPE",
            "name": "Pepe Coin",
            "price": 0.00015,
            "liquidity": 500000,
            "volume_24h": 2000000
        },
        {
            "address": "3NZ9JMVBmGAqocybic2c7LQCJScmgsAZ6vQqTDzcqmJh",
            "symbol": "WBTC",
            "name": "Wrapped Bitcoin",
            "price": 90000,
            "liquidity": 2000000,
            "volume_24h": 4000000
        }
    ]

    print("Token Classification Tests:")
    print("=" * 60)

    for test in tests:
        result = classifier.classify_token(**test)
        print(f"\n{test['symbol']} ({test['name']}):")
        print(f"  Type: {result['type']}")
        print(f"  Trade: {result['should_trade']}")
        print(f"  Reason: {result['reason']}")
        if result['strategy']:
            print(f"  Strategy: {result['strategy']}")
