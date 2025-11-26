"""
Logging configuration for the trading bot.
Provides structured logging to file and console.
"""

import logging
import sys
from pathlib import Path
from typing import Optional


class FlushFileHandler(logging.FileHandler):
    """File handler that flushes after every log write."""
    def emit(self, record):
        super().emit(record)
        self.flush()


def setup_logger(
    name: str = 'trading_bot',
    log_file: Optional[str] = None,
    log_level: str = 'INFO'
) -> logging.Logger:
    """
    Set up a logger with file and console handlers.

    This configures the ROOT logger so all child loggers inherit the handlers.

    Args:
        name: Logger name (ignored, kept for compatibility)
        log_file: Path to log file (optional)
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

    Returns:
        Configured logger instance
    """
    # Get the root logger so ALL loggers inherit these handlers
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))

    # Prevent duplicate handlers
    if root_logger.handlers:
        return root_logger

    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    simple_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    root_logger.addHandler(console_handler)

    # File handler with auto-flush for real-time logging
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = FlushFileHandler(log_file, mode='a', encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(detailed_formatter)
        root_logger.addHandler(file_handler)

        # Write initial log entry to verify file is working
        root_logger.info("=" * 60)
        root_logger.info("Trading Bot Log File Initialized")
        root_logger.info("=" * 60)

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance.

    Args:
        name: Logger name

    Returns:
        Logger instance
    """
    return logging.getLogger(name)
