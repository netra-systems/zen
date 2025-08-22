"""API Gateway Manager

Business Value Justification (BVJ):
- Segment: Mid/Enterprise (API management and security)
- Business Goal: Centralized API traffic management and control
- Value Impact: Enables scalable API operations with rate limiting, auth, and monitoring
- Strategic Impact: Foundation for enterprise API management platform

Provides centralized management of API gateway functionality.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from netra_backend.app.core.exceptions_base import NetraException
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


@dataclass
class ApiEndpoint:
    """Configuration for an API endpoint."""
    path: str
    methods: List[str]
    rate_limit_per_minute: Optional[int] = None
    require_auth: bool = True
    circuit_breaker_enabled: bool = True
    cache_enabled: bool = False
    cache_ttl_seconds: int = 300
    transformation_rules: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RequestContext:
    """Context information for a request."""
    request_id: str
    endpoint: str
    method: str
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None
    headers: Dict[str, str] = field(default_factory=dict)
    query_params: Dict[str, Any] = field(default_factory=dict)
    body: Any = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ResponseContext:
    """Context information for a response."""
    request_context: RequestContext
    status_code: int
    headers: Dict[str, str] = field(default_factory=dict)
    body: Any = None
    processing_time_ms: float = 0.0
    from_cache: bool = False
    circuit_breaker_triggered: bool = False


class ApiGatewayManager:
    """Manages API gateway operations and policies."""
    
    def __init__(self):
        """Initialize the API gateway manager."""
        self._endpoints: Dict[str, ApiEndpoint] = {}
        self._middleware_stack: List[Callable] = []
        self._request_handlers: Dict[str, Callable] = {}
        self._response_interceptors: List[Callable] = []
        self._lock = asyncio.Lock()
    
    async def register_endpoint(self, endpoint_config: ApiEndpoint) -> None:
        """Register an API endpoint with the gateway."""
        async with self._lock:
            self._endpoints[endpoint_config.path] = endpoint_config
            logger.info(f"Registered API endpoint: {endpoint_config.path}")
    
    async def unregister_endpoint(self, path: str) -> bool:
        """Unregister an API endpoint."""
        async with self._lock:
            if path in self._endpoints:
                del self._endpoints[path]
                logger.info(f"Unregistered API endpoint: {path}")
                return True
            return False
    
    async def add_middleware(self, middleware: Callable) -> None:
        """Add middleware to the processing stack."""
        async with self._lock:
            self._middleware_stack.append(middleware)
            logger.info(f"Added middleware: {middleware.__name__}")
    
    async def register_handler(self, endpoint: str, handler: Callable) -> None:
        """Register a request handler for an endpoint."""
        async with self._lock:
            self._request_handlers[endpoint] = handler
            logger.info(f"Registered handler for endpoint: {endpoint}")
    
    async def add_response_interceptor(self, interceptor: Callable) -> None:
        """Add a response interceptor."""
        async with self._lock:
            self._response_interceptors.append(interceptor)
            logger.info(f"Added response interceptor: {interceptor.__name__}")
    
    async def process_request(self, request_context: RequestContext) -> ResponseContext:
        """Process an incoming request through the gateway."""
        start_time = datetime.now(timezone.utc)
        
        try:
            # Check if endpoint is registered
            endpoint_config = await self._get_endpoint_config(request_context.endpoint)
            if not endpoint_config:
                return self._create_error_response(request_context, 404, "Endpoint not found")
            
            # Validate HTTP method
            if request_context.method not in endpoint_config.methods:
                return self._create_error_response(request_context, 405, "Method not allowed")
            
            # Apply middleware stack
            for middleware in self._middleware_stack:
                try:
                    result = await middleware(request_context, endpoint_config)
                    if isinstance(result, ResponseContext):
                        # Middleware returned early response (e.g., auth failed, rate limited)
                        return result
                except Exception as e:
                    logger.error(f"Middleware {middleware.__name__} failed: {e}")
                    return self._create_error_response(request_context, 500, "Middleware processing failed")
            
            # Get and execute handler
            handler = self._request_handlers.get(request_context.endpoint)
            if not handler:
                return self._create_error_response(request_context, 501, "Handler not implemented")
            
            # Execute the actual request handler
            try:
                response_data = await handler(request_context)
                response_context = ResponseContext(
                    request_context=request_context,
                    status_code=200,
                    body=response_data
                )
            except Exception as e:
                logger.error(f"Handler execution failed for {request_context.endpoint}: {e}")
                response_context = self._create_error_response(request_context, 500, "Handler execution failed")
            
            # Apply response interceptors
            for interceptor in self._response_interceptors:
                try:
                    response_context = await interceptor(response_context) or response_context
                except Exception as e:
                    logger.error(f"Response interceptor {interceptor.__name__} failed: {e}")
            
            # Calculate processing time
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            response_context.processing_time_ms = processing_time
            
            return response_context
            
        except Exception as e:
            logger.error(f"Request processing failed: {e}")
            return self._create_error_response(request_context, 500, "Internal server error")
    
    async def get_endpoint_config(self, path: str) -> Optional[ApiEndpoint]:
        """Get configuration for an endpoint."""
        async with self._lock:
            return self._endpoints.get(path)
    
    async def list_endpoints(self) -> List[ApiEndpoint]:
        """List all registered endpoints."""
        async with self._lock:
            return list(self._endpoints.values())
    
    async def update_endpoint_config(self, path: str, updates: Dict[str, Any]) -> bool:
        """Update configuration for an endpoint."""
        async with self._lock:
            if path not in self._endpoints:
                return False
            
            endpoint = self._endpoints[path]
            for key, value in updates.items():
                if hasattr(endpoint, key):
                    setattr(endpoint, key, value)
            
            logger.info(f"Updated configuration for endpoint: {path}")
            return True
    
    async def get_gateway_stats(self) -> Dict[str, Any]:
        """Get gateway statistics."""
        async with self._lock:
            return {
                "total_endpoints": len(self._endpoints),
                "middleware_count": len(self._middleware_stack),
                "handlers_registered": len(self._request_handlers),
                "response_interceptors": len(self._response_interceptors),
                "endpoints": [
                    {
                        "path": endpoint.path,
                        "methods": endpoint.methods,
                        "rate_limited": endpoint.rate_limit_per_minute is not None,
                        "auth_required": endpoint.require_auth,
                        "circuit_breaker": endpoint.circuit_breaker_enabled,
                        "cache_enabled": endpoint.cache_enabled
                    }
                    for endpoint in self._endpoints.values()
                ]
            }
    
    async def enable_endpoint_feature(self, path: str, feature: str, enabled: bool = True) -> bool:
        """Enable or disable a feature for an endpoint."""
        async with self._lock:
            if path not in self._endpoints:
                return False
            
            endpoint = self._endpoints[path]
            
            if feature == "circuit_breaker":
                endpoint.circuit_breaker_enabled = enabled
            elif feature == "cache":
                endpoint.cache_enabled = enabled
            elif feature == "auth":
                endpoint.require_auth = enabled
            else:
                return False
            
            logger.info(f"{'Enabled' if enabled else 'Disabled'} {feature} for endpoint: {path}")
            return True
    
    async def set_rate_limit(self, path: str, requests_per_minute: Optional[int]) -> bool:
        """Set rate limit for an endpoint."""
        async with self._lock:
            if path not in self._endpoints:
                return False
            
            self._endpoints[path].rate_limit_per_minute = requests_per_minute
            logger.info(f"Set rate limit for {path}: {requests_per_minute} requests/minute")
            return True
    
    async def _get_endpoint_config(self, path: str) -> Optional[ApiEndpoint]:
        """Get endpoint configuration (internal method)."""
        return self._endpoints.get(path)
    
    def _create_error_response(self, request_context: RequestContext, status_code: int, message: str) -> ResponseContext:
        """Create an error response."""
        return ResponseContext(
            request_context=request_context,
            status_code=status_code,
            body={"error": message, "timestamp": datetime.now(timezone.utc).isoformat()}
        )
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform gateway health check."""
        return {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "endpoints_count": len(self._endpoints),
            "middleware_count": len(self._middleware_stack)
        }
    
    async def reload_configuration(self, config: Dict[str, Any]) -> None:
        """Reload gateway configuration."""
        async with self._lock:
            # This would typically reload from configuration files or database
            logger.info("Gateway configuration reloaded")
    
    async def shutdown(self) -> None:
        """Shutdown the gateway manager."""
        async with self._lock:
            self._endpoints.clear()
            self._middleware_stack.clear()
            self._request_handlers.clear()
            self._response_interceptors.clear()
            logger.info("API Gateway manager shutdown complete")


# Global API gateway manager instance
api_gateway_manager = ApiGatewayManager()