"""
Main entry point for the Solana Trading Bot.
Orchestrates all components and manages the trading loop.
"""

import asyncio
import signal
import sys
from datetime import datetime
from typing import Optional

from .config import settings
from .monitoring import setup_logger, get_logger, TelegramNotifier, HealthChecker
from .blockchain import AlchemyClient, SolSnifferClient, WalletTracker
from .market import DexScreenerClient, MarketAnalyzer
from .social import TwitterClient, SentimentAnalyzer
from .ai import SentimentModel, PricePredictor, RiskAssessor
from .trading import TelegramExecutor, PositionManager, PaperTradingEngine

# Setup logging
setup_logger(
    name='trading_bot',
    log_file=settings.log_file,
    log_level=settings.log_level
)
logger = get_logger(__name__)


class SolanaTradingBot:
    """Main trading bot orchestrator."""

    def __init__(self):
        """Initialize the trading bot with all components."""
        logger.info("Initializing Solana Trading Bot...")

        # Configuration
        self.settings = settings
        self.running = False

        # Monitoring
        self.notifier = TelegramNotifier(
            bot_token=settings.api.telegram_bot_token,
            chat_id=settings.api.telegram_chat_id
        )
        self.health_checker = HealthChecker()

        # Blockchain
        self.alchemy = AlchemyClient(settings.api.alchemy_api_key)
        self.solsniffer = SolSnifferClient(settings.api.solsniffer_api_key)
        self.wallet_tracker = WalletTracker()

        # Market
        self.dexscreener = DexScreenerClient(settings.api.dexscreener_api_key)
        self.market_analyzer = MarketAnalyzer(
            min_liquidity_usd=settings.trading.min_liquidity_usd
        )

        # Social
        self.twitter = TwitterClient(settings.api.twitter_bearer_token)
        self.sentiment_analyzer = SentimentAnalyzer()

        # AI Models
        self.sentiment_model = SentimentModel()
        self.price_predictor = PricePredictor()
        self.risk_assessor = RiskAssessor(
            max_position_size=settings.trading.max_position_size
        )

        # Trading
        if settings.is_paper_trading():
            logger.info("Paper trading mode enabled")
            self.trading_engine = PaperTradingEngine(initial_capital=1000.0)
        else:
            logger.warning("Live trading mode - using TelegramExecutor")
            self.trading_engine = TelegramExecutor(settings.api.gmgn_telegram_bot)

        self.position_manager = PositionManager(
            max_open_positions=settings.risk.max_open_positions
        )

        # Register health checks
        self._register_health_checks()

        logger.info("Bot initialization complete")

    def _register_health_checks(self):
        """Register component health checks."""
        self.health_checker.register_component('alchemy', self.alchemy.health_check)
        self.health_checker.register_component('solsniffer', self.solsniffer.health_check)
        self.health_checker.register_component('dexscreener', self.dexscreener.health_check)
        self.health_checker.register_component('twitter', self.twitter.health_check)
        self.health_checker.register_component('wallet_tracker', self.wallet_tracker.health_check)

    async def analyze_token(self, token_address: str) -> Optional[dict]:
        """
        Perform comprehensive analysis on a token.

        Args:
            token_address: Token contract address

        Returns:
            Analysis results dictionary or None
        """
        logger.info(f"Analyzing token: {token_address}")

        try:
            # 1. Get market data
            profile = await self.dexscreener.get_token_profile(token_address)
            if not profile:
                logger.warning(f"No market data found for {token_address}")
                return None

            # 2. Get security data
            security_data = await self.solsniffer.analyze_token(token_address)

            # 3. Get social sentiment
            token_symbol = profile.get('symbol', 'UNKNOWN')
            social_data = await self.twitter.analyze_token_buzz(token_symbol, token_address)
            tweets = await self.twitter.search_token_mentions(token_symbol, token_address)
            sentiment_analysis = self.sentiment_analyzer.analyze_tweets(tweets)
            coordination_analysis = self.sentiment_analyzer.detect_coordinated_activity(tweets)

            # 4. Generate market signal
            market_signal = self.market_analyzer.analyze_token(profile)

            # 5. Score sentiment
            sentiment_score = self.sentiment_model.score_sentiment(
                social_data=social_data,
                sentiment_analysis=sentiment_analysis,
                coordination_analysis=coordination_analysis
            )

            # 6. Predict price movement
            price_prediction = self.price_predictor.predict(
                token_address=token_address,
                current_price=profile['price_usd'],
                market_signal=market_signal.__dict__,
                sentiment_score=sentiment_score.__dict__,
                timeframe_hours=24
            )

            # 7. Assess risk
            risk_assessment = self.risk_assessor.assess_risk(
                token_address=token_address,
                market_data=profile,
                security_data=security_data,
                sentiment_score=sentiment_score.__dict__,
                price_prediction=price_prediction.__dict__
            )

            # Record data for learning
            self.market_analyzer.record_price(
                token_address,
                profile['price_usd'],
                profile['volume_24h']
            )
            self.price_predictor.record_price(
                token_address,
                profile['price_usd'],
                profile['volume_24h'],
                profile['liquidity_usd']
            )

            analysis = {
                'token_address': token_address,
                'symbol': token_symbol,
                'profile': profile,
                'security': security_data,
                'market_signal': market_signal,
                'sentiment_score': sentiment_score,
                'price_prediction': price_prediction,
                'risk_assessment': risk_assessment,
                'timestamp': datetime.now().isoformat()
            }

            logger.info(
                f"Analysis complete for {token_symbol}: "
                f"Market={market_signal.signal_type}, "
                f"Sentiment={sentiment_score.recommendation}, "
                f"Risk={risk_assessment.overall_risk}"
            )

            return analysis

        except Exception as e:
            logger.error(f"Error analyzing token {token_address}: {e}")
            return None

    async def make_trading_decision(self, analysis: dict) -> Optional[dict]:
        """
        Make a trading decision based on analysis.

        Args:
            analysis: Token analysis results

        Returns:
            Trading decision dictionary or None
        """
        risk_assessment = analysis['risk_assessment']
        market_signal = analysis['market_signal']
        sentiment_score = analysis['sentiment_score']
        price_prediction = analysis['price_prediction']
        profile = analysis['profile']

        # Debug output
        print(f"    📊 Market Signal: {market_signal.signal_type} (confidence: {market_signal.confidence:.2f})")
        print(f"    😊 Sentiment: {sentiment_score.recommendation} (score: {sentiment_score.overall_score:.2f})")
        print(f"    ⚠️  Risk: {risk_assessment.overall_risk} (score: {risk_assessment.risk_score:.2f})")
        print(f"    ✅ Should Trade: {risk_assessment.should_trade}")

        # Check if we should trade
        if not risk_assessment.should_trade:
            print(f"    ❌ Risk assessment says NO: {', '.join(risk_assessment.warnings)}")
            logger.info("Risk assessment advises against trading")
            return None

        # Check confidence thresholds
        if sentiment_score.confidence < self.settings.trading.min_confidence_score:
            print(f"    ❌ Confidence too low: {sentiment_score.confidence:.2f} < {self.settings.trading.min_confidence_score}")
            logger.info(f"Sentiment confidence too low: {sentiment_score.confidence:.2f}")
            return None

        # Determine action
        # If sentiment is 'avoid' due to no data (confidence=0), rely on market signal alone
        action = None
        if sentiment_score.confidence == 0.0:
            # No sentiment data available, use market signal only
            if market_signal.signal_type == 'buy':
                action = 'buy'
                print(f"    ℹ️  Using market signal only (no sentiment data)")
            elif market_signal.signal_type == 'sell':
                action = 'sell'
                print(f"    ℹ️  Using market signal only (no sentiment data)")
        else:
            # Normal logic with sentiment
            if market_signal.signal_type == 'buy' and sentiment_score.recommendation in ['buy', 'strong_buy']:
                action = 'buy'
            elif market_signal.signal_type == 'sell':
                action = 'sell'

        if not action:
            print(f"    ❌ No action: market={market_signal.signal_type}, sentiment={sentiment_score.recommendation}")
            logger.info("No clear trading signal")
            return None

        # Calculate position size
        position_size = (
            risk_assessment.recommended_position_size *
            self.settings.trading.max_position_size
        )

        # Calculate stop loss and take profit
        entry_price = profile['price_usd']
        stop_loss = self.risk_assessor.calculate_stop_loss(
            entry_price,
            self.settings.risk.stop_loss_percent
        )
        take_profit = self.risk_assessor.calculate_take_profit(
            entry_price,
            self.settings.risk.take_profit_percent
        )

        decision = {
            'action': action,
            'token_address': analysis['token_address'],
            'symbol': analysis['symbol'],
            'entry_price': entry_price,
            'position_size': position_size,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'confidence': sentiment_score.confidence,
            'reasons': sentiment_score.reasoning + price_prediction.factors
        }

        return decision

    async def execute_trade(self, decision: dict) -> bool:
        """
        Execute a trading decision.

        Args:
            decision: Trading decision dictionary

        Returns:
            True if executed successfully
        """
        try:
            # Send trade signal notification
            await self.notifier.send_trade_signal(
                token_address=decision['token_address'],
                action=decision['action'].upper(),
                confidence=decision['confidence'],
                price=decision['entry_price'],
                reasons=decision['reasons']
            )

            if decision['action'] == 'buy':
                result = await self.trading_engine.execute_buy(
                    token_address=decision['token_address'],
                    amount_usd=decision['position_size'],
                    price=decision['entry_price'],
                    stop_loss=decision['stop_loss'],
                    take_profit=decision['take_profit']
                )
            else:
                result = await self.trading_engine.execute_sell(
                    token_address=decision['token_address'],
                    price=decision['entry_price']
                )

            # Send execution notification
            await self.notifier.send_trade_execution(
                token_address=decision['token_address'],
                action=decision['action'].upper(),
                amount=decision['position_size'],
                price=decision['entry_price'],
                status=result.get('status', 'UNKNOWN').upper()
            )

            return result.get('status') == 'success'

        except Exception as e:
            logger.error(f"Error executing trade: {e}")
            await self.notifier.send_alert(
                title="Trade Execution Error",
                message=f"Failed to execute {decision['action']} for {decision['symbol']}: {str(e)}",
                level="ERROR"
            )
            return False

    async def scan_tokens(self):
        """Scan for new tokens and trading opportunities."""
        logger.info("Scanning for tokens...")
        print("🔍 Starting token scan...")

        try:
            # Since SolSniffer is down, use popular Solana tokens
            test_tokens = [
                {'address': 'So11111111111111111111111111111111111111112'},  # SOL
                {'address': 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v'},  # USDC
                {'address': 'DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263'},  # Bonk
                {'address': 'JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN'},   # Jupiter
            ]

            print(f"Analyzing {len(test_tokens)} tokens...")

            for token_data in test_tokens:
                token_address = token_data.get('address')
                if not token_address:
                    continue

                print(f"  → Analyzing {token_address[:8]}...")

                # Analyze token
                analysis = await self.analyze_token(token_address)
                if not analysis:
                    print(f"  ❌ No analysis data")
                    continue

                print(f"  ✅ Analysis complete")

                # Make trading decision
                decision = await self.make_trading_decision(analysis)
                if decision:
                    print(f"  🎯 TRADING OPPORTUNITY: {decision['symbol']}")
                    logger.info(f"Trading opportunity found: {decision['symbol']}")
                    await self.execute_trade(decision)
                else:
                    print(f"  ⏸️  No trade signal")

                # Delay between analyses
                await asyncio.sleep(2)

            print("✅ Scan cycle complete\n")

        except Exception as e:
            logger.error(f"Error scanning tokens: {e}")
            print(f"❌ Error: {e}")

    async def monitor_positions(self):
        """Monitor open positions for stop loss/take profit."""
        if settings.is_paper_trading():
            # Get current prices for all open positions
            positions = self.trading_engine.position_manager.get_all_positions()

            price_updates = {}
            for position in positions:
                try:
                    profile = await self.dexscreener.get_token_profile(position.token_address)
                    if profile:
                        price_updates[position.token_address] = profile['price_usd']
                except Exception as e:
                    logger.error(f"Error getting price for {position.token_address}: {e}")

            # Update positions
            await self.trading_engine.update_prices(price_updates)

    async def main_loop(self):
        """Main trading loop."""
        logger.info("Starting main trading loop...")

        scan_interval = 300  # 5 minutes
        monitor_interval = 60  # 1 minute

        last_scan = 0
        last_monitor = 0

        while self.running:
            try:
                current_time = asyncio.get_event_loop().time()

                # Scan for new opportunities
                if current_time - last_scan >= scan_interval:
                    await self.scan_tokens()
                    last_scan = current_time

                # Monitor positions
                if current_time - last_monitor >= monitor_interval:
                    await self.monitor_positions()
                    last_monitor = current_time

                # Sleep briefly
                await asyncio.sleep(10)

            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                await asyncio.sleep(30)

    async def start(self):
        """Start the trading bot."""
        logger.info("Starting Solana Trading Bot...")
        self.running = True

        # Send startup notification
        await self.notifier.send_startup_message()

        # Start health monitoring in background
        asyncio.create_task(self.health_checker.monitor())

        # Run main loop
        await self.main_loop()

    async def stop(self):
        """Stop the trading bot."""
        logger.info("Stopping Solana Trading Bot...")
        self.running = False

        # Stop health monitoring
        self.health_checker.stop()

        # Send shutdown notification
        await self.notifier.send_shutdown_message()

        # Close connections
        await self.alchemy.close()
        await self.solsniffer.close()
        await self.dexscreener.close()
        await self.twitter.close()

        logger.info("Bot stopped successfully")


async def main():
    """Main entry point."""
    bot = SolanaTradingBot()

    # Setup signal handlers
    def signal_handler(sig, frame):
        logger.info("Received shutdown signal")
        asyncio.create_task(bot.stop())

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        await bot.start()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        await bot.stop()
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot terminated by user")
