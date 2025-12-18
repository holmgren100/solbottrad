"""
View current bot status from the log file.
Run this while the bot is running to see what's happening.
"""
import os
from datetime import datetime

log_file = 'trading_bot.log'

print("=" * 70)
print("TRADING BOT STATUS - LOG FILE VIEWER")
print("=" * 70)
print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

if not os.path.exists(log_file):
    print("❌ Log file not found!")
    print("Make sure the bot is running and writing to 'trading_bot.log'")
else:
    file_size = os.path.getsize(log_file)
    print(f"📄 Log file: {log_file}")
    print(f"📊 File size: {file_size} bytes")
    print()

    if file_size == 0:
        print("⚠️  Log file is empty!")
        print()
        print("Possible reasons:")
        print("1. Bot just started (no logs yet)")
        print("2. File is being held by bot process (Windows file locking)")
        print("3. Logging configuration issue")
        print()
        print("Try:")
        print("- Wait a few seconds for logs to flush")
        print("- Check terminal output instead")
        print("- Stop the bot and check log file again")
    else:
        print("Recent log entries:")
        print("-" * 70)
        try:
            with open(log_file, 'r') as f:
                lines = f.readlines()
                # Show last 30 lines
                for line in lines[-30:]:
                    print(line.rstrip())
        except Exception as e:
            print(f"❌ Error reading log file: {e}")
            print("The file might be locked by the bot process")

print()
print("=" * 70)
print()
print("💡 TIP: To see live positions and trades:")
print("   - Check the terminal where the bot is running")
print("   - Look for '🎯 TRADING OPPORTUNITY' messages")
print("   - '⏭️  Skipping' means position is already open")
print("   - Check your Telegram for trade notifications")
print()
