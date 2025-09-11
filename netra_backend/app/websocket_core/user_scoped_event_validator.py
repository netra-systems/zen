"""
User-Scoped EventValidator Factory - Complete User Isolation for WebSocket Event Validation

Business Value Justification (BVJ):
- Segment: Platform/Core Infrastructure
- Business Goal: $500K+ ARR Protection through Event Validation Isolation
- Value Impact: Prevents singleton-based event validation sharing that causes cross-user contamination
- Strategic Impact: Ensures secure per-user event validation with guaranteed isolation

This module provides the foundational factory pattern to replace the EventValidator singleton
with per-user instances, preventing cross-user event validation state that blocks chat functionality.

CRITICAL BUSINESS CONTEXT:
- Each user execution must get completely isolated event validation instances
- Shared validation state between users causes event confusion and blocks chat delivery
- Factory patterns ensure each user gets fresh, isolated validation component instances
- This factory enables EventValidator isolation critical for WebSocket event delivery

SINGLETON VIOLATION RESOLUTION:
This factory directly addresses the EventValidator singleton violations identified in:
- Shared validation statistics causing cross-user contamination
- Event sequence validation confusion between users
- Business value scoring mixing users' event streams
- Mission critical event tracking shared across user sessions

ARCHITECTURE COMPLIANCE:
@compliance CLAUDE.md - WebSocket events enable substantive chat interactions (Section 6)
@compliance SPEC/core.xml - Single Source of Truth event validation patterns
@compliance SPEC/type_safety.xml - Strongly typed event validation interfaces

Migration Phase: Phase 1 - Foundation Implementation (Parallel to Singleton)
GitHub Issue: https://github.com/netra-systems/netra-apex/issues/232
"""

import threading
import weakref
from typing import Any, Dict, Optional, Set, List, Union, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone

from netra_backend.app.logging_config import central_logger
from netra_backend.app.core.user_execution_context import UserExecutionContext
from netra_backend.app.websocket_core.event_validator import (
    UnifiedEventValidator,
    ValidationResult,
    WebSocketEventMessage,
    EventCriticality,
    CriticalAgentEventType,
    get_critical_event_types
)
from shared.types.execution_types import StronglyTypedUserExecutionContext

logger = central_logger.get_logger(__name__)


@dataclass
class UserEventValidationRegistry:
    """
    Per-user event validation registry with complete isolation.
    
    This registry maintains all event validation state for a single user execution context,
    ensuring complete isolation from other users' validation states.
    """
    user_context: UserExecutionContext
    validator: UnifiedEventValidator
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    validation_count: int = field(default=0)
    last_access: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def __post_init__(self):
        """Initialize registry with user context validation."""
        if not isinstance(self.user_context, UserExecutionContext):
            raise ValueError("UserEventValidationRegistry requires valid UserExecutionContext")
        
        logger.debug(
            f"UserEventValidationRegistry created for user {self.user_context.user_id[:8]}... "
            f"(request: {self.user_context.request_id[:8]}...)"
        )
    
    def get_isolation_key(self) -> str:
        """Get unique isolation key for this user registry."""
        return self.user_context.get_scoped_key("event_validator")
    
    def is_expired(self, max_age_seconds: int = 1800) -> bool:  # 30 minutes default
        """Check if registry has exceeded maximum age."""
        age = (datetime.now(timezone.utc) - self.created_at).total_seconds()
        return age > max_age_seconds
    
    def update_access_time(self):
        """Update last access time for this registry."""
        # Since this is a frozen dataclass, we need to use object.__setattr__
        object.__setattr__(self, 'last_access', datetime.now(timezone.utc))


