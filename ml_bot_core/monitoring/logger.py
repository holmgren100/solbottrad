"""
Simple logging configuration for ML Bot Core.

Provides consistent logging across all core modules.
"""

import logging
import sys
from typing import Optional


def get_logger(name: str, level: Optional[int] = None) -> logging.Logger:
    """
    Get a configured logger instance.

    Args:
        name: Logger name (typically __name__)
        level: Optional log level (defaults to INFO)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Set level
    if level is None:
        level = logging.INFO

    logger.setLevel(level)

    # Prevent propagation to root logger (avoid duplicate logging)
    logger.propagate = False

    # Add handler if none exists
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)

        # Format: [2025-12-18 14:30:15] [INFO] [module] Message
        formatter = logging.Formatter(
            '[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)

        logger.addHandler(handler)

    return logger


def configure_logging(level: int = logging.INFO, log_file: Optional[str] = None):
    """
    Configure logging for the entire application.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file to write logs to
    """
    handlers = [logging.StreamHandler(sys.stdout)]

    if log_file:
        handlers.append(logging.FileHandler(log_file))

    logging.basicConfig(
        level=level,
        format='[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=handlers
    )

    logging.info("Logging configured")
