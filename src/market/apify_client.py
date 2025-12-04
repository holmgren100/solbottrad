"""
Apify DexScreener scraper client.
Uses muhammetakkurtt/dexscreener-scraper for GAINERS discovery with sorting.
"""

from typing import Dict, List, Optional
from apify_client import ApifyClient
from ..monitoring.logger import get_logger

logger = get_logger(__name__)


class ApifyDexScreenerClient:
    """Client for Apify DexScreener scraper - Best for finding GAINERS."""

    # Cycling strategies for token discovery
    DISCOVERY_CYCLES = [
        'priceChange24h',   # Cycle 1: 24h GAINERS (biggest movers)
        'priceChange6h',    # Cycle 2: 6h GAINERS (recent movers)
        'priceChange1h',    # Cycle 3: 1h GAINERS (hot right now)
        'volume',           # Cycle 4: High volume (interest)
        'liquidity',        # Cycle 5: High liquidity (can sell)
    ]

    def __init__(self, api_token: str):
        """
        Initialize Apify DexScreener client.

        Args:
            api_token: Apify API token (get from https://console.apify.com/account/integrations)
        """
        self.api_token = api_token
        self.client = ApifyClient(api_token)
        self.actor_id = "muhammetakkurtt/dexscreener-scraper"  # Best scraper (>99% success)
        self.current_cycle = 0  # Track which discovery cycle we're on

    async def health_check(self) -> bool:
        """Check if Apify API is accessible."""
        try:
            # Try to get account info to verify token
            user = self.client.user().get()
            logger.info(f"Apify connected: {user.get('username', 'unknown')}")
            return True
        except Exception as e:
            logger.error(f"Apify health check failed: {e}")
            return False

    def get_tokens_by_cycle(self, limit: int = 30, min_volume: int = 50000,
                           min_liquidity: int = 10000, time_frame: str = "6h") -> List[Dict]:
        """
        Get tokens using CYCLING strategy (rotates sorting methods).

        Rotates through 5 discovery methods:
        1. priceChange24h - 24h GAINERS
        2. priceChange6h - 6h GAINERS
        3. priceChange1h - 1h GAINERS
        4. volume - High volume tokens
        5. liquidity - High liquidity tokens

        Args:
            limit: Maximum number of tokens to return
            min_volume: Minimum 24h volume in USD
            min_liquidity: Minimum liquidity in USD
            time_frame: Time frame for filtering (6h, 24h)

        Returns:
            List of token dictionaries
        """
        try:
            # Get current cycle
            sort_by = self.DISCOVERY_CYCLES[self.current_cycle]
            logger.info(f"Apify Cycle {self.current_cycle + 1}/5: Using '{sort_by}' discovery")

            # Configure scraper run
            run_input = {
                "chain": "solana",
                "sortBy": sort_by,
                "sortOrder": "desc",
                "timeFrame": time_frame,
                "minVolume": min_volume,
                "minLiquidity": min_liquidity,
                "limit": limit,
                "dexIdsSolana": ["raydium", "orca", "meteora", "jupiter"]
            }

            logger.info(f"Starting Apify scraper (this may take 10-30 seconds)...")

            # Run the actor and wait for it to finish
            run = self.client.actor(self.actor_id).call(run_input=run_input)

            # Get the run status
            if run.get('status') != 'SUCCEEDED':
                logger.warning(f"Apify run status: {run.get('status')}")
                return []

            # Fetch results from the dataset
            dataset_id = run.get('defaultDatasetId')
            if not dataset_id:
                logger.warning("No dataset ID returned from Apify run")
                return []

            # Get items from dataset
            dataset_client = self.client.dataset(dataset_id)
            items = list(dataset_client.iterate_items())

            # Parse and normalize token data
            token_list = []
            for item in items:
                # DexScreener data structure
                token_list.append({
                    'address': item.get('baseToken', {}).get('address'),
                    'symbol': item.get('baseToken', {}).get('symbol'),
                    'name': item.get('baseToken', {}).get('name'),
                    'price': float(item.get('priceUsd', 0)),
                    'liquidity': float(item.get('liquidity', {}).get('usd', 0)),
                    'volume_24h': float(item.get('volume', {}).get('h24', 0)),
                    'price_change_24h': float(item.get('priceChange', {}).get('h24', 0)),
                    'price_change_6h': float(item.get('priceChange', {}).get('h6', 0)),
                    'price_change_1h': float(item.get('priceChange', {}).get('h1', 0)),
                    'dex_id': item.get('dexId'),
                    'pair_address': item.get('pairAddress'),
                    'url': item.get('url'),
                })

            # Advance to next cycle for next scan
            self.current_cycle = (self.current_cycle + 1) % len(self.DISCOVERY_CYCLES)

            logger.info(f"✅ Apify retrieved {len(token_list)} tokens using '{sort_by}' (Next cycle: {self.DISCOVERY_CYCLES[self.current_cycle]})")
            return token_list

        except Exception as e:
            logger.error(f"Error fetching tokens from Apify DexScreener: {e}")
            return []

    def get_top_gainers_24h(self, limit: int = 30) -> List[Dict]:
        """
        Get top 24h GAINERS directly (no cycling).

        Args:
            limit: Maximum number of tokens to return

        Returns:
            List of top gainer token dictionaries
        """
        try:
            run_input = {
                "chain": "solana",
                "sortBy": "priceChange24h",
                "sortOrder": "desc",
                "timeFrame": "24h",
                "minVolume": 50000,
                "minLiquidity": 10000,
                "limit": limit,
                "dexIdsSolana": ["raydium", "orca", "meteora", "jupiter"]
            }

            logger.info(f"Fetching top 24h GAINERS from Apify...")
            run = self.client.actor(self.actor_id).call(run_input=run_input)

            if run.get('status') != 'SUCCEEDED':
                logger.warning(f"Apify run status: {run.get('status')}")
                return []

            dataset_id = run.get('defaultDatasetId')
            if not dataset_id:
                return []

            dataset_client = self.client.dataset(dataset_id)
            items = list(dataset_client.iterate_items())

            token_list = []
            for item in items:
                token_list.append({
                    'address': item.get('baseToken', {}).get('address'),
                    'symbol': item.get('baseToken', {}).get('symbol'),
                    'name': item.get('baseToken', {}).get('name'),
                    'price': float(item.get('priceUsd', 0)),
                    'liquidity': float(item.get('liquidity', {}).get('usd', 0)),
                    'volume_24h': float(item.get('volume', {}).get('h24', 0)),
                    'price_change_24h': float(item.get('priceChange', {}).get('h24', 0)),
                    'price_change_6h': float(item.get('priceChange', {}).get('h6', 0)),
                    'price_change_1h': float(item.get('priceChange', {}).get('h1', 0)),
                    'dex_id': item.get('dexId'),
                })

            logger.info(f"✅ Retrieved {len(token_list)} top 24h GAINERS from Apify")
            return token_list

        except Exception as e:
            logger.error(f"Error fetching top gainers from Apify: {e}")
            return []

    def close(self):
        """Close the Apify client (no-op, but for consistency with other clients)."""
        pass
