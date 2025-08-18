"""Rate Limiter Module - Handles API rate limiting for GCP requests.

Business Value Justification (BVJ):
1. Segment: Mid & Enterprise
2. Business Goal: Ensure reliable GCP API access without quota violations
3. Value Impact: Prevents service disruption from rate limiting
4. Revenue Impact: Supports $15K MRR reliability monitoring features

CRITICAL ARCHITECTURAL COMPLIANCE:
- Maximum file size: 300 lines (enforced)
- Maximum function size: 8 lines (enforced)
- Single responsibility: Rate limiting only
"""

import asyncio
from datetime import datetime, timezone
from typing import Dict


class GCPRateLimiter:
    """Handles rate limiting for GCP Error Reporting API calls."""
    
    def __init__(self, rate_limit_per_minute: int = 1000):
        self.rate_limit_per_minute = rate_limit_per_minute
        self._rate_tracker = self._create_rate_tracker()
        self._last_request_time = 0.0
    
    def _create_rate_tracker(self) -> Dict[str, float]:
        """Create rate tracking dictionary."""
        return {
            "requests": 0.0,
            "window_start": datetime.now(timezone.utc).timestamp()
        }
    
    async def enforce_rate_limit(self) -> None:
        """Enforce API rate limiting before making requests."""
        current_time = datetime.now(timezone.utc).timestamp()
        self._reset_window_if_needed(current_time)
        await self._wait_if_rate_limited(current_time)
        self._increment_request_count(current_time)
    
    def _reset_window_if_needed(self, current_time: float) -> None:
        """Reset rate limiting window if 60 seconds have passed."""
        if current_time - self._rate_tracker["window_start"] >= 60:
            self._rate_tracker["requests"] = 0.0
            self._rate_tracker["window_start"] = current_time
    
    async def _wait_if_rate_limited(self, current_time: float) -> None:
        """Wait if rate limit would be exceeded."""
        if self._rate_tracker["requests"] >= self.rate_limit_per_minute:
            wait_time = self._calculate_wait_time(current_time)
            if wait_time > 0:
                await asyncio.sleep(wait_time)
                self._reset_window_if_needed(datetime.now(timezone.utc).timestamp())
    
    def _calculate_wait_time(self, current_time: float) -> float:
        """Calculate time to wait until next rate window."""
        window_elapsed = current_time - self._rate_tracker["window_start"]
        return max(0, 60 - window_elapsed)
    
    def _increment_request_count(self, current_time: float) -> None:
        """Increment rate limiter request count."""
        self._rate_tracker["requests"] += 1
        self._last_request_time = current_time
    
    def get_current_usage(self) -> Dict[str, float]:
        """Get current rate limiting usage statistics."""
        current_time = datetime.now(timezone.utc).timestamp()
        window_elapsed = current_time - self._rate_tracker["window_start"]
        remaining_requests = max(0, self.rate_limit_per_minute - self._rate_tracker["requests"])
        return {
            "requests_made": self._rate_tracker["requests"],
            "requests_remaining": remaining_requests,
            "window_elapsed_seconds": window_elapsed,
            "requests_per_minute_limit": self.rate_limit_per_minute
        }