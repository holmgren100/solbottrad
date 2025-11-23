#!/usr/bin/env python3
"""
Diagnostic script to check position status and stop loss/take profit triggers
"""

import asyncio
import sys
sys.path.insert(0, 'src')

from trading.paper_trading import PaperTradingEngine
from market.dexscreener_client import DexScreenerClient
from config.settings import TradingConfig

async def diagnose_positions():
    """Diagnose position status"""
    print("🔍 Position Diagnostics\n")
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
        print("❌ No open positions found")
        return

    print(f"📊 Found {len(engine.positions)} open position(s)\n")

    # Check each position
    for token_address, position in engine.positions.items():
        print(f"\n🔹 {position.symbol}")
        print(f"   Address: {token_address[:20]}...")
        print(f"   Entry Price: ${position.entry_price:.8f}")
        print(f"   Current Price (cached): ${position.current_price:.8f}")
        print(f"   Stop Loss: ${position.stop_loss:.8f} ({TradingConfig.STOP_LOSS_PERCENT}%)")
        print(f"   Take Profit: ${position.take_profit:.8f} ({TradingConfig.TAKE_PROFIT_PERCENT}%)")
        print(f"   P&L: {position.pnl_percent:+.2f}%")

        # Fetch current market price
        print(f"   Fetching live price from DexScreener...")
        market_data = await dex_client.get_token_data(token_address)

        if market_data:
            live_price = float(market_data.get('priceUsd', 0))
            print(f"   Live Price: ${live_price:.8f}")

            # Calculate live P&L
            live_pnl_percent = ((live_price - position.entry_price) / position.entry_price) * 100
            print(f"   Live P&L: {live_pnl_percent:+.2f}%")

            # Check triggers
            print(f"\n   ⚖️  Trigger Check:")
            if live_price <= position.stop_loss:
                print(f"   🛑 STOP LOSS TRIGGERED!")
                print(f"      ${live_price:.8f} <= ${position.stop_loss:.8f}")
            elif live_price >= position.take_profit:
                print(f"   🎯 TAKE PROFIT TRIGGERED!")
                print(f"      ${live_price:.8f} >= ${position.take_profit:.8f}")
            else:
                sl_distance = ((live_price - position.stop_loss) / position.stop_loss) * 100
                tp_distance = ((position.take_profit - live_price) / live_price) * 100
                print(f"   ✅ No triggers")
                print(f"      Stop Loss: {sl_distance:+.2f}% away")
                print(f"      Take Profit: {tp_distance:+.2f}% away")
        else:
            print(f"   ❌ Could not fetch live price from DexScreener")

        print(f"   " + "-" * 56)

    # Show portfolio stats
    print(f"\n" + "=" * 60)
    stats = engine.get_statistics()
    print(f"\n💰 Portfolio Summary:")
    print(f"   Cash: ${stats['current_cash']:.2f}")
    print(f"   Portfolio Value: ${stats['portfolio_value']:.2f}")
    print(f"   Total P&L: ${stats['total_pnl']:.2f} ({stats['total_pnl_percent']:+.2f}%)")
    print(f"   Total Trades: {stats['total_trades']} ({stats['total_buys']} buys, {stats['total_sells']} sells)")

if __name__ == "__main__":
    asyncio.run(diagnose_positions())
