import sys
import asyncio
import signal
from pathlib import Path
from typing import Dict, Any, Optional

# Add project root to Python path
project_root = str(Path(__file__).parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from config.settings import settings
from utils.logger import setup_logger
from utils.health_check import HealthCheck
from utils.rate_limiter import RateLimiter
from utils.telegram_notifier import TelegramNotifier

from api.alchemy_api import AlchemyAPI
from api.solsniffer_api import SolSnifferAPI
from api.twitter_api import TwitterAPI
from api.dexscreener_api import DexScreenerAPI

from trading.gmgn_trader import GMGNTrader
from trading.strategy import TradingStrategy

from monitoring.wallet_monitor import WalletMonitor
from monitoring.volume_monitor import VolumeMonitor

from ai.sentiment_model import SentimentAnalyzer
from ai.prediction_model import PricePredictor

from exceptions.custom_exceptions import (
    APIError, TradingError, ModelNotTrainedError,
    ConfigurationError, ConnectionError
)

logger = setup_logger('main')


class TradingBot:
    """Main trading bot class that orchestrates all components."""

    def __init__(self):
        """Initialize the trading bot with all its components."""
        self.logger = setup_logger(__name__)
        self.is_running = False
        self.websocket = None
        self.health_check_counter = 0
        self.last_health_check = None

        try:
            # Validate configuration first
            settings.validate_config()
            
            # Initialize components
            self._initialize_components()
            
            # Setup signal handlers
            self._setup_signal_handlers()
            
            self.logger.info("Trading bot initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize trading bot: {str(e)}")
            raise

    def _initialize_components(self):
        """Initialize all bot components."""
        try:
            # Initialize utilities with proper error handling
            self.rate_limiter = RateLimiter(
                calls_per_second=settings.RATE_LIMIT_CALLS / settings.RATE_LIMIT_PERIOD
            )
            self.notifier = TelegramNotifier()

            # Initialize APIs
            self.alchemy = AlchemyAPI()
            self.solsniffer = SolSnifferAPI()
            self.twitter = TwitterAPI()
            self.dexscreener = DexScreenerAPI()

            # Initialize Trading Components
            self.trader = GMGNTrader()
            self.strategy = TradingStrategy()

            # Initialize Monitoring
            self.wallet_monitor = WalletMonitor()
            self.volume_monitor = VolumeMonitor()

            # Initialize AI Components
            self.sentiment_analyzer = SentimentAnalyzer()
            self.price_predictor = PricePredictor()

            # Initialize Health Checker
            self.health_checker = HealthCheck()

            # Register components for health checks
            self.instances = {
                'alchemy_api': self.alchemy,
                'solsniffer_api': self.solsniffer,
                'twitter_api': self.twitter,
                'dexscreener_api': self.dexscreener,
                'gmgn_trader': self.trader,
                'wallet_monitor': self.wallet_monitor,
                'volume_monitor': self.volume_monitor,
                'sentiment_analyzer': self.sentiment_analyzer,
                'price_predictor': self.price_predictor
            }
            
            self.logger.info("All components initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Error initializing components: {str(e)}")
            raise

    def _setup_signal_handlers(self):
        """Setup handlers for system signals."""
        try:
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)
            self.logger.debug("Signal handlers set up successfully")
        except Exception as e:
            self.logger.warning(f"Could not set up signal handlers: {str(e)}")

    def _signal_handler(self, signum, frame):
        """Handle system signals."""
        self.logger.info(f"Received signal {signum}, initiating shutdown...")
        self.is_running = False

    async def initialize(self) -> bool:
        """Initialize connections and subscriptions."""
        try:
            self.logger.info("Initializing bot connections...")
            
            # Connect to Alchemy WebSocket
            try:
                self.websocket = await self.alchemy.connect()
                self.logger.info("Connected to Alchemy WebSocket")
            except Exception as e:
                self.logger.error(f"Failed to connect to Alchemy WebSocket: {str(e)}")
                return False

            # Subscribe to tracked wallets
            subscription_count = 0
            for wallet in settings.TRACKED_WALLETS:
                try:
                    await self.alchemy.subscribe_to_address(self.websocket, wallet)
                    subscription_count += 1
                    self.logger.debug(f"Subscribed to wallet: {wallet}")
                except Exception as e:
                    self.logger.warning(f"Failed to subscribe to wallet {wallet}: {str(e)}")

            self.logger.info(f"Successfully subscribed to {subscription_count}/{len(settings.TRACKED_WALLETS)} wallets")

            # Send initialization notification
            try:
                notification_msg = "[DRY RUN] " if getattr(settings, 'DRY_RUN', False) else ""
                notification_msg += f"Bot initialization completed successfully. Monitoring {subscription_count} wallets."
                await self.notifier.send_notification(notification_msg)
            except Exception as e:
                self.logger.warning(f"Failed to send initialization notification: {str(e)}")

            self.is_running = True
            self.logger.info("Bot initialization completed successfully")
            return True

        except ConnectionError as e:
            self.logger.error(f"Connection error during initialization: {str(e)}")
            try:
                await self.notifier.send_error_notification(
                    f"Connection error: {str(e)}",
                    severity="ERROR"
                )
            except:
                pass
            return False
        except Exception as e:
            self.logger.error(f"Bot initialization failed: {str(e)}")
            try:
                await self.notifier.send_error_notification(
                    f"Initialization error: {str(e)}",
                    severity="CRITICAL"
                )
            except:
                pass
            return False

    async def process_message(self, message: Dict[str, Any]) -> None:
        """Process incoming messages and execute trading strategy."""
        if not message:
            return

        try:
            self.logger.debug(f"Processing message: {message.get('type', 'unknown')}")

            # Process transaction with error handling
            try:
                await self.wallet_monitor.process_transaction(message)
            except Exception as e:
                self.logger.warning(f"Error processing transaction: {str(e)}")

            # Update market data with error handling
            try:
                await self.volume_monitor.update_volumes()
            except Exception as e:
                self.logger.warning(f"Error updating volumes: {str(e)}")

            # Check trading conditions
            try:
                should_trade = await self.strategy.should_trade(message)
                if should_trade:
                    self.logger.info("Trading conditions met, executing trade...")
                    
                    # Execute trade
                    trade_result = await self.trader.execute_trade(message)

                    # Send trade notification
                    if trade_result and not trade_result.get("skipped"):
                        await self.notifier.send_trade_notification(
                            trade_type=trade_result.get('type', 'unknown'),
                            token=trade_result.get('token', 'unknown'),
                            amount=trade_result.get('amount', 0),
                            price=trade_result.get('price')
                        )
                        self.logger.info(f"Trade executed: {trade_result}")
                    else:
                        self.logger.debug("Trade was skipped or returned no result")
                        
            except TradingError as e:
                self.logger.error(f"Trading error: {str(e)}")
                await self.notifier.send_error_notification(str(e), severity="ERROR")
            except Exception as e:
                self.logger.error(f"Error in trading logic: {str(e)}")

        except Exception as e:
            self.logger.error(f"Error processing message: {str(e)}")
            try:
                await self.notifier.send_error_notification(str(e), severity="WARNING")
            except:
                pass

    async def perform_health_check(self) -> None:
        """Perform periodic health checks."""
        try:
            self.health_check_counter += 1
            
            # Only perform detailed health check every N iterations
            if self.health_check_counter % 10 == 0:
                health_status = await self.health_checker.check_health(self.instances)
                
                if not health_status.get('healthy', False):
                    self.logger.warning(f"Health check failed: {health_status.get('details', 'Unknown')}")
                    await self.notifier.send_error_notification(
                        f"Health check failed: {health_status.get('details', 'Unknown')}",
                        severity="WARNING"
                    )
                else:
                    self.logger.debug("Health check passed")
                    
                self.last_health_check = health_status
                
        except Exception as e:
            self.logger.warning(f"Error during health check: {str(e)}")

    async def cleanup(self) -> None:
        """Cleanup resources before shutdown."""
        self.logger.info("Starting cleanup process...")
        
        try:
            # Close WebSocket connection
            if self.websocket:
                try:
                    if hasattr(self.alchemy, 'disconnect'):
                        await self.alchemy.disconnect(self.websocket)
                    self.logger.info("WebSocket connection closed")
                except Exception as e:
                    self.logger.warning(f"Error closing WebSocket: {str(e)}")

            # Cleanup trading components
            cleanup_tasks = []
            
            if hasattr(self.trader, 'cleanup'):
                cleanup_tasks.append(self.trader.cleanup())
            if hasattr(self.dexscreener, 'cleanup'):
                cleanup_tasks.append(self.dexscreener.cleanup())
            if hasattr(self.volume_monitor, 'close'):
                cleanup_tasks.append(self.volume_monitor.close())

            # Execute cleanup tasks
            if cleanup_tasks:
                await asyncio.gather(*cleanup_tasks, return_exceptions=True)

            self.logger.info("Cleanup completed successfully")
            
            # Send shutdown notification
            try:
                notification_msg = "[DRY RUN] " if getattr(settings, 'DRY_RUN', False) else ""
                notification_msg += "Bot shutdown completed successfully"
                await self.notifier.send_notification(notification_msg)
            except Exception as e:
                self.logger.warning(f"Failed to send shutdown notification: {str(e)}")

        except Exception as e:
            self.logger.error(f"Error during cleanup: {str(e)}")
            try:
                await self.notifier.send_error_notification(
                    f"Cleanup error: {str(e)}",
                    severity="WARNING"
                )
            except:
                pass

    async def run(self) -> None:
        """Main bot execution loop."""
        try:
            # Initialize the bot
            if not await self.initialize():
                self.logger.error("Bot initialization failed, exiting...")
                return

            self.logger.info("Starting main execution loop...")
            loop_counter = 0

            while self.is_running:
                try:
                    loop_counter += 1
                    
                    # Perform periodic health checks
                    await self.perform_health_check()

                    # Handle messages from Alchemy WebSocket (FIXED: async generator)
                    try:
                        async for message in self.alchemy.handle_messages(self.websocket):
                            try:
                                await self.process_message(message)
                            except Exception as e:
                                self.logger.error(f"Error processing message: {e}")
                                
                        # If the generator ends, pause briefly before reconnecting
                        self.logger.warning("WebSocket message stream ended, reconnecting...")
                        await asyncio.sleep(1)
                        
                        # Try to reconnect
                        try:
                            self.websocket = await self.alchemy.connect()
                            for wallet in settings.TRACKED_WALLETS:
                                await self.alchemy.subscribe_to_address(self.websocket, wallet)
                            self.logger.info("Reconnected to WebSocket successfully")
                        except Exception as e:
                            self.logger.error(f"Failed to reconnect: {e}")
                            await asyncio.sleep(5)
                            
                    except Exception as e:
                        self.logger.warning(f"Error handling messages: {str(e)}")
                        await asyncio.sleep(getattr(settings, 'RETRY_DELAY', 5))

                    # Log periodic status
                    if loop_counter % 600 == 0:  # Every ~60 seconds
                        self.logger.info(f"Bot running normally. Loop count: {loop_counter}")

                except Exception as e:
                    self.logger.error(f"Error in main loop: {str(e)}")
                    await asyncio.sleep(getattr(settings, 'RETRY_DELAY', 5))

        except Exception as e:
            self.logger.error(f"Fatal error in bot execution: {str(e)}")
            try:
                await self.notifier.send_error_notification(
                    f"Fatal error: {str(e)}",
                    severity="CRITICAL"
                )
            except:
                pass
            raise
        finally:
            await self.cleanup()


