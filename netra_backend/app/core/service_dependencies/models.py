"""
Service Dependency Models - Core data structures and enums.

Provides type-safe models for service dependency resolution, health checks,
and startup orchestration. Integrates with existing health check systems
while maintaining SSOT compliance.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Union

from netra_backend.app.core.shared_health_types import HealthStatus


class ServiceType(Enum):
    """Types of services in the system."""
    DATABASE_POSTGRES = "database_postgres"
    DATABASE_REDIS = "database_redis"
    AUTH_SERVICE = "auth_service"
    BACKEND_SERVICE = "backend_service"
    WEBSOCKET_SERVICE = "websocket_service"
    LLM_SERVICE = "llm_service"
    FRONTEND_SERVICE = "frontend_service"
    ANALYTICS_SERVICE = "analytics_service"


class DependencyRelation(Enum):
    """Types of dependency relationships."""
    REQUIRED = "required"      # Hard dependency - service cannot start without this
    OPTIONAL = "optional"      # Soft dependency - service can start but functionality reduced
    PREFERRED = "preferred"    # Service works better with this dependency


class DependencyPhase(Enum):
    """Service startup phases for dependency resolution."""
    PHASE_1_CORE = "phase_1_core"           # PostgreSQL, Redis (parallel)
    PHASE_2_AUTH = "phase_2_auth"           # Auth Service (depends on PostgreSQL)
    PHASE_3_BACKEND = "phase_3_backend"     # Backend services (depends on all above)
    PHASE_4_FRONTEND = "phase_4_frontend"   # WebSocket/Frontend (depends on all above)


class RetryStrategy(Enum):
    """Types of retry strategies for service dependencies."""
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    FIXED_INTERVAL = "fixed_interval"
    NO_RETRY = "no_retry"


class EnvironmentType(Enum):
    """Environment types with different dependency configurations."""
    TESTING = "testing"     # Fast timeouts, minimal retries
    DEVELOPMENT = "development"  # Balanced configuration
    STAGING = "staging"     # Production-like but more lenient
    PRODUCTION = "production"  # Robust configuration


@dataclass
class ServiceConfiguration:
    """Configuration for service health checks and retries."""
    service_type: ServiceType
    timeout_seconds: float
    max_retries: int
    retry_delay_base: float
    retry_strategy: RetryStrategy
    health_check_interval: float
    critical: bool = True
    
    @classmethod
    def for_environment(cls, service_type: ServiceType, environment: Union[EnvironmentType, str]) -> 'ServiceConfiguration':
        """Create service configuration appropriate for environment."""
        # Convert string to EnvironmentType if needed
        if isinstance(environment, str):
            environment = EnvironmentType(environment)
            
        configs = {
            EnvironmentType.TESTING: {
                'timeout_seconds': 2.0,
                'max_retries': 3,
                'retry_delay_base': 0.5,
                'health_check_interval': 1.0
            },
            EnvironmentType.DEVELOPMENT: {
                'timeout_seconds': 5.0,
                'max_retries': 5,
                'retry_delay_base': 1.0,
                'health_check_interval': 2.0
            },
            EnvironmentType.STAGING: {
                'timeout_seconds': 15.0,
                'max_retries': 10,
                'retry_delay_base': 2.0,
                'health_check_interval': 5.0
            },
            EnvironmentType.PRODUCTION: {
                'timeout_seconds': 30.0,
                'max_retries': 15,
                'retry_delay_base': 3.0,
                'health_check_interval': 10.0
            }
        }
        
        config = configs[environment]
        return cls(
            service_type=service_type,
            retry_strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
            **config
        )


@dataclass
class ServiceDependency:
    """Represents a dependency relationship between services."""
    service: ServiceType
    depends_on: ServiceType
    relation: DependencyRelation
    phase: DependencyPhase
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HealthCheckResult:
    """Result of a service health check operation."""
    service_type: ServiceType
    service_name: str
    success: bool
    health_status: HealthStatus
    response_time_ms: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    error_message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    retry_count: int = 0


@dataclass
class ServiceValidationResult:
    """Result of validating a single service's dependencies."""
    service_type: ServiceType
    service_name: str
    validation_success: bool
    health_check_result: Optional[HealthCheckResult] = None
    dependency_failures: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DependencyValidationResult:
    """Complete result of service dependency validation."""
    overall_success: bool
    validation_timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    service_results: List[ServiceValidationResult] = field(default_factory=list)
    critical_failures: List[str] = field(default_factory=list)
    phase_results: Dict[DependencyPhase, bool] = field(default_factory=dict)
    total_services_checked: int = 0
    services_healthy: int = 0
    services_degraded: int = 0
    services_failed: int = 0
    execution_duration_ms: float = 0.0


@dataclass
class GoldenPathRequirement:
    """Requirement for golden path business validation."""
    service_type: ServiceType
    requirement_name: str
    validation_function: str  # Name of method to call
    critical: bool
    description: str = ""
    business_impact: str = ""


@dataclass
class RetryContext:
    """Context for retry operations."""
    service_type: ServiceType
    attempt_number: int
    total_attempts: int
    last_error: Optional[str] = None
    retry_delay_seconds: float = 0.0
    start_time: datetime = field(default_factory=lambda: datetime.now(UTC))
    accumulated_delay: float = 0.0


