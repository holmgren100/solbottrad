import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

_DEFAULT_LOG_DIR = Path("logs")
_DEFAULT_LOG_DIR.mkdir(parents=True, exist_ok=True)
_DEFAULT_LOG_FILE = _DEFAULT_LOG_DIR / "bot.log"

def setup_logger(
    name: str = "bot",
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    max_bytes: int = 5_000_000,
    backup_count: int = 5,
    propagate: bool = False,
) -> logging.Logger:
    """
    Create or return a configured logger.
    - Accepts optional log_file to allow per-module files.
    - Uses RotatingFileHandler with delay=True to reduce Windows file locking.
    - Idempotent: won’t attach duplicate handlers on repeated calls.
    """
    logger = logging.getLogger(name)

    # If already configured, just return it
    if getattr(logger, "_configured", False):
        return logger

    logger.setLevel(level)
    logger.propagate = propagate

    # Clean existing handlers (avoid duplicates/locks)
    for h in list(logger.handlers):
        logger.removeHandler(h)
        try:
            h.close()
        except Exception:
            pass

    # Format
    fmt = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

    # Determine log file
    file_path = Path(log_file) if log_file else _DEFAULT_LOG_FILE
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # File handler (delay=True to open file lazily; helps on Windows)
    fh = RotatingFileHandler(
        filename=file_path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
        delay=True,
    )
    fh.setFormatter(fmt)

    # Console handler
    ch = logging.StreamHandler()
    ch.setFormatter(fmt)

    logger.addHandler(fh)
    logger.addHandler(ch)

    logger._configured = True
    return logger

def get_logger(name: str) -> logging.Logger:
    """Convenience accessor if you want to standardize retrieval."""
    return setup_logger(name=name)