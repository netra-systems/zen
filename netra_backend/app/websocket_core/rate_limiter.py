# Shim module for backward compatibility
# Rate limiting integrated into WebSocket auth
from netra_backend.app.services.rate_limiter import RateLimiter
from netra_backend.app.websocket_core.utils import check_rate_limit
import time
from typing import Dict, Optional, Tuple


# Enhanced rate limiter for cold start issues
class WebSocketRateLimiter:
    """Enhanced rate limiter with backpressure support."""
    
    def __init__(self):
        """Initialize rate limiter."""
        self.connection_times: Dict[str, list] = {}
        self.backoff_times: Dict[str, float] = {}
        
    async def check_rate_limit(self, client_ip: str) -> Tuple[bool, Optional[float]]:
        """Check if connection is rate limited."""
        current_time = time.time()
        
        # Simple rate limiting logic
        if client_ip in self.backoff_times:
            if current_time < self.backoff_times[client_ip]:
                remaining = self.backoff_times[client_ip] - current_time
                return False, remaining
            else:
                del self.backoff_times[client_ip]
        
        return True, None
        
    async def record_connection_attempt(self, client_ip: str) -> None:
        """Record a connection attempt."""
        current_time = time.time()
        if client_ip not in self.connection_times:
            self.connection_times[client_ip] = []
        self.connection_times[client_ip].append(current_time)
        
    async def record_connection_complete(self, client_ip: str, success: bool) -> None:
        """Record connection completion."""
        if not success:
            # Apply backoff on failure
            self.backoff_times[client_ip] = time.time() + 5.0  # 5 second backoff
            
    def get_stats(self) -> Dict:
        """Get rate limiter statistics."""
        return {
            'tracked_ips': len(self.connection_times),
            'active_backoffs': len(self.backoff_times)
        }


# Global instance
_enhanced_rate_limiter = WebSocketRateLimiter()


def get_rate_limiter() -> WebSocketRateLimiter:
    """Get enhanced rate limiter instance."""
    return _enhanced_rate_limiter


async def check_connection_rate_limit(client_ip: str) -> Tuple[bool, Optional[float]]:
    """Check connection rate limits."""
    return await _enhanced_rate_limiter.check_rate_limit(client_ip)


class AdaptiveRateLimiter:
    """Adaptive rate limiter that adjusts limits based on system load."""
    
    def __init__(self, base_rate: int = 100, window_seconds: int = 60):
        self.base_rate = base_rate
        self.window_seconds = window_seconds
        self.client_history: Dict[str, list] = {}
        
    def is_allowed(self, client_id: str, current_load: Optional[float] = None) -> bool:
        """Check if client is allowed to make request."""
        now = time.time()
        window_start = now - self.window_seconds
        
        # Clean old entries
        if client_id in self.client_history:
            self.client_history[client_id] = [
                req_time for req_time in self.client_history[client_id]
                if req_time > window_start
            ]
        else:
            self.client_history[client_id] = []
        
        # Calculate adaptive rate based on load
        adaptive_rate = self.base_rate
        if current_load and current_load > 0.8:
            adaptive_rate = int(self.base_rate * 0.5)  # Reduce rate by 50% under high load
        elif current_load and current_load > 0.6:
            adaptive_rate = int(self.base_rate * 0.75)  # Reduce rate by 25% under moderate load
            
        # Check if under limit
        if len(self.client_history[client_id]) < adaptive_rate:
            self.client_history[client_id].append(now)
            return True
        
        return False
        
    def get_remaining_quota(self, client_id: str) -> int:
        """Get remaining quota for client."""
        if client_id not in self.client_history:
            return self.base_rate
        return max(0, self.base_rate - len(self.client_history[client_id]))


__all__ = ['RateLimiter', 'check_rate_limit', 'AdaptiveRateLimiter']
