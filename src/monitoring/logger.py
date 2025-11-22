import logging
import os
from datetime import datetime

def setup_logger(name: str = 'trading_bot', log_file: str = 'trading_bot.log') -> logging.Logger:
    """Setup logger with file and console handlers"""

    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # Prevent duplicate handlers
    if logger.handlers:
        return logger

    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # File handler - ensure it's created in the current working directory
    file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)
    logger.addHandler(file_handler)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(levelname)s: %(message)s')
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # Test that logging works
    logger.info(f"Logger initialized - Log file: {os.path.abspath(log_file)}")

    return logger

def log_trade(logger: logging.Logger, action: str, symbol: str, amount: float, price: float, result: dict):
    """Log trade execution with details"""
    logger.info(f"TRADE EXECUTED: {action.upper()} {symbol}")
    logger.info(f"  Amount: ${amount:.2f} @ ${price:.8f}")
    logger.info(f"  Result: {result}")

def log_signal(logger: logging.Logger, symbol: str, signal_type: str, confidence: float):
    """Log trading signal"""
    logger.info(f"SIGNAL: {signal_type.upper()} {symbol} (confidence: {confidence:.2f})")

def log_error(logger: logging.Logger, error: Exception, context: str = ""):
    """Log error with context"""
    logger.error(f"ERROR in {context}: {type(error).__name__}: {str(error)}", exc_info=True)