async def main() -> None:
    """Main application entry point."""
    try:
        # Setup logging format
        logger.info("=" * 50)
        logger.info("Starting Solana Trading Bot")
        logger.info("=" * 50)

        # Validate configuration
        try:
            settings.validate_config()
            logger.info("✓ Configuration validation successful")
        except Exception as e:
            logger.error(f"✗ Configuration validation failed: {str(e)}")
            raise ConfigurationError(f"Configuration validation failed: {str(e)}")

        # Show important settings
        dry_run_mode = getattr(settings, 'DRY_RUN', False)
        if dry_run_mode:
            logger.warning("⚠️  DRY RUN mode is ON. No real trades will be placed.")
        else:
            logger.info("💰 LIVE TRADING mode is ON. Real trades will be placed!")

        # Log configuration details
        logger.info(f"📊 Tracked wallets: {len(settings.TRACKED_WALLETS)}")
        logger.info(f"💵 Min volume threshold: ${settings.MIN_VOLUME:,}")
        logger.info(f"💧 Min liquidity threshold: ${settings.MIN_LIQUIDITY:,}")
        logger.info(f"📈 Min sentiment score: {settings.MIN_SENTIMENT_SCORE}")
        logger.info(f"⚡ Rate limit: {settings.RATE_LIMIT_CALLS} calls per {settings.RATE_LIMIT_PERIOD}s")

        # Create and run bot
        bot = TradingBot()
        await bot.run()

    except ConfigurationError as e:
        logger.error(f"Configuration error: {str(e)}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user (Ctrl+C)")
    except Exception as e:
        logger.error(f"Bot stopped due to unexpected error: {str(e)}")
        sys.exit(1)
    finally:
        logger.info("Bot execution completed")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        sys.exit(1)