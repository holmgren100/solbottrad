"""
Token Fallback List - Hardcoded Tokens for Offline/Emergency Use

When all APIs fail (network issues, rate limits, etc.), use this curated list
of popular and liquid Solana tokens as fallback.

These are well-known, safe tokens with high liquidity.
"""

# Popular Solana tokens (verified, high liquidity)
FALLBACK_TOKENS = [
    # Major tokens
    "So11111111111111111111111111111111111111112",  # Wrapped SOL
    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
    "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",  # USDT

    # Memecoins (popular)
    "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",  # BONK
    "ukHH6c7mMyiWCf1b9pnWe25TSpkDDt3H5pQZgZ74J82",   # BOME (Book of Meme)
    "EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm",  # WIF (dogwifhat)
    "5z3EqYQo9HiCEs3R84RCDMu2n7anpDMxRhdK8PSWmrRC",  # WEN
    "HeLp6NuQkmYB4pYWo2zYs22mESHXPQYzXbB8n4V98jwC",  # SILLY

    # DeFi tokens
    "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN",   # Jupiter
    "mSoLzYCxHdYgdzU16g5QSh3i5K3z3KZK7ytfqcJm7So",   # Marinade staked SOL
    "J1toso1uCk3RLmjorhTtrVwY9HJ7X8V9yYac6Y7kGCPn",  # Jito staked SOL
    "7dHbWXmci3dT8UFYWYZweBLXgycu7Y3iL6trKn1Y7ARj",  # stSOL

    # Gaming/NFT
    "ATLASXmbPQxBUYbxPsV97usA3fPQYEqzQBUHgiFCUsXx",  # ATLAS (Star Atlas)
    "poLisWXnNRwC6oBu1vHiuKQzFjGL4XDSu4g9qjz9qVk",   # POLIS (Star Atlas)

    # Others
    "SHDWyBxihqiCj6YekG2GUr7wqKLeLAMK1gHZck9pL6y",   # SHDW (Shadow)
    "orcaEKTdK7LKz57vaAYr9QeNsVEPfiu6QeMU1kektZE",   # ORCA
    "RLBxxFkseAZ4RgJH3Sqn8jXxhmGoz9jWxDNJMh8pL7a",   # Rollbit Coin
    "MEW1gQWJ3nEXg2qgERiKu7FAFj79PHvQVREQUzScPP5",   # MEW (cat in a dogs world)
]

def get_fallback_tokens(limit: int = 50) -> list:
    """
    Get fallback token list.

    Args:
        limit: Maximum tokens to return

    Returns:
        List of token addresses
    """
    return FALLBACK_TOKENS[:limit]


def is_fallback_token(token_address: str) -> bool:
    """
    Check if token is in fallback list.

    Args:
        token_address: Token address to check

    Returns:
        True if in fallback list
    """
    return token_address in FALLBACK_TOKENS