class UserScopedEventValidator:
    """
    User-scoped event validator providing complete isolation between user executions.
    
    This class replaces the singleton UnifiedEventValidator pattern with per-user instances,
    ensuring that each user's event validation state is completely isolated from other
    users, preventing validation confusion and ensuring accurate business value tracking.
    
    Key Features:
    - Complete user isolation through UserExecutionContext
    - Per-user validation state with independent lifecycles
    - Business value scoring isolated per user
    - Event sequence validation isolated per user
    - Mission critical event tracking per user
    - Thread-safe operations with user-scoped locking
    """
    
    def __init__(self, user_context: UserExecutionContext, strict_mode: bool = True, timeout_seconds: float = 30.0):
        """
        Initialize user-scoped event validator.
        
        Args:
            user_context: UserExecutionContext for complete isolation
            strict_mode: Whether to require ALL 5 critical events
            timeout_seconds: Maximum time to wait for events
            
        Raises:
            ValueError: If user_context is invalid
        """
        if not isinstance(user_context, UserExecutionContext):
            raise ValueError("UserScopedEventValidator requires valid UserExecutionContext")
        
        self.user_context = user_context
        self.registry = UserEventValidationRegistry(
            user_context=user_context,
            validator=UnifiedEventValidator(
                user_context=StronglyTypedUserExecutionContext(
                    user_id=user_context.user_id,
                    thread_id=user_context.thread_id,
                    run_id=user_context.run_id,
                    request_id=user_context.request_id
                ),
                strict_mode=strict_mode,
                timeout_seconds=timeout_seconds
            )
        )
        self._lock = threading.RLock()
        
        logger.info(
            f"UserScopedEventValidator initialized for user {user_context.user_id[:8]}... "
            f"(isolation_key: {self.registry.get_isolation_key()}, strict_mode: {strict_mode})"
        )
    
    def validate_event(self, event: Dict[str, Any], connection_id: Optional[str] = None) -> ValidationResult:
        """
        Validate a WebSocket event for this user.
        
        Args:
            event: Event data to validate
            connection_id: Optional connection ID
            
        Returns:
            ValidationResult with validation outcome
        """
        with self._lock:
            self.registry.update_access_time()
            self.registry.validation_count += 1
            
            result = self.registry.validator.validate_event(
                event=event,
                user_id=self.user_context.user_id,
                connection_id=connection_id
            )
            
            logger.debug(
                f"Event validated for user {self.user_context.user_id[:8]}...: "
                f"{event.get('type', 'unknown')} (valid: {result.is_valid})"
            )
            
            return result
    
    def record_event(self, event_data: Union[Dict[str, Any], WebSocketEventMessage]) -> bool:
        """
        Record a WebSocket event for this user's business value tracking.
        
        Args:
            event_data: Event data (dict or WebSocketEventMessage)
            
        Returns:
            True if event was recorded successfully
        """
        with self._lock:
            self.registry.update_access_time()
            return self.registry.validator.record_event(event_data)
    
    def validate_connection_ready(self, connection_id: str, websocket_manager: Optional[Any] = None) -> ValidationResult:
        """
        Validate that connection is ready for event emission for this user.
        
        Args:
            connection_id: Connection ID to validate
            websocket_manager: Optional WebSocket manager to check against
            
        Returns:
            ValidationResult with connection readiness status
        """
        with self._lock:
            self.registry.update_access_time()
            return self.registry.validator.validate_connection_ready(
                user_id=self.user_context.user_id,
                connection_id=connection_id,
                websocket_manager=websocket_manager
            )
    
    def validate_event_sequence(self) -> Tuple[bool, List[str]]:
        """
        Validate that events are received in logical order for this user.
        
        Returns:
            Tuple of (is_valid, validation_errors)
        """
        with self._lock:
            self.registry.update_access_time()
            return self.registry.validator.validate_event_sequence()
    
    def validate_event_timing(self) -> Tuple[bool, List[str]]:
        """
        Validate event timing constraints for this user.
        
        Returns:
            Tuple of (is_valid, validation_errors)
        """
        with self._lock:
            self.registry.update_access_time()
            return self.registry.validator.validate_event_timing()
    
    def validate_event_content(self) -> Tuple[bool, List[str]]:
        """
        Validate event content for business value delivery for this user.
        
        Returns:
            Tuple of (is_valid, validation_errors)
        """
        with self._lock:
            self.registry.update_access_time()
            return self.registry.validator.validate_event_content()
    
    def perform_full_validation(self) -> ValidationResult:
        """
        Perform comprehensive validation of all received events for this user.
        
        Returns:
            ValidationResult with complete validation results
        """
        with self._lock:
            self.registry.update_access_time()
            return self.registry.validator.perform_full_validation()
    
    def wait_for_critical_events(self, timeout: Optional[float] = None) -> ValidationResult:
        """
        Wait for all critical events to be received for this user.
        
        Args:
            timeout: Optional timeout override
            
        Returns:
            ValidationResult once complete or timeout
        """
        with self._lock:
            self.registry.update_access_time()
            return self.registry.validator.wait_for_critical_events(timeout)
    
    def get_validation_stats(self) -> Dict[str, Any]:
        """
        Get validation statistics for this user.
        
        Returns:
            Dictionary with user-specific validation statistics
        """
        with self._lock:
            self.registry.update_access_time()
            stats = self.registry.validator.get_validation_stats()
            
            # Add user-specific metadata
            stats.update({
                "user_id_prefix": self.user_context.user_id[:8] + "...",
                "isolation_key": self.registry.get_isolation_key(),
                "registry_validation_count": self.registry.validation_count,
                "registry_created_at": self.registry.created_at.isoformat(),
                "registry_last_access": self.registry.last_access.isoformat(),
                "registry_age_seconds": (datetime.now(timezone.utc) - self.registry.created_at).total_seconds()
            })
            
            return stats
    
    def reset_stats(self):
        """Reset validation statistics for this user."""
        with self._lock:
            self.registry.validator.reset_stats()
            object.__setattr__(self.registry, 'validation_count', 0)
            self.registry.update_access_time()
            
            logger.debug(f"Reset validation stats for user {self.user_context.user_id[:8]}...")
    
    def get_user_context(self) -> UserExecutionContext:
        """Get the user execution context for this validator."""
        return self.user_context
    
    def get_critical_events_received(self) -> Set[str]:
        """Get the set of critical events received for this user."""
        with self._lock:
            return self.registry.validator.critical_events_received.copy()
    
    def get_required_critical_events(self) -> Set[str]:
        """Get the set of required critical events."""
        return self.registry.validator.get_required_critical_events()
    
    def get_business_value_score(self) -> float:
        """Get current business value score for this user."""
        with self._lock:
            return self.registry.validator._calculate_current_business_value_score()


