"""WebSocket CORS handling and security configuration.

This module provides CORS handling specifically for WebSocket connections,
which require special handling compared to regular HTTP CORS.
"""

import re
from typing import List, Optional, Union

from fastapi import Request, WebSocket
from starlette.middleware.cors import CORSMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)

def _get_default_websocket_origins():
    """Get default WebSocket origins from unified configuration."""
    try:
        from netra_backend.app.core.configuration.base import get_unified_config
        config = get_unified_config()
        
        # Start with configured frontend URL
        default_origins = []
        if hasattr(config, 'frontend_url') and config.frontend_url:
            default_origins.append(config.frontend_url)
            # Add HTTPS variant
            if config.frontend_url.startswith("http://"):
                https_url = config.frontend_url.replace("http://", "https://", 1)
                default_origins.append(https_url)
        
        # Add common development ports if in development
        environment = getattr(config, 'environment', 'development').lower()
        if environment in ['development', 'testing']:
            dev_ports = [3000, 3001, 3002, 3003, 4000, 4001, 4200, 5173, 5174]
            for port in dev_ports:
                default_origins.extend([
                    f"http://localhost:{port}",
                    f"https://localhost:{port}",
                    f"http://127.0.0.1:{port}",
                    f"https://127.0.0.1:{port}"
                ])
        
        return default_origins
    except Exception:
        # Fallback to minimal origins if config fails
        return [
            "http://localhost:3000",
            "https://localhost:3000",
            "http://localhost:3010"  # Common frontend port
        ]


# Default allowed origins for WebSocket connections - loaded from configuration
DEFAULT_WEBSOCKET_ORIGINS = _get_default_websocket_origins()

# Production origins (should be configured via environment variables)
PRODUCTION_ORIGINS = [
    "https://netrasystems.ai",
    "https://www.netrasystems.ai", 
    "https://app.netrasystems.ai",
    "https://staging.netrasystems.ai"
]

# Security configuration constants
SECURITY_CONFIG = {
    "max_origin_length": 253,  # Maximum valid domain length per RFC
    "require_https_production": True,  # Require HTTPS in production
    "block_suspicious_patterns": True,  # Block suspicious origin patterns
    "log_security_violations": True,  # Log security violations for monitoring
    "rate_limit_violations": True,  # Rate limit origins with violations
}

# Suspicious patterns to block - relaxed for development
SUSPICIOUS_PATTERNS = [
    # Allow more localhost ports in development - only block very unusual ones
    r".*localhost.*:(?!3000|3001|3002|3003|4000|4001|4200|5173|5174|8000|8001|8002|8003|8080|8081|8082|8083)\d+.*",  # Block only unexpected localhost ports
    r".*\d+\.\d+\.\d+\.\d+.*",  # Block direct IP addresses in production
    r".*\.ngrok\.io.*",  # Block ngrok tunnels in production
    r".*\.localtunnel\.me.*",  # Block localtunnel in production
    r".*\.herokuapp\.com.*",  # Block heroku apps unless explicitly allowed
    r".*chrome-extension://.*",  # Block browser extensions
    r".*moz-extension://.*",  # Block Firefox extensions
]


