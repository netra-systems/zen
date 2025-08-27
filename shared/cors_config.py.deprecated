"""
Unified CORS Configuration Module for Netra Services.

This module provides a centralized CORS configuration system that can be used
by all services (netra_backend, auth_service, frontend) to ensure consistent
CORS handling across environments.

Business Value Justification (BVJ):
- Segment: ALL (Required for frontend-backend communication)
- Business Goal: Enable secure cross-origin requests while maintaining security
- Value Impact: Prevents CORS errors that block user interactions
- Strategic Impact: Foundation for microservice architecture communication
"""

import os
import re
from typing import Dict, List, Optional, Union
from urllib.parse import urlparse


def get_cors_origins(environment: Optional[str] = None) -> List[str]:
    """
    Get CORS origins based on environment configuration.
    
    Args:
        environment: Optional environment override. If None, detects from env vars.
    
    Returns:
        List of allowed CORS origins for the specified environment.
    """
    if environment is None:
        environment = _detect_environment()
    
    # Check for explicit CORS_ORIGINS environment variable first
    cors_origins_env = os.getenv("CORS_ORIGINS", "")
    if cors_origins_env:
        return _parse_cors_origins_env(cors_origins_env)
    
    # Fallback to environment-specific defaults
    if environment == "production":
        return _get_production_origins()
    elif environment == "staging":
        return _get_staging_origins()
    else:
        return _get_development_origins()


def get_cors_config(environment: Optional[str] = None) -> Dict[str, Union[List[str], bool, int]]:
    """
    Get complete CORS configuration compatible with FastAPI's CORSMiddleware.
    
    Args:
        environment: Optional environment override. If None, detects from env vars.
    
    Returns:
        Dictionary containing CORS configuration for FastAPI CORSMiddleware.
    """
    if environment is None:
        environment = _detect_environment()
    
    origins = get_cors_origins(environment)
    
    return {
        "allow_origins": origins,
        "allow_credentials": True,
        "allow_methods": [
            "GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH", "HEAD"
        ],
        "allow_headers": [
            "Authorization",
            "Content-Type", 
            "X-Request-ID",
            "X-Trace-ID",
            "Accept",
            "Origin",
            "Referer", 
            "X-Requested-With",
            "X-Service-Name"  # CORS-013: Service-to-service identification
        ],
        "expose_headers": [
            "X-Trace-ID",
            "X-Request-ID", 
            "Content-Length",
            "Content-Type",
            "Vary"  # CORS-005: Expose Vary header for CDN cache control
        ],
        "max_age": 3600  # CORS-006: Already implemented - 1 hour cache for preflight
    }


def _detect_environment() -> str:
    """
    Detect current environment from various environment variables.
    
    Returns:
        Environment name: 'development', 'staging', or 'production'
    """
    # Check various environment variable formats
    env_vars = [
        os.getenv("ENVIRONMENT", "").lower(),
        os.getenv("ENV", "").lower(), 
        os.getenv("NODE_ENV", "").lower(),
        os.getenv("NETRA_ENV", "").lower(),
        os.getenv("AUTH_ENV", "").lower()
    ]
    
    for env in env_vars:
        if env in ["production", "prod"]:
            return "production"
        elif env in ["staging", "stage", "stg"]:
            return "staging"
        elif env in ["development", "dev", "local"]:
            return "development"
    
    # Default to development if no environment is explicitly set
    return "development"


def _parse_cors_origins_env(cors_origins_env: str) -> List[str]:
    """
    Parse CORS_ORIGINS environment variable.
    
    Args:
        cors_origins_env: Raw CORS_ORIGINS environment variable value
        
    Returns:
        List of parsed CORS origins
    """
    if cors_origins_env.strip() == "*":
        # Wildcard - return development origins for maximum compatibility
        return _get_development_origins()
    
    # Parse comma-separated origins
    origins = [origin.strip() for origin in cors_origins_env.split(",") if origin.strip()]
    return origins if origins else _get_development_origins()


def _get_production_origins() -> List[str]:
    """Get production CORS origins."""
    return [
        "https://netrasystems.ai",
        "https://www.netrasystems.ai",
        "https://app.netrasystems.ai",
        "https://api.netrasystems.ai",
        "https://auth.netrasystems.ai"
    ]


