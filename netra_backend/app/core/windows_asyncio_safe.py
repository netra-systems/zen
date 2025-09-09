"""
Windows-Safe Asyncio Patterns for WebSocket and Streaming Operations

CRITICAL FIX: Windows asyncio has architectural limitations with concurrent streaming operations
that can cause deadlocks when using nested wait_for() calls with multiple sleep() patterns.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: System Stability (preventing $40K+ MRR at risk from streaming deadlocks)
- Value Impact: Ensures streaming functionality works on all platforms including Windows development
- Strategic Impact: Prevents Windows-specific asyncio deadlocks that completely break streaming

ROOT CAUSE ADDRESSED:
- Windows asyncio event loop deadlocks with concurrent streaming operations
- Nested asyncio.wait_for() calls causing circular dependencies
- Multiple asyncio.sleep() calls blocking event loop progression

SSOT COMPLIANT: Single source of truth for Windows-safe asyncio patterns
"""

import asyncio
import platform
import sys
import time
from typing import Any, Awaitable, Callable, Optional, TypeVar, Union
from functools import wraps

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)

T = TypeVar('T')

# CRITICAL FIX: Store original asyncio functions to prevent infinite recursion
# These references are preserved before any monkey patching occurs
_ORIGINAL_ASYNCIO_SLEEP = asyncio.sleep
_ORIGINAL_ASYNCIO_WAIT_FOR = asyncio.wait_for  
_ORIGINAL_ASYNCIO_GATHER = asyncio.gather

class WindowsAsyncioSafePatterns:
    """Windows-safe asyncio patterns to prevent deadlocks."""
    
    def __init__(self):
        self.is_windows = platform.system().lower() == "windows"
        self.asyncio_policy = None
        if self.is_windows:
            self._setup_windows_asyncio_policy()
    
    def _setup_windows_asyncio_policy(self) -> None:
        """Setup Windows-specific asyncio event loop policy."""
        try:
            if sys.version_info >= (3, 8):
                # Use ProactorEventLoop for Windows (better for concurrent operations)
                if asyncio.get_event_loop_policy().__class__.__name__ == 'WindowsProactorEventLoopPolicy':
                    logger.debug("ProactorEventLoop policy already active")
                else:
                    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
                    logger.info("Set WindowsProactorEventLoopPolicy for better concurrent operation support")
            else:
                logger.debug("Python < 3.8 - using default asyncio policy")
        except Exception as e:
            logger.warning(f"Could not set Windows asyncio policy: {e}")
    
    async def safe_sleep(self, delay: float) -> None:
        """Windows-safe sleep that prevents event loop blocking.
        
        Args:
            delay: Sleep duration in seconds
        """
        # CRITICAL FIX: Always use the stored original asyncio.sleep to prevent recursion
        # This method should NEVER be subject to monkey-patching
        if self.is_windows and delay > 0.1:
            # Break long sleeps into smaller chunks on Windows to prevent deadlocks
            remaining = delay
            chunk_size = 0.05  # 50ms chunks
            while remaining > 0:
                sleep_time = min(chunk_size, remaining)
                await _ORIGINAL_ASYNCIO_SLEEP(sleep_time)
                remaining -= sleep_time
                # Allow other tasks to run between chunks
                await _ORIGINAL_ASYNCIO_SLEEP(0)
        else:
            # For short delays or non-Windows, use original sleep directly
            await _ORIGINAL_ASYNCIO_SLEEP(delay)
    
    async def safe_wait_for(
        self, 
        awaitable: Awaitable[T], 
        timeout: float, 
        default: Optional[T] = None
    ) -> T:
        """Windows-safe wait_for that prevents nested deadlocks.
        
        Args:
            awaitable: The awaitable to wait for
            timeout: Timeout in seconds
            default: Default value to return on timeout (if None, raises TimeoutError)
            
        Returns:
            Result of awaitable or default value
            
        Raises:
            asyncio.TimeoutError: If timeout occurs and no default provided
        """
        if self.is_windows:
            # On Windows, use create_task to prevent nested wait_for deadlocks
            task = asyncio.create_task(awaitable)
            
            start_time = time.time()
            check_interval = 0.01  # 10ms check interval
            
            while not task.done():
                elapsed = time.time() - start_time
                if elapsed >= timeout:
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
                    
                    if default is not None:
                        return default
                    raise asyncio.TimeoutError(f"Operation timed out after {timeout}s")
                
                # Non-blocking sleep to allow other tasks
                await _ORIGINAL_ASYNCIO_SLEEP(min(check_interval, timeout - elapsed))
            
            return await task
        else:
            # Non-Windows platforms can use standard wait_for
            try:
                return await _ORIGINAL_ASYNCIO_WAIT_FOR(awaitable, timeout=timeout)
            except asyncio.TimeoutError:
                if default is not None:
                    return default
                raise
    
    async def safe_gather(self, *awaitables, return_exceptions: bool = False) -> list:
        """Windows-safe gather that prevents deadlocks with concurrent operations.
        
        Args:
            *awaitables: Awaitables to execute concurrently
            return_exceptions: Whether to return exceptions instead of raising
            
        Returns:
            List of results
        """
        if self.is_windows and len(awaitables) > 1:
            # On Windows, limit concurrency to prevent deadlocks
            max_concurrent = 3
            results = []
            
            for i in range(0, len(awaitables), max_concurrent):
                chunk = awaitables[i:i + max_concurrent]
                try:
                    chunk_results = await _ORIGINAL_ASYNCIO_GATHER(*chunk, return_exceptions=return_exceptions)
                    results.extend(chunk_results)
                    # Small delay between chunks to prevent event loop saturation
                    if i + max_concurrent < len(awaitables):
                        await _ORIGINAL_ASYNCIO_SLEEP(0.01)
                except Exception as e:
                    if return_exceptions:
                        results.extend([e] * len(chunk))
                    else:
                        raise
            
            return results
        else:
            # Non-Windows or single awaitable
            return await _ORIGINAL_ASYNCIO_GATHER(*awaitables, return_exceptions=return_exceptions)
    
    async def safe_progressive_delay(
        self, 
        attempt: int, 
        base_delay: float = 0.1, 
        max_delay: float = 5.0,
        multiplier: float = 2.0
    ) -> None:
        """Windows-safe progressive delay for retry patterns.
        
        Args:
            attempt: Current attempt number (0-based)
            base_delay: Base delay in seconds
            max_delay: Maximum delay in seconds
            multiplier: Delay multiplier for exponential backoff
        """
        delay = min(base_delay * (multiplier ** attempt), max_delay)
        await self.safe_sleep(delay)
    
    def create_safe_timeout_context(self, timeout: float):
        """Create a Windows-safe timeout context that doesn't use nested wait_for."""
        return WindowsSafeTimeoutContext(self, timeout)


