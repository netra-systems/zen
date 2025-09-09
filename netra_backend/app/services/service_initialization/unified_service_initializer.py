"""Unified Service Initializer - SSOT for Service Initialization with Health Validation

Business Value Justification:
- Segment: Enterprise ($500K+ ARR) and Standard customers
- Business Goal: Zero mock responses, transparent service communication
- Value Impact: Protects $4.1M immediate ARR through honest service status
- Revenue Impact: Prevents contract cancellations from misleading responses

This is the SSOT for all service initialization patterns, implementing progressive
disclosure: Real AI >> Transparent initialization >> Clean failure.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set, TYPE_CHECKING

if TYPE_CHECKING:
    from netra_backend.app.services.user_execution_context import UserExecutionContext

from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.schemas.shared_types import ErrorContext
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)

# Critical services that must be available for any processing
CRITICAL_SERVICES = {
    "database_connection",
    "authentication_service", 
    "user_context_manager"
}

# Services that can run in degraded mode
DEGRADED_MODE_SERVICES = {
    "llm_manager",
    "model_cascade", 
    "data_pipeline",
    "analytics_service"
}

class ServiceStatus(Enum):
    """Service initialization status states."""
    INITIALIZING = "initializing"
    READY = "ready"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    FAILED = "failed"


@dataclass
class ServiceInitializationResult:
    """Result of service initialization process."""
    status: ServiceStatus
    services_ready: Dict[str, ServiceStatus]
    services_failed: Dict[str, str]  # service_name -> error_message
    initialization_time_ms: float
    should_fail_request: bool
    degraded_services: Set[str]
    critical_services_available: bool
    error_context: Optional[ErrorContext] = None
    
    @property
    def is_fully_operational(self) -> bool:
        """Check if all requested services are fully operational."""
        return all(status == ServiceStatus.READY for status in self.services_ready.values())
    
    @property
    def can_process_requests(self) -> bool:
        """Check if system can process requests (possibly in degraded mode)."""
        return self.critical_services_available and not self.should_fail_request


class UnifiedServiceException(Exception):
    """Exception raised when services cannot be initialized properly.
    
    This replaces all mock responses and provides transparent error context.
    """
    
    def __init__(
        self,
        message: str,
        error_context: ErrorContext,
        should_retry: bool = True,
        estimated_recovery_time_seconds: Optional[int] = None,
        alternative_suggestions: Optional[List[str]] = None,
        enterprise_escalation: bool = False
    ):
        super().__init__(message)
        self.message = message
        self.error_context = error_context
        self.should_retry = should_retry
        self.estimated_recovery_time_seconds = estimated_recovery_time_seconds
        self.alternative_suggestions = alternative_suggestions or []
        self.enterprise_escalation = enterprise_escalation


class UnifiedServiceInitializer:
    """SSOT for all service initialization with health validation.
    
    Implements factory pattern from USER_CONTEXT_ARCHITECTURE.md for complete
    user isolation and transparent service status communication.
    """
    
    def __init__(self):
        """Initialize service initializer with monitoring."""
        self.initialization_count = 0
        self.service_health_cache: Dict[str, Dict[str, Any]] = {}
        self.error_handler = UnifiedErrorHandler()
        
    async def initialize_for_context(
        self,
        context: UserExecutionContext,
        required_services: Set[str],
        timeout_seconds: float = 30.0
    ) -> ServiceInitializationResult:
        """Initialize services with progressive disclosure and transparent communication.
        
        This is the core method that eliminates mock responses by providing
        transparent service status and clean failures when services are unavailable.
        
        Args:
            context: User execution context with request isolation
            required_services: Set of service names that need to be initialized
            timeout_seconds: Maximum time to spend on initialization
            
        Returns:
            ServiceInitializationResult with complete status information
            
        Raises:
            UnifiedServiceException: When critical services cannot be initialized
        """
        start_time = time.time()
        self.initialization_count += 1
        
        logger.info(
            f"Starting service initialization for user={context.user_id}, "
            f"request={context.request_id}, services={required_services}"
        )
        
        services_ready: Dict[str, ServiceStatus] = {}
        services_failed: Dict[str, str] = {}
        degraded_services: Set[str] = set()
        
        # Check which services are critical for this request
        critical_requested = required_services.intersection(CRITICAL_SERVICES)
        degradable_requested = required_services.intersection(DEGRADED_MODE_SERVICES)
        
        # Initialize critical services first
        for service_name in critical_requested:
            try:
                await context.websocket_bridge.emit_service_initializing(
                    service_name,
                    initialization_steps=await self._get_initialization_steps(service_name)
                )
                
                service_instance = await self._initialize_service(service_name, context)
                health_status = await self._validate_service_health(service_instance, context)
                
                if health_status.is_healthy:
                    services_ready[service_name] = ServiceStatus.READY
                    await context.websocket_bridge.emit_service_ready(
                        service_name,
                        initialization_time_ms=health_status.response_time_ms
                    )
                else:
                    # Critical service unhealthy = request failure
                    services_failed[service_name] = health_status.error_message
                    await context.websocket_bridge.emit_service_unavailable(
                        service_name,
                        health_status.error_message,
                        estimated_recovery_seconds=60
                    )
                    
            except Exception as e:
                error_msg = f"Critical service {service_name} initialization failed: {str(e)}"
                logger.error(error_msg)
                services_failed[service_name] = str(e)
                
                await context.websocket_bridge.emit_service_unavailable(
                    service_name,
                    str(e),
                    estimated_recovery_seconds=120
                )
        
        # Check if we can continue with critical service failures
        critical_services_available = len(services_failed.intersection(critical_requested)) == 0
        
        if not critical_services_available:
            # Cannot continue - clean failure with context
            error_context = ErrorContext(
                user_id=context.user_id,
                request_id=context.request_id,
                service_name="critical_services",
                error_type="initialization_failure",
                user_tier=context.user_tier
            )
            
            initialization_time = (time.time() - start_time) * 1000
            
            return ServiceInitializationResult(
                status=ServiceStatus.FAILED,
                services_ready=services_ready,
                services_failed=services_failed,
                initialization_time_ms=initialization_time,
                should_fail_request=True,
                degraded_services=degraded_services,
                critical_services_available=False,
                error_context=error_context
            )
        
        # Initialize degradable services (can fail without request failure)
        for service_name in degradable_requested:
            try:
                await context.websocket_bridge.emit_service_initializing(service_name)
                
                service_instance = await self._initialize_service(service_name, context)
                health_status = await self._validate_service_health(service_instance, context)
                
                if health_status.is_healthy:
                    services_ready[service_name] = ServiceStatus.READY
                    await context.websocket_bridge.emit_service_ready(service_name)
                else:
                    # Degraded mode for non-critical services
                    services_ready[service_name] = ServiceStatus.DEGRADED
                    degraded_services.add(service_name)
                    await context.websocket_bridge.emit_service_degraded(
                        service_name,
                        health_status.error_message,
                        fallback_options=await self._get_fallback_options(service_name)
                    )
                    
            except Exception as e:
                error_msg = f"Service {service_name} initialization failed: {str(e)}"
                logger.warning(error_msg)  # Warning for non-critical services
                services_failed[service_name] = str(e)
                
                await context.websocket_bridge.emit_service_unavailable(
                    service_name,
                    str(e),
                    estimated_recovery_seconds=180,
                    alternatives=await self._get_service_alternatives(service_name)
                )
        
        initialization_time = (time.time() - start_time) * 1000
        
        # Determine overall status
        if len(services_failed) == 0:
            overall_status = ServiceStatus.READY
        elif len(degraded_services) > 0:
            overall_status = ServiceStatus.DEGRADED  
        else:
            overall_status = ServiceStatus.READY  # Critical services OK
        
        logger.info(
            f"Service initialization completed: user={context.user_id}, "
            f"status={overall_status.value}, time={initialization_time:.1f}ms, "
            f"ready={len(services_ready)}, failed={len(services_failed)}, "
            f"degraded={len(degraded_services)}"
        )
        
        return ServiceInitializationResult(
            status=overall_status,
            services_ready=services_ready,
            services_failed=services_failed,
            initialization_time_ms=initialization_time,
            should_fail_request=False,
            degraded_services=degraded_services,
            critical_services_available=critical_services_available
        )
    
    async def _initialize_service(
        self,
        service_name: str,
        context: UserExecutionContext
    ) -> Any:
        """Initialize a specific service with user context isolation.
        
        This method ensures each service is initialized with proper user isolation
        following the USER_CONTEXT_ARCHITECTURE.md patterns.
        """
        if service_name == "database_connection":
            # Use context.db_session - already initialized in context
            return context.db_session
            
        elif service_name == "authentication_service":
            # Validate user authentication is still valid
            from netra_backend.app.services.auth.authentication_manager import AuthenticationManager
            auth_manager = AuthenticationManager()
            return await auth_manager.validate_context_auth(context)
            
        elif service_name == "user_context_manager":
            # Context is already created, validate it's complete
            return await self._validate_user_context_completeness(context)
            
        elif service_name == "llm_manager":
            # Initialize LLM manager for this user context
            from netra_backend.app.llm.llm_manager import LLMManager
            llm_manager = LLMManager()
            await llm_manager.initialize_for_context(context)
            return llm_manager
            
        elif service_name == "model_cascade":
            # Initialize model cascade with user-specific configuration
            from netra_backend.app.agents.chat_orchestrator.model_cascade import ModelCascade
            from netra_backend.app.llm.llm_manager import LLMManager
            from netra_backend.app.services.llm.model_selector import ModelSelector
            from netra_backend.app.agents.chat_orchestrator.quality_evaluator import QualityEvaluator
            from netra_backend.app.services.analytics.cost_tracker import CostTracker
            from netra_backend.app.services.monitoring.metrics_service import MetricsService
            
            llm_manager = LLMManager()
            model_selector = ModelSelector()
            quality_evaluator = QualityEvaluator()
            cost_tracker = CostTracker()
            metrics_service = MetricsService()
            
            cascade = ModelCascade(
                llm_manager=llm_manager,
                model_selector=model_selector, 
                quality_evaluator=quality_evaluator,
                cost_tracker=cost_tracker,
                metrics_service=metrics_service
            )
            
            return cascade
            
        elif service_name == "data_pipeline":
            # Initialize data pipeline with user-specific access controls
            from netra_backend.app.agents.data.unified_data_agent import UnifiedDataAgentFactory
            factory = UnifiedDataAgentFactory()
            return factory.create_for_context(context)
            
        elif service_name == "analytics_service":
            # Initialize analytics with user tier-aware configuration
            from netra_backend.app.services.analytics.analytics_engine import AnalyticsEngine
            analytics = AnalyticsEngine()
            await analytics.initialize_for_user_tier(context.user_tier)
            return analytics
            
        else:
            raise ValueError(f"Unknown service: {service_name}")
    
    async def _validate_service_health(
        self,
        service_instance: Any,
        context: UserExecutionContext
    ) -> 'ServiceHealthStatus':
        """Validate service health with user context."""
        start_time = time.time()
        
        try:
            # Service-specific health checks
            if hasattr(service_instance, 'health_check'):
                health_result = await service_instance.health_check(context)
                response_time = (time.time() - start_time) * 1000
                
                return ServiceHealthStatus(
                    is_healthy=health_result.get('healthy', False),
                    response_time_ms=response_time,
                    error_message=health_result.get('error_message'),
                    metadata=health_result.get('metadata', {})
                )
            else:
                # Basic validation - service exists and is not None
                response_time = (time.time() - start_time) * 1000
                return ServiceHealthStatus(
                    is_healthy=service_instance is not None,
                    response_time_ms=response_time,
                    error_message=None if service_instance else "Service instance is None"
                )
                
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return ServiceHealthStatus(
                is_healthy=False,
                response_time_ms=response_time,
                error_message=f"Health check failed: {str(e)}"
            )
    
    async def _get_initialization_steps(self, service_name: str) -> List[str]:
        """Get user-friendly initialization steps for a service."""
        steps_map = {
            "database_connection": [
                "Connecting to database",
                "Validating user permissions",
                "Preparing query engine"
            ],
            "authentication_service": [
                "Verifying user token",
                "Loading user permissions",
                "Setting up security context"
            ],
            "llm_manager": [
                "Connecting to AI models",
                "Loading user preferences",
                "Preparing inference engine"
            ],
            "model_cascade": [
                "Initializing model selection",
                "Loading performance history",
                "Preparing cascade routing"
            ],
            "data_pipeline": [
                "Connecting to data sources",
                "Validating user access",
                "Preparing analytics engine"
            ]
        }
        return steps_map.get(service_name, ["Initializing service"])
    
    async def _get_fallback_options(self, service_name: str) -> List[str]:
        """Get fallback options for degraded services."""
        fallback_map = {
            "llm_manager": [
                "Basic text processing available",
                "Simple queries will work",
                "Complex AI features limited"
            ],
            "model_cascade": [
                "Direct model access available", 
                "Model selection simplified",
                "Quality optimization disabled"
            ],
            "data_pipeline": [
                "Recent data cache available",
                "Real-time data limited",
                "Historical analysis available"
            ]
        }
        return fallback_map.get(service_name, ["Limited functionality available"])
    
    async def _get_service_alternatives(self, service_name: str) -> List[str]:
        """Get alternative suggestions for unavailable services."""
        alternatives_map = {
            "llm_manager": [
                "Try again in 60 seconds",
                "Check system status page", 
                "Contact support for urgent requests"
            ],
            "data_pipeline": [
                "Try again in 2 minutes",
                "Use cached data if available",
                "Schedule analysis for later"
            ]
        }
        return alternatives_map.get(service_name, ["Try again later"])
    
    async def _validate_user_context_completeness(
        self,
        context: UserExecutionContext
    ) -> UserExecutionContext:
        """Validate that user context is complete and properly isolated."""
        required_fields = ['user_id', 'request_id', 'run_id', 'user_tier']
        
        for field in required_fields:
            if not hasattr(context, field) or getattr(context, field) is None:
                raise ValueError(f"User context missing required field: {field}")
        
        # Validate user isolation
        if not hasattr(context, 'websocket_bridge'):
            raise ValueError("User context missing WebSocket bridge for transparent communication")
            
        return context


@dataclass 
class ServiceHealthStatus:
    """Health status result for a service."""
    is_healthy: bool
    response_time_ms: float
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = None