"""
CORS Configuration Builder
Comprehensive class-based CORS configuration system following DatabaseURLBuilder pattern.
Provides organized, environment-aware CORS configuration management.

Business Value Justification (BVJ):
- Segment: ALL (Required for frontend-backend communication)
- Business Goal: Enable secure cross-origin requests while maintaining security
- Value Impact: Prevents CORS errors that block user interactions
- Strategic Impact: Foundation for microservice architecture communication
"""

import os
import re
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple, Union, Any
from urllib.parse import urlparse

from shared.config_builder_base import ConfigBuilderBase


class CORSEnvironment(Enum):
    """Environment types for CORS configuration."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


@dataclass
class CORSSecurityEvent:
    """Security event data for CORS monitoring."""
    event_type: str
    origin: str
    path: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    timestamp: Optional[str] = None
    environment: Optional[str] = None
    request_id: Optional[str] = None


class CORSConfigurationBuilder(ConfigBuilderBase):
    """
    Main CORS configuration builder following DatabaseURLBuilder pattern.
    
    Provides organized access to all CORS configurations:
    - origins.allowed
    - origins.is_allowed(origin)
    - headers.allowed_headers
    - security.validate_content_type(content_type)
    - service_detector.is_internal_request(headers)
    - fastapi.get_middleware_config()
    - health.get_debug_info()
    """
    
    def __init__(self, env_vars: Optional[Dict[str, Any]] = None):
        """Initialize with environment variables."""
        # Call parent constructor which handles environment detection
        super().__init__(env_vars)
        
        # Initialize sub-builders
        self.origins = self.OriginsBuilder(self)
        self.headers = self.HeadersBuilder(self)
        self.security = self.SecurityBuilder(self)
        self.service_detector = self.ServiceDetector(self)
        self.fastapi = self.FastAPIBuilder(self)
        self.health = self.HealthBuilder(self)
        self.websocket = self.WebSocketBuilder(self)
        self.static = self.StaticAssetsBuilder(self)
    
    class OriginsBuilder:
        """Manages allowed origins with environment-specific patterns."""
        
        def __init__(self, parent):
            self.parent = parent
            self._cached_origins = None
            self._cached_patterns = None
        
        @property
        def allowed(self) -> List[str]:
            """Get list of allowed origins for current environment."""
            if self._cached_origins is None:
                self._cached_origins = self._get_allowed_origins()
            return self._cached_origins
        
        @property
        def patterns(self) -> List[re.Pattern]:
            """Get compiled regex patterns for origin matching."""
            if self._cached_patterns is None:
                self._cached_patterns = self._compile_patterns()
            return self._cached_patterns
        
        def is_allowed(self, origin: str, service_to_service: bool = False) -> bool:
            """
            Check if origin is allowed based on environment rules.
            
            Args:
                origin: The origin to check
                service_to_service: If True, bypass CORS for internal services
                
            Returns:
                True if origin is allowed, False otherwise
            """
            if not origin:
                return False
            
            # Service-to-service bypass
            if service_to_service:
                return True
            
            # Direct match
            if origin in self.allowed:
                return True
            
            # In development, allow any localhost origin
            if self.parent.environment == "development" and self._is_localhost_origin(origin):
                return True
            
            # Check for wildcard match
            if "*" in self.allowed:
                return True
            
            # Pattern matching for staging Cloud Run URLs
            if self.parent.environment == "staging" and self._matches_staging_patterns(origin):
                return True
            
            return False
        
        def validate_origin_format(self, origin: str) -> Tuple[bool, Optional[str]]:
            """
            Validate origin format.
            
            Args:
                origin: Origin to validate
                
            Returns:
                Tuple of (is_valid, error_message)
            """
            if not origin:
                return False, "Origin cannot be empty"
            
            try:
                parsed = urlparse(origin)
                if not parsed.scheme:
                    return False, "Origin must include scheme (http:// or https://)"
                if parsed.scheme not in ['http', 'https']:
                    return False, f"Invalid scheme '{parsed.scheme}' - must be http or https"
                if not parsed.netloc:
                    return False, "Origin must include hostname"
                if parsed.path and parsed.path != '/':
                    return False, "Origin should not include path"
                return True, None
            except Exception as e:
                return False, f"Invalid origin format: {str(e)}"
        
        def _get_allowed_origins(self) -> List[str]:
            """Get environment-specific allowed origins."""
            # Check for explicit CORS_ORIGINS environment variable first
            cors_origins_env = self.parent.env.get("CORS_ORIGINS", "")
            if cors_origins_env:
                return self._parse_cors_origins_env(cors_origins_env)
            
            # Fallback to environment-specific defaults
            if self.parent.environment == "production":
                return self._get_production_origins()
            elif self.parent.environment == "staging":
                return self._get_staging_origins()
            else:
                return self._get_development_origins()
        
        def _parse_cors_origins_env(self, cors_origins_env: str) -> List[str]:
            """Parse CORS_ORIGINS environment variable."""
            if cors_origins_env.strip() == "*":
                # Wildcard - return as-is to allow validation to catch it
                return ["*"]
            
            # Parse comma-separated origins
            origins = [origin.strip() for origin in cors_origins_env.split(",") if origin.strip()]
            return origins if origins else self._get_development_origins()
        
        def _get_production_origins(self) -> List[str]:
            """Get production CORS origins."""
            return [
                "https://netrasystems.ai",
                "https://www.netrasystems.ai",
                "https://app.netrasystems.ai",
                "https://api.netrasystems.ai",
                "https://auth.netrasystems.ai"
            ]
        
        def _get_staging_origins(self) -> List[str]:
            """Get staging CORS origins."""
            return [
                # Staging domains - CRITICAL: Include all origins
                "https://staging.netrasystems.ai",  # CRITICAL: Base staging domain
                "https://app.staging.netrasystems.ai",  # Frontend app
                "https://auth.staging.netrasystems.ai",  # Auth service
                "https://api.staging.netrasystems.ai",  # API gateway
                "https://backend.staging.netrasystems.ai",  # Backend service
                
                # Cloud Run patterns for staging
                "https://netra-frontend-701982941522.us-central1.run.app",
                "https://netra-backend-701982941522.us-central1.run.app",
                
                # Local development support for staging testing
                "http://localhost:3000",
                "http://localhost:3001",
                "http://localhost:8000",
                "http://localhost:8080",
                "http://localhost:8081",  # Auth service local port
                "http://127.0.0.1:3000",
                "http://127.0.0.1:3001",
                "http://127.0.0.1:8000",
                "http://127.0.0.1:8080",
                "http://127.0.0.1:8081"  # Auth service local port
            ]
        
        def _get_development_origins(self) -> List[str]:
            """Get development CORS origins with comprehensive localhost support."""
            return [
                # Standard localhost ports
                "http://localhost:3000",
                "http://localhost:3001",
                "http://localhost:3002",
                "http://localhost:8000",
                "http://localhost:8080",
                "http://localhost:8081",
                "http://localhost:5173",  # Vite
                "http://localhost:4200",  # Angular
                
                # 127.0.0.1 variants
                "http://127.0.0.1:3000",
                "http://127.0.0.1:3001",
                "http://127.0.0.1:3002",
                "http://127.0.0.1:8000",
                "http://127.0.0.1:8080",
                "http://127.0.0.1:8081",
                "http://127.0.0.1:5173",
                "http://127.0.0.1:4200",
                
                # HTTPS variants for local cert testing
                "https://localhost:3000",
                "https://localhost:3001",
                "https://localhost:8000",
                "https://localhost:8080",
                "https://127.0.0.1:3000",
                "https://127.0.0.1:3001",
                "https://127.0.0.1:8000",
                "https://127.0.0.1:8080",
                
                # 0.0.0.0 for Docker/container scenarios
                "http://0.0.0.0:3000",
                "http://0.0.0.0:8000",
                "http://0.0.0.0:8080",
                
                # Docker service names
                "http://frontend:3000",
                "http://backend:8000",
                "http://auth:8081",
                "http://netra-frontend:3000",
                "http://netra-backend:8000",
                "http://netra-auth:8081",
                
                # Docker bridge network IP ranges
                "http://172.17.0.1:3000",
                "http://172.17.0.1:8000",
                "http://172.18.0.1:3000",
                "http://172.18.0.1:8000",
                
                # IPv6 localhost
                "http://[::1]:3000",
                "http://[::1]:3001",
                "http://[::1]:8000",
                "http://[::1]:8080"
            ]
        
        def _is_localhost_origin(self, origin: str) -> bool:
            """Check if origin is from localhost."""
            try:
                parsed = urlparse(origin)
                localhost_hosts = [
                    "localhost", "127.0.0.1", "0.0.0.0", "::1", "[::1]",
                    "frontend", "backend", "auth",
                    "netra-frontend", "netra-backend", "netra-auth"
                ]
                
                if parsed.hostname in localhost_hosts:
                    return True
                
                # Check for Docker bridge network IPs
                if parsed.hostname and parsed.hostname.startswith("172."):
                    return True
                
                return False
            except Exception:
                # Fallback regex pattern matching
                localhost_pattern = r'^https?://(localhost|127\.0\.0\.1|0\.0\.0\.0|\[::1\]|frontend|backend|auth|netra-frontend|netra-backend|netra-auth|172\.\d+\.\d+\.\d+)(:\d+)?/?$'
                return bool(re.match(localhost_pattern, origin, re.IGNORECASE))
        
        def _matches_staging_patterns(self, origin: str) -> bool:
            """Check if origin matches staging URL patterns."""
            staging_patterns = [
                # Staging subdomain patterns
                r'^https://[a-zA-Z0-9\-]+\.staging\.netrasystems\.ai$',
                
                # Cloud Run patterns
                r'^https://netra-(frontend|backend|auth)-[0-9]+\.(us-central1|europe-west1|asia-northeast1)\.run\.app$',
                r'^https://[a-zA-Z0-9\-]+(-[a-zA-Z0-9]+)*-[a-z]{2}\.a\.run\.app$'
            ]
            
            for pattern in staging_patterns:
                if re.match(pattern, origin, re.IGNORECASE):
                    return True
            
            return False
        
        def _compile_patterns(self) -> List[re.Pattern]:
            """Compile origin patterns for efficient matching."""
            patterns = []
            for origin in self.allowed:
                # Convert wildcard patterns to regex
                if "*" in origin:
                    pattern = origin.replace(".", r"\.").replace("*", ".*")
                    patterns.append(re.compile(f"^{pattern}$", re.IGNORECASE))
            return patterns
    
    class HeadersBuilder:
        """Manages CORS headers configuration."""
        
        def __init__(self, parent):
            self.parent = parent
        
        @property
        def allowed_headers(self) -> List[str]:
            """Headers that clients can send in requests."""
            return [
                "Authorization",
                "Content-Type",
                "X-Request-ID",
                "X-Trace-ID",
                "Accept",
                "Origin",
                "Referer",
                "X-Requested-With",
                "X-Service-Name"
            ]
        
        @property
        def exposed_headers(self) -> List[str]:
            """Headers exposed to client JavaScript."""
            return [
                "X-Trace-ID",
                "X-Request-ID",
                "Content-Length",
                "Content-Type",
                "Vary"
            ]
        
        @property
        def allowed_methods(self) -> List[str]:
            """HTTP methods allowed for CORS."""
            return ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH", "HEAD"]
        
        @property
        def max_age(self) -> int:
            """Preflight cache duration in seconds."""
            return 3600  # 1 hour
        
        def is_header_allowed(self, header: str) -> bool:
            """Check if header is in allowed list (case-insensitive)."""
            return header.lower() in [h.lower() for h in self.allowed_headers]
        
        def is_method_allowed(self, method: str) -> bool:
            """Check if method is in allowed list."""
            return method.upper() in self.allowed_methods
    
    class SecurityBuilder:
        """Handles security validation and logging."""
        
        def __init__(self, parent):
            self.parent = parent
            self.logger = logging.getLogger("netra.security.cors")
            self._security_events = []
        
        def validate_content_type(self, content_type: str) -> bool:
            """
            Validate Content-Type header for security.
            
            Args:
                content_type: Content-Type header value to validate
                
            Returns:
                True if Content-Type is acceptable, False if suspicious
            """
            if not content_type or not content_type.strip():
                return True  # No Content-Type or empty Content-Type is acceptable
            
            # Normalize content type (remove charset, boundary, etc.)
            normalized = content_type.lower().split(';')[0].strip()
            
            # List of allowed content types
            allowed_types = {
                'application/json',
                'application/x-www-form-urlencoded',
                'text/plain',
                'text/html',
                'text/css',
                'text/javascript',
                'application/javascript',
                'application/xml',
                'text/xml',
                'multipart/form-data',
                'application/octet-stream',
                'image/png',
                'image/jpeg',
                'image/gif',
                'image/svg+xml',
                'image/webp',
                'font/woff',
                'font/woff2',
                'application/font-woff',
                'application/font-woff2'
            }
            
            # Check for suspicious patterns
            suspicious_patterns = [
                'text/x-',  # Non-standard text types
                'application/x-msdownload',  # Executable download
                'application/x-ms',  # Microsoft specific
                'application/vnd.ms',  # Microsoft Office formats
                'text/vbscript',  # VBScript
                'text/jscript',  # JScript
            ]
            
            # Allow standard types
            if normalized in allowed_types:
                return True
            
            # Reject suspicious patterns
            for pattern in suspicious_patterns:
                if pattern in normalized:
                    self.log_security_event(
                        "suspicious_content_type",
                        origin="",
                        path="",
                        additional_info={"content_type": content_type}
                    )
                    return False
            
            # Allow other standard patterns
            if normalized.startswith(('text/', 'image/', 'font/')):
                return True
            
            # Log and reject unknown types
            self.log_security_event(
                "unknown_content_type",
                origin="",
                path="",
                additional_info={"content_type": content_type}
            )
            return False
        
        def log_security_event(self, event_type: str, origin: str, path: str,
                              request_id: str = None, additional_info: dict = None) -> None:
            """
            Log CORS security events for monitoring.
            
            Args:
                event_type: Type of security event
                origin: Origin that triggered the event
                path: Request path
                request_id: Optional request ID for tracing
                additional_info: Additional context for the security event
            """
            event = CORSSecurityEvent(
                event_type=event_type,
                origin=origin,
                path=path,
                details=additional_info or {},
                timestamp=datetime.now(timezone.utc).isoformat(),
                environment=self.parent.environment,
                request_id=request_id
            )
            
            # Add to in-memory events (bounded)
            self._security_events.append(event)
            if len(self._security_events) > 1000:
                self._security_events = self._security_events[-500:]
            
            # Log event
            event_data = {
                'timestamp': event.timestamp,
                'event_type': event.event_type,
                'origin': event.origin,
                'path': event.path,
                'environment': event.environment,
                'service': 'cors-validation'
            }
            
            if request_id:
                event_data['request_id'] = request_id
            
            if additional_info:
                event_data.update(additional_info)
            
            # Log as structured JSON for security monitoring
            import json
            self.logger.warning(f"CORS_SECURITY_EVENT: {json.dumps(event_data)}")
            
            # Also log human-readable format for immediate debugging
            self.logger.warning(
                f"CORS Security Event: {event_type} from origin={origin} on path={path} "
                f"in {self.parent.environment} environment{f' (request_id={request_id})' if request_id else ''}"
            )
        
        def get_security_events(self, limit: int = 100) -> List[CORSSecurityEvent]:
            """Get recent security events."""
            return self._security_events[-limit:]
        
        def clear_security_events(self) -> None:
            """Clear security events (for testing)."""
            self._security_events = []
    
    class ServiceDetector:
        """Detects and handles service-to-service communication."""
        
        def __init__(self, parent):
            self.parent = parent
        
        def is_internal_request(self, request_headers: Dict[str, str]) -> bool:
            """
            Detect if request is service-to-service communication.
            
            Args:
                request_headers: Dictionary of request headers
                
            Returns:
                True if request appears to be service-to-service
            """
            # Check for service identification header
            service_name = request_headers.get('x-service-name', '').lower()
            if service_name in ['auth-service', 'backend-service', 'frontend-service']:
                return True
            
            # Check for internal service user agents
            user_agent = request_headers.get('user-agent', '').lower()
            internal_agents = ['httpx/', 'aiohttp/', 'requests/', 'python-urllib3/']
            if any(agent in user_agent for agent in internal_agents):
                return True
            
            return False
        
        def should_bypass_cors(self, request_headers: Dict[str, str]) -> bool:
            """
            Determine if CORS should be bypassed for this request.
            
            Args:
                request_headers: Dictionary of request headers
                
            Returns:
                True if CORS should be bypassed
            """
            # Only bypass in non-production environments for internal services
            return (
                self.is_internal_request(request_headers) and
                self.parent.environment != "production"
            )
    
    class FastAPIBuilder:
        """Generates FastAPI-compatible CORS middleware configuration."""
        
        def __init__(self, parent):
            self.parent = parent
        
        def get_middleware_config(self) -> Dict[str, Union[List[str], bool, int]]:
            """
            Get complete CORS configuration compatible with FastAPI's CORSMiddleware.
            
            Returns:
                Dictionary containing CORS configuration for FastAPI CORSMiddleware
            """
            return {
                "allow_origins": self.parent.origins.allowed,
                "allow_credentials": True,
                "allow_methods": self.parent.headers.allowed_methods,
                "allow_headers": self.parent.headers.allowed_headers,
                "expose_headers": self.parent.headers.exposed_headers,
                "max_age": self.parent.headers.max_age
            }
        
        def get_middleware_kwargs(self) -> Dict[str, Any]:
            """
            Get keyword arguments for FastAPI CORSMiddleware instantiation.
            
            Returns:
                Dictionary of kwargs for CORSMiddleware
            """
            return self.get_middleware_config()
    
    class WebSocketBuilder:
        """Manages WebSocket-specific CORS configuration."""
        
        def __init__(self, parent):
            self.parent = parent
        
        @property
        def allowed_origins(self) -> List[str]:
            """
            Get CORS origins specifically for WebSocket connections.
            
            Returns:
                List of allowed WebSocket CORS origins
            """
            # For now, WebSocket uses the same origins as HTTP CORS
            # This method exists for future WebSocket-specific customization
            return self.parent.origins.allowed
        
        def is_origin_allowed(self, origin: str) -> bool:
            """Check if WebSocket origin is allowed."""
            return self.parent.origins.is_allowed(origin)
    
    class StaticAssetsBuilder:
        """Manages CORS configuration for static assets."""
        
        def __init__(self, parent):
            self.parent = parent
        
        def get_static_headers(self) -> Dict[str, str]:
            """
            Get CORS headers for static file serving (fonts, images, scripts).
            
            Returns:
                Dictionary of headers for static file responses
            """
            return {
                "Access-Control-Allow-Origin": "*",  # More permissive for static assets
                "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
                "Access-Control-Allow-Headers": "Accept, Accept-Encoding, Accept-Language, Cache-Control, User-Agent",
                "Access-Control-Max-Age": "86400",  # 24 hours cache for static assets
                "Vary": "Origin"
            }
        
        def get_cdn_config(self) -> Dict[str, Union[List[str], bool, int]]:
            """
            Get CORS configuration for CDN-served static assets.
            
            Returns:
                CORS configuration for CDN static asset serving
            """
            base_config = self.parent.fastapi.get_middleware_config()
            
            # More permissive for static assets served via CDN
            cdn_config = base_config.copy()
            cdn_config.update({
                "allow_origins": ["*"],  # CDN assets can be more permissive
                "allow_credentials": False,  # No credentials needed for static assets
                "allow_methods": ["GET", "HEAD", "OPTIONS"],  # Only read operations
                "max_age": 86400  # Longer cache for static assets
            })
            
            return cdn_config
    
    class HealthBuilder:
        """Provides health and debug information."""
        
        def __init__(self, parent):
            self.parent = parent
        
        def get_config_info(self) -> Dict[str, Union[str, int, List[str], bool]]:
            """
            Get CORS health information for debugging and monitoring.
            
            Returns:
                Dictionary containing current CORS configuration for health checks
            """
            origins = self.parent.origins.allowed
            config = self.parent.fastapi.get_middleware_config()
            
            return {
                "environment": self.parent.environment,
                "origins_count": len(origins),
                "origins": origins,
                "allow_credentials": config.get("allow_credentials", False),
                "methods": config.get("allow_methods", []),
                "headers_count": len(config.get("allow_headers", [])),
                "expose_headers": config.get("expose_headers", []),
                "max_age": config.get("max_age", 0),
                "cors_env_override": bool(self.parent.env.get("CORS_ORIGINS", "")),
                "config_valid": self.validate_config(config)
            }
        
        def validate_config(self, config: Dict) -> bool:
            """
            Validate a CORS configuration dictionary.
            
            Args:
                config: CORS configuration dictionary
                
            Returns:
                True if configuration is valid
            """
            required_keys = [
                "allow_origins", "allow_credentials", "allow_methods",
                "allow_headers", "expose_headers", "max_age"
            ]
            
            for key in required_keys:
                if key not in config:
                    return False
            
            # Validate types
            if not isinstance(config["allow_origins"], list):
                return False
            if not isinstance(config["allow_credentials"], bool):
                return False
            if not isinstance(config["allow_methods"], list):
                return False
            if not isinstance(config["allow_headers"], list):
                return False
            if not isinstance(config["expose_headers"], list):
                return False
            if not isinstance(config["max_age"], int):
                return False
            
            return True
        
        def get_debug_info(self) -> Dict[str, Any]:
            """
            Get detailed debug information about current configuration.
            
            Returns:
                Dictionary with comprehensive debug information
            """
            config = self.parent.fastapi.get_middleware_config()
            recent_events = self.parent.security.get_security_events(10)
            
            # Get common debug info from base class
            debug_info = self.parent.get_common_debug_info()
            
            # Add CORS-specific debug information
            debug_info.update({
                "configuration": {
                    "origins_count": len(self.parent.origins.allowed),
                    "allowed_methods": self.parent.headers.allowed_methods,
                    "allow_credentials": config.get("allow_credentials", False),
                    "max_age_seconds": self.parent.headers.max_age
                },
                "validation": {
                    "config_valid": self.validate_config(config),
                    "has_custom_origins": bool(self.parent.get_env_var("CORS_ORIGINS", ""))
                },
                "security": {
                    "recent_events_count": len(recent_events),
                    "recent_events": [
                        {
                            "type": event.event_type,
                            "origin": event.origin,
                            "timestamp": event.timestamp
                        }
                        for event in recent_events
                    ]
                },
                "sample_origins": self.parent.origins.allowed[:5] if self.parent.origins.allowed else []
            })
            
            return debug_info
    
    def validate(self) -> Tuple[bool, str]:
        """
        Validate CORS configuration for current environment.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        config = self.fastapi.get_middleware_config()
        
        # Check for required configuration keys
        if not self.health.validate_config(config):
            return False, "Invalid configuration structure"
        
        # Check for production security
        if self.is_production():
            if "*" in self.origins.allowed:
                return False, "Production environment should not allow all origins"
            if not config.get("allow_credentials", True):
                return False, "Production should allow credentials for authenticated requests"
        
        # Check for at least one allowed origin
        if not self.origins.allowed:
            return False, "No allowed origins configured"
        
        return True, ""
    
    def get_debug_info(self) -> Dict[str, Any]:
        """
        Get detailed debug information about current configuration.
        Implementation of abstract method from ConfigBuilderBase.
        
        Returns:
            Dictionary with comprehensive debug information
        """
        # Delegate to the health sub-builder for the detailed implementation
        return self.health.get_debug_info()
    
    def get_safe_log_message(self) -> str:
        """
        Get a safe log message with current configuration details.
        
        Returns:
            A formatted string safe for logging
        """
        origins_count = len(self.origins.allowed)
        sample_origins = self.origins.allowed[:3] if self.origins.allowed else []
        
        config_type = "Custom" if self.env.get("CORS_ORIGINS") else "Default"
        
        return (
            f"CORS Configuration ({self.environment}/{config_type}): "
            f"{origins_count} origins allowed, "
            f"samples: {', '.join(sample_origins)}"
        )


