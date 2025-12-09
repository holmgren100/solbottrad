"""
Metrics collection system for comprehensive bot monitoring.
"""

import time
from typing import Dict, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from .logger import get_logger

logger = get_logger(__name__)


@dataclass
class APIMetrics:
    """Metrics for a single API."""
    name: str
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    total_response_time_ms: float = 0.0
    last_call_time: Optional[datetime] = None
    last_error: Optional[str] = None

    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.total_calls == 0:
            return 0.0
        return (self.successful_calls / self.total_calls) * 100

    @property
    def avg_response_time_ms(self) -> float:
        """Calculate average response time."""
        if self.successful_calls == 0:
            return 0.0
        return self.total_response_time_ms / self.successful_calls

    @property
    def uptime(self) -> float:
        """Calculate uptime percentage."""
        return self.success_rate / 100


@dataclass
class StrategyMetrics:
    """Metrics for a trading strategy."""
    name: str
    cycles: int = 0
    tokens_found: int = 0
    tokens_passed: int = 0
    trades_executed: int = 0
    wins: int = 0
    losses: int = 0
    total_profit: float = 0.0
    last_active: Optional[datetime] = None

    @property
    def pass_rate(self) -> float:
        """Calculate filter pass rate."""
        if self.tokens_found == 0:
            return 0.0
        return (self.tokens_passed / self.tokens_found) * 100

    @property
    def win_rate(self) -> float:
        """Calculate win rate."""
        total = self.wins + self.losses
        if total == 0:
            return 0.0
        return (self.wins / total) * 100

    @property
    def avg_profit(self) -> float:
        """Calculate average profit per trade."""
        if self.trades_executed == 0:
            return 0.0
        return self.total_profit / self.trades_executed


@dataclass
class TriggerMetrics:
    """Metrics for a trading trigger."""
    name: str
    trigger_type: str  # 'entry', 'exit', 'partial_exit'
    times_fired: int = 0
    successful: int = 0
    failed: int = 0
    last_fired: Optional[datetime] = None
    last_error: Optional[str] = None

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.times_fired == 0:
            return 0.0
        return (self.successful / self.times_fired) * 100


