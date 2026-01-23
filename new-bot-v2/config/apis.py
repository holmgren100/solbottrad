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
# BIRDEYE API (FREE TIER)
# ============================================================================
# Use: Token discovery (trending), prices, OHLCV, security checks
# Limit: 15 RPS = 900 requests/min (FREE tier), 30K compute units/month
# Cost: FREE
# Docs: https://docs.birdeye.so/

BIRDEYE_API_KEY = os.getenv("BIRDEYE_API_KEY", "")
BIRDEYE_BASE_URL = "https://public-api.birdeye.so"

# Birdeye Endpoints
BIRDEYE_ENDPOINTS = {
    "token_list": f"{BIRDEYE_BASE_URL}/defi/tokenlist",
    "trending": f"{BIRDEYE_BASE_URL}/defi/v3/token/trending",  # Top trending tokens
    "token_security": f"{BIRDEYE_BASE_URL}/defi/token_security",
    "token_overview": f"{BIRDEYE_BASE_URL}/defi/token_overview",
    "price": f"{BIRDEYE_BASE_URL}/defi/price",
    "ohlcv": f"{BIRDEYE_BASE_URL}/defi/ohlcv",
}

# ============================================================================
# SOLSCAN API (FREE TIER)
# ============================================================================
# Use: Token metadata, holder analysis, top holders
# Limit: Generous free tier
# Cost: FREE
# Docs: https://docs.solscan.io/

SOLSCAN_API_KEY = os.getenv("SOLSCAN_API_KEY", "")
SOLSCAN_BASE_URL = "https://pro-api.solscan.io/v1.0"

# SolScan Endpoints
SOLSCAN_ENDPOINTS = {
    "token_meta": f"{SOLSCAN_BASE_URL}/token/meta",
    "token_holders": f"{SOLSCAN_BASE_URL}/token/holders",
    "market": f"{SOLSCAN_BASE_URL}/market/token",
}

# ============================================================================
# SOLSNIFFER API
# ============================================================================
# Use: Token security checks, rug detection
# Limit: Free tier available
# Docs: https://solsniffer.com/

SOLSNIFFER_API_KEY = os.getenv("SOLSNIFFER_API_KEY", "")
SOLSNIFFER_BASE_URL = "https://api.solsniffer.com"

SOLSNIFFER_ENDPOINTS = {
    "scan": f"{SOLSNIFFER_BASE_URL}/v1/scan",
    "quick_scan": f"{SOLSNIFFER_BASE_URL}/v1/quick-scan",
}

# ============================================================================
# JUPITER API (SWAP & PRICE ONLY)
# ============================================================================
# Use: Swap quotes and prices (token discovery requires paid plan)
# Limit: Free tier available (higher limits with API key)
# Cost: FREE (optional Pro plan for higher limits)
# Docs: https://dev.jup.ag/docs/api
# IMPORTANT: Price API V3 (not v4!), lite-api deprecated Jan 31, 2026

JUPITER_API_KEY = os.getenv("JUPITER_API_KEY", "")
JUPITER_BASE_URL = "https://quote-api.jup.ag/v6"
JUPITER_PRICE_API_V3 = "https://api.jup.ag/price/v3"

# Jupiter Endpoints (swap & price only)
JUPITER_ENDPOINTS = {
    "quote": f"{JUPITER_BASE_URL}/quote",
    "swap": f"{JUPITER_BASE_URL}/swap",
    "swap_instructions": f"{JUPITER_BASE_URL}/swap-instructions",
    "price": JUPITER_PRICE_API_V3,  # V3, not V4!
    "search": "https://api.jup.ag/tokens/v2/search",  # Token search (requires API key)
    "verified": "https://api.jup.ag/tokens/v2/verified",  # Verified tokens (requires API key)
    "trending": "https://api.jup.ag/tokens/v2/top-trending/5m"  # Trending tokens (requires API key)
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
        "birdeye": {
            "configured": bool(BIRDEYE_API_KEY),
            "endpoint": BIRDEYE_BASE_URL if BIRDEYE_API_KEY else "NOT CONFIGURED",
            "cost": "FREE (100 req/min)"
        },
        "solscan": {
            "configured": bool(SOLSCAN_API_KEY),
            "endpoint": SOLSCAN_BASE_URL if SOLSCAN_API_KEY else "NOT CONFIGURED",
            "cost": "FREE (Generous tier)"
        },
        "solsniffer": {
            "configured": bool(SOLSNIFFER_API_KEY),
            "endpoint": SOLSNIFFER_BASE_URL if SOLSNIFFER_API_KEY else "NOT CONFIGURED",
            "cost": "FREE (Limited)"
        },
        "jupiter": {
            "configured": True,  # No API key required for prices/swaps
            "endpoint": JUPITER_BASE_URL,
            "cost": "FREE (Prices & swaps only)"
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
