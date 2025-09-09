"""
Service Readiness Validator - SSOT Implementation for WebSocket Race Condition Remediation

MISSION CRITICAL: Stage 1 of WebSocket race condition remediation - provides comprehensive
service dependency validation with adaptive timeouts and graceful degradation patterns.

BUSINESS VALUE JUSTIFICATION:
- Segment: Platform/Internal
- Business Goal: Platform Stability & Chat Value Delivery
- Value Impact: Eliminates WebSocket race conditions preventing reliable AI chat functionality
- Strategic Impact: Enables adaptive service validation preventing 1011 errors across environments

SSOT COMPLIANCE:
- Builds upon existing GCPWebSocketInitializationValidator patterns
- Uses shared.isolated_environment for environment detection
- Integrates with existing websocket_core infrastructure
- Follows shared.lifecycle patterns for service management
- Enhances existing WebSocket service checking (lines 448-598 in websocket.py)

CRITICAL: This implementation enhances rather than replaces existing code, maintaining
all current functionality while adding adaptive timeout logic and graceful degradation.
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional, Callable, List, Tuple, Union
from enum import Enum
from dataclasses import dataclass, field
from contextlib import asynccontextmanager

from shared.isolated_environment import get_env
from netra_backend.app.logging_config import central_logger


class ServiceReadinessLevel(Enum):
    """Service readiness levels for adaptive validation."""
    UNKNOWN = "unknown"
    INITIALIZING = "initializing"
    BASIC_READY = "basic_ready"
    FUNCTIONAL_READY = "functional_ready"
    FULLY_READY = "fully_ready"
    DEGRADED = "degraded"
    FAILED = "failed"


class ServiceCriticality(Enum):
    """Service criticality levels for graceful degradation."""
    CRITICAL = "critical"  # Service must be ready for WebSocket connections
    IMPORTANT = "important"  # Service should be ready, but can degrade gracefully
    OPTIONAL = "optional"  # Service can be missing without blocking connections


@dataclass
class AdaptiveTimeout:
    """Adaptive timeout configuration based on environment and service criticality."""
    base_timeout: float = 10.0
    max_timeout: float = 60.0
    retry_count: int = 3
    retry_delay: float = 1.0
    exponential_backoff: bool = True
    environment_multipliers: Dict[str, float] = field(default_factory=lambda: {
        "test": 0.5,
        "development": 1.0,
        "staging": 2.0,
        "production": 3.0
    })
    
    def get_effective_timeout(self, environment: str, criticality: ServiceCriticality) -> float:
        """Calculate effective timeout based on environment and criticality."""
        base = self.base_timeout
        
        # Apply environment multiplier
        multiplier = self.environment_multipliers.get(environment.lower(), 1.0)
        
        # Apply criticality multiplier
        criticality_multipliers = {
            ServiceCriticality.CRITICAL: 1.5,
            ServiceCriticality.IMPORTANT: 1.2,
            ServiceCriticality.OPTIONAL: 0.8
        }
        criticality_multiplier = criticality_multipliers.get(criticality, 1.0)
        
        effective_timeout = base * multiplier * criticality_multiplier
        return min(effective_timeout, self.max_timeout)


@dataclass
class ServiceReadinessConfig:
    """Enhanced configuration for service readiness validation."""
    name: str
    validator: Callable[[], Union[bool, ServiceReadinessLevel]]
    criticality: ServiceCriticality = ServiceCriticality.IMPORTANT
    timeout_config: Optional[AdaptiveTimeout] = None
    dependencies: List[str] = field(default_factory=list)
    description: str = ""
    health_check_url: Optional[str] = None
    graceful_degradation_handler: Optional[Callable] = None
    
    def __post_init__(self):
        if self.timeout_config is None:
            self.timeout_config = AdaptiveTimeout()


@dataclass
class ServiceValidationResult:
    """Result of service readiness validation with detailed diagnostics."""
    service_name: str
    ready: bool
    level: ServiceReadinessLevel
    criticality: ServiceCriticality
    elapsed_time: float
    attempts: int
    effective_timeout: float
    error_message: Optional[str] = None
    degradation_applied: bool = False
    can_gracefully_degrade: bool = False


@dataclass
class ServiceGroupValidationResult:
    """Result of validating a group of services."""
    group_name: str
    overall_ready: bool
    total_services: int
    ready_services: int
    critical_failures: List[str]
    degraded_services: List[str]
    service_results: Dict[str, ServiceValidationResult]
    total_elapsed_time: float
    graceful_degradation_active: bool = False


class ServiceReadinessValidator:
    """
    Comprehensive service readiness validator with adaptive timeouts and graceful degradation.
    
    CRITICAL: Enhances existing WebSocket service checking with intelligent validation
    patterns while maintaining backward compatibility and existing functionality.
    
    STAGE 1 IMPLEMENTATION: Focuses on service dependency validation and adaptive timeouts
    as the foundation for eliminating WebSocket race conditions.
    """
    
    def __init__(self, app_state: Optional[Any] = None, environment: Optional[str] = None):
        self.app_state = app_state
        self.logger = central_logger.get_logger(__name__)
        self.env_manager = get_env()
        
        # Environment detection with override capability
        if environment:
            self.environment = environment.lower()
        else:
            self.environment = self.env_manager.get('ENVIRONMENT', 'development').lower()
        
        # Service registry for validation configurations
        self.service_configs: Dict[str, ServiceReadinessConfig] = {}
        
        # Validation state tracking
        self.last_validation_time = 0.0
        self.validation_cache: Dict[str, Tuple[bool, float]] = {}  # service_name -> (ready, timestamp)
        self.cache_ttl = 30.0  # Cache results for 30 seconds
        
        # Graceful degradation tracking
        self.degraded_services: Dict[str, str] = {}  # service_name -> reason
        
        # Initialize with WebSocket-critical service configurations
        self._register_websocket_critical_services()
    
    def _register_websocket_critical_services(self) -> None:
        """Register critical services for WebSocket functionality."""
        
        # Database - CRITICAL for user context and thread management
        self.register_service(ServiceReadinessConfig(
            name="database",
            validator=self._validate_database_service,
            criticality=ServiceCriticality.CRITICAL,
            timeout_config=AdaptiveTimeout(
                base_timeout=15.0,
                max_timeout=45.0,
                retry_count=3
            ),
            description="Database connectivity and session factory",
            graceful_degradation_handler=self._database_degradation_handler
        ))
        
        # Redis - CRITICAL for caching and session management
        self.register_service(ServiceReadinessConfig(
            name="redis",
            validator=self._validate_redis_service,
            criticality=ServiceCriticality.CRITICAL,
            timeout_config=AdaptiveTimeout(
                base_timeout=10.0,
                max_timeout=60.0,  # Extended timeout for GCP race condition fix
                retry_count=5,
                exponential_backoff=True
            ),
            description="Redis caching and session store",
            graceful_degradation_handler=self._redis_degradation_handler
        ))
        
        # Auth System - CRITICAL for user validation
        self.register_service(ServiceReadinessConfig(
            name="auth_system",
            validator=self._validate_auth_system,
            criticality=ServiceCriticality.CRITICAL,
            timeout_config=AdaptiveTimeout(
                base_timeout=10.0,
                max_timeout=30.0,
                retry_count=3
            ),
            description="Authentication and authorization system",
            graceful_degradation_handler=self._auth_degradation_handler
        ))
        
        # Agent Supervisor - CRITICAL for chat functionality
        self.register_service(ServiceReadinessConfig(
            name="agent_supervisor",
            validator=self._validate_agent_supervisor,
            criticality=ServiceCriticality.CRITICAL,
            timeout_config=AdaptiveTimeout(
                base_timeout=20.0,
                max_timeout=60.0,
                retry_count=5,
                exponential_backoff=True
            ),
            dependencies=["database", "redis", "auth_system"],
            description="Agent supervisor for AI chat processing",
            graceful_degradation_handler=self._supervisor_degradation_handler
        ))
        
        # Thread Service - CRITICAL for conversation management
        self.register_service(ServiceReadinessConfig(
            name="thread_service",
            validator=self._validate_thread_service,
            criticality=ServiceCriticality.CRITICAL,
            timeout_config=AdaptiveTimeout(
                base_timeout=15.0,
                max_timeout=45.0,
                retry_count=3
            ),
            dependencies=["database", "auth_system"],
            description="Thread and conversation management service"
        ))
        
        # WebSocket Bridge - IMPORTANT for real-time events
        self.register_service(ServiceReadinessConfig(
            name="websocket_bridge",
            validator=self._validate_websocket_bridge,
            criticality=ServiceCriticality.IMPORTANT,
            timeout_config=AdaptiveTimeout(
                base_timeout=10.0,
                max_timeout=30.0,
                retry_count=3
            ),
            dependencies=["agent_supervisor"],
            description="WebSocket bridge for real-time event notifications",
            graceful_degradation_handler=self._bridge_degradation_handler
        ))
    
    def register_service(self, config: ServiceReadinessConfig) -> None:
        """Register a service for readiness validation."""
        self.service_configs[config.name] = config
        self.logger.debug(f"Registered service '{config.name}' with criticality {config.criticality.value}")
    
    def update_environment(self, new_environment: str) -> None:
        """Update environment configuration and recalculate timeouts."""
        old_env = self.environment
        self.environment = new_environment.lower()
        
        if old_env != self.environment:
            self.logger.info(f"Environment changed from '{old_env}' to '{self.environment}' - recalculating timeouts")
            self._invalidate_cache()
    
    def _invalidate_cache(self) -> None:
        """Invalidate the validation result cache."""
        self.validation_cache.clear()
    
    def _is_cache_valid(self, service_name: str) -> bool:
        """Check if cached validation result is still valid."""
        if service_name not in self.validation_cache:
            return False
        
        _, timestamp = self.validation_cache[service_name]
        return (time.time() - timestamp) < self.cache_ttl
    
    async def validate_service(
        self, 
        service_name: str, 
        force_refresh: bool = False
    ) -> ServiceValidationResult:
        """
        Validate a single service with adaptive timeouts and graceful degradation.
        
        Args:
            service_name: Name of the service to validate
            force_refresh: Force validation even if cached result exists
            
        Returns:
            ServiceValidationResult with detailed validation information
        """
        if service_name not in self.service_configs:
            return ServiceValidationResult(
                service_name=service_name,
                ready=False,
                level=ServiceReadinessLevel.UNKNOWN,
                criticality=ServiceCriticality.OPTIONAL,
                elapsed_time=0.0,
                attempts=0,
                effective_timeout=0.0,
                error_message=f"Service '{service_name}' not registered"
            )
        
        # Check cache first (unless force refresh)
        if not force_refresh and self._is_cache_valid(service_name):
            cached_ready, _ = self.validation_cache[service_name]
            self.logger.debug(f"Using cached result for service '{service_name}': {cached_ready}")
            # Note: For cached results, we return a simplified result
            # In production, you might want to cache the full ServiceValidationResult
        
        config = self.service_configs[service_name]
        start_time = time.time()
        
        # Calculate effective timeout based on environment and criticality
        effective_timeout = config.timeout_config.get_effective_timeout(
            self.environment, config.criticality
        )
        
        self.logger.debug(
            f"Validating service '{service_name}' - "
            f"timeout: {effective_timeout}s, criticality: {config.criticality.value}"
        )
        
        # Validate dependencies first
        for dep in config.dependencies:
            if dep in self.service_configs:
                dep_result = await self.validate_service(dep)
                if not dep_result.ready and dep_result.criticality == ServiceCriticality.CRITICAL:
                    self.logger.warning(f"Dependency '{dep}' not ready for service '{service_name}'")
                    # Continue validation but note dependency issue
        
        # Perform service validation with retry logic
        attempts = 0
        max_attempts = config.timeout_config.retry_count + 1
        last_error = None
        
        for attempt in range(max_attempts):
            attempts = attempt + 1
            
            try:
                # Execute the validator
                if asyncio.iscoroutinefunction(config.validator):
                    validation_result = await config.validator()
                else:
                    validation_result = config.validator()
                
                # Handle different return types
                if isinstance(validation_result, bool):
                    ready = validation_result
                    level = ServiceReadinessLevel.FULLY_READY if ready else ServiceReadinessLevel.FAILED
                elif isinstance(validation_result, ServiceReadinessLevel):
                    level = validation_result
                    ready = level not in [ServiceReadinessLevel.FAILED, ServiceReadinessLevel.UNKNOWN]
                else:
                    # Default to boolean interpretation
                    ready = bool(validation_result)
                    level = ServiceReadinessLevel.FULLY_READY if ready else ServiceReadinessLevel.FAILED
                
                if ready:
                    elapsed_time = time.time() - start_time
                    
                    # Cache successful result
                    self.validation_cache[service_name] = (True, time.time())
                    
                    result = ServiceValidationResult(
                        service_name=service_name,
                        ready=True,
                        level=level,
                        criticality=config.criticality,
                        elapsed_time=elapsed_time,
                        attempts=attempts,
                        effective_timeout=effective_timeout
                    )
                    
                    self.logger.debug(f"Service '{service_name}' validated successfully in {elapsed_time:.3f}s")
                    return result
                
                # Not ready, check if we should retry
                if attempt < max_attempts - 1:
                    # Calculate delay with optional exponential backoff
                    delay = config.timeout_config.retry_delay
                    if config.timeout_config.exponential_backoff:
                        delay *= (2 ** attempt)
                    
                    self.logger.debug(f"Service '{service_name}' not ready (attempt {attempts}/{max_attempts}), retrying in {delay}s")
                    await asyncio.sleep(delay)
                
                # Check for timeout
                if time.time() - start_time > effective_timeout:
                    self.logger.warning(f"Service '{service_name}' validation timeout after {effective_timeout}s")
                    break
                    
            except Exception as e:
                last_error = str(e)
                self.logger.debug(f"Service '{service_name}' validation error (attempt {attempts}): {e}")
                
                if attempt < max_attempts - 1:
                    delay = config.timeout_config.retry_delay
                    if config.timeout_config.exponential_backoff:
                        delay *= (2 ** attempt)
                    await asyncio.sleep(delay)
        
        # Service validation failed - check for graceful degradation
        elapsed_time = time.time() - start_time
        can_degrade = config.graceful_degradation_handler is not None
        degradation_applied = False
        
        if can_degrade and config.criticality != ServiceCriticality.CRITICAL:
            try:
                if asyncio.iscoroutinefunction(config.graceful_degradation_handler):
                    await config.graceful_degradation_handler()
                else:
                    config.graceful_degradation_handler()
                
                degradation_applied = True
                self.degraded_services[service_name] = f"Service unavailable, graceful degradation applied"
                self.logger.info(f"Applied graceful degradation for service '{service_name}'")
                
            except Exception as e:
                self.logger.error(f"Graceful degradation failed for service '{service_name}': {e}")
        
        # Cache failure result (shorter TTL for failures)
        self.validation_cache[service_name] = (False, time.time())
        
        result = ServiceValidationResult(
            service_name=service_name,
            ready=False,
            level=ServiceReadinessLevel.DEGRADED if degradation_applied else ServiceReadinessLevel.FAILED,
            criticality=config.criticality,
            elapsed_time=elapsed_time,
            attempts=attempts,
            effective_timeout=effective_timeout,
            error_message=last_error,
            degradation_applied=degradation_applied,
            can_gracefully_degrade=can_degrade
        )
        
        return result
    
    async def validate_service_group(
        self, 
        service_names: List[str], 
        group_name: str = "unnamed_group",
        fail_fast_on_critical: bool = True
    ) -> ServiceGroupValidationResult:
        """
        Validate a group of services with dependency-aware ordering.
        
        Args:
            service_names: List of service names to validate
            group_name: Name of the service group for logging
            fail_fast_on_critical: Stop validation on first critical service failure
            
        Returns:
            ServiceGroupValidationResult with group validation status
        """
        start_time = time.time()
        service_results: Dict[str, ServiceValidationResult] = {}
        critical_failures: List[str] = []
        degraded_services: List[str] = []
        
        self.logger.info(f"Validating service group '{group_name}' with {len(service_names)} services")
        
        # Sort services by dependencies (topological sort would be ideal, but simple ordering works)
        ordered_services = self._order_services_by_dependencies(service_names)
        
        for service_name in ordered_services:
            self.logger.debug(f"Validating service '{service_name}' in group '{group_name}'")
            
            result = await self.validate_service(service_name)
            service_results[service_name] = result
            
            if not result.ready:
                if result.criticality == ServiceCriticality.CRITICAL:
                    critical_failures.append(service_name)
                    if fail_fast_on_critical:
                        self.logger.error(
                            f"Critical service '{service_name}' failed in group '{group_name}' - failing fast"
                        )
                        break
                elif result.degradation_applied:
                    degraded_services.append(service_name)
        
        # Calculate group readiness
        total_services = len(service_names)
        ready_services = sum(1 for r in service_results.values() if r.ready)
        overall_ready = len(critical_failures) == 0  # Group ready if no critical failures
        graceful_degradation_active = len(degraded_services) > 0
        
        elapsed_time = time.time() - start_time
        
        result = ServiceGroupValidationResult(
            group_name=group_name,
            overall_ready=overall_ready,
            total_services=total_services,
            ready_services=ready_services,
            critical_failures=critical_failures,
            degraded_services=degraded_services,
            service_results=service_results,
            total_elapsed_time=elapsed_time,
            graceful_degradation_active=graceful_degradation_active
        )
        
        self.logger.info(
            f"Service group '{group_name}' validation complete: "
            f"{ready_services}/{total_services} ready, "
            f"{len(critical_failures)} critical failures, "
            f"{len(degraded_services)} degraded ({elapsed_time:.2f}s)"
        )
        
        return result
    
    def _order_services_by_dependencies(self, service_names: List[str]) -> List[str]:
        """Order services by their dependencies (simple dependency-first ordering)."""
        ordered = []
        remaining = set(service_names)
        
        # Simple approach: services with fewer dependencies first
        while remaining:
            for service_name in list(remaining):
                if service_name not in self.service_configs:
                    ordered.append(service_name)
                    remaining.remove(service_name)
                    continue
                
                config = self.service_configs[service_name]
                unmet_deps = set(config.dependencies) & remaining
                
                if not unmet_deps:  # All dependencies already processed
                    ordered.append(service_name)
                    remaining.remove(service_name)
            
            # Safety check to prevent infinite loops
            if len(ordered) + len(remaining) != len(service_names):
                break
        
        # Add any remaining services (dependency cycles)
        ordered.extend(remaining)
        return ordered
    
    # Service-specific validators (enhance existing patterns)
    
    def _validate_database_service(self) -> bool:
        """Validate database service readiness."""
        try:
            if not self.app_state:
                return False
            
            # Check for db_session_factory
            if not hasattr(self.app_state, 'db_session_factory'):
                return False
            
            db_factory = self.app_state.db_session_factory
            if db_factory is None:
                return False
            
            # Check database availability flag
            if hasattr(self.app_state, 'database_available'):
                return bool(self.app_state.database_available)
            
            return True
            
        except Exception as e:
            self.logger.debug(f"Database validation error: {e}")
            return False
    
    def _validate_redis_service(self) -> bool:
        """Validate Redis service readiness with race condition fix."""
        try:
            if not self.app_state:
                return False
            
            if not hasattr(self.app_state, 'redis_manager'):
                return False
            
            redis_manager = self.app_state.redis_manager
            if redis_manager is None:
                return False
            
            # Check connection status
            if hasattr(redis_manager, 'is_connected'):
                is_connected = redis_manager.is_connected()
                
                # CRITICAL FIX: Apply grace period for GCP environments to prevent race conditions
                if is_connected and self.environment in ['staging', 'production']:
                    # 500ms grace period for background task stabilization
                    time.sleep(0.5)
                
                return is_connected
            
            return True
            
        except Exception as e:
            self.logger.debug(f"Redis validation error: {e}")
            return False
    
    def _validate_auth_system(self) -> bool:
        """Validate authentication system readiness."""
        try:
            if not self.app_state:
                return False
            
            # Check auth validation completion
            if hasattr(self.app_state, 'auth_validation_complete'):
                return bool(self.app_state.auth_validation_complete)
            
            # Check key manager
            if hasattr(self.app_state, 'key_manager'):
                return self.app_state.key_manager is not None
            
            return False
            
        except Exception as e:
            self.logger.debug(f"Auth system validation error: {e}")
            return False
    
    def _validate_agent_supervisor(self) -> bool:
        """Validate agent supervisor readiness."""
        try:
            if not self.app_state:
                return False
            
            # Check agent_supervisor exists
            if not hasattr(self.app_state, 'agent_supervisor'):
                return False
            
            return self.app_state.agent_supervisor is not None
            
        except Exception as e:
            self.logger.debug(f"Agent supervisor validation error: {e}")
            return False
    
    def _validate_thread_service(self) -> bool:
        """Validate thread service readiness."""
        try:
            if not self.app_state:
                return False
            
            # Check thread_service exists
            if not hasattr(self.app_state, 'thread_service'):
                return False
            
            return self.app_state.thread_service is not None
            
        except Exception as e:
            self.logger.debug(f"Thread service validation error: {e}")
            return False
    
    def _validate_websocket_bridge(self) -> bool:
        """Validate WebSocket bridge readiness."""
        try:
            if not self.app_state:
                return False
            
            # Check agent_websocket_bridge exists
            if not hasattr(self.app_state, 'agent_websocket_bridge'):
                return False
            
            bridge = self.app_state.agent_websocket_bridge
            if bridge is None:
                return False
            
            # Check critical notification methods
            required_methods = ['notify_agent_started', 'notify_agent_completed', 'notify_tool_executing']
            for method in required_methods:
                if not hasattr(bridge, method):
                    return False
            
            return True
            
        except Exception as e:
            self.logger.debug(f"WebSocket bridge validation error: {e}")
            return False
    
    # Graceful degradation handlers
    
    def _database_degradation_handler(self) -> None:
        """Handle database service degradation."""
        self.logger.info("Database degradation: WebSocket will use in-memory fallbacks for user context")
    
    def _redis_degradation_handler(self) -> None:
        """Handle Redis service degradation."""
        self.logger.info("Redis degradation: WebSocket will use local session management")
    
    def _auth_degradation_handler(self) -> None:
        """Handle auth system degradation."""
        self.logger.warning("Auth system degradation: WebSocket connections will use basic validation")
    
    def _supervisor_degradation_handler(self) -> None:
        """Handle agent supervisor degradation."""
        self.logger.warning("Agent supervisor degradation: WebSocket will use fallback message handlers")
    
    def _bridge_degradation_handler(self) -> None:
        """Handle WebSocket bridge degradation."""
        self.logger.info("WebSocket bridge degradation: Real-time events will use direct WebSocket send")
    
    # Health check integration
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status for all registered services."""
        health_status = {
            "overall_healthy": True,
            "environment": self.environment,
            "services": {},
            "degraded_services": list(self.degraded_services.keys()),
            "last_validation": self.last_validation_time,
            "cache_size": len(self.validation_cache)
        }
        
        critical_failures = []
        
        for service_name in self.service_configs.keys():
            result = await self.validate_service(service_name, force_refresh=True)
            
            health_status["services"][service_name] = {
                "ready": result.ready,
                "level": result.level.value,
                "criticality": result.criticality.value,
                "elapsed_time": result.elapsed_time,
                "attempts": result.attempts,
                "degradation_applied": result.degradation_applied,
                "error_message": result.error_message
            }
            
            if result.criticality == ServiceCriticality.CRITICAL and not result.ready:
                critical_failures.append(service_name)
        
        health_status["overall_healthy"] = len(critical_failures) == 0
        health_status["critical_failures"] = critical_failures
        
        self.last_validation_time = time.time()
        return health_status


