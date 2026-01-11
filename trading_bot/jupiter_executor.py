"""
Jupiter Swap Executor with Jito Bundle Support
Handles automated trade execution on Solana using Jupiter aggregator.
"""

import asyncio
import aiohttp
import logging
from typing import Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class JupiterSwapExecutor:
    """
    Executes swaps using Jupiter's aggregator API with optional Jito MEV protection.
    """

    def __init__(
        self,
        rpc_url: str,
        use_jito: bool = True,
        paper_trading: bool = True
    ):
        """
        Initialize Jupiter executor.

        Args:
            rpc_url: Solana RPC endpoint URL
            use_jito: Whether to use Jito bundles for MEV protection
            paper_trading: If True, simulates trades without execution
        """
        self.jupiter_api = "https://quote-api.jup.ag/v6"
        self.rpc_url = rpc_url
        self.use_jito = use_jito
        self.paper_trading = paper_trading

        # Jito bundle endpoints
        self.jito_block_engine = "https://mainnet.block-engine.jito.wtf/api/v1"
        self.jito_tip_accounts = [
            "96gYZGLnJYVFmbjzopPSU6QiEV5fGqZNyN9nmNhvrZU5",
            "HFqU5x63VTqvQss8hp11i4wVV8bD44PvwucfZ2bU7gRe",
            "Cw8CFyM9FkoMi7K7Crf6HNQqf4uEMzpKw6QNghXLvLkY",
            "ADaUMid9yfUytqMBgopwjb2DTLSokTSzL1zt6iGPaS49",
            "DfXygSm4jCyNCybVYYK6DwvWqjKee8pbDmJGcLWNDXjh",
            "ADuUkR4vqLUMWXxW9gh6D6L8pMSawimctcNZ5pGwDcEt",
            "DttWaMuVvTiduZRnguLF7jNxTgiMBZ1hyAumKUiL2KRL",
            "3AVi9Tg9Uo68tJfuvoKvqKNWKkC5wPdSSdeBnizKZ6jT"
        ]

        logger.info(
            f"JupiterSwapExecutor initialized - "
            f"Paper Trading: {paper_trading}, "
            f"Jito: {use_jito}"
        )

    async def get_quote(
        self,
        input_mint: str,
        output_mint: str,
        amount: int,
        slippage_bps: int = 500,  # 5% slippage = 500 basis points
        priority_fee_lamports: int = 12000  # Gemini FAS 4.3: 0.012 SOL = 12,000 lamports
    ) -> Optional[Dict]:
        """
        Get a swap quote from Jupiter.

        Args:
            input_mint: Input token mint address
            output_mint: Output token mint address
            amount: Amount in smallest unit (lamports for SOL)
            slippage_bps: Slippage tolerance in basis points
            priority_fee_lamports: Priority fee for faster execution (default 12,000 = 0.012 SOL)

        Returns:
            Quote data or None if failed
        """
        try:
            params = {
                'inputMint': input_mint,
                'outputMint': output_mint,
                'amount': str(amount),
                'slippageBps': slippage_bps,
                'onlyDirectRoutes': 'false',
                'asLegacyTransaction': 'false',
                # Gemini FAS 4.3: Higher priority fee for nuclear stops to reduce slippage
                'prioritizationFeeLamports': str(priority_fee_lamports)
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.jupiter_api}/quote",
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.info(
                            f"Jupiter quote: {amount} {input_mint[:8]} → "
                            f"{data.get('outAmount', 0)} {output_mint[:8]}"
                        )
                        return data
                    else:
                        error_text = await response.text()
                        logger.error(f"Jupiter quote failed: {response.status} - {error_text}")
                        return None

        except Exception as e:
            logger.error(f"Error getting Jupiter quote: {e}")
            return None

    async def execute_swap(
        self,
        input_mint: str,
        output_mint: str,
        amount_in: float,
        slippage_percent: float = 5.0,
        use_jito_bundle: bool = None
    ) -> Dict:
        """
        Execute a swap (or simulate in paper trading mode).

        Args:
            input_mint: Input token mint address
            output_mint: Output token mint address
            amount_in: Amount to swap in token units
            slippage_percent: Slippage tolerance percentage
            use_jito_bundle: Override default Jito setting

        Returns:
            Execution result dictionary
        """
        use_jito = use_jito_bundle if use_jito_bundle is not None else self.use_jito

        if self.paper_trading:
            return await self._simulate_swap(
                input_mint, output_mint, amount_in, slippage_percent, use_jito
            )
        else:
            return await self._execute_real_swap(
                input_mint, output_mint, amount_in, slippage_percent, use_jito
            )

    async def _simulate_swap(
        self,
        input_mint: str,
        output_mint: str,
        amount_in: float,
        slippage_percent: float,
        use_jito: bool
    ) -> Dict:
        """
        Simulate a swap for paper trading (no actual execution).

        Returns realistic fee estimates and execution details.
        """
        # Convert amount to lamports/smallest unit
        amount_lamports = int(amount_in * 1e9)  # Assuming SOL, adjust for other tokens

        # Get quote to calculate realistic output
        quote = await self.get_quote(
            input_mint,
            output_mint,
            amount_lamports,
            int(slippage_percent * 100)  # Convert to basis points
        )

        # Calculate fees
        fees = self._calculate_fees(amount_in, use_jito)

        if quote:
            output_amount = int(quote.get('outAmount', 0)) / 1e9  # Convert back to token units
            price_impact = float(quote.get('priceImpactPct', 0))

            logger.info(
                f"📄 [PAPER] Simulated swap: {amount_in:.4f} → {output_amount:.4f} "
                f"(Impact: {price_impact:.2f}%, Fees: ${fees['total_usd']:.4f})"
            )

            return {
                'status': 'simulated',
                'success': True,
                'input_amount': amount_in,
                'output_amount': output_amount,
                'price_impact_pct': price_impact,
                'fees': fees,
                'route': quote.get('routePlan', []),
                'jito_used': use_jito,
                'timestamp': datetime.now().isoformat()
            }
        else:
            logger.warning(f"📄 [PAPER] Failed to get quote for simulation")
            return {
                'status': 'simulation_failed',
                'success': False,
                'error': 'Could not get quote from Jupiter',
                'timestamp': datetime.now().isoformat()
            }

    async def _execute_real_swap(
        self,
        input_mint: str,
        output_mint: str,
        amount_in: float,
        slippage_percent: float,
        use_jito: bool
    ) -> Dict:
        """
        Execute a real swap on-chain.

        NOTE: This requires wallet private key and will be implemented
        when switching from paper trading to live trading.
        """
        logger.error("❌ Real swap execution not yet implemented - use paper trading mode")
        return {
            'status': 'not_implemented',
            'success': False,
            'error': 'Live trading not yet enabled',
            'message': 'Run bot in paper trading mode or implement wallet integration',
            'timestamp': datetime.now().isoformat()
        }

    def _calculate_fees(self, amount_usd: float, use_jito: bool) -> Dict:
        """
        Calculate estimated fees for a swap.

        Args:
            amount_usd: Trade amount in USD
            use_jito: Whether Jito bundle is used

        Returns:
            Fee breakdown dictionary
        """
        # Jupiter/DEX fee (typically 0.25%)
        dex_fee_pct = 0.0025
        dex_fee_usd = amount_usd * dex_fee_pct

        # Network base fee
        network_fee_usd = 0.003  # ~5000 lamports

        if use_jito:
            # Jito tip (competitive: 10,000 lamports)
            jito_tip_usd = 0.002  # ~10,000 lamports at $200/SOL
            priority_fee_usd = 0.0  # No separate priority fee needed with Jito

            total_usd = dex_fee_usd + network_fee_usd + jito_tip_usd
        else:
            # Standard priority fee
            priority_fee_usd = 0.50  # Higher without Jito
            jito_tip_usd = 0.0

            total_usd = dex_fee_usd + network_fee_usd + priority_fee_usd

        return {
            'dex_fee_usd': round(dex_fee_usd, 4),
            'network_fee_usd': round(network_fee_usd, 4),
            'priority_fee_usd': round(priority_fee_usd, 4),
            'jito_tip_usd': round(jito_tip_usd, 4),
            'total_usd': round(total_usd, 4),
            'total_pct': round((total_usd / amount_usd) * 100, 3) if amount_usd > 0 else 0
        }

    async def buy_token(
        self,
        token_mint: str,
        amount_sol: float,
        slippage_percent: float = 5.0
    ) -> Dict:
        """
        Buy a token with SOL.

        Args:
            token_mint: Token to buy (mint address)
            amount_sol: Amount of SOL to spend
            slippage_percent: Slippage tolerance

        Returns:
            Execution result
        """
        sol_mint = "So11111111111111111111111111111111111111112"  # Wrapped SOL

        logger.info(f"🟢 BUY: {amount_sol} SOL → {token_mint[:8]}...")

        result = await self.execute_swap(
            input_mint=sol_mint,
            output_mint=token_mint,
            amount_in=amount_sol,
            slippage_percent=slippage_percent
        )

        if result.get('success'):
            logger.info(
                f"✅ Buy executed: {amount_sol} SOL → {result.get('output_amount', 0):.4f} tokens "
                f"(Fees: ${result['fees']['total_usd']:.4f})"
            )
        else:
            logger.error(f"❌ Buy failed: {result.get('error', 'Unknown error')}")

        return result

    async def sell_token(
        self,
        token_mint: str,
        amount_tokens: float,
        slippage_percent: float = 5.0
    ) -> Dict:
        """
        Sell a token for SOL.

        Args:
            token_mint: Token to sell (mint address)
            amount_tokens: Amount of tokens to sell
            slippage_percent: Slippage tolerance

        Returns:
            Execution result
        """
        sol_mint = "So11111111111111111111111111111111111111112"  # Wrapped SOL

        logger.info(f"🔴 SELL: {amount_tokens:.4f} {token_mint[:8]}... → SOL")

        result = await self.execute_swap(
            input_mint=token_mint,
            output_mint=sol_mint,
            amount_in=amount_tokens,
            slippage_percent=slippage_percent
        )

        if result.get('success'):
            logger.info(
                f"✅ Sell executed: {amount_tokens:.4f} tokens → {result.get('output_amount', 0):.6f} SOL "
                f"(Fees: ${result['fees']['total_usd']:.4f})"
            )
        else:
            logger.error(f"❌ Sell failed: {result.get('error', 'Unknown error')}")

        return result
