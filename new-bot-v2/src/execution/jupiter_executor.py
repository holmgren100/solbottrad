"""
Jupiter Executor - Swap Execution via Jupiter Aggregator

Handles buying and selling tokens through Jupiter's swap API.

For now: Mock execution (paper trading)
Phase 4: Real wallet integration

Features:
- Get swap quotes
- Execute buys (SOL → Token)
- Execute sells (Token → SOL)
- Auto-retry with increased slippage
- Transaction confirmation
"""

import logging
import time
from typing import Dict, Optional

from src.api.jupiter_client import JupiterClient
from config.parameters import API_MAX_RETRIES

logger = logging.getLogger(__name__)

# Solana addresses
SOL_MINT = "So11111111111111111111111111111111111111112"  # Wrapped SOL


class JupiterExecutor:
    """
    Executes swaps via Jupiter Aggregator.

    Phase 2: Mock execution for testing
    Phase 4: Real execution with wallet
    """

    def __init__(self, mock_mode: bool = True):
        """
        Initialize Jupiter executor.

        Args:
            mock_mode: If True, simulate swaps (no real execution)
        """
        self.jupiter_client = JupiterClient()
        self.mock_mode = mock_mode
        self.max_retries = API_MAX_RETRIES

        mode_str = "MOCK MODE (paper trading)" if mock_mode else "LIVE MODE"
        logger.info(f"Jupiter Executor initialized - {mode_str}")

    def execute_buy(
        self,
        token_address: str,
        amount_sol: float,
        slippage_bps: int = 100
    ) -> Dict:
        """
        Execute buy (SOL → Token).

        Args:
            token_address: Token to buy
            amount_sol: Amount of SOL to spend
            slippage_bps: Slippage tolerance in basis points (100 = 1%)

        Returns:
            {
                "success": bool,
                "tokens_received": float,
                "price": float,
                "slippage_used": int,
                "signature": str,
                "error": str (if failed)
            }
        """
        try:
            logger.info(
                f"🔵 BUY: {amount_sol:.4f} SOL → {token_address[:8]}... "
                f"(slippage: {slippage_bps}bps)"
            )

            # Get quote
            amount_lamports = int(amount_sol * 1e9)  # Convert SOL to lamports
            quote = self._get_quote_with_retry(
                input_mint=SOL_MINT,
                output_mint=token_address,
                amount=amount_lamports,
                slippage_bps=slippage_bps
            )

            if not quote:
                return {
                    "success": False,
                    "tokens_received": 0,
                    "price": 0,
                    "slippage_used": slippage_bps,
                    "signature": "",
                    "error": "Failed to get quote"
                }

            # Calculate tokens received
            tokens_received = float(quote.get("outAmount", 0)) / 1e9  # Adjust for decimals
            price = amount_sol / tokens_received if tokens_received > 0 else 0

            if self.mock_mode:
                # Mock execution
                logger.info(
                    f"✅ MOCK BUY: Received {tokens_received:.2f} tokens "
                    f"@ {price:.6f} SOL/token"
                )

                return {
                    "success": True,
                    "tokens_received": tokens_received,
                    "price": price,
                    "slippage_used": slippage_bps,
                    "signature": "MOCK_TX_" + str(int(time.time())),
                    "error": ""
                }
            else:
                # Real execution (Phase 4)
                # TODO: Implement real transaction signing and sending
                logger.warning("Real execution not yet implemented!")
                return {
                    "success": False,
                    "tokens_received": 0,
                    "price": 0,
                    "slippage_used": slippage_bps,
                    "signature": "",
                    "error": "Real execution not implemented"
                }

        except Exception as e:
            logger.error(f"Error executing buy: {e}")
            return {
                "success": False,
                "tokens_received": 0,
                "price": 0,
                "slippage_used": slippage_bps,
                "signature": "",
                "error": str(e)
            }

    def execute_sell(
        self,
        token_address: str,
        amount_tokens: float,
        slippage_bps: int = 100
    ) -> Dict:
        """
        Execute sell (Token → SOL).

        Args:
            token_address: Token to sell
            amount_tokens: Amount of tokens to sell
            slippage_bps: Slippage tolerance in basis points

        Returns:
            {
                "success": bool,
                "sol_received": float,
                "price": float,
                "slippage_used": int,
                "signature": str,
                "error": str (if failed)
            }
        """
        try:
            logger.info(
                f"🔴 SELL: {amount_tokens:.2f} tokens → SOL "
                f"(slippage: {slippage_bps}bps)"
            )

            # Get quote
            amount_base_units = int(amount_tokens * 1e9)  # Adjust for decimals
            quote = self._get_quote_with_retry(
                input_mint=token_address,
                output_mint=SOL_MINT,
                amount=amount_base_units,
                slippage_bps=slippage_bps
            )

            if not quote:
                return {
                    "success": False,
                    "sol_received": 0,
                    "price": 0,
                    "slippage_used": slippage_bps,
                    "signature": "",
                    "error": "Failed to get quote"
                }

            # Calculate SOL received
            sol_received = float(quote.get("outAmount", 0)) / 1e9
            price = sol_received / amount_tokens if amount_tokens > 0 else 0

            if self.mock_mode:
                # Mock execution
                logger.info(
                    f"✅ MOCK SELL: Received {sol_received:.4f} SOL "
                    f"@ {price:.6f} SOL/token"
                )

                return {
                    "success": True,
                    "sol_received": sol_received,
                    "price": price,
                    "slippage_used": slippage_bps,
                    "signature": "MOCK_TX_" + str(int(time.time())),
                    "error": ""
                }
            else:
                # Real execution (Phase 4)
                # TODO: Implement real transaction signing and sending
                logger.warning("Real execution not yet implemented!")
                return {
                    "success": False,
                    "sol_received": 0,
                    "price": 0,
                    "slippage_used": slippage_bps,
                    "signature": "",
                    "error": "Real execution not implemented"
                }

        except Exception as e:
            logger.error(f"Error executing sell: {e}")
            return {
                "success": False,
                "sol_received": 0,
                "price": 0,
                "slippage_used": slippage_bps,
                "signature": "",
                "error": str(e)
            }

    def _get_quote_with_retry(
        self,
        input_mint: str,
        output_mint: str,
        amount: int,
        slippage_bps: int
    ) -> Optional[Dict]:
        """
        Get swap quote with retry logic and increasing slippage.

        Args:
            input_mint: Input token address
            output_mint: Output token address
            amount: Amount in base units
            slippage_bps: Initial slippage in basis points

        Returns:
            Quote dict or None
        """
        for attempt in range(self.max_retries):
            try:
                # Increase slippage on retries: 100 → 200 → 300 bps
                current_slippage = slippage_bps + (attempt * 100)

                logger.debug(
                    f"Getting quote (attempt {attempt + 1}/{self.max_retries}, "
                    f"slippage: {current_slippage}bps)"
                )

                quote = self.jupiter_client.get_quote(
                    input_mint=input_mint,
                    output_mint=output_mint,
                    amount=amount,
                    slippage_bps=current_slippage
                )

                if quote:
                    logger.debug(f"Quote received on attempt {attempt + 1}")
                    return quote

                logger.warning(f"No quote on attempt {attempt + 1}")

            except Exception as e:
                logger.error(f"Error getting quote (attempt {attempt + 1}): {e}")

            # Wait before retry
            if attempt < self.max_retries - 1:
                time.sleep(1)

        logger.error(f"Failed to get quote after {self.max_retries} attempts")
        return None

    def _wait_for_confirmation(
        self,
        signature: str,
        timeout: int = 30
    ) -> bool:
        """
        Wait for transaction confirmation.

        Args:
            signature: Transaction signature
            timeout: Timeout in seconds

        Returns:
            True if confirmed, False if timeout
        """
        # TODO: Implement in Phase 4 with real transactions
        logger.debug(f"Waiting for confirmation: {signature}")
        return True


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    # Mock executor (paper trading)
    executor = JupiterExecutor(mock_mode=True)

    # Test buy
    buy_result = executor.execute_buy(
        token_address="DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",  # BONK
        amount_sol=0.1,
        slippage_bps=100
    )

    print(f"\nBuy Result:")
    print(f"Success: {buy_result['success']}")
    print(f"Tokens received: {buy_result['tokens_received']:.2f}")
    print(f"Price: {buy_result['price']:.6f} SOL/token")
    print(f"Signature: {buy_result['signature']}")

    # Test sell
    sell_result = executor.execute_sell(
        token_address="DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",
        amount_tokens=1000000,
        slippage_bps=100
    )

    print(f"\nSell Result:")
    print(f"Success: {sell_result['success']}")
    print(f"SOL received: {sell_result['sol_received']:.4f}")
    print(f"Price: {sell_result['price']:.6f} SOL/token")
    print(f"Signature: {sell_result['signature']}")
