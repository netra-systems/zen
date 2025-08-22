"""Service resilience patterns implementing pragmatic rigor principles.

This module provides utilities for graceful service degradation, optional service
management, and resilient startup patterns following Postel's Law.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


class ServiceRegistry:
    """Registry for tracking service availability and providing fallbacks."""
    
    def __init__(self, graceful_mode: bool = True):
        self.services: Dict[str, Dict[str, Any]] = {}
        self.fallbacks: Dict[str, Callable] = {}
        self.graceful_mode = graceful_mode
        
    def register_service(self, name: str, service: Any, 
                        critical: bool = False, fallback: Optional[Callable] = None) -> None:
        """Register a service with optional fallback."""
        self.services[name] = {
            'service': service,
            'available': service is not None,
            'critical': critical,
            'fallback_available': fallback is not None
        }
        if fallback:
            self.fallbacks[name] = fallback
            
    def get_service(self, name: str) -> Any:
        """Get service with graceful fallback handling."""
        service_info = self.services.get(name)
        if not service_info:
            if self.graceful_mode:
                logger.warning(f"Service '{name}' not registered, returning None")
                return None
            raise ValueError(f"Service '{name}' not found")
            
        if service_info['available']:
            return service_info['service']
            
        # Service unavailable, try fallback
        if name in self.fallbacks:
            logger.info(f"Using fallback for unavailable service '{name}'")
            return self.fallbacks[name]
            
        if service_info['critical'] and not self.graceful_mode:
            raise RuntimeError(f"Critical service '{name}' is unavailable")
            
        logger.warning(f"Service '{name}' unavailable and no fallback, returning None")
        return None
        
    def is_service_available(self, name: str) -> bool:
        """Check if service is available."""
        service_info = self.services.get(name)
        return service_info['available'] if service_info else False
        
    def mark_service_unavailable(self, name: str) -> None:
        """Mark service as unavailable."""
        if name in self.services:
            self.services[name]['available'] = False
            logger.warning(f"Service '{name}' marked as unavailable")


# Global service registry
service_registry = ServiceRegistry(graceful_mode=True)


def optional_service(service_name: str, fallback_result: Any = None):
    """Decorator for functions that depend on optional services."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            service = service_registry.get_service(service_name)
            if service is None:
                logger.info(f"Service '{service_name}' unavailable, using fallback result")
                return fallback_result
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger.warning(f"Function {func.__name__} failed with service '{service_name}': {e}")
                service_registry.mark_service_unavailable(service_name)
                return fallback_result
                
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            service = service_registry.get_service(service_name)
            if service is None:
                logger.info(f"Service '{service_name}' unavailable, using fallback result")
                return fallback_result
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.warning(f"Function {func.__name__} failed with service '{service_name}': {e}")
                service_registry.mark_service_unavailable(service_name)
                return fallback_result
                
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator


def graceful_startup(critical_services: Optional[List[str]] = None):
    """Decorator for startup functions that should handle service failures gracefully."""
    critical_services = critical_services or []
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                # Check if any critical services are involved
                error_msg = str(e).lower()
                critical_failure = any(service.lower() in error_msg for service in critical_services)
                
                if critical_failure:
                    logger.error(f"Critical service failure in {func.__name__}: {e}")
                    raise
                else:
                    logger.warning(f"Non-critical failure in {func.__name__}, continuing: {e}")
                    return None
                    
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Check if any critical services are involved
                error_msg = str(e).lower()
                critical_failure = any(service.lower() in error_msg for service in critical_services)
                
                if critical_failure:
                    logger.error(f"Critical service failure in {func.__name__}: {e}")
                    raise
                else:
                    logger.warning(f"Non-critical failure in {func.__name__}, continuing: {e}")
                    return None
                    
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator


@asynccontextmanager
async def resilient_service_context(service_name: str, service_factory: Callable):
    """Context manager for resilient service initialization."""
    service = None
    try:
        logger.info(f"Initializing service '{service_name}'...")
        service = await service_factory() if asyncio.iscoroutinefunction(service_factory) else service_factory()
        service_registry.register_service(service_name, service)
        logger.info(f"Service '{service_name}' initialized successfully")
        yield service
    except Exception as e:
        logger.warning(f"Service '{service_name}' initialization failed: {e}")
        service_registry.register_service(service_name, None)
        yield None
    finally:
        if service and hasattr(service, 'close'):
            try:
                if asyncio.iscoroutinefunction(service.close):
                    await service.close()
                else:
                    service.close()
            except Exception as e:
                logger.warning(f"Error closing service '{service_name}': {e}")


class FallbackService:
    """Base class for fallback service implementations."""
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.logger = logging.getLogger(f"{__name__}.{service_name}")
        
    def log_fallback_usage(self, method_name: str) -> None:
        """Log when fallback is being used."""
        self.logger.info(f"Using fallback implementation for {self.service_name}.{method_name}")


class MockDatabaseService(FallbackService):
    """Mock database service for graceful degradation."""
    
    def __init__(self):
        super().__init__("database")
        self.data = {}
        
    async def query(self, sql: str, params: Optional[Dict] = None) -> List[Dict]:
        """Mock database query."""
        self.log_fallback_usage("query")
        return []
        
    async def execute(self, sql: str, params: Optional[Dict] = None) -> bool:
        """Mock database execute."""
        self.log_fallback_usage("execute")
        return True


class MockClickHouseService(FallbackService):
    """Mock ClickHouse service for graceful degradation."""
    
    def __init__(self):
        super().__init__("clickhouse")
        
    async def insert(self, table: str, data: List[Dict]) -> bool:
        """Mock ClickHouse insert."""
        self.log_fallback_usage("insert")
        return True
        
    async def query(self, sql: str) -> List[Dict]:
        """Mock ClickHouse query."""
        self.log_fallback_usage("query")
        return []


def setup_fallback_services() -> None:
    """Setup fallback services for graceful degradation."""
    service_registry.register_service(
        "database_fallback", 
        MockDatabaseService(), 
        fallback=MockDatabaseService
    )
    service_registry.register_service(
        "clickhouse_fallback", 
        MockClickHouseService(), 
        fallback=MockClickHouseService
    )
    logger.info("Fallback services registered")


def configure_resilient_validation(strict_mode: bool = False) -> Dict[str, Any]:
    """Configure validation settings for resilient operation."""
    return {
        'allow_unknown_types': not strict_mode,
        'graceful_mode': not strict_mode,
        'default_healthy': True,
        'duck_typing_enabled': not strict_mode,
        'flexible_field_matching': not strict_mode,
        'type_coercion_enabled': not strict_mode
    }


# Utility functions for pragmatic validation
def safe_get_attr(obj: Any, attr: str, default: Any = None) -> Any:
    """Safely get attribute with duck typing support."""
    try:
        return getattr(obj, attr, default)
    except (AttributeError, TypeError):
        return default


def safe_call_method(obj: Any, method: str, *args, **kwargs) -> Any:
    """Safely call method with graceful error handling."""
    try:
        method_obj = getattr(obj, method, None)
        if callable(method_obj):
            return method_obj(*args, **kwargs)
        return None
    except Exception as e:
        logger.warning(f"Safe method call failed for {method}: {e}")
        return None


def flexible_type_check(obj: Any, expected_attributes: List[str]) -> bool:
    """Check if object has expected interface (duck typing)."""
    return all(hasattr(obj, attr) for attr in expected_attributes)