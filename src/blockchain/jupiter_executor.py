"""
Jupiter Swap Executor with Jito Bundle Support
Handles automated trade execution on Solana using Jupiter aggregator.
"""

import asyncio
import aiohttp
import base64
import random
from typing import Dict, Optional
from datetime import datetime
from solana.rpc.async_api import AsyncClient
from solders.transaction import VersionedTransaction
from ..monitoring.logger import get_logger

logger = get_logger(__name__)


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
        self.jupiter_api = "https://lite-api.jup.ag/swap/v1"
        self.rpc_url = rpc_url
        self.use_jito = use_jito
        self.paper_trading = paper_trading
        self.wallet = None  # Wallet manager for signing transactions

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

    def set_wallet(self, wallet_manager):
        """
        Set the wallet manager for signing transactions.

        Args:
            wallet_manager: WalletManager instance
        """
        self.wallet = wallet_manager
        logger.info(f"Wallet connected: {wallet_manager.get_public_key()[:8]}...")

    async def get_quote(
        self,
        input_mint: str,
        output_mint: str,
        amount: int,
        slippage_bps: int = 500  # 5% slippage = 500 basis points
    ) -> Optional[Dict]:
        """
        Get a swap quote from Jupiter.

        Args:
            input_mint: Input token mint address
            output_mint: Output token mint address
            amount: Amount in smallest unit (lamports for SOL)
            slippage_bps: Slippage tolerance in basis points

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
                'asLegacyTransaction': 'false'
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

        Steps:
        1. Get quote from Jupiter
        2. Get swap transaction from Jupiter
        3. Sign transaction with wallet
        4. Send transaction (via Jito bundle or standard RPC)
        5. Wait for confirmation
        6. Return execution result
        """
        try:
            # Validate wallet is set
            if not self.wallet or not self.wallet.is_loaded():
                logger.error("❌ Wallet not set or not loaded")
                return {
                    'status': 'error',
                    'success': False,
                    'error': 'Wallet not configured',
                    'timestamp': datetime.now().isoformat()
                }

            # Step 1: Get quote from Jupiter
            logger.info(f"🔍 Getting Jupiter quote for {amount_in} {input_mint[:8]}...")
            amount_lamports = int(amount_in * 1e9)  # Convert to smallest unit
            slippage_bps = int(slippage_percent * 100)  # Convert to basis points

            quote = await self.get_quote(input_mint, output_mint, amount_lamports, slippage_bps)
            if not quote:
                logger.error("❌ Failed to get quote from Jupiter")
                return {
                    'status': 'error',
                    'success': False,
                    'error': 'Failed to get Jupiter quote',
                    'timestamp': datetime.now().isoformat()
                }

            # Step 2: Get swap transaction from Jupiter
            logger.info("🔨 Building swap transaction...")
            swap_tx_data = await self._get_swap_transaction(quote)
            if not swap_tx_data:
                logger.error("❌ Failed to get swap transaction")
                return {
                    'status': 'error',
                    'success': False,
                    'error': 'Failed to build swap transaction',
                    'timestamp': datetime.now().isoformat()
                }

            # Step 3: Deserialize and sign transaction
            logger.info("✍️  Signing transaction...")
            signed_tx = await self._sign_transaction(swap_tx_data)
            if not signed_tx:
                logger.error("❌ Failed to sign transaction")
                return {
                    'status': 'error',
                    'success': False,
                    'error': 'Transaction signing failed',
                    'timestamp': datetime.now().isoformat()
                }

            # Step 4: Send transaction
            logger.info(f"📤 Sending transaction via {'Jito bundle' if use_jito else 'standard RPC'}...")
            if use_jito:
                send_result = await self._send_jito_bundle(signed_tx)
            else:
                send_result = await self._send_transaction(signed_tx)

            if not send_result or not send_result.get('success'):
                logger.error(f"❌ Transaction send failed: {send_result.get('error', 'Unknown')}")
                return {
                    'status': 'error',
                    'success': False,
                    'error': send_result.get('error', 'Transaction send failed'),
                    'timestamp': datetime.now().isoformat()
                }

            signature = send_result.get('signature')
            logger.info(f"✅ Transaction sent: {signature}")

            # Step 5: Wait for confirmation
            logger.info("⏳ Waiting for confirmation...")
            confirmed = await self._wait_for_confirmation(signature)

            if confirmed:
                # Calculate actual output and fees
                output_amount = int(quote.get('outAmount', 0)) / 1e9
                price_impact = float(quote.get('priceImpactPct', 0))
                fees = self._calculate_fees(amount_in, use_jito)

                logger.info(
                    f"🎉 Swap confirmed! "
                    f"{amount_in:.4f} → {output_amount:.4f} "
                    f"(Impact: {price_impact:.2f}%)"
                )

                return {
                    'status': 'confirmed',
                    'success': True,
                    'signature': signature,
                    'input_amount': amount_in,
                    'output_amount': output_amount,
                    'price_impact_pct': price_impact,
                    'fees': fees,
                    'jito_used': use_jito,
                    'timestamp': datetime.now().isoformat()
                }
            else:
                logger.warning(f"⚠️  Transaction confirmation timeout: {signature}")
                return {
                    'status': 'pending',
                    'success': False,
                    'signature': signature,
                    'error': 'Confirmation timeout (transaction may still confirm)',
                    'timestamp': datetime.now().isoformat()
                }

        except Exception as e:
            logger.error(f"❌ Error executing real swap: {e}", exc_info=True)
            return {
                'status': 'error',
                'success': False,
                'error': str(e),
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
    async def _get_swap_transaction(self, quote: Dict) -> Optional[str]:
        """
        Get swap transaction from Jupiter API.

        Args:
            quote: Quote response from Jupiter

        Returns:
            Base64-encoded swap transaction or None
        """
        try:
            async with aiohttp.ClientSession() as session:
                swap_request = {
                    'quoteResponse': quote,
                    'userPublicKey': self.wallet.get_public_key(),
                    'wrapAndUnwrapSol': True,
                    'dynamicComputeUnitLimit': True,
                    'prioritizationFeeLamports': 'auto'
                }

                async with session.post(
                    f"{self.jupiter_api}/swap",
                    json=swap_request,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        swap_transaction = data.get('swapTransaction')
                        if swap_transaction:
                            logger.debug(f"✅ Got swap transaction ({len(swap_transaction)} bytes)")
                            return swap_transaction
                        else:
                            logger.error("❌ No swap transaction in response")
                            return None
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ Jupiter swap API failed: {response.status} - {error_text}")
                        return None

        except Exception as e:
            logger.error(f"❌ Error getting swap transaction: {e}")
            return None

    async def _sign_transaction(self, swap_tx_base64: str) -> Optional[bytes]:
        """
        Deserialize and sign a transaction.

        Args:
            swap_tx_base64: Base64-encoded transaction from Jupiter

        Returns:
            Signed transaction bytes or None
        """
        try:
            from solders.transaction import VersionedTransaction

            # Decode base64 transaction
            tx_bytes = base64.b64decode(swap_tx_base64)

            # Deserialize the versioned transaction
            tx = VersionedTransaction.from_bytes(tx_bytes)

            # Sign with keypair - create new VersionedTransaction with signature
            signed_tx = VersionedTransaction(tx.message, [self.wallet.keypair])

            logger.debug("✅ Transaction signed successfully")
            return bytes(signed_tx)

        except Exception as e:
            logger.error(f"❌ Error signing transaction: {e}")
            return None

    async def _send_transaction(self, signed_tx: bytes) -> Dict:
        """
        Send transaction via standard Solana RPC.

        Args:
            signed_tx: Signed transaction bytes

        Returns:
            Result dictionary with signature and success status
        """
        try:
            client = AsyncClient(self.rpc_url)

            # Deserialize the versioned transaction
            versioned_tx = VersionedTransaction.from_bytes(signed_tx)

            # Send transaction
            response = await client.send_raw_transaction(
                signed_tx,
                opts={'skipPreflight': False, 'maxRetries': 3}
            )

            await client.close()

            if response.value:
                signature = str(response.value)
                logger.info(f"✅ Transaction sent via RPC: {signature}")
                return {
                    'success': True,
                    'signature': signature
                }
            else:
                logger.error(f"❌ Failed to send transaction: {response}")
                return {
                    'success': False,
                    'error': 'Transaction send failed (no signature returned)'
                }

        except Exception as e:
            logger.error(f"❌ Error sending transaction: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    async def _send_jito_bundle(self, signed_tx: bytes) -> Dict:
        """
        Send transaction via Jito bundle for MEV protection.

        Args:
            signed_tx: Signed transaction bytes

        Returns:
            Result dictionary with bundle ID and success status
        """
        try:
            # Select random Jito tip account
            tip_account = random.choice(self.jito_tip_accounts)

            # Encode transaction to base64
            tx_base64 = base64.b64encode(signed_tx).decode('utf-8')

            # Create bundle payload
            bundle_payload = {
                'jsonrpc': '2.0',
                'id': 1,
                'method': 'sendBundle',
                'params': [[tx_base64]]
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.jito_block_engine}/bundles",
                    json=bundle_payload,
                    headers={'Content-Type': 'application/json'},
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        bundle_id = data.get('result')

                        if bundle_id:
                            logger.info(f"✅ Jito bundle submitted: {bundle_id}")
                            # Extract signature from transaction for tracking
                            # For now, use bundle_id as signature
                            return {
                                'success': True,
                                'signature': bundle_id,
                                'bundle_id': bundle_id
                            }
                        else:
                            error = data.get('error', {})
                            logger.error(f"❌ Jito bundle error: {error}")
                            return {
                                'success': False,
                                'error': f"Jito bundle failed: {error.get('message', 'Unknown error')}"
                            }
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ Jito API error: {response.status} - {error_text}")
                        return {
                            'success': False,
                            'error': f"Jito API error: {response.status}"
                        }

        except Exception as e:
            logger.error(f"❌ Error sending Jito bundle: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    async def _wait_for_confirmation(
        self,
        signature: str,
        max_retries: int = 30,
        retry_delay: float = 2.0
    ) -> bool:
        """
        Wait for transaction confirmation.

        Args:
            signature: Transaction signature to track
            max_retries: Maximum number of confirmation checks
            retry_delay: Seconds between checks

        Returns:
            True if confirmed, False if timeout
        """
        try:
            client = AsyncClient(self.rpc_url)

            for attempt in range(max_retries):
                try:
                    # Check transaction status
                    response = await client.get_signature_statuses([signature])

                    if response.value and len(response.value) > 0:
                        status = response.value[0]

                        if status:
                            # Check confirmation status
                            if status.confirmation_status:
                                confirmation_level = str(status.confirmation_status)

                                if confirmation_level in ['confirmed', 'finalized']:
                                    logger.info(f"✅ Transaction confirmed ({confirmation_level}): {signature}")
                                    await client.close()
                                    return True

                                logger.debug(f"⏳ Confirmation status: {confirmation_level} (attempt {attempt + 1}/{max_retries})")

                            # Check for errors
                            if status.err:
                                logger.error(f"❌ Transaction failed: {status.err}")
                                await client.close()
                                return False

                except Exception as check_error:
                    logger.debug(f"⚠️  Confirmation check error (attempt {attempt + 1}): {check_error}")

                # Wait before next check
                await asyncio.sleep(retry_delay)

            logger.warning(f"⏰ Confirmation timeout after {max_retries * retry_delay}s: {signature}")
            await client.close()
            return False

        except Exception as e:
            logger.error(f"❌ Error waiting for confirmation: {e}")
            return False
