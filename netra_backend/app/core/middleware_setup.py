"""
Middleware configuration module.
Handles CORS, session, and other middleware setup for FastAPI.
"""
import logging
import os
import re
from typing import Any, Callable, Dict, List, Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import RedirectResponse, Response

from netra_backend.app.core.configuration import get_configuration

logger = logging.getLogger(__name__)


def get_cors_origins() -> list[str]:
    """Get CORS origins based on environment."""
    config = get_configuration()
    if config.environment == "production":
        return _get_production_cors_origins()
    elif config.environment == "staging":
        return _get_staging_cors_origins()
    return _get_development_cors_origins()


def _get_production_cors_origins() -> list[str]:
    """Get CORS origins for production environment."""
    config = get_configuration()
    cors_origins = getattr(config, 'cors_origins', None)
    if cors_origins:
        return cors_origins if isinstance(cors_origins, list) else cors_origins.split(",")
    return ["https://netrasystems.ai"]


def _get_staging_cors_origins() -> list[str]:
    """Get CORS origins for staging environment."""
    config = get_configuration()
    cors_origins = getattr(config, 'cors_origins', None)
    if cors_origins:
        return cors_origins if isinstance(cors_origins, list) else cors_origins.split(",")
    return _get_default_staging_origins()

def _get_default_staging_origins() -> list[str]:
    """Get default staging CORS origins."""
    staging_domains = _get_staging_domains()
    cloud_run_origins = _get_cloud_run_origins()
    localhost_origins = _get_localhost_origins() 
    return staging_domains + cloud_run_origins + localhost_origins + ["*"]

def _get_staging_domains() -> list[str]:
    """Get staging domain origins."""
    return [
        "https://app.staging.netrasystems.ai",
        "https://auth.staging.netrasystems.ai",
        "https://api.staging.netrasystems.ai",
        "https://backend.staging.netrasystems.ai"
    ]

def _get_cloud_run_origins() -> list[str]:
    """Get Cloud Run origins."""
    return [
        "https://netra-frontend-701982941522.us-central1.run.app",
        "https://netra-backend-701982941522.us-central1.run.app"
    ]

def _get_localhost_origins() -> list[str]:
    """Get localhost origins - now supports dynamic ports with service discovery."""
    # Extended list to support more dynamic ports
    # Pattern matching in CustomCORSMiddleware handles truly dynamic ports
    origins = []
    hosts = ["http://localhost", "http://127.0.0.1"]
    # Common frontend ports (React, Vue, Vite, Angular, etc.)
    frontend_ports = [3000, 3001, 3002, 3003, 4000, 4001, 4200, 5173, 5174, 5175]
    # Common backend/service ports
    backend_ports = [8000, 8001, 8002, 8003, 8080, 8081, 8082, 8083, 5000, 5001]
    
    for host in hosts:
        for port in frontend_ports + backend_ports:
            origins.append(f"{host}:{port}")
    
    # Add service discovery origins if available
    try:
        from pathlib import Path
        from dev_launcher.service_discovery import ServiceDiscovery
        service_discovery = ServiceDiscovery(Path.cwd())
        discovered_origins = service_discovery.get_all_service_origins()
        origins.extend(discovered_origins)
    except (ImportError, Exception):
        # Service discovery not available or failed - continue with static list
        pass
    
    return list(set(origins))  # Remove duplicates


def _get_development_cors_origins() -> list[str]:
    """Get CORS origins for development environment."""
    config = get_configuration()
    cors_origins = getattr(config, 'cors_origins', None)
    if cors_origins:
        return _handle_dev_env_origins(cors_origins)
    return _get_default_dev_origins()

def _handle_dev_env_origins(cors_origins: any) -> list[str]:
    """Handle development environment origins from config."""
    if isinstance(cors_origins, list):
        return cors_origins
    if cors_origins == "*":
        return ["*"]
    return cors_origins.split(",") if isinstance(cors_origins, str) else ["*"]

