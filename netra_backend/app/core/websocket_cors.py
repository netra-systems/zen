"""WebSocket CORS handling and security configuration.

This module provides CORS handling specifically for WebSocket connections,
which require special handling compared to regular HTTP CORS.
"""

import re
import time
from typing import List, Optional, Union

from fastapi import Request, WebSocket
from starlette.middleware.cors import CORSMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)

# WebSocket CORS now uses unified configuration from shared/cors_config_builder.py
# No need for separate WebSocket origin management

# Security configuration constants - more permissive in development
def get_security_config(environment: str = "development") -> dict:
    """Get security configuration based on environment."""
    if environment == "development":
        return {
            "max_origin_length": 253,  # Maximum valid domain length per RFC
            "require_https_production": False,  # No HTTPS requirement in dev
            "block_suspicious_patterns": False,  # Don't block patterns in dev
            "log_security_violations": True,  # Log but don't block
            "rate_limit_violations": False,  # No rate limiting in dev
        }
    elif environment == "staging":
        return {
            "max_origin_length": 253,
            "require_https_production": False,  # Allow HTTP in staging for testing
            "block_suspicious_patterns": True,
            "log_security_violations": True,
            "rate_limit_violations": True,
        }
    else:  # production
        return {
            "max_origin_length": 253,
            "require_https_production": True,
            "block_suspicious_patterns": True,
            "log_security_violations": True,
            "rate_limit_violations": True,
        }

