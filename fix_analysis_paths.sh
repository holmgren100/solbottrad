#!/bin/bash
# Fix analysis scripts to work with correct bot location

echo "🔧 Fixing analysis script paths..."

# Detect where bot is actually running
if [ -f "/home/user/solbottrad/bot.log" ]; then
    BOT_DIR="/home/user/solbottrad"
    echo "✅ Bot detected in: $BOT_DIR"
elif [ -f "/root/solbottrad/bot.log" ]; then
    BOT_DIR="/root/solbottrad"
    echo "✅ Bot detected in: $BOT_DIR"
else
    echo "⚠️  No bot log found. Defaulting to /home/user/solbottrad"
    BOT_DIR="/home/user/solbottrad"
fi

# Update all analysis scripts with correct paths
for script in create_snapshot.sh create_summaries.sh prepare_gemini_input.sh; do
    SCRIPT_PATH="/root/solbottrad/$script"
    if [ -f "$SCRIPT_PATH" ]; then
        echo "📝 Updating $script..."

        # Replace /home/user/solbottrad with actual BOT_DIR
        sed -i "s|/home/user/solbottrad|$BOT_DIR|g" "$SCRIPT_PATH"
        sed -i "s|/root/solbottrad/bot|$BOT_DIR/bot|g" "$SCRIPT_PATH"

        # Also copy to bot directory for convenience
        cp "$SCRIPT_PATH" "$BOT_DIR/"
    fi
done

# Update analysis_pipeline.sh
if [ -f "/root/solbottrad/analysis_pipeline.sh" ]; then
    echo "📝 Updating analysis_pipeline.sh..."
    sed -i "s|/root/solbottrad/data/ml_trades.csv|$BOT_DIR/data/ml_trades.csv|g" /root/solbottrad/analysis_pipeline.sh
    sed -i "s|/root/solbottrad/analysis|$BOT_DIR/analysis|g" /root/solbottrad/analysis_pipeline.sh

    # Copy to bot directory
    cp /root/solbottrad/analysis_pipeline.sh "$BOT_DIR/"
fi

# Create analysis directories
mkdir -p "$BOT_DIR/analysis"/{live,summaries,insights}

echo ""
echo "✅ Analysis scripts updated!"
echo "📂 Bot directory: $BOT_DIR"
echo "📂 Analysis output: $BOT_DIR/analysis/"
echo ""
echo "🚀 Test with: cd $BOT_DIR && ./analysis_pipeline.sh"