class WebSocketCORSHandler:
    """Handle CORS for WebSocket connections with enhanced security."""
    
    def __init__(self, allowed_origins: Optional[List[str]] = None, 
                 environment: str = "development"):
        """Initialize WebSocket CORS handler.
        
        Args:
            allowed_origins: List of allowed origins for WebSocket connections.
                            If None, uses default development origins.
            environment: Current environment (development, staging, production)
        """
        self.allowed_origins = allowed_origins or DEFAULT_WEBSOCKET_ORIGINS
        self.environment = environment
        self._origin_patterns = self._compile_origin_patterns()
        self._suspicious_patterns = self._compile_suspicious_patterns()
        self._violation_counts = {}  # Track violations per origin
        self._blocked_origins = set()  # Temporarily blocked origins
    
    def _compile_origin_patterns(self) -> List[re.Pattern]:
        """Compile origin patterns for efficient matching."""
        patterns = []
        for origin in self.allowed_origins:
            if '*' in origin:
                # Convert wildcard patterns to regex
                pattern = origin.replace('*', '.*')
                patterns.append(re.compile(f'^{pattern}$', re.IGNORECASE))
            else:
                # Exact match pattern
                patterns.append(re.compile(f'^{re.escape(origin)}$', re.IGNORECASE))
        
        return patterns
    
    def _compile_suspicious_patterns(self) -> List[re.Pattern]:
        """Compile suspicious origin patterns for security blocking."""
        patterns = []
        if SECURITY_CONFIG["block_suspicious_patterns"]:
            for pattern_str in SUSPICIOUS_PATTERNS:
                patterns.append(re.compile(pattern_str, re.IGNORECASE))
        return patterns
    
    def _is_suspicious_origin(self, origin: str) -> bool:
        """Check if origin matches suspicious patterns."""
        if not SECURITY_CONFIG["block_suspicious_patterns"]:
            return False
        
        for pattern in self._suspicious_patterns:
            if pattern.match(origin):
                return True
        return False
    
    def _validate_origin_security(self, origin: str) -> tuple[bool, str]:
        """Validate origin against security constraints.
        
        Returns:
            Tuple of (is_valid, reason_if_invalid)
        """
        if not origin:
            return False, "No origin header provided"
        
        # Check length constraints
        if len(origin) > SECURITY_CONFIG["max_origin_length"]:
            return False, f"Origin too long ({len(origin)} > {SECURITY_CONFIG['max_origin_length']})"
        
        # Check if temporarily blocked
        if origin in self._blocked_origins:
            return False, "Origin temporarily blocked due to violations"
        
        # Production HTTPS requirement
        if (self.environment == "production" and 
            SECURITY_CONFIG["require_https_production"] and 
            not origin.startswith("https://")):
            return False, "HTTPS required in production"
        
        # Check suspicious patterns
        if self._is_suspicious_origin(origin):
            return False, "Origin matches suspicious pattern"
        
        return True, ""
    
    def _record_violation(self, origin: str, reason: str) -> None:
        """Record security violation for monitoring and rate limiting."""
        if not SECURITY_CONFIG["log_security_violations"]:
            return
        
        # Track violation count
        if origin not in self._violation_counts:
            self._violation_counts[origin] = 0
        self._violation_counts[origin] += 1
        
        # Temporarily block origins with too many violations
        if (SECURITY_CONFIG["rate_limit_violations"] and 
            self._violation_counts[origin] >= 5):
            self._blocked_origins.add(origin)
            logger.warning(f"Origin {origin} temporarily blocked after {self._violation_counts[origin]} violations")
        
        # Log security violation
        logger.warning(f"WebSocket CORS security violation: {reason} for origin {origin}")
    
    def _is_origin_explicitly_allowed(self, origin: str) -> bool:
        """Check if origin is explicitly allowed by patterns."""
        for pattern in self._origin_patterns:
            if pattern.match(origin):
                return True
        return False
    
    def is_origin_allowed(self, origin: Optional[str]) -> bool:
        """Check if origin is allowed for WebSocket connections with security validation.
        
        Args:
            origin: The origin header value
            
        Returns:
            True if origin is allowed, False otherwise
        """
        # TESTING ENVIRONMENT: Allow connections without origin (e.g., TestClient)
        if not origin:
            if self.environment in ['development', 'testing']:
                logger.debug("WebSocket origin allowed: None (test environment bypass)")
                return True
            self._record_violation("", "WebSocket connection attempted without Origin header")
            return False
        
        # First check security constraints
        is_secure, security_reason = self._validate_origin_security(origin)
        if not is_secure:
            self._record_violation(origin, f"Security validation failed: {security_reason}")
            return False
        
        # Then check against allowed patterns
        if self._is_origin_explicitly_allowed(origin):
            logger.debug(f"WebSocket origin allowed: {origin}")
            return True
        
        # Record violation for denied origin
        self._record_violation(origin, "Origin not in allowed list")
        logger.warning(f"WebSocket origin denied: {origin}")
        return False
    
    def get_cors_headers(self, origin: str) -> dict:
        """Get CORS headers for WebSocket response with security enhancements.
        
        Args:
            origin: The origin to include in headers
            
        Returns:
            Dictionary of CORS headers with security headers
        """
        headers = {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Methods": "GET",
            "Access-Control-Allow-Headers": "Authorization, Content-Type, Origin, Accept, X-Request-ID, X-Trace-ID, X-Service-ID, X-Cross-Service-Auth",
            "Access-Control-Expose-Headers": "X-Trace-ID, X-Request-ID, X-Service-Name, X-Service-Version",
            "Vary": "Origin"
        }
        
        # Add security headers for production
        if self.environment == "production":
            headers.update({
                "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "DENY",
                "X-XSS-Protection": "1; mode=block",
                "Referrer-Policy": "strict-origin-when-cross-origin"
            })
        
        return headers
    
    def get_security_stats(self) -> dict:
        """Get security statistics for monitoring.
        
        Returns:
            Dictionary of security statistics
        """
        return {
            "violation_counts": dict(self._violation_counts),
            "blocked_origins": list(self._blocked_origins),
            "total_violations": sum(self._violation_counts.values()),
            "blocked_origin_count": len(self._blocked_origins),
            "environment": self.environment,
            "security_config": SECURITY_CONFIG.copy()
        }
    
    def unblock_origin(self, origin: str) -> bool:
        """Manually unblock an origin (for administrative purposes).
        
        Args:
            origin: Origin to unblock
            
        Returns:
            True if origin was blocked and is now unblocked, False otherwise
        """
        if origin in self._blocked_origins:
            self._blocked_origins.remove(origin)
            self._violation_counts.pop(origin, None)
            logger.info(f"Origin {origin} manually unblocked")
            return True
        return False


