"""
Alert management system for bot monitoring.
"""

import asyncio
from typing import Dict, Callable, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from .logger import get_logger

logger = get_logger(__name__)


@dataclass
class AlertRule:
    """Configuration for an alert rule."""
    name: str
    condition: Callable  # Function that returns True if alert should fire
    level: str  # 'INFO', 'WARNING', 'ERROR', 'CRITICAL'
    message_template: str
    cooldown_minutes: int
    last_fired: Optional[datetime] = None

    def can_fire(self) -> bool:
        """Check if alert can fire (not in cooldown)."""
        if self.last_fired is None:
            return True
        time_since_last = datetime.now() - self.last_fired
        return time_since_last > timedelta(minutes=self.cooldown_minutes)


class AlertManager:
    """Manage alerts and notifications."""

    def __init__(self, telegram_notifier):
        """
        Initialize alert manager.

        Args:
            telegram_notifier: TelegramNotifier instance for sending alerts
        """
        self.notifier = telegram_notifier
        self.rules: Dict[str, AlertRule] = {}
        self._monitoring = False

        logger.info("🚨 AlertManager initialized")

    def add_rule(
        self,
        name: str,
        condition: Callable,
        level: str,
        message_template: str,
        cooldown_minutes: int = 15
    ):
        """
        Add an alert rule.

        Args:
            name: Unique rule name
            condition: Function that takes metrics dict and returns bool
            level: Alert level (INFO/WARNING/ERROR/CRITICAL)
            message_template: Message template (can use {variables})
            cooldown_minutes: Minimum minutes between alerts
        """
        self.rules[name] = AlertRule(
            name=name,
            condition=condition,
            level=level,
            message_template=message_template,
            cooldown_minutes=cooldown_minutes
        )
        logger.info(f"📋 Added alert rule: {name} ({level})")

    async def check_rules(self, metrics: Dict):
        """
        Check all alert rules against current metrics.

        Args:
            metrics: Current metrics dictionary from MetricsCollector
        """
        for rule in self.rules.values():
            try:
                # Check if condition is met
                if rule.condition(metrics):
                    # Check if not in cooldown
                    if rule.can_fire():
                        await self._fire_alert(rule, metrics)
                    else:
                        logger.debug(f"Alert {rule.name} triggered but in cooldown")
            except Exception as e:
                logger.error(f"Error checking alert rule {rule.name}: {e}")

    async def _fire_alert(self, rule: AlertRule, metrics: Dict):
        """
        Fire an alert.

        Args:
            rule: AlertRule that triggered
            metrics: Current metrics for template formatting
        """
        # Mark as fired
        rule.last_fired = datetime.now()

        # Format message
        try:
            message = rule.message_template.format(**metrics)
        except Exception as e:
            logger.error(f"Error formatting alert message: {e}")
            message = rule.message_template

        # Send alert
        await self.send_alert(rule.level, rule.name, message)

    async def send_alert(self, level: str, title: str, message: str):
        """
        Send an alert via Telegram.

        Args:
            level: Alert level (INFO/WARNING/ERROR/CRITICAL)
            title: Alert title
            message: Alert message
        """
        # Emoji mapping
        emoji_map = {
            'INFO': '🟢',
            'WARNING': '⚠️',
            'ERROR': '🔴',
            'CRITICAL': '🚨'
        }

        emoji = emoji_map.get(level, '❓')

        # Format alert message
        alert_text = f"{emoji} **{level}: {title}**\n\n{message}"

        try:
            await self.notifier.send_message(alert_text)
            logger.info(f"🚨 Alert sent: {level} - {title}")
        except Exception as e:
            logger.error(f"Failed to send alert: {e}")

    def setup_default_rules(self, config: Dict):
        """
        Set up default alert rules based on configuration.

        Args:
            config: Configuration dictionary with thresholds
        """
        # Rule 1: API Down
        self.add_rule(
            name='api_down',
            condition=lambda m: any(
                api['uptime'] < 0.90
                for api in m.get('apis', {}).values()
            ),
            level='ERROR',
            message_template='One or more APIs have <90% uptime. Check API health status.',
            cooldown_minutes=config.get('ALERT_API_DOWN_COOLDOWN', 15)
        )

        # Rule 2: High Error Rate
        self.add_rule(
            name='high_error_rate',
            condition=lambda m: m.get('system', {}).get('errors_this_hour', 0) > config.get('ALERT_ERROR_RATE_PER_HOUR', 10),
            level='WARNING',
            message_template='High error rate: {system[errors_this_hour]} errors in the last hour',
            cooldown_minutes=config.get('ALERT_COOLDOWN_MINUTES', 30)
        )

        # Rule 3: Strategy Stalled
        self.add_rule(
            name='strategy_stalled',
            condition=lambda m: any(
                strat.get('tokens_found', 0) == 0 and strat.get('cycles', 0) > 3
                for strat in m.get('strategies', {}).values()
            ),
            level='WARNING',
            message_template='One or more strategies have found 0 tokens for 3+ cycles',
            cooldown_minutes=config.get('ALERT_NO_TOKENS_COOLDOWN', 30)
        )

        # Rule 4: Trigger Failures
        self.add_rule(
            name='trigger_failures',
            condition=lambda m: any(
                trig.get('success_rate', 100) < 80 and trig.get('times_fired', 0) > 5
                for trig in m.get('triggers', {}).values()
            ),
            level='ERROR',
            message_template='One or more triggers have <80% success rate',
            cooldown_minutes=config.get('ALERT_COOLDOWN_MINUTES', 15)
        )

        # Rule 5: System Healthy (periodic)
        self.add_rule(
            name='system_healthy',
            condition=lambda m: (
                all(api['uptime'] > 0.95 for api in m.get('apis', {}).values()) and
                m.get('system', {}).get('errors_this_hour', 0) < 3 and
                int(m.get('uptime', {}).get('seconds', 0)) % 14400 < 120  # Every 4 hours
            ),
            level='INFO',
            message_template='✅ System health check: All systems operational\nUptime: {uptime[formatted]}',
            cooldown_minutes=240  # 4 hours
        )

        logger.info("📋 Default alert rules configured")

    async def send_startup_alert(self, version: str = "unknown"):
        """Send alert when bot starts."""
        await self.send_alert(
            'INFO',
            'Bot Started',
            f'🤖 Solana Trading Bot started\nVersion: {version}\nMonitoring active'
        )

    async def send_shutdown_alert(self, reason: str = "Manual stop"):
        """Send alert when bot stops."""
        await self.send_alert(
            'INFO',
            'Bot Stopped',
            f'🛑 Solana Trading Bot stopped\nReason: {reason}'
        )
