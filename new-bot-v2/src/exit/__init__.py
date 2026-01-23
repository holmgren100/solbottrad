"""
Exit Logic Package - Know When to Exit

Contains all exit decision modules:
- WeaknessDetector: Detects momentum weakening (60+ score = exit)
- StopManager: Hard stop (-25%) and trailing stop (+100%)
- TimeExit: Cuts stagnant (3m, <5%) and failed (10m, red) positions

Used by: Main orchestrator (Phase 4)
"""

from src.exit.weakness_detector import WeaknessDetector
from src.exit.stop_manager import StopManager
from src.exit.time_exit import TimeExit

__all__ = [
    "WeaknessDetector",
    "StopManager",
    "TimeExit",
]
