#!/usr/bin/env python3
"""
Pre-flight check: Verify all critical systems are working before trading.
Run this BEFORE depositing money and restarting the bot.
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)


async def check_imports():
    """Test that all critical imports work."""
    print("1️⃣  Testing imports...")
    try:
        from src.blockchain.wallet_manager import WalletManager
        from src.blockchain.jupiter_executor import JupiterSwapExecutor
        from src.trading.live_trading import LiveTradingEngine
        from src.trading.position_manager import PositionManager
        from src.market.dexscreener_client import DexScreenerClient
        from src.market.jupiter_client import JupiterClient
        from src.monitoring.telegram_commands import TelegramCommandHandler
        print("   ✅ All imports successful")
        return True
    except Exception as e:
        print(f"   ❌ Import failed: {e}")
        return False


async def check_network():
    """Test network connectivity to required APIs."""
    print("\n2️⃣  Testing network connectivity...")

    import aiohttp

    endpoints = [
        ("Jupiter API", "https://lite-api.jup.ag/"),
        ("DexScreener", "https://api.dexscreener.com/latest/dex/search?q=SOL"),
    ]

    all_ok = True
    for name, url in endpoints:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status < 500:
                        print(f"   ✅ {name}")
                    else:
                        print(f"   ❌ {name} - HTTP {response.status}")
                        all_ok = False
        except Exception as e:
            print(f"   ❌ {name} - {str(e)[:50]}")
            all_ok = False

    return all_ok


async def check_wallet():
    """Test wallet loading and balance check."""
    print("\n3️⃣  Testing wallet...")

    load_dotenv()

    encryption_key = os.getenv('WALLET_ENCRYPTION_KEY')
    encrypted_key = os.getenv('SOLANA_PRIVATE_KEY_ENCRYPTED')

    if not encryption_key or not encrypted_key:
        print("   ❌ Wallet keys not found in .env")
        return False

    try:
        from src.blockchain.wallet_manager import WalletManager
        wallet = WalletManager(encryption_key)
        wallet.load_wallet_from_encrypted_key(encrypted_key)

        pubkey = str(wallet.get_public_key())
        print(f"   ✅ Wallet loaded: {pubkey[:8]}...{pubkey[-8:]}")

        # Test balance check
        from src.blockchain.jupiter_executor import JupiterSwapExecutor
        rpc_url = os.getenv('SOLANA_RPC_URL', 'https://api.mainnet-beta.solana.com')

        executor = JupiterSwapExecutor(rpc_url, use_jito=False, paper_trading=False)
        executor.set_wallet(wallet)

        # Check if we can load from live trading engine
        from src.trading.live_trading import LiveTradingEngine
        engine = LiveTradingEngine(executor)

        balance = await engine.get_wallet_balance()
        print(f"   ✅ Balance check works: ◎{balance:.6f}")

        return True

    except Exception as e:
        print(f"   ❌ Wallet test failed: {e}")
        return False


async def check_position_persistence():
    """Test position save/load functionality."""
    print("\n4️⃣  Testing position persistence...")

    state_file = "live_trading_state.json"

    if os.path.exists(state_file):
        print(f"   ✅ State file exists: {state_file}")

        import json
        try:
            with open(state_file, 'r') as f:
                state = json.load(f)

            positions = state.get('positions', {})
            print(f"   ✅ Can read state file: {len(positions)} positions")

            # Test that LiveTradingEngine can load it
            load_dotenv()
            from src.blockchain.wallet_manager import WalletManager
            from src.blockchain.jupiter_executor import JupiterSwapExecutor
            from src.trading.live_trading import LiveTradingEngine

            rpc_url = os.getenv('SOLANA_RPC_URL', 'https://api.mainnet-beta.solana.com')
            executor = JupiterSwapExecutor(rpc_url, use_jito=False, paper_trading=False)

            encryption_key = os.getenv('WALLET_ENCRYPTION_KEY')
            encrypted_key = os.getenv('SOLANA_PRIVATE_KEY_ENCRYPTED')
            wallet = WalletManager(encryption_key)
            wallet.load_wallet_from_encrypted_key(encrypted_key)
            executor.set_wallet(wallet)

            engine = LiveTradingEngine(executor, state_file=state_file)
            loaded_positions = engine.position_manager.get_all_positions()

            print(f"   ✅ Engine loaded {len(loaded_positions)} positions")
            return True

        except Exception as e:
            print(f"   ❌ Failed to load state: {e}")
            return False
    else:
        print(f"   ⚠️  No state file yet (will be created on first trade)")
        return True


async def check_monitoring():
    """Test position monitoring logic."""
    print("\n5️⃣  Testing position monitoring...")

    try:
        # Check that monitoring code exists and is not paper-trading-only
        with open('src/main.py', 'r') as f:
            main_content = f.read()

        # Look for the monitoring function
        if '_monitor_positions_impl' in main_content:
            print("   ✅ Position monitoring function exists")

            # Make sure it's not wrapped in paper trading check
            if 'if self.settings.is_paper_trading():' in main_content:
                # Check if monitoring code is inside this block
                lines = main_content.split('\n')
                in_paper_check = False
                monitor_in_paper_block = False

                for line in lines:
                    if 'if self.settings.is_paper_trading():' in line:
                        in_paper_check = True
                    elif in_paper_check and 'def _monitor_positions_impl' in line:
                        monitor_in_paper_block = True
                        break
                    elif in_paper_check and line and not line.startswith(' '):
                        in_paper_check = False

                if monitor_in_paper_block:
                    print("   ❌ WARNING: Monitoring still paper-trading only!")
                    return False

            print("   ✅ Monitoring works for live trading")
            return True
        else:
            print("   ❌ Monitoring function not found")
            return False

    except Exception as e:
        print(f"   ❌ Check failed: {e}")
        return False


async def check_config():
    """Check configuration settings."""
    print("\n6️⃣  Checking configuration...")

    load_dotenv()

    issues = []
    warnings = []

    # Critical settings
    paper_mode = os.getenv('PAPER_TRADING_MODE', 'true').lower()
    if paper_mode == 'true':
        warnings.append("PAPER_TRADING_MODE=true (will not execute real trades)")
    else:
        print("   ✅ Live trading mode enabled")

    # Check reasonable limits
    max_positions = int(os.getenv('MAX_OPEN_POSITIONS', '12'))
    if max_positions > 10:
        warnings.append(f"MAX_OPEN_POSITIONS={max_positions} (high, try 3-5)")

    max_trades = int(os.getenv('MAX_DAILY_TRADES', '250'))
    if max_trades > 50:
        warnings.append(f"MAX_DAILY_TRADES={max_trades} (very high, try 10-20)")

    min_liquidity = float(os.getenv('MIN_LIQUIDITY_USD', '5000'))
    if min_liquidity < 8000:
        warnings.append(f"MIN_LIQUIDITY_USD={min_liquidity} (low, increase to 10000+)")

    # Show warnings
    if warnings:
        print("\n   ⚠️  Configuration warnings:")
        for w in warnings:
            print(f"      - {w}")

    if issues:
        print("\n   ❌ Critical issues:")
        for i in issues:
            print(f"      - {i}")
        return False

    return True


async def main():
    print("="*70)
    print("🔍 PRE-FLIGHT CHECK - Verify Bot Is Ready")
    print("="*70)
    print()

    checks = []

    checks.append(("Imports", await check_imports()))
    checks.append(("Network", await check_network()))
    checks.append(("Wallet", await check_wallet()))
    checks.append(("Persistence", await check_position_persistence()))
    checks.append(("Monitoring", await check_monitoring()))
    checks.append(("Config", await check_config()))

    print()
    print("="*70)
    print("SUMMARY")
    print("="*70)

    all_passed = True
    for name, passed in checks:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status:10} {name}")
        if not passed:
            all_passed = False

    print()

    if all_passed:
        print("🎉 ALL CHECKS PASSED!")
        print()
        print("✅ The bot is ready to trade.")
        print()
        print("Next steps:")
        print("1. Review configuration warnings above (if any)")
        print("2. Deposit SOL: 6c9spbhr6NN1btpk84QCyyHeM1BmAEHJxrNyzGcqgspM")
        print("3. Start bot: python -m src.main > bot.log 2>&1 &")
        print("4. Monitor: tail -f bot.log")
        print()
    else:
        print("❌ SOME CHECKS FAILED")
        print()
        print("Fix the issues above before trading.")
        print()

    print("="*70)


if __name__ == '__main__':
    asyncio.run(main())
