#!/usr/bin/env python3
"""
Fearless Momentum Runner v2.0
Entry point for the trading bot

Usage:
    python run.py              # Run in mock mode (paper trading)
    python run.py --live       # Run in live mode (real trading - DANGEROUS!)
"""

import asyncio
import sys
import argparse

from src.main import MomentumBot


def print_banner():
    """Print startup banner."""
    print()
    print("=" * 60)
    print("🚀 FEARLESS MOMENTUM RUNNER V2.0")
    print("=" * 60)
    print()
    print("Target: 50-60% win rate, catch 500-1700% runners")
    print("Strategy: Binary momentum filters + risk-free breakeven")
    print()


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Fearless Momentum Runner v2.0 - Solana Trading Bot"
    )

    parser.add_argument(
        "--live",
        action="store_true",
        help="Run in LIVE mode (real trading - requires wallet setup)"
    )

    parser.add_argument(
        "--mock",
        action="store_true",
        default=True,
        help="Run in MOCK mode (paper trading - default)"
    )

    return parser.parse_args()


def main():
    """Start the bot."""
    print_banner()

    # Parse arguments
    args = parse_args()

    # Determine mode
    mock_mode = not args.live

    if not mock_mode:
        print("⚠️  WARNING: LIVE MODE SELECTED")
        print()
        print("You are about to run the bot with REAL money!")
        print()
        response = input("Are you sure you want to continue? (yes/no): ")

        if response.lower() != "yes":
            print("\n✅ Cancelled - staying safe!")
            sys.exit(0)

        print()
        print("💀 LIVE MODE ENABLED - REAL TRADING!")
        print()

    else:
        print("✅ MOCK MODE - Paper Trading (No Real Money)")
        print()

    print("=" * 60)
    print()

    # Create bot instance
    bot = MomentumBot(mock_mode=mock_mode)

    # Run forever
    try:
        asyncio.run(bot.run())

    except KeyboardInterrupt:
        print("\n\n⏹️  Bot stopped by user (Ctrl+C)")
        sys.exit(0)

    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