def _get_staging_origins() -> List[str]:
    """Get staging CORS origins."""
    return [
        # Staging domains
        "https://app.staging.netrasystems.ai",
        "https://auth.staging.netrasystems.ai", 
        "https://api.staging.netrasystems.ai",
        "https://backend.staging.netrasystems.ai",
        
        # Cloud Run patterns for staging
        "https://netra-frontend-701982941522.us-central1.run.app",
        "https://netra-backend-701982941522.us-central1.run.app",
        
        # Local development support for staging testing
        "http://localhost:3000",
        "http://localhost:3001", 
        "http://localhost:8000",
        "http://localhost:8080",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://127.0.0.1:8000",
        "http://127.0.0.1:8080"
    ]


def _get_development_origins() -> List[str]:
    """Get development CORS origins with support for dynamic ports and Docker networking."""
    # In development, return comprehensive list of localhost variations
    # We can't use wildcard "*" when credentials are included per CORS spec
    # This list covers all common development scenarios
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
        
        # Docker service names and internal networking
        "http://frontend:3000",  # Docker service name for frontend
        "http://backend:8000",   # Docker service name for backend
        "http://auth:8081",      # Docker service name for auth
        "http://netra-frontend:3000",   # Docker container name
        "http://netra-backend:8000",    # Docker container name  
        "http://netra-auth:8081",       # Docker container name
        
        # Docker bridge network IP ranges (common Docker defaults)
        "http://172.17.0.1:3000",
        "http://172.17.0.1:8000",
        "http://172.18.0.1:3000", 
        "http://172.18.0.1:8000",
        "http://172.19.0.1:3000",
        "http://172.19.0.1:8000",
        "http://172.20.0.1:3000",
        "http://172.20.0.1:8000",
        
        # IPv6 localhost
        "http://[::1]:3000",
        "http://[::1]:3001",
        "http://[::1]:8000",
        "http://[::1]:8080"
    ]


def is_origin_allowed(origin: str, allowed_origins: List[str], environment: Optional[str] = None, service_to_service: bool = False) -> bool:
    """
    Check if an origin is allowed based on the CORS configuration.
    
    Args:
        origin: The origin to check
        allowed_origins: List of allowed origins 
        environment: Optional environment for special rules
        service_to_service: If True, apply service-to-service bypass rules (CORS-013)
        
    Returns:
        True if origin is allowed, False otherwise
    """
    if not origin:
        return False
    
    # CORS-013: Service-to-service bypass - no CORS validation for internal calls
    if service_to_service:
        return True
    
    if environment is None:
        environment = _detect_environment()
    
    # Direct match
    if origin in allowed_origins:
        return True
    
    # In development, allow any localhost origin regardless of port
    if environment == "development" and _is_localhost_origin(origin):
        return True
    
    # Check for wildcard match
    if "*" in allowed_origins:
        return True
    
    # Pattern matching for staging Cloud Run URLs
    if environment == "staging" and _matches_staging_patterns(origin):
        return True
    
    return False


def _is_localhost_origin(origin: str) -> bool:
    """
    Check if origin is from localhost/127.0.0.1 with any port, or Docker service names.
    
    Args:
        origin: Origin to check
        
    Returns:
        True if origin is localhost-based or Docker service
    """
    try:
        parsed = urlparse(origin)
        # Include Docker service names and container names
        localhost_hosts = [
            "localhost", "127.0.0.1", "0.0.0.0", "::1", "[::1]",
            # Docker service names from docker-compose.dev.yml
            "frontend", "backend", "auth",
            # Docker container names
            "netra-frontend", "netra-backend", "netra-auth"
        ]
        
        # Check if hostname is in our allowed list
        if parsed.hostname in localhost_hosts:
            return True
        
        # Check for Docker bridge network IPs (172.x.x.x range)
        if parsed.hostname and parsed.hostname.startswith("172."):
            return True
            
        return False
    except Exception:
        # Fallback regex pattern matching
        localhost_pattern = r'^https?://(localhost|127\.0\.0\.1|0\.0\.0\.0|\[::1\]|frontend|backend|auth|netra-frontend|netra-backend|netra-auth|172\.\d+\.\d+\.\d+)(:\d+)?/?$'
        return bool(re.match(localhost_pattern, origin, re.IGNORECASE))


def _matches_staging_patterns(origin: str) -> bool:
    """
    Check if origin matches staging URL patterns.
    
    Args:
        origin: Origin to check
        
    Returns:
        True if origin matches staging patterns
    """
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


def get_websocket_cors_origins(environment: Optional[str] = None) -> List[str]:
    """
    Get CORS origins specifically for WebSocket connections.
    WebSocket CORS handling may differ from HTTP CORS.
    
    Args:
        environment: Optional environment override
        
    Returns:
        List of allowed WebSocket CORS origins
    """
    # For now, WebSocket uses the same origins as HTTP CORS
    # This function exists for future WebSocket-specific customization
    return get_cors_origins(environment)