def _get_default_dev_origins() -> list[str]:
    """Get default development origins - includes common dynamic ports and wildcard."""
    # Include common ports plus wildcard for maximum flexibility in development
    origins = _get_localhost_origins()  # Get all the common localhost ports
    origins.append("*")  # Add wildcard for complete flexibility
    return origins


def setup_cors_middleware(app: FastAPI) -> None:
    """Configure CORS middleware."""
    config = get_configuration()
    if config.environment in ["staging", "development"]:
        _setup_custom_cors_middleware(app)
    else:
        _setup_production_cors_middleware(app)

def _setup_custom_cors_middleware(app: FastAPI) -> None:
    """Setup custom CORS middleware for staging/development with service discovery integration."""
    # Only use ServiceDiscovery in local development, not in staging
    config = get_configuration()
    service_discovery = None
    if config.environment == "development":
        try:
            from pathlib import Path

            from dev_launcher.service_discovery import ServiceDiscovery
            # Initialize service discovery for CORS integration
            service_discovery = ServiceDiscovery(Path.cwd())
        except ImportError:
            # dev_launcher is not available (expected in non-dev environments)
            pass
    
    app.add_middleware(
        CustomCORSMiddleware,
        service_discovery=service_discovery,
        enable_metrics=True
    )

def _setup_production_cors_middleware(app: FastAPI) -> None:
    """Setup production CORS middleware."""
    allowed_origins = get_cors_origins()
    cors_config = _get_production_cors_config(allowed_origins)
    app.add_middleware(CORSMiddleware, **cors_config)

def _get_production_cors_config(allowed_origins: list[str]) -> dict:
    """Get production CORS configuration."""
    return {
        "allow_origins": allowed_origins,
        "allow_credentials": True,
        "allow_methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH", "HEAD"],
        "allow_headers": ["Authorization", "Content-Type", "X-Request-ID", "X-Trace-ID", "Accept", "Origin", "Referer", "X-Requested-With"],
        "expose_headers": ["X-Trace-ID", "X-Request-ID", "Content-Length", "Content-Type"]
    }


def should_add_cors_headers(response: Any) -> bool:
    """Check if CORS headers should be added to response."""
    config = get_configuration()
    return isinstance(response, RedirectResponse) and config.environment in ["development", "staging"]


def add_cors_headers_to_response(response: Any, origin: str) -> None:
    """Add CORS headers to response."""
    response.headers["Access-Control-Allow-Origin"] = origin
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD"
    response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type, X-Request-ID, X-Trace-ID, Accept, Origin, Referer, X-Requested-With"


def process_cors_if_needed(request: Request, response: Any) -> None:
    """Process CORS headers if needed."""
    if should_add_cors_headers(response):
        origin = request.headers.get("origin")
        if origin:
            add_cors_headers_to_response(response, origin)


def create_cors_redirect_middleware() -> Callable:
    """Create CORS redirect middleware."""
    async def cors_redirect_middleware(request: Request, call_next: Callable) -> Any:
        """Handle CORS for redirects (e.g., trailing slash redirects)."""
        response = await call_next(request)
        process_cors_if_needed(request, response)
        return response
    return cors_redirect_middleware


def is_origin_allowed(origin: str, allowed_origins: List[str]) -> bool:
    """Check if origin matches allowed patterns including wildcards."""
    if not origin:
        return False
    return _perform_origin_checks(origin, allowed_origins)

def _perform_origin_checks(origin: str, allowed_origins: List[str]) -> bool:
    """Perform all origin validation checks."""
    # Check pattern matches FIRST for development localhost origins
    # This allows any localhost port to be accepted in development
    if _check_pattern_matches(origin):
        return True
    if _check_direct_origin_match(origin, allowed_origins):
        return True
    if _check_wildcard_match(allowed_origins):
        return True
    return False


def _check_direct_origin_match(origin: str, allowed_origins: List[str]) -> bool:
    """Check if origin has direct match in allowed origins."""
    return origin in allowed_origins


