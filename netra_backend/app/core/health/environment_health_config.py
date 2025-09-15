"""Environment-Aware Health Configuration

Business Value Justification (BVJ):
- Segment: Platform/Infrastructure
- Business Goal: System Stability - Prevent staging deployment failures from blocking Golden Path
- Value Impact: Enables environment-specific service criticality to prevent false alarms in staging
- Strategic Impact: Protects $500K+ ARR by maintaining staging deployment reliability

This module provides environment-specific health configuration that allows different
service criticality levels across environments. Critical for Issue #690 resolution.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from enum import Enum

from shared.isolated_environment import get_env
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class ServiceCriticality(Enum):
    """Service criticality levels for health checks."""
    CRITICAL = "critical"        # Failure blocks deployment/health checks
    IMPORTANT = "important"      # Failure causes warnings but doesn't block
    OPTIONAL = "optional"        # Failure logged but ignored for health status
    DISABLED = "disabled"        # Service check completely skipped


class HealthFailureMode(Enum):
    """How to handle health check failures."""
    FAIL_HARD = "fail_hard"              # Return 503 immediately
    WARN_CONTINUE = "warn_continue"      # Log warning but continue
    GRACEFUL_DEGRADE = "graceful_degrade"  # Continue with reduced functionality
    IGNORE = "ignore"                    # Completely ignore failures


@dataclass
class ServiceHealthConfig:
    """Health configuration for a single service."""
    name: str
    criticality: ServiceCriticality
    timeout_seconds: float
    failure_mode: HealthFailureMode
    retry_count: int = 0
    graceful_fallback_message: Optional[str] = None
    environment_overrides: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    def get_effective_config(self, environment: str) -> 'ServiceHealthConfig':
        """Get effective configuration for the given environment."""
        if environment not in self.environment_overrides:
            return self

        overrides = self.environment_overrides[environment]
        effective_config = ServiceHealthConfig(
            name=self.name,
            criticality=ServiceCriticality(overrides.get('criticality', self.criticality.value)),
            timeout_seconds=overrides.get('timeout_seconds', self.timeout_seconds),
            failure_mode=HealthFailureMode(overrides.get('failure_mode', self.failure_mode.value)),
            retry_count=overrides.get('retry_count', self.retry_count),
            graceful_fallback_message=overrides.get('graceful_fallback_message', self.graceful_fallback_message),
            environment_overrides=self.environment_overrides
        )

        logger.debug(f"Applied environment overrides for {self.name} in {environment}: {overrides}")
        return effective_config


@dataclass
class EnvironmentHealthConfig:
    """Complete health configuration for an environment."""

    # Default service configurations
    services: Dict[str, ServiceHealthConfig] = field(default_factory=dict)

    # Global environment settings
    default_timeout_seconds: float = 10.0
    health_check_timeout_seconds: float = 30.0
    overall_failure_threshold: float = 0.5  # 50% of critical services must pass

    # Environment-specific behavior
    allow_partial_startup: bool = False
    log_level_on_failure: str = "ERROR"

    def __post_init__(self):
        """Initialize default service configurations if not provided."""
        if not self.services:
            self.services = self._get_default_service_configs()

    def _get_default_service_configs(self) -> Dict[str, ServiceHealthConfig]:
        """Get default service health configurations with environment-specific overrides."""

        return {
            # CRITICAL SERVICES - Required for basic functionality
            "postgres": ServiceHealthConfig(
                name="postgres",
                criticality=ServiceCriticality.CRITICAL,
                timeout_seconds=8.0,
                failure_mode=HealthFailureMode.FAIL_HARD,
                retry_count=2,
                graceful_fallback_message="Database connectivity is required for all operations"
            ),

            "websocket": ServiceHealthConfig(
                name="websocket",
                criticality=ServiceCriticality.CRITICAL,
                timeout_seconds=5.0,
                failure_mode=HealthFailureMode.FAIL_HARD,
                retry_count=1,
                graceful_fallback_message="WebSocket functionality required for real-time features"
            ),

            # IMPORTANT SERVICES - Business functionality
            "llm": ServiceHealthConfig(
                name="llm",
                criticality=ServiceCriticality.IMPORTANT,
                timeout_seconds=15.0,
                failure_mode=HealthFailureMode.WARN_CONTINUE,
                retry_count=1,
                graceful_fallback_message="AI functionality limited - some features may not work properly",
                environment_overrides={
                    # CRITICAL REMEDIATION: In staging, LLM manager is optional due to Cloud Run constraints
                    "staging": {
                        "criticality": ServiceCriticality.OPTIONAL.value,
                        "failure_mode": HealthFailureMode.GRACEFUL_DEGRADE.value,
                        "timeout_seconds": 5.0,
                        "graceful_fallback_message": "AI services temporarily unavailable in staging environment"
                    }
                }
            ),

            "redis": ServiceHealthConfig(
                name="redis",
                criticality=ServiceCriticality.IMPORTANT,
                timeout_seconds=3.0,
                failure_mode=HealthFailureMode.WARN_CONTINUE,
                retry_count=1,
                graceful_fallback_message="Caching disabled - performance may be reduced",
                environment_overrides={
                    "staging": {
                        "criticality": ServiceCriticality.OPTIONAL.value,
                        "failure_mode": HealthFailureMode.GRACEFUL_DEGRADE.value,
                        "timeout_seconds": 2.0
                    },
                    "development": {
                        "criticality": ServiceCriticality.OPTIONAL.value,
                        "failure_mode": HealthFailureMode.IGNORE.value
                    }
                }
            ),

            # OPTIONAL SERVICES - Analytics and monitoring
            "clickhouse": ServiceHealthConfig(
                name="clickhouse",
                criticality=ServiceCriticality.OPTIONAL,
                timeout_seconds=5.0,
                failure_mode=HealthFailureMode.GRACEFUL_DEGRADE,
                retry_count=0,
                graceful_fallback_message="Analytics services unavailable",
                environment_overrides={
                    "staging": {
                        "failure_mode": HealthFailureMode.IGNORE.value,
                        "timeout_seconds": 2.0
                    },
                    "development": {
                        "criticality": ServiceCriticality.DISABLED.value
                    }
                }
            ),

            "auth_service": ServiceHealthConfig(
                name="auth_service",
                criticality=ServiceCriticality.IMPORTANT,
                timeout_seconds=8.0,
                failure_mode=HealthFailureMode.WARN_CONTINUE,
                retry_count=2,
                graceful_fallback_message="Authentication service degraded - some features limited"
            )
        }

    def get_service_config(self, service_name: str, environment: Optional[str] = None) -> Optional[ServiceHealthConfig]:
        """Get effective service configuration for the given environment."""
        if service_name not in self.services:
            logger.warning(f"No health configuration found for service: {service_name}")
            return None

        base_config = self.services[service_name]

        if environment is None:
            environment = get_env().get('ENVIRONMENT', 'development')

        return base_config.get_effective_config(environment)

    def get_critical_services(self, environment: Optional[str] = None) -> List[str]:
        """Get list of critical services for the given environment."""
        if environment is None:
            environment = get_env().get('ENVIRONMENT', 'development')

        critical_services = []
        for service_name, service_config in self.services.items():
            effective_config = service_config.get_effective_config(environment)
            if effective_config.criticality == ServiceCriticality.CRITICAL:
                critical_services.append(service_name)

        return critical_services

    def should_fail_health_check(
        self,
        failed_services: Dict[str, str],
        environment: Optional[str] = None
    ) -> tuple[bool, str]:
        """
        Determine if health check should fail based on failed services and environment rules.

        Args:
            failed_services: Dict of service_name -> error_message for failed services
            environment: Target environment (defaults to current environment)

        Returns:
            Tuple of (should_fail: bool, reason: str)
        """
        if environment is None:
            environment = get_env().get('ENVIRONMENT', 'development')

        critical_services = self.get_critical_services(environment)
        failed_critical_services = [
            service for service in failed_services.keys()
            if service in critical_services
        ]

        if failed_critical_services:
            return True, f"Critical services failed: {', '.join(failed_critical_services)}"

        # Check overall failure threshold
        total_important_and_critical = len([
            s for s_name, s_config in self.services.items()
            if s_config.get_effective_config(environment).criticality in [
                ServiceCriticality.CRITICAL, ServiceCriticality.IMPORTANT
            ]
        ])

        if total_important_and_critical == 0:
            return False, "No important services configured"

        failed_important_services = len([
            service for service in failed_services.keys()
            if service in self.services and
            self.services[service].get_effective_config(environment).criticality in [
                ServiceCriticality.CRITICAL, ServiceCriticality.IMPORTANT
            ]
        ])

        failure_rate = failed_important_services / total_important_and_critical

        if failure_rate >= self.overall_failure_threshold:
            return True, f"Too many important services failed ({failure_rate:.1%} >= {self.overall_failure_threshold:.1%})"

        return False, "Sufficient services operational"


# Environment-specific configurations
_ENVIRONMENT_CONFIGS: Dict[str, EnvironmentHealthConfig] = {
    "development": EnvironmentHealthConfig(
        default_timeout_seconds=5.0,
        health_check_timeout_seconds=15.0,
        overall_failure_threshold=0.8,  # More lenient in development
        allow_partial_startup=True,
        log_level_on_failure="WARNING"
    ),

    "staging": EnvironmentHealthConfig(
        default_timeout_seconds=8.0,
        health_check_timeout_seconds=25.0,
        overall_failure_threshold=0.3,  # CRITICAL: More lenient for staging (only 30% critical services need to pass)
        allow_partial_startup=True,      # CRITICAL: Allow partial startup for Cloud Run
        log_level_on_failure="WARNING"
    ),

    "production": EnvironmentHealthConfig(
        default_timeout_seconds=10.0,
        health_check_timeout_seconds=30.0,
        overall_failure_threshold=0.2,  # Strict in production
        allow_partial_startup=False,
        log_level_on_failure="ERROR"
    )
}


def get_environment_health_config(environment: Optional[str] = None) -> EnvironmentHealthConfig:
    """
    Get the health configuration for the specified environment.

    Args:
        environment: Target environment (defaults to current environment)

    Returns:
        EnvironmentHealthConfig: Configuration for the environment
    """
    if environment is None:
        environment = get_env().get('ENVIRONMENT', 'development')

    if environment not in _ENVIRONMENT_CONFIGS:
        logger.warning(f"No health config for environment '{environment}', using development defaults")
        environment = "development"

    config = _ENVIRONMENT_CONFIGS[environment]
    logger.info(f"Loaded health configuration for environment: {environment}")
    return config


def is_service_enabled(service_name: str, environment: Optional[str] = None) -> bool:
    """
    Check if a service is enabled in the given environment.

    Args:
        service_name: Name of the service to check
        environment: Target environment (defaults to current environment)

    Returns:
        bool: True if service is enabled (not disabled)
    """
    config = get_environment_health_config(environment)
    service_config = config.get_service_config(service_name, environment)

    if service_config is None:
        return True  # Unknown services are enabled by default

    return service_config.criticality != ServiceCriticality.DISABLED


def get_service_timeout(service_name: str, environment: Optional[str] = None) -> float:
    """
    Get the timeout for a specific service in the given environment.

    Args:
        service_name: Name of the service
        environment: Target environment (defaults to current environment)

    Returns:
        float: Timeout in seconds
    """
    config = get_environment_health_config(environment)
    service_config = config.get_service_config(service_name, environment)

    if service_config is None:
        return config.default_timeout_seconds

    return service_config.timeout_seconds


# Export main functions and classes
__all__ = [
    "EnvironmentHealthConfig",
    "ServiceHealthConfig",
    "ServiceCriticality",
    "HealthFailureMode",
    "get_environment_health_config",
    "is_service_enabled",
    "get_service_timeout"
]