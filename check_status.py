"""
Quick script to check bot status including open positions.
"""
import sys
sys.path.insert(0, '/home/user/solbottrad')

from src.config import settings
from src.trading import PaperTradingEngine

# Create paper trading engine instance
engine = PaperTradingEngine(initial_capital=1000.0)

# Note: This creates a NEW engine, not the one the bot is using
# The actual bot's positions are in memory and will be lost when bot stops

print("=" * 60)
print("PAPER TRADING STATUS CHECK")
print("=" * 60)
print("\nNOTE: This creates a fresh engine instance.")
print("To see actual bot positions, check terminal output while bot runs.")
print("\nIf you see 'Position already exists' messages in the bot terminal,")
print("it means trades WERE executed and positions are still open!")
print("\nTo properly track performance:")
print("1. The bot needs to be running")
print("2. Positions need to be closed (sold) to show in statistics")
print("3. Currently only CLOSED trades count in total_trades")
print("\nSuggested fixes:")
print("- Add persistence (save positions to file/database)")
print("- Modify scan logic to skip tokens with open positions")
print("- Add a command to view open positions while bot runs")
print("=" * 60)