def _check_wildcard_match(allowed_origins: List[str]) -> bool:
    """Check if wildcard allows all origins based on environment."""
    if "*" not in allowed_origins:
        return False
    return _evaluate_wildcard_environment()

def _evaluate_wildcard_environment() -> bool:
    """Evaluate if current environment allows wildcards."""
    config = get_configuration()
    if config.environment == "development":
        return True
    return config.environment not in ["staging"]


def _check_pattern_matches(origin: str) -> bool:
    """Check if origin matches environment-specific patterns."""
    config = get_configuration()
    # In development, always check localhost patterns
    if config.environment == "development":
        # Check localhost pattern first - this accepts ANY port
        if _check_localhost_pattern(origin):
            return True
    # For staging, check staging patterns
    if config.environment in ["staging", "development"]:
        return _evaluate_pattern_matches(origin)
    return False

def _evaluate_pattern_matches(origin: str) -> bool:
    """Evaluate all pattern matches for origin."""
    return (
        _check_staging_domain_pattern(origin) or
        _check_cloud_run_patterns(origin) or
        _check_localhost_pattern(origin)
    )


def _check_staging_domain_pattern(origin: str) -> bool:
    """Check if origin matches staging domain pattern."""
    staging_pattern = r'^https://[a-zA-Z0-9\-]+\.staging\.netrasystems\.ai$'
    return bool(re.match(staging_pattern, origin))


def _check_cloud_run_patterns(origin: str) -> bool:
    """Check if origin matches any Cloud Run URL pattern."""
    patterns = _get_cloud_run_patterns()
    return any(re.match(pattern, origin) for pattern in patterns)

def _get_cloud_run_patterns() -> list[str]:
    """Get Cloud Run URL patterns."""
    return [
        r'^https://[a-zA-Z0-9\-]+(-[a-zA-Z0-9]+)*-[a-z]{2}\.a\.run\.app$',
        r'^https://netra-(frontend|backend)-[a-zA-Z0-9\-]+\.(us-central1|europe-west1|asia-northeast1)\.run\.app$',
        r'^https://netra-frontend-[0-9]+\.(us-central1|europe-west1|asia-northeast1)\.run\.app$'
    ]


def _check_localhost_pattern(origin: str) -> bool:
    """Check if origin matches localhost pattern with any port."""
    # Accept any localhost or 127.0.0.1 origin with any port in development
    # Updated pattern to be more flexible with ports (including common dev ports)
    localhost_pattern = r'^https?://(localhost|127\.0\.0\.1|0\.0\.0\.0|\[::1\])(:\d+)?$'
    return bool(re.match(localhost_pattern, origin))


