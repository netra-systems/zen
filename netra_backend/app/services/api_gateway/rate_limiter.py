"""API Gateway Rate Limiter implementation."""

import time
from typing import Dict, Optional, Any
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class RateLimitConfig:
    """Rate limit configuration."""
    requests_per_minute: int
    requests_per_hour: int
    burst_size: int = 10
    enabled: bool = True


class RateLimitState:
    """Tracks rate limit state for a client."""
    
    def __init__(self):
        self.requests_this_minute = 0
        self.requests_this_hour = 0
        self.last_minute_reset = time.time()
        self.last_hour_reset = time.time()
        self.burst_tokens = 10
    
    def reset_if_needed(self) -> None:
        """Reset counters if time windows have elapsed."""
        current_time = time.time()
        
        # Reset minute counter
        if current_time - self.last_minute_reset >= 60:
            self.requests_this_minute = 0
            self.last_minute_reset = current_time
        
        # Reset hour counter
        if current_time - self.last_hour_reset >= 3600:
            self.requests_this_hour = 0
            self.last_hour_reset = current_time


class RateLimiter:
    """Rate limiter for API Gateway."""
    
    def __init__(self, config: Optional[RateLimitConfig] = None):
        self.config = config or RateLimitConfig(
            requests_per_minute=60,
            requests_per_hour=1000,
            burst_size=10,
            enabled=True
        )
        self.states: Dict[str, RateLimitState] = defaultdict(RateLimitState)
    
    def check_rate_limit(self, client_id: str) -> tuple[bool, Optional[str]]:
        """Check if a client has exceeded rate limits."""
        if not self.config.enabled:
            return True, None
        
        state = self.states[client_id]
        state.reset_if_needed()
        
        # Check minute limit
        if state.requests_this_minute >= self.config.requests_per_minute:
            return False, "Rate limit exceeded: too many requests per minute"
        
        # Check hour limit
        if state.requests_this_hour >= self.config.requests_per_hour:
            return False, "Rate limit exceeded: too many requests per hour"
        
        # Update counters
        state.requests_this_minute += 1
        state.requests_this_hour += 1
        
        return True, None
    
    def reset_client(self, client_id: str) -> None:
        """Reset rate limit state for a client."""
        if client_id in self.states:
            del self.states[client_id]


class ApiGatewayManager:
    """Manages API Gateway configuration and state."""
    
    def __init__(self):
        self.rate_limiter = None
        self.enabled = True
        self.config = {}
    
    def set_rate_limiter(self, rate_limiter: 'ApiGatewayRateLimiter') -> None:
        """Set the rate limiter instance."""
        self.rate_limiter = rate_limiter
    
    def get_config(self) -> Dict[str, Any]:
        """Get current configuration."""
        return self.config.copy()
    
    def update_config(self, config: Dict[str, Any]) -> None:
        """Update configuration."""
        self.config.update(config)


class ApiGatewayRateLimiter:
    """Rate limiter for API Gateway."""
    
    def __init__(self, default_config: Optional[RateLimitConfig] = None):
        self.default_config = default_config or RateLimitConfig(
            requests_per_minute=60,
            requests_per_hour=1000
        )
        self.client_configs: Dict[str, RateLimitConfig] = {}
        self.client_states: Dict[str, RateLimitState] = defaultdict(RateLimitState)
        self.enabled = True
    
    def set_client_config(self, client_id: str, config: RateLimitConfig) -> None:
        """Set rate limit configuration for a specific client."""
        self.client_configs[client_id] = config
    
    def is_allowed(self, client_id: str, endpoint: str = "") -> bool:
        """Check if request is allowed for client."""
        if not self.enabled:
            return True
        
        config = self.client_configs.get(client_id, self.default_config)
        if not config.enabled:
            return True
        
        state = self.client_states[client_id]
        state.reset_if_needed()
        
        # Check rate limits
        if state.requests_this_minute >= config.requests_per_minute:
            return False
        
        if state.requests_this_hour >= config.requests_per_hour:
            return False
        
        # Allow request and increment counters
        state.requests_this_minute += 1
        state.requests_this_hour += 1
        
        return True
    
    def get_client_stats(self, client_id: str) -> Dict[str, Any]:
        """Get rate limit stats for a client."""
        if client_id not in self.client_states:
            return {'requests_this_minute': 0, 'requests_this_hour': 0}
        
        state = self.client_states[client_id]
        state.reset_if_needed()
        
        return {
            'requests_this_minute': state.requests_this_minute,
            'requests_this_hour': state.requests_this_hour,
            'burst_tokens': state.burst_tokens
        }
    
    def reset_client(self, client_id: str) -> None:
        """Reset rate limit state for a client."""
        if client_id in self.client_states:
            del self.client_states[client_id]
    
    def disable(self) -> None:
        """Disable rate limiting."""
        self.enabled = False
    
    def enable(self) -> None:
        """Enable rate limiting."""
        self.enabled = True
