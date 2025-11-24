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
from .monitoring.telegram_commands import TelegramCommandHandler
from .blockchain import AlchemyClient, SolSnifferClient, WalletTracker
from .market import DexScreenerClient, MarketAnalyzer, JupiterClient
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
        self.trading_paused = False  # Can pause trading via Telegram

        # Monitoring
        self.notifier = TelegramNotifier(
            bot_token=settings.api.telegram_bot_token,
            chat_id=settings.api.telegram_chat_id
        )
        self.health_checker = HealthChecker()
        self.command_handler = TelegramCommandHandler(
            bot_token=settings.api.telegram_bot_token,
            chat_id=settings.api.telegram_chat_id,
            bot_instance=self
        )

        # Blockchain
        self.alchemy = AlchemyClient(settings.api.alchemy_api_key)
        self.solsniffer = SolSnifferClient(settings.api.solsniffer_api_key)
        self.wallet_tracker = WalletTracker()

        # Market
        self.dexscreener = DexScreenerClient(settings.api.dexscreener_api_key)
        self.market_analyzer = MarketAnalyzer(
            min_liquidity_usd=settings.trading.min_liquidity_usd
        )

        # Token Discovery
        self.jupiter = JupiterClient()

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
        # Core components - essential for trading
        self.health_checker.register_component('alchemy', self.alchemy.health_check)
        self.health_checker.register_component('jupiter', self.jupiter.health_check)
        self.health_checker.register_component('dexscreener', self.dexscreener.health_check)

        # Optional components - disabled to reduce log noise
        # These components are not critical for core trading functionality
        # self.health_checker.register_component('solsniffer', self.solsniffer.health_check)
        # self.health_checker.register_component('twitter', self.twitter.health_check)
        # self.health_checker.register_component('wallet_tracker', self.wallet_tracker.health_check)

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
            # 1. Get market data from BOTH sources for validation
            dex_profile = await self.dexscreener.get_token_profile(token_address)
            jupiter_data = await self.jupiter.get_token_price_data(token_address)

            # Validate we have data from at least one source
            if not dex_profile and not jupiter_data:
                logger.warning(f"No market data from either source for {token_address}")
                return None

            # Cross-validate price and liquidity
            if dex_profile and jupiter_data:
                dex_price = dex_profile['price_usd']
                jup_price = jupiter_data['price_usd']
                price_diff_pct = abs((dex_price - jup_price) / dex_price) * 100

                if price_diff_pct > 20:
                    # Large divergence - suspicious data
                    logger.warning(
                        f"⚠️  PRICE DIVERGENCE in analysis: {token_address[:8]}... "
                        f"DexScreener ${dex_price:.8f} vs Jupiter ${jup_price:.8f} ({price_diff_pct:.1f}%)"
                    )
                    # Don't trade on suspicious data
                    return None

            # Use DexScreener as primary (has more metadata), but validated
            profile = dex_profile if dex_profile else jupiter_data

            # 2. Get security data
            security_data = await self.solsniffer.analyze_token(token_address)

            # 3. Get social sentiment (optional - skip if rate limited)
            token_symbol = profile.get('symbol', 'UNKNOWN')
            try:
                social_data = await self.twitter.analyze_token_buzz(token_symbol, token_address)
                tweets = await self.twitter.search_token_mentions(token_symbol, token_address)
                sentiment_analysis = self.sentiment_analyzer.analyze_tweets(tweets)
                coordination_analysis = self.sentiment_analyzer.detect_coordinated_activity(tweets)
            except Exception as e:
                # Twitter optional - use neutral defaults with proper structure
                logger.debug(f"Twitter sentiment unavailable for {token_symbol}: {e}")
                social_data = {
                    'mentions': 0,
                    'sentiment': 'neutral',
                    'buzz_score': 0.5,
                    'tweet_count': 0,
                    'influential_mentions': 0
                }
                sentiment_analysis = {
                    'sentiment': 'neutral',
                    'score': 0.5,
                    'normalized_score': 0.5,
                    'confidence': 0.6  # Moderate confidence even without Twitter
                }
                coordination_analysis = {
                    'coordinated': False,
                    'coordination_score': 0.0
                }

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
            # Wrap trade execution with timeout
            async with asyncio.timeout(30):  # 30 second timeout for single trade
                return await self._execute_trade_impl(decision)
        except asyncio.TimeoutError:
            logger.error(f"Trade execution timed out for {decision['symbol']}")
            print(f"      ⚠️  Trade execution timed out - skipping")
            return False
        except Exception as e:
            logger.error(f"Error executing trade for {decision['symbol']}: {e}")
            print(f"      ❌ Trade execution error: {e}")
            return False

    async def _execute_trade_impl(self, decision: dict) -> bool:
        """Internal implementation of trade execution."""
        print(f"      🔧 EXECUTING TRADE: {decision['action'].upper()} {decision['symbol']}")
        print(f"      💵 Amount: ${decision['position_size']:.2f} @ ${decision['entry_price']:.8f}")

        try:
            # Send trade signal notification
            print(f"      📱 Sending Telegram notification...")
            await self.notifier.send_trade_signal(
                token_address=decision['token_address'],
                action=decision['action'].upper(),
                confidence=decision['confidence'],
                price=decision['entry_price'],
                reasons=decision['reasons']
            )

            print(f"      💰 Calling trading engine...")
            if decision['action'] == 'buy':
                result = await self.trading_engine.execute_buy(
                    token_address=decision['token_address'],
                    amount_usd=decision['position_size'],
                    price=decision['entry_price'],
                    stop_loss=decision['stop_loss'],
                    take_profit=decision['take_profit']
                )
                print(f"      ✅ Trade result: {result}")
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
        # Check if trading is paused
        if self.trading_paused:
            print("⏸️  Trading paused - skipping token scan")
            logger.info("Token scan skipped - trading paused")
            return

        try:
            # Wrap entire scan with timeout to prevent hangs
            async with asyncio.timeout(300):  # 5 minute timeout for entire scan cycle
                await self._scan_tokens_impl()
        except asyncio.TimeoutError:
            logger.error("Token scan timed out after 5 minutes")
            print("  ⚠️  Token scan timed out - will retry next cycle")
        except Exception as e:
            logger.error(f"Error in token scan: {e}")
            print(f"  ❌ Token scan error: {e}")

    async def _scan_tokens_impl(self):
        """Internal implementation of token scanning."""
        logger.info("Scanning for tokens...")
        print("🔍 Starting token scan...")

        try:
            # Get new tokens from Jupiter
            print("  📡 Fetching new tokens from Jupiter...")
            new_tokens = await self.jupiter.get_recent_tokens(limit=20)

            if not new_tokens:
                print("  ⚠️  No tokens returned from Jupiter, using fallback tokens")
                logger.warning("Jupiter returned no tokens, using fallback")
                # Fallback to popular tokens if Jupiter fails
                new_tokens = [
                    {'address': 'So11111111111111111111111111111111111111112'},  # SOL
                    {'address': 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v'},  # USDC
                    {'address': 'DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263'},  # Bonk
                    {'address': 'JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN'},   # Jupiter
                ]
            else:
                print(f"  ✅ Found {len(new_tokens)} new tokens from Jupiter!")
                logger.info(f"Retrieved {len(new_tokens)} tokens from Jupiter")

            # Get currently open positions
            if settings.is_paper_trading():
                open_positions = self.trading_engine.position_manager.open_positions
            else:
                open_positions = self.position_manager.open_positions

            print(f"Analyzing {len(new_tokens)} tokens ({len(open_positions)} positions already open)...")

            for token_data in new_tokens:
                token_address = token_data.get('address')
                if not token_address:
                    logger.warning(f"Skipping token with no address: {token_data}")
                    continue

                # Skip tokens we already have positions in
                if token_address in open_positions:
                    print(f"  ⏭️  Skipping {token_address[:8]}... (position already open)")
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
        try:
            # Wrap entire method with timeout to prevent hangs
            async with asyncio.timeout(60):  # 60 second timeout for entire monitoring cycle
                await self._monitor_positions_impl()
        except asyncio.TimeoutError:
            logger.error("Position monitoring timed out after 60 seconds")
            print("  ⚠️  Position monitoring timed out - will retry next cycle")
        except Exception as e:
            logger.error(f"Error in position monitoring: {e}")
            print(f"  ❌ Position monitoring error: {e}")

    async def _monitor_positions_impl(self):
        """Internal implementation of position monitoring."""
        if settings.is_paper_trading():
            # Get current prices for all open positions
            positions = self.trading_engine.position_manager.get_all_positions()

            if not positions:
                return  # No positions to monitor

            print(f"📊 Monitoring {len(positions)} open position(s)...")
            logger.info(f"Monitoring {len(positions)} positions")

            price_updates = {}
            liquidity_updates = {}  # Track liquidity for rug detection

            for position in positions:
                try:
                    # DUAL-SOURCE VALIDATION: Query both DexScreener and Jupiter
                    dex_profile = await self.dexscreener.get_token_profile(position.token_address)
                    jupiter_data = await self.jupiter.get_token_price_data(position.token_address)

                    # Extract data from both sources
                    dex_price = dex_profile['price_usd'] if dex_profile else None
                    dex_liquidity = dex_profile.get('liquidity_usd', 0.0) if dex_profile else 0.0

                    jupiter_price = jupiter_data['price_usd'] if jupiter_data else None
                    jupiter_liquidity = jupiter_data.get('liquidity_usd', 0.0) if jupiter_data else 0.0

                    # Cross-validate and choose best data
                    current_price = None
                    liquidity = 0.0
                    data_source = None

                    if dex_price and jupiter_price:
                        # Both sources available - cross-validate
                        price_diff_pct = abs((dex_price - jupiter_price) / dex_price) * 100

                        if price_diff_pct < 10:
                            # Prices agree (within 10%) - use average
                            current_price = (dex_price + jupiter_price) / 2
                            liquidity = max(dex_liquidity, jupiter_liquidity)  # Use higher liquidity
                            data_source = "✅ DexScreener + Jupiter"
                            logger.debug(f"Price agreement for {position.token_address[:8]}: Dex ${dex_price:.8f} vs Jup ${jupiter_price:.8f} (diff: {price_diff_pct:.1f}%)")
                        else:
                            # Large divergence - flag as suspicious
                            logger.warning(
                                f"⚠️  PRICE DIVERGENCE: {position.token_address[:8]}... "
                                f"DexScreener ${dex_price:.8f} vs Jupiter ${jupiter_price:.8f} ({price_diff_pct:.1f}% diff!)"
                            )
                            # Use DexScreener as primary (more reliable for liquidity)
                            current_price = dex_price
                            liquidity = dex_liquidity
                            data_source = "⚠️  DexScreener (divergence)"

                    elif dex_price:
                        # Only DexScreener available
                        current_price = dex_price
                        liquidity = dex_liquidity
                        data_source = "📊 DexScreener"

                    elif jupiter_price:
                        # Only Jupiter available - use as fallback
                        current_price = jupiter_price
                        liquidity = jupiter_liquidity
                        data_source = "🔄 Jupiter (fallback)"
                        logger.info(f"Using Jupiter fallback for {position.token_address[:8]}...")

                    else:
                        # No data from either source
                        logger.error(f"❌ No price data from either source for {position.token_address[:8]}...")
                        # Mark position as having failed price update
                        self.trading_engine.position_manager.mark_position_price_failed(position.token_address)
                        continue

                    # Now validate the chosen price
                    profile = dex_profile or jupiter_data  # Use whichever is available for symbol/name

                    # 🛡️ ENHANCED PRICE VALIDATION - Reject bad data that would cause 100% loss
                    # Check 1: None or not a number
                    if current_price is None:
                        print(f"  ⚠️  Price is None - SKIPPING UPDATE")
                        logger.warning(f"Price is None for {position.token_address[:8]}")
                        continue

                    # Check 2: NaN (not a number)
                    try:
                        if not isinstance(current_price, (int, float)) or (isinstance(current_price, float) and (current_price != current_price)):  # NaN check
                            print(f"  ⚠️  Price is NaN - SKIPPING UPDATE")
                            logger.warning(f"Price is NaN for {position.token_address[:8]}")
                            continue
                    except (TypeError, ValueError):
                        print(f"  ⚠️  Invalid price type - SKIPPING UPDATE")
                        logger.warning(f"Invalid price type for {position.token_address[:8]}: {type(current_price)}")
                        continue

                    # Check 3: Infinity
                    try:
                        import math
                        if math.isinf(current_price):
                            print(f"  ⚠️  Price is Infinity - SKIPPING UPDATE")
                            logger.warning(f"Price is Infinity for {position.token_address[:8]}")
                            continue
                    except:
                        pass

                    # Check 4: Zero or negative
                    if current_price <= 0:
                        print(f"  ⚠️  Bad price data: ${current_price} - SKIPPING UPDATE")
                        logger.warning(f"Invalid price ${current_price} for {position.token_address[:8]}")
                        continue

                    # Check 5: Extremely small (effectively zero, < $0.000000001)
                    if current_price < 1e-9:
                        print(f"  ⚠️  Price too small: ${current_price} - SKIPPING UPDATE")
                        logger.warning(f"Price too small ${current_price} for {position.token_address[:8]}")
                        continue

                    # Check 6: Suspicious price drops (>80% loss in one update)
                    try:
                        price_change_pct = ((current_price - position.entry_price) / position.entry_price) * 100
                    except (ZeroDivisionError, TypeError):
                        print(f"  ⚠️  Error calculating price change - SKIPPING UPDATE")
                        logger.error(f"Error calculating price change for {position.token_address[:8]}")
                        continue

                    if price_change_pct < -80:
                        print(f"  🚨 SUSPICIOUS: Price dropped {price_change_pct:.1f}% - SKIPPING (likely bad data)")
                        logger.error(
                            f"Rejected suspicious price for {position.token_address[:8]}: "
                            f"${position.entry_price:.8f} → ${current_price:.8f} ({price_change_pct:.1f}%)"
                        )
                        continue

                    # Price validated - safe to use
                    price_updates[position.token_address] = current_price
                    liquidity_updates[position.token_address] = liquidity

                    # Calculate current P&L
                    pnl_percent = ((current_price - position.entry_price) / position.entry_price) * 100

                    # Show price update with data source
                    symbol = profile.get('symbol', position.token_address[:8])
                    print(f"  💹 {symbol}: ${current_price:.8f} ({pnl_percent:+.2f}%) [{data_source}]")

                    # Check if close to stop loss or take profit/trailing stop
                    if position.use_trailing_stop:
                        # Show trailing stop info
                        print(f"  🔄 Trailing stop: ${position.trailing_stop_price:.8f} ({position.trailing_stop_percent:.0f}% below peak ${position.highest_price:.8f})")
                        # Warn if close to trailing stop
                        if current_price <= position.trailing_stop_price * 1.02:  # Within 2% of trailing stop
                            print(f"  ⚠️  Warning: Close to trailing stop!")
                    else:
                        # Fixed stop loss / take profit
                        sl_distance = ((current_price - position.stop_loss) / position.stop_loss) * 100
                        tp_distance = ((position.take_profit - current_price) / current_price) * 100

                        if sl_distance < 5:  # Within 5% of stop loss
                            print(f"  ⚠️  Warning: Close to stop loss (${position.stop_loss:.8f})")
                        elif tp_distance < 10:  # Within 10% of take profit
                            print(f"  🎯 Near take profit target (${position.take_profit:.8f})")

                except Exception as e:
                    logger.error(f"Error getting price for {position.token_address}: {e}")
                    print(f"  ❌ Error updating price for {position.token_address[:8]}...")
                    # Mark position as having failed price update
                    self.trading_engine.position_manager.mark_position_price_failed(position.token_address)

            # Update positions (this triggers stop loss/take profit checks AND rug detection)
            await self.trading_engine.update_prices(price_updates, liquidity_updates)
            print()

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

        # Start Telegram command handler
        asyncio.create_task(self.command_handler.start())

        # Start health monitoring in background
        asyncio.create_task(self.health_checker.monitor())

        # Run main loop
        await self.main_loop()

    async def stop(self):
        """Stop the trading bot."""
        logger.info("Stopping Solana Trading Bot...")
        self.running = False

        # Stop Telegram command handler
        await self.command_handler.stop()

        # Stop health monitoring
        self.health_checker.stop()

        # Send shutdown notification
        await self.notifier.send_shutdown_message()

        # Close connections
        await self.alchemy.close()
        await self.jupiter.close()
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