class CustomCORSMiddleware(BaseHTTPMiddleware):
    """Custom CORS middleware with wildcard subdomain support and enhanced cross-service integration."""
    
    def __init__(self, app, **kwargs):
        """Initialize CORS middleware with service discovery integration."""
        super().__init__(app)
        self._service_discovery = kwargs.get('service_discovery')
        self._metrics_enabled = kwargs.get('enable_metrics', True)
        self._cors_metrics = self._setup_metrics() if self._metrics_enabled else None
    
    def _setup_metrics(self) -> Optional[Dict]:
        """Setup CORS metrics tracking."""
        return {
            'requests_processed': 0,
            'cors_rejections': 0,
            'preflight_requests': 0,
            'origins_allowed': set(),
            'origins_rejected': set()
        }
    
    async def dispatch(self, request: Request, call_next):
        """Handle CORS with wildcard support and service discovery integration."""
        origin = request.headers.get("origin")
        
        # Update metrics
        if self._cors_metrics:
            self._cors_metrics['requests_processed'] += 1
            if request.method == "OPTIONS":
                self._cors_metrics['preflight_requests'] += 1
        
        response = await self._handle_request(request, call_next)
        await self._process_cors_response(response, origin, request)
        return response

    async def _handle_request(self, request: Request, call_next) -> Response:
        """Handle request and return response with enhanced preflight support."""
        if request.method == "OPTIONS":
            return await self._handle_preflight_request(request)
        return await call_next(request)
    
    async def _handle_preflight_request(self, request: Request) -> Response:
        """Handle preflight requests with service discovery awareness."""
        response = Response(status_code=200)
        origin = request.headers.get("origin")
        
        if origin and self._is_origin_allowed_with_discovery(origin):
            self._add_preflight_headers(response, origin)
            # Track successful preflight
            if self._cors_metrics:
                self._cors_metrics['origins_allowed'].add(origin)
        
        return response
    
    def _add_preflight_headers(self, response: Response, origin: str) -> None:
        """Add comprehensive preflight headers."""
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD"
        response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type, X-Request-ID, X-Trace-ID, Accept, Origin, Referer, X-Requested-With, X-Service-ID, X-Cross-Service-Auth"
        response.headers["Access-Control-Max-Age"] = "3600"
        response.headers["Vary"] = "Origin"

    async def _process_cors_response(self, response: Response, origin: Optional[str], request: Request) -> None:
        """Process CORS headers for response with enhanced validation."""
        if not origin:
            return
        
        if self._is_origin_allowed_with_discovery(origin):
            self._add_enhanced_cors_headers(response, origin, request)
            # Track successful CORS
            if self._cors_metrics:
                self._cors_metrics['origins_allowed'].add(origin)
        else:
            self._log_cors_rejection(origin, request)
            # Track rejection
            if self._cors_metrics:
                self._cors_metrics['cors_rejections'] += 1
                self._cors_metrics['origins_rejected'].add(origin)
    
    def _is_origin_allowed_with_discovery(self, origin: str) -> bool:
        """Check if origin is allowed with service discovery integration."""
        # In development, always allow localhost with any port
        config = get_configuration()
        if config.environment == "development" and self._is_localhost_origin(origin):
            return True
        
        allowed_origins = get_cors_origins()
        
        # Basic origin check
        if is_origin_allowed(origin, allowed_origins):
            return True
        
        # Service discovery integration - check registered services
        if self._service_discovery:
            return self._check_service_discovery_origins(origin)
        
        return False
    
    def _is_localhost_origin(self, origin: str) -> bool:
        """Check if origin is from localhost with any port."""
        if not origin:
            return False
        # Use the improved localhost pattern check
        return _check_localhost_pattern(origin)
    
    def _check_service_discovery_origins(self, origin: str) -> bool:
        """Check origins from service discovery registry."""
        try:
            # Check if origin matches any registered service
            backend_info = self._service_discovery.read_backend_info()
            frontend_info = self._service_discovery.read_frontend_info()
            auth_info = self._service_discovery.read_auth_info()
            
            service_origins = set()
            
            if backend_info:
                service_origins.add(backend_info.get('api_url', ''))
                # Add WebSocket URL as HTTP origin for CORS
                ws_url = backend_info.get('ws_url', '')
                if ws_url:
                    http_origin = ws_url.replace('ws://', 'http://').replace('wss://', 'https://')
                    # Extract just the origin part (protocol + host + port)
                    if '/' in http_origin.split('://')[1]:
                        http_origin = http_origin.split('/')[0] + '//' + http_origin.split('//')[1].split('/')[0]
                    service_origins.add(http_origin)
            
            if frontend_info:
                service_origins.add(frontend_info.get('url', ''))
            
            if auth_info:
                service_origins.add(auth_info.get('url', ''))
                if auth_info.get('api_url'):
                    service_origins.add(auth_info.get('api_url'))
            
            # Filter out empty strings
            service_origins = {origin for origin in service_origins if origin}
            
            if origin in service_origins:
                logger.debug(f"Origin {origin} matches service discovery registry")
                return True
                
            return False
        except Exception as e:
            logger.warning(f"Service discovery CORS check failed: {e}")
            return False

    def _add_enhanced_cors_headers(self, response: Response, origin: str, request: Request) -> None:
        """Add enhanced CORS headers with service metadata."""
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD"
        response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type, X-Request-ID, X-Trace-ID, Accept, Origin, Referer, X-Requested-With, X-Service-ID, X-Cross-Service-Auth"
        response.headers["Access-Control-Expose-Headers"] = "X-Trace-ID, X-Request-ID, Content-Length, Content-Type, X-Service-Response-Time"
        response.headers["Vary"] = "Origin"
        
        # Add service identification for cross-service requests
        if self._is_cross_service_request(request):
            response.headers["X-Service-ID"] = "netra-backend"
            response.headers["X-Cross-Service-Response"] = "true"

    def _is_cross_service_request(self, request: Request) -> bool:
        """Check if request is from another service."""
        service_id_header = request.headers.get("x-service-id")
        cross_service_auth = request.headers.get("x-cross-service-auth")
        return bool(service_id_header or cross_service_auth)

    def _log_cors_rejection(self, origin: str, request: Request) -> None:
        """Log CORS rejection with enhanced debugging info."""
        import logging
        logger = logging.getLogger(__name__)
        
        allowed_origins = get_cors_origins()
        user_agent = request.headers.get("user-agent", "unknown")
        request_id = request.headers.get("x-request-id", "no-id")
        
        logger.warning(
            f"CORS rejection: origin={origin}, user_agent={user_agent[:50]}, "
            f"request_id={request_id}, allowed_origins={len(allowed_origins)} entries"
        )
        
        # In development, log more details
        config = get_configuration()
        if config.environment == "development":
            logger.debug(f"CORS: Detailed rejection - Origin {origin} not in {allowed_origins}")
    
    def get_cors_metrics(self) -> Optional[Dict]:
        """Get CORS metrics for monitoring."""
        if not self._cors_metrics:
            return None
        
        # Convert sets to lists for JSON serialization
        return {
            **self._cors_metrics,
            'origins_allowed': list(self._cors_metrics['origins_allowed']),
            'origins_rejected': list(self._cors_metrics['origins_rejected'])
        }


