"""
Exit Manager - Main Exit Decision Coordinator

Coordinates all exit logic in priority order:
1. HARD STOP (Highest priority - capital preservation!)
2. WEAKNESS SCORE (Exit on facts - momentum dying)
3. TIME-BASED EXIT (Dead price - no action)

Returns unified exit decision with clear reasons.
"""

import logging
from typing import Dict, Optional

from src.exit.stop_loss_manager import StopLossManager
from src.exit.weakness_detector import WeaknessDetector
from src.exit.time_exit import TimeExit

logger = logging.getLogger(__name__)


class ExitManager:
    """
    Main coordinator for all exit decisions.

    Checks exits in priority order and returns highest priority signal.
    """

    def __init__(self):
        """Initialize exit manager with all exit modules."""
        self.stop_loss_manager = StopLossManager()
        self.weakness_detector = WeaknessDetector()
        self.time_exit = TimeExit()

        logger.info("Exit Manager initialized - coordinating all exit logic")

    def check_exit_conditions(
        self,
        position,
        token_data: Optional[Dict] = None
    ) -> Dict:
        """
        Check all exit conditions in priority order.

        Priority order:
        1. Hard/trailing stop (CRITICAL - capital preservation!)
        2. Weakness score (facts-based exit)
        3. Time-based exit (dead price)
        4. No exit (position healthy)

        Args:
            position: Position object
            token_data: Optional dict with prices, candles, token_address

        Returns:
            {
                "should_exit": bool,
                "exit_type": str,  # 'hard_stop', 'trailing_stop', 'weakness', 'time', None
                "reason": str,
                "details": dict,  # Additional info from specific check
                "priority": int   # Lower = higher priority
            }
        """
        try:
            # PRIORITY 1: Check hard/trailing stop (ALWAYS CHECK FIRST!)
            stop_result = self.stop_loss_manager.check_stops(position)

            if stop_result["hit"]:
                exit_type = f"{stop_result['stop_type']}_stop"

                logger.warning(
                    f"🛑 EXIT SIGNAL: {exit_type} for {position.symbol}"
                )
                logger.warning(f"   {stop_result['reason']}")

                return {
                    "should_exit": True,
                    "exit_type": exit_type,
                    "reason": stop_result["reason"],
                    "details": stop_result,
                    "priority": 1
                }

            # PRIORITY 2: Check weakness score (if token_data provided)
            if token_data:
                weakness_result = self.weakness_detector.calculate_score(token_data)

                if weakness_result["should_exit"]:
                    logger.warning(
                        f"⚠️ EXIT SIGNAL: weakness for {position.symbol}"
                    )
                    logger.warning(f"   {weakness_result['reason']}")

                    return {
                        "should_exit": True,
                        "exit_type": "weakness",
                        "reason": weakness_result["reason"],
                        "details": weakness_result,
                        "priority": 2
                    }

            # PRIORITY 3: Check time-based exit
            time_result = self.time_exit.should_exit(position)

            if time_result["should_exit"]:
                logger.warning(
                    f"⏱️ EXIT SIGNAL: time exit for {position.symbol}"
                )
                logger.warning(f"   {time_result['reason']}")

                return {
                    "should_exit": True,
                    "exit_type": "time",
                    "reason": time_result["reason"],
                    "details": time_result,
                    "priority": 3
                }

            # NO EXIT: Position is healthy
            logger.debug(f"✅ No exit signals for {position.symbol} - position healthy")

            return {
                "should_exit": False,
                "exit_type": None,
                "reason": "Position healthy - all checks passed",
                "details": {
                    "stop_check": stop_result,
                    "weakness_check": weakness_result if token_data else None,
                    "time_check": time_result
                },
                "priority": 999
            }

        except Exception as e:
            logger.error(f"Error checking exit conditions: {e}")

            # On error, default to checking hard stop only (safety first!)
            stop_result = self.stop_loss_manager.check_stops(position)

            if stop_result["hit"]:
                return {
                    "should_exit": True,
                    "exit_type": f"{stop_result['stop_type']}_stop",
                    "reason": f"Error in checks - hard stop triggered: {stop_result['reason']}",
                    "details": {"error": str(e), "stop": stop_result},
                    "priority": 1
                }
            else:
                return {
                    "should_exit": False,
                    "exit_type": None,
                    "reason": f"Error in checks - defaulting to no exit: {e}",
                    "details": {"error": str(e)},
                    "priority": 999
                }

    def _prioritize_exit_signals(self, signals: list) -> Dict:
        """
        Prioritize multiple exit signals (if somehow multiple triggered).

        Args:
            signals: List of exit signal dicts

        Returns:
            Highest priority signal
        """
        if not signals:
            return {
                "should_exit": False,
                "exit_type": None,
                "reason": "No signals",
                "details": {},
                "priority": 999
            }

        # Sort by priority (lower number = higher priority)
        sorted_signals = sorted(signals, key=lambda x: x.get("priority", 999))

        return sorted_signals[0]

    def get_exit_summary(self, position, token_data: Optional[Dict] = None) -> Dict:
        """
        Get detailed summary of all exit checks (for logging/debugging).

        Args:
            position: Position object
            token_data: Optional token data

        Returns:
            Dict with all check results
        """
        try:
            summary = {
                "symbol": position.symbol,
                "token_address": position.token_address,
                "current_pnl": position.pnl_percent,
                "hold_time": position.hold_time_minutes,
                "checks": {}
            }

            # Run all checks
            summary["checks"]["stop"] = self.stop_loss_manager.check_stops(position)

            if token_data:
                summary["checks"]["weakness"] = self.weakness_detector.calculate_score(token_data)
            else:
                summary["checks"]["weakness"] = None

            summary["checks"]["time"] = self.time_exit.should_exit(position)

            # Final decision
            decision = self.check_exit_conditions(position, token_data)
            summary["decision"] = decision

            return summary

        except Exception as e:
            logger.error(f"Error getting exit summary: {e}")
            return {
                "error": str(e),
                "symbol": getattr(position, "symbol", "unknown")
            }