class MetricsCollector:
    """Collect and store system metrics."""

    def __init__(self):
        """Initialize metrics collector."""
        self.start_time = datetime.now()
        self.api_metrics: Dict[str, APIMetrics] = {}
        self.strategy_metrics: Dict[str, StrategyMetrics] = {}
        self.trigger_metrics: Dict[str, TriggerMetrics] = {}

        # System-wide counters
        self.total_scan_cycles = 0
        self.total_tokens_analyzed = 0
        self.total_errors = 0
        self.errors_this_hour = 0
        self.last_error_reset = datetime.now()

        logger.info("📊 MetricsCollector initialized")

    # API Metrics
    def register_api(self, api_name: str):
        """Register an API for tracking."""
        if api_name not in self.api_metrics:
            self.api_metrics[api_name] = APIMetrics(name=api_name)
            logger.info(f"📡 Registered API for monitoring: {api_name}")

    def record_api_call(self, api_name: str, success: bool, response_time_ms: float, error: Optional[str] = None):
        """Record an API call."""
        if api_name not in self.api_metrics:
            self.register_api(api_name)

        metrics = self.api_metrics[api_name]
        metrics.total_calls += 1
        metrics.last_call_time = datetime.now()

        if success:
            metrics.successful_calls += 1
            metrics.total_response_time_ms += response_time_ms
        else:
            metrics.failed_calls += 1
            metrics.last_error = error
            self.record_error(f"API {api_name} failed: {error}")

    def get_api_stats(self, api_name: str) -> Optional[APIMetrics]:
        """Get statistics for a specific API."""
        return self.api_metrics.get(api_name)

    def get_all_api_stats(self) -> Dict[str, APIMetrics]:
        """Get all API statistics."""
        return self.api_metrics

    # Strategy Metrics
    def register_strategy(self, strategy_name: str):
        """Register a strategy for tracking."""
        if strategy_name not in self.strategy_metrics:
            self.strategy_metrics[strategy_name] = StrategyMetrics(name=strategy_name)
            logger.info(f"🎯 Registered strategy for monitoring: {strategy_name}")

    def record_strategy_cycle(self, strategy_name: str, tokens_found: int, tokens_passed: int):
        """Record a strategy execution cycle."""
        if strategy_name not in self.strategy_metrics:
            self.register_strategy(strategy_name)

        metrics = self.strategy_metrics[strategy_name]
        metrics.cycles += 1
        metrics.tokens_found += tokens_found
        metrics.tokens_passed += tokens_passed
        metrics.last_active = datetime.now()

        self.total_tokens_analyzed += tokens_found

    def record_strategy_trade(self, strategy_name: str, win: bool, profit: float = 0.0):
        """Record a trade outcome for a strategy."""
        if strategy_name not in self.strategy_metrics:
            self.register_strategy(strategy_name)

        metrics = self.strategy_metrics[strategy_name]
        metrics.trades_executed += 1
        metrics.total_profit += profit

        if win:
            metrics.wins += 1
        else:
            metrics.losses += 1

    def get_strategy_stats(self, strategy_name: str) -> Optional[StrategyMetrics]:
        """Get statistics for a specific strategy."""
        return self.strategy_metrics.get(strategy_name)

    def get_all_strategy_stats(self) -> Dict[str, StrategyMetrics]:
        """Get all strategy statistics."""
        return self.strategy_metrics

    def get_best_strategy(self) -> Optional[StrategyMetrics]:
        """Get the best performing strategy by win rate."""
        if not self.strategy_metrics:
            return None

        strategies_with_trades = [s for s in self.strategy_metrics.values() if s.trades_executed > 0]
        if not strategies_with_trades:
            return None

        return max(strategies_with_trades, key=lambda s: s.win_rate)

    # Trigger Metrics
    def register_trigger(self, trigger_name: str, trigger_type: str):
        """Register a trigger for tracking."""
        if trigger_name not in self.trigger_metrics:
            self.trigger_metrics[trigger_name] = TriggerMetrics(
                name=trigger_name,
                trigger_type=trigger_type
            )
            logger.info(f"⚡ Registered trigger for monitoring: {trigger_name} ({trigger_type})")

    def record_trigger_fire(self, trigger_name: str, success: bool, error: Optional[str] = None):
        """Record a trigger execution."""
        if trigger_name not in self.trigger_metrics:
            # Auto-register if not registered
            trigger_type = 'unknown'
            if 'entry' in trigger_name.lower() or 'buy' in trigger_name.lower():
                trigger_type = 'entry'
            elif 'milestone' in trigger_name.lower() or 'partial' in trigger_name.lower():
                trigger_type = 'partial_exit'
            else:
                trigger_type = 'exit'
            self.register_trigger(trigger_name, trigger_type)

        metrics = self.trigger_metrics[trigger_name]
        metrics.times_fired += 1
        metrics.last_fired = datetime.now()

        if success:
            metrics.successful += 1
        else:
            metrics.failed += 1
            metrics.last_error = error
            self.record_error(f"Trigger {trigger_name} failed: {error}")

    def get_trigger_stats(self, trigger_name: str) -> Optional[TriggerMetrics]:
        """Get statistics for a specific trigger."""
        return self.trigger_metrics.get(trigger_name)

    def get_all_trigger_stats(self) -> Dict[str, TriggerMetrics]:
        """Get all trigger statistics."""
        return self.trigger_metrics

    # System Metrics
    def record_scan_cycle(self):
        """Record completion of a scan cycle."""
        self.total_scan_cycles += 1

    def record_error(self, error_message: str):
        """Record a system error."""
        self.total_errors += 1
        self.errors_this_hour += 1

        # Reset hourly counter if hour has passed
        if datetime.now() - self.last_error_reset > timedelta(hours=1):
            self.errors_this_hour = 1
            self.last_error_reset = datetime.now()

        logger.error(f"📊 Error recorded: {error_message}")

    def get_uptime_seconds(self) -> float:
        """Get bot uptime in seconds."""
        return (datetime.now() - self.start_time).total_seconds()

    def get_uptime_formatted(self) -> str:
        """Get formatted uptime string."""
        seconds = self.get_uptime_seconds()
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours}h {minutes}m {secs}s"

    def get_summary(self) -> Dict:
        """Get comprehensive metrics summary."""
        return {
            'uptime': {
                'seconds': self.get_uptime_seconds(),
                'formatted': self.get_uptime_formatted(),
                'start_time': self.start_time.isoformat()
            },
            'system': {
                'scan_cycles': self.total_scan_cycles,
                'tokens_analyzed': self.total_tokens_analyzed,
                'total_errors': self.total_errors,
                'errors_this_hour': self.errors_this_hour
            },
            'apis': {name: {
                'total_calls': api.total_calls,
                'success_rate': api.success_rate,
                'avg_response_time_ms': api.avg_response_time_ms,
                'uptime': api.uptime,
                'last_error': api.last_error
            } for name, api in self.api_metrics.items()},
            'strategies': {name: {
                'cycles': strat.cycles,
                'tokens_found': strat.tokens_found,
                'tokens_passed': strat.tokens_passed,
                'pass_rate': strat.pass_rate,
                'trades': strat.trades_executed,
                'win_rate': strat.win_rate,
                'total_profit': strat.total_profit,
                'avg_profit': strat.avg_profit
            } for name, strat in self.strategy_metrics.items()},
            'triggers': {name: {
                'times_fired': trig.times_fired,
                'success_rate': trig.success_rate,
                'last_error': trig.last_error
            } for name, trig in self.trigger_metrics.items()}
        }

    def reset_hourly_counters(self):
        """Reset counters that track per-hour metrics."""
        self.errors_this_hour = 0
        self.last_error_reset = datetime.now()