def validate_websocket_origin(websocket: WebSocket, cors_handler: WebSocketCORSHandler) -> bool:
    """Validate WebSocket connection origin.
    
    Args:
        websocket: The WebSocket connection
        cors_handler: CORS handler instance
        
    Returns:
        True if origin is valid, False otherwise
    """
    # Get origin from headers
    origin = websocket.headers.get("origin")
    if not origin:
        # Some clients might use "Origin" with capital O
        origin = websocket.headers.get("Origin")
    
    # Check if origin is allowed
    if not cors_handler.is_origin_allowed(origin):
        logger.error(f"WebSocket connection denied: invalid origin {origin}")
        return False
    
    logger.info(f"WebSocket connection allowed from origin: {origin}")
    return True


def get_environment_origins() -> List[str]:
    """Get allowed origins based on environment configuration and service discovery."""
    from netra_backend.app.core.configuration.base import get_unified_config
    config = get_unified_config()
    
    env = getattr(config, 'environment', 'development').lower()
    
    # Get CORS origins from unified config
    cors_origins = getattr(config, 'cors_origins', None)
    if cors_origins:
        # Handle both list and comma-separated string formats
        if isinstance(cors_origins, str):
            custom_list = [origin.strip() for origin in cors_origins.split(",") if origin.strip()]
        elif isinstance(cors_origins, list):
            custom_list = [str(origin).strip() for origin in cors_origins if origin]
        else:
            custom_list = []
    else:
        custom_list = []
    
    if env == "production":
        # Production environment: use production origins + custom
        allowed_origins = PRODUCTION_ORIGINS + custom_list
    elif env == "staging":
        # Staging environment: use staging + development origins + custom
        staging_origins = [origin for origin in PRODUCTION_ORIGINS if "staging" in origin]
        allowed_origins = staging_origins + DEFAULT_WEBSOCKET_ORIGINS + custom_list
    else:
        # Development/test environment: use development origins + custom + service discovery
        allowed_origins = DEFAULT_WEBSOCKET_ORIGINS + custom_list
        
        # Add service discovery origins if available
        try:
            from pathlib import Path
            from dev_launcher.service_discovery import ServiceDiscovery
            
            service_discovery = ServiceDiscovery(Path.cwd())
            discovered_origins = service_discovery.get_all_service_origins()
            allowed_origins.extend(discovered_origins)
            
            logger.debug(f"Added {len(discovered_origins)} service discovery origins for WebSocket CORS")
        except (ImportError, Exception) as e:
            logger.debug(f"Service discovery not available for WebSocket CORS: {e}")
    
    # Remove duplicates while preserving order
    unique_origins = []
    seen = set()
    for origin in allowed_origins:
        if origin and origin not in seen:
            unique_origins.append(origin)
            seen.add(origin)
    
    logger.info(f"WebSocket CORS configured for environment '{env}' with {len(unique_origins)} allowed origins")
    return unique_origins


