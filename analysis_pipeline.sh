#!/bin/bash
# MASTER ANALYSIS PIPELINE
# Skapar all data som Claude behöver för komplett analys

echo "🔄 Running analysis pipeline..."

# 1. Create snapshots
/home/user/solbottrad/create_snapshot.sh

# 2. Create summaries
/home/user/solbottrad/create_summaries.sh

# 3. Generate insights (Python analysis)
python3 << 'PYTHON'
import pandas as pd
import os
from datetime import datetime

output_dir = "/home/user/solbottrad/analysis/insights"
os.makedirs(output_dir, exist_ok=True)

csv_path = "/home/user/solbottrad/data/ml_trades.csv"
if os.path.exists(csv_path):
    df = pd.read_csv(csv_path)

    # Generate timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(f"{output_dir}/latest_insights.txt", "w") as f:
        f.write(f"=== ANALYSIS INSIGHTS - {timestamp} ===\n\n")

        # 1. Performance by hour
        if 'entry_time' in df.columns:
            f.write("📊 PERFORMANCE BY HOUR:\n")
            try:
                df['hour'] = pd.to_datetime(df['entry_time']).dt.hour
                hourly = df.groupby('hour')['profit_pct'].agg(['count', 'mean'])
                f.write(hourly.to_string() + "\n\n")
            except:
                f.write("Error parsing entry_time\n\n")

        # 2. Best/Worst performers
        f.write("🏆 TOP 10 WINNERS:\n")
        cols = ['symbol', 'profit_pct', 'exit_reason']
        if 'entry_filter_reason' in df.columns:
            cols.append('entry_filter_reason')
        f.write(df.nlargest(10, 'profit_pct')[cols].to_string() + "\n\n")

        f.write("💀 TOP 10 LOSERS:\n")
        f.write(df.nsmallest(10, 'profit_pct')[cols].to_string() + "\n\n")

        # 3. Nuclear stops analysis
        nuclear = df[df['exit_reason'].str.contains('nuclear', na=False)]
        if len(nuclear) > 0:
            f.write(f"🚨 NUCLEAR STOPS: {len(nuclear)} trades\n")
            f.write(f"   Avg exit: {nuclear['profit_pct'].mean():.2f}%\n")
            f.write(f"   Target: -20%, Actual: {nuclear['profit_pct'].mean():.2f}%\n")
            f.write(f"   Slippage: {abs(nuclear['profit_pct'].mean() + 20):.2f}%\n")
            f.write(f"   Best: {nuclear['profit_pct'].max():.2f}%\n")
            f.write(f"   Worst: {nuclear['profit_pct'].min():.2f}%\n\n")

        # 4. Step-up tier analysis
        if 'step_tier' in df.columns:
            tiers = df[df['step_tier'].notna()]
            if len(tiers) > 0:
                f.write("📈 STEP-UP TIER ANALYSIS:\n")
                f.write(tiers.groupby('step_tier')['profit_pct'].agg(['count', 'mean', 'min', 'max']).to_string() + "\n\n")

                # Expected vs actual
                f.write("   Expected ranges:\n")
                f.write("   - tight_7pct: exits at <20% profit\n")
                f.write("   - standard_15pct: exits at 20-100% profit\n")
                f.write("   - wide_25pct: exits at >100% profit\n\n")

        # 5. Moonshot exceptions
        moonshots = df[df['entry_filter_reason'].str.contains('moonshot_exception', na=False)]
        if len(moonshots) > 0:
            f.write(f"🚀 MOONSHOT EXCEPTIONS: {len(moonshots)} trades\n")
            f.write(f"   Win rate: {(moonshots['profit_pct'] > 0).sum() / len(moonshots) * 100:.1f}%\n")
            f.write(f"   Avg profit: {moonshots['profit_pct'].mean():.2f}%\n")
            f.write(f"   Best: {moonshots['profit_pct'].max():.2f}%\n\n")
        else:
            f.write("🚀 MOONSHOT EXCEPTIONS: None yet\n")
            f.write("   Waiting for tokens with:\n")
            f.write("   - Vol/Liq ratio 4.0-6.0\n")
            f.write("   - LP burned 100%\n")
            f.write("   - Liquidity $30k+\n\n")

        # 6. Incubator triggers
        incubator = df[df['entry_filter_reason'].str.contains('incubator', na=False)]
        if len(incubator) > 0:
            f.write(f"💎 INCUBATOR TRIGGERS: {len(incubator)} trades\n")
            f.write(f"   Win rate: {(incubator['profit_pct'] > 0).sum() / len(incubator) * 100:.1f}%\n")
            f.write(f"   Avg profit: {incubator['profit_pct'].mean():.2f}%\n")

            # Strong vs Early
            strong = incubator[incubator['entry_filter_reason'].str.contains('strong')]
            early = incubator[incubator['entry_filter_reason'].str.contains('early')]
            if len(strong) > 0:
                f.write(f"   STRONG triggers: {len(strong)} (win: {(strong['profit_pct']>0).sum()/len(strong)*100:.1f}%)\n")
            if len(early) > 0:
                f.write(f"   EARLY triggers: {len(early)} (win: {(early['profit_pct']>0).sum()/len(early)*100:.1f}%)\n")
        else:
            f.write("💎 INCUBATOR TRIGGERS: None yet\n")
            f.write("   Criteria may be too strict:\n")
            f.write("   - LP burned 100%\n")
            f.write("   - Age >10 min\n")
            f.write("   - Liquidity $15k-$150k\n")
            f.write("   - Volume >$30k\n")
            f.write("   - Vol/Liq <1.5\n\n")

        # 7. Session comparison (last 50 vs all)
        if len(df) > 50:
            f.write("📉 RECENT vs ALL (last 50 trades):\n")
            recent = df.tail(50)
            f.write(f"   Recent win rate: {(recent['profit_pct']>0).sum()/len(recent)*100:.1f}%\n")
            f.write(f"   All-time win rate: {(df['profit_pct']>0).sum()/len(df)*100:.1f}%\n")
            f.write(f"   Recent avg: {recent['profit_pct'].mean():.2f}%\n")
            f.write(f"   All-time avg: {df['profit_pct'].mean():.2f}%\n\n")

    print(f"✅ Insights saved to {output_dir}/latest_insights.txt")
else:
    print("⚠️  No trades CSV found yet")
PYTHON

echo "✅ Analysis pipeline complete!"
echo "📂 Results in /home/user/solbottrad/analysis/"