class WindowsSafeTimeoutContext:
    """Context manager for Windows-safe timeout operations."""
    
    def __init__(self, asyncio_safe: WindowsAsyncioSafePatterns, timeout: float):
        self.asyncio_safe = asyncio_safe
        self.timeout = timeout
        self.start_time = None
        self.is_timed_out = False
    
    async def __aenter__(self):
        self.start_time = time.time()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass
    
    def check_timeout(self) -> bool:
        """Check if timeout has been exceeded."""
        if self.start_time is None:
            return False
        
        elapsed = time.time() - self.start_time
        self.is_timed_out = elapsed >= self.timeout
        return self.is_timed_out
    
    def remaining_time(self) -> float:
        """Get remaining time before timeout."""
        if self.start_time is None:
            return self.timeout
        
        elapsed = time.time() - self.start_time
        return max(0, self.timeout - elapsed)


# Global instance for easy access
_windows_asyncio_safe = WindowsAsyncioSafePatterns()


async def windows_safe_sleep(delay: float) -> None:
    """Global function for Windows-safe sleep."""
    await _windows_asyncio_safe.safe_sleep(delay)


async def windows_safe_wait_for(
    awaitable: Awaitable[T], 
    timeout: float, 
    default: Optional[T] = None
) -> T:
    """Global function for Windows-safe wait_for."""
    return await _windows_asyncio_safe.safe_wait_for(awaitable, timeout, default)


async def windows_safe_gather(*awaitables, return_exceptions: bool = False) -> list:
    """Global function for Windows-safe gather."""
    return await _windows_asyncio_safe.safe_gather(*awaitables, return_exceptions=return_exceptions)


async def windows_safe_progressive_delay(
    attempt: int, 
    base_delay: float = 0.1, 
    max_delay: float = 5.0,
    multiplier: float = 2.0
) -> None:
    """Global function for Windows-safe progressive delay."""
    await _windows_asyncio_safe.safe_progressive_delay(attempt, base_delay, max_delay, multiplier)


def windows_asyncio_safe(func: Callable) -> Callable:
    """Decorator to make async functions Windows-safe by replacing asyncio calls.
    
    CRITICAL FIX: This decorator creates isolated monkey-patching that doesn't interfere
    with the internal safe_sleep implementations that rely on _ORIGINAL_ASYNCIO_SLEEP.
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Store the current asyncio functions (might already be monkey-patched)
        current_sleep = asyncio.sleep
        current_wait_for = asyncio.wait_for
        current_gather = asyncio.gather
        
        # Create isolated Windows-safe functions for this decorator context
        # These functions use the ORIGINAL asyncio functions directly to avoid recursion
        async def isolated_windows_safe_sleep(delay: float) -> None:
            """Isolated Windows-safe sleep that bypasses any monkey-patching."""
            await _windows_asyncio_safe.safe_sleep(delay)
        
        async def isolated_windows_safe_wait_for(
            awaitable: Awaitable[T], 
            timeout: float, 
            default: Optional[T] = None
        ) -> T:
            """Isolated Windows-safe wait_for that bypasses any monkey-patching."""
            return await _windows_asyncio_safe.safe_wait_for(awaitable, timeout, default)
        
        async def isolated_windows_safe_gather(*awaitables, return_exceptions: bool = False) -> list:
            """Isolated Windows-safe gather that bypasses any monkey-patching."""
            return await _windows_asyncio_safe.safe_gather(*awaitables, return_exceptions=return_exceptions)
        
        try:
            # Replace with isolated Windows-safe versions (no circular references)
            asyncio.sleep = isolated_windows_safe_sleep
            asyncio.wait_for = isolated_windows_safe_wait_for
            asyncio.gather = isolated_windows_safe_gather
            
            return await func(*args, **kwargs)
        finally:
            # Restore the functions that were active before this decorator
            asyncio.sleep = current_sleep
            asyncio.wait_for = current_wait_for
            asyncio.gather = current_gather
    
    return wrapper


# Export main utilities
__all__ = [
    "WindowsAsyncioSafePatterns",
    "WindowsSafeTimeoutContext", 
    "windows_safe_sleep",
    "windows_safe_wait_for",
    "windows_safe_gather",
    "windows_safe_progressive_delay",
    "windows_asyncio_safe",
]