SECURITY_CONFIG = get_security_config()  # Default for backward compatibility

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
    """Handle CORS for WebSocket connections with enhanced security using unified configuration."""
    
    def __init__(self, allowed_origins: Optional[List[str]] = None, 
                 environment: str = "development"):
        """Initialize WebSocket CORS handler.
        
        Args:
            allowed_origins: List of allowed origins for WebSocket connections.
                            If None, uses unified CORS configuration.
            environment: Current environment (development, staging, production)
        """
        if allowed_origins is None:
            from shared.cors_config_builder import CORSConfigurationBuilder
            cors = CORSConfigurationBuilder({"ENVIRONMENT": environment} if environment else None)
            allowed_origins = cors.websocket.allowed_origins
        
        self.allowed_origins = allowed_origins
        self.environment = environment
        self.security_config = get_security_config(environment)  # Environment-specific config
        self._origin_patterns = self._compile_origin_patterns()
        self._suspicious_patterns = self._compile_suspicious_patterns()
        self._violation_counts = {}  # Track violations per origin
        self._blocked_origins = set()  # Temporarily blocked origins
        
        # Clear any existing blocks in development
        if environment == "development":
            self._blocked_origins.clear()
            self._violation_counts.clear()
    
    def _compile_origin_patterns(self) -> List[re.Pattern]:
        """Compile origin patterns for efficient matching."""
        patterns = []
        for origin in self.allowed_origins:
            if '*' in origin:
                # Convert wildcard patterns to regex
                pattern = origin.replace('*', '.*')
                patterns.append(re.compile(f'^{pattern}/?$', re.IGNORECASE))
            else:
                # Exact match pattern - allow optional trailing slash
                patterns.append(re.compile(f'^{re.escape(origin)}/?$', re.IGNORECASE))
        
        return patterns
    
    def _compile_suspicious_patterns(self) -> List[re.Pattern]:
        """Compile suspicious origin patterns for security blocking."""
        patterns = []
        if self.security_config["block_suspicious_patterns"]:
            for pattern_str in SUSPICIOUS_PATTERNS:
                patterns.append(re.compile(pattern_str, re.IGNORECASE))
        return patterns
    
    def _is_suspicious_origin(self, origin: str) -> bool:
        """Check if origin matches suspicious patterns."""
        if not self.security_config["block_suspicious_patterns"]:
            return False
        
        # In development, be very permissive - almost nothing is "suspicious"
        if self.environment == "development":
            # Check if it's a localhost, Docker service, or bridge network IP
            import re
            localhost_docker_pattern = r'^https?://(127\.0\.0\.1|0\.0\.0\.0|\[::1\]|localhost|frontend|backend|auth|netra-frontend|netra-backend|netra-auth|172\.\d+\.\d+\.\d+)(:\d+)?(/.*)?$'
            if re.match(localhost_docker_pattern, origin, re.IGNORECASE):
                return False  # Never suspicious in development for local/Docker testing
        
        # In staging, allow localhost IP addresses for testing  
        if self.environment == "staging":
            # Check if it's a localhost IP
            import re
            localhost_ip_pattern = r'^https?://(127\.0\.0\.1|0\.0\.0\.0|\[::1\]|localhost)(:\d+)?(/.*)?$'
            if re.match(localhost_ip_pattern, origin, re.IGNORECASE):
                return False  # Not suspicious in staging for local testing
        
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
        if len(origin) > self.security_config["max_origin_length"]:
            return False, f"Origin too long ({len(origin)} > {self.security_config['max_origin_length']})"
        
        # Check if temporarily blocked
        if origin in self._blocked_origins:
            return False, "Origin temporarily blocked due to violations"
        
        # Production HTTPS requirement
        if (self.environment == "production" and 
            self.security_config["require_https_production"] and 
            not origin.startswith("https://")):
            return False, "HTTPS required in production"
        
        # Check suspicious patterns
        if self._is_suspicious_origin(origin):
            return False, "Origin matches suspicious pattern"
        
        return True, ""
    
    def _record_violation(self, origin: str, reason: str) -> None:
        """Record security violation for monitoring and rate limiting with enhanced logging."""
        if not self.security_config["log_security_violations"]:
            return
        
        # In development, just log without blocking
        if self.environment == "development":
            logger.info(f"WebSocket CORS info (dev mode): {reason} for origin '{origin}'")
            return
        
        # Track violation count
        if origin not in self._violation_counts:
            self._violation_counts[origin] = 0
        self._violation_counts[origin] += 1
        
        # Temporarily block origins with too many violations
        if (self.security_config["rate_limit_violations"] and 
            self._violation_counts[origin] >= 5):
            self._blocked_origins.add(origin)
            logger.warning(f"Origin {origin} temporarily blocked after {self._violation_counts[origin]} violations")
        
        # Enhanced security logging with structured data
        violation_details = {
            "event": "websocket_cors_violation",
            "origin": origin,
            "reason": reason,
            "environment": self.environment,
            "violation_count": self._violation_counts[origin],
            "total_allowed_origins": len(self.allowed_origins),
            "blocked": origin in self._blocked_origins,
            "timestamp": time.time()
        }
        
        # Log at appropriate level based on severity
        if "suspicious" in reason.lower() or "blocked" in reason.lower():
            logger.error(f"WebSocket CORS SECURITY ALERT: {reason} for origin '{origin}' in environment '{self.environment}' - Details: {violation_details}")
        else:
            logger.warning(f"WebSocket CORS security violation: {reason} for origin '{origin}' in environment '{self.environment}'")
        
        # Always log structured details for monitoring
        logger.info(f"CORS violation details: {violation_details}")
    
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
        # Handle None origin case (common for desktop/mobile apps)
        if not origin:
            if self.environment in ['development', 'testing']:
                logger.info("WebSocket connection allowed: None origin in development/testing mode (common for desktop/mobile apps)")
                return True
            else:
                logger.warning(f"WebSocket connection denied: None origin not allowed in {self.environment} environment")
                self._record_violation("", "WebSocket connection attempted without Origin header in non-development environment")
                return False
        
        # In development mode, be very permissive - allow almost everything
        if self.environment == "development":
            # Check if it's any localhost origin or Docker service
            from shared.cors_config_builder import CORSConfigurationBuilder
            cors = CORSConfigurationBuilder()
            if cors.origins._is_localhost_origin(origin):
                logger.debug(f"WebSocket origin allowed (dev localhost/Docker): {origin}")
                return True
            
            # In development, allow any origin that looks reasonable
            # This helps with Docker networking and development scenarios
            logger.info(f"WebSocket origin allowed (dev mode - permissive): {origin}")
            return True
        
        # First check security constraints for non-development environments
        is_secure, security_reason = self._validate_origin_security(origin)
        if not is_secure:
            self._record_violation(origin, f"Security validation failed: {security_reason}")
            logger.error(f"CORS ERROR: Security validation failed for '{origin}': {security_reason}")
            return False
        
        # Then check against allowed patterns
        explicitly_allowed = self._is_origin_explicitly_allowed(origin)
        if explicitly_allowed:
            # Log successful validation with details for monitoring
            logger.info(f"WebSocket origin ALLOWED: '{origin}' in environment '{self.environment}'")
            logger.debug(f"WebSocket origin validation details - Environment: '{self.environment}', Origin patterns matched: True")
            return True
        
        # Record violation for denied origin with enhanced context
        self._record_violation(origin, "Origin not in allowed list")
        
        # Log denial with helpful context for debugging
        sample_allowed = [o for o in self.allowed_origins[:3] if 'localhost' in o or 'staging' in o]
        logger.error(f"WebSocket origin DENIED: '{origin}' not in allowed list for environment '{self.environment}' (Sample allowed: {sample_allowed})")
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
            "security_config": self.security_config.copy()
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
    # Get origin from headers with robust extraction
    origin = _extract_origin_from_websocket(websocket)
    
    # Log origin details for debugging
    logger.debug(f"WebSocket connection attempt - Origin: {origin}, Environment: {cors_handler.environment}")
    
    # Check if origin is allowed
    if not cors_handler.is_origin_allowed(origin):
        logger.error(f"WebSocket connection denied: Origin '{origin}' not allowed in {cors_handler.environment} environment")
        return False
    
    logger.info(f"WebSocket connection allowed from origin: {origin} in {cors_handler.environment} environment")
    return True


