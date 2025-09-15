"""
Error policy framework for environment-aware exception handling.

This module provides the foundational framework for progressive error escalation
across development, staging, and production environments while maintaining
business value protection and backward compatibility.

SSOP Compliance:
- Uses SSOT pattern with IsolatedEnvironment for all environment access
- Eliminates direct os.getenv() usage in favor of shared.isolated_environment.get_env()
- Maintains singleton pattern for consistent policy across application
- Supports dependency injection for testing while maintaining production safety

Business Value:
- Enables progressive error escalation (dev warnings -> staging errors -> prod failures)
- Protects business-critical flows in production while allowing development flexibility
- Provides consistent error handling policies across all environments
- Supports graceful degradation and recovery strategies
"""

import logging
from enum import Enum
from typing import Any, Dict, Optional, Union, Callable, TYPE_CHECKING
from datetime import datetime, timezone

# Use TYPE_CHECKING to avoid circular imports
if TYPE_CHECKING:
    from shared.isolated_environment import IsolatedEnvironment

# Import get_env for SSOT environment access
from shared.isolated_environment import get_env

from netra_backend.app.core.exceptions_base import NetraException
from netra_backend.app.core.error_codes import ErrorSeverity


class EnvironmentType(Enum):
    """Environment types for error policy decisions."""
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"
    UNKNOWN = "unknown"


class ErrorEscalationPolicy(Enum):
    """Error escalation policies for different severity levels."""
    WARN_ONLY = "warn_only"              # Log warning and continue
    WARN_WITH_METRICS = "warn_metrics"   # Log warning + emit metrics
    ERROR_GRACEFUL = "error_graceful"    # Raise exception with fallback
    ERROR_STRICT = "error_strict"        # Raise exception, no fallback
    FATAL = "fatal"                      # Immediate system shutdown


