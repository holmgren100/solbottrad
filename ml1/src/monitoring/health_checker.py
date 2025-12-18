"""
Health checking system for monitoring component status.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Callable, Awaitable
from dataclasses import dataclass
from .logger import get_logger

logger = get_logger(__name__)


@dataclass
class ComponentHealth:
    """Health status of a component."""
    name: str
    status: str  # 'healthy', 'degraded', 'unhealthy'
    last_check: datetime
    error_message: str = ''


class HealthChecker:
    """Monitors health of bot components."""

    def __init__(self):
        """Initialize the health checker."""
        self.components: Dict[str, Callable[[], Awaitable[bool]]] = {}
        self.health_status: Dict[str, ComponentHealth] = {}
        self._running = False
        self._check_interval = 60  # seconds

    def register_component(
        self,
        name: str,
        health_check: Callable[[], Awaitable[bool]]
    ):
        """
        Register a component for health monitoring.

        Args:
            name: Component name
            health_check: Async function that returns True if healthy
        """
        self.components[name] = health_check
        self.health_status[name] = ComponentHealth(
            name=name,
            status='unknown',
            last_check=datetime.now()
        )
        logger.info(f"Registered health check for component: {name}")

    async def check_component(self, name: str) -> ComponentHealth:
        """
        Check health of a specific component.

        Args:
            name: Component name

        Returns:
            ComponentHealth status
        """
        if name not in self.components:
            logger.warning(f"Component not registered: {name}")
            return ComponentHealth(
                name=name,
                status='unknown',
                last_check=datetime.now(),
                error_message='Component not registered'
            )

        try:
            is_healthy = await self.components[name]()
            status = 'healthy' if is_healthy else 'unhealthy'
            health = ComponentHealth(
                name=name,
                status=status,
                last_check=datetime.now()
            )
        except Exception as e:
            logger.error(f"Health check failed for {name}: {e}")
            health = ComponentHealth(
                name=name,
                status='unhealthy',
                last_check=datetime.now(),
                error_message=str(e)
            )

        self.health_status[name] = health
        return health

    async def check_all(self) -> Dict[str, ComponentHealth]:
        """
        Check health of all registered components.

        Returns:
            Dictionary of component health statuses
        """
        tasks = [self.check_component(name) for name in self.components]
        await asyncio.gather(*tasks, return_exceptions=True)
        return self.health_status

    async def monitor(self):
        """Continuously monitor component health."""
        self._running = True
        logger.info("Health monitoring started")

        while self._running:
            try:
                await self.check_all()

                # Log unhealthy components
                unhealthy = [
                    h for h in self.health_status.values()
                    if h.status != 'healthy'
                ]
                if unhealthy:
                    for health in unhealthy:
                        logger.warning(
                            f"Component {health.name} is {health.status}: "
                            f"{health.error_message}"
                        )

                await asyncio.sleep(self._check_interval)
            except Exception as e:
                logger.error(f"Error in health monitoring: {e}")
                await asyncio.sleep(self._check_interval)

    def stop(self):
        """Stop health monitoring."""
        self._running = False
        logger.info("Health monitoring stopped")

    def get_overall_status(self) -> str:
        """
        Get overall system health status.

        Returns:
            'healthy', 'degraded', or 'unhealthy'
        """
        if not self.health_status:
            return 'unknown'

        statuses = [h.status for h in self.health_status.values()]

        if all(s == 'healthy' for s in statuses):
            return 'healthy'
        elif any(s == 'unhealthy' for s in statuses):
            return 'degraded'
        else:
            return 'healthy'

    def get_status_summary(self) -> str:
        """
        Get a formatted summary of component health.

        Returns:
            Formatted status summary string
        """
        lines = ["Component Health Status:"]
        for health in self.health_status.values():
            emoji = {
                'healthy': '✅',
                'degraded': '⚠️',
                'unhealthy': '❌',
                'unknown': '❓'
            }.get(health.status, '❓')

            line = f"{emoji} {health.name}: {health.status}"
            if health.error_message:
                line += f" - {health.error_message}"
            lines.append(line)

        return '\n'.join(lines)
