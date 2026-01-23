"""
Health Check - System Health Monitoring

Monitors bot health and detects issues:
- API connectivity (Alchemy, Jupiter, DexScreener)
- Last successful scan time
- Position count limits
- System resources

Returns health status with warnings and errors.
"""

import logging
import os
import psutil
from datetime import datetime, timedelta
from typing import Dict, List

from src.api.alchemy_client import AlchemyClient
from src.api.jupiter_client import JupiterClient
from src.api.dexscreener_client import DexScreenerClient
from config.parameters import (
    MAX_OPEN_POSITIONS,
    ML_TRADES_CSV,
    REJECTED_TRADES_CSV
)

logger = logging.getLogger(__name__)


class HealthCheck:
    """
    Monitors system health and detects issues.

    Checks:
    - API connectivity
    - Last scan time
    - Position limits
    - File accessibility
    - Memory usage
    """

    def __init__(self):
        """Initialize health check."""
        self.alchemy_client = AlchemyClient()
        self.jupiter_client = JupiterClient()
        self.dexscreener_client = DexScreenerClient()

        self.last_check_time = None
        self.check_count = 0

        logger.info("Health Check initialized")

    def check_system_health(
        self,
        last_scan_time: datetime = None,
        position_count: int = 0
    ) -> Dict:
        """
        Perform comprehensive health check.

        Args:
            last_scan_time: Timestamp of last successful scan
            position_count: Current number of open positions

        Returns:
            {
                "status": str,  # 'healthy', 'warning', 'error'
                "issues": List[str],
                "warnings": List[str],
                "last_check": datetime,
                "details": dict
            }
        """
        try:
            self.check_count += 1
            self.last_check_time = datetime.now()

            issues = []
            warnings = []
            details = {}

            # 1. Check API connectivity
            api_status = self._check_api_connectivity()
            details["apis"] = api_status

            if not api_status["alchemy"]:
                issues.append("Alchemy API not responding")
            if not api_status["jupiter"]:
                issues.append("Jupiter API not responding")
            if not api_status["dexscreener"]:
                warnings.append("DexScreener API not responding")

            # 2. Check last scan time
            if last_scan_time:
                time_since_scan = (datetime.now() - last_scan_time).total_seconds()
                details["time_since_last_scan"] = time_since_scan

                if time_since_scan > 300:  # 5 minutes
                    issues.append(f"No scan in {int(time_since_scan / 60)} minutes")
                elif time_since_scan > 120:  # 2 minutes
                    warnings.append(f"Last scan {int(time_since_scan)} seconds ago")

            # 3. Check position count
            details["position_count"] = position_count
            details["max_positions"] = MAX_OPEN_POSITIONS

            if position_count >= MAX_OPEN_POSITIONS:
                warnings.append(f"At max positions ({position_count}/{MAX_OPEN_POSITIONS})")

            # 4. Check data files
            file_status = self._check_data_files()
            details["files"] = file_status

            if not file_status["ml_trades_writable"]:
                issues.append("Cannot write to ml_trades.csv")
            if not file_status["rejected_trades_writable"]:
                warnings.append("Cannot write to rejected_trades.csv")

            # 5. Check memory usage (if available)
            try:
                memory_info = self._check_memory()
                details["memory"] = memory_info

                if memory_info["percent"] > 90:
                    issues.append(f"High memory usage: {memory_info['percent']}%")
                elif memory_info["percent"] > 75:
                    warnings.append(f"Memory usage: {memory_info['percent']}%")

            except Exception as e:
                logger.debug(f"Memory check not available: {e}")

            # Determine overall status
            if issues:
                status = "error"
            elif warnings:
                status = "warning"
            else:
                status = "healthy"

            result = {
                "status": status,
                "issues": issues,
                "warnings": warnings,
                "last_check": self.last_check_time,
                "check_count": self.check_count,
                "details": details
            }

            # Log results
            if status == "healthy":
                logger.info("✅ System health: HEALTHY")
            elif status == "warning":
                logger.warning(f"⚠️ System health: WARNING - {', '.join(warnings)}")
            else:
                logger.error(f"❌ System health: ERROR - {', '.join(issues)}")

            return result

        except Exception as e:
            logger.error(f"Error in health check: {e}")
            return {
                "status": "error",
                "issues": [f"Health check failed: {e}"],
                "warnings": [],
                "last_check": datetime.now(),
                "check_count": self.check_count,
                "details": {}
            }

    def _check_api_connectivity(self) -> Dict:
        """
        Check connectivity to all APIs.

        Returns:
            {"alchemy": bool, "jupiter": bool, "dexscreener": bool}
        """
        status = {
            "alchemy": False,
            "jupiter": False,
            "dexscreener": False
        }

        # Check Alchemy
        try:
            # Try a simple RPC call
            test_address = "So11111111111111111111111111111111111111112"  # SOL
            self.alchemy_client.check_mint_authority(test_address)
            status["alchemy"] = True
        except Exception as e:
            logger.warning(f"Alchemy connectivity check failed: {e}")

        # Check Jupiter
        try:
            # Try getting a price
            test_address = "So11111111111111111111111111111111111111112"
            self.jupiter_client.get_token_price(test_address)
            status["jupiter"] = True
        except Exception as e:
            logger.warning(f"Jupiter connectivity check failed: {e}")

        # Check DexScreener
        try:
            # Try getting token data
            test_address = "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263"  # BONK
            self.dexscreener_client.get_token_data(test_address)
            status["dexscreener"] = True
        except Exception as e:
            logger.warning(f"DexScreener connectivity check failed: {e}")

        logger.debug(
            f"API connectivity: Alchemy={status['alchemy']}, "
            f"Jupiter={status['jupiter']}, DexScreener={status['dexscreener']}"
        )

        return status

    def _check_data_files(self) -> Dict:
        """
        Check if data files are accessible and writable.

        Returns:
            {"ml_trades_writable": bool, "rejected_trades_writable": bool}
        """
        status = {
            "ml_trades_writable": False,
            "rejected_trades_writable": False
        }

        # Check ml_trades.csv
        try:
            # Ensure directory exists
            ml_dir = os.path.dirname(ML_TRADES_CSV)
            if ml_dir and not os.path.exists(ml_dir):
                os.makedirs(ml_dir)

            # Try to open for appending
            with open(ML_TRADES_CSV, "a"):
                pass
            status["ml_trades_writable"] = True
        except Exception as e:
            logger.warning(f"Cannot write to {ML_TRADES_CSV}: {e}")

        # Check rejected_trades.csv
        try:
            # Ensure directory exists
            rej_dir = os.path.dirname(REJECTED_TRADES_CSV)
            if rej_dir and not os.path.exists(rej_dir):
                os.makedirs(rej_dir)

            # Try to open for appending
            with open(REJECTED_TRADES_CSV, "a"):
                pass
            status["rejected_trades_writable"] = True
        except Exception as e:
            logger.warning(f"Cannot write to {REJECTED_TRADES_CSV}: {e}")

        return status

    def _check_memory(self) -> Dict:
        """
        Check system memory usage.

        Returns:
            {"used": int, "total": int, "percent": float}
        """
        try:
            memory = psutil.virtual_memory()

            return {
                "used": memory.used,
                "total": memory.total,
                "percent": memory.percent
            }
        except Exception as e:
            logger.debug(f"Memory check failed: {e}")
            return {
                "used": 0,
                "total": 0,
                "percent": 0
            }

    def get_quick_status(self, position_count: int = 0) -> str:
        """
        Get quick status string for logging.

        Args:
            position_count: Current open positions

        Returns:
            Status string (e.g., "✅ Healthy | Positions: 2/5")
        """
        health = self.check_system_health(position_count=position_count)

        status_emoji = {
            "healthy": "✅",
            "warning": "⚠️",
            "error": "❌"
        }

        emoji = status_emoji.get(health["status"], "❓")

        return (
            f"{emoji} {health['status'].upper()} | "
            f"Positions: {position_count}/{MAX_OPEN_POSITIONS} | "
            f"Check #{health['check_count']}"
        )


