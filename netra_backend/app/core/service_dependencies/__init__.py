"""
Service Dependencies Module - Systematic service dependency resolution.

Provides comprehensive service dependency validation, health checking,
retry logic, startup orchestration, and golden path business validation
to ensure reliable service startup and business functionality protection.

Key Components:
- ServiceDependencyChecker: Main validation and coordination
- HealthCheckValidator: Service-specific health validation
- RetryMechanism: Progressive retry with circuit breaker
- DependencyGraphResolver: Dependency ordering and resolution
- StartupOrchestrator: Service startup coordination
- GoldenPathValidator: Business functionality validation
- IntegrationManager: Docker and service integration coordination

Usage:
    from netra_backend.app.core.service_dependencies import ServiceDependencyChecker
    from netra_backend.app.core.service_dependencies.models import ServiceType, EnvironmentType
    
    checker = ServiceDependencyChecker(environment=EnvironmentType.DEVELOPMENT)
    result = await checker.validate_service_dependencies(app)
"""

# Main service dependency checker
from .service_dependency_checker import ServiceDependencyChecker

# Core models and types
from .models import (
    # Service types and enums
    ServiceType,
    DependencyRelation,
    DependencyPhase,
    RetryStrategy,
    EnvironmentType,
    
    # Data models
    ServiceConfiguration,
    ServiceDependency,
    HealthCheckResult,
    ServiceValidationResult,
    DependencyValidationResult,
    GoldenPathRequirement,
    RetryContext,
    
    # Predefined configurations
    DEFAULT_SERVICE_DEPENDENCIES,
    GOLDEN_PATH_REQUIREMENTS,
)

# Specialized validators and components
from .health_check_validator import HealthCheckValidator
from .retry_mechanism import RetryMechanism
from .dependency_graph_resolver import DependencyGraphResolver
from .golden_path_validator import (
    GoldenPathValidator, 
    GoldenPathValidationResult
)
from .startup_orchestrator import (
    StartupOrchestrator,
    StartupOrchestrationResult
)
from .integration_manager import IntegrationManager

# Export all key components
__all__ = [
    # Main checker
    "ServiceDependencyChecker",
    
    # Core types and enums
    "ServiceType",
    "DependencyRelation", 
    "DependencyPhase",
    "RetryStrategy",
    "EnvironmentType",
    
    # Data models
    "ServiceConfiguration",
    "ServiceDependency",
    "HealthCheckResult",
    "ServiceValidationResult", 
    "DependencyValidationResult",
    "GoldenPathRequirement",
    "RetryContext",
    
    # Predefined configurations
    "DEFAULT_SERVICE_DEPENDENCIES",
    "GOLDEN_PATH_REQUIREMENTS",
    
    # Specialized components
    "HealthCheckValidator",
    "RetryMechanism", 
    "DependencyGraphResolver",
    "GoldenPathValidator",
    "GoldenPathValidationResult",
    "StartupOrchestrator",
    "StartupOrchestrationResult",
    "IntegrationManager",
]