class EventValidatorFactory:
    """
    Factory for creating user-scoped EventValidator instances.
    
    This factory manages the lifecycle of UserScopedEventValidator instances,
    providing automatic cleanup and memory management to prevent resource leaks.
    """
    
    def __init__(self):
        """Initialize factory with user registry tracking."""
        self._user_validators: Dict[str, weakref.ReferenceType] = {}
        self._lock = threading.RLock()
        
        logger.info("EventValidatorFactory initialized")
    
    def create_for_user(self, 
                       user_context: UserExecutionContext, 
                       strict_mode: bool = True, 
                       timeout_seconds: float = 30.0) -> UserScopedEventValidator:
        """
        Create or get user-scoped event validator.
        
        Args:
            user_context: UserExecutionContext for isolation
            strict_mode: Whether to require ALL 5 critical events
            timeout_seconds: Maximum time to wait for events
            
        Returns:
            UserScopedEventValidator for the user
        """
        with self._lock:
            isolation_key = user_context.get_scoped_key("event_validator")
            
            # Check if we already have a validator for this user context
            if isolation_key in self._user_validators:
                existing_ref = self._user_validators[isolation_key]
                existing_validator = existing_ref()
                
                if existing_validator is not None:
                    logger.debug(
                        f"Reusing existing EventValidator for user {user_context.user_id[:8]}..."
                    )
                    return existing_validator
                else:
                    # Clean up dead reference
                    del self._user_validators[isolation_key]
            
            # Create new user-scoped validator
            validator = UserScopedEventValidator(
                user_context=user_context,
                strict_mode=strict_mode,
                timeout_seconds=timeout_seconds
            )
            
            # Store weak reference for cleanup tracking
            self._user_validators[isolation_key] = weakref.ref(validator)
            
            logger.info(
                f"Created new UserScopedEventValidator for user {user_context.user_id[:8]}... "
                f"(total active: {len(self._user_validators)})"
            )
            
            return validator
    
    def cleanup_expired_validators(self, max_age_seconds: int = 1800) -> int:
        """
        Clean up expired user validators.
        
        Args:
            max_age_seconds: Maximum age before cleanup (default: 30 minutes)
            
        Returns:
            Number of validators cleaned up
        """
        with self._lock:
            expired_keys = []
            
            for isolation_key, validator_ref in self._user_validators.items():
                validator = validator_ref()
                
                if validator is None:
                    # Dead reference
                    expired_keys.append(isolation_key)
                elif validator.registry.is_expired(max_age_seconds):
                    # Expired validator
                    validator.reset_stats()
                    expired_keys.append(isolation_key)
            
            # Clean up expired references
            for key in expired_keys:
                del self._user_validators[key]
            
            if expired_keys:
                logger.info(f"Cleaned up {len(expired_keys)} expired event validators")
            
            return len(expired_keys)
    
    def get_factory_stats(self) -> Dict[str, Any]:
        """
        Get factory statistics.
        
        Returns:
            Dictionary with factory statistics
        """
        with self._lock:
            active_count = 0
            total_validations = 0
            total_business_value = 0.0
            
            for validator_ref in self._user_validators.values():
                validator = validator_ref()
                if validator is not None:
                    active_count += 1
                    stats = validator.get_validation_stats()
                    total_validations += stats.get("total_validations", 0)
                    total_business_value += stats.get("business_value_score", 0.0)
            
            avg_business_value = total_business_value / active_count if active_count > 0 else 0.0
            
            return {
                "active_validators": active_count,
                "total_tracked": len(self._user_validators),
                "total_validations": total_validations,
                "average_business_value_score": avg_business_value,
                "dead_references": len(self._user_validators) - active_count
            }
    
    def get_user_validator_if_exists(self, user_context: UserExecutionContext) -> Optional[UserScopedEventValidator]:
        """
        Get existing user validator if it exists.
        
        Args:
            user_context: UserExecutionContext to look up
            
        Returns:
            UserScopedEventValidator if exists, None otherwise
        """
        with self._lock:
            isolation_key = user_context.get_scoped_key("event_validator")
            
            if isolation_key in self._user_validators:
                validator_ref = self._user_validators[isolation_key]
                return validator_ref()
            
            return None