class WebSocketCORSMiddleware:
    """ASGI middleware for WebSocket CORS handling."""
    
    def __init__(self, app: ASGIApp, cors_handler: Optional[WebSocketCORSHandler] = None):
        """Initialize WebSocket CORS middleware.
        
        Args:
            app: The ASGI application
            cors_handler: Optional CORS handler, creates default if None
        """
        self.app = app
        self.cors_handler = cors_handler or WebSocketCORSHandler(get_environment_origins())
    
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """ASGI middleware call.
        
        Args:
            scope: ASGI scope
            receive: ASGI receive callable
            send: ASGI send callable
        """
        if scope["type"] == "websocket":
            # Handle WebSocket CORS
            await self._handle_websocket_cors(scope, receive, send)
        else:
            # Pass through for non-WebSocket requests
            await self.app(scope, receive, send)
    
    async def _handle_websocket_cors(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Handle CORS for WebSocket connections.
        
        Args:
            scope: ASGI WebSocket scope
            receive: ASGI receive callable
            send: ASGI send callable
        """
        # Extract origin from headers
        headers = dict(scope.get("headers", []))
        origin = None
        
        for header_name, header_value in headers.items():
            if header_name.lower() == b"origin":
                origin = header_value.decode("latin1")
                break
        
        # Validate origin
        if not self.cors_handler.is_origin_allowed(origin):
            # Reject WebSocket connection
            await send({
                "type": "websocket.close",
                "code": 1008,  # Policy violation
                "reason": "Origin not allowed"
            })
            return
        
        # Add origin to scope for use by application
        scope["websocket_cors_origin"] = origin
        
        # Continue with the application
        await self.app(scope, receive, send)


# Global CORS handler instance
_global_cors_handler: Optional[WebSocketCORSHandler] = None


def get_websocket_cors_handler() -> WebSocketCORSHandler:
    """Get global WebSocket CORS handler instance."""
    global _global_cors_handler
    
    if _global_cors_handler is None:
        from netra_backend.app.core.configuration.base import get_unified_config
        config = get_unified_config()
        environment = getattr(config, 'environment', 'development').lower()
        _global_cors_handler = WebSocketCORSHandler(
            get_environment_origins(), 
            environment=environment
        )
    
    return _global_cors_handler


def configure_websocket_cors(app: ASGIApp) -> ASGIApp:
    """Configure WebSocket CORS for FastAPI application.
    
    Args:
        app: The FastAPI application
        
    Returns:
        App wrapped with WebSocket CORS middleware
    """
    cors_handler = get_websocket_cors_handler()
    logger.info(f"Configuring WebSocket CORS with {len(cors_handler.allowed_origins)} allowed origins")
    
    return WebSocketCORSMiddleware(app, cors_handler)


# Utility functions for route handlers
def check_websocket_cors(websocket: WebSocket) -> bool:
    """Quick CORS check for WebSocket route handlers.
    
    Args:
        websocket: The WebSocket connection
        
    Returns:
        True if CORS is valid, False otherwise
    """
    cors_handler = get_websocket_cors_handler()
    return validate_websocket_origin(websocket, cors_handler)


def get_websocket_cors_headers(websocket: WebSocket) -> dict:
    """Get CORS headers for WebSocket response.
    
    Args:
        websocket: The WebSocket connection
        
    Returns:
        Dictionary of CORS headers, empty if origin not allowed
    """
    cors_handler = get_websocket_cors_handler()
    origin = websocket.headers.get("origin") or websocket.headers.get("Origin")
    
    if origin and cors_handler.is_origin_allowed(origin):
        return cors_handler.get_cors_headers(origin)
    
    return {}