"""
🔒 PROTECTED - ML Bot 2 Monitoring Module

Contains the PriceValidator for dual-source price validation.

Dual-Source Validation:
- DexScreener + Jupiter price cross-check
- Use average if within 10% agreement
- Reject suspicious drops >80%
- Prevent bad data from causing fake losses

WHY IT WORKS:
- Prevents 100% losses from bad API data
- Catches price manipulation
- Saved countless trades
- Proven: Critical for data integrity
"""

from ml_bot_core.monitoring.price_validator import PriceValidator

__all__ = ['PriceValidator']