def setup_session_middleware(app: FastAPI) -> None:
    """Setup session middleware."""
    from netra_backend.app.clients.auth_client import auth_client
    current_environment = auth_client.detect_environment()
    session_config = _determine_session_config(current_environment)
    _log_session_config(session_config, current_environment)
    _add_session_middleware(app, session_config)

def _determine_session_config(current_environment) -> dict:
    """Determine session configuration based on environment."""
    is_deployed = current_environment.value in ["production", "staging"]
    is_localhost = _check_localhost_environment()
    return _create_session_config(is_localhost, is_deployed)

def _check_localhost_environment() -> bool:
    """Check if running in localhost environment."""
    config = get_configuration()
    return any([
        "localhost" in config.frontend_url,
        "localhost" in config.api_base_url,
        config.environment == "development",
    ])

def _create_session_config(is_localhost: bool, is_deployed: bool) -> dict:
    """Create session configuration dictionary."""
    config = get_configuration()
    disable_https = getattr(config, 'disable_https_only', False)
    if is_localhost or disable_https:
        return {"same_site": "lax", "https_only": False}
    return {
        "same_site": "none" if is_deployed else "lax",
        "https_only": is_deployed
    }

def _log_session_config(session_config: dict, current_environment) -> None:
    """Log session configuration for debugging."""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(
        f"Session middleware config: same_site={session_config['same_site']}, "
        f"https_only={session_config['https_only']}, environment={current_environment.value}"
    )

def _add_session_middleware(app: FastAPI, session_config: dict) -> None:
    """Add session middleware to app."""
    config = get_configuration()
    app.add_middleware(
        SessionMiddleware,
        secret_key=config.secret_key,
        same_site=session_config["same_site"],
        https_only=session_config["https_only"],
        max_age=3600,  # 1 hour session
    )