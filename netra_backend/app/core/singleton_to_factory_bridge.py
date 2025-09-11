"""
Singleton to Factory Migration Bridge - Backward Compatibility Layer

Business Value Justification (BVJ):
- Segment: Platform/Core Infrastructure
- Business Goal: $500K+ ARR Protection during Zero-Downtime Migration
- Value Impact: Enables gradual migration from singletons to user-scoped factories without breaking changes
- Strategic Impact: Provides safety net during migration ensuring business continuity

This module provides backward compatibility bridges that detect context availability
and route to appropriate implementation (user-scoped or singleton fallback), enabling
seamless migration from singleton patterns to factory patterns.

CRITICAL BUSINESS CONTEXT:
- Zero downtime migration from singleton to factory patterns
- Automatic detection of user context availability
- Gradual migration path without breaking existing code
- Business continuity during transition period
- Performance monitoring to track migration progress

MIGRATION STRATEGY:
1. Phase 1: Deploy factories alongside singletons with bridge routing
2. Phase 2: Gradually migrate callers to provide user context
3. Phase 3: Monitor singleton usage decline and factory adoption
4. Phase 4: Remove singleton code once migration is complete

ARCHITECTURE COMPLIANCE:
@compliance CLAUDE.md - Factory patterns for user-scoped components (Section 2.1)
@compliance SPEC/core.xml - Single Source of Truth coordination patterns
@compliance SPEC/type_safety.xml - Strongly typed migration interfaces

Migration Phase: Phase 1 - Backward Compatibility Implementation
GitHub Issue: https://github.com/netra-systems/netra-apex/issues/232
"""

import threading
import time
from typing import Any, Dict, Optional, Type, TypeVar, Union, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

from netra_backend.app.logging_config import central_logger
from netra_backend.app.core.user_execution_context import UserExecutionContext
from netra_backend.app.core.user_factory_coordinator import (
    get_user_factory_coordinator,
    UserScopedServiceLocator,
    UserScopedEventValidator,
    UserScopedWebSocketEventRouter
)

logger = central_logger.get_logger(__name__)
T = TypeVar("T")


class RoutingMode(Enum):
    """Routing modes for the migration bridge."""
    USER_SCOPED = "user_scoped"        # Use user-scoped factory
    SINGLETON_FALLBACK = "singleton_fallback"  # Use legacy singleton
    MIGRATION_DETECTED = "migration_detected"  # Context provided but using singleton


@dataclass
class BridgeMetrics:
    """Metrics for tracking migration progress."""
    total_calls: int = 0
    user_scoped_calls: int = 0
    singleton_fallback_calls: int = 0
    migration_detected_calls: int = 0
    last_reset: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    @property
    def user_scoped_percentage(self) -> float:
        """Calculate percentage of calls using user-scoped factories."""
        if self.total_calls == 0:
            return 0.0
        return (self.user_scoped_calls / self.total_calls) * 100
    
    @property
    def migration_progress_percentage(self) -> float:
        """Calculate overall migration progress percentage."""
        if self.total_calls == 0:
            return 0.0
        # Include migration_detected as partial progress
        progress_calls = self.user_scoped_calls + (self.migration_detected_calls * 0.5)
        return (progress_calls / self.total_calls) * 100


