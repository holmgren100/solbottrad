#!/bin/bash
# Backup and Reset Bot Data
# Creates timestamped backup of old data and starts fresh

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="backups/backup_$TIMESTAMP"

echo "🔄 Creating backup directory: $BACKUP_DIR"
mkdir -p "$BACKUP_DIR"

# Backup bot state
if [ -f "bot_state.json" ]; then
    echo "📦 Backing up bot_state.json..."
    cp bot_state.json "$BACKUP_DIR/"
    rm bot_state.json
    echo "   ✅ Backed up and removed"
else
    echo "   ℹ️  No bot_state.json found"
fi

# Backup CSV files
if [ -d "data" ]; then
    echo "📦 Backing up CSV files from data/..."
    cp -r data "$BACKUP_DIR/"
    rm -rf data/*.csv 2>/dev/null
    echo "   ✅ CSV files backed up and removed"
else
    echo "   ℹ️  No data directory found"
fi

# Backup log files
if ls *.log 1> /dev/null 2>&1; then
    echo "📦 Backing up log files..."
    cp *.log "$BACKUP_DIR/" 2>/dev/null
    rm *.log 2>/dev/null
    echo "   ✅ Log files backed up and removed"
else
    echo "   ℹ️  No log files found"
fi

echo ""
echo "✅ Backup complete!"
echo "📁 Location: $BACKUP_DIR"
echo ""
echo "🆕 Bot is now ready for fresh start!"
echo "   All old data safely backed up"
echo ""
echo "To restore backup:"
echo "   cp $BACKUP_DIR/bot_state.json ."
echo "   cp -r $BACKUP_DIR/data ."