# Example usage
if __name__ == "__main__":
    from datetime import datetime, timedelta
    logging.basicConfig(level=logging.DEBUG)

    checker = HealthCheck()

    print("\n" + "=" * 60)
    print("Test 1: Full Health Check")
    print("=" * 60)

    result = checker.check_system_health(
        last_scan_time=datetime.now() - timedelta(seconds=30),
        position_count=2
    )

    print(f"\nStatus: {result['status']}")
    print(f"Issues: {result['issues']}")
    print(f"Warnings: {result['warnings']}")
    print(f"Check count: {result['check_count']}")
    print(f"\nDetails:")
    print(f"  APIs: {result['details'].get('apis')}")
    print(f"  Positions: {result['details'].get('position_count')}/{result['details'].get('max_positions')}")
    print(f"  Files: {result['details'].get('files')}")

    print("\n" + "=" * 60)
    print("Test 2: Old Scan Warning")
    print("=" * 60)

    result2 = checker.check_system_health(
        last_scan_time=datetime.now() - timedelta(minutes=3),
        position_count=5
    )

    print(f"\nStatus: {result2['status']}")
    print(f"Warnings: {result2['warnings']}")

    print("\n" + "=" * 60)
    print("Test 3: Quick Status")
    print("=" * 60)

    status_str = checker.get_quick_status(position_count=3)
    print(f"\n{status_str}")
