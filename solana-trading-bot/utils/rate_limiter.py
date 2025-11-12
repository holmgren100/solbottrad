import time
import asyncio
from collections import deque
from functools import wraps
from typing import Callable, Any
from utils.logger import setup_logger

class RateLimiter:
    """
    Rate limiter that supports both async and sync operations.
    Tracks API calls and enforces rate limits.
    """

    def __init__(self, calls_per_second: float = 2.0):
        """
        Initialize rate limiter.
        
        Args:
            calls_per_second: Maximum number of calls allowed per second
        """
        self.calls_per_second = calls_per_second
        self.min_interval = 1.0 / calls_per_second  # Minimum time between calls
        self.calls = deque()
        self.logger = setup_logger(__name__)
        
        self.logger.debug(f"RateLimiter initialized: {calls_per_second} calls/second")

    def __call__(self, func: Callable) -> Callable:
        """
        Decorator version of rate limiter for async functions.
        
        Args:
            func: The async function to rate limit
            
        Returns:
            Wrapped function with rate limiting
        """
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            await self.wait_if_needed()
            return await func(*args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            self.wait_if_needed_sync()
            return func(*args, **kwargs)

        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    async def wait_if_needed(self) -> None:
        """
        Async version: Check if we need to wait before making another API call.
        """
        try:
            now = time.time()
            
            # Clean up old calls (older than 1 second)
            while self.calls and self.calls[0] <= now - 1.0:
                self.calls.popleft()

            # Check if we need to wait
            if len(self.calls) >= self.calls_per_second:
                # Calculate wait time based on oldest call
                oldest_call = self.calls[0]
                wait_time = oldest_call + 1.0 - now
                
                if wait_time > 0:
                    self.logger.debug(f"Rate limit reached, waiting {wait_time:.2f} seconds")
                    await asyncio.sleep(wait_time)
                    
                    # Clean up again after waiting
                    now = time.time()
                    while self.calls and self.calls[0] <= now - 1.0:
                        self.calls.popleft()

            # Record this call
            self.calls.append(now)
            
        except Exception as e:
            self.logger.error(f"Error in async wait_if_needed: {str(e)}")
            raise

    def wait_if_needed_sync(self) -> None:
        """
        Sync version: Check if we need to wait before making another API call.
        """
        try:
            now = time.time()
            
            # Clean up old calls (older than 1 second)
            while self.calls and self.calls[0] <= now - 1.0:
                self.calls.popleft()

            # Check if we need to wait
            if len(self.calls) >= self.calls_per_second:
                # Calculate wait time based on oldest call
                oldest_call = self.calls[0]
                wait_time = oldest_call + 1.0 - now
                
                if wait_time > 0:
                    self.logger.debug(f"Rate limit reached, waiting {wait_time:.2f} seconds (sync)")
                    time.sleep(wait_time)
                    
                    # Clean up again after waiting
                    now = time.time()
                    while self.calls and self.calls[0] <= now - 1.0:
                        self.calls.popleft()

            # Record this call
            self.calls.append(now)
            
        except Exception as e:
            self.logger.error(f"Error in sync wait_if_needed: {str(e)}")
            raise

    def can_make_call(self) -> bool:
        """
        Check if a call can be made without waiting.
        
        Returns:
            True if a call can be made immediately, False otherwise
        """
        try:
            now = time.time()
            
            # Clean up old calls
            while self.calls and self.calls[0] <= now - 1.0:
                self.calls.popleft()

            return len(self.calls) < self.calls_per_second
            
        except Exception as e:
            self.logger.error(f"Error in can_make_call: {str(e)}")
            return False

    def get_wait_time(self) -> float:
        """
        Get the time needed to wait before the next call can be made.
        
        Returns:
            Wait time in seconds (0 if no wait needed)
        """
        try:
            now = time.time()
            
            # Clean up old calls
            while self.calls and self.calls[0] <= now - 1.0:
                self.calls.popleft()

            if len(self.calls) < self.calls_per_second:
                return 0.0
            
            # Calculate wait time based on oldest call
            oldest_call = self.calls[0]
            wait_time = oldest_call + 1.0 - now
            return max(0.0, wait_time)
            
        except Exception as e:
            self.logger.error(f"Error in get_wait_time: {str(e)}")
            return 0.0

    def reset(self) -> None:
        """Reset the rate limiter, clearing all recorded calls."""
        self.calls.clear()
        self.logger.debug("Rate limiter reset")

    def get_stats(self) -> dict:
        """
        Get current rate limiter statistics.
        
        Returns:
            Dictionary with current stats
        """
        try:
            now = time.time()
            
            # Clean up old calls
            while self.calls and self.calls[0] <= now - 1.0:
                self.calls.popleft()

            return {
                "calls_per_second_limit": self.calls_per_second,
                "current_calls_in_window": len(self.calls),
                "can_make_call": self.can_make_call(),
                "wait_time": self.get_wait_time(),
                "calls_remaining": max(0, self.calls_per_second - len(self.calls))
            }
            
        except Exception as e:
            self.logger.error(f"Error in get_stats: {str(e)}")
            return {}

# Test functions
async def test_async_rate_limiter():
    """Test async rate limiter functionality"""
    print("Testing async rate limiter...")
    
    limiter = RateLimiter(calls_per_second=2)  # 2 calls per second
    
    @limiter
    async def test_api_call(call_id: int):
        print(f"Making async API call {call_id} at {time.time():.2f}")
        return f"Result {call_id}"
    
    # Make several calls quickly
    start_time = time.time()
    tasks = [test_api_call(i) for i in range(5)]
    results = await asyncio.gather(*tasks)
    end_time = time.time()
    
    print(f"Async test completed in {end_time - start_time:.2f} seconds")
    print(f"Results: {results}")
    print(f"Stats: {limiter.get_stats()}")

def test_sync_rate_limiter():
    """Test sync rate limiter functionality"""
    print("\nTesting sync rate limiter...")
    
    limiter = RateLimiter(calls_per_second=2)  # 2 calls per second
    
    @limiter
    def test_api_call(call_id: int):
        print(f"Making sync API call {call_id} at {time.time():.2f}")
        return f"Result {call_id}"
    
    # Make several calls quickly
    start_time = time.time()
    results = []
    for i in range(5):
        result = test_api_call(i)
        results.append(result)
    end_time = time.time()
    
    print(f"Sync test completed in {end_time - start_time:.2f} seconds")
    print(f"Results: {results}")
    print(f"Stats: {limiter.get_stats()}")

async def test_manual_rate_limiter():
    """Test manual rate limiter usage"""
    print("\nTesting manual rate limiter...")
    
    limiter = RateLimiter(calls_per_second=3)
    
    for i in range(5):
        await limiter.wait_if_needed()
        print(f"Manual call {i} at {time.time():.2f}")

# Main test function
async def test_rate_limiter():
    """Run all rate limiter tests"""
    await test_async_rate_limiter()
    test_sync_rate_limiter()
    await test_manual_rate_limiter()

if __name__ == "__main__":
    asyncio.run(test_rate_limiter())