"""Resource pooling for LLM operations.

Manages LLM request pooling with rate limiting to prevent
API overload and ensure fair resource allocation.
"""

import asyncio
from collections import deque
from datetime import datetime, timedelta


class RequestPool:
    """Manages LLM request pooling with rate limiting."""
    
    def __init__(self, max_concurrent: int = 5, 
                 requests_per_minute: int = 60):
        """Initialize request pool with limits."""
        self.max_concurrent = max_concurrent
        self.requests_per_minute = requests_per_minute
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._request_times = deque(maxlen=requests_per_minute)
        self._lock = asyncio.Lock()
    
    async def acquire(self) -> None:
        """Acquire permission to make request."""
        await self._check_rate_limit()
        await self._semaphore.acquire()
        await self._record_request()
    
    async def _check_rate_limit(self) -> None:
        """Check and enforce rate limiting."""
        async with self._lock:
            await self._clean_old_requests()
            await self._wait_if_at_limit()
    
    async def _clean_old_requests(self) -> None:
        """Remove requests older than 1 minute."""
        cutoff = datetime.now() - timedelta(minutes=1)
        while self._request_times:
            if self._request_times[0] >= cutoff:
                break
            self._request_times.popleft()
    
    async def _wait_if_at_limit(self) -> None:
        """Wait if at rate limit."""
        if len(self._request_times) >= self.requests_per_minute:
            oldest = self._request_times[0]
            wait_time = self._calculate_wait_time(oldest)
            if wait_time > 0:
                await asyncio.sleep(wait_time)
    
    def _calculate_wait_time(self, oldest: datetime) -> float:
        """Calculate wait time until rate limit clears."""
        elapsed = (datetime.now() - oldest).total_seconds()
        return max(0, 60 - elapsed + 0.1)
    
    async def _record_request(self) -> None:
        """Record request timestamp."""
        async with self._lock:
            self._request_times.append(datetime.now())
    
    def release(self) -> None:
        """Release request slot."""
        self._semaphore.release()
    
    async def __aenter__(self):
        """Context manager entry."""
        await self.acquire()
        return self
    
    async def __aexit__(self, *args):
        """Context manager exit."""
        self.release()