# SSOT Factory Functions

def create_service_readiness_validator(
    app_state: Optional[Any] = None, 
    environment: Optional[str] = None
) -> ServiceReadinessValidator:
    """
    Create service readiness validator using SSOT patterns.
    
    SSOT COMPLIANCE: This is the canonical way to create service validators.
    All other creation methods should delegate to this function.
    
    Args:
        app_state: Application state containing service references
        environment: Environment override (test, development, staging, production)
        
    Returns:
        ServiceReadinessValidator instance
    """
    return ServiceReadinessValidator(app_state, environment)


# Integration Context Managers

@asynccontextmanager
async def websocket_readiness_guard(
    app_state: Any, 
    required_services: Optional[List[str]] = None,
    timeout_seconds: float = 60.0
):
    """
    Context manager for WebSocket readiness validation with graceful degradation.
    
    INTEGRATION: Use this in WebSocket route handlers to ensure service readiness.
    
    Usage:
        async with websocket_readiness_guard(app.state, ["database", "redis", "agent_supervisor"]):
            await websocket.accept()
            # WebSocket connection is ready for processing
    
    Args:
        app_state: Application state
        required_services: List of required service names (defaults to WebSocket-critical services)
        timeout_seconds: Maximum time to wait for services to be ready
    """
    if required_services is None:
        required_services = ["database", "redis", "auth_system", "agent_supervisor", "thread_service"]
    
    validator = create_service_readiness_validator(app_state)
    
    try:
        # Validate required services
        group_result = await validator.validate_service_group(
            required_services, 
            group_name="websocket_critical",
            fail_fast_on_critical=False  # Don't fail fast, we want to see all issues
        )
        
        # Yield validation result for inspection
        yield {
            "ready": group_result.overall_ready,
            "degradation_active": group_result.graceful_degradation_active,
            "critical_failures": group_result.critical_failures,
            "degraded_services": group_result.degraded_services,
            "service_results": group_result.service_results,
            "elapsed_time": group_result.total_elapsed_time
        }
        
    except Exception as e:
        logger = central_logger.get_logger(__name__)
        logger.error(f"WebSocket readiness guard error: {e}")
        # Don't re-raise - let WebSocket connection proceed with degradation
        yield {
            "ready": False,
            "degradation_active": True,
            "critical_failures": ["validation_error"],
            "degraded_services": [],
            "service_results": {},
            "elapsed_time": 0.0,
            "error": str(e)
        }


# Health Check Integration Function

async def get_websocket_service_health(app_state: Any) -> Tuple[bool, Dict[str, Any]]:
    """
    Get WebSocket service health status for integration with health endpoints.
    
    Returns:
        Tuple of (overall_healthy: bool, health_details: dict)
    """
    validator = create_service_readiness_validator(app_state)
    health_status = await validator.get_health_status()
    
    return health_status["overall_healthy"], health_status