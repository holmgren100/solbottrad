#!/usr/bin/env python3
"""
Analyze why win rate is low despite being profitable.
Identifies patterns in losing trades to improve filters.
"""

import json
import pandas as pd
from collections import defaultdict

def load_trades():
    """Load all trades from ML data."""
    trades = []
    with open('data/ml_training/ml_trades.jsonl', 'r') as f:
        for line in f:
            trades.append(json.loads(line))
    return pd.DataFrame(trades)

def analyze_losses(df):
    """Deep dive into losing trades."""

    # Split wins vs losses
    wins = df[df['win'] == True]
    losses = df[df['win'] == False]

    print("=" * 80)
    print("📊 WIN RATE ANALYSIS")
    print("=" * 80)
    print(f"\nTotal Trades: {len(df)}")
    print(f"Wins: {len(wins)} ({len(wins)/len(df)*100:.1f}%)")
    print(f"Losses: {len(losses)} ({len(losses)/len(df)*100:.1f}%)")

    # Calculate fee impact
    total_fees = df['total_fees_usd'].sum()
    avg_fee_per_trade = total_fees / len(df)
    fees_from_losses = losses['total_fees_usd'].sum()

    print(f"\n💸 FEE ANALYSIS:")
    print(f"Total fees paid: ${total_fees:.2f}")
    print(f"Avg fee per trade: ${avg_fee_per_trade:.2f}")
    print(f"Fees wasted on losses: ${fees_from_losses:.2f} ({fees_from_losses/total_fees*100:.1f}%)")

    # Exit reasons
    print(f"\n🚪 WHY DID TRADES EXIT?")
    print("\nWinning trades:")
    print(wins['exit_reason'].value_counts())
    print("\nLosing trades:")
    print(losses['exit_reason'].value_counts())

    # Hold duration
    print(f"\n⏱️  HOLD DURATION:")
    print(f"Winners avg hold: {wins['hold_duration_minutes'].mean():.1f} minutes")
    print(f"Losers avg hold: {losses['hold_duration_minutes'].mean():.1f} minutes")

    # Entry conditions comparison
    print(f"\n📊 ENTRY CONDITIONS (Winners vs Losers):")

    metrics = {
        'Liquidity': 'entry_liquidity_usd',
        'Volume 24h': 'entry_volume_24h',
        'Token Age (hrs)': 'token_age_hours',
        'Risk Score': 'overall_risk_score',
        'Sentiment': 'sentiment_score'
    }

    for name, col in metrics.items():
        if col in df.columns:
            win_avg = wins[col].mean()
            loss_avg = losses[col].mean()
            diff_pct = ((win_avg - loss_avg) / loss_avg * 100) if loss_avg != 0 else 0
            print(f"{name:20s} Winners: ${win_avg:10,.0f} | Losers: ${loss_avg:10,.0f} | Diff: {diff_pct:+.1f}%")

    # Dead tokens analysis
    dead_token_losses = losses[losses['exit_reason'] == 'low_liquidity']
    print(f"\n💀 DEAD TOKEN ANALYSIS:")
    print(f"Losses from dead tokens: {len(dead_token_losses)} ({len(dead_token_losses)/len(losses)*100:.1f}% of losses)")
    print(f"Avg loss on dead tokens: ${dead_token_losses['pnl_usd'].mean():.2f}")
    print(f"Avg hold time before detection: {dead_token_losses['hold_duration_minutes'].mean():.1f} minutes")

    # Stop loss analysis
    stop_losses = losses[losses['exit_reason'] == 'stop_loss']
    print(f"\n🛑 STOP LOSS ANALYSIS:")
    print(f"Stop loss exits: {len(stop_losses)} ({len(stop_losses)/len(losses)*100:.1f}% of losses)")
    print(f"Avg loss on stop: ${stop_losses['pnl_usd'].mean():.2f}")

    # Trailing stop on losers
    trailing_losses = losses[losses['exit_reason'] == 'trailing_stop']
    print(f"\n📉 TRAILING STOP LOSSES:")
    print(f"Trailing stop exits (losers): {len(trailing_losses)} ({len(trailing_losses)/len(losses)*100:.1f}%)")
    print(f"These peaked, then fell below trailing stop")
    if len(trailing_losses) > 0:
        print(f"Avg peak gain before fall: {trailing_losses['highest_price_reached'].div(trailing_losses['entry_price']).sub(1).mul(100).mean():.1f}%")

    # P&L distribution
    print(f"\n💰 P&L DISTRIBUTION:")
    print(f"Biggest win: ${wins['pnl_usd'].max():.2f} (+{wins['pnl_percent'].max():.1f}%)")
    print(f"Avg win: ${wins['pnl_usd'].mean():.2f} (+{wins['pnl_percent'].mean():.1f}%)")
    print(f"Biggest loss: ${losses['pnl_usd'].min():.2f} ({losses['pnl_percent'].min():.1f}%)")
    print(f"Avg loss: ${losses['pnl_usd'].mean():.2f} ({losses['pnl_percent'].mean():.1f}%)")

    # Net P&L
    total_pnl = df['pnl_usd'].sum()
    win_pnl = wins['pnl_usd'].sum()
    loss_pnl = losses['pnl_usd'].sum()
    print(f"\n💵 NET P&L:")
    print(f"Total from wins: ${win_pnl:.2f}")
    print(f"Total from losses: ${loss_pnl:.2f}")
    print(f"Net profit: ${total_pnl:.2f}")
    print(f"Profit factor: {abs(win_pnl/loss_pnl):.2f}x" if loss_pnl != 0 else "N/A")

    return wins, losses

