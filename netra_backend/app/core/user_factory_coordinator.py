"""
User Factory Coordinator - Unified Management of User-Scoped Component Factories

Business Value Justification (BVJ):
- Segment: Platform/Core Infrastructure
- Business Goal: $500K+ ARR Protection through Comprehensive User Isolation
- Value Impact: Coordinates all singleton-to-factory migrations ensuring complete user isolation
- Strategic Impact: Provides single entry point for all user-scoped components, eliminating session bleeding

This module provides the central coordination layer for all user-scoped component factories,
ensuring consistent lifecycle management, cleanup, and monitoring across ServiceLocator,
EventValidator, and EventRouter factories.

CRITICAL BUSINESS CONTEXT:
- Single point of coordination for all user-scoped component creation
- Unified lifecycle management prevents resource leaks and memory issues
- Coordinated cleanup ensures proper user session termination
- Monitoring and metrics across all user-scoped components
- Business continuity through coordinated fallback mechanisms

SINGLETON VIOLATION RESOLUTION:
This coordinator directly addresses the systemic singleton violations by:
- Coordinating ServiceLocator, EventValidator, and EventRouter factory patterns
- Providing unified user context management across all components
- Ensuring consistent cleanup to prevent memory leaks
- Monitoring factory health and business value delivery
- Providing fallback mechanisms during migration phase

ARCHITECTURE COMPLIANCE:
@compliance CLAUDE.md - Factory patterns for user-scoped components (Section 2.1)
@compliance SPEC/core.xml - Single Source of Truth coordination patterns
@compliance SPEC/type_safety.xml - Strongly typed factory coordination interfaces

Migration Phase: Phase 1 - Foundation Implementation (Coordinated Factory Management)
GitHub Issue: https://github.com/netra-systems/netra-apex/issues/232
"""

import asyncio
import threading
import weakref
from typing import Any, Dict, Optional, Set, List, Tuple, NamedTuple
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

from netra_backend.app.logging_config import central_logger
from netra_backend.app.core.user_execution_context import UserExecutionContext
from netra_backend.app.services.user_scoped_service_locator import (
    UserScopedServiceLocator,
    ServiceLocatorFactory,
    get_service_locator_factory
)
from netra_backend.app.websocket_core.user_scoped_event_validator import (
    UserScopedEventValidator,
    EventValidatorFactory,
    get_event_validator_factory
)
from netra_backend.app.services.user_scoped_websocket_event_router import (
    UserScopedWebSocketEventRouter,
    WebSocketEventRouterFactory,
    get_event_router_factory
)

logger = central_logger.get_logger(__name__)


class ComponentType(Enum):
    """Types of user-scoped components managed by the coordinator."""
    SERVICE_LOCATOR = "service_locator"
    EVENT_VALIDATOR = "event_validator"
    EVENT_ROUTER = "event_router"


class CoordinatorHealth(Enum):
    """Health status of the factory coordinator."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    FAILED = "failed"


@dataclass
class ComponentStats:
    """Statistics for a specific component type."""
    component_type: ComponentType
    active_instances: int
    total_tracked: int
    dead_references: int
    total_operations: int
    last_cleanup: datetime
    health_status: CoordinatorHealth


@dataclass
class UserComponentSet:
    """
    Complete set of user-scoped components for a single user.
    
    This represents all the isolated components needed for a user's
    execution context, ensuring complete isolation from other users.
    """
    user_context: UserExecutionContext
    service_locator: Optional[UserScopedServiceLocator] = None
    event_validator: Optional[UserScopedEventValidator] = None
    event_router: Optional[UserScopedWebSocketEventRouter] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_access: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    access_count: int = field(default=0)
    
    def __post_init__(self):
        """Initialize component set with user context validation."""
        if not isinstance(self.user_context, UserExecutionContext):
            raise ValueError("UserComponentSet requires valid UserExecutionContext")
        
        logger.debug(
            f"UserComponentSet created for user {self.user_context.user_id[:8]}... "
            f"(request: {self.user_context.request_id[:8]}...)"
        )
    
    def get_isolation_key(self) -> str:
        """Get unique isolation key for this component set."""
        return self.user_context.get_scoped_key("component_set")
    
    def is_expired(self, max_age_seconds: int = 3600) -> bool:
        """Check if component set has exceeded maximum age."""
        age = (datetime.now(timezone.utc) - self.created_at).total_seconds()
        return age > max_age_seconds
    
    def update_access_time(self):
        """Update last access time and increment access count."""
        object.__setattr__(self, 'last_access', datetime.now(timezone.utc))
        object.__setattr__(self, 'access_count', self.access_count + 1)
    
    def get_component_count(self) -> int:
        """Get number of instantiated components."""
        count = 0
        if self.service_locator is not None:
            count += 1
        if self.event_validator is not None:
            count += 1
        if self.event_router is not None:
            count += 1
        return count
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics for this component set."""
        return {
            "user_id_prefix": self.user_context.user_id[:8] + "...",
            "isolation_key": self.get_isolation_key(),
            "component_count": self.get_component_count(),
            "has_service_locator": self.service_locator is not None,
            "has_event_validator": self.event_validator is not None,
            "has_event_router": self.event_router is not None,
            "created_at": self.created_at.isoformat(),
            "last_access": self.last_access.isoformat(),
            "access_count": self.access_count,
            "age_seconds": (datetime.now(timezone.utc) - self.created_at).total_seconds(),
            "is_expired": self.is_expired()
        }


