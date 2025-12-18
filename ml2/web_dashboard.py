"""
Flask web server for the Solana Trading Bot dashboard.
Serves the HTML dashboard with live data from the log file.

Run with: python web_dashboard.py
Then open: http://localhost:5000
"""

from flask import Flask, jsonify, send_file
import os
import sys
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from src.config import settings
except:
    settings = None

app = Flask(__name__)

def parse_log_for_positions():
    """Parse log file to find current positions."""
    log_file = 'trading_bot.log'
    positions = {}

    if not os.path.exists(log_file):
        return positions

    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        for line in lines:
            # Look for buy trades
            if '[PAPER] BUY' in line:
                parts = line.split()
                for i, part in enumerate(parts):
                    if part == 'BUY' and i+1 < len(parts):
                        token = parts[i+1]
                        # Extract price
                        for j in range(i, min(i+10, len(parts))):
                            if parts[j].startswith('$') and '.' in parts[j]:
                                try:
                                    price = float(parts[j].replace('$', '').replace(',', ''))
                                    # Extract size
                                    for k in range(j, min(j+5, len(parts))):
                                        if parts[k].startswith('$') and parts[k] != parts[j]:
                                            try:
                                                size = float(parts[k].replace('$', '').replace(',', ''))
                                                positions[token] = {
                                                    'token': token[:12] + '...',
                                                    'entry_price': price,
                                                    'size': size,
                                                    'current_price': price,
                                                    'pnl_pct': 0.0
                                                }
                                                break
                                            except:
                                                pass
                                    break
                                except:
                                    pass
                        break

            # Look for sell trades (remove from positions)
            elif '[PAPER] SELL' in line:
                parts = line.split()
                for i, part in enumerate(parts):
                    if part == 'SELL' and i+1 < len(parts):
                        token = parts[i+1]
                        if token in positions:
                            del positions[token]
                        break

        return positions
    except Exception as e:
        print(f"Error parsing log: {e}")
        return {}

def get_recent_trades(limit=10):
    """Get recent trades from log file."""
    log_file = 'trading_bot.log'
    trades = []

    if not os.path.exists(log_file):
        return trades

    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        for line in reversed(lines):
            if '[PAPER] BUY' in line or '[PAPER] SELL' in line:
                # Extract timestamp
                timestamp = line.split(' - ')[0] if ' - ' in line else ''
                action = 'BUY' if 'BUY' in line else 'SELL'

                # Try to extract token and price
                parts = line.split()
                token = ""
                price = ""

                for i, part in enumerate(parts):
                    if part in ['BUY', 'SELL'] and i+1 < len(parts):
                        token = parts[i+1][:12] + '...'
                        # Find price
                        for j in range(i, min(i+10, len(parts))):
                            if parts[j].startswith('$') and '.' in parts[j]:
                                price = parts[j]
                                break
                        break

                trades.append({
                    'timestamp': timestamp.split(' ')[-1] if timestamp else '',
                    'action': action,
                    'token': token,
                    'price': price
                })

                if len(trades) >= limit:
                    break

        return trades
    except Exception as e:
        print(f"Error getting trades: {e}")
        return []

@app.route('/')
def index():
    """Serve the dashboard HTML."""
    return send_file('dashboard_live.html')

@app.route('/api/portfolio')
def get_portfolio():
    """API endpoint for portfolio data."""
    positions = parse_log_for_positions()
    total_invested = sum(pos['size'] for pos in positions.values())
    initial_capital = 1000.0
    cash = initial_capital - total_invested
    total_value = initial_capital  # In paper trading, P&L is 0 for now
    total_pnl = total_value - initial_capital

    return jsonify({
        'portfolio_value': total_value,
        'cash': cash,
        'invested': total_invested,
        'total_pnl': total_pnl,
        'total_return_pct': (total_pnl / initial_capital * 100) if initial_capital > 0 else 0,
        'positions_count': len(positions),
        'positions': list(positions.values()),
        'recent_trades': get_recent_trades(10)
    })

@app.route('/api/settings')
def get_settings():
    """API endpoint for bot settings."""
    if settings:
        return jsonify({
            'mode': 'Paper Trading' if settings.is_paper_trading() else 'Live Trading',
            'stop_loss': settings.risk.stop_loss_percent,
            'take_profit': settings.risk.take_profit_percent,
            'max_position': settings.trading.max_position_size,
            'max_positions': settings.risk.max_open_positions
        })
    else:
        return jsonify({
            'mode': 'Unknown',
            'stop_loss': 0,
            'take_profit': 0,
            'max_position': 0,
            'max_positions': 0
        })

if __name__ == '__main__':
    print("=" * 70)
    print("🤖 Solana Trading Bot - Web Dashboard")
    print("=" * 70)
    print("\n✅ Starting Flask server...")
    print("\n📊 Dashboard will be available at:")
    print("   → http://localhost:5000")
    print("   → http://127.0.0.1:5000")
    print("\n💡 Keep this running and open the URL in your browser!")
    print("\n⚠️  Press Ctrl+C to stop the server")
    print("=" * 70)
    print()

    app.run(debug=False, host='0.0.0.0', port=5000)
