"""
Enhanced bot integration - uses all new systems together.
This shows how to integrate multi-source aggregator, RugCheck, market monitor,
and dynamic scoring with 5-10 second position monitoring.
"""

import asyncio
import os
from typing import Dict, List
from datetime import datetime

from ..monitoring.logger import get_logger
from .multi_source_aggregator import MultiSourceAggregator
from .rugcheck_client import RugCheckClient
from .market_monitor import MarketMonitor
from ..trading.dynamic_scorer import DynamicTokenScorer

logger = get_logger(__name__)


class EnhancedTradingIntegration:
    """
    Enhanced trading integration using all new systems:
    - Multi-source data aggregation (Jupiter + DexScreener + Birdeye)
    - RugCheck holder analysis
    - Market monitoring (BTC/ETH/SOL)
    - Dynamic scoring (adaptive thresholds)
    - 5-10 second position monitoring
    """

    def __init__(
        self,
        jupiter_client,
        dexscreener_client,
        birdeye_client,
        position_manager,
        trading_engine,
        notifier
    ):
        """Initialize enhanced integration."""

        # Core components
        self.position_manager = position_manager
        self.trading_engine = trading_engine
        self.notifier = notifier

        # NEW: Multi-source aggregator with rate limiting
        self.aggregator = MultiSourceAggregator(
            jupiter_client,
            dexscreener_client,
            birdeye_client
        )

        # NEW: RugCheck for holder analysis
        self.rugcheck = RugCheckClient()

        # NEW: Market monitor for BTC/ETH/SOL
        self.market_monitor = MarketMonitor()

        # NEW: Dynamic scorer (learns from trade history)
        self.scorer = DynamicTokenScorer()

        # Active monitoring tasks
        self.monitoring_tasks = {}  # token_address -> asyncio.Task

    async def start_background_monitoring(self):
        """Start background tasks for market monitoring."""
        logger.info("Starting background monitoring tasks...")

        # Start market monitoring (every 60 seconds)
        asyncio.create_task(self.market_monitor.monitor_continuous(check_interval=60))

        logger.info("✅ Background monitoring started")

    async def evaluate_token_comprehensive(
        self,
        token_address: str,
        source: str = 'unknown'
    ) -> Dict:
        """
        Comprehensive token evaluation using ALL available data.

        This is the MAIN entry point for token evaluation.

        Args:
            token_address: Token mint address
            source: Where token was discovered (jupiter/dexscreener/birdeye)

        Returns:
            Evaluation result with score and recommendation
        """
        logger.info(f"🔍 Evaluating token {token_address[:8]}... from {source}")

        # STEP 1: Get comprehensive data from all sources
        logger.info("  📊 Fetching multi-source data...")
        token_data = await self.aggregator.get_token_data_all_sources(token_address)

        if not token_data or token_data['confidence'] == 'none':
            logger.warning(f"  ❌ No data available for {token_address[:8]}...")
            return {
                'action': 'skip',
                'reason': 'No data from any source',
                'token_address': token_address
            }

        logger.info(
            f"  ✅ Data fetched: ${token_data['price']:.8f}, "
            f"Liq ${token_data['liquidity']:,.0f}, "
            f"Vol ${token_data['volume_24h']:,.0f}, "
            f"Confidence: {token_data['confidence']} "
            f"({token_data['sources_count']} sources)"
        )

        # STEP 2: Get holder analysis from RugCheck
        logger.info("  🛡️ Running RugCheck analysis...")
        rugcheck_data = await self.rugcheck.analyze_holder_risk(token_address)

        if rugcheck_data:
            logger.info(
                f"  🛡️ RugCheck: {rugcheck_data['risk_level']} risk, "
                f"Safety {rugcheck_data['safety_score']}/100, "
                f"Top 10: {rugcheck_data['top_10_percentage']:.1f}%"
            )
        else:
            logger.warning("  ⚠️ No RugCheck data available")

        # STEP 3: Check market conditions
        logger.info("  📈 Checking market conditions...")
        market_data = await self.market_monitor.get_market_data()
        sol_health = self.market_monitor.get_sol_health()
        can_trade, market_reason = self.market_monitor.should_trade()

        if not can_trade:
            logger.warning(f"  ⛔ Market conditions prohibit trading: {market_reason}")
            return {
                'action': 'skip',
                'reason': f'Market: {market_reason}',
                'token_address': token_address
            }

        market_state = {
            'market_state': self.market_monitor.market_state,
            'sol_health': sol_health,
            'position_size_multiplier': self.market_monitor.get_position_size_multiplier(),
            'btc': self.market_monitor.btc_data,
            'eth': self.market_monitor.eth_data,
            'sol': self.market_monitor.sol_data
        }

        logger.info(
            f"  📈 Market: {market_state['market_state']}, "
            f"SOL: ${sol_health['price']:.2f} ({sol_health['change_1h']:+.1f}%), "
            f"Size multiplier: {market_state['position_size_multiplier']:.2f}x"
        )

        # STEP 4: Score token dynamically
        logger.info("  🎯 Scoring token...")
        score_result = self.scorer.score_token(
            token_data=token_data,
            rugcheck_data=rugcheck_data,
            market_data=market_state
        )

        logger.info(
            f"  🎯 Score: {score_result['score']}/100, "
            f"Action: {score_result['action']}, "
            f"Position: ${score_result['position_size']}, "
            f"Confidence: {score_result['confidence']}"
        )

        # Log warnings if any
        if score_result['warnings']:
            for warning in score_result['warnings']:
                logger.warning(f"  ⚠️ {warning}")

        # Build comprehensive result
        result = {
            'action': score_result['action'],
            'token_address': token_address,
            'source': source,
            'score': score_result['score'],
            'score_breakdown': score_result['breakdown'],
            'confidence': score_result['confidence'],
            'position_size': score_result['position_size'],
            'warnings': score_result['warnings'],
            'is_pumpfun': score_result['is_pumpfun'],
            'reason': score_result['reason'],

            # Store full data for entry notification
            'token_data': token_data,
            'rugcheck_data': rugcheck_data,
            'market_data': market_state,
            'timestamp': datetime.now().isoformat()
        }

        return result

    async def execute_entry(self, evaluation: Dict) -> bool:
        """
        Execute entry based on evaluation.

        Args:
            evaluation: Result from evaluate_token_comprehensive

        Returns:
            True if entered successfully
        """
        if evaluation['action'] != 'enter':
            logger.info(f"Skipping entry: {evaluation['reason']}")
            return False

        token_address = evaluation['token_address']
        token_data = evaluation['token_data']
        position_size = evaluation['position_size']

        logger.info(
            f"🟢 ENTERING: {token_address[:8]}... "
            f"${position_size} @ ${token_data['price']:.8f}"
        )

        # Send enhanced entry notification
        await self._send_entry_notification(evaluation)

        # Execute trade through trading engine
        try:
            # Calculate stop loss and take profit
            entry_price = token_data['price']
            stop_loss_pct = float(os.getenv('STOP_LOSS_PERCENT', '15'))
            trailing_stop_pct = float(os.getenv('TRAILING_STOP_PERCENT', '10'))

            stop_loss = entry_price * (1 - stop_loss_pct / 100)
            take_profit = entry_price * (1 + trailing_stop_pct / 100)  # Initial trigger

            result = await self.trading_engine.execute_buy(
                token_address=token_address,
                amount_usd=position_size,
                price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                analysis_data={
                    'evaluation': evaluation,
                    'entry_source': evaluation['source']
                },
                pair_created_at=token_data.get('pair_created_at', 0)
            )

            if result.get('status') == 'success':
                # Start continuous monitoring for this position
                await self._start_position_monitoring(
                    token_address,
                    token_data['liquidity']
                )
                return True

            return False

        except Exception as e:
            logger.error(f"Error executing entry for {token_address[:8]}...: {e}")
            await self.notifier.send_alert(
                title="Entry Error",
                message=f"Failed to enter {token_address[:8]}...: {str(e)}",
                level="ERROR"
            )
            return False

    async def _send_entry_notification(self, evaluation: Dict):
        """Send enhanced entry notification with ALL data."""
        token_data = evaluation['token_data']
        rugcheck_data = evaluation.get('rugcheck_data')
        market_data = evaluation.get('market_data', {})

        # Get token age
        pair_created_at = token_data.get('pair_created_at', 0)
        if pair_created_at > 0:
            age_hours = (datetime.now().timestamp() - pair_created_at / 1000) / 3600
        else:
            age_hours = 0

        # Build message
        token_emoji = '🚀' if evaluation['is_pumpfun'] else '📈'
        confidence_emoji = '🟢' if evaluation['confidence'] == 'high' else '🟡' if evaluation['confidence'] == 'medium' else '🟠'

        message = (
            f"{confidence_emoji} ENTERED: {token_data.get('symbol', 'UNKNOWN')} {token_emoji}\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"💰 Position: ${evaluation['position_size']:.2f}\n"
            f"💲 Entry: ${token_data['price']:.8f}\n"
            f"📊 Score: {evaluation['score']}/100 ({evaluation['confidence']})\n"
            f"\n"
            f"📍 Source: {evaluation['source'].upper()}\n"
            f"💧 Liquidity: ${token_data['liquidity']:,.0f} ({token_data['confidence']})\n"
            f"📈 Volume 24h: ${token_data['volume_24h']:,.0f}\n"
            f"⏰ Age: {age_hours:.1f}h\n"
            f"🔗 Data: {token_data['sources_count']} sources ({', '.join(token_data.get('sources_used', []))})\n"
        )

        # Add score breakdown
        message += f"\n✅ Score Breakdown:\n"
        for factor, points in evaluation['score_breakdown'].items():
            message += f"  • {factor}: {points} pts\n"

        # Add RugCheck if available
        if rugcheck_data:
            message += (
                f"\n🛡️ RugCheck:\n"
                f"  • Safety: {rugcheck_data['safety_score']}/100\n"
                f"  • Risk: {rugcheck_data['risk_level']}\n"
                f"  • Top 10 holders: {rugcheck_data['top_10_percentage']:.1f}%\n"
            )
            if rugcheck_data.get('warnings'):
                message += f"  ⚠️ {rugcheck_data['warnings'][0]}\n"

        # Add market conditions
        sol_health = market_data.get('sol_health', {})
        message += (
            f"\n📈 Market: {market_data.get('market_state', 'unknown').upper()}\n"
            f"  • SOL: ${sol_health.get('price', 0):.2f} ({sol_health.get('change_1h', 0):+.1f}%)\n"
        )

        # Add warnings if any
        if evaluation['warnings']:
            message += f"\n⚠️ Warnings:\n"
            for warning in evaluation['warnings'][:3]:  # Max 3
                message += f"  • {warning}\n"

        message += f"\n🔗 {evaluation['token_address'][:8]}...{evaluation['token_address'][-4:]}"

        await self.notifier.send_message(message)

    async def _start_position_monitoring(
        self,
        token_address: str,
        entry_liquidity: float
    ):
        """
        Start continuous monitoring for a position (5-10 second intervals).

        This runs in background until position is closed.
        """
        # Cancel existing task if any
        if token_address in self.monitoring_tasks:
            self.monitoring_tasks[token_address].cancel()

        # Create callback for force exit
        async def on_liquidity_drop(reason: str, data: Dict):
            """Called when liquidity drops critically."""
            logger.error(
                f"🚨 FORCE EXIT triggered for {token_address[:8]}...: {reason}"
            )

            # Send alert
            await self.notifier.send_alert(
                title=f"Force Exit: {reason}",
                message=(
                    f"Token: {token_address[:8]}...\n"
                    f"Reason: {data['reason']}\n"
                    f"Entry Liq: ${data['entry_liquidity']:,.0f}\n"
                    f"Current Liq: ${data['current_liquidity']:,.0f}\n"
                    f"Drop: {data['drop_pct']:.0f}%"
                ),
                level="CRITICAL"
            )

            # Force close position
            try:
                await self.trading_engine.force_close_position(
                    token_address,
                    reason=reason
                )
            except Exception as e:
                logger.error(f"Error force closing {token_address[:8]}...: {e}")

        # Start monitoring task with 5-second interval
        task = asyncio.create_task(
            self.aggregator.monitor_position_continuous(
                token_address=token_address,
                entry_liquidity=entry_liquidity,
                callback_on_drop=on_liquidity_drop,
                check_interval=5  # 5 seconds - fast monitoring
            )
        )

        self.monitoring_tasks[token_address] = task
        logger.info(f"✅ Started 5-second monitoring for {token_address[:8]}...")

    def stop_position_monitoring(self, token_address: str):
        """Stop monitoring for a position (called when position closed)."""
        if token_address in self.monitoring_tasks:
            self.monitoring_tasks[token_address].cancel()
            del self.monitoring_tasks[token_address]
            logger.info(f"⏹️ Stopped monitoring for {token_address[:8]}...")

    async def close(self):
        """Cleanup resources."""
        logger.info("Closing enhanced integration...")

        # Cancel all monitoring tasks
        for task in self.monitoring_tasks.values():
            task.cancel()

        # Close clients
        await self.aggregator.jupiter.close()
        await self.aggregator.dexscreener.close()
        await self.aggregator.birdeye.close()
        await self.rugcheck.close()
        await self.market_monitor.close()