def _extract_origin_from_websocket(websocket: WebSocket) -> Optional[str]:
    """Extract origin from WebSocket headers with resilient handling.
    
    Args:
        websocket: The WebSocket connection
        
    Returns:
        Origin value or None if not found
    """
    # Collect all origin-related headers (case-insensitive)
    origin_headers = []
    for header_name, header_value in websocket.headers.items():
        if header_name.lower() == "origin":
            origin_headers.append(header_value)
    
    # Handle multiple origin headers
    if len(origin_headers) > 1:
        # Check if they're all the same value
        unique_origins = set(origin_headers)
        if len(unique_origins) == 1:
            # All values are identical - use the first one
            logger.debug(f"Multiple identical origin headers found: {origin_headers[0]}")
            return origin_headers[0]
        else:
            # Different values - this is a potential security issue
            logger.warning(f"Multiple different origin headers found: {origin_headers}")
            # In development, use the first one but log the issue
            # In production, this should be more strict
            from netra_backend.app.config import get_config as get_unified_config
            try:
                config = get_unified_config()
                if getattr(config, 'environment', 'production').lower() == 'development':
                    logger.info(f"Development mode: Using first origin from multiple values: {origin_headers[0]}")
                    return origin_headers[0]
                else:
                    logger.error("Production mode: Rejecting request with multiple different origin headers")
                    return None
            except Exception:
                # Fallback to safe behavior
                logger.error("Cannot determine environment: Rejecting request with multiple different origin headers")
                return None
    elif len(origin_headers) == 1:
        return origin_headers[0]
    else:
        # No origin headers found
        return None


def get_environment_origins() -> List[str]:
    """Get allowed origins based on environment using unified CORS configuration."""
    try:
        from netra_backend.app.config import get_config as get_unified_config
        config = get_unified_config()
        env = getattr(config, 'environment', 'development').lower()
        logger.info(f"WebSocket CORS: Using config environment: '{env}'")
    except Exception as e:
        from shared.cors_config_builder import CORSConfigurationBuilder
        cors = CORSConfigurationBuilder()
        env = cors.environment
        logger.warning(f"WebSocket CORS: Config unavailable, using fallback environment: '{env}' (Error: {e})")
    
    return get_environment_origins_for_environment(env)


