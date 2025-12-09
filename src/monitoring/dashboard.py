"""
Real-time metrics dashboard for bot monitoring.
"""

from typing import Dict
from .logger import get_logger

logger = get_logger(__name__)


class Dashboard:
    """Display real-time metrics dashboard."""

    def __init__(self, metrics_collector):
        """
        Initialize dashboard.

        Args:
            metrics_collector: MetricsCollector instance
        """
        self.metrics = metrics_collector
        logger.info("📊 Dashboard initialized")

    def render_console(self) -> str:
        """
        Render dashboard to console-formatted string.

        Returns:
            Formatted dashboard string
        """
        metrics = self.metrics.get_summary()

        # Build dashboard
        lines = []
        lines.append("╔" + "═" * 79 + "╗")
        lines.append("║" + "SOLANA TRADING BOT - LIVE MONITORING".center(79) + "║")
        lines.append("╠" + "═" * 79 + "╣")

        # Uptime & System Summary
        uptime = metrics['uptime']['formatted']
        system = metrics['system']
        summary = (
            f" ⏱️  Uptime: {uptime} | "
            f"Cycles: {system['scan_cycles']} | "
            f"Tokens: {system['tokens_analyzed']} | "
            f"Errors: {system['errors_this_hour']}/hr"
        )
        lines.append("║" + summary.ljust(79) + "║")
        lines.append("╠" + "═" * 79 + "╣")

        # API Health Status
        lines.append("║ 📡 API HEALTH STATUS".ljust(80) + "║")
        apis = metrics.get('apis', {})
        if apis:
            for name, api in apis.items():
                status_emoji = "✅" if api['uptime'] > 0.95 else "⚠️" if api['uptime'] > 0.80 else "❌"
                line = (
                    f" {status_emoji} {name:<15} "
                    f"{api['avg_response_time_ms']:>4.0f}ms avg  "
                    f"{api['total_calls']:>5} calls  "
                    f"{api['success_rate']:>5.1f}% success"
                )
                lines.append("║" + line.ljust(79) + "║")
        else:
            lines.append("║  No API data yet".ljust(80) + "║")

        lines.append("╠" + "═" * 79 + "╣")

        # Strategy Performance
        lines.append("║ 🎯 STRATEGY PERFORMANCE".ljust(80) + "║")
        strategies = metrics.get('strategies', {})
        if strategies:
            for name, strat in strategies.items():
                # Format strategy name
                display_name = name.replace('_', ' ').title()[:20]

                # Build status line
                line = (
                    f" {display_name:<20} "
                    f"{strat['tokens_found']:>3} found → "
                    f"{strat['tokens_passed']:>3} passed → "
                    f"{strat['trades']:>2} trades → "
                    f"{strat['win_rate']:>5.1f}%"
                )
                lines.append("║" + line.ljust(79) + "║")

            # Show best performer
            best = self.metrics.get_best_strategy()
            if best:
                best_line = f" 🏆 Best: {best.name} ({best.win_rate:.1f}% win rate, ${best.total_profit:.2f})"
                lines.append("║" + best_line.ljust(79) + "║")
        else:
            lines.append("║  No strategy data yet".ljust(80) + "║")

        lines.append("╠" + "═" * 79 + "╣")

        # Trigger Execution Status
        lines.append("║ ⚡ TRIGGER EXECUTION STATUS".ljust(80) + "║")
        triggers = metrics.get('triggers', {})
        if triggers:
            # Group by type
            trigger_types = {'entry': [], 'exit': [], 'partial_exit': []}
            for name, trig in triggers.items():
                # Determine type from name
                if 'entry' in name.lower() or 'buy' in name.lower():
                    ttype = 'entry'
                elif 'milestone' in name.lower() or 'partial' in name.lower():
                    ttype = 'partial_exit'
                else:
                    ttype = 'exit'

                trigger_types[ttype].append((name, trig))

            # Display by type
            for ttype, trig_list in trigger_types.items():
                if trig_list:
                    for name, trig in trig_list[:5]:  # Limit to 5 per type
                        display_name = name.replace('_', ' ').title()[:25]
                        success_emoji = "✅" if trig['success_rate'] > 95 else "⚠️" if trig['success_rate'] > 80 else "❌"
                        line = (
                            f" {success_emoji} {display_name:<25} "
                            f"{trig['times_fired']:>3} fired  "
                            f"{trig['success_rate']:>5.1f}% success"
                        )
                        lines.append("║" + line.ljust(79) + "║")
        else:
            lines.append("║  No trigger data yet".ljust(80) + "║")

        lines.append("╚" + "═" * 79 + "╝")

        return "\n".join(lines)

    def get_telegram_summary(self) -> str:
        """
        Get formatted summary for Telegram.

        Returns:
            Telegram-formatted summary
        """
        metrics = self.metrics.get_summary()

        lines = []
        lines.append("📊 **BOT STATUS REPORT**\n")

        # Uptime
        uptime = metrics['uptime']['formatted']
        lines.append(f"⏱️ Uptime: {uptime}")

        # System stats
        system = metrics['system']
        lines.append(f"🔄 Scan Cycles: {system['scan_cycles']}")
        lines.append(f"🔍 Tokens Analyzed: {system['tokens_analyzed']}")
        lines.append(f"⚠️ Errors This Hour: {system['errors_this_hour']}\n")

        # API Health
        apis = metrics.get('apis', {})
        if apis:
            lines.append("📡 **API Health:**")
            for name, api in apis.items():
                status = "✅" if api['uptime'] > 0.95 else "⚠️" if api['uptime'] > 0.80 else "❌"
                lines.append(f"{status} {name}: {api['success_rate']:.1f}% uptime")
            lines.append("")

        # Strategy Performance
        strategies = metrics.get('strategies', {})
        if strategies:
            lines.append("🎯 **Strategy Performance:**")
            for name, strat in strategies.items():
                display_name = name.replace('_', ' ').title()
                lines.append(
                    f"{display_name}: {strat['trades']} trades, "
                    f"{strat['win_rate']:.1f}% win rate"
                )

            # Best strategy
            best = self.metrics.get_best_strategy()
            if best:
                lines.append(f"\n🏆 Best: {best.name} ({best.win_rate:.1f}%)")

        return "\n".join(lines)

    def get_compact_status(self) -> str:
        """
        Get a compact one-line status.

        Returns:
            Compact status string
        """
        metrics = self.metrics.get_summary()

        # Check overall health
        apis = metrics.get('apis', {})
        all_apis_healthy = all(api['uptime'] > 0.90 for api in apis.values()) if apis else True

        system = metrics['system']
        low_errors = system['errors_this_hour'] < 5

        overall_status = "✅ HEALTHY" if (all_apis_healthy and low_errors) else "⚠️ DEGRADED"

        return (
            f"{overall_status} | "
            f"Up: {metrics['uptime']['formatted']} | "
            f"Cycles: {system['scan_cycles']} | "
            f"Tokens: {system['tokens_analyzed']} | "
            f"Errors: {system['errors_this_hour']}/hr"
        )

    def print_dashboard(self):
        """Print dashboard to console."""
        dashboard_text = self.render_console()
        print("\n" + dashboard_text + "\n")
