"""
Main entry point for the Solana Trading Bot.
Orchestrates all components and manages the trading loop.
"""

import asyncio
import signal
import sys
import os
from datetime import datetime
from typing import Optional

from .config import settings
from .monitoring import setup_logger, get_logger, TelegramNotifier, HealthChecker
from .monitoring.telegram_commands import TelegramCommandHandler
from .blockchain import AlchemyClient, SolSnifferClient, WalletTracker, RugCheckClient, WhaleAnalyzer, MovementDetector
from .blockchain.jupiter_executor import JupiterSwapExecutor
from .blockchain.wallet_manager import WalletManager
from .market import DexScreenerClient, MarketAnalyzer, JupiterClient, VolumeAnalyzer, BirdeyeClient
from .market.coingecko_client import CoinGeckoClient
from .market.apify_client import ApifyDexScreenerClient
from .social import TwitterClient, SentimentAnalyzer
from .ai import SentimentModel, PricePredictor, RiskAssessor
from .trading import TelegramExecutor, PositionManager, PaperTradingEngine
from .trading.live_trading import LiveTradingEngine
from .data import MLDataCollector

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

        # Enhanced Monitoring System
        from .monitoring import MetricsCollector, AlertManager, Dashboard
        self.metrics = MetricsCollector()
        self.alert_manager = AlertManager(self.notifier)
        self.dashboard = Dashboard(self.metrics)

        # Register APIs for monitoring
        self.metrics.register_api('alchemy')
        self.metrics.register_api('jupiter')
        self.metrics.register_api('dexscreener')
        self.metrics.register_api('twitter')
        self.metrics.register_api('solsniffer')
        self.metrics.register_api('rugcheck')
        self.metrics.register_api('whale_analyzer')
        self.metrics.register_api('movement_detector')
        # New multi-source system APIs
        self.metrics.register_api('coingecko')  # Market monitor (BTC/ETH/SOL)
        self.metrics.register_api('rugcheck_holder')  # RugCheck holder analysis
        self.metrics.register_api('birdeye')  # Birdeye API

        # Set up default alert rules
        alert_config = {
            'ALERT_API_DOWN_COOLDOWN': int(os.getenv('ALERT_API_DOWN_MINUTES', '5')),
            'ALERT_ERROR_RATE_PER_HOUR': int(os.getenv('ALERT_ERROR_RATE_PER_HOUR', '10')),
            'ALERT_NO_TOKENS_COOLDOWN': int(os.getenv('ALERT_NO_TOKENS_MINUTES', '30')),
            'ALERT_COOLDOWN_MINUTES': int(os.getenv('ALERT_COOLDOWN_MINUTES', '15'))
        }
        self.alert_manager.setup_default_rules(alert_config)

        # === FEATURE ENABLE FLAGS (Test features one by one) ===
        self.enable_rugcheck = os.getenv('ENABLE_RUGCHECK_API', 'false').lower() == 'true'
        self.enable_whale_tracking = os.getenv('ENABLE_WHALE_TRACKING', 'false').lower() == 'true'
        self.enable_movement_detection = os.getenv('ENABLE_MOVEMENT_DETECTION', 'false').lower() == 'true'
        self.enable_twitter_sentiment = os.getenv('ENABLE_TWITTER_SENTIMENT', 'false').lower() == 'true'
        self.enable_volume_analyzer = os.getenv('ENABLE_VOLUME_ANALYZER', 'false').lower() == 'true'

        # === MULTI-SOURCE SYSTEM FLAGS (New enhanced monitoring) ===
        self.enable_multi_source_aggregator = os.getenv('ENABLE_MULTI_SOURCE_AGGREGATOR', 'false').lower() == 'true'
        self.enable_rugcheck_holder_analysis = os.getenv('ENABLE_RUGCHECK_HOLDER_ANALYSIS', 'false').lower() == 'true'
        self.enable_market_monitor = os.getenv('ENABLE_MARKET_MONITOR', 'false').lower() == 'true'
        self.enable_dynamic_scorer = os.getenv('ENABLE_DYNAMIC_SCORER', 'false').lower() == 'true'

        # Blockchain (core - always enabled)
        self.alchemy = AlchemyClient(settings.api.alchemy_api_key)
        self.solsniffer = SolSnifferClient(settings.api.solsniffer_api_key)
        self.wallet_tracker = WalletTracker()

        # RugCheck (optional)
        if self.enable_rugcheck:
            self.rugcheck = RugCheckClient(settings.api.rugcheck_api_key)
            logger.info("✅ RugCheck API ENABLED")
        else:
            self.rugcheck = None
            logger.info("🔒 RugCheck API DISABLED")

        # Whale Tracking (optional)
        if self.enable_whale_tracking:
            self.whale_analyzer = WhaleAnalyzer(settings.api.solscan_api_key)
            logger.info("✅ Whale tracking ENABLED")
        else:
            self.whale_analyzer = None
            logger.info("🔒 Whale tracking DISABLED")

        # Movement Detection (optional)
        if self.enable_movement_detection:
            self.movement_detector = MovementDetector(settings.api.solscan_api_key)
            logger.info("✅ Movement detection ENABLED")
        else:
            self.movement_detector = None
            logger.info("🔒 Movement detection DISABLED")

        # Market (core - always enabled)
        self.dexscreener = DexScreenerClient(settings.api.dexscreener_api_key)
        self.birdeye = BirdeyeClient(settings.api.birdeye_api_key) if settings.api.birdeye_api_key else None

        # CoinGecko (optional - top gainers/losers)
        coingecko_api_key = os.getenv('COINGECKO_API_KEY')
        self.coingecko = CoinGeckoClient(coingecko_api_key) if coingecko_api_key and coingecko_api_key != 'your_coingecko_api_key_here' else None

        # Apify DexScreener scraper (optional - BEST for GAINERS)
        apify_api_token = os.getenv('APIFY_API_TOKEN')
        self.apify = ApifyDexScreenerClient(apify_api_token) if apify_api_token and apify_api_token != 'your_apify_api_token_here' else None

        self.market_analyzer = MarketAnalyzer(
            min_liquidity_usd=settings.trading.min_liquidity_usd,
            min_volume_24h=settings.trading.min_volume_24h
        )

        # Volume Analyzer (optional)
        if self.enable_volume_analyzer:
            self.volume_analyzer = VolumeAnalyzer()
            logger.info("✅ Volume analyzer ENABLED")
        else:
            self.volume_analyzer = None
            logger.info("🔒 Volume analyzer DISABLED")

        # Token Discovery (core - always enabled)
        self.jupiter = JupiterClient()

        # Social (optional)
        if self.enable_twitter_sentiment:
            self.twitter = TwitterClient(settings.api.twitter_bearer_token)
            self.sentiment_analyzer = SentimentAnalyzer()
            logger.info("✅ Twitter sentiment analysis ENABLED")
        else:
            self.twitter = None
            self.sentiment_analyzer = None
            logger.info("🔒 Twitter sentiment DISABLED")

        # AI Models (core - always enabled)
        self.sentiment_model = SentimentModel()
        self.price_predictor = PricePredictor()
        self.risk_assessor = RiskAssessor(
            max_position_size=settings.trading.max_position_size
        )

        # Trading
        if settings.is_paper_trading():
            logger.info("📄 Paper trading mode enabled")
            self.trading_engine = PaperTradingEngine(initial_capital=1000.0)
            self.position_manager = PositionManager(
                max_open_positions=settings.risk.max_open_positions
            )
        else:
            logger.warning("💰 LIVE TRADING MODE ENABLED")
            logger.warning("=" * 80)
            logger.warning("⚠️  REAL MONEY AT RISK - Ensure wallet is funded and tested!")
            logger.warning("=" * 80)

            # Initialize wallet
            encryption_key = os.getenv('WALLET_ENCRYPTION_KEY')
            encrypted_key = os.getenv('SOLANA_PRIVATE_KEY_ENCRYPTED')

            if not encryption_key or not encrypted_key:
                logger.error("❌ Wallet credentials not found in .env")
                logger.error("Required: WALLET_ENCRYPTION_KEY and SOLANA_PRIVATE_KEY_ENCRYPTED")
                raise ValueError("Missing wallet credentials for live trading")

            wallet = WalletManager(encryption_key=encryption_key)
            success = wallet.load_wallet_from_encrypted_key(encrypted_key)

            if not success:
                logger.error("❌ Failed to load wallet from encrypted key")
                raise ValueError("Wallet loading failed")

            logger.info(f"✅ Wallet loaded: {wallet.get_public_key()}")

            # Initialize Jupiter executor with wallet
            rpc_url = os.getenv('SOLANA_RPC_URL', 'https://api.mainnet-beta.solana.com')
            use_jito = os.getenv('USE_JITO', 'true').lower() == 'true'

            jupiter_executor = JupiterSwapExecutor(
                rpc_url=rpc_url,
                use_jito=use_jito,
                paper_trading=False  # LIVE MODE
            )
            jupiter_executor.set_wallet(wallet)

            logger.info(f"✅ Jupiter executor initialized (Jito: {use_jito})")

            # Initialize live trading engine
            # Get absolute path for state file (in project root)
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            state_file = os.path.join(project_root, 'live_trading_state.json')

            self.position_manager = PositionManager(
                max_open_positions=settings.risk.max_open_positions
            )
            self.trading_engine = LiveTradingEngine(
                jupiter_executor=jupiter_executor,
                position_manager=self.position_manager,
                max_open_positions=settings.risk.max_open_positions,
                state_file=state_file
            )

            logger.info(f"✅ Live trading engine ready (state: {state_file})")
            logger.warning("⚠️  Start with SMALL position sizes for testing!")

        # ML Data Collection
        self.ml_collector = MLDataCollector()
        logger.info("📊 ML data collection enabled - all trades will be logged for future training")

        # Connect ML collector to trading engine
        from .trading.paper_trading import set_ml_collector
        set_ml_collector(self.ml_collector)

        # === MULTI-SOURCE MONITORING SYSTEM (Optional) ===
        # Enhanced bot with cross-validation, holder analysis, market monitoring, dynamic scoring
        self.enhanced_bot = None
        if self.enable_multi_source_aggregator:
            try:
                from .market.enhanced_bot_integration import EnhancedTradingIntegration
                self.enhanced_bot = EnhancedTradingIntegration(
                    jupiter_client=self.jupiter,
                    dexscreener_client=self.dexscreener,
                    birdeye_client=self.birdeye,
                    position_manager=self.position_manager,
                    trading_engine=self.trading_engine,
                    notifier=self.notifier
                )
                logger.info("✅ Multi-Source Monitoring System ENABLED")
                logger.info("   - Cross-validation across Jupiter/DexScreener/Birdeye")
                logger.info("   - 5-second position monitoring with force exit")
                logger.info("   - Holder analysis, market monitoring, dynamic scoring")
            except Exception as e:
                logger.error(f"Failed to initialize enhanced bot: {e}")
                self.enable_multi_source_aggregator = False

        # Register health checks
        self._register_health_checks()

        logger.info("Bot initialization complete")

    def _register_health_checks(self):
        """Register component health checks."""
        # Core components - essential for trading
        self.health_checker.register_component('alchemy', self.alchemy.health_check)
        self.health_checker.register_component('jupiter', self.jupiter.health_check)
        self.health_checker.register_component('dexscreener', self.dexscreener.health_check)
        if self.birdeye:
            self.health_checker.register_component('birdeye', self.birdeye.health_check)
        if self.coingecko:
            self.health_checker.register_component('coingecko', self.coingecko.health_check)
        if self.apify:
            self.health_checker.register_component('apify', self.apify.health_check)

        # Optional components - disabled to reduce log noise
        # These components are not critical for core trading functionality
        # self.health_checker.register_component('solsniffer', self.solsniffer.health_check)
        # self.health_checker.register_component('twitter', self.twitter.health_check)
        # self.health_checker.register_component('wallet_tracker', self.wallet_tracker.health_check)

    async def analyze_token(self, token_address: str, jupiter_token_data: Optional[dict] = None) -> Optional[dict]:
        """
        Perform comprehensive analysis on a token.

        Args:
            token_address: Token contract address
            jupiter_token_data: Optional pre-fetched data from Jupiter discovery
                              (includes usdPrice, liquidity, mcap, etc.)

        Returns:
            Analysis results dictionary or None
        """
        logger.info(f"Analyzing token: {token_address}")

        try:
            # 0. EARLY FILTER: RugCheck risk assessment (if enabled)
            import time
            rug_check = None
            if self.enable_rugcheck and self.rugcheck:
                rug_start = time.time()
                rug_check = await self.rugcheck.quick_check(token_address)
                rug_time_ms = (time.time() - rug_start) * 1000
                self.metrics.record_api_call('rugcheck', success=True, response_time_ms=rug_time_ms)

                # Block high-risk tokens immediately (if strict mode enabled)
                if self.settings.trading.rugcheck_strict_mode:
                    if rug_check['risk_level'] in ['critical', 'high'] and not rug_check['is_safe']:
                        logger.warning(
                            f"🚫 Token {token_address[:8]}... REJECTED by RugCheck: "
                            f"Risk={rug_check['risk_level']}, Score={rug_check['risk_score']}, "
                            f"Risks={rug_check['risks']}"
                        )
                        await self.notifier.send_message(
                            f"🚫 **RugCheck Alert**\n"
                            f"Token: `{token_address[:8]}...`\n"
                            f"Risk Level: **{rug_check['risk_level'].upper()}**\n"
                            f"Score: {rug_check['risk_score']}/100\n"
                            f"Risks: {', '.join(rug_check['risks'][:3])}"
                        )
                        return None

                    # Also check minimum score threshold
                    if rug_check['risk_score'] < self.settings.trading.rugcheck_min_score:
                        logger.warning(
                            f"🚫 Token {token_address[:8]}... REJECTED: "
                            f"RugCheck score {rug_check['risk_score']} < minimum {self.settings.trading.rugcheck_min_score}"
                        )
                        return None

                logger.info(
                    f"✅ RugCheck passed: {token_address[:8]}... "
                    f"(Risk: {rug_check['risk_level']}, Score: {rug_check['risk_score']})"
                )
            else:
                logger.debug("RugCheck API disabled - skipping risk assessment")

            # 1. Get market data - prioritize Jupiter discovery data if available
            profile = None

            # If Jupiter already provided price/liquidity data in discovery, use it!
            if jupiter_token_data and jupiter_token_data.get('usdPrice'):
                # Convert Jupiter discovery format to profile format
                profile = {
                    'address': token_address,
                    'symbol': jupiter_token_data.get('symbol', 'UNKNOWN'),
                    'name': jupiter_token_data.get('name', 'Unknown'),
                    'price_usd': float(jupiter_token_data.get('usdPrice', 0)),
                    'liquidity_usd': float(jupiter_token_data.get('liquidity', 0)),
                    'volume_24h': 0,  # Not in discovery data
                    'price_change_24h': 0,  # Not in discovery data
                    'market_cap': float(jupiter_token_data.get('mcap', 0)),
                    'fdv': float(jupiter_token_data.get('fdv', 0)),
                    'pair_created_at': jupiter_token_data.get('createdAt'),
                    'source': 'jupiter_discovery'
                }
                logger.info(f"✅ Using Jupiter discovery data for {token_address[:12]}... (price: ${profile['price_usd']:.8f}, liq: ${profile['liquidity_usd']:,.0f})")

            # ALWAYS fetch DexScreener data if liquidity or volume is missing
            # Jupiter discovery often has price but missing/zero liquidity and volume
            if not profile or profile['price_usd'] == 0 or profile.get('liquidity_usd', 0) == 0 or profile.get('volume_24h', 0) == 0:
                # Try DexScreener first (has best liquidity + volume data)
                dex_profile = await self.dexscreener.get_token_profile(token_address)

                # Only call Jupiter search if DexScreener fails (reduce rate limit pressure)
                jupiter_data = None
                if not dex_profile:
                    jupiter_data = await self.jupiter.get_token_price_data(token_address)

                # Validate we have data from at least one source
                if not dex_profile and not jupiter_data:
                    logger.warning(f"No market data from either source for {token_address}")
                    return None

                # Use DexScreener as primary (has liquidity + volume), fallback to Jupiter
                # DexScreener is most reliable for liquidity and volume data
                profile = dex_profile if dex_profile else jupiter_data

                if profile:
                    logger.info(f"📊 Enriched with real data: {token_address[:12]}... (liq: ${profile.get('liquidity_usd', 0):,.0f}, vol: ${profile.get('volume_24h', 0):,.0f})")

            # CRITICAL: Safety check - ensure we have profile data before proceeding
            if not profile:
                logger.warning(f"⚠️  No profile data for {token_address} - skipping analysis")
                return None

            # 1.5. MULTI-LAYER SCREENING (Phase 3) - Additional smart money & risk filters
            volume_analysis = None
            whale_analysis = None
            movement_analysis = None

            # Volume breakout detection (if enabled)
            if self.enable_volume_analyzer and self.volume_analyzer and self.settings.trading.enable_volume_breakout and profile:
                try:
                    volume_analysis = self.volume_analyzer.detect_smart_money_accumulation(
                        token_address=token_address,
                        current_volume=profile.get('volume_24h', 0),
                        liquidity_usd=profile.get('liquidity_usd', 0)
                    )
                    logger.info(
                        f"📈 Volume: {volume_analysis['signal']} | "
                        f"Score: {volume_analysis['smart_money_score']:.2f} | "
                        f"Indicators: {', '.join(volume_analysis['indicators'][:2])}"
                    )
                except Exception as e:
                    logger.debug(f"Volume analysis skipped: {e}")
            elif not self.enable_volume_analyzer:
                logger.debug("Volume analyzer disabled - skipping volume breakout detection")

            # Whale concentration analysis (if enabled)
            if self.enable_whale_tracking and self.whale_analyzer and self.settings.trading.enable_whale_tracking:
                try:
                    whale_start = time.time()
                    token_supply = profile.get('fdv', 0) / profile.get('price_usd', 1) if profile.get('price_usd', 0) > 0 else None
                    whale_analysis = await self.whale_analyzer.quick_whale_check(token_address, token_supply)
                    whale_time_ms = (time.time() - whale_start) * 1000
                    self.metrics.record_api_call('whale_analyzer', success=True, response_time_ms=whale_time_ms)

                    if not whale_analysis['is_safe']:
                        logger.warning(
                            f"⚠️  Whale risk detected: {whale_analysis['whale_risk']} | "
                            f"Top holder: {whale_analysis.get('top_holder_percent', 0):.1f}% | "
                            f"Warnings: {', '.join(whale_analysis['warnings'][:2])}"
                        )
                    else:
                        logger.info(f"✅ Whale check passed: {whale_analysis['whale_risk']} risk")
                except Exception as e:
                    logger.debug(f"Whale analysis skipped: {e}")
            elif not self.enable_whale_tracking:
                logger.debug("Whale tracking disabled - skipping analysis")

            # Unusual movement detection (if enabled)
            if self.enable_movement_detection and self.movement_detector and self.settings.trading.enable_movement_detection:
                try:
                    movement_start = time.time()
                    movement_analysis = await self.movement_detector.quick_movement_check(token_address)
                    movement_time_ms = (time.time() - movement_start) * 1000
                    self.metrics.record_api_call('movement_detector', success=True, response_time_ms=movement_time_ms)

                    if not movement_analysis['is_safe']:
                        logger.warning(
                            f"🚨 Unusual movement: {movement_analysis['movement_risk']} | "
                            f"Pattern: {movement_analysis['pattern']} | "
                            f"Flags: {', '.join(movement_analysis['warnings'][:2])}"
                        )

                        # Block critical rug signals
                        if movement_analysis['rug_risk'] == 'critical':
                            logger.error(f"🚫 Token REJECTED: Critical rug signals detected")
                            await self.notifier.send_message(
                                f"🚨 **Critical Rug Signals**\n"
                                f"Token: `{token_address[:8]}...`\n"
                                f"Signals: {', '.join(movement_analysis['rug_signals'])}"
                            )
                            return None
                    else:
                        logger.info(f"✅ Movement check passed: {movement_analysis['movement_risk']} risk")
                except Exception as e:
                    logger.debug(f"Movement analysis skipped: {e}")

            # 2. Get security data
            security_data = await self.solsniffer.analyze_token(token_address)

            # 3. Get social sentiment (if enabled)
            token_symbol = profile.get('symbol', 'UNKNOWN')
            if self.enable_twitter_sentiment and self.twitter and self.sentiment_analyzer:
                try:
                    social_data = await self.twitter.analyze_token_buzz(token_symbol, token_address)
                    tweets = await self.twitter.search_token_mentions(token_symbol, token_address)
                    sentiment_analysis = self.sentiment_analyzer.analyze_tweets(tweets)
                    coordination_analysis = self.sentiment_analyzer.detect_coordinated_activity(tweets)
                    logger.debug(f"Twitter sentiment analyzed for {token_symbol}")
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
            else:
                # Twitter disabled - use neutral defaults
                logger.debug(f"Twitter sentiment disabled - using neutral scores")
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
                    'confidence': 0.6
                }
                coordination_analysis = {
                    'coordinated': False,
                    'coordination_score': 0.0
                }

            # 4. Generate market signal
            market_signal = self.market_analyzer.analyze_token(profile)

            # 6. Score sentiment
            sentiment_score = self.sentiment_model.score_sentiment(
                social_data=social_data,
                sentiment_analysis=sentiment_analysis,
                coordination_analysis=coordination_analysis
            )

            # 7. Predict price movement
            price_prediction = self.price_predictor.predict(
                token_address=token_address,
                current_price=profile['price_usd'],
                market_signal=market_signal.__dict__,
                sentiment_score=sentiment_score.__dict__,
                timeframe_hours=24
            )

            # 8. Assess risk
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
                'rug_check': rug_check,
                'volume_analysis': volume_analysis,
                'whale_analysis': whale_analysis,
                'movement_analysis': movement_analysis,
                'market_signal': market_signal,
                'sentiment_score': sentiment_score,
                'price_prediction': price_prediction,
                'risk_assessment': risk_assessment,
                'timestamp': datetime.now().isoformat()
            }

            # Build log message (handle None rug_check)
            rug_info = f"RugCheck={rug_check['risk_score']}/100" if rug_check else "RugCheck=disabled"
            logger.info(
                f"Analysis complete for {token_symbol}: "
                f"{rug_info}, "
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
        # Market signal must be 'buy' AND sentiment must NOT be 'avoid' (allow hold/buy/strong_buy)
        # This allows trading when Twitter unavailable (sentiment='hold') but blocks bearish tokens
        action = None
        if market_signal.signal_type == 'buy' and sentiment_score.recommendation != 'avoid':
            action = 'buy'
        elif market_signal.signal_type == 'sell':
            # Can't short on DEXs - only sell if we own the token
            token_address = analysis['token_address']
            if settings.is_paper_trading():
                has_position = token_address in self.trading_engine.position_manager.open_positions
            else:
                has_position = token_address in self.position_manager.open_positions

            if has_position:
                action = 'sell'
            else:
                print(f"    ⏭️  SELL signal ignored: no position in {analysis['symbol']} (can't short on DEX)")
                logger.info(f"SELL signal ignored - no position in {token_address[:8]}")
                return None

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
            'reasons': sentiment_score.reasoning + price_prediction.factors,
            # Store full analysis for ML data collection
            'analysis_data': analysis
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
            print(f"      💰 Calling trading engine...")
            if decision['action'] == 'buy':
                # Extract pair_created_at from analysis data for age-based strategy
                analysis_data = decision.get('analysis_data', {})
                profile = analysis_data.get('profile', {}) if analysis_data else {}
                pair_created_at = profile.get('pair_created_at', 0)

                result = await self.trading_engine.execute_buy(
                    token_address=decision['token_address'],
                    amount_usd=decision['position_size'],
                    price=decision['entry_price'],
                    stop_loss=decision['stop_loss'],
                    take_profit=decision['take_profit'],
                    analysis_data=analysis_data,
                    pair_created_at=pair_created_at  # Pass for age-based strategy selection
                )
                print(f"      ✅ Trade result: {result}")

                # ONLY send Telegram notification on SUCCESSFUL entry
                if result.get('status') == 'success':
                    print(f"      📱 Sending entry notification to Telegram...")
                    await self.notifier.send_entry_notification(
                        token_address=decision['token_address'],
                        symbol=decision['symbol'],
                        entry_price=decision['entry_price'],
                        position_size=decision['position_size'],
                        score=analysis_data.get('score', 0),
                        confidence=decision.get('confidence', 'medium'),
                        token_data=profile or {},
                        rugcheck_data=analysis_data.get('rug_check'),
                        market_data=None,  # Could add market conditions here
                        score_breakdown=analysis_data.get('score_breakdown'),
                        warnings=decision.get('warnings', []),
                        is_pumpfun=decision['token_address'].endswith('pump')
                    )
                # Failures are just logged, no Telegram spam
            else:
                result = await self.trading_engine.execute_sell(
                    token_address=decision['token_address'],
                    price=decision['entry_price']
                )

                # ONLY send Telegram notification on SUCCESSFUL exit
                if result.get('status') == 'success':
                    print(f"      📱 Sending exit notification to Telegram...")
                    # TODO: Implement exit notification with P&L data
                    # await self.notifier.send_exit_notification(...)

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
        """Internal implementation of token scanning - COMBINES all enabled sources."""
        logger.info("Scanning for tokens...")
        print("🔍 Starting token scan...")

        try:
            all_tokens = []  # Will combine tokens from all sources
            seen_addresses = set()  # Track duplicates

            # Get enable flags from environment (default: Jupiter enabled, others disabled for safety)
            enable_jupiter = os.getenv('ENABLE_JUPITER', 'true').lower() == 'true'
            enable_dexscreener = os.getenv('ENABLE_DEXSCREENER', 'false').lower() == 'true'
            enable_birdeye = os.getenv('ENABLE_BIRDEYE', 'false').lower() == 'true'
            enable_coingecko = os.getenv('ENABLE_COINGECKO', 'false').lower() == 'true'
            enable_apify = os.getenv('ENABLE_APIFY', 'false').lower() == 'true'

            print(f"  🔧 Token sources: Jupiter={enable_jupiter}, DexScreener={enable_dexscreener}, Birdeye={enable_birdeye}, CoinGecko={enable_coingecko}, Apify={enable_apify}")
            logger.info(f"Token source flags: ENABLE_JUPITER={enable_jupiter}, ENABLE_DEXSCREENER={enable_dexscreener}, ENABLE_BIRDEYE={enable_birdeye}, ENABLE_COINGECKO={enable_coingecko}, ENABLE_APIFY={enable_apify}")

            # 🚫 BLUECHIP FILTER - Define once, use everywhere
            # Skip these stable/high-cap tokens (won't 10x-100x)
            BLUECHIP_SYMBOLS = {'SOL', 'USDC', 'USDT', 'JUP', 'BONK', 'WIF', 'TRUMP', 'PYTH', 'RAY', 'ORCA'}
            BLUECHIP_ADDRESSES = {
                'So11111111111111111111111111111111111111112',  # SOL
                'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v',  # USDC
                'Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB',  # USDT
                'JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN',  # JUP
                'DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263',  # BONK
            }
            MAX_MARKET_CAP = 100_000_000  # $100M - tokens above this are too big to 10x

            # === SOURCE 1: JUPITER (CYCLING for gainers - finds movers!) ===
            if enable_jupiter:
                print("  📡 Fetching tokens from Jupiter (CYCLING discovery)...")
                try:
                    # 🔄 CYCLING: Rotates through toporganicscore → toptraded → toptrending
                    # This finds GAINERS and MOVERS, not just bluechips!
                    # category=None enables automatic cycling in jupiter_client.py
                    jupiter_tokens = await self.jupiter.get_trending_tokens(
                        category=None,  # Enable cycling (was hardcoded 'toporganicscore')
                        interval='1h',
                        limit=30
                    )

                    if jupiter_tokens:
                        # 🚫 Apply bluechip filter (using constants defined above)
                        filtered_tokens = []
                        for token in jupiter_tokens:
                            symbol = token.get('symbol', '').upper()
                            addr = token.get('address')
                            mcap = token.get('mcap', 0)

                            # Skip bluechips by symbol, address, or market cap
                            if symbol in BLUECHIP_SYMBOLS:
                                logger.debug(f"[JUP] Filtered out bluechip: {symbol}")
                                continue
                            if addr in BLUECHIP_ADDRESSES:
                                logger.debug(f"[JUP] Filtered out bluechip: {addr[:8]}...")
                                continue
                            if mcap and mcap > MAX_MARKET_CAP:
                                logger.debug(f"[JUP] Filtered out high mcap: {symbol} (${mcap/1e6:.1f}M)")
                                continue

                            filtered_tokens.append(token)

                        print(f"  ✅ Jupiter: Found {len(filtered_tokens)} tokens ({len(jupiter_tokens) - len(filtered_tokens)} bluechips filtered)")
                        logger.info(f"Jupiter returned {len(filtered_tokens)} tokens after bluechip filter")

                        for token in filtered_tokens:
                            addr = token.get('address')
                            if addr and addr not in seen_addresses:
                                all_tokens.append(token)
                                seen_addresses.add(addr)
                    else:
                        print("  ⚠️  Jupiter returned no tokens")
                        logger.warning("Jupiter tokens returned empty")
                except Exception as e:
                    logger.error(f"Jupiter error: {e}")
                    print(f"  ❌ Jupiter error: {e}")

            # === SOURCE 2: DEXSCREENER (Organic only - NO paid promotions) ===
            if enable_dexscreener:
                print("  📡 Fetching tokens from DexScreener (organic only)...")
                try:
                    # Get ORGANIC tokens - filters out boosted (paid promotions)
                    # Boosted tokens are usually scams!
                    # Reduced to 20-25 for better quality focus
                    dex_tokens = await self.dexscreener.get_organic_tokens(limit=25)

                    if dex_tokens:
                        # 🚫 Apply bluechip filter (using same constants as Jupiter)
                        filtered_dex_tokens = []
                        for token in dex_tokens:
                            symbol = token.get('symbol', '').upper()
                            addr = token.get('address')
                            mcap = token.get('mcap', 0)

                            # Skip bluechips by symbol, address, or market cap
                            if symbol in BLUECHIP_SYMBOLS:
                                logger.debug(f"[DEX] Filtered out bluechip: {symbol}")
                                continue
                            if addr in BLUECHIP_ADDRESSES:
                                logger.debug(f"[DEX] Filtered out bluechip: {addr[:8]}...")
                                continue
                            if mcap and mcap > MAX_MARKET_CAP:
                                logger.debug(f"[DEX] Filtered out high mcap: {symbol} (${mcap/1e6:.1f}M)")
                                continue

                            filtered_dex_tokens.append(token)

                        print(f"  ✅ DexScreener: Found {len(filtered_dex_tokens)} tokens ({len(dex_tokens) - len(filtered_dex_tokens)} bluechips filtered)")
                        logger.info(f"DexScreener returned {len(filtered_dex_tokens)} tokens after bluechip filter")

                        for token in filtered_dex_tokens:
                            addr = token.get('address')
                            if addr and addr not in seen_addresses:
                                all_tokens.append(token)
                                seen_addresses.add(addr)
                    else:
                        print("  ⚠️  DexScreener returned no organic tokens")
                        logger.warning("DexScreener organic tokens returned empty")
                except Exception as e:
                    logger.error(f"DexScreener error: {e}")
                    print(f"  ❌ DexScreener error: {e}")

            # === SOURCE 3: BIRDEYE (OPTIMIZED for GAINERS - reduced CU usage) ===
            # NOTE: Free tier is 30K CUs/month - we optimize by using SMALL limits
            # Birdeye HAS THE BEST GAINER DATA (priceChange24h, priceChange1h sorting!)
            # Cycling through: rank → liquidity → volume → priceChange24h → priceChange1h
            if enable_birdeye and self.birdeye:
                print("  📡 Fetching tokens from Birdeye (GAINERS focus)...")
                try:
                    # OPTIMIZED: Use limit=5 (was 12) to save CUs
                    # The cycling in birdeye_client.py will rotate through:
                    # - priceChange24h (24h GAINERS!)
                    # - priceChange1h (1h MOVERS!)
                    # - volume24hUSD (high interest)
                    # - liquidity (liquid tokens)
                    # - rank (trending)
                    trending = await self.birdeye.get_trending_tokens(limit=5)  # Reduced from 12

                    # Skip new_listings call to save CUs (trending already has new movers)
                    birdeye_tokens = trending or []

                    if birdeye_tokens:
                        # 🚫 Apply bluechip filter (same as Jupiter/DexScreener)
                        filtered_birdeye_tokens = []
                        for token in birdeye_tokens:
                            symbol = token.get('symbol', '').upper()
                            addr = token.get('address')
                            # Birdeye doesn't always have mcap, skip that filter

                            # Skip bluechips by symbol or address
                            if symbol in BLUECHIP_SYMBOLS:
                                logger.debug(f"[BIRDEYE] Filtered out bluechip: {symbol}")
                                continue
                            if addr in BLUECHIP_ADDRESSES:
                                logger.debug(f"[BIRDEYE] Filtered out bluechip: {addr[:8]}...")
                                continue

                            filtered_birdeye_tokens.append(token)

                        print(f"  ✅ Birdeye: Found {len(filtered_birdeye_tokens)} GAINERS ({len(birdeye_tokens) - len(filtered_birdeye_tokens)} bluechips filtered)")
                        logger.info(f"Birdeye returned {len(filtered_birdeye_tokens)} tokens after bluechip filter")

                        for token in filtered_birdeye_tokens:
                            addr = token.get('address')
                            if addr and addr not in seen_addresses:
                                all_tokens.append(token)
                                seen_addresses.add(addr)
                    else:
                        print("  ⚠️  Birdeye returned no tokens")
                        logger.warning("Birdeye returned no tokens")
                except Exception as e:
                    logger.error(f"Birdeye error: {e}")
                    print(f"  ❌ Birdeye error: {e}")

            # === SOURCE 4: COINGECKO (Top Gainers/Losers - FREE) ===
            # CoinGecko provides top gainers across ALL chains with Solana filtering
            # FREE tier: 30 calls/min (1,800/hour) - Perfect as supplement
            # Cycling through: top_gainers → trending → top_losers
            if enable_coingecko and self.coingecko:
                print("  📡 Fetching tokens from CoinGecko (Top Gainers)...")
                try:
                    # Use cycling method to rotate discovery strategies
                    coingecko_tokens = await self.coingecko.get_tokens_by_cycle(limit=10)

                    if coingecko_tokens:
                        # 🚫 Apply bluechip filter
                        filtered_cg_tokens = []
                        for token in coingecko_tokens:
                            symbol = token.get('symbol', '').upper()
                            addr = token.get('address')

                            # Skip bluechips by symbol or address
                            if symbol in BLUECHIP_SYMBOLS:
                                logger.debug(f"[CG] Filtered out bluechip: {symbol}")
                                continue
                            if addr in BLUECHIP_ADDRESSES:
                                logger.debug(f"[CG] Filtered out bluechip: {addr[:8]}...")
                                continue

                            filtered_cg_tokens.append(token)

                        print(f"  ✅ CoinGecko: Found {len(filtered_cg_tokens)} GAINERS ({len(coingecko_tokens) - len(filtered_cg_tokens)} bluechips filtered)")
                        logger.info(f"CoinGecko returned {len(filtered_cg_tokens)} tokens after bluechip filter")

                        for token in filtered_cg_tokens:
                            addr = token.get('address')
                            if addr and addr not in seen_addresses:
                                all_tokens.append(token)
                                seen_addresses.add(addr)
                    else:
                        print("  ⚠️  CoinGecko returned no tokens")
                        logger.warning("CoinGecko returned no tokens")
                except Exception as e:
                    logger.error(f"CoinGecko error: {e}")
                    print(f"  ❌ CoinGecko error: {e}")

            # === SOURCE 5: APIFY DEXSCREENER SCRAPER (BEST for GAINERS - ~$50/mo) ===
            # Apify scraper gets SORTED DexScreener data by price change!
            # This is the MAIN GAINER source - actual price movement sorting
            # Cycling through: priceChange24h → priceChange6h → priceChange1h → volume → liquidity
            if enable_apify and self.apify:
                print("  📡 Fetching tokens from Apify DexScreener (SORTED BY GAINERS)...")
                try:
                    # Use cycling method to rotate discovery strategies
                    # NOTE: Apify runs take 10-30 seconds, so this will slow down scans
                    apify_tokens = self.apify.get_tokens_by_cycle(
                        limit=20,
                        min_volume=50000,
                        min_liquidity=10000,
                        time_frame="6h"
                    )

                    if apify_tokens:
                        # 🚫 Apply bluechip filter
                        filtered_apify_tokens = []
                        for token in apify_tokens:
                            symbol = token.get('symbol', '').upper()
                            addr = token.get('address')
                            mcap = token.get('mcap', 0)

                            # Skip bluechips by symbol, address, or market cap
                            if symbol in BLUECHIP_SYMBOLS:
                                logger.debug(f"[APIFY] Filtered out bluechip: {symbol}")
                                continue
                            if addr in BLUECHIP_ADDRESSES:
                                logger.debug(f"[APIFY] Filtered out bluechip: {addr[:8]}...")
                                continue
                            if mcap and mcap > MAX_MARKET_CAP:
                                logger.debug(f"[APIFY] Filtered out high mcap: {symbol} (${mcap/1e6:.1f}M)")
                                continue

                            filtered_apify_tokens.append(token)

                        print(f"  ✅ Apify: Found {len(filtered_apify_tokens)} SORTED GAINERS ({len(apify_tokens) - len(filtered_apify_tokens)} bluechips filtered)")
                        logger.info(f"Apify returned {len(filtered_apify_tokens)} tokens after bluechip filter")

                        for token in filtered_apify_tokens:
                            addr = token.get('address')
                            if addr and addr not in seen_addresses:
                                all_tokens.append(token)
                                seen_addresses.add(addr)
                    else:
                        print("  ⚠️  Apify returned no tokens")
                        logger.warning("Apify returned no tokens")
                except Exception as e:
                    logger.error(f"Apify error: {e}")
                    print(f"  ❌ Apify error: {e}")

            # === COMBINE AND DEDUPLICATE ===
            if not all_tokens:
                print("  ⚠️  No tokens from any source - using safe fallback")
                logger.warning("All token sources returned no tokens, using fallback")
                all_tokens = [
                    {'address': 'DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263'},  # Bonk
                    {'address': 'JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN'},   # Jupiter
                ]
            else:
                print(f"  ✅ Combined: {len(all_tokens)} unique tokens from {sum([enable_jupiter, enable_dexscreener, enable_birdeye])} sources")
                logger.info(f"Combined {len(all_tokens)} unique tokens from enabled sources")

            new_tokens = all_tokens

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

                # Analyze token (trending tokens don't have price data, will fetch from DexScreener)
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
        # Monitor positions for BOTH paper and live trading
        # Get current prices for all open positions
        positions = self.trading_engine.position_manager.get_all_positions()

        if not positions:
            return  # No positions to monitor

        # Reduce log spam: only log header occasionally
        # Monitor runs every 10 seconds, log header every 60 seconds
        current_time = asyncio.get_event_loop().time()
        if not hasattr(self, '_last_monitor_log_time'):
            self._last_monitor_log_time = 0

        should_log_header = (current_time - self._last_monitor_log_time) >= 60
        if should_log_header:
            print(f"📊 Monitoring {len(positions)} open position(s)...")
            logger.info(f"Monitoring {len(positions)} positions")
            self._last_monitor_log_time = current_time
        else:
            # Silent monitoring - just logger debug
            logger.debug(f"Monitoring {len(positions)} positions")

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

                # REDUCE LOG SPAM: Only print if significant change or important event
                # Track last printed price for each position
                if not hasattr(self, '_last_printed_prices'):
                    self._last_printed_prices = {}

                last_price = self._last_printed_prices.get(position.token_address, position.entry_price)
                price_change_pct = abs((current_price - last_price) / last_price * 100) if last_price > 0 else 100

                # Only print if:
                # 1. Periodic header was shown (every 60 seconds), OR
                # 2. Price changed >2% since last print, OR
                # 3. Close to stop/target
                symbol = profile.get('symbol', position.token_address[:8])

                close_to_action = False
                if position.use_trailing_stop:
                    close_to_action = current_price <= position.trailing_stop_price * 1.02
                else:
                    sl_distance = ((current_price - position.stop_loss) / position.stop_loss) * 100
                    tp_distance = ((position.take_profit - current_price) / current_price) * 100
                    close_to_action = sl_distance < 5 or tp_distance < 10

                should_print = should_log_header or price_change_pct >= 2.0 or close_to_action

                if should_print:
                    print(f"  💹 {symbol}: ${current_price:.8f} ({pnl_percent:+.2f}%) [{data_source}]")
                    self._last_printed_prices[position.token_address] = current_price

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
                else:
                    # Silent monitoring - just debug log
                    logger.debug(f"{symbol}: ${current_price:.8f} ({pnl_percent:+.2f}%)")

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

        scan_interval = 120  # 2 minutes - find new opportunities
        monitor_interval = 10  # 10 seconds - CRITICAL for fast position monitoring and rug detection

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

                # Sleep briefly - keep responsive
                await asyncio.sleep(5)

            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                await asyncio.sleep(30)

    async def start(self):
        """Start the trading bot."""
        logger.info("Starting Solana Trading Bot...")
        self.running = True

        # Initialize wallet balance for live trading
        if not settings.is_paper_trading():
            logger.info("💰 Initializing wallet balance from blockchain...")
            await self.trading_engine.init_wallet_balance(sol_price_usd=240.0)

        # Send startup notification
        await self.notifier.send_startup_message()

        # Start Telegram command handler
        asyncio.create_task(self.command_handler.start())

        # Start health monitoring in background
        asyncio.create_task(self.health_checker.monitor())

        # Start enhanced bot background monitoring (if enabled)
        if self.enhanced_bot:
            try:
                await self.enhanced_bot.start_background_monitoring()
                logger.info("✅ Enhanced bot background monitoring started (BTC/ETH/SOL market monitor)")
            except Exception as e:
                logger.error(f"Failed to start enhanced bot monitoring: {e}")

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
        if self.birdeye:
            await self.birdeye.close()
        if self.twitter:
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