# Global factory instance for creating user-scoped validators
_factory_instance: Optional[EventValidatorFactory] = None
_factory_lock = threading.RLock()


def get_event_validator_factory() -> EventValidatorFactory:
    """
    Get the global EventValidatorFactory instance.
    
    Returns:
        EventValidatorFactory instance
    """
    global _factory_instance
    
    with _factory_lock:
        if _factory_instance is None:
            _factory_instance = EventValidatorFactory()
        
        return _factory_instance


def create_user_event_validator(user_context: UserExecutionContext,
                               strict_mode: bool = True,
                               timeout_seconds: float = 30.0) -> UserScopedEventValidator:
    """
    Create user-scoped event validator for the given context.
    
    Args:
        user_context: UserExecutionContext for isolation
        strict_mode: Whether to require ALL 5 critical events
        timeout_seconds: Maximum time to wait for events
        
    Returns:
        UserScopedEventValidator instance
    """
    factory = get_event_validator_factory()
    return factory.create_for_user(user_context, strict_mode, timeout_seconds)


def validate_user_event(event: Dict[str, Any], 
                       user_context: UserExecutionContext,
                       connection_id: Optional[str] = None) -> ValidationResult:
    """
    Convenience function to validate an event for a specific user.
    
    Args:
        event: Event data to validate
        user_context: UserExecutionContext for isolation
        connection_id: Optional connection ID
        
    Returns:
        ValidationResult for the user's validation
    """
    validator = create_user_event_validator(user_context)
    return validator.validate_event(event, connection_id)


def validate_user_agent_events(events: List[Union[Dict[str, Any], WebSocketEventMessage]],
                              user_context: UserExecutionContext,
                              strict_mode: bool = True) -> ValidationResult:
    """
    SSOT function to validate a list of agent events for a specific user.
    
    Args:
        events: List of events to validate
        user_context: UserExecutionContext for isolation
        strict_mode: If True, require ALL 5 critical events
        
    Returns:
        ValidationResult with validation results
    """
    validator = create_user_event_validator(user_context, strict_mode=strict_mode)
    
    # Record all events
    for event in events:
        validator.record_event(event)
    
    return validator.perform_full_validation()


def assert_user_critical_events_received(events: List[Union[Dict[str, Any], WebSocketEventMessage]],
                                        user_context: UserExecutionContext,
                                        custom_error_message: Optional[str] = None) -> None:
    """
    Assert that all critical agent events are received for a specific user.
    
    Args:
        events: List of events to validate
        user_context: UserExecutionContext for isolation
        custom_error_message: Optional custom error message
        
    Raises:
        AssertionError: If critical events are missing or invalid
    """
    result = validate_user_agent_events(events, user_context, strict_mode=True)
    
    if not result.is_valid:
        error_msg = custom_error_message or (
            f"CRITICAL AGENT EVENTS VALIDATION FAILED for user {user_context.user_id[:8]}...\n"
            f"Revenue Impact: {result.revenue_impact}\n"
            f"Missing Events: {result.missing_critical_events}\n"
            f"Business Value Score: {result.business_value_score:.1f}%\n"
            f"Error Details: {result.error_message}\n"
            f"This failure blocks revenue-generating chat functionality for this user!"
        )
        raise AssertionError(error_msg)


# Backward Compatibility Bridge
def get_websocket_validator_with_context(user_context: Optional[UserExecutionContext] = None) -> Union[UnifiedEventValidator, UserScopedEventValidator]:
    """
    Backward compatibility function that routes to appropriate validator.
    
    If user_context is provided, uses user-scoped validator.
    Otherwise, falls back to singleton validator for backward compatibility.
    
    Args:
        user_context: Optional UserExecutionContext for user-scoped access
        
    Returns:
        Event validator instance (user-scoped or singleton)
    """
    if user_context is not None:
        return create_user_event_validator(user_context)
    else:
        # Fallback to singleton for backward compatibility
        from netra_backend.app.websocket_core.event_validator import get_websocket_validator
        logger.warning(
            "Using singleton EventValidator - consider migrating to user-scoped access"
        )
        return get_websocket_validator()


# SSOT Exports
__all__ = [
    # Core classes
    "UserScopedEventValidator",
    "EventValidatorFactory",
    "UserEventValidationRegistry",
    
    # Factory functions
    "get_event_validator_factory",
    "create_user_event_validator",
    "validate_user_event",
    
    # SSOT validation functions
    "validate_user_agent_events",
    "assert_user_critical_events_received",
    
    # Compatibility functions
    "get_websocket_validator_with_context"
]