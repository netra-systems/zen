# Shim module for backward compatibility
# Rate limiting integrated into WebSocket auth
from netra_backend.app.websocket_core.auth import RateLimiter
from netra_backend.app.websocket_core.utils import check_rate_limit

__all__ = ['RateLimiter', 'check_rate_limit']
