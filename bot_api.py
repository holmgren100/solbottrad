#!/usr/bin/env python3
"""
Bot Control & Monitoring API för Claude Code
Exponerar bot-status, data, och kontroll via HTTP
"""

from flask import Flask, jsonify, request, send_file
from flask_httpauth import HTTPBasicAuth
import os
import json
from datetime import datetime
import pandas as pd
import psutil
import subprocess

app = Flask(__name__)
auth = HTTPBasicAuth()

# Security: Basic auth credentials
USERS = {
    "claude": "your_secure_password_here"  # Ändra detta!
}

@auth.verify_password
def verify_password(username, password):
    if username in USERS and USERS[username] == password:
        return username
    return None

# ============================================================================
# HEALTH & STATUS ENDPOINTS
# ============================================================================

@app.route('/health', methods=['GET'])
def health():
    """Health check - no auth needed"""
    return jsonify({"status": "ok", "timestamp": datetime.now().isoformat()})

@app.route('/api/status', methods=['GET'])
@auth.login_required
def bot_status():
    """Get bot status, positions, and performance"""
    try:
        # Check if bot is running
        bot_running = False
        bot_pid = None
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            cmdline = proc.info.get('cmdline', [])
            if cmdline and 'trading_bot' in ' '.join(cmdline):
                bot_running = True
                bot_pid = proc.info['pid']
                break

        # Read latest trades
        trades_csv = "/home/user/solbottrad/data/ml_trades.csv"
        positions = []
        stats = {}

        if os.path.exists(trades_csv):
            df = pd.read_csv(trades_csv)

            # Calculate stats
            stats = {
                "total_trades": len(df),
                "win_rate": (df['profit_pct'] > 0).sum() / len(df) * 100 if len(df) > 0 else 0,
                "avg_profit": df['profit_pct'].mean() if len(df) > 0 else 0,
                "total_pnl": df['profit_pct'].sum() if len(df) > 0 else 0,
                "best_trade": df['profit_pct'].max() if len(df) > 0 else 0,
                "worst_trade": df['profit_pct'].min() if len(df) > 0 else 0,
            }

            # Get recent trades (last 10)
            recent = df.tail(10).to_dict('records')
            positions = recent

        return jsonify({
            "bot_running": bot_running,
            "bot_pid": bot_pid,
            "timestamp": datetime.now().isoformat(),
            "stats": stats,
            "recent_trades": positions
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ============================================================================
# DATA ACCESS ENDPOINTS
# ============================================================================

@app.route('/api/data/trades', methods=['GET'])
@auth.login_required
def get_trades():
    """Get trades CSV data"""
    try:
        csv_path = "/home/user/solbottrad/data/ml_trades.csv"

        if not os.path.exists(csv_path):
            return jsonify({"error": "No trades data yet"}), 404

        # Query parameters
        limit = request.args.get('limit', type=int, default=100)
        format_type = request.args.get('format', 'json')

        df = pd.read_csv(csv_path)

        # Apply limit
        if limit:
            df = df.tail(limit)

        if format_type == 'csv':
            return send_file(csv_path, mimetype='text/csv')
        else:
            return jsonify({
                "count": len(df),
                "data": df.to_dict('records')
            })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/data/rejected', methods=['GET'])
@auth.login_required
def get_rejected():
    """Get rejected trades CSV data"""
    try:
        csv_path = "/home/user/solbottrad/data/rejected_trades.csv"

        if not os.path.exists(csv_path):
            return jsonify({"error": "No rejected trades data yet"}), 404

        limit = request.args.get('limit', type=int, default=100)
        format_type = request.args.get('format', 'json')

        df = pd.read_csv(csv_path)

        if limit:
            df = df.tail(limit)

        if format_type == 'csv':
            return send_file(csv_path, mimetype='text/csv')
        else:
            # Get rejection reason counts
            rejection_counts = df['Rejection Reason'].value_counts().to_dict()

            return jsonify({
                "count": len(df),
                "rejection_counts": rejection_counts,
                "data": df.to_dict('records')
            })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/data/logs', methods=['GET'])
@auth.login_required
def get_logs():
    """Get recent bot logs"""
    try:
        log_path = "/home/user/solbottrad/bot.log"

        if not os.path.exists(log_path):
            return jsonify({"error": "No log file found"}), 404

        lines = request.args.get('lines', type=int, default=100)
        level = request.args.get('level', 'all')  # all, error, warning, info

        # Read last N lines
        result = subprocess.run(
            ['tail', f'-{lines}', log_path],
            capture_output=True,
            text=True
        )

        log_lines = result.stdout.split('\n')

        # Filter by level if specified
        if level != 'all':
            log_lines = [l for l in log_lines if level.upper() in l]

        return jsonify({
            "lines": len(log_lines),
            "logs": log_lines
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ============================================================================
# ANALYSIS ENDPOINTS
# ============================================================================

@app.route('/api/analysis/session', methods=['GET'])
@auth.login_required
def analyze_session():
    """Analyze current trading session"""
    try:
        csv_path = "/home/user/solbottrad/data/ml_trades.csv"

        if not os.path.exists(csv_path):
            return jsonify({"error": "No trades data yet"}), 404

        df = pd.read_csv(csv_path)

        # Session analysis
        analysis = {
            "total_trades": len(df),
            "win_rate": (df['profit_pct'] > 0).sum() / len(df) * 100 if len(df) > 0 else 0,
            "avg_profit": float(df['profit_pct'].mean()) if len(df) > 0 else 0,
            "total_pnl": float(df['profit_pct'].sum()) if len(df) > 0 else 0,

            # Exit analysis
            "exit_reasons": df['exit_reason'].value_counts().to_dict() if 'exit_reason' in df.columns else {},

            # Entry analysis
            "entry_reasons": df['entry_filter_reason'].value_counts().to_dict() if 'entry_filter_reason' in df.columns else {},

            # Nuclear stops
            "nuclear_stops": {
                "count": len(df[df['exit_reason'].str.contains('nuclear', na=False)]),
                "avg_loss": float(df[df['exit_reason'].str.contains('nuclear', na=False)]['profit_pct'].mean()) if len(df[df['exit_reason'].str.contains('nuclear', na=False)]) > 0 else 0
            },

            # Top performers
            "top_winners": df.nlargest(5, 'profit_pct')[['symbol', 'profit_pct', 'exit_reason']].to_dict('records'),
            "top_losers": df.nsmallest(5, 'profit_pct')[['symbol', 'profit_pct', 'exit_reason']].to_dict('records'),
        }

        return jsonify(analysis)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ============================================================================
# CONTROL ENDPOINTS (Optional - implement with caution!)
# ============================================================================

@app.route('/api/control/stop', methods=['POST'])
@auth.login_required
def stop_bot():
    """Stop the trading bot (DANGEROUS!)"""
    # TODO: Implement safe bot shutdown
    return jsonify({"error": "Not implemented - use manual stop for safety"}), 501

@app.route('/api/control/config', methods=['GET'])
@auth.login_required
def get_config():
    """Get current bot configuration"""
    try:
        config_path = "/home/user/solbottrad/config.json"

        if not os.path.exists(config_path):
            return jsonify({"error": "Config not found"}), 404

        with open(config_path, 'r') as f:
            config = json.load(f)

        # Redact sensitive data
        if 'api_keys' in config:
            config['api_keys'] = {k: "***REDACTED***" for k in config['api_keys']}

        return jsonify(config)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ============================================================================
# RUN SERVER
# ============================================================================

if __name__ == '__main__':
    # Production: Use gunicorn or uwsgi
    # Development: Use Flask dev server

    port = int(os.environ.get('API_PORT', 8765))

    print("=" * 60)
    print("🤖 Bot Control API Started!")
    print("=" * 60)
    print(f"📡 Listening on: http://0.0.0.0:{port}")
    print(f"🔒 Authentication: Basic Auth required")
    print(f"📊 Endpoints:")
    print(f"   GET  /health                   - Health check (no auth)")
    print(f"   GET  /api/status                - Bot status & stats")
    print(f"   GET  /api/data/trades          - Get trades CSV")
    print(f"   GET  /api/data/rejected        - Get rejected trades")
    print(f"   GET  /api/data/logs            - Get recent logs")
    print(f"   GET  /api/analysis/session     - Session analysis")
    print(f"   GET  /api/control/config       - Get bot config")
    print("=" * 60)
    print("⚠️  WARNING: Bind to 0.0.0.0 = PUBLIC ACCESS!")
    print("💡 Use nginx reverse proxy with SSL for production")
    print("=" * 60)

    app.run(host='0.0.0.0', port=port, debug=False)