class ErrorPolicy:
    """
    Environment-aware error policy management for systematic remediation.

    Provides centralized policy decisions for when warnings should be escalated
    to errors based on environment context and business impact assessment.

    Business Value: Enables safe rollout of error escalation without disrupting
    existing functionality in development while ensuring production reliability.
    """

    _instance: Optional['ErrorPolicy'] = None
    _environment_type: Optional[EnvironmentType] = None
    _policy_overrides: Dict[str, ErrorEscalationPolicy] = {}
    _initialized: bool = False
    _env_accessor: Optional['IsolatedEnvironment'] = None

    def __new__(cls, isolated_env: Optional['IsolatedEnvironment'] = None) -> 'ErrorPolicy':
        """Singleton pattern for consistent policy across application."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, isolated_env: Optional['IsolatedEnvironment'] = None) -> None:
        """
        Initialize ErrorPolicy with optional IsolatedEnvironment dependency injection.

        Args:
            isolated_env: Optional IsolatedEnvironment instance for SSOT compliance.
                         If not provided, uses shared get_env() function.

        Note:
            Maintains singleton pattern - only first initialization is effective.
            Subsequent calls to __init__ are ignored to preserve singleton behavior.
        """
        # Prevent re-initialization in singleton pattern
        if self.__class__._initialized:
            return

        # Store the environment accessor as class variable for classmethod access
        if isolated_env is not None:
            self.__class__._env_accessor = isolated_env
        elif self.__class__._env_accessor is None:
            # Only set default if not already set
            self.__class__._env_accessor = get_env()

        self.__class__._initialized = True
    
    @classmethod
    def detect_environment(cls) -> EnvironmentType:
        """
        Detect current environment type for policy decisions.
        
        Uses multiple indicators to reliably determine environment:
        - Environment variables (ENVIRONMENT, NETRA_ENV)  
        - Service discovery patterns
        - Configuration markers
        """
        if cls._environment_type is not None:
            return cls._environment_type
        
        # Check explicit environment variables - SSOT compliant
        # Initialize environment accessor if not set
        if cls._env_accessor is None:
            cls._env_accessor = get_env()

        env_var = cls._env_accessor.get('ENVIRONMENT', '').lower()
        netra_env = cls._env_accessor.get('NETRA_ENV', '').lower()
        
        # Production indicators
        if any(env in ['prod', 'production'] for env in [env_var, netra_env]):
            cls._environment_type = EnvironmentType.PRODUCTION
        # Staging indicators
        elif any(env in ['staging', 'stage'] for env in [env_var, netra_env]):
            cls._environment_type = EnvironmentType.STAGING
        # Testing indicators
        elif any(env in ['test', 'testing'] for env in [env_var, netra_env]):
            cls._environment_type = EnvironmentType.TESTING
        # Development indicators (default)
        elif any(env in ['dev', 'development', 'local'] for env in [env_var, netra_env]):
            cls._environment_type = EnvironmentType.DEVELOPMENT
        else:
            # Additional detection logic
            if cls._detect_production_indicators():
                cls._environment_type = EnvironmentType.PRODUCTION
            elif cls._detect_staging_indicators():
                cls._environment_type = EnvironmentType.STAGING
            elif cls._detect_testing_indicators():
                cls._environment_type = EnvironmentType.TESTING
            else:
                # Default to development for safety
                cls._environment_type = EnvironmentType.DEVELOPMENT
        
        return cls._environment_type
    
    @classmethod
    def _detect_production_indicators(cls) -> bool:
        """Detect production environment through indirect indicators."""
        # Ensure environment accessor is available
        if cls._env_accessor is None:
            cls._env_accessor = get_env()

        indicators = [
            # GCP production project
            cls._env_accessor.get('GCP_PROJECT', '').endswith('-prod'),
            # Production database URLs
            'prod' in cls._env_accessor.get('DATABASE_URL', '').lower(),
            # Production Redis
            'prod' in cls._env_accessor.get('REDIS_URL', '').lower(),
            # Production service discovery
            cls._env_accessor.get('SERVICE_ENV') == 'production'
        ]
        return any(indicators)
    
    @classmethod
    def _detect_staging_indicators(cls) -> bool:
        """Detect staging environment through indirect indicators."""
        # Ensure environment accessor is available
        if cls._env_accessor is None:
            cls._env_accessor = get_env()

        indicators = [
            # GCP staging project
            cls._env_accessor.get('GCP_PROJECT', '').endswith('-staging'),
            # Staging database URLs
            'staging' in cls._env_accessor.get('DATABASE_URL', '').lower(),
            # Staging Redis
            'staging' in cls._env_accessor.get('REDIS_URL', '').lower(),
            # Staging service discovery
            cls._env_accessor.get('SERVICE_ENV') == 'staging'
        ]
        return any(indicators)
    
    @classmethod
    def _detect_testing_indicators(cls) -> bool:
        """Detect testing environment through indirect indicators."""
        # Ensure environment accessor is available
        if cls._env_accessor is None:
            cls._env_accessor = get_env()

        indicators = [
            # Pytest running
            'pytest' in cls._env_accessor.get('_', '').lower(),
            # Test database ports
            cls._env_accessor.get('POSTGRES_PORT') in ['5434', '5433'],
            # Test Redis ports
            cls._env_accessor.get('REDIS_PORT') in ['6381', '6380'],
            # CI/CD environment
            bool(cls._env_accessor.get('CI')),
            # Testing framework markers
            bool(cls._env_accessor.get('TESTING'))
        ]
        return any(indicators)
    
    @classmethod
    def get_escalation_policy(
        cls, 
        error_category: str,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        business_critical: bool = False
    ) -> ErrorEscalationPolicy:
        """
        Get appropriate escalation policy based on environment and context.
        
        Args:
            error_category: Category of error (websocket, agent, deprecated, etc.)
            severity: Error severity level
            business_critical: Whether error affects core business functionality
            
        Returns:
            Appropriate escalation policy for current environment
        """
        # Check for explicit overrides first
        override_key = f"{error_category}.{severity.value}"
        if override_key in cls._policy_overrides:
            return cls._policy_overrides[override_key]
        
        environment = cls.detect_environment()
        
        # Production: Strict error handling for business-critical, graceful for others
        if environment == EnvironmentType.PRODUCTION:
            if business_critical or severity == ErrorSeverity.CRITICAL:
                return ErrorEscalationPolicy.ERROR_STRICT
            elif severity == ErrorSeverity.HIGH:
                return ErrorEscalationPolicy.ERROR_GRACEFUL
            else:
                return ErrorEscalationPolicy.WARN_WITH_METRICS
        
        # Staging: Progressive escalation to test production readiness
        elif environment == EnvironmentType.STAGING:
            if severity == ErrorSeverity.CRITICAL:
                return ErrorEscalationPolicy.ERROR_STRICT
            elif severity == ErrorSeverity.HIGH or business_critical:
                return ErrorEscalationPolicy.ERROR_GRACEFUL
            else:
                return ErrorEscalationPolicy.WARN_WITH_METRICS
        
        # Testing: Errors for validation, warnings for non-critical
        elif environment == EnvironmentType.TESTING:
            if severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
                return ErrorEscalationPolicy.ERROR_GRACEFUL
            else:
                return ErrorEscalationPolicy.WARN_ONLY
        
        # Development: Warnings only to avoid disrupting development flow
        else:  # DEVELOPMENT or UNKNOWN
            if severity == ErrorSeverity.CRITICAL:
                return ErrorEscalationPolicy.ERROR_GRACEFUL
            else:
                return ErrorEscalationPolicy.WARN_ONLY
    
    @classmethod
    def set_policy_override(
        cls, 
        error_category: str, 
        severity: ErrorSeverity,
        policy: ErrorEscalationPolicy
    ) -> None:
        """Set explicit policy override for testing or special cases."""
        override_key = f"{error_category}.{severity.value}"
        cls._policy_overrides[override_key] = policy
    
    @classmethod
    def clear_policy_overrides(cls) -> None:
        """Clear all policy overrides (useful for testing)."""
        cls._policy_overrides.clear()
    
    @classmethod
    def force_environment(cls, env_type: EnvironmentType) -> None:
        """Force specific environment type (useful for testing)."""
        cls._environment_type = env_type


class EnvironmentAwareException:
    """
    Mixin for exceptions that should behave differently based on environment.
    
    Provides policy-aware exception behavior that can escalate from warnings
    to errors based on environment context and business impact.
    """
    
    @classmethod
    def handle_with_policy(
        cls,
        error_category: str,
        message: str,
        exception_class: type = None,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        business_critical: bool = False,
        context: Optional[Dict[str, Any]] = None,
        logger: Optional[logging.Logger] = None,
        fallback_action: Optional[Callable] = None
    ) -> Optional[Exception]:
        """
        Handle error according to environment-aware policy.
        
        Args:
            error_category: Category of error for policy lookup
            message: Error message
            exception_class: Exception class to raise if escalating
            severity: Error severity level
            business_critical: Whether error affects core business functionality
            context: Additional context for error
            logger: Logger for warning messages
            fallback_action: Optional fallback action for graceful degradation
            
        Returns:
            Exception if raised, None if handled as warning
        """
        policy = ErrorPolicy.get_escalation_policy(error_category, severity, business_critical)
        
        # Build enhanced context
        enhanced_context = context or {}
        enhanced_context.update({
            "environment": ErrorPolicy.detect_environment().value,
            "escalation_policy": policy.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "business_critical": business_critical
        })
        
        if policy == ErrorEscalationPolicy.WARN_ONLY:
            if logger:
                logger.warning(f"[{error_category}] {message}")
            return None
        
        elif policy == ErrorEscalationPolicy.WARN_WITH_METRICS:
            if logger:
                logger.warning(f"[{error_category}] {message} (metrics emitted)")
            # TODO: Emit metrics in future phases
            return None
        
        elif policy == ErrorEscalationPolicy.ERROR_GRACEFUL:
            # Execute fallback if available, then raise
            if fallback_action:
                try:
                    fallback_action()
                except Exception as fallback_error:
                    enhanced_context["fallback_error"] = str(fallback_error)
            
            if exception_class and issubclass(exception_class, NetraException):
                exc = exception_class(message=message, context=enhanced_context)
            else:
                exc = RuntimeError(f"[{error_category}] {message}")
            raise exc
        
        elif policy == ErrorEscalationPolicy.ERROR_STRICT:
            if exception_class and issubclass(exception_class, NetraException):
                exc = exception_class(message=message, context=enhanced_context)
            else:
                exc = RuntimeError(f"[{error_category}] {message}")
            raise exc
        
        else:  # FATAL
            if logger:
                logger.critical(f"[{error_category}] FATAL: {message}")
            # TODO: Implement graceful shutdown in future phases
            raise SystemExit(f"FATAL ERROR: {message}")


class ProgressiveErrorHandler:
    """
    Progressive error handler that escalates warnings to errors over multiple phases.
    
    Provides a structured approach to migrating from warnings to errors while
    maintaining system stability and business value protection.
    """
    
    def __init__(self, category: str, logger: Optional[logging.Logger] = None):
        self.category = category
        self.logger = logger
        self.policy_engine = ErrorPolicy()
    
    def handle_websocket_event_failure(
        self, 
        event_type: str, 
        error: Exception,
        agent_name: str = None,
        run_id: str = None
    ) -> None:
        """Handle WebSocket event emission failures with progressive escalation."""
        from netra_backend.app.core.exceptions.websocket_exceptions import WebSocketEventEmissionError
        
        EnvironmentAwareException.handle_with_policy(
            error_category=f"{self.category}.websocket_event",
            message=f"Failed to emit {event_type} event: {error}",
            exception_class=WebSocketEventEmissionError,
            severity=ErrorSeverity.HIGH,
            business_critical=True,  # WebSocket events are critical for UX
            context={
                "event_type": event_type,
                "agent_name": agent_name, 
                "run_id": run_id,
                "original_error": str(error)
            },
            logger=self.logger
        )
    
    def handle_agent_lifecycle_failure(
        self,
        agent_name: str,
        phase: str,
        error: Exception,
        run_id: str = None
    ) -> None:
        """Handle agent lifecycle failures with progressive escalation."""
        from netra_backend.app.core.exceptions.agent_exceptions import AgentLifecycleError
        
        EnvironmentAwareException.handle_with_policy(
            error_category=f"{self.category}.agent_lifecycle",
            message=f"Agent {agent_name} lifecycle failure in {phase}: {error}",
            exception_class=AgentLifecycleError,
            severity=ErrorSeverity.HIGH,
            business_critical=True,  # Agent lifecycle is critical for execution
            context={
                "agent_name": agent_name,
                "lifecycle_phase": phase,
                "run_id": run_id,
                "original_error": str(error)
            },
            logger=self.logger
        )
    
    def handle_deprecated_pattern(
        self,
        pattern_name: str,
        usage_location: str,
        modern_alternative: str
    ) -> None:
        """Handle deprecated pattern usage with progressive escalation."""
        from netra_backend.app.core.exceptions.deprecated_pattern_exceptions import DeprecatedGlobalToolDispatcherError
        
        EnvironmentAwareException.handle_with_policy(
            error_category=f"{self.category}.deprecated_pattern",
            message=f"Deprecated pattern {pattern_name} used at {usage_location}",
            exception_class=DeprecatedGlobalToolDispatcherError,
            severity=ErrorSeverity.MEDIUM,
            business_critical=False,  # Technical debt, not business-critical
            context={
                "pattern_name": pattern_name,
                "usage_location": usage_location,
                "modern_alternative": modern_alternative
            },
            logger=self.logger
        )