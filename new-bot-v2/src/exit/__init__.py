"""
Exit Logic Package - Know When to Exit

Contains all exit decision modules:
- WeaknessDetector: Detects momentum weakening (70+ score = exit)
- StopLossManager: Hard stop (-25%) and trailing stop (+100%)
- TimeExit: Cuts stagnant (3m, <5%) and failed (10m, red) positions
- ExitManager: Main coordinator for all exit decisions

Used by: Main orchestrator (Phase 4)
"""

from src.exit.weakness_detector import WeaknessDetector
from src.exit.stop_loss_manager import StopLossManager
from src.exit.time_exit import TimeExit
from src.exit.exit_manager import ExitManager

__all__ = [
    "WeaknessDetector",
    "StopLossManager",
    "TimeExit",
    "ExitManager",
]