def find_optimization_opportunities(wins, losses):
    """Find filters that could improve win rate."""

    print(f"\n" + "=" * 80)
    print("🔍 OPTIMIZATION OPPORTUNITIES")
    print("=" * 80)

    # Liquidity threshold analysis
    print(f"\n💧 LIQUIDITY FILTER ANALYSIS:")
    for threshold in [50000, 75000, 100000, 150000]:
        high_liq_wins = wins[wins['entry_liquidity_usd'] >= threshold]
        high_liq_losses = losses[losses['entry_liquidity_usd'] >= threshold]
        total_high_liq = len(high_liq_wins) + len(high_liq_losses)
        if total_high_liq > 0:
            win_rate = len(high_liq_wins) / total_high_liq * 100
            print(f"  Liquidity >= ${threshold:,}: {len(high_liq_wins)}/{total_high_liq} wins ({win_rate:.1f}% win rate)")

    # Volume threshold analysis
    print(f"\n📊 VOLUME FILTER ANALYSIS:")
    for threshold in [50000, 100000, 200000, 300000]:
        high_vol_wins = wins[wins['entry_volume_24h'] >= threshold]
        high_vol_losses = losses[losses['entry_volume_24h'] >= threshold]
        total_high_vol = len(high_vol_wins) + len(high_vol_losses)
        if total_high_vol > 0:
            win_rate = len(high_vol_wins) / total_high_vol * 100
            print(f"  Volume >= ${threshold:,}: {len(high_vol_wins)}/{total_high_vol} wins ({win_rate:.1f}% win rate)")

    # Token age analysis
    print(f"\n⏰ TOKEN AGE ANALYSIS:")
    for min_age, max_age in [(0, 6), (6, 24), (24, 72), (72, 999)]:
        age_wins = wins[(wins['token_age_hours'] >= min_age) & (wins['token_age_hours'] < max_age)]
        age_losses = losses[(losses['token_age_hours'] >= min_age) & (losses['token_age_hours'] < max_age)]
        total_age = len(age_wins) + len(age_losses)
        if total_age > 0:
            win_rate = len(age_wins) / total_age * 100
            print(f"  Age {min_age}-{max_age}h: {len(age_wins)}/{total_age} wins ({win_rate:.1f}% win rate)")

    # Risk score analysis
    print(f"\n⚠️  RISK SCORE FILTER:")
    for max_risk in [0.3, 0.4, 0.5, 0.6]:
        low_risk_wins = wins[wins['overall_risk_score'] <= max_risk]
        low_risk_losses = losses[losses['overall_risk_score'] <= max_risk]
        total_low_risk = len(low_risk_wins) + len(low_risk_losses)
        if total_low_risk > 0:
            win_rate = len(low_risk_wins) / total_low_risk * 100
            print(f"  Risk <= {max_risk}: {len(low_risk_wins)}/{total_low_risk} wins ({win_rate:.1f}% win rate)")

    # Sentiment analysis
    print(f"\n😊 SENTIMENT FILTER:")
    for min_sentiment in [0.4, 0.5, 0.6, 0.7]:
        good_sent_wins = wins[wins['sentiment_score'] >= min_sentiment]
        good_sent_losses = losses[losses['sentiment_score'] >= min_sentiment]
        total_good_sent = len(good_sent_wins) + len(good_sent_losses)
        if total_good_sent > 0:
            win_rate = len(good_sent_wins) / total_good_sent * 100
            print(f"  Sentiment >= {min_sentiment}: {len(good_sent_wins)}/{total_good_sent} wins ({win_rate:.1f}% win rate)")

