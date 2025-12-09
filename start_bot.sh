#!/bin/bash
# Solana Trading Bot Startup Script
# This script ensures the bot runs with correct Python module imports

set -e  # Exit on error

# Change to bot directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Starting Solana Trading Bot..."
echo "Working directory: $(pwd)"

# Check if virtual environment exists
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1)
echo "Python version: $PYTHON_VERSION"

# Run bot as Python module (required for relative imports)
echo "Launching bot with: python3 -m src.main"
exec python3 -m src.main