class SingletonToFactoryBridge:
    """
    Central bridge for managing singleton to factory migration.
    
    This bridge provides automatic routing between singleton and factory patterns
    based on context availability, enabling seamless migration without breaking changes.
    """
    
    def __init__(self):
        """Initialize bridge with metrics tracking."""
        self._metrics_lock = threading.RLock()
        
        # Component-specific metrics
        self._service_locator_metrics = BridgeMetrics()
        self._event_validator_metrics = BridgeMetrics()
        self._event_router_metrics = BridgeMetrics()
        
        # Global metrics
        self._start_time = datetime.now(timezone.utc)
        
        logger.info("SingletonToFactoryBridge initialized for migration support")
    
    def get_service_locator(self, 
                           service_type: Type[T],
                           user_context: Optional[UserExecutionContext] = None) -> T:
        """
        Bridge method for ServiceLocator access.
        
        Routes to user-scoped factory if context is available,
        otherwise falls back to singleton for backward compatibility.
        
        Args:
            service_type: Service interface type
            user_context: Optional UserExecutionContext for user-scoped access
            
        Returns:
            Service instance (user-scoped or singleton)
        """
        with self._metrics_lock:
            self._service_locator_metrics.total_calls += 1
            
            if user_context is not None:
                # Use user-scoped factory
                self._service_locator_metrics.user_scoped_calls += 1
                routing_mode = RoutingMode.USER_SCOPED
                
                try:
                    coordinator = get_user_factory_coordinator()
                    user_locator = coordinator.get_user_service_locator(user_context)
                    service = user_locator.get(service_type)
                    
                    logger.debug(
                        f"ServiceLocator bridge: USER_SCOPED route for {service_type.__name__} "
                        f"(user: {user_context.user_id[:8]}...)"
                    )
                    
                    return service
                    
                except Exception as e:
                    logger.error(
                        f"ServiceLocator bridge: USER_SCOPED route failed for {service_type.__name__}: {e}"
                    )
                    # Fall through to singleton fallback
            
            # Fallback to singleton
            self._service_locator_metrics.singleton_fallback_calls += 1
            routing_mode = RoutingMode.SINGLETON_FALLBACK
            
            from netra_backend.app.services.service_locator import get_service
            
            logger.warning(
                f"ServiceLocator bridge: SINGLETON_FALLBACK route for {service_type.__name__} "
                f"(context provided: {user_context is not None})"
            )
            
            return get_service(service_type)
    
    def get_event_validator(self, 
                           user_context: Optional[UserExecutionContext] = None,
                           strict_mode: bool = True,
                           timeout_seconds: float = 30.0) -> Union[UserScopedEventValidator, Any]:
        """
        Bridge method for EventValidator access.
        
        Args:
            user_context: Optional UserExecutionContext for user-scoped access
            strict_mode: Whether to require ALL 5 critical events
            timeout_seconds: Maximum time to wait for events
            
        Returns:
            Event validator instance (user-scoped or singleton)
        """
        with self._metrics_lock:
            self._event_validator_metrics.total_calls += 1
            
            if user_context is not None:
                # Use user-scoped factory
                self._event_validator_metrics.user_scoped_calls += 1
                
                try:
                    coordinator = get_user_factory_coordinator()
                    user_validator = coordinator.get_user_event_validator(
                        user_context, strict_mode, timeout_seconds
                    )
                    
                    logger.debug(
                        f"EventValidator bridge: USER_SCOPED route "
                        f"(user: {user_context.user_id[:8]}...)"
                    )
                    
                    return user_validator
                    
                except Exception as e:
                    logger.error(
                        f"EventValidator bridge: USER_SCOPED route failed: {e}"
                    )
                    # Fall through to singleton fallback
            
            # Fallback to singleton
            self._event_validator_metrics.singleton_fallback_calls += 1
            
            from netra_backend.app.websocket_core.event_validator import get_websocket_validator
            
            logger.warning(
                f"EventValidator bridge: SINGLETON_FALLBACK route "
                f"(context provided: {user_context is not None})"
            )
            
            return get_websocket_validator()
    
    def get_event_router(self, 
                        user_context: Optional[UserExecutionContext] = None,
                        websocket_manager: Optional[Any] = None) -> Union[UserScopedWebSocketEventRouter, Any]:
        """
        Bridge method for EventRouter access.
        
        Args:
            user_context: Optional UserExecutionContext for user-scoped access
            websocket_manager: Optional WebSocket manager
            
        Returns:
            Event router instance (user-scoped or singleton)
        """
        with self._metrics_lock:
            self._event_router_metrics.total_calls += 1
            
            if user_context is not None:
                # Use user-scoped factory
                self._event_router_metrics.user_scoped_calls += 1
                
                try:
                    coordinator = get_user_factory_coordinator()
                    user_router = coordinator.get_user_event_router(user_context)
                    
                    logger.debug(
                        f"EventRouter bridge: USER_SCOPED route "
                        f"(user: {user_context.user_id[:8]}...)"
                    )
                    
                    return user_router
                    
                except Exception as e:
                    logger.error(
                        f"EventRouter bridge: USER_SCOPED route failed: {e}"
                    )
                    # Fall through to singleton fallback
            
            # Fallback to singleton
            self._event_router_metrics.singleton_fallback_calls += 1
            
            from netra_backend.app.services.websocket_event_router import get_websocket_router
            
            logger.warning(
                f"EventRouter bridge: SINGLETON_FALLBACK route "
                f"(context provided: {user_context is not None})"
            )
            
            return get_websocket_router(websocket_manager)
    
    def get_migration_metrics(self) -> Dict[str, Any]:
        """
        Get comprehensive migration metrics.
        
        Returns:
            Dictionary with migration progress metrics
        """
        with self._metrics_lock:
            uptime = (datetime.now(timezone.utc) - self._start_time).total_seconds()
            
            return {
                "bridge_uptime_seconds": uptime,
                "service_locator": {
                    "total_calls": self._service_locator_metrics.total_calls,
                    "user_scoped_calls": self._service_locator_metrics.user_scoped_calls,
                    "singleton_fallback_calls": self._service_locator_metrics.singleton_fallback_calls,
                    "migration_detected_calls": self._service_locator_metrics.migration_detected_calls,
                    "user_scoped_percentage": self._service_locator_metrics.user_scoped_percentage,
                    "migration_progress_percentage": self._service_locator_metrics.migration_progress_percentage
                },
                "event_validator": {
                    "total_calls": self._event_validator_metrics.total_calls,
                    "user_scoped_calls": self._event_validator_metrics.user_scoped_calls,
                    "singleton_fallback_calls": self._event_validator_metrics.singleton_fallback_calls,
                    "migration_detected_calls": self._event_validator_metrics.migration_detected_calls,
                    "user_scoped_percentage": self._event_validator_metrics.user_scoped_percentage,
                    "migration_progress_percentage": self._event_validator_metrics.migration_progress_percentage
                },
                "event_router": {
                    "total_calls": self._event_router_metrics.total_calls,
                    "user_scoped_calls": self._event_router_metrics.user_scoped_calls,
                    "singleton_fallback_calls": self._event_router_metrics.singleton_fallback_calls,
                    "migration_detected_calls": self._event_router_metrics.migration_detected_calls,
                    "user_scoped_percentage": self._event_router_metrics.user_scoped_percentage,
                    "migration_progress_percentage": self._event_router_metrics.migration_progress_percentage
                },
                "overall_migration_progress": self._calculate_overall_progress()
            }
    
    def _calculate_overall_progress(self) -> float:
        """Calculate overall migration progress across all components."""
        total_calls = (
            self._service_locator_metrics.total_calls +
            self._event_validator_metrics.total_calls +
            self._event_router_metrics.total_calls
        )
        
        if total_calls == 0:
            return 0.0
        
        total_user_scoped = (
            self._service_locator_metrics.user_scoped_calls +
            self._event_validator_metrics.user_scoped_calls +
            self._event_router_metrics.user_scoped_calls
        )
        
        return (total_user_scoped / total_calls) * 100
    
    def reset_metrics(self):
        """Reset all metrics (useful for testing or milestone tracking)."""
        with self._metrics_lock:
            self._service_locator_metrics = BridgeMetrics()
            self._event_validator_metrics = BridgeMetrics()
            self._event_router_metrics = BridgeMetrics()
            self._start_time = datetime.now(timezone.utc)
            
            logger.info("Migration bridge metrics reset")
    
    def log_migration_report(self):
        """Log comprehensive migration progress report."""
        metrics = self.get_migration_metrics()
        
        logger.info("=== SINGLETON TO FACTORY MIGRATION REPORT ===")
        logger.info(f"Overall Migration Progress: {metrics['overall_migration_progress']:.1f}%")
        logger.info(f"Bridge Uptime: {metrics['bridge_uptime_seconds']:.1f} seconds")
        
        for component, stats in metrics.items():
            if isinstance(stats, dict) and 'total_calls' in stats:
                logger.info(
                    f"{component.replace('_', ' ').title()}: "
                    f"{stats['user_scoped_percentage']:.1f}% user-scoped "
                    f"({stats['user_scoped_calls']}/{stats['total_calls']} calls)"
                )


