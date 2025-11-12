import time
import requests
from datetime import datetime
from typing import Dict, Any
from utils.logger import setup_logger

class HealthCheck:
    def __init__(self):
        self.logger = setup_logger(__name__)
        self.components = {
            'twitter_api': False,
            'dexscreener_api': False,
            'solsniffer_api': False,
            'alchemy_api': False,
            'prediction_model': False,
            'gmgn_trader': False,
            'wallet_monitor': False,
            'volume_monitor': False
        }
        self.last_check_time = None
        self.errors = []

    async def check_health(self, instances: Dict[str, Any]) -> Dict[str, Any]:
        """
        Async health check for all components.
        """
        self.last_check_time = datetime.now()
        self.errors = []

        # Check APIs
        for api_name in ['twitter_api', 'dexscreener_api', 'solsniffer_api', 'alchemy_api']:
            if api_name in instances:
                try:
                    # If the API has an async test method, use it; else, use sync
                    test_method = getattr(instances[api_name], "health_check", None)
                    if callable(test_method):
                        if hasattr(test_method, "__await__"):
                            await test_method()
                        else:
                            test_method()
                    self.components[api_name] = True
                except Exception as e:
                    self.errors.append(f"{api_name} error: {str(e)}")
                    self.components[api_name] = False

        # Check ML models
        if 'prediction_model' in instances:
            try:
                # Dummy prediction to check model
                import numpy as np
                test_data = np.array([[1]])
                instances['prediction_model'].predict(test_data)
                self.components['prediction_model'] = True
            except Exception as e:
                self.errors.append(f"prediction_model error: {str(e)}")
                self.components['prediction_model'] = False

        # Check monitors
        if 'wallet_monitor' in instances:
            try:
                # Add your wallet monitor test here if needed
                self.components['wallet_monitor'] = True
            except Exception as e:
                self.errors.append(f"wallet_monitor error: {str(e)}")
                self.components['wallet_monitor'] = False
        if 'volume_monitor' in instances:
            try:
                # Add your volume monitor test here if needed
                self.components['volume_monitor'] = True
            except Exception as e:
                self.errors.append(f"volume_monitor error: {str(e)}")
                self.components['volume_monitor'] = False

        # Check trader
        if 'gmgn_trader' in instances:
            try:
                # Add your GMGN trader test here if needed
                self.components['gmgn_trader'] = True
            except Exception as e:
                self.errors.append(f"gmgn_trader error: {str(e)}")
                self.components['gmgn_trader'] = False

        status = self.get_status()
        self.logger.info(f"Health check status: {status['status']}")
        if status['errors']:
            self.logger.warning(f"Health check errors: {status['errors']}")
        return status

    def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of all components.
        """
        healthy = all(self.components.values())
        return {
            'status': 'healthy' if healthy else 'unhealthy',
            'healthy': healthy,
            'components': self.components,
            'last_check': self.last_check_time.strftime('%Y-%m-%d %H:%M:%S') if self.last_check_time else None,
            'errors': self.errors
        }

# Example usage (for manual testing)
if __name__ == "__main__":
    from api.twitter_api import TwitterAPI
    from api.dexscreener_api import DexScreenerAPI
    from ai.prediction_model import PricePredictor
    from monitoring.volume_monitor import VolumeMonitor

    import asyncio

    instances = {
        'twitter_api': TwitterAPI(),
        'dexscreener_api': DexScreenerAPI(),
        'prediction_model': PricePredictor(),
        'volume_monitor': VolumeMonitor()
    }

    async def test_health():
        health_checker = HealthCheck()
        status = await health_checker.check_health(instances)
        print("Health Check Status:", status)

    asyncio.run(test_health())