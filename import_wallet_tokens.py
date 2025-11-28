#!/usr/bin/env python3
"""
Import all tokens from wallet into the bot as monitored positions.
This allows the bot to monitor and protect ALL holdings, not just recent buys.
"""

import asyncio
import sys
import os
from datetime import datetime
from dotenv import load_dotenv

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from src.blockchain.wallet_manager import WalletManager
from src.market.dexscreener_client import DexScreenerClient
from src.market.jupiter_client import JupiterClient
from src.trading.position_manager import Position
from src.trading.live_trading import LiveTradingEngine
from src.blockchain.jupiter_executor import JupiterSwapExecutor
from src.monitoring.logger import get_logger

logger = get_logger(__name__)


async def get_token_accounts(wallet_pubkey: str, rpc_url: str):
    """Get all token accounts for a wallet."""
    import aiohttp

    payload = {
        'jsonrpc': '2.0',
        'id': 1,
        'method': 'getTokenAccountsByOwner',
        'params': [
            wallet_pubkey,
            {'programId': 'TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA'},
            {'encoding': 'jsonParsed'}
        ]
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(rpc_url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as response:
            if response.status == 200:
                result = await response.json()
                return result.get('result', {}).get('value', [])

    return []


async def main():
    # Load environment
    load_dotenv()

    encryption_key = os.getenv('WALLET_ENCRYPTION_KEY')
    encrypted_key = os.getenv('SOLANA_PRIVATE_KEY_ENCRYPTED')
    rpc_url = os.getenv('SOLANA_RPC_URL', 'https://api.mainnet-beta.solana.com')

    if not encryption_key or not encrypted_key:
        print("❌ Wallet not configured in .env")
        return

    print("🔍 Scanning wallet for tokens...")
    print()

    # Load wallet
    wallet = WalletManager(encryption_key)
    wallet.load_wallet_from_encrypted_key(encrypted_key)
    wallet_pubkey = str(wallet.get_public_key())

    print(f"👛 Wallet: {wallet_pubkey[:8]}...")
    print()

    # Get all token accounts
    token_accounts = await get_token_accounts(wallet_pubkey, rpc_url)

    if not token_accounts:
        print("❌ No tokens found in wallet")
        return

    print(f"📊 Found {len(token_accounts)} token accounts")
    print()

    # Initialize APIs
    dex_api = DexScreenerClient()
    jupiter_api = JupiterClient()

    # Initialize trading engine to access position manager
    jupiter_executor = JupiterSwapExecutor(rpc_url, use_jito=False, paper_trading=False)
    jupiter_executor.set_wallet(wallet)

    trading_engine = LiveTradingEngine(jupiter_executor)

    imported_count = 0
    skipped_count = 0

    for account in token_accounts:
        try:
            # Parse token info
            parsed_info = account['account']['data']['parsed']['info']
            token_mint = parsed_info['mint']
            token_amount_str = parsed_info['tokenAmount']['uiAmountString']
            token_amount = float(token_amount_str) if token_amount_str else 0

            # Skip if no balance
            if token_amount == 0:
                skipped_count += 1
                continue

            # Get current price
            print(f"  🔎 Checking {token_mint[:8]}... ({token_amount:.2f} tokens)")

            # Try DexScreener first
            token_data = await dex_api.get_token_profile(token_mint)
            if not token_data:
                # Fallback to Jupiter
                token_data = await jupiter_api.get_token_price_data(token_mint)

            if not token_data or not token_data.get('price_usd'):
                print(f"     ⚠️  No price data - skipping")
                skipped_count += 1
                continue

            current_price = token_data['price_usd']
            token_name = token_data.get('name', 'Unknown')
            liquidity = token_data.get('liquidity_usd', 0)

            # Calculate position value
            position_value_usd = token_amount * current_price

            # VALIDATION: Check for suspicious prices
            if position_value_usd > 100000:
                print(f"     ⚠️  SUSPICIOUS: Position value ${position_value_usd:,.2f} seems too high")
                print(f"        Price: ${current_price:.8f}, Quantity: {token_amount:,.2f}")
                print(f"        This might be bad price data - SKIPPING for safety")
                skipped_count += 1
                continue

            # VALIDATION: Check for unreasonably high token prices
            if current_price > 10000:
                print(f"     ⚠️  SUSPICIOUS: Token price ${current_price:,.2f} seems too high")
                print(f"        This might be bad data (wrong decimal places) - SKIPPING")
                skipped_count += 1
                continue

            # Skip very small positions (< $0.10)
            if position_value_usd < 0.10:
                print(f"     ⚠️  Value too small (${position_value_usd:.4f}) - skipping")
                skipped_count += 1
                continue

            # Set stop loss at -20% from current price
            stop_loss = current_price * 0.80

            # Set take profit at +50% from current price
            take_profit = current_price * 1.50

            # Check if already tracked
            if token_mint in trading_engine.position_manager.open_positions:
                print(f"     ✓ Already tracked as position")
                continue

            # Create position
            position = Position(
                token_address=token_mint,
                entry_price=current_price,  # Use current price as entry
                current_price=current_price,
                amount_usd=position_value_usd,
                quantity=token_amount,
                entry_time=datetime.now(),
                stop_loss=stop_loss,
                take_profit=take_profit,
                use_trailing_stop=True,
                trailing_stop_percent=20.0,  # 20% trailing stop
                highest_price=current_price,
                trailing_stop_price=stop_loss
            )

            # Add to position manager
            trading_engine.position_manager.open_positions[token_mint] = position

            print(f"     ✅ Imported: {token_name}")
            print(f"        Price: ${current_price:.8f}")
            print(f"        Value: ${position_value_usd:.2f}")
            print(f"        Stop Loss: ${stop_loss:.8f} (-20%)")
            print(f"        Liquidity: ${liquidity:,.0f}")
            print()

            imported_count += 1

        except Exception as e:
            logger.error(f"Error processing token account: {e}")
            skipped_count += 1
            continue

    # Save state
    if imported_count > 0:
        trading_engine.save_state()
        print(f"💾 Saved {imported_count} positions to live_trading_state.json")

    print()
    print("="*60)
    print(f"✅ Import complete!")
    print(f"   Imported: {imported_count} tokens")
    print(f"   Skipped: {skipped_count} tokens (no price, too small, or already tracked)")
    print(f"   Total positions: {len(trading_engine.position_manager.open_positions)}")
    print()
    print("🔄 Restart your bot to start monitoring all positions:")
    print("   pkill -9 python3 && python -m src.main > bot.log 2>&1 &")
    print()


if __name__ == '__main__':
    asyncio.run(main())
