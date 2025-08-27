"""Async rate limiting functionality for controlling operation frequency."""

import asyncio
import time
from typing import List


class AsyncRateLimiter:
    """Rate limiter for async operations."""
    
    def __init__(self, max_calls: int, time_window: float):
        self._max_calls = max_calls
        self._time_window = time_window
        self._calls: List[float] = []
        self._lock = asyncio.Lock()
    
    async def acquire(self):
        """Acquire permission to make a call."""
        async with self._lock:
            now = time.time()
            self._cleanup_old_calls(now)
            
            if await self._should_wait(now):
                # Release lock before recursive call to avoid deadlock
                oldest_call = min(self._calls)
                wait_time = self._calculate_wait_time(oldest_call)
        
        # If we need to wait, do so outside the lock
        if 'wait_time' in locals() and wait_time > 0:
            await asyncio.sleep(wait_time)
            await self.acquire()  # Recursive call after waiting, without holding lock
        else:
            # Only record the call if we didn't need to wait
            async with self._lock:
                now = time.time()
                self._cleanup_old_calls(now)
                self._record_call(now)
    
    def _cleanup_old_calls(self, now: float):
        """Remove old calls outside the time window."""
        self._calls = [
            call_time for call_time in self._calls 
            if now - call_time < self._time_window
        ]
    
    async def _should_wait(self, now: float) -> bool:
        """Check if we need to wait before making a call."""
        return len(self._calls) >= self._max_calls
    
    
    def _calculate_wait_time(self, oldest_call: float) -> float:
        """Calculate how long to wait before next call."""
        now = time.time()
        return self._time_window - (now - oldest_call)
    
    def _record_call(self, now: float):
        """Record this call timestamp."""
        self._calls.append(now)
    
    @property
    def current_calls(self) -> int:
        """Get current number of calls in the time window."""
        now = time.time()
        return len([
            call_time for call_time in self._calls 
            if now - call_time < self._time_window
        ])
    
    @property
    def max_calls(self) -> int:
        """Get maximum allowed calls."""
        return self._max_calls
    
    @property
    def time_window(self) -> float:
        """Get time window in seconds."""
        return self._time_window
    
    @property
    def remaining_calls(self) -> int:
        """Get remaining calls available in current window."""
        return max(0, self._max_calls - self.current_calls)
    
    async def reset(self):
        """Reset the rate limiter state."""
        async with self._lock:
            self._calls.clear()
    
    async def can_make_call(self) -> bool:
        """Check if a call can be made without waiting."""
        async with self._lock:
            now = time.time()
            self._cleanup_old_calls(now)
            return len(self._calls) < self._max_calls