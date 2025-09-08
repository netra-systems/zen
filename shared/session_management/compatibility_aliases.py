"""SessionMetrics Compatibility Aliases - SSOT Violation Migration Support

This module provides temporary compatibility aliases during the SessionMetrics SSOT
violation remediation. It ensures that existing code continues to work while we
migrate from the conflicting SessionMetrics classes to the new business-focused names.

Business Value Justification (BVJ):
- Segment: Platform/Internal - Migration risk mitigation
- Business Goal: Zero-downtime migration from SSOT violation to clean architecture
- Value Impact: Prevents system breakage during critical infrastructure changes
- Strategic Impact: Enables safe, atomic migration to business-focused naming

Key Features:
- Backward compatibility aliases for both SessionMetrics classes
- Safe attribute access with proper error handling
- Gradual migration support with deprecation warnings
- Type-safe access patterns during transition period
- Clear migration paths for all existing code

Migration Strategy:
This module provides temporary aliases that will be gradually deprecated:
1. Phase 1: Aliases active, warnings logged for deprecated usage
2. Phase 2: Aliases deprecated, errors logged but still functional
3. Phase 3: Aliases removed, migration complete

CRITICAL WARNING:
This module is TEMPORARY and will be removed after migration is complete.
All code should migrate to use SystemSessionAggregator and UserSessionTracker directly.
"""

import warnings
from typing import Any, Dict, Optional, Type, Union
from datetime import datetime, timezone

from netra_backend.app.logging_config import central_logger
from .session_metrics_provider import (
    UnifiedSessionMetrics,
    SessionMetricsAdapter,
    get_unified_session_metrics_provider
)

logger = central_logger.get_logger(__name__)

# Migration phase configuration
MIGRATION_PHASE = 1  # 1=Active, 2=Deprecated, 3=Removed