def get_environment_origins_for_environment(environment: str) -> List[str]:
    """Get allowed origins for specific environment.
    
    Args:
        environment: Target environment name
        
    Returns:
        List of allowed origins for the environment
    """
    from shared.cors_config_builder import CORSConfigurationBuilder
    
    cors = CORSConfigurationBuilder({"ENVIRONMENT": environment} if environment else None)
    origins = cors.websocket.allowed_origins
    logger.info(f"WebSocket CORS configured for environment '{environment}' with {len(origins)} allowed origins")
    
    # Add explicit logging for critical staging/production detection
    if environment in ['staging', 'production']:
        logger.info(f"WebSocket CORS: CRITICAL - Running in {environment.upper()} mode with restricted origins")
        staging_count = sum(1 for o in origins if 'staging' in o or 'run.app' in o)
        localhost_count = sum(1 for o in origins if 'localhost' in o or '127.0.0.1' in o)
        logger.info(f"WebSocket CORS: {environment} origins - staging/cloud: {staging_count}, localhost: {localhost_count}")
    elif environment == 'development':
        logger.info(f"WebSocket CORS: Running in DEVELOPMENT mode with permissive origins")
    
    return origins


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
        # Extract origin from headers with resilient handling
        origin = self._extract_origin_from_scope(scope)
        
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
    
    def _extract_origin_from_scope(self, scope: Scope) -> Optional[str]:
        """Extract origin from ASGI scope with resilient handling.
        
        Args:
            scope: ASGI WebSocket scope
            
        Returns:
            Origin value or None if not found
        """
        headers = dict(scope.get("headers", []))
        origin_headers = []
        
        # Collect all origin-related headers (case-insensitive)
        for header_name, header_value in headers.items():
            if header_name.lower() == b"origin":
                origin_headers.append(header_value.decode("latin1"))
        
        # Handle multiple origin headers (same logic as _extract_origin_from_websocket)
        if len(origin_headers) > 1:
            unique_origins = set(origin_headers)
            if len(unique_origins) == 1:
                logger.debug(f"Multiple identical origin headers in ASGI scope: {origin_headers[0]}")
                return origin_headers[0]
            else:
                logger.warning(f"Multiple different origin headers in ASGI scope: {origin_headers}")
                # In development, use first; in production, be strict
                if self.cors_handler.environment == "development":
                    logger.info(f"Development mode: Using first origin from ASGI scope: {origin_headers[0]}")
                    return origin_headers[0]
                else:
                    logger.error("Production mode: Rejecting ASGI request with multiple different origin headers")
                    return None
        elif len(origin_headers) == 1:
            return origin_headers[0]
        else:
            return None


# Global CORS handler instance
_global_cors_handler: Optional[WebSocketCORSHandler] = None


def get_websocket_cors_handler(environment: Optional[str] = None) -> WebSocketCORSHandler:
    """Get global WebSocket CORS handler instance with explicit environment detection.
    
    Args:
        environment: Optional explicit environment. If None, detects from config.
    """
    global _global_cors_handler
    
    # Detect environment with explicit logging
    if environment is None:
        try:
            from netra_backend.app.config import get_config as get_unified_config
            config = get_unified_config()
            environment = getattr(config, 'environment', 'development').lower()
            logger.info(f"WebSocket CORS: Detected environment from config: '{environment}'")
        except Exception as e:
            # Fallback to shared CORS config environment detection
            from shared.cors_config_builder import CORSConfigurationBuilder
            fallback_cors = CORSConfigurationBuilder()
            environment = fallback_cors.environment
            logger.warning(f"WebSocket CORS: Config unavailable, using fallback detection: '{environment}' (Error: {e})")
    else:
        logger.info(f"WebSocket CORS: Using explicit environment: '{environment}'")
    
    # Always recreate handler if environment is explicitly provided
    if environment and _global_cors_handler and _global_cors_handler.environment != environment:
        logger.info(f"WebSocket CORS: Environment changed from '{_global_cors_handler.environment}' to '{environment}', recreating handler")
        _global_cors_handler = None
    
    if _global_cors_handler is None:
        origins = get_environment_origins_for_environment(environment)
        logger.info(f"WebSocket CORS: Creating handler for environment '{environment}' with {len(origins)} origins")
        _global_cors_handler = WebSocketCORSHandler(origins, environment=environment)
        
        # Log some example origins for debugging (without exposing secrets)
        example_origins = [o for o in origins[:3] if 'localhost' in o or 'staging' in o]
        if example_origins:
            logger.debug(f"WebSocket CORS: Example allowed origins: {example_origins}")
    
    return _global_cors_handler


def configure_websocket_cors(app: ASGIApp, environment: Optional[str] = None) -> ASGIApp:
    """Configure WebSocket CORS for FastAPI application.
    
    Args:
        app: The FastAPI application
        environment: Optional explicit environment for CORS configuration
        
    Returns:
        App wrapped with WebSocket CORS middleware
    """
    cors_handler = get_websocket_cors_handler(environment=environment)
    logger.info(f"Configuring WebSocket CORS with {len(cors_handler.allowed_origins)} allowed origins for environment '{cors_handler.environment}'")
    
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
    origin = _extract_origin_from_websocket(websocket)
    
    if origin and cors_handler.is_origin_allowed(origin):
        return cors_handler.get_cors_headers(origin)
    
    return {}