# ===== BACKWARD COMPATIBILITY FUNCTIONS =====
# These functions provide compatibility with existing code using the old API

def get_cors_origins(environment: Optional[str] = None) -> List[str]:
    """
    Get CORS origins based on environment configuration.
    Backward compatibility wrapper.
    """
    env_vars = {"ENVIRONMENT": environment} if environment else None
    cors = CORSConfigurationBuilder(env_vars)
    return cors.origins.allowed


def get_cors_config(environment: Optional[str] = None) -> Dict[str, Union[List[str], bool, int]]:
    """
    Get complete CORS configuration compatible with FastAPI's CORSMiddleware.
    Backward compatibility wrapper.
    """
    env_vars = {"ENVIRONMENT": environment} if environment else None
    cors = CORSConfigurationBuilder(env_vars)
    return cors.fastapi.get_middleware_config()


def is_origin_allowed(origin: str, allowed_origins: List[str], 
                      environment: Optional[str] = None, 
                      service_to_service: bool = False) -> bool:
    """
    Check if an origin is allowed based on the CORS configuration.
    Backward compatibility wrapper.
    """
    env_vars = {"ENVIRONMENT": environment} if environment else None
    cors = CORSConfigurationBuilder(env_vars)
    return cors.origins.is_allowed(origin, service_to_service)