class SessionMetricsCompatibilityWrapper:
    """Compatibility wrapper for legacy SessionMetrics access.
    
    This wrapper provides backward compatibility for code that expects the
    old SessionMetrics interface while redirecting to the new unified system.
    """
    
    def __init__(self, metrics_source: str = "unified"):
        """Initialize compatibility wrapper.
        
        Args:
            metrics_source: Source of metrics ("system", "user", or "unified")
        """
        self._metrics_source = metrics_source
        self._cached_metrics: Optional[UnifiedSessionMetrics] = None
        self._cache_timestamp: Optional[datetime] = None
        self._cache_timeout_seconds = 30
        
        # Log compatibility wrapper usage
        if MIGRATION_PHASE == 1:
            logger.info(f"SessionMetrics compatibility wrapper active for {metrics_source}")
        elif MIGRATION_PHASE == 2:
            logger.warning(f"DEPRECATED: SessionMetrics compatibility wrapper used for {metrics_source}. "
                          "Please migrate to SystemSessionAggregator or UserSessionTracker.")
    
    def _get_fresh_metrics(self) -> UnifiedSessionMetrics:
        """Get fresh metrics, using cache if still valid."""
        now = datetime.now(timezone.utc)
        
        if (self._cached_metrics and 
            self._cache_timestamp and 
            (now - self._cache_timestamp).total_seconds() < self._cache_timeout_seconds):
            return self._cached_metrics
        
        # Get fresh metrics from unified provider
        try:
            provider = get_unified_session_metrics_provider()
            
            # Simple synchronous access for compatibility
            if self._metrics_source == "system":
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        self._cached_metrics = SessionMetricsAdapter.create_safe_default()
                    else:
                        self._cached_metrics = loop.run_until_complete(provider.get_system_metrics())
                except RuntimeError:
                    self._cached_metrics = asyncio.run(provider.get_system_metrics())
            
            elif self._metrics_source == "user":
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        self._cached_metrics = SessionMetricsAdapter.create_safe_default()
                    else:
                        self._cached_metrics = loop.run_until_complete(provider.get_user_metrics())
                except RuntimeError:
                    self._cached_metrics = asyncio.run(provider.get_user_metrics())
            
            else:  # unified
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        self._cached_metrics = SessionMetricsAdapter.create_safe_default()
                    else:
                        self._cached_metrics = loop.run_until_complete(provider.get_combined_metrics())
                except RuntimeError:
                    self._cached_metrics = asyncio.run(provider.get_combined_metrics())
            
            self._cache_timestamp = now
            
        except Exception as e:
            logger.error(f"Error getting metrics for compatibility wrapper: {e}")
            self._cached_metrics = SessionMetricsAdapter.create_safe_default()
            self._cache_timestamp = now
        
        return self._cached_metrics
    
    def __getattr__(self, name: str) -> Any:
        """Provide compatible attribute access.
        
        Args:
            name: Attribute name being accessed
            
        Returns:
            Attribute value from unified metrics
        """
        # CRITICAL: Handle the specific last_activity attribute that causes errors
        if name == "last_activity":
            metrics = self._get_fresh_metrics()
            return metrics.last_activity
        
        # Handle other common attributes
        metrics = self._get_fresh_metrics()
        
        if hasattr(metrics, name):
            return getattr(metrics, name)
        
        # Handle legacy attribute mappings
        legacy_mappings = {
            # System-level legacy mappings
            "last_activity_at": "last_activity",  # Map old system attribute to new
            "session_id": None,  # Not available in unified metrics
            "request_id": None,  # Not available in unified metrics
            "user_id": None,     # Not available in unified metrics
            "created_at": "timestamp",
            "state": None,       # Not available in unified metrics
            "query_count": None, # Not available in unified metrics
            "transaction_count": None, # Not available in unified metrics
            "total_time_ms": None,     # Not available in unified metrics
            "closed_at": None,         # Not available in unified metrics
            "error_count": None,       # Not available in unified metrics
            "last_error": None,        # Not available in unified metrics
            
            # User-level legacy mappings  
            "memory_usage_mb": "memory_usage_mb",  # Direct mapping
            "expired_sessions_cleaned": "expired_sessions_cleaned",  # Direct mapping
        }
        
        if name in legacy_mappings:
            mapped_name = legacy_mappings[name]
            if mapped_name and hasattr(metrics, mapped_name):
                return getattr(metrics, mapped_name)
            else:
                # Attribute not available - return safe default
                logger.warning(f"Legacy attribute '{name}' not available in unified metrics")
                return None
        
        # Log unknown attribute access
        logger.error(f"Unknown attribute '{name}' accessed on SessionMetrics compatibility wrapper")
        raise AttributeError(f"'SessionMetrics' object has no attribute '{name}'")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for backward compatibility."""
        metrics = self._get_fresh_metrics()
        return metrics.to_dict()
    
    def mark_activity(self) -> None:
        """Mock method for backward compatibility."""
        logger.warning("mark_activity() called on compatibility wrapper - operation ignored")
    
    def record_error(self, error: str) -> None:
        """Mock method for backward compatibility."""
        logger.warning(f"record_error('{error}') called on compatibility wrapper - operation ignored")
    
    def close(self) -> None:
        """Mock method for backward compatibility."""
        logger.warning("close() called on compatibility wrapper - operation ignored")


# CRITICAL: These are the compatibility aliases that fix the SSOT violation
class SystemSessionMetrics(SessionMetricsCompatibilityWrapper):
    """Compatibility alias for system-level SessionMetrics.
    
    DEPRECATED: Use SystemSessionAggregator directly.
    This alias maps to system-level session metrics functionality.
    """
    
    def __init__(self):
        super().__init__("system")
        
        if MIGRATION_PHASE >= 2:
            warnings.warn(
                "SystemSessionMetrics is deprecated. Use SystemSessionAggregator instead.",
                DeprecationWarning,
                stacklevel=2
            )


class UserSessionMetrics(SessionMetricsCompatibilityWrapper):
    """Compatibility alias for user-level SessionMetrics.
    
    DEPRECATED: Use UserSessionTracker directly.
    This alias maps to user-level session metrics functionality.
    """
    
    def __init__(self):
        super().__init__("user")
        
        if MIGRATION_PHASE >= 2:
            warnings.warn(
                "UserSessionMetrics is deprecated. Use UserSessionTracker instead.", 
                DeprecationWarning,
                stacklevel=2
            )


# CRITICAL: Legacy SessionMetrics alias that resolves the SSOT violation
class SessionMetrics(SessionMetricsCompatibilityWrapper):
    """Legacy SessionMetrics compatibility alias.
    
    This class resolves the SSOT violation by providing a unified interface
    that works regardless of which original SessionMetrics was expected.
    
    CRITICAL: This fixes the 'last_activity' AttributeError by ensuring
    the attribute is always available through the unified interface.
    
    DEPRECATED: Use SystemSessionAggregator or UserSessionTracker directly
    based on your specific use case:
    - SystemSessionAggregator: For database session lifecycle tracking
    - UserSessionTracker: For user behavior and engagement tracking
    """
    
    def __init__(self, **kwargs):
        """Initialize legacy SessionMetrics with backward compatibility.
        
        Args:
            **kwargs: Legacy constructor arguments (ignored for compatibility)
        """
        # Determine which type of metrics based on constructor arguments
        if any(arg in kwargs for arg in ['session_id', 'request_id', 'user_id', 'created_at']):
            # Looks like system-level SessionMetrics constructor
            super().__init__("system")
        elif any(arg in kwargs for arg in ['total_sessions', 'active_sessions', 'memory_usage_mb']):
            # Looks like user-level SessionMetrics constructor  
            super().__init__("user")
        else:
            # Default to unified
            super().__init__("unified")
        
        if MIGRATION_PHASE >= 2:
            warnings.warn(
                "SessionMetrics is deprecated due to SSOT violation. "
                "Use SystemSessionAggregator for system metrics or "
                "UserSessionTracker for user metrics.",
                DeprecationWarning,
                stacklevel=2
            )
        
        # Store constructor arguments for backward compatibility
        self._constructor_kwargs = kwargs
        
        # CRITICAL: Ensure last_activity is always available
        if 'last_activity' not in self.__dict__:
            self.last_activity = datetime.now(timezone.utc)
        if 'last_activity_at' not in self.__dict__:
            self.last_activity_at = datetime.now(timezone.utc)


# Factory functions for creating appropriate SessionMetrics instances
def create_system_session_metrics(**kwargs) -> SessionMetrics:
    """Create SessionMetrics for system-level operations.
    
    DEPRECATED: Use SystemSessionAggregator directly.
    
    Returns:
        SessionMetrics: System-focused metrics instance
    """
    if MIGRATION_PHASE >= 2:
        logger.warning("create_system_session_metrics() is deprecated. Use SystemSessionAggregator.")
    
    return SessionMetrics(**kwargs)


def create_user_session_metrics(**kwargs) -> SessionMetrics:
    """Create SessionMetrics for user-level operations.
    
    DEPRECATED: Use UserSessionTracker directly.
    
    Returns:
        SessionMetrics: User-focused metrics instance
    """
    if MIGRATION_PHASE >= 2:
        logger.warning("create_user_session_metrics() is deprecated. Use UserSessionTracker.")
    
    return SessionMetrics(**kwargs)


# Migration helper functions
def get_migration_status() -> Dict[str, Any]:
    """Get current migration status and recommendations.
    
    Returns:
        Migration status information
    """
    return {
        'migration_phase': MIGRATION_PHASE,
        'phase_description': {
            1: "Active - Compatibility aliases working, no warnings",
            2: "Deprecated - Compatibility aliases working with warnings", 
            3: "Removed - Migration must be complete"
        }.get(MIGRATION_PHASE, "Unknown"),
        'recommendations': {
            'system_metrics': "Migrate to SystemSessionAggregator",
            'user_metrics': "Migrate to UserSessionTracker", 
            'unified_access': "Use UnifiedSessionMetricsProvider"
        },
        'breaking_changes': {
            'last_activity': "Now always available through unified interface",
            'constructor_args': "New classes have different constructor signatures",
            'method_names': "Some methods renamed for clarity"
        }
    }


# Export compatibility interface
__all__ = [
    # CRITICAL: These aliases resolve the SSOT violation
    'SessionMetrics',           # Legacy unified alias
    'SystemSessionMetrics',     # System-specific alias
    'UserSessionMetrics',       # User-specific alias
    
    # Factory functions
    'create_system_session_metrics',
    'create_user_session_metrics',
    
    # Migration utilities
    'get_migration_status',
    'SessionMetricsCompatibilityWrapper'
]