def get_cors_health_info(environment: Optional[str] = None) -> Dict[str, Union[str, int, List[str]]]:
    """
    Get CORS health information for debugging and monitoring.
    
    Args:
        environment: Optional environment override
        
    Returns:
        Dictionary containing current CORS configuration for health checks
    """
    if environment is None:
        environment = _detect_environment()
    
    origins = get_cors_origins(environment)
    config = get_cors_config(environment)
    
    return {
        "environment": environment,
        "origins_count": len(origins),
        "origins": origins,
        "allow_credentials": config.get("allow_credentials", False),
        "methods": config.get("allow_methods", []),
        "headers_count": len(config.get("allow_headers", [])),
        "expose_headers": config.get("expose_headers", []),
        "max_age": config.get("max_age", 0),
        "cors_env_override": bool(os.getenv("CORS_ORIGINS", "")),
        "config_valid": validate_cors_config(config)
    }


def validate_content_type(content_type: str) -> bool:
    """
    Validate Content-Type header for security (CORS-012).
    
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
        'application/vnd.ms',  # Microsoft Office formats (could be malicious)
        'text/vbscript',  # VBScript
        'text/jscript',  # JScript
    ]
    
    # Allow standard types
    if normalized in allowed_types:
        return True
    
    # Reject suspicious patterns
    for pattern in suspicious_patterns:
        if pattern in normalized:
            return False
    
    # Allow other standard patterns
    if normalized.startswith(('text/', 'image/', 'font/')):
        return True
    
    # Log and reject unknown types as potentially suspicious
    return False


def is_service_to_service_request(request_headers: Dict[str, str]) -> bool:
    """
    Detect if request is service-to-service communication (CORS-013).
    
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


def validate_cors_config(config: Dict) -> bool:
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


# Convenience function for getting environment-aware CORS middleware config
def log_cors_security_event(event_type: str, origin: str, path: str, environment: str, 
                           request_id: str = None, additional_info: dict = None) -> None:
    """
    Log CORS security events for monitoring (SEC-002).
    
    Args:
        event_type: Type of security event (validation_failure, suspicious_content_type, etc.)
        origin: Origin that triggered the event
        path: Request path
        environment: Current environment
        request_id: Optional request ID for tracing
        additional_info: Additional context for the security event
    """
    import logging
    import json
    from datetime import datetime, UTC
    
    security_logger = logging.getLogger('netra.security.cors')
    
    event_data = {
        'timestamp': datetime.now(UTC).isoformat(),
        'event_type': event_type,
        'origin': origin,
        'path': path,
        'environment': environment,
        'service': 'cors-validation'
    }
    
    if request_id:
        event_data['request_id'] = request_id
    
    if additional_info:
        event_data.update(additional_info)
    
    # Log as structured JSON for security monitoring
    security_logger.warning(f"CORS_SECURITY_EVENT: {json.dumps(event_data)}")
    
    # Also log human-readable format for immediate debugging
    security_logger.warning(
        f"CORS Security Event: {event_type} from origin={origin} on path={path} "
        f"in {environment} environment{f' (request_id={request_id})' if request_id else ''}"
    )


# Static asset CORS configuration
def get_static_file_cors_headers() -> Dict[str, str]:
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


def get_cdn_cors_config(environment: Optional[str] = None) -> Dict[str, Union[List[str], bool, int]]:
    """
    Get CORS configuration for CDN-served static assets.
    
    Args:
        environment: Optional environment override
        
    Returns:
        CORS configuration for CDN static asset serving
    """
    base_config = get_cors_config(environment)
    
    # More permissive for static assets served via CDN
    cdn_config = base_config.copy()
    cdn_config.update({
        "allow_origins": ["*"],  # CDN assets can be more permissive
        "allow_credentials": False,  # No credentials needed for static assets
        "allow_methods": ["GET", "HEAD", "OPTIONS"],  # Only read operations
        "max_age": 86400  # Longer cache for static assets
    })
    
    return cdn_config


def get_fastapi_cors_config(environment: Optional[str] = None) -> Dict:
    """
    Get CORS configuration formatted for FastAPI's CORSMiddleware.
    Alias for get_cors_config() for clarity.
    
    Args:
        environment: Optional environment override
        
    Returns:
        CORS configuration dictionary for FastAPI
    """
    return get_cors_config(environment)