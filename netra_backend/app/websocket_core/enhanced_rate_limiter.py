# Shim module for backward compatibility
from netra_backend.app.websocket_core.rate_limiter import AdaptiveRateLimiter as EnhancedRateLimiter
from netra_backend.app.websocket_core.utils import check_rate_limit

__all__ = ['EnhancedRateLimiter', 'check_rate_limit']