def validate_content_type(content_type: str) -> bool:
    """
    Validate Content-Type header for security.
    Backward compatibility wrapper.
    """
    cors = CORSConfigurationBuilder()
    return cors.security.validate_content_type(content_type)


def is_service_to_service_request(request_headers: Dict[str, str]) -> bool:
    """
    Detect if request is service-to-service communication.
    Backward compatibility wrapper.
    """
    cors = CORSConfigurationBuilder()
    return cors.service_detector.is_internal_request(request_headers)


def get_cors_health_info(environment: Optional[str] = None) -> Dict[str, Union[str, int, List[str], bool]]:
    """
    Get CORS health information for debugging and monitoring.
    Backward compatibility wrapper.
    """
    env_vars = {"ENVIRONMENT": environment} if environment else None
    cors = CORSConfigurationBuilder(env_vars)
    return cors.health.get_config_info()


def get_websocket_cors_origins(environment: Optional[str] = None) -> List[str]:
    """
    Get CORS origins specifically for WebSocket connections.
    Backward compatibility wrapper.
    """
    env_vars = {"ENVIRONMENT": environment} if environment else None
    cors = CORSConfigurationBuilder(env_vars)
    return cors.websocket.allowed_origins


def get_static_file_cors_headers() -> Dict[str, str]:
    """
    Get CORS headers for static file serving.
    Backward compatibility wrapper.
    """
    cors = CORSConfigurationBuilder()
    return cors.static.get_static_headers()


def get_cdn_cors_config(environment: Optional[str] = None) -> Dict[str, Union[List[str], bool, int]]:
    """
    Get CORS configuration for CDN-served static assets.
    Backward compatibility wrapper.
    """
    env_vars = {"ENVIRONMENT": environment} if environment else None
    cors = CORSConfigurationBuilder(env_vars)
    return cors.static.get_cdn_config()


def get_fastapi_cors_config(environment: Optional[str] = None) -> Dict:
    """
    Get CORS configuration formatted for FastAPI's CORSMiddleware.
    Backward compatibility wrapper.
    """
    return get_cors_config(environment)


def log_cors_security_event(event_type: str, origin: str, path: str, environment: str,
                           request_id: str = None, additional_info: dict = None) -> None:
    """
    Log CORS security events for monitoring.
    Backward compatibility wrapper.
    """
    env_vars = {"ENVIRONMENT": environment} if environment else None
    cors = CORSConfigurationBuilder(env_vars)
    cors.security.log_security_event(event_type, origin, path, request_id, additional_info)


def validate_cors_config(config: Dict) -> bool:
    """
    Validate a CORS configuration dictionary.
    Backward compatibility wrapper.
    """
    cors = CORSConfigurationBuilder()
    return cors.health.validate_config(config)