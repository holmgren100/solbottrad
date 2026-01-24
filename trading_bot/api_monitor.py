"""
API Rate Limit & Error Monitoring
Tracks all API calls, rate limits, errors for optimization
"""

import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class APIMetrics:
    """Metrics for a single API source."""

    source: str
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    rate_limit_hits: int = 0

    # Timing
    total_response_time: float = 0.0
    min_response_time: float = float('inf')
    max_response_time: float = 0.0

    # Rate limiting
    calls_this_minute: List[float] = field(default_factory=list)
    calls_this_hour: List[float] = field(default_factory=list)

    # Error tracking
    last_error: Optional[str] = None
    last_error_time: Optional[datetime] = None
    consecutive_errors: int = 0

    # Rate limits (configured per API)
    rate_limit_per_minute: int = 0
    rate_limit_per_hour: int = 0

    @property
    def avg_response_time(self) -> float:
        """Average response time in seconds."""
        if self.successful_calls == 0:
            return 0.0
        return self.total_response_time / self.successful_calls

    @property
    def success_rate(self) -> float:
        """Success rate as percentage."""
        if self.total_calls == 0:
            return 0.0
        return (self.successful_calls / self.total_calls) * 100

    @property
    def calls_last_minute(self) -> int:
        """Number of calls in the last minute."""
        cutoff = time.time() - 60
        self.calls_this_minute = [t for t in self.calls_this_minute if t > cutoff]
        return len(self.calls_this_minute)

    @property
    def calls_last_hour(self) -> int:
        """Number of calls in the last hour."""
        cutoff = time.time() - 3600
        self.calls_this_hour = [t for t in self.calls_this_hour if t > cutoff]
        return len(self.calls_this_hour)

    def can_make_request(self) -> bool:
        """Check if we can make a request without hitting rate limits."""
        if self.rate_limit_per_minute > 0 and self.calls_last_minute >= self.rate_limit_per_minute:
            return False
        if self.rate_limit_per_hour > 0 and self.calls_last_hour >= self.rate_limit_per_hour:
            return False
        return True

    def wait_time_seconds(self) -> float:
        """Calculate how long to wait before next request."""
        if self.can_make_request():
            return 0.0

        # Check minute limit
        if self.rate_limit_per_minute > 0 and self.calls_last_minute >= self.rate_limit_per_minute:
            # Wait until oldest call expires
            if self.calls_this_minute:
                oldest = min(self.calls_this_minute)
                wait = 60 - (time.time() - oldest)
                return max(0, wait)

        # Check hour limit
        if self.rate_limit_per_hour > 0 and self.calls_last_hour >= self.rate_limit_per_hour:
            if self.calls_this_hour:
                oldest = min(self.calls_this_hour)
                wait = 3600 - (time.time() - oldest)
                return max(0, wait)

        return 0.0


class APIMonitor:
    """Monitor and track all API calls for rate limiting and performance."""

    # Rate limits for each API source (calls per minute, calls per hour)
    RATE_LIMITS = {
        'dexscreener': (280, 16800),    # 280/min from docs
        'jupiter': (500, 30000),        # 500/min estimated
        'birdeye': (100, 6000),         # 100/min free tier
        'coingecko': (30, 1800),        # 30/min free tier
        'solscan': (300, 18000),        # 300/min from docs
        'rugcheck': (60, 3600),         # Conservative estimate
        'meteora': (100, 6000),         # Conservative estimate
    }

    def __init__(self):
        self.metrics: Dict[str, APIMetrics] = {}
        self._initialize_metrics()

    def _initialize_metrics(self):
        """Initialize metrics for all known API sources."""
        for source, (per_min, per_hour) in self.RATE_LIMITS.items():
            self.metrics[source] = APIMetrics(
                source=source,
                rate_limit_per_minute=per_min,
                rate_limit_per_hour=per_hour
            )

    def can_call(self, source: str) -> bool:
        """Check if we can make an API call to this source."""
        if source not in self.metrics:
            logger.warning(f"Unknown API source: {source}")
            return True

        return self.metrics[source].can_make_request()

    def get_wait_time(self, source: str) -> float:
        """Get wait time in seconds before next call."""
        if source not in self.metrics:
            return 0.0

        return self.metrics[source].wait_time_seconds()

    def record_call_start(self, source: str) -> float:
        """Record the start of an API call. Returns start timestamp."""
        if source not in self.metrics:
            self._initialize_metrics()

        timestamp = time.time()
        metrics = self.metrics[source]
        metrics.total_calls += 1
        metrics.calls_this_minute.append(timestamp)
        metrics.calls_this_hour.append(timestamp)

        return timestamp

    def record_call_success(self, source: str, start_time: float):
        """Record a successful API call."""
        if source not in self.metrics:
            return

        response_time = time.time() - start_time
        metrics = self.metrics[source]
        metrics.successful_calls += 1
        metrics.total_response_time += response_time
        metrics.min_response_time = min(metrics.min_response_time, response_time)
        metrics.max_response_time = max(metrics.max_response_time, response_time)
        metrics.consecutive_errors = 0

    def record_call_failure(self, source: str, error: str, is_rate_limit: bool = False):
        """Record a failed API call."""
        if source not in self.metrics:
            return

        metrics = self.metrics[source]
        metrics.failed_calls += 1
        metrics.consecutive_errors += 1
        metrics.last_error = error
        metrics.last_error_time = datetime.now()

        if is_rate_limit:
            metrics.rate_limit_hits += 1
            logger.warning(
                f"⚠️  Rate limit hit for {source}: "
                f"{metrics.calls_last_minute}/{metrics.rate_limit_per_minute} per min, "
                f"{metrics.calls_last_hour}/{metrics.rate_limit_per_hour} per hour"
            )

    def get_summary(self) -> Dict[str, Dict]:
        """Get summary of all API metrics."""
        summary = {}
        for source, metrics in self.metrics.items():
            if metrics.total_calls == 0:
                continue

            summary[source] = {
                'total_calls': metrics.total_calls,
                'success_rate': f"{metrics.success_rate:.1f}%",
                'avg_response_time': f"{metrics.avg_response_time:.3f}s",
                'calls_last_minute': f"{metrics.calls_last_minute}/{metrics.rate_limit_per_minute}",
                'calls_last_hour': f"{metrics.calls_last_hour}/{metrics.rate_limit_per_hour}",
                'rate_limit_hits': metrics.rate_limit_hits,
                'consecutive_errors': metrics.consecutive_errors,
                'last_error': metrics.last_error
            }

        return summary

    def log_summary(self):
        """Log summary of API usage."""
        summary = self.get_summary()
        if not summary:
            return

        logger.info("📊 API Monitoring Summary:")
        for source, stats in summary.items():
            logger.info(
                f"  {source}: {stats['total_calls']} calls, "
                f"{stats['success_rate']} success, "
                f"avg {stats['avg_response_time']}, "
                f"rate: {stats['calls_last_minute']}/min, {stats['calls_last_hour']}/hr"
            )
            if stats['consecutive_errors'] > 0:
                logger.warning(
                    f"    ⚠️  {stats['consecutive_errors']} consecutive errors, "
                    f"last: {stats['last_error']}"
                )

    def should_backoff(self, source: str) -> bool:
        """Check if we should back off from this API due to errors."""
        if source not in self.metrics:
            return False

        metrics = self.metrics[source]
        # Back off after 3 consecutive errors
        if metrics.consecutive_errors >= 3:
            logger.warning(
                f"⚠️  Backing off {source} after {metrics.consecutive_errors} errors"
            )
            return True

        return False


# Global API monitor instance
api_monitor = APIMonitor()