# Global bridge instance
_bridge_instance: Optional[SingletonToFactoryBridge] = None
_bridge_lock = threading.RLock()


def get_migration_bridge() -> SingletonToFactoryBridge:
    """
    Get the global SingletonToFactoryBridge instance.
    
    Returns:
        SingletonToFactoryBridge instance
    """
    global _bridge_instance
    
    with _bridge_lock:
        if _bridge_instance is None:
            _bridge_instance = SingletonToFactoryBridge()
        
        return _bridge_instance


# Convenience functions for bridge access

def get_service_with_bridge(service_type: Type[T], 
                           user_context: Optional[UserExecutionContext] = None) -> T:
    """
    Get service through migration bridge.
    
    Args:
        service_type: Service interface type
        user_context: Optional UserExecutionContext for user-scoped access
        
    Returns:
        Service instance (user-scoped or singleton)
    """
    bridge = get_migration_bridge()
    return bridge.get_service_locator(service_type, user_context)


def get_event_validator_with_bridge(user_context: Optional[UserExecutionContext] = None,
                                   strict_mode: bool = True,
                                   timeout_seconds: float = 30.0) -> Union[UserScopedEventValidator, Any]:
    """
    Get event validator through migration bridge.
    
    Args:
        user_context: Optional UserExecutionContext for user-scoped access
        strict_mode: Whether to require ALL 5 critical events
        timeout_seconds: Maximum time to wait for events
        
    Returns:
        Event validator instance (user-scoped or singleton)
    """
    bridge = get_migration_bridge()
    return bridge.get_event_validator(user_context, strict_mode, timeout_seconds)


