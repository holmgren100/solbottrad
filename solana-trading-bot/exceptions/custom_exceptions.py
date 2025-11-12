class BaseCustomException(Exception):
    """Base exception class for custom exceptions"""
    pass

class ConnectionError(Exception):
    """Raised when a connection fails"""
    pass

class APIError(BaseCustomException):
    """Exception raised for API-related errors"""
    pass

class VolumeMonitorError(BaseCustomException):
    """Exception raised for volume monitoring errors"""
    pass

class WalletMonitorError(BaseCustomException):
    """Exception raised for wallet monitoring errors"""
    pass

class TradingError(BaseCustomException):
    """Exception raised for trading-related errors"""
    pass

class ConfigurationError(BaseCustomException):
    """Exception raised for configuration-related errors"""
    pass

class RateLimitExceededError(Exception):
    """Raised when the API rate limit is exceeded."""
    pass

class RateLimitError(BaseCustomException):
    """Exception raised for rate limiting issues"""
    pass

class ModelNotTrainedError(BaseCustomException):
    """Exception raised when a model is used before being trained"""
    pass

class ModelNotTrainedError(Exception):
    """Exception raised when a model is used before being trained"""
    pass