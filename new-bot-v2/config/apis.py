"""
Fearless Momentum Runner v2.0 - API Configurations

FREE APIs ONLY - No premium services!
Cost: $0/month for all APIs (within free tier limits)
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ============================================================================
# ALCHEMY API (FREE TIER)
# ============================================================================
# Use: Token metadata, LP burned check, mint authority check
# Limit: 300M compute units/month (plenty for our needs)
# Cost: FREE
# Docs: https://docs.alchemy.com/reference/solana-api-quickstart

ALCHEMY_API_KEY = os.getenv("ALCHEMY_API_KEY", "")
ALCHEMY_BASE_URL = "https://solana-mainnet.g.alchemy.com/v2"
ALCHEMY_ENDPOINT = f"{ALCHEMY_BASE_URL}/{ALCHEMY_API_KEY}"

# Alchemy RPC Methods
ALCHEMY_METHODS = {
    "get_account_info": "getAccountInfo",
    "get_token_supply": "getTokenSupply",
    "get_token_accounts": "getTokenAccountsByOwner",
}

# ============================================================================
# JUPITER API (FREE)
# ============================================================================
# Use: Token discovery, prices, market data, swaps
# Limit: Unlimited (FREE!)
# Cost: FREE
# Docs: https://station.jup.ag/docs/apis/swap-api

JUPITER_BASE_URL = "https://quote-api.jup.ag/v6"
JUPITER_PRICE_API = "https://price.jup.ag/v4"

# Jupiter Endpoints
JUPITER_ENDPOINTS = {
    "quote": f"{JUPITER_BASE_URL}/quote",
    "swap": f"{JUPITER_BASE_URL}/swap",
    "swap_instructions": f"{JUPITER_BASE_URL}/swap-instructions",
    "price": f"{JUPITER_PRICE_API}/price",
    "tokens": "https://token.jup.ag/all",  # All tokens list
    "strict_tokens": "https://token.jup.ag/strict",  # Verified tokens only
}

# ============================================================================
# DEXSCREENER API (FREE)
# ============================================================================
# Use: Market data, price candles, volume, liquidity, buy/sell orders
# Limit: Rate limited (respect limits - no specific number published)
# Cost: FREE
# Docs: https://docs.dexscreener.com/api/reference

DEXSCREENER_BASE_URL = "https://api.dexscreener.com/latest"

# DexScreener Endpoints
DEXSCREENER_ENDPOINTS = {
    "base": DEXSCREENER_BASE_URL,  # Base URL for building endpoints
    "token_profiles": f"{DEXSCREENER_BASE_URL}/dex/tokens",  # /tokens/{addresses}
    "pair_by_address": f"{DEXSCREENER_BASE_URL}/dex/pairs/solana",  # /pairs/solana/{address}
    "search": f"{DEXSCREENER_BASE_URL}/dex/search",  # /search/?q={query}
    "token_pairs": f"{DEXSCREENER_BASE_URL}/dex/tokens",  # Get all pairs for token
    "latest_pairs": f"{DEXSCREENER_BASE_URL}/dex/pairs/solana",  # Latest Solana pairs
}

# Rate limit handling
DEXSCREENER_RATE_LIMIT_DELAY = 2  # Seconds between requests (conservative)
DEXSCREENER_BATCH_SIZE = 10       # Max tokens per batch request

# ============================================================================
# SOLANA RPC (FREE - Public RPC)
# ============================================================================
# Use: Backup for basic on-chain data if Alchemy quota exceeded
# Limit: Public RPC has rate limits
# Cost: FREE
# Note: Use Alchemy primarily, this is backup

SOLANA_PUBLIC_RPC = "https://api.mainnet-beta.solana.com"

# ============================================================================
# API REQUEST CONFIGURATION
# ============================================================================

# Timeout settings (prevent hanging)
API_TIMEOUT_SECONDS = 10
API_CONNECT_TIMEOUT = 5

# Retry settings (handle temporary failures)
API_MAX_RETRIES = 3
API_RETRY_DELAY = 2  # Seconds between retries
API_RETRY_BACKOFF = 2  # Exponential backoff multiplier

# Headers
DEFAULT_HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": "FearlessMomentumRunner/2.0"
}

# ============================================================================
# API STATUS CHECKING
# ============================================================================

def check_api_keys():
    """Check if required API keys are configured."""
    missing_keys = []

    if not ALCHEMY_API_KEY:
        missing_keys.append("ALCHEMY_API_KEY")

    if missing_keys:
        raise ValueError(
            f"Missing required API keys: {', '.join(missing_keys)}\n"
            f"Please set them in your .env file"
        )

    return True


def get_api_summary():
    """Get summary of API configuration."""
    return {
        "alchemy": {
            "configured": bool(ALCHEMY_API_KEY),
            "endpoint": ALCHEMY_ENDPOINT if ALCHEMY_API_KEY else "NOT CONFIGURED",
            "cost": "FREE (300M compute units/month)"
        },
        "jupiter": {
            "configured": True,  # No API key required
            "endpoint": JUPITER_BASE_URL,
            "cost": "FREE (Unlimited)"
        },
        "dexscreener": {
            "configured": True,  # No API key required
            "endpoint": DEXSCREENER_BASE_URL,
            "cost": "FREE (Rate limited)"
        },
        "total_cost": "$0/month (all free tier)"
    }

# ============================================================================
# NOTES
# ============================================================================

"""
API USAGE NOTES:

1. ALCHEMY (FREE TIER):
   - 300M compute units/month
   - Use for: LP burned check, mint authority check, token metadata
   - Each call ~= 1-10 compute units
   - We can make 30M+ calls/month easily

2. JUPITER (FREE):
   - No rate limits
   - Use for: Token discovery, prices, swap quotes
   - Most reliable for price data

3. DEXSCREENER (FREE):
   - Rate limited but no hard cap
   - Use for: Market data, candles, volume, buy/sell pressure
   - Be conservative with requests (2 sec delay)
   - Batch requests when possible

COST ANALYSIS:
- Alchemy: $0 (free tier)
- Jupiter: $0 (always free)
- DexScreener: $0 (free tier)
- Total: $0/month

BACKUP PLAN:
- If Alchemy quota exceeded: Use public Solana RPC
- If DexScreener rate limited: Reduce scan frequency
- If Jupiter down: Use DexScreener prices

NO PREMIUM SERVICES:
- NO GMGN API (costs money)
- NO RugCheck API (costs money)
- NO SolSniffer API (costs money)
- Add these later when bot is profitable!
"""
