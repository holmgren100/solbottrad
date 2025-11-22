import asyncio
from typing import Dict, List
from datetime import datetime
import logging

class HealthChecker:
    """Monitor system health and component status"""

    def __init__(self):
        self.logger = logging.getLogger('trading_bot.health')
        self.components = {}
        self.last_check = None

    def register_component(self, name: str, status: str = "unknown"):
        """Register a component for health monitoring"""
        self.components[name] = {
            'status': status,
            'last_update': datetime.now(),
            'errors': []
        }

    def update_component_status(self, name: str, status: str, error: str = None):
        """Update component status"""
        if name not in self.components:
            self.register_component(name)

        self.components[name]['status'] = status
        self.components[name]['last_update'] = datetime.now()

        if error:
            self.components[name]['errors'].append({
                'timestamp': datetime.now(),
                'error': error
            })

    def get_health_status(self) -> Dict:
        """Get overall health status"""
        healthy = sum(1 for c in self.components.values() if c['status'] == 'healthy')
        total = len(self.components)

        return {
            'overall': 'healthy' if healthy == total else 'degraded',
            'healthy_components': healthy,
            'total_components': total,
            'components': self.components,
            'last_check': datetime.now()
        }

    def log_health(self):
        """Log current health status"""
        status = self.get_health_status()
        self.logger.info(f"Health: {status['healthy_components']}/{status['total_components']} components healthy")

        for name, component in status['components'].items():
            if component['status'] != 'healthy':
                self.logger.warning(f"Component '{name}' is {component['status']}")