class UserFactoryCoordinator:
    """
    Central coordinator for all user-scoped component factories.
    
    This coordinator provides a unified interface for creating, managing, and
    cleaning up all user-scoped components (ServiceLocator, EventValidator,
    EventRouter), ensuring consistent lifecycle management and preventing
    resource leaks.
    
    Key Features:
    - Unified component creation and management
    - Coordinated cleanup and lifecycle management
    - Comprehensive monitoring and health checking
    - Business value tracking across all components
    - Thread-safe operations with proper isolation
    - Automatic resource management and memory leak prevention
    """
    
    def __init__(self):
        """Initialize coordinator with factory instances."""
        self._user_components: Dict[str, weakref.ReferenceType] = {}
        self._lock = threading.RLock()
        
        # Initialize factory instances
        self._service_locator_factory = get_service_locator_factory()
        self._event_validator_factory = get_event_validator_factory()
        self._event_router_factory = get_event_router_factory()
        
        # Coordinator metrics
        self._total_created = 0
        self._total_cleaned = 0
        self._last_cleanup = datetime.now(timezone.utc)
        
        logger.info("UserFactoryCoordinator initialized with all component factories")
    
    def create_user_components(self, 
                              user_context: UserExecutionContext,
                              components: Optional[Set[ComponentType]] = None) -> UserComponentSet:
        """
        Create complete set of user-scoped components.
        
        Args:
            user_context: UserExecutionContext for isolation
            components: Optional set of specific components to create (default: all)
            
        Returns:
            UserComponentSet with requested components
        """
        with self._lock:
            isolation_key = user_context.get_scoped_key("component_set")
            
            # Check if we already have components for this user context
            if isolation_key in self._user_components:
                existing_ref = self._user_components[isolation_key]
                existing_set = existing_ref()
                
                if existing_set is not None:
                    existing_set.update_access_time()
                    logger.debug(
                        f"Reusing existing component set for user {user_context.user_id[:8]}..."
                    )
                    return existing_set
                else:
                    # Clean up dead reference
                    del self._user_components[isolation_key]
            
            # Default to creating all components
            if components is None:
                components = {ComponentType.SERVICE_LOCATOR, ComponentType.EVENT_VALIDATOR, ComponentType.EVENT_ROUTER}
            
            # Create new component set
            component_set = UserComponentSet(user_context=user_context)
            
            # Create requested components
            try:
                if ComponentType.SERVICE_LOCATOR in components:
                    component_set.service_locator = self._service_locator_factory.create_for_user(user_context)
                
                if ComponentType.EVENT_VALIDATOR in components:
                    component_set.event_validator = self._event_validator_factory.create_for_user(user_context)
                
                if ComponentType.EVENT_ROUTER in components:
                    component_set.event_router = self._event_router_factory.create_for_user(user_context)
                
                # Store weak reference for cleanup tracking
                self._user_components[isolation_key] = weakref.ref(component_set)
                self._total_created += 1
                
                logger.info(
                    f"Created complete component set for user {user_context.user_id[:8]}... "
                    f"(components: {[c.value for c in components]}, "
                    f"total active: {len(self._user_components)})"
                )
                
                return component_set
                
            except Exception as e:
                logger.critical(
                    f" ALERT:  CRITICAL: Failed to create component set for user "
                    f"{user_context.user_id[:8]}...: {e}"
                )
                logger.critical(
                    f" ALERT:  BUSINESS VALUE AT RISK: User isolation creation failed"
                )
                raise
    
    def get_user_service_locator(self, user_context: UserExecutionContext) -> UserScopedServiceLocator:
        """
        Get or create ServiceLocator for user.
        
        Args:
            user_context: UserExecutionContext for isolation
            
        Returns:
            UserScopedServiceLocator instance
        """
        component_set = self.create_user_components(
            user_context, 
            components={ComponentType.SERVICE_LOCATOR}
        )
        
        if component_set.service_locator is None:
            component_set.service_locator = self._service_locator_factory.create_for_user(user_context)
        
        return component_set.service_locator
    
    def get_user_event_validator(self, 
                                user_context: UserExecutionContext,
                                strict_mode: bool = True,
                                timeout_seconds: float = 30.0) -> UserScopedEventValidator:
        """
        Get or create EventValidator for user.
        
        Args:
            user_context: UserExecutionContext for isolation
            strict_mode: Whether to require ALL 5 critical events
            timeout_seconds: Maximum time to wait for events
            
        Returns:
            UserScopedEventValidator instance
        """
        component_set = self.create_user_components(
            user_context, 
            components={ComponentType.EVENT_VALIDATOR}
        )
        
        if component_set.event_validator is None:
            component_set.event_validator = self._event_validator_factory.create_for_user(
                user_context, strict_mode, timeout_seconds
            )
        
        return component_set.event_validator
    
    def get_user_event_router(self, user_context: UserExecutionContext) -> UserScopedWebSocketEventRouter:
        """
        Get or create EventRouter for user.
        
        Args:
            user_context: UserExecutionContext for isolation
            
        Returns:
            UserScopedWebSocketEventRouter instance
        """
        component_set = self.create_user_components(
            user_context, 
            components={ComponentType.EVENT_ROUTER}
        )
        
        if component_set.event_router is None:
            component_set.event_router = self._event_router_factory.create_for_user(user_context)
        
        return component_set.event_router
    
    async def cleanup_expired_components(self, max_age_seconds: int = 3600) -> int:
        """
        Clean up expired user components across all factories.
        
        Args:
            max_age_seconds: Maximum age before cleanup
            
        Returns:
            Number of component sets cleaned up
        """
        with self._lock:
            expired_keys = []
            
            # Check component sets
            for isolation_key, component_ref in self._user_components.items():
                component_set = component_ref()
                
                if component_set is None:
                    # Dead reference
                    expired_keys.append(isolation_key)
                elif component_set.is_expired(max_age_seconds):
                    # Expired component set
                    expired_keys.append(isolation_key)
            
            # Clean up expired references
            for key in expired_keys:
                del self._user_components[key]
            
            self._total_cleaned += len(expired_keys)
            
            if expired_keys:
                logger.info(f"Cleaned up {len(expired_keys)} expired component sets")
        
        # Clean up individual factories
        service_cleanup = self._service_locator_factory.cleanup_expired_locators(max_age_seconds)
        validator_cleanup = self._event_validator_factory.cleanup_expired_validators(max_age_seconds)
        router_cleanup = await self._event_router_factory.cleanup_expired_routers(max_age_seconds)
        
        total_cleanup = len(expired_keys) + service_cleanup + validator_cleanup + router_cleanup
        
        if total_cleanup > 0:
            self._last_cleanup = datetime.now(timezone.utc)
            logger.info(
                f"Total component cleanup: {total_cleanup} "
                f"(sets: {len(expired_keys)}, services: {service_cleanup}, "
                f"validators: {validator_cleanup}, routers: {router_cleanup})"
            )
        
        return total_cleanup
    
    def get_component_stats(self, component_type: ComponentType) -> ComponentStats:
        """
        Get statistics for a specific component type.
        
        Args:
            component_type: Type of component to get stats for
            
        Returns:
            ComponentStats for the component type
        """
        if component_type == ComponentType.SERVICE_LOCATOR:
            factory_stats = self._service_locator_factory.get_factory_stats()
            return ComponentStats(
                component_type=component_type,
                active_instances=factory_stats["active_locators"],
                total_tracked=factory_stats["total_tracked"],
                dead_references=factory_stats["dead_references"],
                total_operations=factory_stats["total_services"],
                last_cleanup=self._last_cleanup,
                health_status=self._assess_component_health(factory_stats)
            )
        
        elif component_type == ComponentType.EVENT_VALIDATOR:
            factory_stats = self._event_validator_factory.get_factory_stats()
            return ComponentStats(
                component_type=component_type,
                active_instances=factory_stats["active_validators"],
                total_tracked=factory_stats["total_tracked"],
                dead_references=factory_stats["dead_references"],
                total_operations=factory_stats["total_validations"],
                last_cleanup=self._last_cleanup,
                health_status=self._assess_component_health(factory_stats)
            )
        
        elif component_type == ComponentType.EVENT_ROUTER:
            factory_stats = self._event_router_factory.get_factory_stats()
            return ComponentStats(
                component_type=component_type,
                active_instances=factory_stats["active_routers"],
                total_tracked=factory_stats["total_tracked"],
                dead_references=factory_stats["dead_references"],
                total_operations=factory_stats["total_routings"],
                last_cleanup=self._last_cleanup,
                health_status=self._assess_component_health(factory_stats)
            )
        
        else:
            raise ValueError(f"Unknown component type: {component_type}")
    
    def _assess_component_health(self, stats: Dict[str, Any]) -> CoordinatorHealth:
        """Assess health status based on component statistics."""
        active = stats.get("active_instances", 0) or stats.get("active_locators", 0) or stats.get("active_validators", 0) or stats.get("active_routers", 0)
        total = stats.get("total_tracked", 0)
        dead = stats.get("dead_references", 0)
        
        if total == 0:
            return CoordinatorHealth.HEALTHY
        
        dead_ratio = dead / total if total > 0 else 0
        active_ratio = active / total if total > 0 else 0
        
        if dead_ratio > 0.5:  # More than 50% dead references
            return CoordinatorHealth.CRITICAL
        elif dead_ratio > 0.2:  # More than 20% dead references
            return CoordinatorHealth.DEGRADED
        elif active_ratio < 0.5:  # Less than 50% active
            return CoordinatorHealth.DEGRADED
        else:
            return CoordinatorHealth.HEALTHY
    
    def get_coordinator_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive coordinator statistics.
        
        Returns:
            Dictionary with coordinator statistics
        """
        with self._lock:
            active_sets = 0
            total_components = 0
            
            for component_ref in self._user_components.values():
                component_set = component_ref()
                if component_set is not None:
                    active_sets += 1
                    total_components += component_set.get_component_count()
            
            # Get individual component stats
            service_stats = self.get_component_stats(ComponentType.SERVICE_LOCATOR)
            validator_stats = self.get_component_stats(ComponentType.EVENT_VALIDATOR)
            router_stats = self.get_component_stats(ComponentType.EVENT_ROUTER)
            
            # Assess overall health
            component_healths = [service_stats.health_status, validator_stats.health_status, router_stats.health_status]
            overall_health = CoordinatorHealth.HEALTHY
            
            if CoordinatorHealth.CRITICAL in component_healths:
                overall_health = CoordinatorHealth.CRITICAL
            elif CoordinatorHealth.DEGRADED in component_healths:
                overall_health = CoordinatorHealth.DEGRADED
            
            return {
                "active_component_sets": active_sets,
                "total_tracked_sets": len(self._user_components),
                "total_components": total_components,
                "total_created": self._total_created,
                "total_cleaned": self._total_cleaned,
                "last_cleanup": self._last_cleanup.isoformat(),
                "overall_health": overall_health.value,
                "component_stats": {
                    "service_locator": service_stats.__dict__,
                    "event_validator": validator_stats.__dict__,
                    "event_router": router_stats.__dict__
                }
            }
    
    def get_user_component_set_if_exists(self, user_context: UserExecutionContext) -> Optional[UserComponentSet]:
        """
        Get existing user component set if it exists.
        
        Args:
            user_context: UserExecutionContext to look up
            
        Returns:
            UserComponentSet if exists, None otherwise
        """
        with self._lock:
            isolation_key = user_context.get_scoped_key("component_set")
            
            if isolation_key in self._user_components:
                component_ref = self._user_components[isolation_key]
                component_set = component_ref()
                
                if component_set is not None:
                    component_set.update_access_time()
                
                return component_set
            
            return None
    
    async def validate_user_isolation(self, user_context: UserExecutionContext) -> bool:
        """
        Validate that user components maintain proper isolation.
        
        Args:
            user_context: UserExecutionContext to validate
            
        Returns:
            True if isolation is properly maintained
        """
        try:
            component_set = self.get_user_component_set_if_exists(user_context)
            
            if component_set is None:
                # No components exist - isolation is trivially maintained
                return True
            
            # Check individual component isolation
            isolation_issues = []
            
            if component_set.service_locator is not None:
                locator_stats = component_set.service_locator.get_registry_stats()
                expected_key = user_context.get_scoped_key("service_locator")
                if locator_stats["isolation_key"] != expected_key:
                    isolation_issues.append(f"ServiceLocator isolation key mismatch")
            
            if component_set.event_validator is not None:
                validator_stats = component_set.event_validator.get_validation_stats()
                expected_key = user_context.get_scoped_key("event_validator")
                if validator_stats["isolation_key"] != expected_key:
                    isolation_issues.append(f"EventValidator isolation key mismatch")
            
            if component_set.event_router is not None:
                router_stats = await component_set.event_router.get_router_stats()
                expected_key = user_context.get_scoped_key("event_router")
                if router_stats["isolation_key"] != expected_key:
                    isolation_issues.append(f"EventRouter isolation key mismatch")
            
            if isolation_issues:
                logger.critical(
                    f" ALERT:  CRITICAL: User isolation violations detected for user "
                    f"{user_context.user_id[:8]}...: {isolation_issues}"
                )
                logger.critical(
                    f" ALERT:  BUSINESS VALUE AT RISK: Component isolation compromised"
                )
                return False
            
            return True
            
        except Exception as e:
            logger.critical(
                f" ALERT:  CRITICAL: User isolation validation failed for user "
                f"{user_context.user_id[:8]}...: {e}"
            )
            return False


# Global coordinator instance
_coordinator_instance: Optional[UserFactoryCoordinator] = None
_coordinator_lock = threading.RLock()


def get_user_factory_coordinator() -> UserFactoryCoordinator:
    """
    Get the global UserFactoryCoordinator instance.
    
    Returns:
        UserFactoryCoordinator instance
    """
    global _coordinator_instance
    
    with _coordinator_lock:
        if _coordinator_instance is None:
            _coordinator_instance = UserFactoryCoordinator()
        
        return _coordinator_instance


# Convenience functions for unified component access

def create_user_component_set(user_context: UserExecutionContext,
                             components: Optional[Set[ComponentType]] = None) -> UserComponentSet:
    """
    Create complete set of user-scoped components.
    
    Args:
        user_context: UserExecutionContext for isolation
        components: Optional set of specific components to create
        
    Returns:
        UserComponentSet with requested components
    """
    coordinator = get_user_factory_coordinator()
    return coordinator.create_user_components(user_context, components)


def get_user_service_locator_coordinated(user_context: UserExecutionContext) -> UserScopedServiceLocator:
    """
    Get user-scoped ServiceLocator through coordinator.
    
    Args:
        user_context: UserExecutionContext for isolation
        
    Returns:
        UserScopedServiceLocator instance
    """
    coordinator = get_user_factory_coordinator()
    return coordinator.get_user_service_locator(user_context)


def get_user_event_validator_coordinated(user_context: UserExecutionContext,
                                        strict_mode: bool = True,
                                        timeout_seconds: float = 30.0) -> UserScopedEventValidator:
    """
    Get user-scoped EventValidator through coordinator.
    
    Args:
        user_context: UserExecutionContext for isolation
        strict_mode: Whether to require ALL 5 critical events
        timeout_seconds: Maximum time to wait for events
        
    Returns:
        UserScopedEventValidator instance
    """
    coordinator = get_user_factory_coordinator()
    return coordinator.get_user_event_validator(user_context, strict_mode, timeout_seconds)


def get_user_event_router_coordinated(user_context: UserExecutionContext) -> UserScopedWebSocketEventRouter:
    """
    Get user-scoped EventRouter through coordinator.
    
    Args:
        user_context: UserExecutionContext for isolation
        
    Returns:
        UserScopedWebSocketEventRouter instance
    """
    coordinator = get_user_factory_coordinator()
    return coordinator.get_user_event_router(user_context)


async def cleanup_all_user_components(max_age_seconds: int = 3600) -> int:
    """
    Clean up all expired user components across all factories.
    
    Args:
        max_age_seconds: Maximum age before cleanup
        
    Returns:
        Number of components cleaned up
    """
    coordinator = get_user_factory_coordinator()
    return await coordinator.cleanup_expired_components(max_age_seconds)


def get_coordinator_health_report() -> Dict[str, Any]:
    """
    Get comprehensive health report for all user-scoped components.
    
    Returns:
        Dictionary with health report
    """
    coordinator = get_user_factory_coordinator()
    return coordinator.get_coordinator_stats()


# SSOT Exports
__all__ = [
    # Core classes
    "UserFactoryCoordinator",
    "UserComponentSet",
    "ComponentType",
    "CoordinatorHealth",
    "ComponentStats",
    
    # Global access
    "get_user_factory_coordinator",
    
    # Convenience functions
    "create_user_component_set",
    "get_user_service_locator_coordinated",
    "get_user_event_validator_coordinated", 
    "get_user_event_router_coordinated",
    "cleanup_all_user_components",
    "get_coordinator_health_report"
]