# Example usage
if __name__ == "__main__":
    import time
    from datetime import datetime, timedelta
    logging.basicConfig(level=logging.DEBUG)

    from src.position.position_manager import Position

    manager = ExitManager()

    # Example 1: Hard stop hit
    print("\n" + "="*60)
    print("EXAMPLE 1: Hard Stop Hit")
    print("="*60)

    position1 = Position(
        token_address="TEST1",
        symbol="HARDSTOP",
        entry_price=0.001,
        size_sol=0.1
    )
    position1.update_price(0.00075)  # -25%

    result1 = manager.check_exit_conditions(position1)
    print(f"\nShould Exit: {result1['should_exit']}")
    print(f"Exit Type: {result1['exit_type']}")
    print(f"Reason: {result1['reason']}")
    print(f"Priority: {result1['priority']}")

    # Example 2: Weakness detected
    print("\n" + "="*60)
    print("EXAMPLE 2: Weakness Detected")
    print("="*60)

    position2 = Position(
        token_address="TEST2",
        symbol="WEAK",
        entry_price=0.001,
        size_sol=0.1
    )
    position2.update_price(0.0012)  # +20%

    weak_data = {
        "prices": [100 + i for i in range(20)] + [120 - i for i in range(10)],
        "candles": [
            {"volume": 100000},
            {"volume": 80000},
            {"volume": 50000},  # 50% decline
        ],
        "token_address": "TEST2"
    }

    result2 = manager.check_exit_conditions(position2, weak_data)
    print(f"\nShould Exit: {result2['should_exit']}")
    print(f"Exit Type: {result2['exit_type']}")
    print(f"Reason: {result2['reason']}")
    print(f"Priority: {result2['priority']}")

    # Example 3: Time exit
    print("\n" + "="*60)
    print("EXAMPLE 3: Time Exit (Dead Price)")
    print("="*60)

    position3 = Position(
        token_address="TEST3",
        symbol="STAGNANT",
        entry_price=0.001,
        size_sol=0.1,
        timestamp=datetime.now() - timedelta(minutes=4)
    )
    position3.update_price(0.00103)  # Only +3%

    result3 = manager.check_exit_conditions(position3)
    print(f"\nShould Exit: {result3['should_exit']}")
    print(f"Exit Type: {result3['exit_type']}")
    print(f"Reason: {result3['reason']}")
    print(f"Priority: {result3['priority']}")

    # Example 4: Healthy position
    print("\n" + "="*60)
    print("EXAMPLE 4: Healthy Position")
    print("="*60)

    position4 = Position(
        token_address="TEST4",
        symbol="HEALTHY",
        entry_price=0.001,
        size_sol=0.1
    )
    position4.update_price(0.0025)  # +150%

    healthy_data = {
        "prices": [100 + i*2 for i in range(30)],  # Strong uptrend
        "candles": [{"volume": 50000 + i*1000} for i in range(5)],  # Growing volume
        "token_address": "TEST4"
    }

    result4 = manager.check_exit_conditions(position4, healthy_data)
    print(f"\nShould Exit: {result4['should_exit']}")
    print(f"Exit Type: {result4['exit_type']}")
    print(f"Reason: {result4['reason']}")
    print(f"Priority: {result4['priority']}")

    # Example 5: Trailing stop (big winner!)
    print("\n" + "="*60)
    print("EXAMPLE 5: Trailing Stop (Big Winner)")
    print("="*60)

    position5 = Position(
        token_address="TEST5",
        symbol="BIGWIN",
        entry_price=0.001,
        size_sol=0.1
    )
    position5.update_price(0.020)  # +1900% peak
    position5.update_price(0.014)  # -30% from peak, still +1300%

    result5 = manager.check_exit_conditions(position5)
    print(f"\nShould Exit: {result5['should_exit']}")
    print(f"Exit Type: {result5['exit_type']}")
    print(f"Reason: {result5['reason']}")
    print(f"Priority: {result5['priority']}")

    # Example 6: Exit summary
    print("\n" + "="*60)
    print("EXAMPLE 6: Exit Summary (Detailed)")
    print("="*60)

    summary = manager.get_exit_summary(position2, weak_data)
    print(f"\nSymbol: {summary['symbol']}")
    print(f"PnL: {summary['current_pnl']:.1f}%")
    print(f"Hold Time: {summary['hold_time']} minutes")
    print(f"\nStop Check Hit: {summary['checks']['stop']['hit']}")
    if summary['checks']['weakness']:
        print(f"Weakness Score: {summary['checks']['weakness']['score']}/100")
    print(f"Time Exit Triggered: {summary['checks']['time']['should_exit']}")
    print(f"\nFinal Decision: {summary['decision']['should_exit']}")
    print(f"Exit Type: {summary['decision']['exit_type']}")
