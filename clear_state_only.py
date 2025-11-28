#!/usr/bin/env python3
"""
Just clear the state file without selling.
Use this if tokens are unsellable (no liquidity) or you want to abandon them.
"""

import json
import os
import shutil
from datetime import datetime


def main():
    print("="*70)
    print("🗑️  CLEAR STATE ONLY - Skip Selling")
    print("="*70)
    print()
    print("This will:")
    print("   ✅ Clear the position state file")
    print("   ✅ Create a backup first")
    print("   ❌ NOT sell any tokens (they'll stay in wallet)")
    print()
    print("Use this if:")
    print("   - Tokens have no liquidity (can't sell)")
    print("   - You want to abandon them")
    print("   - You just want fresh bot state")
    print()

    response = input("Continue? (yes/no): ")
    if response.lower() != 'yes':
        print("❌ Cancelled")
        return

    print()

    state_file = "live_trading_state.json"

    if not os.path.exists(state_file):
        print("ℹ️  No state file found - nothing to clear")
        print()
        print("You're already starting fresh!")
        return

    # Backup
    backup_file = f"{state_file}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy(state_file, backup_file)
    print(f"💾 Backed up to: {backup_file}")

    # Show what we're removing
    with open(state_file, 'r') as f:
        state = json.load(f)

    positions = state.get('positions', {})
    print(f"📊 Removing {len(positions)} positions from tracking")

    if positions:
        print()
        print("Positions being cleared:")
        for i, (token, pos) in enumerate(positions.items(), 1):
            amount = pos.get('amount_usd', 0)
            print(f"   {i}. {token[:8]}... (${amount:.2f})")

    # Remove
    os.remove(state_file)
    print()
    print(f"🗑️  Removed: {state_file}")
    print()
    print("="*70)
    print("✅ STATE CLEARED!")
    print()
    print("Notes:")
    print("   - Tokens are still in your wallet (just not tracked)")
    print("   - Bot will start with 0 positions next time")
    print("   - You can restore from backup if needed:")
    print(f"     cp {backup_file} {state_file}")
    print()
    print("Next steps:")
    print("   1. Review CLEAN_RESTART.md")
    print("   2. Decide if you want to deposit more SOL")
    print("   3. Run: python3 preflight_check.py")
    print("   4. Start fresh: python -m src.main > bot.log 2>&1 &")
    print("="*70)


if __name__ == '__main__':
    main()