# Predefined service dependency graph for the system
DEFAULT_SERVICE_DEPENDENCIES = [
    # Phase 1 - Core services (can start in parallel)
    ServiceDependency(
        service=ServiceType.DATABASE_POSTGRES,
        depends_on=ServiceType.DATABASE_POSTGRES,  # Self-dependency for phase grouping
        relation=DependencyRelation.REQUIRED,
        phase=DependencyPhase.PHASE_1_CORE,
        description="PostgreSQL database core storage"
    ),
    ServiceDependency(
        service=ServiceType.DATABASE_REDIS,
        depends_on=ServiceType.DATABASE_REDIS,  # Self-dependency for phase grouping
        relation=DependencyRelation.REQUIRED,
        phase=DependencyPhase.PHASE_1_CORE,
        description="Redis cache and session storage"
    ),
    
    # Phase 2 - Auth service (depends on PostgreSQL)
    ServiceDependency(
        service=ServiceType.AUTH_SERVICE,
        depends_on=ServiceType.DATABASE_POSTGRES,
        relation=DependencyRelation.REQUIRED,
        phase=DependencyPhase.PHASE_2_AUTH,
        description="Authentication service requires PostgreSQL for user data"
    ),
    
    # Phase 3 - Backend services (depend on databases and auth)
    ServiceDependency(
        service=ServiceType.BACKEND_SERVICE,
        depends_on=ServiceType.DATABASE_POSTGRES,
        relation=DependencyRelation.REQUIRED,
        phase=DependencyPhase.PHASE_3_BACKEND,
        description="Backend service requires PostgreSQL"
    ),
    ServiceDependency(
        service=ServiceType.BACKEND_SERVICE,
        depends_on=ServiceType.DATABASE_REDIS,
        relation=DependencyRelation.REQUIRED,
        phase=DependencyPhase.PHASE_3_BACKEND,
        description="Backend service requires Redis for caching"
    ),
    ServiceDependency(
        service=ServiceType.BACKEND_SERVICE,
        depends_on=ServiceType.AUTH_SERVICE,
        relation=DependencyRelation.REQUIRED,
        phase=DependencyPhase.PHASE_3_BACKEND,
        description="Backend service requires Auth service for user validation"
    ),
    ServiceDependency(
        service=ServiceType.LLM_SERVICE,
        depends_on=ServiceType.BACKEND_SERVICE,
        relation=DependencyRelation.PREFERRED,
        phase=DependencyPhase.PHASE_3_BACKEND,
        description="LLM service integration with backend"
    ),
    
    # Phase 4 - Frontend services (depend on everything)
    ServiceDependency(
        service=ServiceType.WEBSOCKET_SERVICE,
        depends_on=ServiceType.BACKEND_SERVICE,
        relation=DependencyRelation.REQUIRED,
        phase=DependencyPhase.PHASE_4_FRONTEND,
        description="WebSocket service requires backend for agent communication"
    ),
    ServiceDependency(
        service=ServiceType.FRONTEND_SERVICE,
        depends_on=ServiceType.BACKEND_SERVICE,
        relation=DependencyRelation.REQUIRED,
        phase=DependencyPhase.PHASE_4_FRONTEND,
        description="Frontend requires backend APIs"
    ),
    ServiceDependency(
        service=ServiceType.FRONTEND_SERVICE,
        depends_on=ServiceType.WEBSOCKET_SERVICE,
        relation=DependencyRelation.REQUIRED,
        phase=DependencyPhase.PHASE_4_FRONTEND,
        description="Frontend requires WebSocket for real-time updates"
    ),
]


# Golden path requirements for business value validation
GOLDEN_PATH_REQUIREMENTS = [
    GoldenPathRequirement(
        service_type=ServiceType.DATABASE_POSTGRES,
        requirement_name="user_authentication_ready",
        validation_function="validate_user_auth_tables",
        critical=True,
        description="User authentication tables and indexes ready",
        business_impact="Users cannot log in without proper auth tables"
    ),
    GoldenPathRequirement(
        service_type=ServiceType.DATABASE_REDIS,
        requirement_name="session_storage_ready", 
        validation_function="validate_session_storage",
        critical=True,
        description="Redis session storage operational",
        business_impact="User sessions cannot be maintained without Redis"
    ),
    GoldenPathRequirement(
        service_type=ServiceType.AUTH_SERVICE,
        requirement_name="jwt_validation_ready",
        validation_function="validate_jwt_capabilities",
        critical=True,
        description="JWT token creation and validation working",
        business_impact="JWT authentication failure prevents users from accessing chat functionality"
    ),
    GoldenPathRequirement(
        service_type=ServiceType.BACKEND_SERVICE,
        requirement_name="agent_execution_ready",
        validation_function="validate_agent_execution_chain",
        critical=True,
        description="Agent supervisor and execution engine operational",
        business_impact="Chat functionality completely broken without agent execution"
    ),
    GoldenPathRequirement(
        service_type=ServiceType.WEBSOCKET_SERVICE,
        requirement_name="realtime_communication_ready",
        validation_function="validate_websocket_agent_events",
        critical=True,
        description="WebSocket agent event notifications working",
        business_impact="Users get no real-time feedback during AI processing"
    ),
]