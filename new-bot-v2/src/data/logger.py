"""
Data Logger - CSV Export for ML Analysis

Logs all trades and rejections to CSV files for:
- AI model training
- Strategy optimization
- Performance analysis

Files:
- ml_trades.csv: Successful trades with full details
- rejected_trades.csv: Rejected tokens with reasons
"""

import csv
import logging
import os
from datetime import datetime
from typing import Dict
from pathlib import Path

from config.parameters import (
    ML_TRADES_CSV,
    REJECTED_TRADES_CSV
)

logger = logging.getLogger(__name__)


class DataLogger:
    """
    CSV logger for trade data and rejections.

    All data is logged for future ML analysis and optimization.
    """

    def __init__(self):
        """Initialize data logger and ensure CSV files exist."""
        self.ml_trades_csv = ML_TRADES_CSV
        self.rejected_trades_csv = REJECTED_TRADES_CSV

        # Create data directory if it doesn't exist
        Path("data").mkdir(exist_ok=True)

        # Initialize CSV files with headers
        self._init_ml_trades_csv()
        self._init_rejected_trades_csv()

        logger.info("Data Logger initialized")

    def _init_ml_trades_csv(self):
        """Initialize ml_trades.csv with headers if it doesn't exist."""
        if not os.path.exists(self.ml_trades_csv):
            headers = [
                "timestamp",
                "token_address",
                "symbol",
                "action",  # "ENTRY" or "EXIT"
                "entry_price",
                "exit_price",
                "size_sol",
                "profit_pct",
                "profit_sol",
                "peak_profit_pct",
                "hold_time_minutes",
                "exit_reason",
                "exit_type",  # "hard_stop", "trailing_stop", "weakness", "time", etc.
                # Entry signals
                "momentum_score",
                "macd_score",
                "volume_score",
                "rsi_score",
                "pullback_score",
                "macd_histogram",
                "rsi_value",
                "volume_velocity",
                # Market data
                "liquidity_usd",
                "volume_24h",
                "price_change_5m",
                "buys_5m",
                "sells_5m",
                # Safety checks
                "mint_revoked",
                "lp_burned",
                # Position management
                "breakeven_triggered",
                "pyramid_1_triggered",
                "pyramid_2_triggered",
                "partial_1_taken",
                "partial_2_taken",
                "partials_count",
                # Exit analysis
                "weakness_score_at_exit",
                "win",  # True if profit > 0
            ]

            with open(self.ml_trades_csv, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(headers)

            logger.info(f"Created {self.ml_trades_csv}")

    def _init_rejected_trades_csv(self):
        """Initialize rejected_trades.csv with headers if it doesn't exist."""
        if not os.path.exists(self.rejected_trades_csv):
            headers = [
                "timestamp",
                "token_address",
                "symbol",
                "name",
                "rejection_stage",  # "SAFETY", "MOMENTUM", "TREND", "FOMO"
                "rejection_reason",
                "momentum_score",
                "macd_score",
                "volume_score",
                "rsi_score",
                "pullback_score",
                "macd_histogram",
                "rsi_value",
                "volume_velocity",
                "price",
                "price_change_5m",
                "price_change_1h",
                "liquidity_usd",
                "volume_5m",
                "volume_1h",
                "volume_24h",
                "buys_5m",
                "sells_5m",
                "buy_sell_ratio",
                "mint_revoked",
                "lp_burned",
                "holder_count",
                "top_10_holders_pct",
                "market_cap_usd",
                "data_source",  # Which API provided data
                "rejection_count",  # Times rejected (for tracking patterns)
            ]

            with open(self.rejected_trades_csv, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(headers)

            logger.info(f"Created {self.rejected_trades_csv}")

    def log_trade(self, trade_data: Dict):
        """
        Log a trade action (entry or exit) to ml_trades.csv.

        Enhanced to include position management data.

        Args:
            trade_data: Dict containing all trade data including
                        entry signals, market data, position management, etc.
        """
        try:
            action = trade_data.get("action", "EXIT")
            profit_pct = trade_data.get("profit_pct", trade_data.get("pnl_percent", 0))

            row = [
                datetime.now().isoformat(),
                trade_data.get("token_address", ""),
                trade_data.get("symbol", ""),
                action,
                trade_data.get("entry_price", 0),
                trade_data.get("exit_price", trade_data.get("price", 0)),
                trade_data.get("size_sol", 0),
                profit_pct,
                trade_data.get("profit_sol", trade_data.get("pnl_sol", 0)),
                trade_data.get("peak_profit_pct", 0),
                trade_data.get("hold_time_minutes", 0),
                trade_data.get("exit_reason", trade_data.get("reason", "")),
                trade_data.get("exit_type", ""),
                trade_data.get("momentum_score", 0),
                trade_data.get("macd_score", 0),
                trade_data.get("volume_score", 0),
                trade_data.get("rsi_score", 0),
                trade_data.get("pullback_score", 0),
                trade_data.get("macd_histogram", 0),
                trade_data.get("rsi_value", 0),
                trade_data.get("volume_velocity", 0),
                trade_data.get("liquidity_usd", 0),
                trade_data.get("volume_24h", 0),
                trade_data.get("price_change_5m", 0),
                trade_data.get("buys_5m", 0),
                trade_data.get("sells_5m", 0),
                trade_data.get("mint_revoked", False),
                trade_data.get("lp_burned", False),
                # Position management
                trade_data.get("breakeven_triggered", False),
                trade_data.get("pyramid_1_triggered", False),
                trade_data.get("pyramid_2_triggered", False),
                trade_data.get("partial_1_taken", False),
                trade_data.get("partial_2_taken", False),
                trade_data.get("partials_count", 0),
                # Exit analysis
                trade_data.get("weakness_score_at_exit", 0),
                profit_pct > 0,  # win = True if profit > 0
            ]

            with open(self.ml_trades_csv, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(row)

            logger.info(
                f"✅ Logged trade: {trade_data.get('symbol')} "
                f"({trade_data.get('profit_pct', 0):+.1f}%)"
            )

        except Exception as e:
            logger.error(f"Error logging trade: {e}")

    def log_rejected(self, rejection_data: Dict):
        """
        Log a rejected token to rejected_trades.csv with ENHANCED DATA.

        Args:
            rejection_data: Dict containing full token data for analysis
        """
        try:
            # Calculate buy/sell ratio
            buys = rejection_data.get("buys", rejection_data.get("buys_5m", 0))
            sells = rejection_data.get("sells", rejection_data.get("sells_5m", 0))
            buy_sell_ratio = buys / sells if sells > 0 else 0

            row = [
                datetime.now().isoformat(),
                rejection_data.get("token_address", rejection_data.get("address", "")),
                rejection_data.get("symbol", ""),
                rejection_data.get("name", ""),
                rejection_data.get("rejection_stage", ""),
                rejection_data.get("rejection_reason", ""),
                rejection_data.get("momentum_score", 0),
                rejection_data.get("macd_score", 0),
                rejection_data.get("volume_score", 0),
                rejection_data.get("rsi_score", 0),
                rejection_data.get("pullback_score", 0),
                rejection_data.get("macd_histogram", 0),
                rejection_data.get("rsi_value", rejection_data.get("rsi", 0)),
                rejection_data.get("volume_velocity", 0),
                rejection_data.get("price", 0),
                rejection_data.get("price_change_5m", 0),
                rejection_data.get("price_change_1h", 0),
                rejection_data.get("liquidity_usd", rejection_data.get("liquidity", 0)),
                rejection_data.get("volume_5m", 0),
                rejection_data.get("volume_1h", 0),
                rejection_data.get("volume_24h", 0),
                buys,
                sells,
                buy_sell_ratio,
                rejection_data.get("mint_revoked", False),
                rejection_data.get("lp_burned", False),
                rejection_data.get("holder_count", 0),
                rejection_data.get("top_10_holders_pct", 0),
                rejection_data.get("market_cap_usd", 0),
                rejection_data.get("data_source", "unknown"),
                rejection_data.get("rejection_count", 1),
            ]

            with open(self.rejected_trades_csv, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(row)

            logger.info(
                f"❌ Logged rejection: {rejection_data.get('symbol')} "
                f"({rejection_data.get('rejection_stage')}) - "
                f"{rejection_data.get('rejection_reason')}"
            )

        except Exception as e:
            logger.error(f"Error logging rejection: {e}")

    def log_rejection(self, token_address: str, stage: str, reason: str):
        """
        Simplified rejection logging (backward compatibility wrapper).

        Args:
            token_address: Token address
            stage: Rejection stage (SAFETY, MOMENTUM, TREND, FOMO)
            reason: Rejection reason
        """
        rejection_data = {
            "token_address": token_address,
            "symbol": token_address[:8] + "...",
            "rejection_stage": stage,
            "rejection_reason": reason,
            "momentum_score": 0,
            "macd_score": 0,
            "volume_score": 0,
            "rsi_score": 0,
            "macd_histogram": 0,
            "rsi_value": 0,
            "volume_velocity": 0,
            "price": 0,
            "liquidity_usd": 0,
            "volume_24h": 0,
            "mint_revoked": False,
            "lp_burned": False,
        }
        self.log_rejected(rejection_data)

    def get_trade_count(self) -> int:
        """Get total number of trades logged."""
        try:
            if not os.path.exists(self.ml_trades_csv):
                return 0

            with open(self.ml_trades_csv, 'r') as f:
                return sum(1 for _ in f) - 1  # -1 for header

        except Exception as e:
            logger.error(f"Error getting trade count: {e}")
            return 0

    def get_rejection_count(self) -> int:
        """Get total number of rejections logged."""
        try:
            if not os.path.exists(self.rejected_trades_csv):
                return 0

            with open(self.rejected_trades_csv, 'r') as f:
                return sum(1 for _ in f) - 1  # -1 for header

        except Exception as e:
            logger.error(f"Error getting rejection count: {e}")
            return 0

    def get_today_trades(self) -> list:
        """
        Get all trades from today for daily summary.

        Returns:
            List of trade dicts
        """
        try:
            if not os.path.exists(self.ml_trades_csv):
                return []

            today = datetime.now().date()
            today_trades = []

            with open(self.ml_trades_csv, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Parse timestamp
                    timestamp = row.get("timestamp", "")
                    if timestamp:
                        trade_date = datetime.fromisoformat(timestamp).date()
                        if trade_date == today and row.get("action") == "EXIT":
                            today_trades.append(row)

            return today_trades

        except Exception as e:
            logger.error(f"Error getting today's trades: {e}")
            return []

    def calculate_stats(self, trades: list) -> Dict:
        """
        Calculate statistics from trade list.

        Args:
            trades: List of trade dicts

        Returns:
            Dict with stats (total_trades, wins, losses, win_rate, etc.)
        """
        try:
            if not trades:
                return {
                    "total_trades": 0,
                    "wins": 0,
                    "losses": 0,
                    "win_rate": 0,
                    "total_pnl": 0,
                    "total_pnl_sol": 0,
                    "best_trade": 0,
                    "worst_trade": 0,
                    "avg_duration": 0,
                    "big_winners": 0,
                    "breakeven_count": 0,
                    "pyramid_count": 0
                }

            total_trades = len(trades)
            wins = 0
            losses = 0
            total_pnl = 0
            total_pnl_sol = 0
            best_trade = -100
            worst_trade = 100
            total_duration = 0
            big_winners = 0
            breakeven_count = 0
            pyramid_count = 0

            for trade in trades:
                # PnL
                pnl = float(trade.get("profit_pct", 0))
                pnl_sol = float(trade.get("profit_sol", 0))

                total_pnl += pnl
                total_pnl_sol += pnl_sol

                if pnl > 0:
                    wins += 1
                else:
                    losses += 1

                if pnl > best_trade:
                    best_trade = pnl

                if pnl < worst_trade:
                    worst_trade = pnl

                # Big winners (500%+)
                if pnl >= 500:
                    big_winners += 1

                # Duration
                duration = int(trade.get("hold_time_minutes", 0))
                total_duration += duration

                # Position management
                if trade.get("breakeven_triggered", "False") == "True":
                    breakeven_count += 1

                if (trade.get("pyramid_1_triggered", "False") == "True" or
                    trade.get("pyramid_2_triggered", "False") == "True"):
                    pyramid_count += 1

            win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
            avg_duration = total_duration // total_trades if total_trades > 0 else 0

            return {
                "total_trades": total_trades,
                "wins": wins,
                "losses": losses,
                "win_rate": win_rate,
                "total_pnl": total_pnl,
                "total_pnl_sol": total_pnl_sol,
                "best_trade": best_trade,
                "worst_trade": worst_trade,
                "avg_duration": avg_duration,
                "big_winners": big_winners,
                "breakeven_count": breakeven_count,
                "pyramid_count": pyramid_count
            }

        except Exception as e:
            logger.error(f"Error calculating stats: {e}")
            return {}


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    data_logger = DataLogger()

    # Example trade
    trade_data = {
        "token_address": "ABC123...",
        "symbol": "TEST",
        "entry_price": 0.15,
        "exit_price": 0.20,
        "profit_pct": 33.3,
        "profit_sol": 0.05,
        "hold_time_minutes": 45,
        "exit_reason": "Take profit +500%",
        "momentum_score": 85,
        "macd_score": 40,
        "volume_score": 30,
        "rsi_score": 15,
        "pullback_score": 0,
        "macd_histogram": 0.0025,
        "rsi_value": 65,
        "volume_velocity": 4.5,
        "liquidity_usd": 75000,
        "volume_24h": 500000,
        "price_change_5m": 5.2,
        "buys_5m": 150,
        "sells_5m": 80,
        "mint_revoked": True,
        "lp_burned": True,
    }

    data_logger.log_trade(trade_data)

    # Example rejection
    rejection_data = {
        "token_address": "XYZ789...",
        "symbol": "FAIL",
        "rejection_stage": "SAFETY",
        "rejection_reason": "LP not burned",
        "momentum_score": 75,
        "macd_score": 35,
        "volume_score": 30,
        "rsi_score": 10,
        "macd_histogram": 0.0020,
        "rsi_value": 58,
        "volume_velocity": 3.8,
        "price": 0.12,
        "liquidity_usd": 45000,
        "volume_24h": 300000,
        "mint_revoked": True,
        "lp_burned": False,
    }

    data_logger.log_rejected(rejection_data)

    # Get counts
    print(f"\nTrades logged: {data_logger.get_trade_count()}")
    print(f"Rejections logged: {data_logger.get_rejection_count()}")
