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
        """Get service with graceful fallback handling and comprehensive degradation logging."""
        service_info = self.services.get(name)
        if not service_info:
            if self.graceful_mode:
                logger.warning(f" ALERT:  SERVICE REGISTRY: Service '{name}' not registered "
                              f"(graceful_mode: enabled, "
                              f"action: returning_none, "
                              f"golden_path_impact: {self._assess_service_impact(name)}, "
                              f"recovery_action: Register service or check service name)")
                return None
            raise ValueError(f"Service '{name}' not found")
            
        if service_info['available']:
            logger.debug(f" PASS:  SERVICE AVAILABLE: Service '{name}' is healthy and available "
                        f"(service_status: available)")
            return service_info['service']
            
        # Service unavailable, try fallback
        if name in self.fallbacks:
            logger.warning(f"[U+1F527] GRACEFUL DEGRADATION: Using fallback for unavailable service '{name}' "
                          f"(service_status: unavailable, "
                          f"fallback_activated: true, "
                          f"golden_path_impact: {self._assess_service_impact(name)}, "
                          f"degraded_functionality: Service operates with limited features)")
            return self.fallbacks[name]
            
        if service_info['critical'] and not self.graceful_mode:
            logger.critical(f" ALERT:  CRITICAL SERVICE FAILURE: Critical service '{name}' is unavailable "
                           f"(critical: true, "
                           f"graceful_mode: disabled, "
                           f"fallback_available: false, "
                           f"golden_path_impact: CRITICAL - System cannot function properly, "
                           f"action: raising_exception)")
            raise RuntimeError(f"Critical service '{name}' is unavailable")
            
        logger.warning(f" WARNING: [U+FE0F] SERVICE DEGRADATION: Service '{name}' unavailable with no fallback "
                      f"(service_status: unavailable, "
                      f"fallback_available: false, "
                      f"graceful_mode: enabled, "
                      f"golden_path_impact: {self._assess_service_impact(name)}, "
                      f"action: returning_none)")
        return None
        
    def is_service_available(self, name: str) -> bool:
        """Check if service is available."""
        service_info = self.services.get(name)
        return service_info['available'] if service_info else False
        
    def mark_service_unavailable(self, name: str) -> None:
        """Mark service as unavailable with comprehensive circuit breaker logging."""
        if name in self.services:
            service_info = self.services[name]
            previous_status = service_info['available']
            self.services[name]['available'] = False
            
            # Log circuit breaker activation
            if previous_status:  # Service was previously available
                logger.critical(f" ALERT:  CIRCUIT BREAKER ACTIVATED: Service '{name}' marked as unavailable "
                               f"(previous_status: available, "
                               f"new_status: unavailable, "
                               f"critical: {service_info['critical']}, "
                               f"fallback_available: {service_info['fallback_available']}, "
                               f"golden_path_impact: {self._assess_service_impact(name)}, "
                               f"circuit_breaker_action: Service calls will be blocked or fallback activated)")
            else:
                logger.warning(f" WARNING: [U+FE0F] SERVICE STATUS UPDATE: Service '{name}' remains unavailable "
                              f"(status: already_unavailable, "
                              f"circuit_breaker_status: already_active)")
        else:
            logger.error(f" ALERT:  SERVICE REGISTRY ERROR: Cannot mark unknown service '{name}' as unavailable "
                        f"(action: service_not_registered, "
                        f"recovery_action: Register service before marking unavailable)")
    
    def _assess_service_impact(self, service_name: str) -> str:
        """Assess the impact of service unavailability on Golden Path functionality."""
        critical_services = {
            "auth_service": "CRITICAL - Authentication blocked", 
            "database": "CRITICAL - Data persistence blocked",
            "websocket_manager": "CRITICAL - Real-time communication blocked",
            "supervisor_service": "CRITICAL - AI responses blocked"
        }
        
        high_impact_services = {
            "redis": "HIGH - Caching and session management degraded",
            "thread_service": "HIGH - Conversation management limited",
            "message_service": "HIGH - Message persistence may fail"
        }
        
        if service_name in critical_services:
            return critical_services[service_name]
        elif service_name in high_impact_services:
            return high_impact_services[service_name]
        else:
            return "MEDIUM - Some functionality may be limited"


# Global service registry
service_registry = ServiceRegistry(graceful_mode=True)


def optional_service(service_name: str, fallback_result: Any = None):
    """Decorator for functions that depend on optional services."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            service = service_registry.get_service(service_name)
            if service is None:
                logger.warning(f"[U+1F527] GRACEFUL DEGRADATION: Service '{service_name}' unavailable, using fallback "
                              f"(function: {func.__name__}, "
                              f"fallback_type: {type(fallback_result).__name__}, "
                              f"degradation_mode: fallback_result)")
                return fallback_result
            try:
                result = await func(*args, **kwargs)
                logger.debug(f" PASS:  SERVICE OPERATION SUCCESS: Function '{func.__name__}' completed with service '{service_name}'")
                return result
            except Exception as e:
                logger.critical(f" ALERT:  SERVICE OPERATION FAILURE: Function '{func.__name__}' failed with service '{service_name}' "
                               f"(exception_type: {type(e).__name__}, "
                               f"exception_message: {str(e)}, "
                               f"circuit_breaker_action: Marking service unavailable, "
                               f"fallback_activated: true, "
                               f"golden_path_impact: {service_registry._assess_service_impact(service_name)})")
                service_registry.mark_service_unavailable(service_name)
                return fallback_result
                
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            service = service_registry.get_service(service_name)
            if service is None:
                logger.warning(f"[U+1F527] GRACEFUL DEGRADATION: Service '{service_name}' unavailable, using fallback "
                              f"(function: {func.__name__}, "
                              f"fallback_type: {type(fallback_result).__name__}, "
                              f"degradation_mode: fallback_result)")
                return fallback_result
            try:
                result = func(*args, **kwargs)
                logger.debug(f" PASS:  SERVICE OPERATION SUCCESS: Function '{func.__name__}' completed with service '{service_name}'")
                return result
            except Exception as e:
                logger.critical(f" ALERT:  SERVICE OPERATION FAILURE: Function '{func.__name__}' failed with service '{service_name}' "
                               f"(exception_type: {type(e).__name__}, "
                               f"exception_message: {str(e)}, "
                               f"circuit_breaker_action: Marking service unavailable, "
                               f"fallback_activated: true, "
                               f"golden_path_impact: {service_registry._assess_service_impact(service_name)})")
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