"""Configuration module for the trading bot."""

from .settings import Settings

# Create global settings instance
settings = Settings()

__all__ = ['Settings', 'settings']
