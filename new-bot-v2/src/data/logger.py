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
                "entry_price",
                "exit_price",
                "profit_pct",
                "profit_sol",
                "hold_time_minutes",
                "exit_reason",
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
                "rejection_stage",  # "SAFETY", "MOMENTUM", "TREND", "FOMO"
                "rejection_reason",
                "momentum_score",
                "macd_score",
                "volume_score",
                "rsi_score",
                "macd_histogram",
                "rsi_value",
                "volume_velocity",
                "price",
                "liquidity_usd",
                "volume_24h",
                "mint_revoked",
                "lp_burned",
            ]

            with open(self.rejected_trades_csv, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(headers)

            logger.info(f"Created {self.rejected_trades_csv}")

    def log_trade(self, trade_data: Dict):
        """
        Log a successful trade to ml_trades.csv.

        Args:
            trade_data: Dict containing:
                {
                    "token_address": str,
                    "symbol": str,
                    "entry_price": float,
                    "exit_price": float,
                    "profit_pct": float,
                    "profit_sol": float,
                    "hold_time_minutes": int,
                    "exit_reason": str,
                    "momentum_score": int,
                    "macd_score": int,
                    "volume_score": int,
                    "rsi_score": int,
                    "pullback_score": int,
                    "macd_histogram": float,
                    "rsi_value": float,
                    "volume_velocity": float,
                    "liquidity_usd": float,
                    "volume_24h": float,
                    "price_change_5m": float,
                    "buys_5m": int,
                    "sells_5m": int,
                    "mint_revoked": bool,
                    "lp_burned": bool,
                }
        """
        try:
            row = [
                datetime.now().isoformat(),
                trade_data.get("token_address", ""),
                trade_data.get("symbol", ""),
                trade_data.get("entry_price", 0),
                trade_data.get("exit_price", 0),
                trade_data.get("profit_pct", 0),
                trade_data.get("profit_sol", 0),
                trade_data.get("hold_time_minutes", 0),
                trade_data.get("exit_reason", ""),
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
        Log a rejected token to rejected_trades.csv.

        Args:
            rejection_data: Dict containing:
                {
                    "token_address": str,
                    "symbol": str,
                    "rejection_stage": str,  # "SAFETY", "MOMENTUM", "TREND", "FOMO"
                    "rejection_reason": str,
                    "momentum_score": int,
                    "macd_score": int,
                    "volume_score": int,
                    "rsi_score": int,
                    "macd_histogram": float,
                    "rsi_value": float,
                    "volume_velocity": float,
                    "price": float,
                    "liquidity_usd": float,
                    "volume_24h": float,
                    "mint_revoked": bool,
                    "lp_burned": bool,
                }
        """
        try:
            row = [
                datetime.now().isoformat(),
                rejection_data.get("token_address", ""),
                rejection_data.get("symbol", ""),
                rejection_data.get("rejection_stage", ""),
                rejection_data.get("rejection_reason", ""),
                rejection_data.get("momentum_score", 0),
                rejection_data.get("macd_score", 0),
                rejection_data.get("volume_score", 0),
                rejection_data.get("rsi_score", 0),
                rejection_data.get("macd_histogram", 0),
                rejection_data.get("rsi_value", 0),
                rejection_data.get("volume_velocity", 0),
                rejection_data.get("price", 0),
                rejection_data.get("liquidity_usd", 0),
                rejection_data.get("volume_24h", 0),
                rejection_data.get("mint_revoked", False),
                rejection_data.get("lp_burned", False),
            ]

            with open(self.rejected_trades_csv, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(row)

            logger.info(
                f"❌ Logged rejection: {rejection_data.get('symbol')} "
                f"({rejection_data.get('rejection_stage')})"
            )

        except Exception as e:
            logger.error(f"Error logging rejection: {e}")

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
