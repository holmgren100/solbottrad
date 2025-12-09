#!/usr/bin/env python3
"""
Manual position closer - Force close all or specific positions
"""

import asyncio
import sys
sys.path.insert(0, 'src')

from trading.paper_trading import PaperTradingEngine
from market.dexscreener_client import DexScreenerClient
from config.settings import TradingConfig

async def close_all_positions():
    """Close all open positions at current market price"""
    print("🔴 Manual Position Closer\n")
    print("=" * 60)

    # Initialize components
    engine = PaperTradingEngine(
        initial_capital=TradingConfig.INITIAL_CAPITAL,
        stop_loss_percent=TradingConfig.STOP_LOSS_PERCENT,
        take_profit_percent=TradingConfig.TAKE_PROFIT_PERCENT
    )

    dex_client = DexScreenerClient()

    # Check if there are any positions
    if not engine.positions:
        print("✅ No open positions to close")
        return

    print(f"Found {len(engine.positions)} open position(s)\n")

    # List positions
    for i, (token_address, position) in enumerate(engine.positions.items(), 1):
        print(f"{i}. {position.symbol}")
        print(f"   Address: {token_address[:20]}...")
        print(f"   Entry: ${position.entry_price:.8f}")
        print(f"   P&L: {position.pnl_percent:+.2f}%")
        print(f"   Size: ${position.position_size_usd:.2f}")
        print()

    # Ask for confirmation
    response = input("\nDo you want to close ALL positions? (yes/no): ").strip().lower()

    if response not in ['yes', 'y']:
        print("\n❌ Cancelled")
        return

    print(f"\n🔄 Closing {len(engine.positions)} position(s)...\n")

    # Close each position
    closed_count = 0
    total_pnl = 0

    for token_address, position in list(engine.positions.items()):
        print(f"Closing {position.symbol}...")

        # Fetch current market price
        market_data = await dex_client.get_token_data(token_address)

        if market_data:
            current_price = float(market_data.get('priceUsd', 0))
            print(f"  Current price: ${current_price:.8f}")

            # Execute sell
            result = await engine.execute_sell(token_address, current_price)

            if result.get('success'):
                pnl = result.get('pnl', 0)
                pnl_pct = result.get('pnl_percent', 0)
                total_pnl += pnl
                print(f"  ✅ Closed: P&L ${pnl:.2f} ({pnl_pct:+.2f}%)")
                closed_count += 1
            else:
                print(f"  ❌ Failed: {result.get('reason')}")
        else:
            print(f"  ❌ Could not fetch market price")

        print()

    # Summary
    print("=" * 60)
    print(f"\n✅ Closed {closed_count} / {len(list(engine.positions))} positions")
    print(f"💰 Total P&L: ${total_pnl:.2f}")

    # Show new portfolio stats
    stats = engine.get_statistics()
    print(f"\n📊 Portfolio After Closing:")
    print(f"   Cash: ${stats['current_cash']:.2f}")
    print(f"   Portfolio Value: ${stats['portfolio_value']:.2f}")
    print(f"   Total P&L: ${stats['total_pnl']:.2f} ({stats['total_pnl_percent']:+.2f}%)")

async def close_specific_position():
    """Close a specific position by symbol or address"""
    print("🔴 Close Specific Position\n")
    print("=" * 60)

    # Initialize components
    engine = PaperTradingEngine(
        initial_capital=TradingConfig.INITIAL_CAPITAL,
        stop_loss_percent=TradingConfig.STOP_LOSS_PERCENT,
        take_profit_percent=TradingConfig.TAKE_PROFIT_PERCENT
    )

    dex_client = DexScreenerClient()

    # Check if there are any positions
    if not engine.positions:
        print("✅ No open positions")
        return

    # List positions
    positions_list = list(engine.positions.items())
    print(f"Open Positions:\n")
    for i, (token_address, position) in enumerate(positions_list, 1):
        print(f"{i}. {position.symbol} - P&L: {position.pnl_percent:+.2f}%")

    # Get user choice
    choice = input("\nEnter position number to close (or 'all' for all): ").strip()

    if choice.lower() == 'all':
        await close_all_positions()
        return

    try:
        index = int(choice) - 1
        if index < 0 or index >= len(positions_list):
            print("❌ Invalid position number")
            return

        token_address, position = positions_list[index]

        print(f"\nClosing {position.symbol}...")

        # Fetch current market price
        market_data = await dex_client.get_token_data(token_address)

        if market_data:
            current_price = float(market_data.get('priceUsd', 0))
            print(f"Current price: ${current_price:.8f}")

            # Execute sell
            result = await engine.execute_sell(token_address, current_price)

            if result.get('success'):
                pnl = result.get('pnl', 0)
                pnl_pct = result.get('pnl_percent', 0)
                print(f"\n✅ Position closed!")
                print(f"   P&L: ${pnl:.2f} ({pnl_pct:+.2f}%)")
            else:
                print(f"\n❌ Failed to close: {result.get('reason')}")
        else:
            print(f"❌ Could not fetch market price")

    except ValueError:
        print("❌ Invalid input")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == '--all':
        asyncio.run(close_all_positions())
    else:
        asyncio.run(close_specific_position())