def get_event_router_with_bridge(user_context: Optional[UserExecutionContext] = None,
                                websocket_manager: Optional[Any] = None) -> Union[UserScopedWebSocketEventRouter, Any]:
    """
    Get event router through migration bridge.
    
    Args:
        user_context: Optional UserExecutionContext for user-scoped access
        websocket_manager: Optional WebSocket manager
        
    Returns:
        Event router instance (user-scoped or singleton)
    """
    bridge = get_migration_bridge()
    return bridge.get_event_router(user_context, websocket_manager)


def get_migration_progress_report() -> Dict[str, Any]:
    """
    Get comprehensive migration progress report.
    
    Returns:
        Dictionary with migration metrics
    """
    bridge = get_migration_bridge()
    return bridge.get_migration_metrics()


def log_migration_status():
    """Log current migration status to help track progress."""
    bridge = get_migration_bridge()
    bridge.log_migration_report()


# Context detection utilities

def detect_user_context_in_kwargs(**kwargs) -> Optional[UserExecutionContext]:
    """
    Detect UserExecutionContext in function kwargs.
    
    This utility helps existing functions detect if a user context
    is available in their arguments for migration.
    
    Args:
        **kwargs: Function keyword arguments
        
    Returns:
        UserExecutionContext if found, None otherwise
    """
    # Common parameter names for user context
    context_keys = [
        'user_context',
        'execution_context', 
        'context',
        'user_execution_context'
    ]
    
    for key in context_keys:
        value = kwargs.get(key)
        if isinstance(value, UserExecutionContext):
            return value
    
    return None


def extract_user_context_from_args(*args) -> Optional[UserExecutionContext]:
    """
    Extract UserExecutionContext from function positional arguments.
    
    Args:
        *args: Function positional arguments
        
    Returns:
        UserExecutionContext if found, None otherwise
    """
    for arg in args:
        if isinstance(arg, UserExecutionContext):
            return arg
    
    return None


# Migration decorators for gradual adoption

def migrate_to_user_scoped(component_type: str):
    """
    Decorator to gradually migrate functions to user-scoped access.
    
    Args:
        component_type: Type of component ('service_locator', 'event_validator', 'event_router')
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            # Try to detect user context in arguments
            user_context = extract_user_context_from_args(*args) or detect_user_context_in_kwargs(**kwargs)
            
            if user_context is not None:
                logger.debug(
                    f"Migration decorator: UserContext detected for {func.__name__} "
                    f"({component_type})"
                )
            
            # Call original function with context awareness
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


# SSOT Exports
__all__ = [
    # Core classes
    "SingletonToFactoryBridge",
    "BridgeMetrics",
    "RoutingMode",
    
    # Global access
    "get_migration_bridge",
    
    # Convenience functions
    "get_service_with_bridge",
    "get_event_validator_with_bridge",
    "get_event_router_with_bridge",
    "get_migration_progress_report",
    "log_migration_status",
    
    # Migration utilities
    "detect_user_context_in_kwargs",
    "extract_user_context_from_args",
    "migrate_to_user_scoped"
]