def recommend_filters(wins, losses):
    """Recommend specific filter changes."""

    print(f"\n" + "=" * 80)
    print("🎯 RECOMMENDED FILTER IMPROVEMENTS")
    print("=" * 80)

    # Calculate optimal thresholds
    all_trades = pd.concat([wins, losses])

    # Find liquidity threshold that maximizes win rate while keeping volume
    best_liq_threshold = None
    best_liq_win_rate = 0
    for threshold in range(30000, 200000, 10000):
        filtered_wins = wins[wins['entry_liquidity_usd'] >= threshold]
        filtered_losses = losses[losses['entry_liquidity_usd'] >= threshold]
        total = len(filtered_wins) + len(filtered_losses)
        if total > 50:  # Need enough trades
            win_rate = len(filtered_wins) / total
            if win_rate > best_liq_win_rate:
                best_liq_win_rate = win_rate
                best_liq_threshold = threshold

    if best_liq_threshold:
        print(f"\n1. MIN_ENTRY_LIQUIDITY: Increase to ${best_liq_threshold:,}")
        print(f"   Expected win rate: {best_liq_win_rate*100:.1f}%")
        saved_losses = len(losses[losses['entry_liquidity_usd'] < best_liq_threshold])
        print(f"   Would avoid {saved_losses} losing trades")

    # Volume threshold
    best_vol_threshold = None
    best_vol_win_rate = 0
    for threshold in range(50000, 400000, 25000):
        filtered_wins = wins[wins['entry_volume_24h'] >= threshold]
        filtered_losses = losses[losses['entry_volume_24h'] >= threshold]
        total = len(filtered_wins) + len(filtered_losses)
        if total > 50:
            win_rate = len(filtered_wins) / total
            if win_rate > best_vol_win_rate:
                best_vol_win_rate = win_rate
                best_vol_threshold = threshold

    if best_vol_threshold:
        print(f"\n2. MIN_24H_VOLUME: Increase to ${best_vol_threshold:,}")
        print(f"   Expected win rate: {best_vol_win_rate*100:.1f}%")
        saved_losses = len(losses[losses['entry_volume_24h'] < best_vol_threshold])
        print(f"   Would avoid {saved_losses} losing trades")

    # Risk threshold
    best_risk = None
    best_risk_win_rate = 0
    for threshold in [0.25, 0.3, 0.35, 0.4, 0.45, 0.5]:
        filtered_wins = wins[wins['overall_risk_score'] <= threshold]
        filtered_losses = losses[losses['overall_risk_score'] <= threshold]
        total = len(filtered_wins) + len(filtered_losses)
        if total > 50:
            win_rate = len(filtered_wins) / total
            if win_rate > best_risk_win_rate:
                best_risk_win_rate = win_rate
                best_risk = threshold

    if best_risk:
        print(f"\n3. MAX_RISK_SCORE: Set to {best_risk}")
        print(f"   Expected win rate: {best_risk_win_rate*100:.1f}%")
        saved_losses = len(losses[losses['overall_risk_score'] > best_risk])
        print(f"   Would avoid {saved_losses} losing trades")

    print(f"\n💡 SUMMARY:")
    print(f"Current win rate: {len(wins)/(len(wins)+len(losses))*100:.1f}%")
    print(f"With recommended filters: ~{max(best_liq_win_rate, best_vol_win_rate, best_risk_win_rate)*100:.1f}%")
    print(f"\n⚠️  Trade-off: Fewer trades, but higher quality!")

if __name__ == '__main__':
    print("\n🔬 Loading 1,680 trades for analysis...")
    df = load_trades()

    print(f"✅ Loaded {len(df)} trades")

    # Analyze
    wins, losses = analyze_losses(df)
    find_optimization_opportunities(wins, losses)
    recommend_filters(wins, losses)

    print(f"\n" + "=" * 80)
    print("✅ Analysis complete!")
    print("=" * 80)
