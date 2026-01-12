#!/bin/bash
# Skapar sammanfattningar som Claude kan läsa enkelt

DATA_DIR="/home/user/solbottrad/data"
ANALYSIS_DIR="/home/user/solbottrad/analysis"

# 1. SENASTE 50 TRADES (lätt att läsa)
echo "=== LATEST 50 TRADES ===" > "$ANALYSIS_DIR/summaries/latest_trades.txt"
if [ -f "$DATA_DIR/ml_trades.csv" ]; then
    tail -51 "$DATA_DIR/ml_trades.csv" >> "$ANALYSIS_DIR/summaries/latest_trades.txt"
else
    echo "No trades yet" >> "$ANALYSIS_DIR/summaries/latest_trades.txt"
fi

# 2. PERFORMANCE SUMMARY
echo "=== PERFORMANCE SUMMARY ===" > "$ANALYSIS_DIR/summaries/performance.txt"
if [ -f "$DATA_DIR/ml_trades.csv" ]; then
    python3 << 'PYTHON' >> "$ANALYSIS_DIR/summaries/performance.txt"
import pandas as pd
import os

csv_path = "/home/user/solbottrad/data/ml_trades.csv"
if os.path.exists(csv_path):
    df = pd.read_csv(csv_path)

    print(f"Total Trades: {len(df)}")
    print(f"Win Rate: {(df['profit_pct'] > 0).sum() / len(df) * 100:.1f}%")
    print(f"Avg Profit: {df['profit_pct'].mean():.2f}%")
    print(f"Avg Win: {df[df['profit_pct'] > 0]['profit_pct'].mean():.2f}%")
    print(f"Avg Loss: {df[df['profit_pct'] <= 0]['profit_pct'].mean():.2f}%")
    print(f"Total PnL: ${df['profit_usd'].sum():.2f}")
    print(f"\n📊 BY EXIT REASON:")
    print(df.groupby('exit_reason')['profit_pct'].agg(['count', 'mean']).to_string())

    # Step-up tiers (if exists)
    if 'step_tier' in df.columns:
        tiers = df[df['step_tier'].notna()]
        if len(tiers) > 0:
            print(f"\n📈 BY STEP-UP TIER:")
            print(tiers.groupby('step_tier')['profit_pct'].agg(['count', 'mean', 'min', 'max']).to_string())

    # Entry filter reasons
    if 'entry_filter_reason' in df.columns:
        print(f"\n🎯 TOP ENTRY REASONS:")
        print(df['entry_filter_reason'].value_counts().head(10).to_string())
PYTHON
else
    echo "No trades yet" >> "$ANALYSIS_DIR/summaries/performance.txt"
fi

# 3. REJECTED TOKENS SUMMARY
echo "=== REJECTED TOKENS SUMMARY (Last 100) ===" > "$ANALYSIS_DIR/summaries/rejected.txt"
if [ -f "$DATA_DIR/export_rejected.csv" ]; then
    tail -101 "$DATA_DIR/export_rejected.csv" >> "$ANALYSIS_DIR/summaries/rejected.txt"
else
    echo "No rejected data yet" >> "$ANALYSIS_DIR/summaries/rejected.txt"
fi

# 4. MOONSHOT EXCEPTIONS (if any)
echo "=== MOONSHOT EXCEPTIONS ===" > "$ANALYSIS_DIR/summaries/moonshots.txt"
if [ -f "$DATA_DIR/ml_trades.csv" ]; then
    grep "moonshot_exception" "$DATA_DIR/ml_trades.csv" >> "$ANALYSIS_DIR/summaries/moonshots.txt" 2>/dev/null || echo "None yet (waiting for tokens with LP burned 100% + ratio 4-6)" >> "$ANALYSIS_DIR/summaries/moonshots.txt"
else
    echo "No trades yet" >> "$ANALYSIS_DIR/summaries/moonshots.txt"
fi

# 5. INCUBATOR TRADES
echo "=== INCUBATOR TRADES ===" > "$ANALYSIS_DIR/summaries/incubator.txt"
if [ -f "$DATA_DIR/ml_trades.csv" ]; then
    grep "incubator" "$DATA_DIR/ml_trades.csv" >> "$ANALYSIS_DIR/summaries/incubator.txt" 2>/dev/null || echo "None yet (no incubator triggers)" >> "$ANALYSIS_DIR/summaries/incubator.txt"
else
    echo "No trades yet" >> "$ANALYSIS_DIR/summaries/incubator.txt"
fi

echo "✅ Summaries created in $ANALYSIS_DIR/summaries/"
