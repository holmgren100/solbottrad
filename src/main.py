#!/usr/bin/env python3
"""
Solana Trading Bot - Main Orchestrator
Automated trading bot for Solana meme coins and small-cap tokens
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional

# Configuration
from config.settings import TradingConfig, RiskConfig, APIConfig, validate_config

# Blockchain clients
from blockchain.alchemy_client import AlchemyClient
from blockchain.solsniffer_client import SolSnifferClient
from blockchain.wallet_tracker import WalletTracker

# Market analysis
from market.dexscreener_client import DexScreenerClient
from market.market_analyzer import MarketAnalyzer, MarketSignal

# Social sentiment
from social.twitter_client import TwitterClient
from social.sentiment_analyzer import SentimentAnalyzer, SentimentScore

# AI models
from ai.sentiment_model import SentimentModel
from ai.price_predictor import PricePredictor, PricePrediction
from ai.risk_assessor import RiskAssessor, RiskAssessment

# Trading
from trading.paper_trading import PaperTradingEngine
from trading.position_manager import PositionManager
from trading.telegram_executor import TelegramExecutor

# Monitoring
from monitoring.logger import setup_logger, log_trade, log_signal, log_error
from monitoring.telegram_notifier import TelegramNotifier
from monitoring.health_checker import HealthChecker


class SolanaTradingBot:
    """Main trading bot orchestrator"""

    def __init__(self):
        # Setup logging
        self.logger = setup_logger('trading_bot', 'trading_bot.log')
        self.logger.info("=" * 60)
        self.logger.info("SOLANA TRADING BOT STARTING")
        self.logger.info("=" * 60)

        # Initialize components
        self.health_checker = HealthChecker()

        # API Clients
        self.alchemy_client = AlchemyClient(APIConfig.ALCHEMY_API_KEY) if APIConfig.ALCHEMY_API_KEY else None
        self.solsniffer_client = SolSnifferClient(APIConfig.SOLSNIFFER_API_KEY)
        self.dexscreener_client = DexScreenerClient(APIConfig.DEXSCREENER_API_KEY)
        self.twitter_client = TwitterClient(APIConfig.TWITTER_BEARER_TOKEN)

        # Analysis engines
        self.market_analyzer = MarketAnalyzer()
        self.sentiment_analyzer = SentimentAnalyzer()
        self.wallet_tracker = WalletTracker()

        # AI models
        self.sentiment_model = SentimentModel(APIConfig.SENTIMENT_MODEL)
        self.price_predictor = PricePredictor(APIConfig.PRICE_MODEL)
        self.risk_assessor = RiskAssessor(TradingConfig.MAX_POSITION_SIZE)

        # Trading engine
        if TradingConfig.PAPER_TRADING_MODE:
            self.logger.info("📄 PAPER TRADING MODE ENABLED")
            self.trading_engine = PaperTradingEngine(
                initial_capital=TradingConfig.INITIAL_CAPITAL,
                stop_loss_percent=TradingConfig.STOP_LOSS_PERCENT,
                take_profit_percent=TradingConfig.TAKE_PROFIT_PERCENT
            )
        else:
            self.logger.warning("🔴 LIVE TRADING MODE - USE WITH CAUTION")
            self.trading_engine = TelegramExecutor()

        self.position_manager = PositionManager(self.trading_engine)

        # Notifications
        self.telegram_notifier = TelegramNotifier(
            APIConfig.TELEGRAM_BOT_TOKEN,
            APIConfig.TELEGRAM_CHAT_ID
        )

        # State
        self.running = False
        self.scan_count = 0

        self.logger.info("✅ Bot initialized successfully")

    async def start(self):
        """Start the trading bot"""
        self.logger.info("🚀 Starting trading bot...")
        print("\n" + "=" * 60)
        print("🤖 SOLANA TRADING BOT")
        print("=" * 60)
        print(f"Mode: {'📄 PAPER TRADING' if TradingConfig.PAPER_TRADING_MODE else '🔴 LIVE TRADING'}")
        print(f"Initial Capital: ${TradingConfig.INITIAL_CAPITAL:,.2f}")
        print(f"Max Position Size: ${TradingConfig.MAX_POSITION_SIZE:,.2f}")
        print(f"Scan Interval: {TradingConfig.SCAN_INTERVAL}s")
        print("=" * 60 + "\n")

        # Validate configuration
        if not validate_config():
            self.logger.error("❌ Configuration validation failed")
            return

        # Send startup notification
        await self.telegram_notifier.notify_status("🤖 Trading bot started")

        # Check API health
        await self.check_health()

        # Start main loop
        self.running = True
        await self.main_loop()

    async def check_health(self):
        """Check health of all components"""
        self.logger.info("🏥 Checking component health...")

        # Check DexScreener
        if await self.dexscreener_client.is_connected():
            self.health_checker.update_component_status('dexscreener', 'healthy')
            self.logger.info("  ✅ DexScreener: Connected")
        else:
            self.health_checker.update_component_status('dexscreener', 'degraded')
            self.logger.warning("  ⚠️ DexScreener: Connection issues")

        # Check SolSniffer
        if await self.solsniffer_client.is_connected():
            self.health_checker.update_component_status('solsniffer', 'healthy')
            self.logger.info("  ✅ SolSniffer: Connected")
        else:
            self.health_checker.update_component_status('solsniffer', 'degraded')
            self.logger.warning("  ⚠️ SolSniffer: Connection issues (will use test tokens)")

        # Check Twitter
        if self.twitter_client.enabled:
            if await self.twitter_client.is_connected():
                self.health_checker.update_component_status('twitter', 'healthy')
                self.logger.info("  ✅ Twitter: Connected")
            else:
                self.health_checker.update_component_status('twitter', 'degraded')
                self.logger.warning("  ⚠️ Twitter: Connection issues")
        else:
            self.health_checker.update_component_status('twitter', 'disabled')
            self.logger.info("  ⚠️ Twitter: Disabled (no credentials)")

    async def main_loop(self):
        """Main trading loop"""
        self.logger.info("🔄 Entering main trading loop...")

        while self.running:
            try:
                self.scan_count += 1
                self.logger.info(f"\n{'=' * 60}")
                self.logger.info(f"SCAN #{self.scan_count} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                self.logger.info(f"{'=' * 60}")

                print(f"\n🔍 Scan #{self.scan_count} - {datetime.now().strftime('%H:%M:%S')}")

                # 1. Scan for new tokens
                tokens = await self.scan_tokens()
                self.logger.info(f"📊 Found {len(tokens)} tokens to analyze")

                # 2. Analyze each token
                for token in tokens:
                    await self.analyze_token(token)

                # 3. Check existing positions for stop loss / take profit
                if hasattr(self.trading_engine, 'positions'):
                    await self.check_positions()

                # 4. Display status
                self.display_status()

                # Wait before next scan
                self.logger.info(f"⏳ Waiting {TradingConfig.SCAN_INTERVAL}s until next scan...")
                await asyncio.sleep(TradingConfig.SCAN_INTERVAL)

            except KeyboardInterrupt:
                self.logger.info("⚠️ Keyboard interrupt received")
                break
            except Exception as e:
                self.logger.error(f"❌ Error in main loop: {e}", exc_info=True)
                log_error(self.logger, e, "main_loop")
                await asyncio.sleep(10)  # Wait before retrying

        await self.shutdown()

    async def scan_tokens(self) -> List[Dict]:
        """Scan for new tokens to analyze"""
        self.logger.info("🔍 Scanning for tokens...")

        try:
            # Try to get tokens from SolSniffer
            tokens = await self.solsniffer_client.get_new_tokens(limit=20)

            if tokens:
                self.logger.info(f"  Found {len(tokens)} tokens from SolSniffer")
                return tokens
            else:
                # FALLBACK: Use hardcoded test tokens when SolSniffer is down
                self.logger.warning("  SolSniffer returned no tokens, using test tokens")
                test_tokens = [
                    {'address': 'So11111111111111111111111111111111111111112', 'symbol': 'SOL'},  # Wrapped SOL
                    {'address': 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v', 'symbol': 'USDC'},  # USDC
                    {'address': 'DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263', 'symbol': 'Bonk'},  # Bonk
                    {'address': 'JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN', 'symbol': 'JUP'},  # Jupiter
                ]
                self.logger.info(f"  Using {len(test_tokens)} test tokens")
                return test_tokens

        except Exception as e:
            self.logger.error(f"Error scanning tokens: {e}")
            log_error(self.logger, e, "scan_tokens")
            return []

    async def analyze_token(self, token: Dict):
        """Analyze a token and make trading decision"""
        token_address = token.get('address')
        token_symbol = token.get('symbol', token_address[:8])

        self.logger.info(f"\n  🔍 Analyzing {token_symbol} ({token_address[:12]}...)")

        try:
            # Skip if we already have a position
            if hasattr(self.trading_engine, 'positions') and token_address in self.trading_engine.positions:
                self.logger.info(f"    ⏭️  Position already exists for {token_symbol}")
                return

            # 1. Get market data from DexScreener
            self.logger.info(f"    📊 Fetching market data...")
            market_data = await self.dexscreener_client.get_token_data(token_address)

            if not market_data:
                self.logger.warning(f"    ❌ No market data available for {token_symbol}")
                return

            # 2. Analyze market signals
            market_signal = self.market_analyzer.analyze(market_data)
            self.logger.info(f"    📈 Market signal: {market_signal.signal_type} (confidence: {market_signal.confidence:.2f})")
            self.logger.info(f"       Price: ${market_signal.price:.8f} | 24h change: {market_signal.price_change_24h:+.2f}%")
            self.logger.info(f"       Volume: ${market_signal.volume_24h:,.2f} | Liquidity: ${market_signal.liquidity:,.2f}")

            # 3. Get social sentiment
            self.logger.info(f"    💬 Analyzing sentiment...")
            tweets = await self.twitter_client.get_token_mentions(token_symbol, token_address)
            sentiment_score = await self.sentiment_analyzer.analyze_tweets(tweets)
            self.logger.info(f"    💭 Sentiment: {sentiment_score.sentiment} (score: {sentiment_score.score:.2f}, confidence: {sentiment_score.confidence:.2f})")

            # 4. Make trading decision
            decision = await self.make_trading_decision(
                token_address=token_address,
                token_symbol=token_symbol,
                market_data=market_data,
                market_signal=market_signal,
                sentiment_score=sentiment_score
            )

            # 5. Execute trade if decision is made
            if decision:
                await self.execute_trade(decision)

        except Exception as e:
            self.logger.error(f"Error analyzing token {token_symbol}: {e}", exc_info=True)
            log_error(self.logger, e, f"analyze_token:{token_symbol}")

    async def make_trading_decision(
        self,
        token_address: str,
        token_symbol: str,
        market_data: Dict,
        market_signal: MarketSignal,
        sentiment_score: SentimentScore
    ) -> Optional[Dict]:
        """Make trading decision based on all available data"""

        self.logger.info(f"    🤔 Making trading decision for {token_symbol}...")

        try:
            # Get price prediction
            prediction = self.price_predictor.predict(
                current_price=market_signal.price,
                price_change_24h=market_signal.price_change_24h,
                volume_24h=market_signal.volume_24h,
                liquidity=market_signal.liquidity
            )
            self.logger.info(f"    🔮 Price prediction: {prediction.direction} (confidence: {prediction.confidence:.2f})")

            # Determine action based on market signal and sentiment
            action = None

            # FIXED: Allow trading when sentiment confidence is 0 (no social data)
            if sentiment_score.confidence == 0.0:
                # No sentiment data available, use market signal only
                if market_signal.signal_type == 'buy':
                    action = 'buy'
                    self.logger.info(f"    ℹ️  Using market signal only (no sentiment data)")
            else:
                # Both market and sentiment available
                if market_signal.signal_type == 'buy' and sentiment_score.sentiment in ['positive', 'neutral']:
                    action = 'buy'
                elif market_signal.signal_type == 'sell' or sentiment_score.sentiment == 'negative':
                    action = 'sell'

            if action != 'buy':
                self.logger.info(f"    ❌ No buy action: market={market_signal.signal_type}, sentiment={sentiment_score.sentiment}")
                return None

            # Risk assessment
            portfolio_value = self.trading_engine.get_portfolio_value() if hasattr(self.trading_engine, 'get_portfolio_value') else TradingConfig.INITIAL_CAPITAL

            risk_assessment = self.risk_assessor.assess(
                token_data=market_data,
                prediction_confidence=prediction.confidence,
                sentiment_score=sentiment_score.score,
                current_portfolio_value=portfolio_value
            )

            self.logger.info(f"    ⚖️  Risk score: {risk_assessment.risk_score:.2f}")
            self.logger.info(f"    💰 Recommended position: ${risk_assessment.recommended_position_size:.2f}")

            if risk_assessment.warnings:
                for warning in risk_assessment.warnings:
                    self.logger.warning(f"    ⚠️  {warning}")

            if not risk_assessment.approved:
                self.logger.warning(f"    ❌ Trade not approved by risk assessment")
                return None

            # Create trading decision
            decision = {
                'action': action,
                'token_address': token_address,
                'symbol': token_symbol,
                'entry_price': market_signal.price,
                'position_size': risk_assessment.recommended_position_size,
                'market_signal': market_signal,
                'sentiment': sentiment_score,
                'prediction': prediction,
                'risk_assessment': risk_assessment
            }

            self.logger.info(f"    ✅ DECISION: {action.upper()} ${risk_assessment.recommended_position_size:.2f} of {token_symbol}")

            return decision

        except Exception as e:
            self.logger.error(f"Error making trading decision: {e}", exc_info=True)
            log_error(self.logger, e, "make_trading_decision")
            return None

    async def execute_trade(self, decision: Dict) -> bool:
        """Execute a trading decision with detailed logging"""
        print(f"\n      🎯 TRADING OPPORTUNITY: {decision['symbol']}")
        print(f"      🔧 EXECUTING TRADE: {decision['action'].upper()} {decision['symbol']}")
        print(f"      💵 Amount: ${decision['position_size']:.2f} @ ${decision['entry_price']:.8f}")

        self.logger.info(f"🔧 EXECUTING TRADE: {decision['action'].upper()} {decision['symbol']}")
        self.logger.info(f"   Amount: ${decision['position_size']:.2f} @ ${decision['entry_price']:.8f}")

        try:
            # Send Telegram notification about opportunity
            print(f"      📱 Sending Telegram notification...")
            self.logger.info("   📱 Sending Telegram notification...")

            await self.telegram_notifier.notify_opportunity(
                symbol=decision['symbol'],
                confidence=decision['market_signal'].confidence,
                signal_type=decision['action']
            )

            # Execute trade
            print(f"      💰 Calling trading engine...")
            self.logger.info("   💰 Calling trading engine...")

            if decision['action'] == 'buy':
                result = await self.trading_engine.execute_buy(
                    token_address=decision['token_address'],
                    symbol=decision['symbol'],
                    price=decision['entry_price'],
                    amount_usd=decision['position_size']
                )
            else:
                result = await self.trading_engine.execute_sell(
                    token_address=decision['token_address'],
                    price=decision['entry_price']
                )

            print(f"      ✅ Trade result: {result}")
            self.logger.info(f"   ✅ Trade result: {result}")

            # Log the trade
            if result.get('success'):
                log_trade(
                    self.logger,
                    action=decision['action'],
                    symbol=decision['symbol'],
                    amount=decision['position_size'],
                    price=decision['entry_price'],
                    result=result
                )

                # Send trade notification
                await self.telegram_notifier.notify_trade(
                    action=decision['action'],
                    symbol=decision['symbol'],
                    amount=decision['position_size'],
                    price=decision['entry_price'],
                    position_size=decision['position_size']
                )

                return True
            else:
                self.logger.warning(f"   ⚠️ Trade failed: {result.get('reason')}")
                return False

        except Exception as e:
            self.logger.error(f"Error executing trade: {e}", exc_info=True)
            log_error(self.logger, e, "execute_trade")
            await self.telegram_notifier.notify_error(f"Trade execution error: {str(e)}")
            return False

    async def check_positions(self):
        """Check existing positions for stop loss / take profit"""
        if not hasattr(self.trading_engine, 'positions'):
            return

        positions = self.position_manager.get_open_positions()

        if not positions:
            return

        self.logger.info(f"\n  📊 Checking {len(positions)} open position(s)...")

        # Get current prices
        price_data = {}
        for position in positions:
            market_data = await self.dexscreener_client.get_token_data(position['token_address'])
            if market_data:
                price_data[position['token_address']] = float(market_data.get('priceUsd', 0))

        # Check for stop loss / take profit triggers
        actions = await self.position_manager.check_positions(price_data)

        for action in actions:
            self.logger.info(f"  🎯 Triggered: {action['reason']} for {action['symbol']}")

            # Execute sell
            decision = {
                'action': 'sell',
                'token_address': action['token_address'],
                'symbol': action['symbol'],
                'entry_price': action['price'],
                'position_size': 0,  # Selling full position
            }

            await self.execute_trade(decision)

    def display_status(self):
        """Display current bot status"""
        if not hasattr(self.trading_engine, 'get_statistics'):
            return

        stats = self.trading_engine.get_statistics()

        print(f"\n📈 Portfolio Status:")
        print(f"   Cash: ${stats['current_cash']:.2f}")
        print(f"   Portfolio Value: ${stats['portfolio_value']:.2f}")
        print(f"   P&L: ${stats['total_pnl']:.2f} ({stats['total_pnl_percent']:+.2f}%)")
        print(f"   Trades: {stats['total_trades']} ({stats['total_buys']} buys, {stats['total_sells']} sells)")
        print(f"   Open Positions: {stats['open_positions']}")

        self.logger.info(f"\n📈 Portfolio: ${stats['portfolio_value']:.2f} | P&L: ${stats['total_pnl']:.2f} ({stats['total_pnl_percent']:+.2f}%) | Positions: {stats['open_positions']}")

    async def shutdown(self):
        """Shutdown the bot gracefully"""
        self.logger.info("\n" + "=" * 60)
        self.logger.info("🛑 SHUTTING DOWN TRADING BOT")
        self.logger.info("=" * 60)

        self.running = False

        # Display final statistics
        if hasattr(self.trading_engine, 'get_statistics'):
            stats = self.trading_engine.get_statistics()
            self.logger.info(f"Final Portfolio Value: ${stats['portfolio_value']:.2f}")
            self.logger.info(f"Total P&L: ${stats['total_pnl']:.2f} ({stats['total_pnl_percent']:+.2f}%)")
            self.logger.info(f"Total Trades: {stats['total_trades']}")

        await self.telegram_notifier.notify_status("🛑 Trading bot stopped")

        self.logger.info("✅ Shutdown complete")


async def main():
    """Main entry point"""
    bot = SolanaTradingBot()
    await bot.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Bot stopped by user")
